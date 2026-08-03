"""Tests for the INLINE (`!`) disposition: GSM->GSM expansion and its consumers."""

from __future__ import annotations

import dataclasses
import pathlib
from collections.abc import Sequence
from typing import cast

import pytest

from fltk.fegen import fltk2gsm, fltk_parser, gsm, gsm2tree
from fltk.fegen import fltk_cst_protocol as cst
from fltk.fegen.pyrt import terminalsrc
from fltk.iir.context import create_default_context
from fltk.iir.py import reg as pyreg
from fltk.lsp.analysis import prepare_analysis_grammar
from fltk.lsp.lsp_config import build_grammar_index
from fltk.plumbing import (
    generate_parser,
    generate_unparser,
    parse_format_config,
    parse_grammar,
    parse_text,
    render_doc,
    unparse_cst,
)
from fltk.unparse import genunparser

ITEM_GRAMMAR_TAIL = "item := name:/[a-z]+/ ;\n"


def raw_grammar(text: str) -> gsm.Grammar:
    """Parse grammar text to GSM *without* applying inline expansion.

    `plumbing.parse_grammar` expands as part of the parse boundary; these tests need the
    unexpanded form so they can drive `expand_inline_dispositions` directly.
    """
    terminals = terminalsrc.TerminalSource(text)
    parser = fltk_parser.Parser(terminalsrc=terminals)
    result = parser.apply__parse_grammar(0)
    assert result is not None, f"grammar failed to parse: {text!r}"
    assert result.pos == len(terminals.terminals), f"grammar not fully consumed: {text!r}"
    return fltk2gsm.Cst2Gsm(terminals.terminals).visit_grammar(cast("cst.Grammar", result.result))


def all_items(grammar: gsm.Grammar) -> list[gsm.Item]:
    """Every Item in the grammar, recursing into sub-expression terms."""
    found: list[gsm.Item] = []
    for rule in grammar.rules:
        for alt in rule.alternatives:
            gsm.for_each_item(alt, lambda _idx, item: found.append(item))
    return found


def all_items_objects(grammar: gsm.Grammar) -> list[gsm.Items]:
    """Every Items object in the grammar, recursing into sub-expression terms."""
    found: list[gsm.Items] = []

    def walk(items: gsm.Items) -> None:
        found.append(items)
        for item in items.items:
            if isinstance(item.term, Sequence):
                for alt in item.term:
                    walk(alt)

    for rule in grammar.rules:
        for alt in rule.alternatives:
            walk(alt)
    return found


def sole_item(grammar: gsm.Grammar, rule_name: str) -> gsm.Item:
    rule = grammar.identifiers[rule_name]
    assert len(rule.alternatives) == 1
    assert len(rule.alternatives[0].items) == 1
    return rule.alternatives[0].items[0]


def spliced_alternatives(item: gsm.Item) -> Sequence[gsm.Items]:
    assert isinstance(item.term, Sequence), f"expected a sub-expression term, got {item.term!r}"
    return cast("Sequence[gsm.Items]", item.term)


