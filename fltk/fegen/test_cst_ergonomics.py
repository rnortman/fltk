"""Tests for label arity analysis and ergonomic-member planning."""

from __future__ import annotations

import logging
import pathlib

import pytest

from fltk.fegen import cst_ergonomics as ce
from fltk.fegen import gsm, gsm2tree
from fltk.iir.context import create_default_context
from fltk.iir.py import reg as pyreg
from fltk.plumbing import parse_grammar, parse_grammar_file

ITEM_TAIL = "item := name:/[a-z]+/ ;\n"

_FLTK_ROOT = pathlib.Path(__file__).parents[1]
IN_TREE_GRAMMARS = [
    _FLTK_ROOT / "fegen" / "fegen.fltkg",
    _FLTK_ROOT / "lsp" / "fltklsp.fltkg",
    _FLTK_ROOT / "unparse" / "unparsefmt.fltkg",
]


def grammar_for(body: str, extra_rules: str = "") -> gsm.Grammar:
    return parse_grammar(f"target := {body} ;\n{extra_rules}{ITEM_TAIL}")


def arities(body: str, extra_rules: str = "") -> dict[str, tuple[int, int]]:
    rule = grammar_for(body, extra_rules).identifiers["target"]
    return {label: (count.min, count.max) for label, count in ce.compute_label_arities(rule).items()}


def plan_for(body: str, extra_rules: str = "", rule_name: str = "target") -> ce.RulePlan:
    grammar = grammar_for(body, extra_rules)
    context = create_default_context()
    grammar = gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(grammar, context))
    cstgen = gsm2tree.CstGenerator(grammar=grammar, py_module=pyreg.Builtins, context=context)
    return ce.plan_rule(grammar.identifiers[rule_name], cstgen.rule_models[rule_name])


def skipped_by_name(plan: ce.RulePlan) -> dict[str, ce.SkippedMember]:
    return {member.name: member for member in plan.skipped}


def emitted_member_names(plan: ce.RulePlan) -> set[str]:
    names = set(plan.bare_accessors) | {f"{label}_text" for label in plan.text_accessors}
    if plan.rule_text:
        names.add("text")
    if plan.variant:
        names.add("variant")
    return names


def assert_plan_is_consistent(model: gsm2tree.ItemsModel, plan: ce.RulePlan) -> None:
    """Invariants every plan must satisfy, whatever the grammar."""
    labels = set(model.labels)
    assert set(plan.bare_accessors) <= labels
    assert set(plan.text_accessors) <= labels
    assert {member.label for member in plan.skipped} <= labels

    quintet = {name for label in labels for name in ce.quintet_member_names(label)}
    emitted = emitted_member_names(plan)
    assert not emitted & quintet
    # The rule-level members own their reserved names; nothing else may take a reserved name.
    assert not (emitted - ce.RULE_MEMBER_NAMES) & ce.RESERVED_MEMBER_NAMES
    assert not emitted & {member.name for member in plan.skipped}


class TestLabelCount:
    @pytest.mark.parametrize(
        ("count", "expected"),
        [
            (ce.LabelCount(min=1, max=1), ce.ArityClass.REQUIRED_SINGLE),
            (ce.LabelCount(min=0, max=1), ce.ArityClass.OPTIONAL_SINGLE),
            (ce.LabelCount(min=0, max=2), ce.ArityClass.COLLECTION),
            (ce.LabelCount(min=1, max=2), ce.ArityClass.COLLECTION),
            (ce.LabelCount(min=2, max=2), ce.ArityClass.COLLECTION),
        ],
    )
    def test_arity_class(self, count: ce.LabelCount, expected: ce.ArityClass) -> None:
        assert count.arity_class is expected

    def test_of_saturates_both_bounds(self) -> None:
        assert ce.LabelCount.of(7, 9) == ce.LabelCount(min=2, max=2)

    def test_of_leaves_small_counts_alone(self) -> None:
        assert ce.LabelCount.of(0, 1) == ce.LabelCount(min=0, max=1)