class TestExpansionShape:
    def test_basic_splice(self) -> None:
        grammar = raw_grammar(f"wrapper := !inner ;\ninner := a:item . b:item ;\n{ITEM_GRAMMAR_TAIL}")
        expanded = gsm.expand_inline_dispositions(grammar)

        item = sole_item(expanded, "wrapper")
        assert item.label is None
        assert item.disposition == gsm.Disposition.INCLUDE
        assert item.quantifier is gsm.REQUIRED

        alts = spliced_alternatives(item)
        assert list(alts) == list(expanded.identifiers["inner"].alternatives)
        assert [i.label for i in alts[0].items] == ["a", "b"]

    def test_inlined_rule_still_exists(self) -> None:
        grammar = raw_grammar(f"wrapper := !inner ;\ninner := a:item . b:item ;\n{ITEM_GRAMMAR_TAIL}")
        expanded = gsm.expand_inline_dispositions(grammar)

        assert [rule.name for rule in expanded.rules] == ["wrapper", "inner", "item"]

    def test_no_inline_items_remain(self) -> None:
        grammar = raw_grammar(f"wrapper := !inner* ;\ninner := a:item . b:item ;\n{ITEM_GRAMMAR_TAIL}")
        expanded = gsm.expand_inline_dispositions(grammar)

        assert all(item.disposition != gsm.Disposition.INLINE for item in all_items(expanded))

    @pytest.mark.parametrize(
        ("suffix", "quantifier"),
        [("", gsm.REQUIRED), ("?", gsm.NOT_REQUIRED), ("+", gsm.ONE_OR_MORE), ("*", gsm.ZERO_OR_MORE)],
    )
    def test_quantifier_preserved(self, suffix: str, quantifier: gsm.Quantifier) -> None:
        grammar = raw_grammar(f"wrapper := !inner{suffix} ;\ninner := a:item . b:item ;\n{ITEM_GRAMMAR_TAIL}")
        expanded = gsm.expand_inline_dispositions(grammar)

        assert sole_item(expanded, "wrapper").quantifier is quantifier

    def test_separators_preserved(self) -> None:
        grammar = raw_grammar(
            f"wrapper := x:item . !inner : y:item ;\ninner := , a:item : b:item ;\n{ITEM_GRAMMAR_TAIL}"
        )
        expanded = gsm.expand_inline_dispositions(grammar)

        wrapper_items = expanded.identifiers["wrapper"].alternatives[0]
        # Parent-side separators are untouched: item replacement is positional.
        assert wrapper_items.initial_sep == gsm.Separator.NO_WS
        assert list(wrapper_items.sep_after) == [
            gsm.Separator.NO_WS,
            gsm.Separator.WS_REQUIRED,
            gsm.Separator.NO_WS,
        ]

        inner_alt = spliced_alternatives(wrapper_items.items[1])[0]
        assert inner_alt.initial_sep == gsm.Separator.WS_ALLOWED
        assert list(inner_alt.sep_after) == [gsm.Separator.WS_REQUIRED, gsm.Separator.NO_WS]

    def test_transitive_expansion(self) -> None:
        grammar = raw_grammar(f"a := !b ;\nb := !c ;\nc := x:item ;\n{ITEM_GRAMMAR_TAIL}")
        expanded = gsm.expand_inline_dispositions(grammar)

        a_item = sole_item(expanded, "a")
        b_body = spliced_alternatives(a_item)[0]
        assert len(b_body.items) == 1
        c_body = spliced_alternatives(b_body.items[0])[0]
        assert [i.label for i in c_body.items] == ["x"]

    def test_multiple_alternatives_spliced(self) -> None:
        grammar = raw_grammar(f"wrapper := !inner ;\ninner := a:item | b:item ;\n{ITEM_GRAMMAR_TAIL}")
        expanded = gsm.expand_inline_dispositions(grammar)

        alts = spliced_alternatives(sole_item(expanded, "wrapper"))
        assert [alt.items[0].label for alt in alts] == ["a", "b"]

    def test_inline_inside_sub_expression(self) -> None:
        grammar = raw_grammar(f"wrapper := ( !inner )* ;\ninner := a:item ;\n{ITEM_GRAMMAR_TAIL}")
        expanded = gsm.expand_inline_dispositions(grammar)

        outer = sole_item(expanded, "wrapper")
        inner_item = spliced_alternatives(outer)[0].items[0]
        assert inner_item.disposition == gsm.Disposition.INCLUDE
        assert [i.label for i in spliced_alternatives(inner_item)[0].items] == ["a"]


class TestExpansionInvariants:
    def test_idempotent(self) -> None:
        grammar = raw_grammar(f"wrapper := !inner ;\ninner := a:item . b:item ;\n{ITEM_GRAMMAR_TAIL}")
        once = gsm.expand_inline_dispositions(grammar)
        twice = gsm.expand_inline_dispositions(once)

        assert list(twice.rules) == list(once.rules)

    def test_identifiers_map_rebuilt(self) -> None:
        grammar = raw_grammar(f"wrapper := !inner ;\ninner := a:item . b:item ;\n{ITEM_GRAMMAR_TAIL}")
        expanded = gsm.expand_inline_dispositions(grammar)

        assert set(expanded.identifiers) == {rule.name for rule in expanded.rules}
        for rule in expanded.rules:
            assert expanded.identifiers[rule.name] is rule

    def test_no_items_shared_with_input(self) -> None:
        grammar = raw_grammar(f"wrapper := !inner ;\ninner := a:item . b:item ;\n{ITEM_GRAMMAR_TAIL}")
        expanded = gsm.expand_inline_dispositions(grammar)

        original_ids = {id(items) for items in all_items_objects(grammar)}
        assert not any(id(items) in original_ids for items in all_items_objects(expanded))

    def test_nil_memo_reset(self) -> None:
        grammar = raw_grammar(f"wrapper := !inner ;\ninner := a:item . b:item ;\n{ITEM_GRAMMAR_TAIL}")
        # Prime the memo on the input grammar's objects.
        grammar.identifiers["inner"].can_be_nil(grammar)
        expanded = gsm.expand_inline_dispositions(grammar)

        for rule in expanded.rules:
            assert rule._can_be_nil is None
        for items in all_items_objects(expanded):
            assert items._can_be_nil is None

    def test_grammar_without_inline_is_unchanged_semantically(self) -> None:
        text = f"wrapper := x:item . y:item ;\n{ITEM_GRAMMAR_TAIL}"
        grammar = raw_grammar(text)
        expanded = gsm.expand_inline_dispositions(grammar)

        assert list(expanded.rules) == list(grammar.rules)


class TestExpansionErrors:
    def test_labeled_inline_rejected(self) -> None:
        grammar = raw_grammar(f"wrapper := x:!inner ;\ninner := a:item ;\n{ITEM_GRAMMAR_TAIL}")
        with pytest.raises(ValueError, match=r"wrapper.*label") as exc:
            gsm.expand_inline_dispositions(grammar)
        assert "x" in str(exc.value)

    @pytest.mark.parametrize("term_text", ['!"lit"', "!/[a-z]+/", "!( a:item )"])
    def test_non_identifier_term_rejected(self, term_text: str) -> None:
        grammar = raw_grammar(f"wrapper := {term_text} ;\n{ITEM_GRAMMAR_TAIL}")
        with pytest.raises(ValueError, match="wrapper"):
            gsm.expand_inline_dispositions(grammar)

    def test_unknown_rule_rejected(self) -> None:
        grammar = raw_grammar(f"wrapper := !nope ;\n{ITEM_GRAMMAR_TAIL}")
        with pytest.raises(ValueError, match="nope"):
            gsm.expand_inline_dispositions(grammar)

    def test_trivia_rule_target_rejected(self) -> None:
        grammar = raw_grammar(f"wrapper := !_trivia ;\n_trivia := /\\s+/ ;\n{ITEM_GRAMMAR_TAIL}")
        with pytest.raises(ValueError, match="_trivia"):
            gsm.expand_inline_dispositions(grammar)

    def test_trivia_reachable_target_rejected(self) -> None:
        grammar = raw_grammar(f"wrapper := !ws ;\n_trivia := ws+ ;\nws := /\\s+/ ;\n{ITEM_GRAMMAR_TAIL}")
        with pytest.raises(ValueError, match="ws"):
            gsm.expand_inline_dispositions(grammar)

    def test_inline_inside_trivia_subtree_rejected(self) -> None:
        grammar = raw_grammar(f"wrapper := x:item ;\n_trivia := !ws ;\nws := /\\s+/ ;\n{ITEM_GRAMMAR_TAIL}")
        with pytest.raises(ValueError, match="ws"):
            gsm.expand_inline_dispositions(grammar)

    def test_direct_cycle_rejected(self) -> None:
        grammar = raw_grammar(f"a := !a ;\n{ITEM_GRAMMAR_TAIL}")
        with pytest.raises(ValueError, match="a -> a"):
            gsm.expand_inline_dispositions(grammar)

    def test_mutual_cycle_rejected(self) -> None:
        grammar = raw_grammar(f"a := !b ;\nb := !a ;\n{ITEM_GRAMMAR_TAIL}")
        with pytest.raises(ValueError, match="a -> b -> a"):
            gsm.expand_inline_dispositions(grammar)

    def test_non_inline_recursion_allowed(self) -> None:
        grammar = raw_grammar(f"a := !b ;\nb := x:item . a? ;\n{ITEM_GRAMMAR_TAIL}")
        expanded = gsm.expand_inline_dispositions(grammar)

        body = spliced_alternatives(sole_item(expanded, "a"))[0]
        assert [i.label for i in body.items] == ["x", "a"]