class TestComputeLabelArities:
    @pytest.mark.parametrize(
        ("body", "expected"),
        [
            # Quantifiers on a single labeled item.
            ("x:item", {"x": (1, 1)}),
            ("x:item?", {"x": (0, 1)}),
            ("x:item+", {"x": (1, 2)}),
            ("x:item*", {"x": (0, 2)}),
            # Terms other than rule references carry labels the same way.
            ('x:"lit"', {"x": (1, 1)}),
            ("x:/[a-z]+/", {"x": (1, 1)}),
            # An unlabeled rule reference is auto-labeled with the rule name.
            ("item", {"item": (1, 1)}),
            # Sequence combination within one alternative.
            ("x:item . y:item", {"x": (1, 1), "y": (1, 1)}),
            ("x:item . x:item", {"x": (2, 2)}),
            ("x:item . x:item?", {"x": (1, 2)}),
            # Alternative combination across the rule's alternatives.
            ("x:item | y:item", {"x": (0, 1), "y": (0, 1)}),
            ("x:item | x:item", {"x": (1, 1)}),
            ("x:item . y:item | x:item", {"x": (1, 1), "y": (0, 1)}),
            # Sub-expressions: inner labels are contributed to the parent, quantifiers compose.
            ("x:item . ( y:item )?", {"x": (1, 1), "y": (0, 1)}),
            ("( a:item . b:item+ )*", {"a": (0, 2), "b": (0, 2)}),
            ("( x:item? )+", {"x": (0, 2)}),
            ("( a:item | b:item )", {"a": (0, 1), "b": (0, 1)}),
            ("( a:item | b:item )+", {"a": (0, 2), "b": (0, 2)}),
            # Suppressed items contribute nothing.
            ("%item . x:item", {"x": (1, 1)}),
            ('%"lit" . x:item', {"x": (1, 1)}),
        ],
    )
    def test_arities(self, body: str, expected: dict[str, tuple[int, int]]) -> None:
        assert arities(body) == expected

    def test_rule_reference_does_not_expose_referee_labels(self) -> None:
        """A rule-reference item contributes its own label only."""
        assert arities("x:inner", extra_rules="inner := deep:item ;\n") == {"x": (1, 1)}

    def test_twice_required_label_is_a_collection(self) -> None:
        rule = grammar_for("x:item . x:item").identifiers["target"]
        assert ce.compute_label_arities(rule)["x"].arity_class is ce.ArityClass.COLLECTION

    def test_labels_from_expanded_inline_rule(self) -> None:
        """The parse boundary expands `!`, so inlined labels are the parent's labels."""
        grammar = parse_grammar(f"wrapper := !inner ;\ninner := a:item , b:item ;\n{ITEM_TAIL}")
        rule = grammar.identifiers["wrapper"]

        assert {label: (c.min, c.max) for label, c in ce.compute_label_arities(rule).items()} == {
            "a": (1, 1),
            "b": (1, 1),
        }

    def test_quantified_inline_composes_like_a_sub_expression(self) -> None:
        grammar = parse_grammar(f"wrapper := !inner* ;\ninner := a:item . ';' ;\n{ITEM_TAIL}")
        rule = grammar.identifiers["wrapper"]

        assert ce.compute_label_arities(rule)["a"] == ce.LabelCount(min=0, max=2)