class TestFltk2GsmLabels:
    def test_unlabeled_inline_gets_no_implicit_label(self) -> None:
        grammar = raw_grammar(f"wrapper := !inner ;\ninner := a:item ;\n{ITEM_GRAMMAR_TAIL}")
        item = sole_item(grammar, "wrapper")

        assert item.disposition == gsm.Disposition.INLINE
        assert item.label is None

    def test_explicit_label_on_inline_preserved(self) -> None:
        grammar = raw_grammar(f"wrapper := x:!inner ;\ninner := a:item ;\n{ITEM_GRAMMAR_TAIL}")
        item = sole_item(grammar, "wrapper")

        assert item.disposition == gsm.Disposition.INLINE
        assert item.label == "x"

    def test_unlabeled_non_inline_identifier_still_gets_implicit_label(self) -> None:
        grammar = raw_grammar(f"wrapper := inner ;\ninner := a:item ;\n{ITEM_GRAMMAR_TAIL}")
        item = sole_item(grammar, "wrapper")

        assert item.disposition == gsm.Disposition.INCLUDE
        assert item.label == "inner"


class TestParseBoundariesExpand:
    """Every text->GSM boundary hands its consumers a grammar with no INLINE items left."""

    GRAMMAR = f"wrapper := !inner ;\ninner := a:item . b:item ;\n{ITEM_GRAMMAR_TAIL}"

    def test_plumbing_parse_grammar(self) -> None:
        grammar = parse_grammar(self.GRAMMAR)

        assert all(item.disposition != gsm.Disposition.INLINE for item in all_items(grammar))

    def test_genunparser_parse_grammar_file(self, tmp_path: pathlib.Path) -> None:
        """The standalone unparser-generation path has its own boundary."""
        grammar_path = tmp_path / "inline.fltkg"
        grammar_path.write_text(self.GRAMMAR)

        grammar, _text = genunparser.parse_grammar_file(grammar_path)

        assert all(item.disposition != gsm.Disposition.INLINE for item in all_items(grammar))
        assert [i.label for i in spliced_alternatives(sole_item(grammar, "wrapper"))[0].items] == ["a", "b"]


def rule_models(grammar_text: str) -> dict[str, gsm2tree.ItemsModel]:
    """Build the CST model map for a grammar, applying the standard pipeline."""
    grammar = parse_grammar(grammar_text)
    context = create_default_context()
    grammar = gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(grammar, context))
    cstgen = gsm2tree.CstGenerator(grammar=grammar, py_module=pyreg.Builtins, context=context)
    return cstgen.rule_models


class TestModelEquivalence:
    """An inlined rule yields the same ItemsModel as the hand-written sub-expression."""

    def test_no_whitespace_separators(self) -> None:
        inline = rule_models(f"wrapper := !inner ;\ninner := a:item . b:item ;\n{ITEM_GRAMMAR_TAIL}")
        subexpr = rule_models(f"wrapper := ( a:item . b:item ) ;\n{ITEM_GRAMMAR_TAIL}")

        assert inline["wrapper"] == subexpr["wrapper"]
        assert "_trivia" not in inline["wrapper"].types

    def test_whitespace_separators_inject_trivia(self) -> None:
        inline = rule_models(f"wrapper := !inner ;\ninner := a:item , b:item ;\n{ITEM_GRAMMAR_TAIL}")
        subexpr = rule_models(f"wrapper := ( a:item , b:item ) ;\n{ITEM_GRAMMAR_TAIL}")

        assert inline["wrapper"] == subexpr["wrapper"]
        assert "_trivia" in inline["wrapper"].types


class TestGeneratorGuards:
    """Programmatically constructed INLINE grammars must fail loudly, never misparse."""

    @staticmethod
    def inline_grammar() -> gsm.Grammar:
        child = gsm.Rule(
            name="child",
            alternatives=[
                gsm.Items(
                    items=[
                        gsm.Item(
                            label="v",
                            disposition=gsm.Disposition.INCLUDE,
                            term=gsm.Regex(r"[a-z]+"),
                            quantifier=gsm.REQUIRED,
                        )
                    ],
                    sep_after=[gsm.Separator.NO_WS],
                )
            ],
        )
        parent = gsm.Rule(
            name="parent",
            alternatives=[
                gsm.Items(
                    items=[
                        gsm.Item(
                            label=None,
                            disposition=gsm.Disposition.INLINE,
                            term=gsm.Identifier("child"),
                            quantifier=gsm.REQUIRED,
                        )
                    ],
                    sep_after=[gsm.Separator.NO_WS],
                )
            ],
        )
        return gsm.Grammar(rules=[parent, child], identifiers={"parent": parent, "child": child})

    def test_cst_generator_rejects_inline(self) -> None:
        grammar = self.inline_grammar()
        with pytest.raises(ValueError, match="expand_inline_dispositions"):
            gsm2tree.CstGenerator(grammar=grammar, py_module=pyreg.Builtins, context=create_default_context())

    def test_generate_parser_rejects_inline(self) -> None:
        with pytest.raises(ValueError, match="expand_inline_dispositions"):
            generate_parser(self.inline_grammar())

    def test_expansion_makes_it_generatable(self) -> None:
        expanded = gsm.expand_inline_dispositions(self.inline_grammar())
        result = generate_parser(expanded)

        assert result.parser_class is not None


DOC_GRAMMAR = f"wrapper := !inner ;\ninner := a:item . ',' . b:item ;\n{ITEM_GRAMMAR_TAIL}"
WS_GRAMMAR = f"wrapper := !inner ;\ninner := a:item , b:item ;\n{ITEM_GRAMMAR_TAIL}"


class TestEndToEndPython:
    def test_documented_splice_shape(self) -> None:
        grammar = parse_grammar(DOC_GRAMMAR)
        parser_result = generate_parser(grammar, capture_trivia=False)
        parse_result = parse_text(parser_result, "a,b", "wrapper")
        assert parse_result.success, parse_result.error_message

        node = parse_result.cst
        assert node is not None
        wrapper_cls = parser_result.cst_module.Wrapper
        item_cls = parser_result.cst_module.Item
        assert type(node) is wrapper_cls
        assert [label for label, _ in node.children] == [wrapper_cls.Label.A, wrapper_cls.Label.B]
        assert all(type(child) is item_cls for _, child in node.children)
        assert node.child_a().child_name().text() == "a"
        assert node.child_b().child_name().text() == "b"

    def test_dual_use_rule_splices_only_at_the_marked_site(self) -> None:
        """`!inner` splices; an ordinary `inner` reference in the same rule still builds a node."""
        grammar = parse_grammar(
            f"wrapper := !inner . ';' . inner ;\ninner := a:item . ',' . b:item ;\n{ITEM_GRAMMAR_TAIL}"
        )
        parser_result = generate_parser(grammar, capture_trivia=False)
        parse_result = parse_text(parser_result, "a,b;c,d", "wrapper")
        assert parse_result.success, parse_result.error_message

        node = parse_result.cst
        assert node is not None
        wrapper_cls = parser_result.cst_module.Wrapper
        inner_cls = parser_result.cst_module.Inner
        assert [label for label, _ in node.children] == [
            wrapper_cls.Label.A,
            wrapper_cls.Label.B,
            wrapper_cls.Label.INNER,
        ]
        assert type(node.child_inner()) is inner_cls
        assert node.child_a().child_name().text() == "a"
        assert node.child_inner().child_a().child_name().text() == "c"

    def test_quantified_inline_repeats(self) -> None:
        grammar = parse_grammar(f"wrapper := !inner* ;\ninner := a:item . ';' ;\n{ITEM_GRAMMAR_TAIL}")
        parser_result = generate_parser(grammar, capture_trivia=False)
        parse_result = parse_text(parser_result, "x;y;z;", "wrapper")
        assert parse_result.success, parse_result.error_message

        node = parse_result.cst
        assert node is not None
        wrapper_cls = parser_result.cst_module.Wrapper
        labels = [label for label, _ in node.children]
        assert labels == [wrapper_cls.Label.A] * 3

    def test_trivia_children_attach_to_parent(self) -> None:
        grammar = parse_grammar(WS_GRAMMAR)
        parser_result = generate_parser(grammar, capture_trivia=True)
        parse_result = parse_text(parser_result, "a b", "wrapper")
        assert parse_result.success, parse_result.error_message

        node = parse_result.cst
        assert node is not None
        wrapper_cls = parser_result.cst_module.Wrapper
        labels = [label for label, _ in node.children]
        assert labels == [wrapper_cls.Label.A, None, wrapper_cls.Label.B]

    @staticmethod
    def unparse(grammar_text: str, source: str) -> str:
        grammar = parse_grammar(grammar_text)
        parser_result = generate_parser(grammar, capture_trivia=True)
        parse_result = parse_text(parser_result, source, "wrapper")
        assert parse_result.success, parse_result.error_message

        unparser_result = generate_unparser(parser_result.grammar, parser_result.cst_module_name)
        doc = unparse_cst(unparser_result, parse_result.cst, source, "wrapper")
        return render_doc(doc)

    def test_unparse_round_trip(self) -> None:
        assert self.unparse(DOC_GRAMMAR, "a,b") == "a,b"

    def test_unparse_matches_sub_expression_form(self) -> None:
        """Whitespace-separated inline content unparses exactly like the hand-written form."""
        sub_expression = f"wrapper := ( a:item , b:item ) ;\n{ITEM_GRAMMAR_TAIL}"

        assert self.unparse(WS_GRAMMAR, "a b") == self.unparse(sub_expression, "a b")