class TestComputeLabelAritiesErrors:
    @staticmethod
    def inline_rule() -> gsm.Rule:
        return gsm.Rule(
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

    def test_inline_item_rejected(self) -> None:
        with pytest.raises(ValueError, match="expand_inline_dispositions") as exc:
            ce.compute_label_arities(self.inline_rule())
        assert "parent" in str(exc.value)

    def test_labeled_sub_expression_rejected(self) -> None:
        rule = grammar_for("x:( a:item . b:item )").identifiers["target"]
        with pytest.raises(ValueError, match=r"Label 'x'.*sub-expression") as exc:
            ce.compute_label_arities(rule)
        assert "target" in str(exc.value)

    def test_unsupported_term_rejected(self) -> None:
        rule = gsm.Rule(
            name="odd",
            alternatives=[
                gsm.Items(
                    items=[
                        gsm.Item(
                            label="x",
                            disposition=gsm.Disposition.INCLUDE,
                            term=None,  # type: ignore[arg-type]
                            quantifier=gsm.REQUIRED,
                        )
                    ],
                    sep_after=[gsm.Separator.NO_WS],
                )
            ],
        )
        with pytest.raises(ValueError, match="Unsupported term type"):
            ce.compute_label_arities(rule)


class TestNameHelpers:
    def test_quintet_member_names(self) -> None:
        assert ce.quintet_member_names("foo") == (
            "append_foo",
            "extend_foo",
            "children_foo",
            "child_foo",
            "maybe_foo",
        )

    @pytest.mark.parametrize(("name", "expected"), [("type", "r#type"), ("match", "r#match"), ("value", "value")])
    def test_rust_method_ident(self, name: str, expected: str) -> None:
        assert ce.rust_method_ident(name) == expected

    def test_rule_members_are_reserved(self) -> None:
        assert ce.RULE_MEMBER_NAMES <= ce.RESERVED_MEMBER_NAMES

    def test_reserved_covers_both_backends(self) -> None:
        # A sample from each fixed-member family the planner must protect.
        assert {"children", "span", "clear", "push_child", "shared", "to_py_canonical"} <= ce.RESERVED_MEMBER_NAMES

    def test_unrawable_keywords_are_not_in_rawable_set(self) -> None:
        assert not (ce.RUST_UNRAWABLE_KEYWORDS & ce.RUST_KEYWORDS)


class TestBareAccessorPlanning:
    @pytest.mark.parametrize(
        ("body", "expected"),
        [
            ("x:item", ce.ArityClass.REQUIRED_SINGLE),
            ("x:item?", ce.ArityClass.OPTIONAL_SINGLE),
            ("x:item*", ce.ArityClass.COLLECTION),
            ("x:item+", ce.ArityClass.COLLECTION),
            ("x:item . x:item", ce.ArityClass.COLLECTION),
        ],
    )
    def test_arity_class_recorded(self, body: str, expected: ce.ArityClass) -> None:
        assert plan_for(body).bare_accessors == {"x": expected}

    def test_label_free_rule_gets_no_bare_accessors(self) -> None:
        plan = plan_for('%"a" . /[a-z]+/')
        assert plan.bare_accessors == {}
        assert plan.skipped == []


class TestTextAccessorPlanning:
    def test_span_only_label_gets_text_accessor(self) -> None:
        plan = plan_for("a:/[a-z]+/ . b:item")
        assert plan.text_accessors == {"a": ce.ArityClass.REQUIRED_SINGLE}

    def test_optional_span_label_gets_text_accessor(self) -> None:
        assert plan_for("a:/[a-z]+/?").text_accessors == {"a": ce.ArityClass.OPTIONAL_SINGLE}

    def test_collection_span_label_gets_no_text_accessor(self) -> None:
        plan = plan_for("a:/[a-z]+/*")
        assert plan.bare_accessors == {"a": ce.ArityClass.COLLECTION}
        assert plan.text_accessors == {}

    def test_node_typed_label_gets_no_text_accessor(self) -> None:
        assert plan_for("b:item").text_accessors == {}

    def test_mixed_type_label_gets_no_text_accessor(self) -> None:
        """A label carrying both a Span and a node across alternatives is not span-only."""
        plan = plan_for("a:/[a-z]+/ | a:item")
        assert plan.bare_accessors == {"a": ce.ArityClass.REQUIRED_SINGLE}
        assert plan.text_accessors == {}


class TestRuleTextPlanning:
    @pytest.mark.parametrize(
        ("body", "expected"),
        [
            ('a:"x" . b:"y"', True),
            ("a:/[a-z]+/", True),
            # Whitespace separators inject a _trivia child type, which must not disqualify.
            ('a:"x" , b:"y"', True),
            ("a:item", False),
            ("a:/[a-z]+/ . b:item", False),
        ],
    )
    def test_rule_text_predicate(self, body: str, *, expected: bool) -> None:
        assert plan_for(body).rule_text is expected


class TestVariantPlanning:
    @pytest.mark.parametrize(
        ("body", "expected"),
        [
            ("a:item | b:item", True),
            # Unlabeled rule references are auto-labeled, so dispatch rules qualify.
            ("item | other", True),
            # Single alternative: nothing to discriminate.
            ("a:item", False),
            # Quantified item: the node may have zero or many labeled children.
            ("a:item? | b:item", False),
            ("a:item* | b:item", False),
            # More than one item in an alternative.
            ("a:item . b:item | c:item", False),
            # Suppressed item: no labeled child at all in that alternative.
            ('%"x" | b:item', False),
        ],
    )
    def test_variant_predicate(self, body: str, *, expected: bool) -> None:
        assert plan_for(body, extra_rules="other := o:/[a-z]+/ ;\n").variant is expected

    def test_shared_label_across_alternatives_still_qualifies(self) -> None:
        """`variant()` is uninformative here but harmless; no special-casing."""
        assert plan_for("v:item | v:other", extra_rules="other := o:/[a-z]+/ ;\n").variant is True


class TestCollisionPolicy:
    def test_reserved_rule_member_beats_label(self) -> None:
        plan = plan_for("text:/[a-z]+/")

        assert "text" not in plan.bare_accessors
        assert plan.text_accessors == {"text": ce.ArityClass.REQUIRED_SINGLE}
        assert plan.rule_text is True
        assert "already taken" in skipped_by_name(plan)["text"].reason

    def test_reserved_text_leaves_no_text_member_at_all(self) -> None:
        """`text` is reserved even for rules that get no rule-level text()."""
        plan = plan_for("text:item . x:item")

        assert plan.bare_accessors == {"x": ce.ArityClass.REQUIRED_SINGLE}
        assert plan.text_accessors == {}
        assert plan.rule_text is False
        assert "already taken" in skipped_by_name(plan)["text"].reason
        assert emitted_member_names(plan) == {"x"}

    def test_reserved_fixed_member_beats_label(self) -> None:
        plan = plan_for("children:item")

        assert plan.bare_accessors == {}
        skipped = skipped_by_name(plan)["children"]
        assert skipped.kind is ce.MemberKind.BARE_ACCESSOR
        assert "already taken" in skipped.reason

    def test_rust_trait_method_label_skipped(self) -> None:
        """`clone` is callable on every generated Rust struct via the `Clone` derive.

        An inherent `fn clone(&self) -> &NameChild` would take precedence over `Clone::clone`
        at every downstream call site, so the label loses the bare accessor.
        """
        plan = plan_for("clone:item")

        assert plan.bare_accessors == {}
        assert "already taken" in skipped_by_name(plan)["clone"].reason

    @pytest.mark.parametrize("label", ["into", "borrow", "to_owned", "eq", "hash", "fmt", "type_id"])
    def test_rust_trait_methods_are_reserved(self, label: str) -> None:
        plan = plan_for(f"{label}:item")

        assert plan.bare_accessors == {}
        assert skipped_by_name(plan)[label].kind is ce.MemberKind.BARE_ACCESSOR

    def test_python_keyword_label_skipped(self) -> None:
        plan = plan_for("class:item")

        assert plan.bare_accessors == {}
        assert "Python keyword" in skipped_by_name(plan)["class"].reason

    @pytest.mark.parametrize("label", ["self", "crate", "super"])
    def test_unrawable_rust_keyword_label_skipped(self, label: str) -> None:
        plan = plan_for(f"{label}:item")

        assert plan.bare_accessors == {}
        assert "raw identifier" in skipped_by_name(plan)[label].reason

    def test_rawable_rust_keyword_label_emitted(self) -> None:
        plan = plan_for("type:item")

        assert plan.bare_accessors == {"type": ce.ArityClass.REQUIRED_SINGLE}
        assert plan.skipped == []

    def test_dunder_label_skips_both_members(self) -> None:
        plan = plan_for("__eq__:/[a-z]+/")

        assert plan.bare_accessors == {}
        assert plan.text_accessors == {}
        skipped = skipped_by_name(plan)
        assert set(skipped) == {"__eq__", "__eq___text"}
        assert all("mangling" in member.reason for member in skipped.values())

    def test_mangling_prone_label_skipped(self) -> None:
        plan = plan_for("__foo:item")

        assert plan.bare_accessors == {}
        assert "mangling" in skipped_by_name(plan)["__foo"].reason

    def test_quintet_of_another_label_wins(self) -> None:
        plan = plan_for("append_x:item . x:item")

        assert plan.bare_accessors == {"x": ce.ArityClass.REQUIRED_SINGLE}
        assert "append_x() accessor for label 'x'" in skipped_by_name(plan)["append_x"].reason

    def test_quintet_wins_regardless_of_label_order(self) -> None:
        """The full quintet name set is claimed up front, so sorted order cannot flip the winner."""
        plan = plan_for("x:item . append_x:item")

        assert plan.bare_accessors == {"x": ce.ArityClass.REQUIRED_SINGLE}
        assert list(skipped_by_name(plan)) == ["append_x"]

    def test_derived_text_name_collides_with_another_label(self) -> None:
        """Claim order is sorted by label, so `a`'s derived text accessor wins over label `a_text`."""
        plan = plan_for("a:/[a-z]+/ . a_text:item")

        assert plan.bare_accessors == {"a": ce.ArityClass.REQUIRED_SINGLE}
        assert plan.text_accessors == {"a": ce.ArityClass.REQUIRED_SINGLE}
        assert "already taken by the a_text() accessor" in skipped_by_name(plan)["a_text"].reason

    def test_collision_never_raises(self) -> None:
        """Every collision class at once still produces a plan."""
        plan = plan_for("text:/[a-z]+/ . children:item . class:item . self:item . __eq__:item")

        assert plan.bare_accessors == {}
        assert len(plan.skipped) == 5

    def test_plan_is_deterministic(self) -> None:
        body = "text:/[a-z]+/ . append_x:item . x:item . type:item"
        first = plan_for(body)
        second = plan_for(body)

        assert first == second
        assert list(first.bare_accessors) == sorted(first.bare_accessors)

    def test_reserved_name_skips_are_logged_at_info(self, caplog: pytest.LogCaptureFixture) -> None:
        """A label shadowing a fixed member is routine: reported, but not as a warning."""
        with caplog.at_level(logging.INFO, logger=ce.__name__):
            plan_for("children:item")

        records = [record for record in caplog.records if "children" in record.getMessage()]
        assert records
        assert {record.levelno for record in records} == {logging.INFO}
        assert all("target" in record.getMessage() for record in records)

    def test_surprising_skips_are_logged_at_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """A cross-label quintet collision is not something the grammar author expects."""
        with caplog.at_level(logging.INFO, logger=ce.__name__):
            plan_for("append_x:item . x:item")

        records = [record for record in caplog.records if "append_x" in record.getMessage()]
        assert records
        assert {record.levelno for record in records} == {logging.WARNING}


class TestInTreeGrammars:
    """Planning must succeed, and stay self-consistent, on every real grammar in the tree."""

    @pytest.mark.parametrize("grammar_path", IN_TREE_GRAMMARS, ids=lambda path: path.name)
    def test_every_rule_plans_consistently(self, grammar_path: pathlib.Path) -> None:
        grammar = parse_grammar_file(grammar_path)
        context = create_default_context()
        grammar = gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(grammar, context))
        cstgen = gsm2tree.CstGenerator(grammar=grammar, py_module=pyreg.Builtins, context=context)

        for rule in grammar.rules:
            model = cstgen.rule_models[rule.name]
            assert_plan_is_consistent(model, ce.plan_rule(rule, model))


class TestPlanRuleConsistency:
    def test_synthetic_collision_grammar_is_consistent(self) -> None:
        body = "text:/[a-z]+/ . children:item . append_x:item . x:item . type:item . a_text:item"
        grammar = grammar_for(body)
        context = create_default_context()
        grammar = gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(grammar, context))
        cstgen = gsm2tree.CstGenerator(grammar=grammar, py_module=pyreg.Builtins, context=context)
        model = cstgen.rule_models["target"]

        assert_plan_is_consistent(model, ce.plan_rule(grammar.identifiers["target"], model))

    def test_model_label_without_arity_is_an_error(self) -> None:
        grammar = grammar_for("x:item")
        rule = grammar.identifiers["target"]
        model = gsm2tree.ItemsModel()
        model.labels["x"] = {"item"}
        model.labels["ghost"] = {"item"}
        model.types = {"item"}

        with pytest.raises(ValueError, match="ghost"):
            ce.plan_rule(rule, model)