class TestFormatterConfigAtSpliceSite:
    """Inlined content lives in the parent node, so the parent rule's config governs it."""

    GRAMMAR = f"wrapper := !inner , inner ;\ninner := a:item , b:item ;\n{ITEM_GRAMMAR_TAIL}"
    CONFIG = "rule wrapper { ws_allowed: hard; }\nrule inner { ws_allowed: nil; }\n"
    SOURCE = "a b c d"

    def render(self) -> str:
        grammar = parse_grammar(self.GRAMMAR)
        parser_result = generate_parser(grammar, capture_trivia=True)
        parse_result = parse_text(parser_result, self.SOURCE, "wrapper")
        assert parse_result.success, parse_result.error_message

        unparser_result = generate_unparser(
            parser_result.grammar,
            parser_result.cst_module_name,
            formatter_config=parse_format_config(self.CONFIG),
        )
        return render_doc(unparse_cst(unparser_result, parse_result.cst, self.SOURCE, "wrapper"))

    def test_parent_config_governs_spliced_items(self) -> None:
        """`rule wrapper`'s hard line wins at the `!inner` site; `rule inner`'s nil does not."""
        assert self.render().startswith("a\nb")

    def test_inner_config_still_governs_an_ordinary_reference(self) -> None:
        """The same rule referenced normally keeps its own config: `rule inner`'s nil applies."""
        assert self.render().endswith("cd")


class TestLspIndexSeesSplicedSurface:
    def test_inlined_labels_indexed_under_parent(self) -> None:
        grammar = parse_grammar(DOC_GRAMMAR)
        index = build_grammar_index(grammar)

        assert "a" in index.rules["wrapper"].labels
        assert "b" in index.rules["wrapper"].labels


def test_analysis_grammar_rejects_programmatic_inline() -> None:
    """`prepare_analysis_grammar` stays a defensive guard for programmatic callers."""
    with pytest.raises(ValueError, match="inline"):
        prepare_analysis_grammar(TestGeneratorGuards.inline_grammar())


def test_expansion_preserves_frozen_dataclass_contract() -> None:
    """Rebuilt objects are still frozen dataclasses of the same types."""
    grammar = raw_grammar(f"wrapper := !inner ;\ninner := a:item ;\n{ITEM_GRAMMAR_TAIL}")
    expanded = gsm.expand_inline_dispositions(grammar)

    for rule in expanded.rules:
        assert dataclasses.is_dataclass(rule)
        with pytest.raises(dataclasses.FrozenInstanceError):
            rule.name = "nope"  # type: ignore[misc]
