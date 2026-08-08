"""Tests for the backend-neutral AST model."""

from __future__ import annotations

import ast
import math
import pathlib
import re

import pytest

from fltk.fegen import ast_config as ac
from fltk.fegen import ast_model as am
from fltk.fegen import ast_test_grammars as fixtures
from fltk.fegen import cst_ergonomics as ce
from fltk.fegen import grammar_shape as gshape
from fltk.fegen import gsm, gsm2ast, gsm2ast_rs
from fltk.fegen.ast_test_grammars import FOLD_GRAMMAR, FOLD_SIDECAR
from fltk.plumbing import parse_grammar, parse_grammar_file

_FLTK_ROOT = pathlib.Path(__file__).parents[1]
IN_TREE_GRAMMARS = [
    _FLTK_ROOT / "fegen" / "fegen.fltkg",
    _FLTK_ROOT / "lsp" / "fltklsp.fltkg",
    _FLTK_ROOT / "unparse" / "unparsefmt.fltkg",
]

# The subset that needs no sidecar annotations to model cleanly; the remaining one carries a
# rule that Tier 0 rejects by design (see TestInTreeGrammars).
TIER0_CLEAN_GRAMMARS = [_FLTK_ROOT / "fegen" / "fegen.fltkg", _FLTK_ROOT / "lsp" / "fltklsp.fltkg"]

ITEM_TAIL = "item := name:/[a-z]+/ ;\nother := oname:/[0-9]+/ ;\n"


def pipeline(grammar: gsm.Grammar) -> gsm.Grammar:
    return fixtures.classify(grammar)


def model_for_text(text: str) -> am.AstModel:
    return am.build_ast_model(pipeline(parse_grammar(text)))


def model_for(body: str, extra_rules: str = "") -> am.AstModel:
    return model_for_text(f"target := {body} ;\n{extra_rules}{ITEM_TAIL}")


def node_for(body: str, extra_rules: str = "") -> am.RuleNode:
    return model_for(body, extra_rules).nodes["target"]


def errors_for(body: str, extra_rules: str = "") -> tuple[str, ...]:
    with pytest.raises(am.AstModelError) as exc:
        model_for(body, extra_rules)
    return exc.value.errors


def configured_model(text: str, config_text: str) -> am.AstModel:
    """Build a model for ``text`` shaped by the ``.fltkast`` sidecar ``config_text``."""
    grammar = pipeline(parse_grammar(text))
    return am.build_ast_model(grammar, ac.load_ast_config(config_text, grammar, {ac.Backend.PYTHON}))


def configured(body: str, config_text: str, extra_rules: str = "") -> am.AstModel:
    return configured_model(f"target := {body} ;\n{extra_rules}{ITEM_TAIL}", config_text)


def configured_errors(body: str, config_text: str, extra_rules: str = "") -> tuple[str, ...]:
    with pytest.raises(am.AstModelError) as exc:
        configured(body, config_text, extra_rules)
    return exc.value.errors


def payload_name(variant: am.SumVariant) -> str:
    """The name of a sum variant's payload type, which the tests below all expect generated."""
    assert isinstance(variant.payload, am.NodeType)
    return variant.payload.name


def fields_by_name(node: am.RuleNode) -> dict[str, am.FieldType]:
    assert isinstance(node, am.ProductNode)
    return {field.name: field.type for field in node.fields}


class TestAritiesForAlternative:
    """The per-alternative view keeps what ``compute_label_arities`` folds away."""

    @staticmethod
    def per_alternative(body: str) -> list[dict[str, tuple[int, int]]]:
        rule = parse_grammar(f"target := {body} ;\n{ITEM_TAIL}").identifiers["target"]
        return [
            {label: (count.min, count.max) for label, count in ce.arities_for_alternative(alt, "target").items()}
            for alt in rule.alternatives
        ]

    def test_alternatives_are_not_combined(self) -> None:
        assert self.per_alternative("x:item | y:item") == [{"x": (1, 1)}, {"y": (1, 1)}]

    def test_sub_expression_labels_compose(self) -> None:
        assert self.per_alternative("x:item . ( y:item )?") == [{"x": (1, 1), "y": (0, 1)}]

    def test_dotted_name_repetition_is_a_collection(self) -> None:
        assert self.per_alternative('part:item . ( "." . part:item )*') == [{"part": (1, 2)}]

    def test_suppressed_items_contribute_nothing(self) -> None:
        assert self.per_alternative("%item . x:item") == [{"x": (1, 1)}]

    def test_inline_item_still_rejected(self) -> None:
        rule = gsm.Rule(
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
        with pytest.raises(ValueError, match="expand_inline_dispositions"):
            ce.arities_for_alternative(rule.alternatives[0], "parent")


class TestClassification:
    def test_single_alternative_rule_is_a_product(self) -> None:
        node = node_for("x:item , y:item")
        assert isinstance(node, am.ProductNode)
        assert node.name == "Target"
        assert node.merged is False

    def test_terminal_only_rule(self) -> None:
        node = node_for('a:"x" . b:/[0-9]+/')
        assert isinstance(node, am.TerminalNode)

    def test_rule_referencing_another_rule_is_not_terminal_only(self) -> None:
        assert isinstance(node_for("a:/[0-9]+/ . b:item"), am.ProductNode)

    def test_suppressed_rule_reference_still_disqualifies_terminal_only(self) -> None:
        """A suppressed reference means the node's text is not a pure lexeme of terminals."""
        assert not isinstance(node_for("a:/[0-9]+/ . %item"), am.TerminalNode)

    def test_a_literal_only_rule_is_a_marker_product(self) -> None:
        """No regex means no text of its own, so the node carries a span and nothing else."""
        node = node_for('"open" , "close"')
        assert isinstance(node, am.ProductNode)
        assert node.fields == ()

    def test_a_literal_only_rule_ignores_the_terminal_separator_constraint(self) -> None:
        """The constraint exists to keep a ``text`` field free of formatting; there is no text."""
        assert isinstance(node_for('"namespace" , ";" ,'), am.ProductNode)

    def test_a_labeled_literal_only_rule_is_a_product_of_positions(self) -> None:
        node = node_for('a:"x" . b:"y"')
        assert isinstance(node, am.ProductNode)
        assert fields_by_name(node) == {
            "a": am.FieldType(am.SPAN, am.Container.SINGLE),
            "b": am.FieldType(am.SPAN, am.Container.SINGLE),
        }

    def test_a_regex_inside_a_sub_expression_is_enough_to_be_terminal_only(self) -> None:
        """The regex search recurses, so a nested one still gives the node a ``text``."""
        assert isinstance(node_for('a:"x" . ( b:/[0-9]+/ )'), am.TerminalNode)

    def test_a_regex_in_only_one_branch_of_a_nested_alternation_is_enough(self) -> None:
        assert isinstance(node_for('a:"x" . ( b:"y" | b:/[0-9]+/ )'), am.TerminalNode)

    def test_deeply_nested_literals_stay_a_product(self) -> None:
        """No regex at any depth means no text of its own, however the literals nest."""
        assert isinstance(node_for('a:"x" . ( ( b:"y" ) )'), am.ProductNode)

    def test_enum_shaped_rule_beats_terminal_only(self) -> None:
        node = node_for('counter:"counter" | gauge:"gauge" | histogram:"histogram"')
        assert isinstance(node, am.EnumNode)
        assert node.value_enum.name == "TargetValue"
        assert [variant.name for variant in node.value_enum.variants] == ["Counter", "Gauge", "Histogram"]
        assert [variant.literal for variant in node.value_enum.variants] == ["counter", "gauge", "histogram"]

    def test_regex_alternatives_are_not_enum_shaped(self) -> None:
        """The enum-shaped test is narrowed to literal terms."""
        assert isinstance(node_for("a:/[a-z]+/ | b:/[0-9]+/"), am.TerminalNode)

    def test_trivia_rules_get_no_node(self) -> None:
        model = model_for_text("target := x:item ;\n" + ITEM_TAIL + "_trivia := content:/[ ]+/ ;\n")
        assert "_trivia" not in model.nodes
        assert set(model.nodes) == {"target", "item", "other"}

    def test_every_non_trivia_rule_gets_a_node(self) -> None:
        model = model_for("x:item")
        assert set(model.nodes) == {"target", "item", "other"}


class TestEquivalentLiteralSpellings:
    """A label states what a value is, so alternatives sharing one are one variant."""

    COLOUR = 'red:"red" | blue:"blue" | gray:"gray" | gray:"grey"'

    def test_alternatives_sharing_a_label_merge_into_one_variant(self) -> None:
        node = node_for(self.COLOUR)
        assert isinstance(node, am.EnumNode)
        assert [variant.name for variant in node.value_enum.variants] == ["Red", "Blue", "Gray"]

    def test_the_first_spelling_is_the_canonical_one(self) -> None:
        """It is what the reverse direction renders the merged variant as."""
        node = node_for(self.COLOUR)
        assert isinstance(node, am.EnumNode)
        assert [variant.literal for variant in node.value_enum.variants] == ["red", "blue", "gray"]

    def test_a_merged_variant_is_renameable_under_its_computed_name(self) -> None:
        model = configured(self.COLOUR, "rule target { variant Gray: Grey; }")
        node = model.nodes["target"]
        assert isinstance(node, am.EnumNode)
        assert [variant.name for variant in node.value_enum.variants] == ["Red", "Blue", "Grey"]

    def test_distinct_labels_landing_on_one_variant_name_are_still_an_error(self) -> None:
        """Merging is about equivalent spellings of one value, not about colliding names."""
        assert "value-enum variant 'Gray'" in errors_for('gray:"gray" | gray_:"grey"')[0]


class TestTerminalOnlySeparators:
    def test_no_ws_separators_are_fine(self) -> None:
        assert isinstance(node_for('a:"x" . b:/[0-9]+/'), am.TerminalNode)

    def test_ws_allowed_separator_is_an_error(self) -> None:
        errors = errors_for('a:"x" , b:/[0-9]+/')
        assert len(errors) == 1
        assert "whitespace-permitting separator" in errors[0]
        assert "text_from" in errors[0]

    def test_ws_required_separator_is_an_error(self) -> None:
        assert "whitespace-permitting separator" in errors_for('a:"x" : b:/[0-9]+/')[0]

    def test_trailing_separator_is_an_error(self) -> None:
        assert "whitespace-permitting separator" in errors_for('a:"x" . b:/[0-9]+/ ,')[0]

    def test_reported_once_per_rule(self) -> None:
        assert len(errors_for('a:"x" , b:/[0-9]+/ | c:"y" , d:/[0-9]+/')) == 1

    def test_sub_expression_separator_is_an_error(self) -> None:
        """The rule's span covers the sub-expression too, so its separators matter as much."""
        assert "whitespace-permitting separator" in errors_for('( a:"x" : b:/[0-9]+/ )')[0]

    def test_nested_sub_expression_separator_is_an_error(self) -> None:
        assert "whitespace-permitting separator" in errors_for('a:"x" . ( ( b:"y" , c:/[0-9]+/ ) )')[0]

    def test_sub_expression_with_no_ws_separators_is_fine(self) -> None:
        assert isinstance(node_for('a:"x" . ( b:"y" . c:/[0-9]+/ )?'), am.TerminalNode)


class TestSumVersusProduct:
    def test_disjoint_alternatives_are_a_sum(self) -> None:
        node = node_for("a:item | b:other")
        assert isinstance(node, am.SumNode)
        assert [variant.name for variant in node.variants] == ["A", "B"]

    def test_non_disjoint_alternatives_merge_into_a_product(self) -> None:
        """Same labels, indistinguishable in the CST: one shape, not a fork."""
        node = node_for('a:item , "!" | a:item , "?"')
        assert isinstance(node, am.ProductNode)
        assert node.merged is True

    def test_optional_extras_subset_pair_merges(self) -> None:
        node = node_for("a:item | a:item , b:other?")
        assert isinstance(node, am.ProductNode)
        assert fields_by_name(node)["b"].container is am.Container.OPTIONAL

    def test_required_extras_subset_pair_merges(self) -> None:
        """Disjoint, but one alternative is a strict extension of the other."""
        node = node_for('"import" , name:item | "import" , name:item , "as" , alias:other')
        assert isinstance(node, am.ProductNode)
        types = fields_by_name(node)
        assert types["name"].container is am.Container.SINGLE
        assert types["alias"].container is am.Container.OPTIONAL

    def test_shared_label_conflict_stays_a_sum(self) -> None:
        """The shared structure itself differs, so the pair is a genuine fork."""
        node = node_for("a:item | a:item . a:item , b:other")
        assert isinstance(node, am.SumNode)

    def test_order_only_difference_merges(self) -> None:
        """The count-based test cannot use child order, so this over-approximates."""
        node = node_for("a:item , b:other | b:other , a:item")
        assert isinstance(node, am.ProductNode)
        assert node.merged is True

    def test_disjoint_kinds_on_a_shared_required_label(self) -> None:
        """Identical label sets, but the shared required labels cannot hold the same children."""
        node = node_for("x:item . a:item | x:other . a:other")
        assert isinstance(node, am.SumNode)
        assert [variant.name for variant in node.variants] == ["Alt1", "Alt2"]

    def test_three_alternatives_all_pairwise_disjoint(self) -> None:
        node = node_for("a:item | b:other | c:item")
        assert isinstance(node, am.SumNode)

    def test_one_bad_pair_merges_the_whole_rule(self) -> None:
        node = node_for("a:item | b:other | a:item , c:item?")
        assert isinstance(node, am.ProductNode)


class TestSignaturePredicates:
    @staticmethod
    def signatures(body: str) -> list[gshape.AltSignature]:
        rule = parse_grammar(f"target := {body} ;\n{ITEM_TAIL}").identifiers["target"]
        signatures: list[gshape.AltSignature] = []
        for alt in rule.alternatives:
            arities = ce.arities_for_alternative(alt, "target")
            signatures.append(
                gshape.AltSignature(
                    labels={
                        label: gshape.LabelSignature(count=count, kinds=frozenset({gshape.TEXT_KIND}))
                        for label, count in arities.items()
                    }
                )
            )
        return signatures

    @staticmethod
    def signature(**labels: tuple[int, int, frozenset[str]]) -> gshape.AltSignature:
        return gshape.AltSignature(
            labels={
                label: gshape.LabelSignature(count=ce.LabelCount.of(low, high), kinds=kinds)
                for label, (low, high, kinds) in labels.items()
            }
        )

    def test_absent_label_is_exactly_zero(self) -> None:
        left, right = self.signatures("a:item | a:item , b:other?")
        assert gshape.alternatives_are_disjoint(left, right) is False

    def test_disjoint_kinds_on_a_shared_required_label(self) -> None:
        left = self.signature(a=(1, 1, frozenset({"item"})))
        right = self.signature(a=(1, 1, frozenset({"other"})))
        assert gshape.alternatives_are_disjoint(left, right) is True

    def test_disjoint_kinds_on_an_optional_label_do_not_separate(self) -> None:
        """Both alternatives can present zero children for the label, so it cannot dispatch."""
        left = self.signature(a=(0, 1, frozenset({"item"})))
        right = self.signature(a=(0, 1, frozenset({"other"})))
        assert gshape.alternatives_are_disjoint(left, right) is False

    def test_overlapping_kinds_do_not_separate(self) -> None:
        left = self.signature(a=(1, 1, frozenset({"item", "other"})))
        right = self.signature(a=(1, 1, frozenset({"other"})))
        assert gshape.alternatives_are_disjoint(left, right) is False

    def test_subset_shape_needs_intersecting_kinds(self) -> None:
        left = self.signature(a=(1, 1, frozenset({"item"})))
        right = self.signature(a=(1, 1, frozenset({"other"})), b=(1, 1, frozenset({"item"})))
        assert gshape.alternatives_are_subset_shaped(left, right) is False

    def test_required_extra_makes_a_pair_disjoint(self) -> None:
        left, right = self.signatures("a:item | a:item . b:other")
        assert gshape.alternatives_are_disjoint(left, right) is True

    def test_unbounded_max_intersects_everything(self) -> None:
        left, right = self.signatures("a:item+ | a:item . a:item . a:item")
        assert gshape.alternatives_are_disjoint(left, right) is False

    def test_equal_label_sets_are_never_subset_shaped(self) -> None:
        left, right = self.signatures("a:item | a:item")
        assert gshape.alternatives_are_subset_shaped(left, right) is False

    def test_subset_shape_is_symmetric(self) -> None:
        left, right = self.signatures("a:item | a:item . b:other")
        assert gshape.alternatives_are_subset_shaped(left, right) is True
        assert gshape.alternatives_are_subset_shaped(right, left) is True


class TestSumVariants:
    def test_single_rule_reference_alternative_gets_a_direct_payload(self) -> None:
        node = node_for("a:item | b:other")
        assert isinstance(node, am.SumNode)
        assert [variant.payload for variant in node.variants] == [am.NodeType("Item"), am.NodeType("Other")]

    def test_auto_labeled_rule_reference_is_a_direct_payload(self) -> None:
        node = node_for("item | other")
        assert isinstance(node, am.SumNode)
        assert [variant.name for variant in node.variants] == ["Item", "Other"]
        assert [payload_name(variant) for variant in node.variants] == ["Item", "Other"]

    def test_shared_payload_type_falls_back_to_generated_classes(self) -> None:
        """Rule (a)'s uniqueness condition keeps the Python union free of duplicates."""
        model = model_for("a:item | b:item")
        node = model.nodes["target"]
        assert isinstance(node, am.SumNode)
        assert [payload_name(variant) for variant in node.variants] == ["TargetA", "TargetB"]
        assert set(model.payload_classes) == {"TargetA", "TargetB"}

    def test_optional_rule_reference_is_not_a_direct_payload(self) -> None:
        model = model_for("a:item? . b:other | c:item")
        node = model.nodes["target"]
        assert isinstance(node, am.SumNode)
        assert payload_name(node.variants[0]) == "TargetAlt1"
        assert payload_name(node.variants[1]) == "Item"

    def test_multi_item_alternative_is_named_by_index(self) -> None:
        node = node_for("a:item . b:other | c:item")
        assert isinstance(node, am.SumNode)
        assert [variant.name for variant in node.variants] == ["Alt1", "C"]

    def test_payload_class_fields_use_per_alternative_arity(self) -> None:
        """The label required in this alternative is not degraded by the other alternative."""
        model = model_for("a:item . b:other | c:item")
        payload = model.payload_classes["TargetAlt1"]
        assert payload.alternative_index == 0
        assert {field.name: field.type.container for field in payload.fields} == {
            "a": am.Container.SINGLE,
            "b": am.Container.SINGLE,
        }

    def test_a_nested_sum_payload_stays_direct_while_its_members_are_distinct(self) -> None:
        model = model_for_text(
            "target := t:outer | u:item ;\nouter := i:other | b:extra ;\nextra := e:/[A-Z]+/ ;\n" + ITEM_TAIL
        )
        node = model.nodes["target"]
        assert isinstance(node, am.SumNode)
        assert [variant.payload_rule for variant in node.variants] == ["outer", "item"]

    def test_a_class_reachable_through_two_variants_demotes_both(self) -> None:
        """A nested sum's members are members of the enclosing union too, so ``Item`` twice
        would leave ``isinstance`` dispatch picking whichever variant comes first."""
        model = model_for_text("target := t:outer | u:item ;\nouter := i:other | b:item ;\n" + ITEM_TAIL)
        node = model.nodes["target"]
        assert isinstance(node, am.SumNode)
        assert [payload_name(variant) for variant in node.variants] == ["TargetT", "TargetU"]
        outer = model.nodes["outer"]
        assert isinstance(outer, am.SumNode)
        assert [variant.payload_rule for variant in outer.variants] == ["other", "item"]

    def test_a_self_referential_sum_payload_terminates(self) -> None:
        """Expansion cuts the cycle: the variant carries nothing the others do not already."""
        model = model_for_text("target := t:target | u:item ;\n" + ITEM_TAIL)
        node = model.nodes["target"]
        assert isinstance(node, am.SumNode)
        assert [variant.payload_rule for variant in node.variants] == ["target", "item"]

    def test_variant_carries_its_dispatch_signature(self) -> None:
        node = node_for("a:item | b:other")
        assert isinstance(node, am.SumNode)
        assert set(node.variants[0].signature.labels) == {"a"}
        assert node.variants[0].signature.labels["a"].kinds == frozenset({"item"})


class TestSumDispatch:
    """The table a converter counts a node's children into to recover the alternative."""

    def sum_dispatch(self, body: str) -> am.SumDispatch:
        node = node_for(body)
        assert isinstance(node, am.SumNode)
        return am.sum_dispatch(node)

    def test_one_pair_per_label_and_kind_it_can_carry(self) -> None:
        dispatch = self.sum_dispatch("a:item | b:other")
        assert dispatch.pairs == (am.DispatchPair("a", "item"), am.DispatchPair("b", "other"))

    def test_an_alternative_bounds_its_own_labels_and_forbids_the_rest(self) -> None:
        dispatch = self.sum_dispatch("a:item | b:other")
        first, second = dispatch.alternatives
        assert first.bounds == (am.LabelBound(label="a", pairs=(0,), minimum=1, maximum=1),)
        assert first.forbidden == (1,)
        assert second.bounds == (am.LabelBound(label="b", pairs=(1,), minimum=1, maximum=1),)
        assert second.forbidden == (0,)

    def test_a_label_two_alternatives_share_counts_each_kind_apart(self) -> None:
        """A label whose kind differs per alternative needs a count per kind, not per label."""
        dispatch = self.sum_dispatch("a:item . b:other | a:other . c:item")
        index = {pair: position for position, pair in enumerate(dispatch.pairs)}
        as_item = index[am.DispatchPair("a", "item")]
        as_other = index[am.DispatchPair("a", "other")]
        first, second = dispatch.alternatives
        assert am.LabelBound(label="a", pairs=(as_item,), minimum=1, maximum=1) in first.bounds
        assert as_other in first.forbidden
        assert am.LabelBound(label="a", pairs=(as_other,), minimum=1, maximum=1) in second.bounds
        assert as_item in second.forbidden

    def test_a_repeated_label_carries_an_unbounded_maximum(self) -> None:
        dispatch = self.sum_dispatch("a:item+ . b:other | c:item")
        (bound_a, bound_b) = dispatch.alternatives[0].bounds
        assert (bound_a.minimum, bound_a.maximum) == (1, math.inf)
        assert (bound_b.minimum, bound_b.maximum) == (1, 1)

    def test_a_label_the_alternative_accepts_freely_needs_no_bound(self) -> None:
        dispatch = self.sum_dispatch("a:item . b:other* | c:item")
        assert [bound.label for bound in dispatch.alternatives[0].bounds] == ["a"]
        assert dispatch.alternatives[0].forbidden == (2,)


class TestFieldTypes:
    def test_required_rule_reference(self) -> None:
        assert fields_by_name(node_for("x:item"))["x"] == am.FieldType(am.NodeType("Item"), am.Container.SINGLE)

    def test_optional_rule_reference(self) -> None:
        assert fields_by_name(node_for("x:item?"))["x"] == am.FieldType(am.NodeType("Item"), am.Container.OPTIONAL)

    def test_repeated_rule_reference(self) -> None:
        assert fields_by_name(node_for("x:item*"))["x"] == am.FieldType(am.NodeType("Item"), am.Container.COLLECTION)

    def test_required_regex(self) -> None:
        assert fields_by_name(node_for("x:/[0-9]+/ . y:item"))["x"] == am.FieldType(am.TEXT, am.Container.SINGLE)

    def test_optional_regex(self) -> None:
        assert fields_by_name(node_for("x:/[0-9]+/? . y:item"))["x"] == am.FieldType(am.TEXT, am.Container.OPTIONAL)

    def test_repeated_regex(self) -> None:
        assert fields_by_name(node_for("x:/[0-9]+/* . y:item"))["x"] == am.FieldType(am.TEXT, am.Container.COLLECTION)

    def test_required_literal_is_a_span(self) -> None:
        assert fields_by_name(node_for('x:"lit" . y:item'))["x"] == am.FieldType(am.SPAN, am.Container.SINGLE)

    def test_optional_literal_is_a_presence_bool(self) -> None:
        assert fields_by_name(node_for('x:"pub"? . y:item'))["x"] == am.FieldType(am.BOOL, am.Container.SINGLE)

    def test_repeated_literal_is_a_span_collection(self) -> None:
        assert fields_by_name(node_for('x:"!"* . y:item'))["x"] == am.FieldType(am.SPAN, am.Container.COLLECTION)

    def test_dotted_name_repetition_stays_one_collection(self) -> None:
        """The same type under one label is a plain collection, not a field enum."""
        types = fields_by_name(node_for('part:item . ( "." . part:item )*'))
        assert types["part"] == am.FieldType(am.NodeType("Item"), am.Container.COLLECTION)

    def test_unlabeled_items_contribute_no_fields(self) -> None:
        node = node_for('%"(" . x:item . %")"')
        assert isinstance(node, am.ProductNode)
        assert [field.name for field in node.fields] == ["x"]

    def test_label_free_product_is_a_marker_node(self) -> None:
        node = node_for('%"(" . %item . %")"')
        assert isinstance(node, am.ProductNode)
        assert node.fields == ()

    def test_fields_follow_grammar_order(self) -> None:
        node = node_for("zebra:item . alpha:other")
        assert isinstance(node, am.ProductNode)
        assert [field.name for field in node.fields] == ["zebra", "alpha"]


class TestMergedProductFields:
    def test_label_present_in_one_alternative_is_optional(self) -> None:
        types = fields_by_name(node_for("a:item , b:other? | a:item"))
        assert types["b"].container is am.Container.OPTIONAL

    def test_types_collect_across_alternatives(self) -> None:
        """A label typed differently per alternative becomes one field enum on the merged product."""
        model = model_for("a:item? . c:item | a:other? . c:item")
        node = model.nodes["target"]
        assert isinstance(node, am.ProductNode)
        assert node.merged is True
        field_type = fields_by_name(node)["a"]
        assert field_type.element == am.NodeType("TargetA")
        assert field_type.container is am.Container.OPTIONAL
        assert [variant.name for variant in model.field_enums["TargetA"].variants] == ["Item", "Other"]


class TestFieldEnums:
    def test_sub_expression_alternation_under_one_label(self) -> None:
        model = model_for("( a:item | a:other ) . b:item")
        field_type = fields_by_name(model.nodes["target"])["a"]
        assert field_type.element == am.NodeType("TargetA")
        assert field_type.container is am.Container.SINGLE
        enum = model.field_enums["TargetA"]
        assert [(variant.name, variant.element) for variant in enum.variants] == [
            ("Item", am.NodeType("Item")),
            ("Other", am.NodeType("Other")),
        ]

    def test_label_reappearing_on_differently_typed_items(self) -> None:
        model = model_for("a:item , a:other")
        assert [variant.name for variant in model.field_enums["TargetA"].variants] == ["Item", "Other"]

    def test_node_and_terminal_under_one_label(self) -> None:
        model = model_for("a:item , a:/[0-9]+/")
        enum = model.field_enums["TargetA"]
        assert [(variant.name, variant.element) for variant in enum.variants] == [
            ("Item", am.NodeType("Item")),
            ("Text", am.TEXT),
        ]

    def test_literal_mixed_with_a_node_collapses_to_text(self) -> None:
        """A literal's text is recoverable from its span, so the mixed label carries text."""
        model = model_for('a:item , a:"lit"')
        assert [variant.element for variant in model.field_enums["TargetA"].variants] == [
            am.NodeType("Item"),
            am.TEXT,
        ]

    def test_literal_mixed_with_a_regex_is_plain_text(self) -> None:
        types = fields_by_name(node_for('a:"lit" , a:/[0-9]+/ , b:item'))
        assert types["a"] == am.FieldType(am.TEXT, am.Container.COLLECTION)

    def test_a_field_enum_carries_at_most_one_scalar_variant(self) -> None:
        """A literal and a regex under one label are one ``Text``, which is why a position of
        either kind resolves to a single variant."""
        model = model_for('a:"lit" , a:/[0-9]+/ , a:item')
        assert [(variant.name, variant.element) for variant in model.field_enums["TargetA"].variants] == [
            ("Text", am.TEXT),
            ("Item", am.NodeType("Item")),
        ]

    def test_payload_class_field_enum_is_named_for_the_payload(self) -> None:
        model = model_for("a:item , a:other , z:item | q:other")
        assert "TargetAlt1A" in model.field_enums


class TestUnlabeledIncludedRegex:
    """An included regex needs a label, or its text is recorded nowhere."""

    def test_unlabeled_included_regex_in_a_product_is_an_error(self) -> None:
        errors = errors_for("a:item . $/[0-9]+/")
        assert len(errors) == 1
        assert "included regex /[0-9]+/ has no label" in errors[0]

    def test_reported_once_per_pattern(self) -> None:
        assert len(errors_for("a:item . $/[0-9]+/ | b:item . $/[0-9]+/")) == 1

    def test_a_suppressed_regex_is_not_an_error(self) -> None:
        """A suppressed item is no child of the CST either, so nothing is being dropped."""
        assert isinstance(node_for("a:item . %/[0-9]+/"), am.ProductNode)

    def test_terminal_only_rules_are_exempt(self) -> None:
        """Their whole span is the ``text`` field, unlabeled parts included."""
        assert isinstance(node_for('a:"x" . $/[0-9]+/'), am.TerminalNode)


class TestSynthesisPlans:
    """The grammar-shaped plans the reverse converters follow."""

    @staticmethod
    def slots(body: str) -> list[am.Slot]:
        return list(model_for(body).plans["target"].alternatives[0].slots)

    def test_nested_quantifier_bounds_multiply(self) -> None:
        assert [(slot.label, slot.minimum, slot.maximum) for slot in self.slots("x:item . ( y:item . y:item )*")] == [
            ("x", 1, 1),
            ("y", 0, math.inf),
            ("y", 0, math.inf),
        ]

    def test_optional_sub_expression_bounds(self) -> None:
        assert [(slot.minimum, slot.maximum) for slot in self.slots("x:item . ( y:item )?")] == [(1, 1), (0, 1)]

    def test_alternation_branches_share_a_group_and_record_their_branch(self) -> None:
        slots = self.slots("( a:item | a:other )*")
        assert [slot.rule_name for slot in slots] == ["item", "other"]
        assert slots[0].group is not None
        assert slots[0].group == slots[1].group
        assert [slot.branch for slot in slots] == [0, 1]

    def test_a_group_counts_the_branches_that_contribute_no_slot(self) -> None:
        """A branch of suppressed literals demands none of the group's labels, so the count
        cannot be read back off the slots."""
        slots = self.slots('( a:item | %"none" )')
        assert [(slot.branch, slot.branch_count) for slot in slots] == [(0, 2)]

    def test_a_nested_alternation_keeps_its_branch_count(self) -> None:
        slots = self.slots("( a:item | ( a:other | a:item ) )")
        assert [slot.branch_count for slot in slots] == [2, 2, 2]

    def test_a_position_outside_an_alternation_has_one_branch(self) -> None:
        assert [(slot.branch, slot.branch_count) for slot in self.slots("x:item")] == [(0, 1)]

    def test_a_groups_own_repetition_is_recorded_apart_from_its_slots(self) -> None:
        """A starred item inside a branch is not the group repeating: only one branch is taken."""
        inner_star = self.slots("( a:item* | b:other )")
        assert [(slot.maximum, slot.group_maximum) for slot in inner_star] == [(math.inf, 1), (1, 1)]
        repeated = self.slots("( a:item | b:other )*")
        assert [slot.group_maximum for slot in repeated] == [math.inf, math.inf]

    def test_a_nested_alternation_keeps_the_outer_repetition_bound(self) -> None:
        assert [slot.group_maximum for slot in self.slots("( a:item | ( a:other | a:item ) )*")] == [math.inf] * 3

    def test_a_plain_sub_expression_starts_no_group(self) -> None:
        """Only mutually exclusive branches may take a label's values out of position order."""
        assert [slot.group for slot in self.slots('part:item . ( "." . part:item )*')] == [None, None]

    def test_a_nested_alternation_stays_in_its_branch(self) -> None:
        slots = self.slots("( a:item | ( a:other | a:item ) )*")
        assert len({slot.group for slot in slots}) == 1
        assert [slot.branch for slot in slots] == [0, 1, 1]

    def test_terminal_plan_spells_an_alternative_as_one_regex(self) -> None:
        plan = model_for_text('target := a:"x" . b:/[0-9]+/ ;\n').plans["target"].terminals[0]
        assert plan.pattern is not None
        assert re.fullmatch(plan.pattern, "x42") is not None
        assert re.fullmatch(plan.pattern, "y42") is None
        assert [(piece.label, piece.group is None) for piece in plan.pieces] == [("a", True), ("b", False)]

    @pytest.mark.parametrize(
        "body",
        ["c:/[a-z]/+", '( a:"x" . b:/[0-9]+/ )'],
        ids=["repeated_included_item", "sub_expression"],
    )
    def test_unsynthesisable_terminal_shapes_have_no_pattern(self, body: str) -> None:
        """One regex cannot say which slice of the text each occurrence took."""
        node = node_for(body)
        assert isinstance(node, am.TerminalNode)
        assert model_for(body).plans["target"].terminals[0].pattern is None

    def test_a_literal_slot_records_the_text_it_renders(self) -> None:
        """It is the only value the position can carry: the text comes back from the grammar."""
        slots = self.slots('x:"null" . x:/[0-9]+/ . y:item')
        assert [(slot.kind, slot.literal, slot.pattern) for slot in slots] == [
            (am.SlotKind.LITERAL, "null", None),
            (am.SlotKind.TEXT, None, "[0-9]+"),
            (am.SlotKind.NODE, None, None),
        ]

    def test_only_terminal_only_rules_get_text_plans(self) -> None:
        assert model_for("x:item").plans["target"].terminals == ()


class TestTerminalPatternComposition:
    """A rule's terminals are concatenated into one pattern, which has to compile."""

    def test_two_terminals_sharing_a_group_name_is_an_error(self) -> None:
        errors = errors_for("a:/(?P<d>[0-9])/ . b:/(?P<d>[a-z])/")
        assert len(errors) == 1
        assert "capture group 'd' is defined more than once" in errors[0]
        assert "make it non-capturing" in errors[0]

    def test_a_group_named_like_a_generated_one_is_an_error(self) -> None:
        errors = errors_for("a:/(?P<_ast_g0>[0-9])+/")
        assert len(errors) == 1
        assert "capture group '_ast_g0' is defined more than once" in errors[0]

    def test_a_redirected_text_checks_its_own_item(self) -> None:
        errors = configured_errors('"<" . a:/(?P<_ast_g0>[0-9]+)/ . ">"', "rule target { text_from: a; }")
        assert len(errors) == 1
        assert "capture group '_ast_g0' is defined more than once" in errors[0]

    def test_distinct_group_names_compose_into_a_pattern_that_compiles(self) -> None:
        plan = model_for("a:/(?P<d>[0-9])/ . b:/(?P<e>[a-z])/").plans["target"].terminals[0]
        assert plan.pattern is not None
        assert re.fullmatch(plan.pattern, "1a") is not None

    def test_an_escaped_parenthesis_is_no_group(self) -> None:
        """A literal ``(?P<`` in the terminal's text defines nothing."""
        plan = model_for(r"a:/\(\?P<d>x/ . b:/\(\?P<d>y/").plans["target"].terminals[0]
        assert plan.pattern is not None
        assert re.fullmatch(plan.pattern, "(?P<d>x(?P<d>y") is not None

    def test_a_duplicate_behind_a_lookbehind_is_still_found(self) -> None:
        """``(?<=`` opens a lookbehind, so the group after it is a definition like any other."""
        errors = errors_for("a:/(?<=x)(?P<d>[0-9])/ . b:/(?P<d>[a-z])/")
        assert len(errors) == 1
        assert "capture group 'd' is defined more than once" in errors[0]

    @pytest.mark.parametrize("assertion", ["(?<=x)", "(?<!x)", "(?=x)", "(?!x)"])
    def test_a_lookaround_defines_no_group(self, assertion: str) -> None:
        """The same assertion twice is not a repeated group name, so the rule composes."""
        model = model_for(f"a:/{assertion}[0-9]+/ . b:/{assertion}[a-z]+/")
        plan = model.plans["target"].terminals[0]
        assert plan.pattern is not None
        assert re.compile(plan.pattern).groupindex.keys() == {"_ast_g0", "_ast_g1"}

    def test_two_lookbehinds_naming_one_group_after_them_are_one_error(self) -> None:
        errors = errors_for("a:/(?<=x)(?<d>[0-9])/ . b:/(?<=y)(?<d>[a-z])/")
        assert len(errors) == 1
        assert "capture group 'd' is defined more than once" in errors[0]


class TestNameHygiene:
    @pytest.mark.parametrize("label", ["class", "def", "lambda"])
    def test_python_keyword_label_is_an_error(self, label: str) -> None:
        errors = errors_for(f"{label}:item")
        assert len(errors) == 1
        assert "Python keyword" in errors[0]
        assert f"field {label}" in errors[0]

    @pytest.mark.parametrize("label", ["self", "crate", "super"])
    def test_unrawable_rust_keyword_label_is_an_error(self, label: str) -> None:
        assert "raw identifier" in errors_for(f"{label}:item")[0]

    def test_rawable_rust_keyword_label_is_fine(self) -> None:
        assert "type" in fields_by_name(node_for("type:item"))

    def test_dunder_label_is_an_error(self) -> None:
        assert "mangling" in errors_for("__eq__:item")[0]

    @pytest.mark.parametrize("label", ["span", "text", "from_cst", "to_cst"])
    def test_reserved_member_label_is_an_error(self, label: str) -> None:
        assert "every generated node already carries" in errors_for(f"{label}:item")[0]

    def test_every_bad_label_is_reported(self) -> None:
        assert len(errors_for("class:item . self:item . span:item")) == 3

    def test_colliding_rule_type_names(self) -> None:
        """Underscores collapse in type names, so two rule names can land on one type."""
        with pytest.raises(am.AstModelError) as exc:
            model_for_text("target := a:foo_bar . b:foo__bar ;\nfoo_bar := x:/[a-z]+/ ;\nfoo__bar := y:/[a-z]+/ ;\n")
        assert "collides with rule 'foo_bar'" in exc.value.errors[0]

    def test_generated_payload_name_colliding_with_a_rule(self) -> None:
        with pytest.raises(am.AstModelError) as exc:
            model_for_text(
                "target := a:item . b:other | c:item . d:other . e:item ;\ntarget_alt1 := z:/[a-z]+/ ;\n" + ITEM_TAIL
            )
        assert any("TargetAlt1" in error for error in exc.value.errors)

    def test_value_enum_name_collision(self) -> None:
        with pytest.raises(am.AstModelError) as exc:
            model_for_text('target := a:flag ;\nflag := on:"on" | off:"off" ;\nflag_value := z:/[a-z]+/ ;\n')
        assert any("FlagValue" in error for error in exc.value.errors)

    def test_duplicate_value_enum_variant_name(self) -> None:
        with pytest.raises(am.AstModelError) as exc:
            model_for_text('target := on:"on" | on_:"1" | off:"off" ;\n')
        assert "value-enum variant 'On'" in exc.value.errors[0]

    def test_variants_colliding_only_as_python_enum_members(self) -> None:
        """``HTTPCode`` and ``HttpCode`` are distinct variants but one Python enum member."""
        errors = configured_errors(
            'http_code:"http" | other:"other"',
            "rule target { variant Other: HTTPCode; }",
        )
        assert len(errors) == 1
        assert "the Python enum member 'HTTP_CODE'" in errors[0]
        assert "variant Other:" in errors[0]

    def test_duplicate_sum_variant_name(self) -> None:
        with pytest.raises(am.AstModelError) as exc:
            model_for_text(f"target := on:item | on_:other ;\n{ITEM_TAIL}")
        assert "both produce variant name 'On'" in exc.value.errors[0]

    def test_labeled_invocation_is_an_error(self) -> None:
        rule = gsm.Rule(
            name="target",
            alternatives=[
                gsm.Items(
                    items=[
                        gsm.Item(
                            label="x",
                            disposition=gsm.Disposition.INCLUDE,
                            term=gsm.Invocation(method_name="m", expression=None),
                            quantifier=gsm.REQUIRED,
                        ),
                        gsm.Item(
                            label="y",
                            disposition=gsm.Disposition.INCLUDE,
                            term=gsm.Identifier("target"),
                            quantifier=gsm.REQUIRED,
                        ),
                    ],
                    sep_after=[gsm.Separator.NO_WS, gsm.Separator.NO_WS],
                )
            ],
        )
        grammar = gsm.Grammar(rules=[rule], identifiers={"target": rule})
        with pytest.raises(am.AstModelError) as exc:
            am.build_ast_model(grammar)
        assert "invocation term" in exc.value.errors[0]


class TestInTreeGrammars:
    """Model building on the real grammars in the tree."""

    @pytest.mark.parametrize("grammar_path", TIER0_CLEAN_GRAMMARS, ids=lambda path: path.name)
    def test_model_builds(self, grammar_path: pathlib.Path) -> None:
        grammar = pipeline(parse_grammar_file(grammar_path))
        model = am.build_ast_model(grammar)

        expected = {rule.name for rule in grammar.rules if not rule.is_trivia_rule}
        assert set(model.nodes) == expected

        names = {node.name for node in model.nodes.values()}
        names |= set(model.payload_classes) | set(model.field_enums) | set(model.value_enums)
        total = len(model.nodes) + len(model.payload_classes) + len(model.field_enums) + len(model.value_enums)
        assert len(names) == total

    @pytest.mark.parametrize("grammar_path", TIER0_CLEAN_GRAMMARS, ids=lambda path: path.name)
    def test_referenced_types_all_exist(self, grammar_path: pathlib.Path) -> None:
        model = am.build_ast_model(pipeline(parse_grammar_file(grammar_path)))
        known = {node.name for node in model.nodes.values()} | set(model.payload_classes) | set(model.field_enums)

        def check(element: am.ElementType) -> None:
            if isinstance(element, am.NodeType):
                assert element.name in known

        for node in model.nodes.values():
            if isinstance(node, am.ProductNode):
                for field in node.fields:
                    check(field.type.element)
            elif isinstance(node, am.SumNode):
                for variant in node.variants:
                    check(variant.payload)
        for payload in model.payload_classes.values():
            for field in payload.fields:
                check(field.type.element)
        for field_enum in model.field_enums.values():
            for variant in field_enum.variants:
                check(variant.element)

    @pytest.mark.parametrize("grammar_path", IN_TREE_GRAMMARS, ids=lambda path: path.name)
    def test_only_actionable_errors(self, grammar_path: pathlib.Path) -> None:
        """A grammar that needs sidecar annotations must say so, never crash some other way."""
        grammar = pipeline(parse_grammar_file(grammar_path))
        try:
            am.build_ast_model(grammar)
        except am.AstModelError as error:
            rule_names = {rule.name for rule in grammar.rules}
            for message in error.errors:
                assert any(f"{name!r}" in message for name in rule_names)
                assert "`rule " in message

    def test_lsp_grammars_literal_only_rule_is_a_marker_product(self) -> None:
        """`namespace_stmt := "namespace" , ";" ,` carries no data, so it carries only a span.

        No sidecar statement could have rescued a ``text`` field here — the rule has no label to
        redirect to and one alternative to merge — which is why the literal-only shape classifies
        as a product instead.
        """
        model = am.build_ast_model(pipeline(parse_grammar_file(_FLTK_ROOT / "lsp" / "fltklsp.fltkg")))
        node = model.nodes["namespace_stmt"]
        assert isinstance(node, am.ProductNode)
        assert node.fields == ()

    def test_unparsefmt_grammar_needs_a_field_rename(self) -> None:
        """`text_literal := ... text:literal ...` collides with the reserved `text` member."""
        with pytest.raises(am.AstModelError) as exc:
            am.build_ast_model(pipeline(parse_grammar_file(_FLTK_ROOT / "unparse" / "unparsefmt.fltkg")))
        assert [error for error in exc.value.errors if "'text_literal'" in error]

    def test_a_two_line_sidecar_unblocks_the_unparsefmt_grammar(self) -> None:
        """The mirror image of the failure above: the rename is what the sidecar is for."""
        grammar = pipeline(parse_grammar_file(_FLTK_ROOT / "unparse" / "unparsefmt.fltkg"))
        config = ac.load_ast_config("rule text_literal { field text { name: body; } }", grammar, {ac.Backend.PYTHON})
        model = am.build_ast_model(grammar, config)
        node = model.nodes["text_literal"]
        assert isinstance(node, am.ProductNode)
        assert [(field.name, field.label) for field in node.fields] == [("body", "text")]

    def test_the_validator_and_the_model_classify_every_rule_alike(self) -> None:
        """One ladder, two consumers: a sidecar validated against a shape the model does not
        emit would accept an annotation that applies to nothing, or refuse a legal one."""
        grammar = pipeline(parse_grammar_file(_FLTK_ROOT / "fegen" / "fegen.fltkg"))
        model = am.build_ast_model(grammar)
        index = ac.build_grammar_index(grammar)
        shapes = {
            am.EnumNode: gshape.RuleShape.ENUM,
            am.TerminalNode: gshape.RuleShape.TERMINAL,
            am.SumNode: gshape.RuleShape.SUM,
            am.ProductNode: gshape.RuleShape.PRODUCT,
        }
        for rule_name, node in model.nodes.items():
            assert shapes[type(node)] is index.rules[rule_name].shape, rule_name
            if isinstance(node, am.ProductNode):
                assert set(index.rules[rule_name].label_index) == {field.label for field in node.fields}, rule_name


class TestTypeNameOverride:
    """`name:` renames a rule's generated type, and every name derived from it follows."""

    def test_rule_type_is_renamed(self) -> None:
        model = configured("x:item", "rule target { name: Document; }")
        assert model.rule_type_names["target"] == "Document"
        assert model.nodes["target"].name == "Document"

    def test_untouched_rules_keep_their_computed_names(self) -> None:
        model = configured("x:item", "rule target { name: Document; }")
        assert model.rule_type_names["item"] == "Item"

    def test_value_enum_name_follows_the_rename(self) -> None:
        model = configured_model(
            'target := kind:flavour ;\nflavour := hot:"hot" | cold:"cold" ;\n' + ITEM_TAIL,
            "rule flavour { name: Temperature; }",
        )
        node = model.nodes["flavour"]
        assert isinstance(node, am.EnumNode)
        assert node.value_enum.name == "TemperatureValue"
        assert set(model.value_enums) == {"TemperatureValue"}

    def test_payload_class_names_follow_the_rename(self) -> None:
        model = configured("a:item . b:other | c:item", "rule target { name: Choice; }")
        assert set(model.payload_classes) == {"ChoiceAlt1"}

    def test_field_enum_names_follow_the_rename(self) -> None:
        model = configured("a:item , a:other", "rule target { name: Choice; }")
        assert set(model.field_enums) == {"ChoiceA"}

    def test_a_rename_can_still_collide(self) -> None:
        errors = configured_errors("x:item", "rule target { name: Item; }")
        assert len(errors) == 1
        assert "collides with" in errors[0]


class TestVariantRenames:
    def test_sum_variant_is_renamed(self) -> None:
        model = configured("a:item | b:other", "rule target { variant A: Alpha; }")
        node = model.nodes["target"]
        assert isinstance(node, am.SumNode)
        assert [variant.name for variant in node.variants] == ["Alpha", "B"]

    def test_generated_payload_class_takes_the_new_name(self) -> None:
        model = configured("a:item . b:other | c:item", "rule target { variant Alt1: Pair; }")
        assert set(model.payload_classes) == {"TargetPair"}

    def test_value_enum_variant_is_renamed(self) -> None:
        model = configured_model(
            'target := kind:flavour ;\nflavour := hot:"hot" | cold:"cold" ;\n' + ITEM_TAIL,
            "rule flavour { variant Hot: Warm; }",
        )
        node = model.nodes["flavour"]
        assert isinstance(node, am.EnumNode)
        assert [variant.name for variant in node.value_enum.variants] == ["Warm", "Cold"]
        assert [variant.member for variant in node.value_enum.variants] == ["WARM", "COLD"]
        assert [variant.label for variant in node.value_enum.variants] == ["hot", "cold"]

    def test_member_name_is_the_upper_snake_of_the_variant(self) -> None:
        model = configured_model(
            'target := kind:flavour ;\nflavour := very_hot:"vh" | cold:"cold" ;\n' + ITEM_TAIL,
            "",
        )
        node = model.nodes["flavour"]
        assert isinstance(node, am.EnumNode)
        assert [variant.member for variant in node.value_enum.variants] == ["VERY_HOT", "COLD"]

    @pytest.mark.parametrize(
        ("new_name", "member"),
        [("HTTPCode", "HTTP_CODE"), ("XL", "XL"), ("HttpCode", "HTTP_CODE"), ("Alt2Foo", "ALT2_FOO")],
    )
    def test_member_name_keeps_an_acronym_run_together(self, new_name: str, member: str) -> None:
        """The member is permanent public API, so a rename must not come back mangled."""
        model = configured_model(
            'target := kind:flavour ;\nflavour := very_hot:"vh" | cold:"cold" ;\n' + ITEM_TAIL,
            f"rule flavour {{ variant VeryHot: {new_name}; }}",
        )
        node = model.nodes["flavour"]
        assert isinstance(node, am.EnumNode)
        assert node.value_enum.variants[0].member == member

    def test_unknown_selector_lists_the_computed_names(self) -> None:
        errors = configured_errors("a:item | b:other", "rule target { variant Nope: Alpha; }")
        assert len(errors) == 1
        assert "`variant Nope:` names no variant" in errors[0]
        assert "A, B" in errors[0]

    def test_a_rename_can_collide_with_a_sibling_variant(self) -> None:
        errors = configured_errors("a:item | b:other", "rule target { variant A: B; }")
        assert any("both produce variant name 'B'" in error for error in errors)


class TestFieldRenames:
    def test_field_is_renamed_and_keeps_its_label(self) -> None:
        model = configured("stanza:item", "rule target { field stanza { name: stanzas; } }")
        node = model.nodes["target"]
        assert isinstance(node, am.ProductNode)
        assert [(field.name, field.label) for field in node.fields] == [("stanzas", "stanza")]

    def test_rename_fixes_an_unusable_label(self) -> None:
        """A reserved label is a generation error; the rename is the documented fix."""
        model = configured("text:item", "rule target { field text { name: body; } }")
        assert list(fields_by_name(model.nodes["target"])) == ["body"]

    def test_rename_colliding_with_a_sibling_is_an_error(self) -> None:
        errors = configured_errors("a:item , b:other", "rule target { field a { name: b; } }")
        assert len(errors) == 1
        assert "both produce field name 'b'" in errors[0]

    def test_payload_class_fields_are_renamed_too(self) -> None:
        model = configured("a:item . b:other | c:item", "rule target { field a { name: alpha; } }")
        payload = model.payload_classes["TargetAlt1"]
        assert [field.name for field in payload.fields] == ["alpha", "b"]

    def test_rename_reaching_no_field_is_an_error(self) -> None:
        """Every variant carries its payload rule's type, so the sum has no field to rename."""
        errors = configured_errors("a:item | b:other", "rule target { field a { name: alpha; } }")
        assert len(errors) == 1
        assert "`field a { name: ... }` renames no field of this rule" in errors[0]

    def test_rename_of_a_suppressed_label_is_an_error(self) -> None:
        errors = configured_errors("a:item . %b:other", "rule target { field b { name: beta; } }")
        assert len(errors) == 1
        assert "renames no field of this rule" in errors[0]


class TestShapeOverride:
    def test_product_forces_disjoint_alternatives_to_merge(self) -> None:
        node = configured("a:item | b:other", "rule target { product; }").nodes["target"]
        assert isinstance(node, am.ProductNode)
        assert node.merged is True
        assert sorted(fields_by_name(node)) == ["a", "b"]

    def test_sum_forces_a_subset_shaped_pair_to_a_fork(self) -> None:
        """The extras are required, so dispatch on them is sound and `sum;` is legal."""
        node = configured("a:item | a:item . b:other", "rule target { sum; }").nodes["target"]
        assert isinstance(node, am.SumNode)
        assert [variant.name for variant in node.variants] == ["A", "Alt2"]

    def test_the_same_pair_defaults_to_a_merged_product(self) -> None:
        node = node_for("a:item | a:item . b:other")
        assert isinstance(node, am.ProductNode)
        assert node.merged is True

    def test_sum_on_a_non_disjoint_pair_is_an_error(self) -> None:
        errors = configured_errors("a:item | a:item . b:other?", "rule target { sum; }")
        assert len(errors) == 1
        assert "alternatives 1 and 2 cannot be" in errors[0]
        assert "label a distinguishing terminal" in errors[0]

    def test_stating_the_default_is_harmless(self) -> None:
        assert isinstance(configured("a:item | b:other", "rule target { sum; }").nodes["target"], am.SumNode)


class TestCustomRules:
    CUSTOM = 'rule item { custom(python: "pkg.mod.Item"); }'

    def test_custom_rule_gets_no_node(self) -> None:
        model = configured("x:item", self.CUSTOM)
        assert "item" not in model.nodes
        assert "item" not in model.rule_type_names
        assert model.custom_types["item"] == am.CustomType(rule_name="item", python="pkg.mod.Item", rust=None)

    def test_referencing_field_takes_the_custom_type(self) -> None:
        model = configured("x:item", self.CUSTOM)
        assert fields_by_name(model.nodes["target"])["x"] == am.FieldType(
            am.CustomType("item", "pkg.mod.Item", None), am.Container.SINGLE
        )

    def test_custom_rule_is_a_direct_sum_payload(self) -> None:
        model = configured("a:item | b:other", self.CUSTOM)
        node = model.nodes["target"]
        assert isinstance(node, am.SumNode)
        assert node.variants[0].payload == am.CustomType("item", "pkg.mod.Item", None)
        assert node.variants[0].payload_rule == "item"

    def test_custom_rule_names_a_field_enum_variant(self) -> None:
        model = configured("a:item , a:other", self.CUSTOM)
        assert [variant.name for variant in model.field_enums["TargetA"].variants] == ["Item", "Other"]

    def test_two_custom_rules_on_one_type_fall_back_to_payload_classes(self) -> None:
        """Uniqueness is by payload type: an `isinstance` dispatch could not tell these apart."""
        model = configured(
            "a:item | b:other",
            'rule item { custom(python: "pkg.mod.Shared"); }\nrule other { custom(python: "pkg.mod.Shared"); }',
        )
        node = model.nodes["target"]
        assert isinstance(node, am.SumNode)
        assert [payload_name(variant) for variant in node.variants] == ["TargetA", "TargetB"]

    def test_two_custom_rules_on_distinct_types_stay_direct(self) -> None:
        model = configured(
            "a:item | b:other",
            'rule item { custom(python: "pkg.mod.One"); }\nrule other { custom(python: "pkg.mod.Two"); }',
        )
        node = model.nodes["target"]
        assert isinstance(node, am.SumNode)
        assert [variant.payload_rule for variant in node.variants] == ["item", "other"]

    def test_a_shared_rust_type_falls_back_on_both_backends(self) -> None:
        """The two ASTs must stay shape-equivalent, so a Rust collision moves the Python one too."""
        model = configured(
            "a:item | b:other",
            'rule item { custom(rust: "app::Shared", python: "pkg.mod.One"); }\n'
            'rule other { custom(rust: "app::Shared", python: "pkg.mod.Two"); }',
        )
        node = model.nodes["target"]
        assert isinstance(node, am.SumNode)
        assert [payload_name(variant) for variant in node.variants] == ["TargetA", "TargetB"]

    def test_custom_rule_type_name_is_free_for_reuse(self) -> None:
        """The generator emits no `Item` type, so a rule may claim the name."""
        model = configured_model(
            "target := x:item . y:thing ;\nthing := z:/[a-z]+/ ;\n" + ITEM_TAIL,
            self.CUSTOM + "\nrule thing { name: Item; }\n",
        )
        assert model.rule_type_names["thing"] == "Item"


SCALAR_GRAMMAR = """
target := n:num , u:ident ;
num    := /-?[0-9]+/ ;
ident  := /[a-z]+/ ;
"""

QUOTED_GRAMMAR = """
target := s:quoted ;
quoted := "\\"" . content:/[^"]*/ . "\\"" ;
"""


def terminal_node(model: am.AstModel, rule_name: str) -> am.TerminalNode:
    node = model.nodes[rule_name]
    assert isinstance(node, am.TerminalNode)
    return node


class TestScalarCoercion:
    """``type:`` replaces a terminal-only rule's ``text`` with a typed ``value``."""

    def test_builtin_coercion_is_recorded(self) -> None:
        node = terminal_node(configured_model(SCALAR_GRAMMAR, "rule num { type: i64; }"), "num")
        assert node.coercion == am.BuiltinCoercion(name="i64")

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("i8", ("integer", 8, True)),
            ("u32", ("integer", 32, False)),
            ("f32", ("float", 32, False)),
            ("f64", ("float", 64, False)),
        ],
    )
    def test_builtin_widths(self, name: str, expected: tuple[str, int, bool]) -> None:
        coercion = am.BuiltinCoercion(name=name)
        family = "integer" if coercion.is_integer else "float" if coercion.is_float else "other"
        assert (family, coercion.bits, coercion.signed) == expected

    def test_every_builtin_the_sidecar_accepts_has_a_python_type(self) -> None:
        """The vocabulary and the type table must not drift: a builtin the validator takes but
        the table misses would reach a parse helper that does not exist."""
        assert set(am.PYTHON_SCALAR_TYPES) == set(ac.BUILTIN_SCALAR_TYPES)

    def test_the_three_builtin_families_are_pairwise_disjoint(self) -> None:
        """A width listed twice would report two families and pick a parse helper by accident."""
        families = [ac.INTEGER_SCALAR_TYPES, ac.FLOAT_SCALAR_TYPES, ac.WIDE_SCALAR_TYPES]
        for index, one in enumerate(families):
            for other in families[index + 1 :]:
                assert one & other == frozenset()

    def test_every_builtin_reports_exactly_one_family(self) -> None:
        """The drift a new width can cause: added to the vocabulary but to no family."""
        for name in ac.BUILTIN_SCALAR_TYPES:
            coercion = am.BuiltinCoercion(name=name)
            assert (coercion.is_integer, coercion.is_float) != (True, True)
            if coercion.is_integer or coercion.is_float:
                assert coercion.bits in (8, 16, 32, 64)
            else:
                assert name in ac.WIDE_SCALAR_TYPES

    @pytest.mark.parametrize("name", ["uuid", "decimal"])
    def test_the_two_opt_in_builtins_are_neither_integer_nor_float(self, name: str) -> None:
        coercion = am.BuiltinCoercion(name=name)
        assert not coercion.is_integer
        assert not coercion.is_float

    def test_custom_coercion_mirrors_every_entry(self) -> None:
        model = configured_model(
            SCALAR_GRAMMAR,
            'rule num { type: custom(rust_type: "app::Money", rust_parse: "app::parse", '
            'rust_unparse: "app::render", py_type: "pkg.mod.Money", py_parse: "pkg.mod.parse", '
            'py_unparse: "pkg.mod.render"); }',
        )
        assert terminal_node(model, "num").coercion == am.CustomCoercion(
            rule_name="num",
            python_type="pkg.mod.Money",
            python_parse="pkg.mod.parse",
            python_unparse="pkg.mod.render",
            rust_type="app::Money",
            rust_parse="app::parse",
            rust_unparse="app::render",
        )

    def test_an_ungenerated_backends_entries_stay_none(self) -> None:
        """Only the generated backend's entries are required, so the others may be absent."""
        model = configured_model(
            SCALAR_GRAMMAR,
            'rule num { type: custom(py_type: "pkg.mod.Money", py_parse: "pkg.mod.parse", '
            'py_unparse: "pkg.mod.render"); }',
        )
        coercion = terminal_node(model, "num").coercion
        assert isinstance(coercion, am.CustomCoercion)
        assert coercion.rust_type is None

    def test_a_coercion_does_not_change_the_use_site_type(self) -> None:
        """Erasing the node type at use sites is `transparent;`, which `type:` alone does not do."""
        model = configured_model(SCALAR_GRAMMAR, "rule num { type: i64; }")
        assert fields_by_name(model.nodes["target"])["n"].element == am.NodeType("Num")


class TestTextFrom:
    """``text_from:`` redirects a terminal-only rule's text to one label's child."""

    def test_the_label_is_recorded(self) -> None:
        node = terminal_node(configured_model(QUOTED_GRAMMAR, "rule quoted { text_from: content; }"), "quoted")
        assert node.text_from == "content"

    def test_the_plan_matches_only_the_redirected_text(self) -> None:
        """The node's text is the child's, so the pattern is that child's own terminal."""
        model = configured_model(QUOTED_GRAMMAR, "rule quoted { text_from: content; }")
        (plan,) = model.plans["quoted"].terminals
        assert plan.pattern == '(?P<_ast_g0>[^"]*)'
        assert [piece.label for piece in plan.pieces] == ["content"]

    def test_a_literal_sibling_keeps_its_position(self) -> None:
        """An included literal comes back from the grammar, so it stays a group-less piece."""
        model = configured_model(
            'target := s:tagged ;\ntagged := $"#" . content:/[a-z]+/ ;\n',
            "rule tagged { text_from: content; }",
        )
        (plan,) = model.plans["tagged"].terminals
        assert [(piece.label, piece.group) for piece in plan.pieces] == [(None, None), ("content", "_ast_g1")]

    def test_a_whitespace_separator_is_allowed_once_the_text_is_redirected(self) -> None:
        """`text_from:` is one of the fixes the separator error itself proposes."""
        grammar = 'target := s:spaced ;\nspaced := "(" , content:/[a-z]+/ , ")" ;\n'
        assert "whitespace-permitting" in errors_for("s:spaced", 'spaced := "(" , content:/[a-z]+/ , ")" ;\n')[0]
        model = configured_model(grammar, "rule spaced { text_from: content; }")
        assert terminal_node(model, "spaced").text_from == "content"

    def test_another_included_regex_is_an_error(self) -> None:
        """Only the redirected label's text survives, so the other regex could not come back."""
        errors = configured_errors(
            "s:pair",
            "rule pair { text_from: left; }",
            "pair := left:/[a-z]+/ . right:/[0-9]+/ ;\n",
        )
        assert len(errors) == 1
        assert "/[0-9]+/ is recorded nowhere" in errors[0]
        assert "`text_from: left;`" in errors[0]

    def test_a_suppressed_sibling_regex_is_fine(self) -> None:
        model = configured_model(
            "target := s:pair ;\npair := left:/[a-z]+/ . %/[0-9]+/ ;\n",
            "rule pair { text_from: left; }",
        )
        assert terminal_node(model, "pair").text_from == "left"

    def test_a_sub_expression_alternative_has_no_plan(self) -> None:
        """Conversion still works; only the reverse direction has nothing determined to do."""
        model = configured_model(
            "target := s:pair ;\npair := content:/[a-z]+/ . (%/[0-9]/ . %/[0-9]/) ;\n",
            "rule pair { text_from: content; }",
        )
        (plan,) = model.plans["pair"].terminals
        assert plan.pattern is None

    def test_a_coercion_applies_to_the_redirected_text(self) -> None:
        model = configured_model(
            'target := s:quoted ;\nquoted := "\\"" . content:/[0-9]+/ . "\\"" ;\n',
            "rule quoted { text_from: content; type: i64; }",
        )
        node = terminal_node(model, "quoted")
        assert (node.text_from, node.coercion) == ("content", am.BuiltinCoercion(name="i64"))


class TestTextFromModelChecks:
    """The label checks the model repeats for a hand-built ``ResolvedAstConfig``."""

    @staticmethod
    def hand_built(text: str, rule_name: str, label: str) -> tuple[str, ...]:
        config = ac.ResolvedAstConfig(rules={rule_name: ac.ResolvedRule(rule_name=rule_name, text_from=label)})
        with pytest.raises(am.AstModelError) as exc:
            am.build_ast_model(pipeline(parse_grammar(text)), config)
        return exc.value.errors

    def test_an_unknown_label_is_refused(self) -> None:
        errors = self.hand_built("target := s:tag ;\ntag := content:/[a-z]+/ ;\n", "tag", "nope")
        assert any("names no included label of this rule — its labels are: content" in error for error in errors)

    def test_a_suppressed_label_is_refused(self) -> None:
        """A suppressed item contributes no child, so there is no span to read the text from."""
        errors = self.hand_built("target := s:tag ;\ntag := %/[a-z]+/ . k:/[0-9]+/ ;\n", "tag", "nope")
        assert any("names no included label" in error for error in errors)

    def test_an_optional_label_is_refused(self) -> None:
        """``astrt.one`` would fail on every node the label happened not to match."""
        errors = self.hand_built("target := s:tag ;\ntag := content:/[a-z]+/? . k:/[0-9]+/ ;\n", "tag", "content")
        assert any("is optional_single — only a label occurring exactly once" in error for error in errors)

    def test_a_label_occurring_twice_is_refused(self) -> None:
        """The plan would keep the second occurrence's group while its pieces name the first."""
        errors = self.hand_built("target := s:tag ;\ntag := c:/[a-z]+/ . c:/[0-9]+/ ;\n", "tag", "c")
        assert any("is collection — only a label occurring exactly once" in error for error in errors)


ENUM_GRAMMAR = 'target := f:flag ;\nflag := yes:"yes" | no:"no" ;\n'

# A single-field product used at a required position, so `transparent;` applies to it.
WRAPPER_GRAMMAR = 'target := w:wrap ;\nwrap := "(" . only:item . ")" ;\n' + ITEM_TAIL


def element_of(model: am.AstModel, rule_name: str, field_name: str) -> am.ElementType:
    return fields_by_name(model.nodes[rule_name])[field_name].element


class TestTransparent:
    """``transparent;`` erases a rule's type: use sites carry its payload instead."""

    def test_a_terminal_only_rule_erases_to_its_text(self) -> None:
        model = configured("x:item", "rule item { transparent; }")
        assert element_of(model, "target", "x") == am.TransparentType("item", am.TEXT)
        assert model.transparent_types["item"] == am.TransparentType("item", am.TEXT)

    def test_an_erased_rule_is_not_a_public_node(self) -> None:
        model = configured("x:item", "rule item { transparent; }")
        assert "item" in model.nodes
        assert "item" not in model.public_nodes()
        assert "target" in model.public_nodes()

    def test_a_coercion_travels_with_the_payload(self) -> None:
        model = configured_model(SCALAR_GRAMMAR, "rule num { type: i64; transparent; }")
        assert element_of(model, "target", "n") == am.TransparentType("num", am.TEXT, am.BuiltinCoercion("i64"))

    def test_the_container_of_the_use_site_is_untouched(self) -> None:
        model = configured("x:item*", "rule item { transparent; }")
        assert fields_by_name(model.nodes["target"])["x"].container is am.Container.COLLECTION

    def test_an_enum_shaped_rule_erases_to_its_value_enum(self) -> None:
        model = configured_model(ENUM_GRAMMAR + ITEM_TAIL, "rule flag { transparent; }")
        assert element_of(model, "target", "f") == am.TransparentType("flag", am.NodeType("FlagValue"))
        assert set(model.value_enums) == {"FlagValue"}

    def test_a_bool_rule_erases_to_a_plain_boolean(self) -> None:
        model = configured_model(ENUM_GRAMMAR + ITEM_TAIL, "rule flag { bool: yes; transparent; }")
        assert element_of(model, "target", "f") == am.TransparentType("flag", am.BOOL)
        assert model.value_enums == {}

    def test_a_single_field_product_erases_to_its_field(self) -> None:
        model = configured_model(WRAPPER_GRAMMAR, "rule wrap { transparent; }")
        assert element_of(model, "target", "w") == am.TransparentType("wrap", am.NodeType("Item"))

    def test_the_erased_products_node_keeps_the_field_for_its_converter(self) -> None:
        """No public field is emitted, so the field is named uniformly rather than after its label."""
        model = configured_model(WRAPPER_GRAMMAR, "rule wrap { transparent; }")
        node = model.nodes["wrap"]
        assert isinstance(node, am.ProductNode)
        assert [(field.name, field.label) for field in node.fields] == [("value", "only")]

    def test_erasure_is_transitive(self) -> None:
        model = configured_model(WRAPPER_GRAMMAR, "rule wrap { transparent; }\nrule item { transparent; }")
        assert element_of(model, "target", "w") == am.TransparentType("wrap", am.TransparentType("item", am.TEXT))

    def test_a_field_enum_can_be_the_payload(self) -> None:
        model = configured_model(
            "target := w:wrap ;\nwrap := ( only:item | only:other ) ;\n" + ITEM_TAIL,
            "rule wrap { transparent; }",
        )
        assert element_of(model, "target", "w") == am.TransparentType("wrap", am.NodeType("WrapOnly"))
        assert [variant.name for variant in model.field_enums["WrapOnly"].variants] == ["Item", "Other"]

    def test_the_erased_rules_type_name_is_free_for_reuse(self) -> None:
        """Nothing is emitted under it, so another rule may claim the name."""
        model = configured_model(
            "target := x:item . y:thing ;\nthing := z:/[a-z]+/ ;\n" + ITEM_TAIL,
            "rule item { transparent; }\nrule thing { name: Item; }\n",
        )
        assert model.rule_type_names["thing"] == "Item"
        assert element_of(model, "target", "y") == am.NodeType("Item")
        assert element_of(model, "target", "x") == am.TransparentType("item", am.TEXT)

    def test_a_reserved_label_needs_no_rename_once_the_rule_is_erased(self) -> None:
        """The label produces no public field, so it never has to be a usable identifier."""
        assert "every generated node already carries" in errors_for("w:wrap", "wrap := text:item ;\n")[0]
        model = configured_model(
            "target := w:wrap ;\nwrap := text:item ;\n" + ITEM_TAIL,
            "rule wrap { transparent; }",
        )
        assert element_of(model, "target", "w") == am.TransparentType("wrap", am.NodeType("Item"))

    def test_an_erased_direct_sum_payload_carries_the_payload_type(self) -> None:
        model = configured("a:item | b:other", "rule item { transparent; }")
        node = model.nodes["target"]
        assert isinstance(node, am.SumNode)
        assert node.variants[0].payload == am.TransparentType("item", am.TEXT)
        assert node.variants[0].payload_rule == "item"

    def test_two_rules_erasing_to_one_python_type_fall_back_to_payload_classes(self) -> None:
        """Both erase to ``str``, so a union listing it twice could not dispatch either variant."""
        model = configured("a:item | b:other", "rule item { transparent; }\nrule other { transparent; }")
        node = model.nodes["target"]
        assert isinstance(node, am.SumNode)
        assert [payload_name(variant) for variant in node.variants] == ["TargetA", "TargetB"]

    def test_two_integer_widths_collide_on_python_and_demote_both(self) -> None:
        """``i32`` and ``i64`` are distinct Rust types but one ``int``; shapes must stay equal."""
        model = configured_model(
            "target := a:num | b:other ;\nnum := /[0-9]+/ ;\nother := /[0-9]+/ ;\n",
            "rule num { type: i32; transparent; }\nrule other { type: i64; transparent; }",
        )
        node = model.nodes["target"]
        assert isinstance(node, am.SumNode)
        assert [payload_name(variant) for variant in node.variants] == ["TargetA", "TargetB"]

    def test_distinct_payload_types_stay_direct(self) -> None:
        model = configured("a:item | b:other", "rule item { transparent; }\nrule other { type: i64; transparent; }")
        node = model.nodes["target"]
        assert isinstance(node, am.SumNode)
        assert [variant.payload_rule for variant in node.variants] == ["item", "other"]


class TestTransparentErrors:
    """Erasures the model refuses, whether or not the sidecar validator can see them."""

    def test_an_optional_only_field_has_no_single_payload(self) -> None:
        errors = configured_errors(
            "w:wrap",
            "rule wrap { transparent; }",
            "wrap := only:item? ;\n",
        )
        assert len(errors) == 1
        assert "erases the rule to its 'only' field, which is optional" in errors[0]

    def test_a_repeated_only_field_has_no_single_payload(self) -> None:
        errors = configured_errors("w:wrap", "rule wrap { transparent; }", "wrap := only:item* ;\n")
        assert len(errors) == 1
        assert "which is collection" in errors[0]

    def test_a_literal_only_field_carries_no_value(self) -> None:
        errors = configured_errors("w:wrap", "rule wrap { transparent; }", 'wrap := only:"!" . %item ;\n')
        assert len(errors) == 1
        assert "position of the 'only' literal, which carries no value" in errors[0]

    @staticmethod
    def hand_built(text: str, *rule_names: str) -> tuple[str, ...]:
        """Reach the model's own checks past a validator that would reject the sidecar first."""
        config = ac.ResolvedAstConfig(
            rules={name: ac.ResolvedRule(rule_name=name, transparent=True) for name in rule_names}
        )
        with pytest.raises(am.AstModelError) as exc:
            am.build_ast_model(pipeline(parse_grammar(text)), config)
        return exc.value.errors

    def test_a_sum_has_no_common_payload(self) -> None:
        errors = self.hand_built(f"target := s:pick ;\npick := a:item | b:other ;\n{ITEM_TAIL}", "pick")
        assert any("this rule is a sum" in error for error in errors)

    def test_a_multi_field_product_has_no_single_payload(self) -> None:
        errors = self.hand_built(f"target := w:pair ;\npair := a:item . b:other ;\n{ITEM_TAIL}", "pair")
        assert any("exactly one field to erase to, but this rule has 2: a, b" in error for error in errors)

    def test_a_label_free_product_has_no_payload(self) -> None:
        errors = self.hand_built(f"target := w:pair ;\npair := %item . %other ;\n{ITEM_TAIL}", "pair")
        assert any("has 0: (none)" in error for error in errors)

    def test_a_cycle_never_bottoms_out(self) -> None:
        errors = self.hand_built("target := w:one ;\none := v:two ;\ntwo := v:one ;\n", "one", "two")
        assert any("never bottoms out" in error for error in errors)

    def test_an_unresolvable_erasure_is_reported_once(self) -> None:
        """Two use sites of the same broken erasure must not report it twice."""
        errors = self.hand_built(f"target := a:pair . b:pair ;\npair := a:item . b:other ;\n{ITEM_TAIL}", "pair")
        assert len([error for error in errors if "exactly one field" in error]) == 1


class TestBoolMapping:
    """``bool:`` turns an enum-shaped rule's value into a plain boolean."""

    GRAMMAR = 'target := f:flag ;\nflag := yes:"yes" | no:"no" ;\n'

    def test_the_truthy_label_is_recorded(self) -> None:
        node = configured_model(self.GRAMMAR, "rule flag { bool: yes; }").nodes["flag"]
        assert isinstance(node, am.EnumNode)
        assert node.bool_truthy == "yes"
        assert [variant.label for variant in node.value_enum.variants] == ["yes", "no"]

    def test_no_value_enum_is_generated(self) -> None:
        model = configured_model(self.GRAMMAR, "rule flag { bool: yes; }")
        assert model.value_enums == {}

    def test_the_value_enum_name_is_free_for_another_rule(self) -> None:
        """`FlagValue` is not emitted, so claiming it is not a collision."""
        model = configured_model(
            self.GRAMMAR + "other := o:/[a-z]+/ ;\n",
            "rule flag { bool: yes; }\nrule other { name: FlagValue; }\n",
        )
        assert model.rule_type_names["other"] == "FlagValue"

    def test_without_bool_the_value_enum_name_is_taken(self) -> None:
        errors = configured_errors(
            "f:flag",
            "rule spare { name: FlagValue; }",
            'flag := yes:"yes" | no:"no" ;\nspare := o:/[a-z]+/ ;\n',
        )
        assert len(errors) == 1
        assert "'FlagValue'" in errors[0]

    def test_a_variant_rename_on_a_bool_rule_is_a_sidecar_error(self) -> None:
        """The rename would reach nothing: a boolean value has no variants to name."""
        grammar = pipeline(parse_grammar(self.GRAMMAR + ITEM_TAIL))
        with pytest.raises(ac.AstConfigError) as exc:
            ac.load_ast_config("rule flag { bool: yes; variant Yes: Affirmative; }", grammar, {ac.Backend.PYTHON})
        assert "whose value is a plain boolean" in str(exc.value)

    def test_equivalent_spellings_of_the_true_value_are_one_variant(self) -> None:
        """Both spellings map to ``True`` and the false label still supplies ``False``."""
        node = configured_model(
            'target := f:flag ;\nflag := yes:"yes" | yes:"y" | no:"no" ;\n', "rule flag { bool: yes; }"
        ).nodes["flag"]
        assert isinstance(node, am.EnumNode)
        assert [(variant.label, variant.literal) for variant in node.value_enum.variants] == [
            ("yes", "yes"),
            ("no", "no"),
        ]

    def test_a_rule_with_one_variant_cannot_be_a_boolean(self) -> None:
        """Its ``False`` would name no alternative; the validator says so with a sidecar span."""
        grammar = pipeline(parse_grammar('target := f:flag ;\nflag := yes:"yes" | yes:"y" ;\n' + ITEM_TAIL))
        with pytest.raises(ac.AstConfigError) as exc:
            ac.load_ast_config("rule flag { bool: yes; }", grammar, {ac.Backend.PYTHON})
        assert "exactly two variants" in str(exc.value)
        assert "has 1 (yes)" in str(exc.value)

    def test_the_model_backstops_the_variant_count(self) -> None:
        """A hand-built resolved config reaches past the validator."""
        grammar = pipeline(parse_grammar('target := f:flag ;\nflag := yes:"yes" | yes:"y" ;\n' + ITEM_TAIL))
        config = ac.ResolvedAstConfig(rules={"flag": ac.ResolvedRule(rule_name="flag", bool_truthy="yes")})
        with pytest.raises(am.AstModelError) as exc:
            am.build_ast_model(grammar, config)
        assert "`bool:` needs exactly two variants" in exc.value.errors[0]


# One wrapper carrying a field of every arity, used both required and optional so that the
# degradation an optional site imposes is visible beside the undegraded shape.
FLATTEN_GRAMMAR = """
top   := a:maybe , b:sure ;
maybe := "?" , w:parts? ;
sure  := "!" , w:parts ;
parts := k:word . "=" . v:num , o:num? , flags:flag* , mark:"~"? ;
flag  := f:/[a-z]/ ;
word  := w:/[a-z]+/ ;
num   := d:/[0-9]+/ ;
"""

FLATTEN_CONFIG = "rule parts { flatten; }"


class TestFlatten:
    """``flatten;`` splices a wrapper's fields into the nodes that reference it."""

    def test_the_wrapper_is_recorded_and_emits_no_type(self) -> None:
        model = configured_model(FLATTEN_GRAMMAR, FLATTEN_CONFIG)
        assert model.flattened_rules == frozenset({"parts"})
        assert "parts" in model.nodes
        assert "parts" not in model.public_nodes()

    def test_a_required_site_carries_the_wrappers_own_field_types(self) -> None:
        fields = fields_by_name(configured_model(FLATTEN_GRAMMAR, FLATTEN_CONFIG).nodes["sure"])
        assert fields == {
            "k": am.FieldType(am.NodeType("Word"), am.Container.SINGLE),
            "v": am.FieldType(am.NodeType("Num"), am.Container.SINGLE),
            "o": am.FieldType(am.NodeType("Num"), am.Container.OPTIONAL),
            "flags": am.FieldType(am.NodeType("Flag"), am.Container.COLLECTION),
            "mark": am.FieldType(am.BOOL, am.Container.SINGLE),
        }

    def test_an_optional_site_degrades_only_the_required_fields(self) -> None:
        """A collection, an optional field and a presence flag already have an absent value."""
        fields = fields_by_name(configured_model(FLATTEN_GRAMMAR, FLATTEN_CONFIG).nodes["maybe"])
        assert fields == {
            "k": am.FieldType(am.NodeType("Word"), am.Container.OPTIONAL),
            "v": am.FieldType(am.NodeType("Num"), am.Container.OPTIONAL),
            "o": am.FieldType(am.NodeType("Num"), am.Container.OPTIONAL),
            "flags": am.FieldType(am.NodeType("Flag"), am.Container.COLLECTION),
            "mark": am.FieldType(am.BOOL, am.Container.SINGLE),
        }

    @pytest.mark.parametrize(("rule_name", "expected"), [("sure", False), ("maybe", True)])
    def test_the_hoist_records_the_site_and_what_the_wrapper_requires(self, rule_name: str, expected: bool) -> None:  # noqa: FBT001
        node = configured_model(FLATTEN_GRAMMAR, FLATTEN_CONFIG).nodes[rule_name]
        assert isinstance(node, am.ProductNode)
        (hoist,) = node.hoists
        assert (hoist.rule_name, hoist.label, hoist.optional) == ("parts", "w", expected)
        assert hoist.required == frozenset({"k", "v"})
        assert [field.name for field in hoist.fields] == ["k", "v", "o", "flags", "mark"]

    def test_every_hoisted_field_names_the_wrapper_it_came_through(self) -> None:
        node = configured_model(FLATTEN_GRAMMAR, FLATTEN_CONFIG).nodes["sure"]
        assert isinstance(node, am.ProductNode)
        assert {field.wrapper for field in node.fields} == {"w"}

    @pytest.mark.parametrize(("rule_name", "expected"), [("sure", False), ("maybe", True)])
    def test_the_path_records_each_wrappers_own_optionality(self, rule_name: str, expected: bool) -> None:  # noqa: FBT001
        node = configured_model(FLATTEN_GRAMMAR, FLATTEN_CONFIG).nodes[rule_name]
        assert isinstance(node, am.ProductNode)
        assert {field.hoist for field in node.fields} == {(am.Wrapper(label="w", optional=expected),)}

    def test_the_wrappers_type_name_is_free_for_reuse(self) -> None:
        """Nothing is emitted under it, so another rule may claim the name."""
        model = configured_model(FLATTEN_GRAMMAR, FLATTEN_CONFIG + "\nrule flag { name: Parts; }\n")
        assert model.rule_type_names["flag"] == "Parts"

    def test_hoisting_is_transitive(self) -> None:
        model = configured_model(
            "top := t:outer ;\nouter := i:inner , tail:word ;\ninner := k:word . '=' . v:num ;\n"
            "word := w:/[a-z]+/ ;\nnum := d:/[0-9]+/ ;\n",
            "rule outer { flatten; }\nrule inner { flatten; }\n",
        )
        assert list(fields_by_name(model.nodes["top"])) == ["k", "v", "tail"]

    def test_a_transitive_hoist_carries_the_whole_path(self) -> None:
        """Two wrappers down is two steps: the field is neither on the node nor on the first."""
        model = configured_model(
            "top := t:outer? ;\nouter := i:inner , tail:word ;\ninner := k:word . '=' . v:num ;\n"
            "word := w:/[a-z]+/ ;\nnum := d:/[0-9]+/ ;\n",
            "rule outer { flatten; }\nrule inner { flatten; }\n",
        )
        node = model.nodes["top"]
        assert isinstance(node, am.ProductNode)
        paths = {field.name: field.hoist for field in node.fields}
        assert paths["k"] == (am.Wrapper(label="t", optional=True), am.Wrapper(label="i", optional=False))
        assert paths["tail"] == (am.Wrapper(label="t", optional=True),)

    def test_a_rename_inside_the_wrapper_names_the_hoisted_field(self) -> None:
        model = configured_model(FLATTEN_GRAMMAR, "rule parts { flatten; field k { name: key; } }")
        assert "key" in fields_by_name(model.nodes["sure"])

    def test_a_sum_variant_over_a_wrapper_takes_a_generated_payload(self) -> None:
        """The wrapper has no type, so it cannot be the variant's direct payload."""
        model = configured_model(
            "top := s:choice ;\nchoice := a:wrap | b:num ;\nwrap := k:word . '=' . v:num ;\n"
            "word := w:/[a-z]+/ ;\nnum := d:/[0-9]+/ ;\n",
            "rule wrap { flatten; }",
        )
        node = model.nodes["choice"]
        assert isinstance(node, am.SumNode)
        assert [payload_name(variant) for variant in node.variants] == ["ChoiceA", "Num"]
        assert [field.name for field in model.payload_classes["ChoiceA"].fields] == ["k", "v"]


class TestFlattenErrors:
    """Hoists the model refuses, whether or not the sidecar validator can see them."""

    @staticmethod
    def hand_built(text: str, *rule_names: str) -> tuple[str, ...]:
        """Reach the model's own checks past a validator that would reject the sidecar first."""
        config = ac.ResolvedAstConfig(
            rules={name: ac.ResolvedRule(rule_name=name, flatten=True) for name in rule_names}
        )
        with pytest.raises(am.AstModelError) as exc:
            am.build_ast_model(pipeline(parse_grammar(text)), config)
        return exc.value.errors

    def test_a_collection_site_has_nowhere_to_put_repeated_fields(self) -> None:
        errors = self.hand_built(f"target := xs:pair* ;\npair := a:item . b:other ;\n{ITEM_TAIL}", "pair")
        assert any("has no AST type of its own" in error for error in errors)

    def test_a_label_carrying_a_second_type_cannot_hoist(self) -> None:
        errors = self.hand_built(f"target := ( x:pair | x:item ) ;\npair := a:item . b:other ;\n{ITEM_TAIL}", "pair")
        assert any("carries nothing else" in error for error in errors)

    def test_a_non_product_wrapper_has_no_fields_to_hoist(self) -> None:
        errors = self.hand_built(f"target := s:pick ;\npick := a:item | b:other ;\n{ITEM_TAIL}", "pick")
        assert any("applies only to a product rule" in error for error in errors)
        assert not any("has no AST type of its own" in error for error in errors)

    def test_a_cycle_never_bottoms_out(self) -> None:
        errors = self.hand_built("target := w:one ;\none := v:two ;\ntwo := v:one ;\n", "one", "two")
        assert any("never bottoms out" in error for error in errors)

    def test_a_hoisted_field_colliding_with_a_sibling_is_named(self) -> None:
        errors = configured_errors(
            "a:item . w:pair",
            "rule pair { flatten; }",
            "pair := a:item . b:other ;\n",
        )
        assert len(errors) == 1
        assert "hoisted from the flattened rule 'pair' collides with the field of label 'a'" in errors[0]

    def test_the_wrapper_first_order_reports_the_same_collision(self) -> None:
        """Either declaration order names the wrapper and the rename that fixes it."""
        errors = configured_errors(
            "w:pair . a:item",
            "rule pair { flatten; }",
            "pair := a:item . b:other ;\n",
        )
        assert len(errors) == 1
        assert "hoisted from the flattened rule 'pair' collides with the field of label 'a'" in errors[0]
        assert "rule pair { field a { name: <new>; } }" in errors[0]

    def test_flatten_and_key_cannot_both_apply(self) -> None:
        """A `key:` acts only at a collection use site, which a wrapper can never occupy."""
        config = ac.ResolvedAstConfig(
            rules={"pair": ac.ResolvedRule("pair", flatten=True, key=ac.ResolvedKey(label="a"))}
        )
        with pytest.raises(am.AstModelError) as exc:
            am.build_ast_model(
                pipeline(parse_grammar(f"target := w:pair ;\npair := a:item . b:other ;\n{ITEM_TAIL}")), config
            )
        assert any("`flatten;` and `key:` cannot both apply" in error for error in exc.value.errors)

    def test_two_item_positions_for_one_wrapper_label_have_no_single_home(self) -> None:
        """The alternation's branches are one field, but the wrapper is rebuilt at one position."""
        errors = configured_errors(
            "( w:pair | w:pair )",
            "rule pair { flatten; }",
            "pair := a:item . b:other ;\n",
        )
        assert any("matched by more than one item position" in error for error in errors)

    def test_flatten_cannot_combine_with_transparent(self) -> None:
        config = ac.ResolvedAstConfig(rules={"pair": ac.ResolvedRule("pair", flatten=True, transparent=True)})
        with pytest.raises(am.AstModelError) as exc:
            am.build_ast_model(
                pipeline(parse_grammar(f"target := w:pair ;\npair := a:item . b:other ;\n{ITEM_TAIL}")), config
            )
        assert any("cannot combine with `transparent;`" in error for error in exc.value.errors)

    def test_a_transparent_rule_cannot_erase_to_a_wrapper(self) -> None:
        errors = configured_errors(
            "w:hold",
            "rule pair { flatten; }\nrule hold { transparent; }\n",
            "hold := p:pair ;\npair := a:item . b:other ;\n",
        )
        assert any("has no AST type of its own" in error for error in errors)


class TestCstBackpointers:
    """``option cst = true;`` reaches the model as one flag, and reserves one member name."""

    def test_the_option_is_recorded(self) -> None:
        assert configured("x:item", "option cst = true;").cst_backpointers is True

    def test_off_by_default(self) -> None:
        assert configured("x:item", "").cst_backpointers is False
        assert configured("x:item", "option cst = false;").cst_backpointers is False

    def test_a_cst_label_is_reserved_only_while_the_option_is_on(self) -> None:
        """The member exists only under the option, so Tier 0 must keep the label usable."""
        assert fields_by_name(configured("cst:item", "").nodes["target"]).keys() == {"cst"}
        errors = configured_errors("cst:item", "option cst = true;")
        assert len(errors) == 1
        assert "the CST back-pointer member `option cst = true;` adds" in errors[0]

    def test_a_field_rename_is_the_fix(self) -> None:
        model = configured("cst:item", "option cst = true;\nrule target { field cst { name: node; } }")
        assert fields_by_name(model.nodes["target"]).keys() == {"node"}


# A keyed element rule (`entry`, keyed by its `name` field) reached at every arity: a
# collection, an optional single and a required single.
KEYED_GRAMMAR = """
top   := e:entry* , o:entry? , r:entry ;
entry := name:word , "=" , v:num ;
word  := w:/[a-z]+/ ;
num   := d:/[0-9]+/ ;
"""

KEYED_CONFIG = "rule word { transparent; }\nrule entry { key: name; }\n"

MULTI_CONFIG = "rule word { transparent; }\nrule entry { key: name multi; }\n"


class TestKeyedCollections:
    """``key:`` turns every collection use site of the element rule into a map."""

    def test_a_collection_use_site_becomes_a_map(self) -> None:
        field = fields_by_name(configured_model(KEYED_GRAMMAR, KEYED_CONFIG).nodes["top"])["e"]
        assert field.container is am.Container.MAP
        assert field.key == am.MapKey(
            rule_name="entry", label="name", field_name="name", element=am.TransparentType("word", am.TEXT)
        )

    def test_multi_keeps_the_map_container_and_records_the_accumulation(self) -> None:
        """``multi`` alters what a key holds, so only the key says which of the two forms it is."""
        field = fields_by_name(configured_model(KEYED_GRAMMAR, MULTI_CONFIG).nodes["top"])["e"]
        assert field.container is am.Container.MAP
        assert field.key == am.MapKey(
            rule_name="entry",
            label="name",
            field_name="name",
            element=am.TransparentType("word", am.TEXT),
            multi=True,
        )

    def test_single_use_sites_are_untouched(self) -> None:
        fields = fields_by_name(configured_model(KEYED_GRAMMAR, KEYED_CONFIG).nodes["top"])
        assert fields["r"].container is am.Container.SINGLE
        assert fields["o"].container is am.Container.OPTIONAL
        assert (fields["r"].key, fields["o"].key) == (None, None)

    def test_the_key_field_stays_a_field_of_the_element(self) -> None:
        fields = fields_by_name(configured_model(KEYED_GRAMMAR, KEYED_CONFIG).nodes["entry"])
        assert fields["name"] == am.FieldType(am.TransparentType("word", am.TEXT), am.Container.SINGLE)

    def test_an_erased_key_field_resolves_through_to_text(self) -> None:
        field = fields_by_name(configured_model(KEYED_GRAMMAR, KEYED_CONFIG).nodes["top"])["e"]
        assert field.key is not None
        assert field.key.element == am.TransparentType("word", am.TEXT)

    def test_a_labeled_regex_keys_directly(self) -> None:
        model = configured_model(KEYED_GRAMMAR.replace("name:word", "name:/[a-z]+/"), "rule entry { key: name; }")
        field = fields_by_name(model.nodes["top"])["e"]
        assert field.key is not None
        assert field.key.element == am.TEXT

    def test_an_integer_coercion_keys_as_that_builtin(self) -> None:
        model = configured_model(
            KEYED_GRAMMAR,
            "rule num { type: u32; transparent; }\nrule entry { key: v; }\n",
        )
        field = fields_by_name(model.nodes["top"])["e"]
        assert field.key is not None
        assert field.key.element == am.TransparentType("num", am.TEXT, am.BuiltinCoercion("u32"))

    def test_a_renamed_key_field_is_named_by_its_new_name(self) -> None:
        """Both directions read the key off the element, so the member is what they need."""
        model = configured_model(
            KEYED_GRAMMAR,
            "rule word { transparent; }\nrule entry { key: name; field name { name: ident; } }\n",
        )
        field = fields_by_name(model.nodes["top"])["e"]
        assert field.key is not None
        assert (field.key.label, field.key.field_name) == ("name", "ident")

    def test_a_label_carrying_two_element_types_stays_a_plain_collection(self) -> None:
        """A field enum has no single key field, so the label keeps its list container."""
        model = configured_model(
            "top := e:entry* , e:other* ;\nentry := name:word ;\nother := o:num ;\n"
            "word := w:/[a-z]+/ ;\nnum := d:/[0-9]+/ ;\n",
            KEYED_CONFIG,
        )
        field = fields_by_name(model.nodes["top"])["e"]
        assert field.container is am.Container.COLLECTION
        assert field.key is None

    def test_a_sum_payload_class_gets_the_map_too(self) -> None:
        model = configured_model(
            "top := s:pick ;\npick := a:word , e:entry+ | b:num ;\n"
            'entry := name:word , "=" , v:num ;\nword := w:/[a-z]+/ ;\nnum := d:/[0-9]+/ ;\n',
            KEYED_CONFIG,
        )
        payload = model.payload_classes["PickAlt1"]
        assert {field.name: field.type.container for field in payload.fields}["e"] is am.Container.MAP


class TestKeyedCollectionErrors:
    """Keys the model refuses, whether or not the sidecar validator can see them first."""

    @staticmethod
    def hand_built(text: str, **keys: str) -> tuple[str, ...]:
        """Reach the model's own checks past a validator that would reject the sidecar first."""
        config = ac.ResolvedAstConfig(
            rules={
                name: ac.ResolvedRule(rule_name=name, key=ac.ResolvedKey(label=label)) for name, label in keys.items()
            }
        )
        with pytest.raises(am.AstModelError) as exc:
            am.build_ast_model(pipeline(parse_grammar(text)), config)
        return exc.value.errors

    def test_a_node_typed_key_is_refused(self) -> None:
        errors = self.hand_built(KEYED_GRAMMAR, entry="name")
        assert len(errors) == 1
        assert "does not resolve to a string or an integer" in errors[0]
        assert "mark the referenced rule `transparent;`" in errors[0]

    def test_a_float_coercion_cannot_key(self) -> None:
        grammar = pipeline(parse_grammar(KEYED_GRAMMAR))
        config = ac.ResolvedAstConfig(
            rules={
                "num": ac.ResolvedRule(rule_name="num", coercion=ac.BuiltinScalar("f64"), transparent=True),
                "entry": ac.ResolvedRule(rule_name="entry", key=ac.ResolvedKey(label="v")),
            }
        )
        with pytest.raises(am.AstModelError) as exc:
            am.build_ast_model(grammar, config)
        assert "does not resolve to a string or an integer" in exc.value.errors[0]

    def test_a_sum_rule_has_no_fields_to_key(self) -> None:
        errors = self.hand_built(
            f"top := e:pick* ;\npick := a:item | b:other ;\n{ITEM_TAIL}",
            pick="a",
        )
        assert any("`key:` applies only to a product rule" in error for error in errors)

    def test_an_unknown_label_is_refused(self) -> None:
        errors = self.hand_built(KEYED_GRAMMAR.replace("name:word", "%word"), entry="name")
        assert any("names no field of this rule — its fields are: v" in error for error in errors)

    def test_an_optional_key_field_is_refused(self) -> None:
        errors = self.hand_built(KEYED_GRAMMAR.replace("name:word ,", "name:word? ,"), entry="name")
        assert any("only a field occurring exactly once can key a map" in error for error in errors)

    def test_an_erased_element_rule_has_no_key_field(self) -> None:
        grammar = pipeline(parse_grammar("top := e:entry* ;\nentry := name:/[a-z]+/ ;\n"))
        config = ac.ResolvedAstConfig(
            rules={"entry": ac.ResolvedRule(rule_name="entry", key=ac.ResolvedKey(label="name"), transparent=True)}
        )
        with pytest.raises(am.AstModelError) as exc:
            am.build_ast_model(grammar, config)
        assert "`key:` and `transparent;` cannot both apply" in exc.value.errors[0]

    def test_a_broken_key_is_reported_once(self) -> None:
        """Two collection use sites of one keyed rule must not report the same problem twice."""
        errors = self.hand_built(
            "top := a:entry* , b:entry* ;\nentry := name:word ;\nword := w:/[a-z]+/ ;\n", entry="name"
        )
        assert len(errors) == 1


def fold_node(model: am.AstModel, rule_name: str) -> am.FoldNode:
    node = model.nodes[rule_name]
    assert isinstance(node, am.FoldNode)
    return node


class TestFoldForm:
    """``fold_left:``/``fold_right:`` replaces a rule's product shape with a chain."""

    def test_the_rule_becomes_a_fold_node(self) -> None:
        node = fold_node(configured_model(FOLD_GRAMMAR, FOLD_SIDECAR), "expr")
        assert (node.name, node.direction) == ("Expr", ac.FoldDirection.LEFT)
        assert (node.operand_variant, node.binary_variant) == ("Operand", "Binary")

    def test_the_direction_is_recorded(self) -> None:
        config = FOLD_SIDECAR.replace("rule expr       { fold_left: op; }", "rule expr { fold_right: op; }")
        assert fold_node(configured_model(FOLD_GRAMMAR, config), "expr").direction is ac.FoldDirection.RIGHT

    def test_the_link_carries_the_operator_once(self) -> None:
        binary = fold_node(configured_model(FOLD_GRAMMAR, FOLD_SIDECAR), "expr").binary
        assert binary.name == "ExprBinary"
        assert binary.op.name == "op"
        operator = am.TransparentType("add_op", am.NodeType("AddOpValue"))
        assert binary.op.type == am.FieldType(operator, am.Container.SINGLE)

    def test_the_operand_and_operators_are_the_flattened_chain(self) -> None:
        node = fold_node(configured_model(FOLD_GRAMMAR, FOLD_SIDECAR), "expr")
        assert node.operand.label == "term"
        assert node.operand.type == am.FieldType(am.NodeType("Term"), am.Container.COLLECTION)
        assert node.operators.type.container is am.Container.COLLECTION
        assert node.operators.type.element == node.binary.op.type.element

    def test_the_operand_type_resolves_through_erasure(self) -> None:
        """A ``transparent;`` operand hands its payload straight to the chain's leaves."""
        model = configured(
            "e:expr",
            "rule expr { fold_left: op; }\nrule word { transparent; }\n",
            "expr := w:word , ( , op:other , w:word)* ;\nword := t:/[a-z]+/ ;\n",
        )
        assert fold_node(model, "expr").operand.type.element == am.TransparentType("word", am.TEXT)

    def test_a_fold_is_reachable_as_a_sum_payload(self) -> None:
        """``factor``'s ``paren`` variant carries the erased wrapper's ``Expr`` chain."""
        model = configured_model(FOLD_GRAMMAR, FOLD_SIDECAR)
        node = model.nodes["factor"]
        assert isinstance(node, am.SumNode)
        payloads = {variant.name: variant.payload for variant in node.variants}
        assert payloads["Paren"] == am.TransparentType("paren_expr", am.NodeType("Expr"))
        assert fold_node(model, "term").operand.type.element == am.NodeType("Factor")

    def test_the_link_name_is_claimed_globally(self) -> None:
        errors = configured_errors(
            "e:expr",
            "rule expr { fold_left: op; }\nrule spare { name: ExprBinary; }\n",
            "expr := t:item , ( , op:other , t:item)* ;\nspare := s:/[a-z]+/ ;\n",
        )
        assert len(errors) == 1
        assert "'ExprBinary'" in errors[0]
        assert "the chain link of fold rule 'expr'" in errors[0]

    def test_a_name_override_carries_into_the_link(self) -> None:
        model = configured(
            "e:expr",
            "rule expr { fold_left: op; name: Sum; }",
            "expr := t:item , ( , op:other , t:item)* ;\n",
        )
        node = fold_node(model, "expr")
        assert (node.name, node.binary.name) == ("Sum", "SumBinary")

    def test_variant_renames_apply_to_both_variants(self) -> None:
        model = configured(
            "e:expr",
            "rule expr { fold_left: op; variant Operand: Leaf; variant Binary: Chain; }",
            "expr := t:item , ( , op:other , t:item)* ;\n",
        )
        node = fold_node(model, "expr")
        assert (node.operand_variant, node.binary_variant) == ("Leaf", "Chain")
        assert node.binary.name == "ExprChain"

    def test_an_unknown_variant_selector_is_refused(self) -> None:
        errors = configured_errors(
            "e:expr",
            "rule expr { fold_left: op; variant Alt1: Chain; }",
            "expr := t:item , ( , op:other , t:item)* ;\n",
        )
        assert len(errors) == 1
        assert "the computed variant names are: Operand, Binary" in errors[0]

    def test_a_field_rename_names_the_operator_member(self) -> None:
        model = configured(
            "e:expr",
            "rule expr { fold_left: op; field op { name: operator; } }",
            "expr := t:item , ( , op:other , t:item)* ;\n",
        )
        assert fold_node(model, "expr").binary.op.name == "operator"

    def test_a_labeled_regex_operand_carries_text(self) -> None:
        model = configured(
            "e:expr",
            "rule expr { fold_left: op; }",
            "expr := t:/[a-z]+/ , ( , op:other . t:/[a-z]+/)* ;\n",
        )
        node = fold_node(model, "expr")
        assert node.operand.type.element == am.TEXT
        assert model.plans["expr"].alternatives[0].slots[0].kind is am.SlotKind.TEXT


class TestFoldErrors:
    """Shapes a fold cannot be built on, whether or not the validator sees them first."""

    @staticmethod
    def hand_built(text: str, rule_name: str, op_label: str, **extra: object) -> tuple[str, ...]:
        """Reach the model's own checks past a validator that would reject the sidecar first."""
        config = ac.ResolvedAstConfig(
            rules={
                rule_name: ac.ResolvedRule(
                    rule_name=rule_name,
                    fold=ac.Fold(direction=ac.FoldDirection.LEFT, op_label=op_label),
                    **extra,  # type: ignore[arg-type]
                )
            }
        )
        with pytest.raises(am.AstModelError) as exc:
            am.build_ast_model(pipeline(parse_grammar(text)), config)
        return exc.value.errors

    def test_a_multi_alternative_rule_cannot_fold(self) -> None:
        errors = self.hand_built(
            f"target := e:expr ;\nexpr := t:item | t:item , ( , op:other , t:item)+ ;\n{ITEM_TAIL}", "expr", "op"
        )
        assert any("needs a single-alternative rule" in error for error in errors)

    def test_a_third_label_cannot_fold(self) -> None:
        errors = self.hand_built(
            f"target := e:expr ;\nexpr := t:item , x:other , ( , op:other , t:item)* ;\n{ITEM_TAIL}", "expr", "op"
        )
        assert any("whose only two labels are the operand and the operator" in error for error in errors)

    def test_an_unknown_operator_label_cannot_fold(self) -> None:
        errors = self.hand_built(
            f"target := e:expr ;\nexpr := t:item , ( , op:other , t:item)* ;\n{ITEM_TAIL}", "expr", "nope"
        )
        assert any("whose only two labels are the operand and the operator" in error for error in errors)

    def test_a_non_repeatable_operator_cannot_fold(self) -> None:
        errors = self.hand_built(f"target := e:expr ;\nexpr := t:item , op:other , t:item ;\n{ITEM_TAIL}", "expr", "op")
        assert any("must be repeatable" in error for error in errors)

    def test_an_optional_operand_cannot_fold(self) -> None:
        errors = self.hand_built(f"target := e:expr ;\nexpr := ( , op:other , t:item)* ;\n{ITEM_TAIL}", "expr", "op")
        assert any("must occur one or more times" in error for error in errors)

    def test_an_unlabeled_included_item_has_no_place_in_the_walk(self) -> None:
        errors = self.hand_built(
            f'target := e:expr ;\nexpr := t:item , ( , op:other , $"," , t:item)* ;\n{ITEM_TAIL}', "expr", "op"
        )
        assert any("every included item must be labeled" in error for error in errors)

    def test_an_alternation_over_one_label_has_no_single_position(self) -> None:
        errors = self.hand_built(
            f"target := e:expr ;\nexpr := t:item , ( , (op:other | op:item) , t:item)* ;\n{ITEM_TAIL}", "expr", "op"
        )
        assert any("do not all accept the same values" in error for error in errors)

    def test_an_alternation_of_two_literal_operators_has_no_single_position(self) -> None:
        """Both positions are a bare span, so nothing records which operator a link carried."""
        errors = self.hand_built(
            f'target := e:expr ;\nexpr := t:item , ( , (op:"+" | op:"-") , t:item)* ;\n{ITEM_TAIL}', "expr", "op"
        )
        assert any("the fold label 'op' is matched by item positions" in error for error in errors)

    def test_an_alternation_of_two_regex_operators_has_no_single_position(self) -> None:
        """One pattern would validate every value, so the other branch's text could not render."""
        errors = self.hand_built(
            f"target := e:expr ;\nexpr := t:item , ( , (op:/[+]/ | op:/[-]/) , t:item)* ;\n{ITEM_TAIL}", "expr", "op"
        )
        assert any("the fold label 'op' is matched by item positions" in error for error in errors)

    def test_two_positions_of_one_pattern_are_still_one_position(self) -> None:
        """The ordinary fold shape repeats the operand's own terminal; that is not an alternation."""
        model = configured(
            "e:expr",
            "rule expr { fold_left: op; }",
            "expr := t:/[a-z]+/ , ( , op:/[+-]/ . t:/[a-z]+/)* ;\n",
        )
        assert fold_node(model, "expr").operand.type.element == am.TEXT

    def test_flatten_cannot_combine_with_a_fold(self) -> None:
        errors = self.hand_built(
            f"target := e:expr ;\nexpr := t:item , ( , op:other , t:item)* ;\n{ITEM_TAIL}",
            "expr",
            "op",
            flatten=True,
        )
        assert any("cannot combine with a fold" in error for error in errors)

    def test_both_fold_variants_renamed_to_one_name_collide(self) -> None:
        errors = configured_errors(
            "e:expr",
            "rule expr { fold_left: op; variant Operand: Leaf; variant Binary: Leaf; }",
            "expr := t:item , ( , op:other , t:item)* ;\n",
        )
        assert any("both fold variants are named 'Leaf'" in error for error in errors)

    def test_transparent_cannot_erase_a_fold(self) -> None:
        errors = self.hand_built(
            f"target := e:expr ;\nexpr := t:item , ( , op:other , t:item)* ;\n{ITEM_TAIL}",
            "expr",
            "op",
            transparent=True,
        )
        assert any("`transparent;` cannot apply to a fold rule" in error for error in errors)

    def test_an_operator_named_lhs_collides_with_the_link(self) -> None:
        errors = self.hand_built(
            f"target := e:expr ;\nexpr := t:item , ( , lhs:other , t:item)* ;\n{ITEM_TAIL}", "expr", "lhs"
        )
        assert any("collides with the lhs/rhs members" in error for error in errors)

    def test_an_unfoldable_rule_is_reported_once(self) -> None:
        """The identity walk asks for the shape as well as the builder."""
        errors = self.hand_built(
            f"target := p:pick ;\npick := e:expr | n:other ;\nexpr := t:item , op:other , t:item ;\n{ITEM_TAIL}",
            "expr",
            "op",
        )
        assert len([error for error in errors if "must be repeatable" in error]) == 1

    def test_a_renamed_operand_reaches_no_field(self) -> None:
        errors = configured_errors(
            "e:expr",
            "rule expr { fold_left: op; field t { name: operand; } }",
            "expr := t:item , ( , op:other , t:item)* ;\n",
        )
        assert len(errors) == 1
        assert "renames no field of this rule" in errors[0]
        assert "a fold's operand" in errors[0]


def runs_for(body: str, config_text: str = "", extra_rules: str = "") -> tuple[am.SlotRun, ...]:
    """The synthesis runs of ``target``'s first alternative."""
    model = configured(body, config_text, extra_rules) if config_text else model_for(body, extra_rules)
    return am.synthesis_runs(model, model.plans["target"].alternatives[0])


def guards_for(body: str, config_text: str = "", extra_rules: str = "") -> list[am.Guard]:
    """Every run's guards, in the order each run tests them."""
    return [placement.guard for run in runs_for(body, config_text, extra_rules) for placement in run.placements]


class TestSynthesisRuns:
    """Which item position takes which of a label's values, and what it takes it on."""

    def test_a_position_outside_an_alternation_is_its_own_run(self) -> None:
        runs = runs_for("x:item . y:other")
        assert [run.label for run in runs] == ["x", "y"]
        assert [(run.dispatched, run.minimum, run.maximum, run.reserve) for run in runs] == [
            (False, 1, 1, 0),
            (False, 1, 1, 0),
        ]

    def test_rival_branches_of_one_alternation_become_a_dispatch_run(self) -> None:
        (run,) = runs_for("( a:item | a:other )*")
        assert run.dispatched
        assert [placement.slot.rule_name for placement in run.placements] == ["item", "other"]
        assert (run.minimum, run.maximum) == (0, math.inf)

    def test_branches_that_accept_the_same_values_do_not_dispatch(self) -> None:
        """Nothing records which branch a value came from, so nothing could route it."""
        runs = runs_for("( a:item | a:item )")
        assert [run.dispatched for run in runs] == [False, False]
        assert [run.minimum for run in runs] == [0, 0]

    def test_two_literal_branches_stay_rival_positions(self) -> None:
        """A labeled literal's text is left out of the signature: the AST records a position.

        The group is optional, so the label's datum is presence rather than which spelling was
        written — the shape where two literal spellings under one label are legitimate.
        """
        runs = runs_for('( a:"yes" | a:"no" )?')
        assert [run.dispatched for run in runs] == [False, False]

    def test_two_regex_branches_dispatch_on_their_patterns(self) -> None:
        (run,) = runs_for("( a:/[0-9]+/ | a:/[a-z]+/ )")
        assert run.dispatched
        assert [placement.guard for placement in run.placements] == [
            am.Guard(am.GuardKind.PATTERN, pattern="[0-9]+"),
            am.Guard(am.GuardKind.PATTERN, pattern="[a-z]+"),
        ]

    def test_the_maximum_is_the_most_a_single_branch_accepts(self) -> None:
        (run,) = runs_for("( a:item . a:item | a:other )")
        assert (run.maximum, run.minimum) == (2, 1)

    def test_a_later_position_of_the_same_kind_reserves_a_value(self) -> None:
        runs = runs_for("x:/[a-z]+/ . x:/[0-9]+/")
        assert [run.reserve for run in runs] == [1, 0]

    def test_a_rival_branch_reserves_nothing(self) -> None:
        """Only one branch is ever taken, so neither has to leave the other any values."""
        assert [run.reserve for run in runs_for("( a:item | a:item )")] == [0, 0]

    def test_a_later_position_of_another_kind_reserves_nothing_from_a_lone_position(self) -> None:
        assert [run.reserve for run in runs_for("a:item . a:/[0-9]+/")] == [0, 0]

    def test_a_dispatch_run_reserves_content_blind(self) -> None:
        """Its own branches have already sorted the values by what accepts them."""
        runs = runs_for("( a:item | a:other )* . a:/[0-9]+/")
        assert runs[0].dispatched
        assert [run.reserve for run in runs] == [1, 0]

    def test_a_lone_position_needs_no_guard(self) -> None:
        assert guards_for("x:item . y:other") == [am.NO_GUARD, am.NO_GUARD]

    def test_rival_sequential_positions_guard_by_kind(self) -> None:
        """A text position reports its own terminal mismatch; a literal renders from the grammar."""
        assert guards_for('x:"null" . x:/[0-9]+/') == [
            am.Guard(am.GuardKind.LITERAL, literal="null"),
            am.Guard(am.GuardKind.TEXT),
        ]

    def test_a_node_position_guards_on_the_referenced_rule(self) -> None:
        assert guards_for("a:item . a:/[0-9]+/") == [
            am.Guard(am.GuardKind.NODE, rule_name="item"),
            am.Guard(am.GuardKind.TEXT),
        ]

    def test_an_erased_terminal_rule_is_guarded_by_its_own_converter(self) -> None:
        """Two rules erased to plain text share a type, so only their terminals tell them apart."""
        guards = guards_for(
            "( a:word | a:digits )",
            "rule word { transparent; }\nrule digits { transparent; type: i64; }\n",
            "word := w:/[a-z]+/ ;\ndigits := d:/[0-9]+/ ;\n",
        )
        assert guards == [
            am.Guard(am.GuardKind.CONVERTIBLE, rule_name="word"),
            am.Guard(am.GuardKind.CONVERTIBLE, rule_name="digits"),
        ]

    def test_a_custom_coerced_rule_is_guarded_by_its_declared_type(self) -> None:
        """The user's unparse function is written for one type; probing it with another is not safe."""
        config = (
            'rule money { transparent; type: custom(py_type: "m.Money", py_parse: "m.parse", '
            'py_unparse: "m.render"); }\nrule word { transparent; }\n'
        )
        guards = guards_for(
            "( a:money | a:word )",
            config,
            "money := m:/[0-9]+/ ;\nword := w:/[a-z]+/ ;\n",
        )
        assert guards == [
            am.Guard(am.GuardKind.NODE, rule_name="money"),
            am.Guard(am.GuardKind.CONVERTIBLE, rule_name="word"),
        ]

    def test_a_boolean_branch_is_tested_before_an_integer_one(self) -> None:
        """Python's ``bool`` is an ``int``, so the integer branch would take a ``True`` as 1."""
        (run,) = runs_for(
            "( a:digits | a:flag )",
            "rule digits { transparent; type: i64; }\nrule flag { bool: yes; transparent; }\n",
            'digits := d:/[0-9]+/ ;\nflag := yes:"yes" | no:"no" ;\n',
        )
        assert [placement.slot.rule_name for placement in run.placements] == ["flag", "digits"]
        assert [slot.rule_name for slot in run.slots] == ["digits", "flag"]

    def test_an_erased_wrapper_over_a_scalar_is_guarded_by_its_own_converter(self) -> None:
        """Transparency resolves transitively, so the guard has to look at the resolved payload.

        ``wrap`` is a product, but what its use sites carry is ``small``'s integer — a type test
        would accept every integer and then refuse the ones only ``big``'s terminal matches.
        """
        config = (
            "rule wrap { transparent; }\nrule small { transparent; type: i32; }\nrule big { transparent; type: i64; }\n"
        )
        guards = guards_for(
            "( a:wrap | a:big )",
            config,
            'wrap := "(" . v:small . ")" ;\nsmall := s:/[0-9][0-9]/ ;\nbig := b:/[0-9]+/ ;\n',
        )
        assert guards == [
            am.Guard(am.GuardKind.CONVERTIBLE, rule_name="wrap"),
            am.Guard(am.GuardKind.CONVERTIBLE, rule_name="big"),
        ]

    def test_an_erased_value_enum_still_guards_on_its_type(self) -> None:
        """A value enum is a concrete class, so there is nothing a converter probe would add."""
        guards = guards_for(
            "( a:flag | a:word )",
            "rule flag { transparent; }\nrule word { transparent; }\n",
            'flag := yes:"yes" | no:"no" ;\nword := w:/[a-z]+/ ;\n',
        )
        assert guards == [
            am.Guard(am.GuardKind.NODE, rule_name="flag"),
            am.Guard(am.GuardKind.CONVERTIBLE, rule_name="word"),
        ]

    def test_an_unlabeled_position_carries_its_grammar_minimum(self) -> None:
        runs = runs_for('x:item . $"!"')
        assert runs[1].slots[0].kind is am.SlotKind.UNLABELED
        assert runs[1].minimum == 1


class TestIndistinguishableBranches:
    """Two branches of one alternation whose values carry no trace of which they came from."""

    BOOL_RULES = 'yn := y:"yes" | n:"no" ;\ntf := t:"true" | f:"false" ;\n'
    BOOL_CONFIG = "rule yn { bool: y; transparent; }\nrule tf { bool: t; transparent; }\n"

    def test_two_erased_booleans_under_one_label_are_refused(self) -> None:
        errors = configured_errors("( a:yn | a:tf )", self.BOOL_CONFIG, self.BOOL_RULES)
        assert len(errors) == 1
        assert "the 'a' branches referencing 'yn' and 'tf' both carry bool" in errors[0]
        assert "give each branch its own label" in errors[0]

    def test_dropping_transparency_from_one_makes_them_distinguishable(self) -> None:
        """The fix the message names: one branch then carries a node of its own."""
        model = configured(
            "( a:yn | a:tf )", "rule yn { bool: y; transparent; }\nrule tf { bool: t; }\n", self.BOOL_RULES
        )
        assert am.accepted_identities(model, "tf") == frozenset({("generated", "Tf")})

    def test_two_custom_rules_naming_one_class_are_refused(self) -> None:
        config = (
            'rule one { transparent; type: custom(py_type: "m.Money", py_parse: "m.p", py_unparse: "m.r"); }\n'
            'rule two { transparent; type: custom(py_type: "m.Money", py_parse: "m.p", py_unparse: "m.r"); }\n'
        )
        errors = configured_errors("( a:one | a:two )", config, "one := a:/[0-9]+/ ;\ntwo := b:/[a-z]+/ ;\n")
        assert len(errors) == 1
        assert "both carry m.Money" in errors[0]

    def test_a_branch_whose_sum_already_carries_the_other_is_refused(self) -> None:
        """Overlap is enough: the sum's ``isinstance`` test takes the sibling's values too."""
        errors = errors_for("( a:expr | a:item )", "expr := w:item | n:other ;\n")
        assert len(errors) == 1
        assert "'expr' and 'item' both carry Item" in errors[0]

    def test_branches_carrying_distinct_node_types_are_fine(self) -> None:
        assert isinstance(node_for("( a:item | a:other )"), am.ProductNode)

    def test_two_positions_referencing_one_rule_are_fine(self) -> None:
        """They append the same child either way, so which of them takes a value is not observable."""
        assert isinstance(node_for("( a:item . a:item | a:other )"), am.ProductNode)


PRODUCT_SIDECAR = "rule target { product; }\n"
"""Keeps a rule whose alternatives are disjoint a merged product, which is where the union
label — one field, several kinds — lives."""


def selection_for(body: str, config_text: str = "", extra_rules: str = "") -> list[tuple[am.SelectionGuard, ...]]:
    """Every alternative's selection guards, in grammar order."""
    model = configured(body, config_text, extra_rules) if config_text else model_for(body, extra_rules)
    node = model.nodes["target"]
    assert isinstance(node, am.ProductNode)
    return [am.selection_guards(model, node.fields, plan) for plan in model.plans["target"].alternatives]


def accepted_elements(guards: tuple[am.SelectionGuard, ...]) -> dict[str, list[am.ElementType]]:
    """One alternative's guards as label -> the kinds it accepts, in test order."""
    return {guard.label: [kind.element for kind in guard.accepted] for guard in guards}


class TestSelectionGuards:
    """What a value's kinds say about which alternative can rebuild it."""

    UNION_LABEL = "x:item | x:other | x:/[!@#$]+/"

    def test_each_alternative_of_a_union_label_accepts_its_own_kind(self) -> None:
        """The shape name-only selection cannot see: one field, three kinds, one per alternative."""
        assert [accepted_elements(guards) for guards in selection_for(self.UNION_LABEL, PRODUCT_SIDECAR)] == [
            {"x": [am.NodeType("Item")]},
            {"x": [am.NodeType("Other")]},
            {"x": [am.TEXT]},
        ]

    def test_each_accepted_kind_carries_the_test_an_untagged_value_needs(self) -> None:
        """A backend without a tag on the value tests the value, with the dispatch guards."""
        guards = selection_for(self.UNION_LABEL, PRODUCT_SIDECAR)
        assert [[kind.guard for kind in guard.accepted] for alternative in guards for guard in alternative] == [
            [am.Guard(am.GuardKind.NODE, rule_name="item")],
            [am.Guard(am.GuardKind.NODE, rule_name="other")],
            [am.Guard(am.GuardKind.TEXT)],
        ]

    def test_an_alternative_accepting_every_kind_the_field_holds_is_unguarded(self) -> None:
        """The test would be vacuous, and its absence keeps today's selection code unchanged."""
        assert selection_for("x:item . x:other | x:other . x:item") == [(), ()]

    def test_a_field_holding_one_kind_is_unguarded(self) -> None:
        """The merged product: the alternatives differ by label set, which names already decide."""
        assert selection_for("x:item | x:item , y:other") == [(), ()]

    def test_a_label_the_alternative_omits_is_unguarded(self) -> None:
        """A populated field it cannot carry already fails the name test."""
        guards = selection_for("x:item . x:other . y:item | y:other", PRODUCT_SIDECAR)
        assert [accepted_elements(alternative) for alternative in guards] == [
            {"y": [am.NodeType("Item")]},
            {"y": [am.NodeType("Other")]},
        ]

    def test_a_literal_and_a_node_under_one_label_are_kind_distinct(self) -> None:
        """A labeled literal's element is text where the label also carries nodes."""
        assert [accepted_elements(guards) for guards in selection_for('v:"lit" | v:item', PRODUCT_SIDECAR)] == [
            {"v": [am.TEXT]},
            {"v": [am.NodeType("Item")]},
        ]

    def test_a_hoisted_field_is_not_kind_tested(self) -> None:
        """The wrapper occupies one position and places its own fields, so a label it hoists is
        not this rule's to route — even where a field this rule carries itself shares the label,
        which a rename of the hoisted field's name allows."""
        guards = selection_for(
            "w:wrap . k:item | k:other",
            "rule wrap { flatten; field k { name: inner; } }\n" + PRODUCT_SIDECAR,
            "wrap := k:item , k:other ;\n",
        )
        assert [[guard.label for guard in alternative] for alternative in guards] == [["k"], ["k"]]
        assert [accepted_elements(alternative) for alternative in guards] == [
            {"k": [am.NodeType("Item")]},
            {"k": [am.NodeType("Other")]},
        ]

    def test_kinds_a_backend_cannot_tell_apart_are_left_to_the_name_test(self) -> None:
        """Two coercions naming one Python class, with no converter probe to separate them."""
        config = (
            'rule one { transparent; type: custom(py_type: "m.Money", py_parse: "m.p", py_unparse: "m.r"); }\n'
            'rule two { transparent; type: custom(py_type: "m.Money", py_parse: "m.p", py_unparse: "m.r"); }\n'
            + PRODUCT_SIDECAR
        )
        guards = selection_for("x:one | x:two", config, "one := a:/[0-9]+/ ;\ntwo := b:/[a-z]+/ ;\n")
        assert guards == [(), ()]

    def test_a_kind_a_sibling_sum_already_carries_is_left_to_the_name_test(self) -> None:
        """Overlap is enough: a type test for ``item`` takes the values of the sum holding it."""
        guards = selection_for("x:item | x:expr", PRODUCT_SIDECAR, "expr := w:item | n:other ;\n")
        assert guards == [(), ()]

    def test_an_erased_scalar_kind_is_tested_by_its_own_converter(self) -> None:
        """Its values are a bare string on a backend with no tag, so only its terminal says so."""
        guards = selection_for(
            "x:word | x:item",
            "rule word { transparent; }\n" + PRODUCT_SIDECAR,
            "word := w:/[a-z]+/ ;\n",
        )
        assert [[kind.guard for kind in guard.accepted] for alternative in guards for guard in alternative] == [
            [am.Guard(am.GuardKind.CONVERTIBLE, rule_name="word")],
            [am.Guard(am.GuardKind.NODE, rule_name="item")],
        ]

    def test_an_erased_scalar_kind_is_told_from_bare_text_by_its_converter(self) -> None:
        """The shape the probe exists for: both kinds are a bare string where the value carries
        no tag, so an identity test cannot separate them and only the rule's terminal can.  The
        text alternative keeps no guard of its own — bare text is what the erased rule's strings
        are too — so it takes whatever the probe ahead of it declined."""
        guards = selection_for(
            "x:word | x:/[!@#]+/",
            "rule word { transparent; }\n" + PRODUCT_SIDECAR,
            "word := w:/[a-z]+/ ;\n",
        )
        assert [[kind.guard for kind in guard.accepted] for alternative in guards for guard in alternative] == [
            [am.Guard(am.GuardKind.CONVERTIBLE, rule_name="word")]
        ]
        assert guards[1] == ()

    def test_kinds_one_field_enum_variant_name_covers_are_left_to_the_name_test(self) -> None:
        """``a_b`` and ``a__b`` spell one variant name, so a tag cannot say which of them a
        value is, and the converter probe that would otherwise separate them is not enough."""
        guards = selection_for(
            "x:a_b | x:a__b",
            "rule a_b { transparent; }\nrule a__b { transparent; }\n" + PRODUCT_SIDECAR,
            "a_b := p:/[a-z]+/ ;\na__b := q:/[0-9]+/ ;\n",
        )
        assert guards == [(), ()]

    def test_the_kinds_are_ordered_by_the_precedence_a_dispatch_chain_tests_in(self) -> None:
        """Selection offers a value every accepted kind, so the order does not decide which
        alternative wins; it is what keeps both backends emitting one sequence."""
        config = (
            "rule digits { transparent; type: i64; }\nrule flag { bool: yes; transparent; }\n"
            "rule word { transparent; }\n" + PRODUCT_SIDECAR
        )
        extra = 'digits := d:/[0-9]+/ ;\nflag := yes:"yes" | no:"no" ;\nword := w:/[a-z]+/ ;\n'
        first, second = selection_for("x:digits . x:flag | x:word", config, extra)
        assert accepted_elements(first) == {
            "x": [
                am.TransparentType(rule_name="flag", payload=am.BOOL),
                am.TransparentType(rule_name="digits", payload=am.TEXT, coercion=am.BuiltinCoercion("i64")),
            ]
        }
        assert accepted_elements(second) == {"x": [am.TransparentType(rule_name="word", payload=am.TEXT)]}


class TestGroupChecks:
    """What a sub-expression alternation demands of the values reaching it."""

    @staticmethod
    def checks(body: str, config_text: str = "", extra_rules: str = "") -> tuple[am.GroupCheck, ...]:
        model = configured(body, config_text, extra_rules) if config_text else model_for(body, extra_rules)
        node = model.nodes["target"]
        assert isinstance(node, am.ProductNode)
        return am.group_checks(model.plans["target"].alternatives[0], node.fields, node.hoists)

    def test_every_branch_needing_a_value_makes_the_group_demanded(self) -> None:
        (check,) = self.checks("( a:item | b:other )")
        assert check.labels == ("a", "b")
        assert check.branches == (frozenset({"a"}), frozenset({"b"}))
        assert check.demanded
        assert check.exclusive == frozenset({"a", "b"})

    def test_a_branch_of_suppressed_literals_is_not_demanded(self) -> None:
        """That branch renders with nothing populated, so the group may legitimately be empty."""
        (check,) = self.checks('( a:item | %"none" )')
        assert check.branches == (frozenset({"a"}), frozenset())
        assert not check.demanded
        assert check.exclusive == frozenset({"a"})

    def test_a_repeatable_group_claims_no_label_exclusively(self) -> None:
        """It may draw one label's values from several branches in turn."""
        (check,) = self.checks("( a:item | b:other )+")
        assert check.exclusive == frozenset()
        assert check.demanded

    def test_an_optional_group_demands_nothing_but_still_claims_its_labels(self) -> None:
        (check,) = self.checks("( a:item | b:other )?")
        assert not check.demanded
        assert check.exclusive == frozenset({"a", "b"})

    def test_a_label_used_outside_the_group_is_not_exclusive(self) -> None:
        (check,) = self.checks("b:other . ( a:item | b:other )")
        assert check.labels == ("a", "b")
        assert check.exclusive == frozenset({"a"})

    def test_an_alternation_of_unlabeled_items_is_not_checked(self) -> None:
        """Nothing records which branch was written, so there is no state to judge."""
        assert self.checks('x:item . ( $"a" | $"b" )') == ()

    def test_a_group_needing_nothing_and_claiming_nothing_is_not_checked(self) -> None:
        """A repeated group may be empty, and its labels may be filled from any branch."""
        assert self.checks("x:item . ( a:item | b:other )*") == ()

    def test_a_hoisted_wrapper_supplies_its_labels_state(self) -> None:
        checks = self.checks(
            "( w:wrap | b:other )",
            "rule wrap { flatten; }\n",
            "wrap := k:item . v:other ;\n",
        )
        assert [check.labels for check in checks] == [("b", "w")]


class TestInstanceElements:
    """Which concrete types a value of a rule's AST type can have."""

    def test_a_sum_expands_to_its_variant_payloads(self) -> None:
        model = model_for("a:item | b:other")
        assert am.instance_elements(model, "target") == (am.NodeType("Item"), am.NodeType("Other"))

    def test_a_nested_sum_is_expanded(self) -> None:
        """A union alias is a plain string at runtime, so the outer sum needs the inner classes."""
        model = model_for_text(
            f"target := a:inner | b:third ;\ninner := c:item | d:other ;\nthird := t:/[a-z]+/ ;\n{ITEM_TAIL}"
        )
        assert am.instance_elements(model, "target") == (
            am.NodeType("Item"),
            am.NodeType("Other"),
            am.NodeType("Third"),
        )

    def test_an_erased_rule_contributes_its_payload(self) -> None:
        model = configured("w:word", "rule word { transparent; }\n", "word := t:/[a-z]+/ ;\n")
        assert am.instance_elements(model, "word") == (am.TEXT,)

    def test_a_fold_expands_to_its_operand_and_its_link(self) -> None:
        model = configured(
            "e:expr",
            "rule expr { fold_left: op; }\n",
            "expr := t:item , ( , op:other , t:item)* ;\n",
        )
        assert am.instance_elements(model, "expr") == (am.NodeType("Item"), am.NodeType("ExprBinary"))

    def test_an_operand_that_is_itself_a_sum_is_expanded(self) -> None:
        """The chain's leaves are the sum's payloads, not a name that stands for them."""
        elements = am.instance_elements(configured_model(FOLD_GRAMMAR, FOLD_SIDECAR), "term")
        assert elements[-1] == am.NodeType("TermBinary")
        assert am.NodeType("Factor") not in elements
        assert am.TransparentType("number", am.TEXT, am.BuiltinCoercion("i64")) in elements

    def test_a_field_enum_expands_to_its_arms(self) -> None:
        model = model_for("( a:item | a:other )")
        assert am.payload_elements(model, am.NodeType("TargetA")) == (am.NodeType("Item"), am.NodeType("Other"))

    def test_a_value_enum_stands_alone(self) -> None:
        model = model_for_text(f'target := f:flag ;\nflag := on:"on" | off:"off" ;\n{ITEM_TAIL}')
        assert am.payload_elements(model, am.NodeType("FlagValue")) == (am.NodeType("FlagValue"),)

    def test_a_rule_emitting_no_type_has_no_entry_in_the_type_index(self) -> None:
        model = configured("w:word", "rule word { transparent; }\n", "word := t:/[a-z]+/ ;\n")
        assert "Word" not in model.rule_of_type
        assert model.rule_of_type["Target"] == "target"


class TestGeneratedNameCollisions:
    """Every generated module-level name runs through one claim table."""

    def test_an_erased_rule_and_a_field_enum_can_want_one_helper_name(self) -> None:
        errors = configured_errors(
            "e:erased . f:foo",
            "rule foo { transparent; }\n",
            "erased := ( foo:item | foo:other ) ;\nfoo := t:/[a-z]+/ ;\n",
        )
        assert len(errors) == 1
        assert "'_erased_foo_from_cst'" in errors[0]
        assert "the converter of the 'foo' field enum of rule 'erased'" in errors[0]
        assert "collides with the private converters of the erased rule 'foo'" in errors[0]

    def test_a_flattened_rule_and_a_field_enum_can_want_one_helper_name(self) -> None:
        """The flattened prefix was minted alongside the erased one and is the same defect."""
        errors = configured_errors(
            "f:flat . g:foo",
            "rule foo { flatten; }\n",
            "flat := ( foo:item | foo:other ) ;\nfoo := t:item ;\n",
        )
        assert len(errors) == 1
        assert "'_flat_foo_from_cst'" in errors[0]
        assert "the converter of the 'foo' field enum of rule 'flat'" in errors[0]
        assert "collides with the private converters of the flattened rule 'foo'" in errors[0]

    def test_a_renamed_type_can_collide_with_a_converter(self) -> None:
        errors = configured_errors("x:item", "rule item { name: target_from_cst; }\n")
        assert len(errors) == 1
        assert "'target_from_cst'" in errors[0]
        assert "the converters of rule 'target'" in errors[0]
        assert "collides with rule 'item'" in errors[0]

    def test_a_renamed_type_can_collide_with_a_signature_constant(self) -> None:
        """A rename shaped like a per-rule constant clobbers the class at module exec."""
        errors = configured_errors("x:item | y:other", "rule item { name: _TARGET_SIGNATURES; }\n")
        assert len(errors) == 1
        assert "'_TARGET_SIGNATURES'" in errors[0]
        assert "the alternative signatures of rule 'target'" in errors[0]
        assert "collides with rule 'item'" in errors[0]

    def test_a_renamed_type_can_collide_with_a_payload_constant(self) -> None:
        errors = configured_errors("x:item | y:other", "rule item { name: _TARGET_PAYLOADS; }\n")
        assert len(errors) == 1
        assert "the payload table of rule 'target'" in errors[0]
        assert "collides with rule 'item'" in errors[0]

    def test_a_renamed_type_can_collide_with_a_terminal_constant(self) -> None:
        errors = configured_errors("x:item", "rule other { name: _ITEM_TERMINALS; }\n")
        assert len(errors) == 1
        assert "the terminal patterns of rule 'item'" in errors[0]
        assert "collides with rule 'other'" in errors[0]

    def test_a_renamed_type_can_collide_with_the_parse_entry_point(self) -> None:
        errors = configured_errors("x:item", "rule item { name: unparse; }\n")
        assert len(errors) == 1
        assert "the module-level `unparse()` entry point" in errors[0]
        assert "collides with rule 'item'" in errors[0]

    @pytest.mark.parametrize("entry", ["parse_str", "unparse_str"])
    def test_a_renamed_type_can_collide_with_a_rust_entry_point(self, entry: str) -> None:
        """The two backends spell their entry points differently, so both names are claimed."""
        errors = configured_errors("x:item", f"rule item {{ name: {entry}; }}\n")
        assert len(errors) == 1
        assert f"the module-level `{entry}()` entry point" in errors[0]
        assert "collides with rule 'item'" in errors[0]

    def test_the_ordinary_names_do_not_collide(self) -> None:
        model = configured_model(FOLD_GRAMMAR, FOLD_SIDECAR)
        assert set(model.nodes) >= {"expr", "term", "factor"}

    @pytest.mark.parametrize(
        ("enum_name", "converter"),
        [
            ("ErasedFoo", "_erased_foo_from_cst"),
            ("HTTPThingA", "_http_thing_a_from_cst"),
            ("XL", "_xl_from_cst"),
            ("Alt2Foo", "_alt2_foo_from_cst"),
        ],
    )
    def test_a_field_enum_converter_snakes_at_the_same_boundaries_as_an_enum_member(
        self, enum_name: str, converter: str
    ) -> None:
        """One boundary definition serves both snake spellings, so an acronym stays one word."""
        assert am.field_enum_converter_name(enum_name) == converter

    def test_an_acronym_type_name_reaches_the_claim_table_unmangled(self) -> None:
        model = configured("( a:item | a:other )", "rule target { name: HTTPThing; }\n")
        assert "HTTPThingA" in model.field_enums
        assert am.field_enum_converter_name("HTTPThingA") == "_http_thing_a_from_cst"

    def test_a_renamed_type_can_collide_with_an_erased_alternative_helper(self) -> None:
        """A multi-alternative erased product emits one reverse helper per alternative."""
        errors = configured_errors(
            "w:wrapped",
            "rule wrapped { transparent; }\nrule item { name: _erased_wrapped_to_cst_alt0; }\n",
            'wrapped := v:other | "(" . v:other . ")" ;\n',
        )
        assert len(errors) == 1
        assert "'_erased_wrapped_to_cst_alt0'" in errors[0]
        assert "the per-alternative reverse helpers of the erased rule 'wrapped'" in errors[0]
        assert "collides with rule 'item'" in errors[0]

    def test_a_renamed_type_can_collide_with_a_flattened_alternative_helper(self) -> None:
        errors = configured_errors(
            "t:tagged",
            "rule bracket { flatten; }\nrule item { name: _flat_bracket_to_cst_alt0; }\n",
            'tagged := label:other , bracket? ;\nbracket := "[" . n:other . "]" | "{" . n:other . "}" ;\n',
        )
        assert len(errors) == 1
        assert "'_flat_bracket_to_cst_alt0'" in errors[0]
        assert "the per-alternative reverse helpers of the flattened rule 'bracket'" in errors[0]
        assert "collides with rule 'item'" in errors[0]

    def test_a_single_alternative_helper_has_no_suffixed_halves(self) -> None:
        """The suffixed names exist only where a trial picks between alternatives."""
        model = configured("w:wrapped", "rule wrapped { transparent; }\n", "wrapped := v:other ;\n")
        assert "_erased_wrapped_to_cst" in model.claimed_names
        assert "_erased_wrapped_to_cst_alt0" not in model.claimed_names

    def test_a_renamed_type_can_collide_with_a_fold_teardown_witness(self) -> None:
        errors = configured_errors(
            "e:expr",
            "rule expr { fold_left: op; }\nrule item { name: _expr_drop_witness; }\n",
            'expr := d:other , ( , op:sign , d:other)* ;\nsign := p:"+" | m:"-" ;\n',
        )
        assert len(errors) == 1
        assert "'_expr_drop_witness'" in errors[0]
        assert "the teardown witness of fold rule 'expr'" in errors[0]
        assert "collides with rule 'item'" in errors[0]

    def test_a_renamed_type_can_collide_with_the_equality_walk_module(self) -> None:
        """Rust modules and types share a namespace, so the walk's module name is claimed too."""
        errors = configured_errors("x:item", f"rule item {{ name: {am.EQ_SUPPORT_MODULE}; }}\n")
        assert len(errors) == 1
        assert f"the Rust `{am.EQ_SUPPORT_MODULE}` equality-walk module" in errors[0]
        assert "collides with rule 'item'" in errors[0]

    @pytest.mark.parametrize("alias", ["cst", "astrt", "typing", "_parser", "parser"])
    def test_a_renamed_type_can_collide_with_an_import_a_generated_module_binds(self, alias: str) -> None:
        """A class emitted under an import of the same name wins, and every use of it breaks."""
        errors = configured_errors("x:item", f"rule item {{ name: {alias}; }}\n")
        assert len(errors) == 1
        assert f"the `{alias}` a generated module's imports bind" in errors[0]
        assert "collides with rule 'item'" in errors[0]

    def test_a_renamed_type_can_collide_with_a_custom_types_own_import(self) -> None:
        """The head of a `custom(...)` path is imported, so it is a module-level name too."""
        errors = configured_errors(
            "x:thing",
            'rule thing { custom(python: "pkg.mod.Thing"); }\nrule item { name: pkg; }\n',
            "thing := t:/[a-z]+/ ;\n",
        )
        assert len(errors) == 1
        assert "the `import pkg` the Python module needs for the `custom(...)` type of rule 'thing'" in errors[0]
        assert "collides with rule 'item'" in errors[0]

    def test_two_paths_sharing_a_head_claim_it_once(self) -> None:
        """Both entries of one coercion import the same module, which is one name, not two."""
        model = configured(
            "x:money",
            'rule money { type: custom(py_type: "pkg.mod.Cents", py_parse: "pkg.mod.parse", '
            'py_unparse: "pkg.mod.render"); }\n',
            "money := d:/[0-9]+/ ;\n",
        )
        assert "pkg" in model.claimed_names

    def test_a_renamed_type_can_collide_with_the_head_of_a_rust_custom_path(self) -> None:
        """Rust writes the path inline, and its head resolves against the module's own items."""
        errors = configured_errors(
            "x:thing",
            'rule thing { custom(python: "pkg.mod.Thing", rust: "app::Thing"); }\nrule item { name: app; }\n',
            "thing := t:/[a-z]+/ ;\n",
        )
        assert len(errors) == 1
        assert "the `app` the Rust module's path for the `custom(...)` type of rule 'thing'" in errors[0]
        assert "collides with rule 'item'" in errors[0]

    def test_a_renamed_type_can_collide_with_the_head_of_a_rust_coercion_path(self) -> None:
        errors = configured_errors(
            "x:money",
            'rule money { type: custom(py_type: "pkg.mod.Cents", py_parse: "pkg.mod.parse", '
            'py_unparse: "pkg.mod.render", rust_type: "money::Cents", rust_parse: "money::parse", '
            'rust_unparse: "money::render"); }\nrule item { name: money; }\n',
            "money := d:/[0-9]+/ ;\n",
        )
        assert len(errors) == 1
        assert "the `money` the Rust module's path for the `type: custom(...)` type of rule 'money'" in errors[0]

    def test_one_head_spelled_on_both_backends_is_claimed_once(self) -> None:
        """Otherwise the Python claim and the Rust claim would report a collision with themselves."""
        model = configured(
            "x:thing",
            'rule thing { custom(python: "app.mod.Thing", rust: "app::Thing"); }\n',
            "thing := t:/[a-z]+/ ;\n",
        )
        assert "the `import app` the Python module needs" in model.claimed_names["app"]

    @pytest.mark.parametrize("head", ["crate", "super", "self", "Self"])
    def test_a_rust_path_rooted_in_the_module_tree_claims_nothing(self, head: str) -> None:
        """``crate::x`` names a position, not a module-level name a generated type could take."""
        model = configured(
            "x:thing",
            f'rule thing {{ custom(python: "pkg.mod.Thing", rust: "{head}::app::Thing"); }}\n',
            "thing := t:/[a-z]+/ ;\n",
        )
        assert head not in model.claimed_names

    def test_a_renamed_type_can_collide_with_a_sum_rules_alternative_dispatch(self) -> None:
        """The dispatch is a Rust-only `fn`, so only the Rust sweep would otherwise see it."""
        errors = configured_errors(
            "x:choice", "rule other { name: _choice_alternative; }\n", "choice := lit:item | nested:other ;\n"
        )
        assert len(errors) == 1
        assert "the alternative dispatch of sum rule 'choice'" in errors[0]
        assert "collides with rule 'other'" in errors[0]

    def test_a_wide_scalar_coercion_claims_the_module_its_type_comes_from(self) -> None:
        model = configured("x:ident", "rule ident { type: uuid; }\n", "ident := t:/[a-z0-9-]+/ ;\n")
        assert model.claimed_names["uuid"] == (
            "the `import uuid` the Python module needs for the `type: uuid` coercion of rule 'ident'"
        )


def _collect_names(body: list[ast.stmt], names: set[str]) -> None:
    """Add every name the statements of one module-level block bind."""
    for statement in body:
        if isinstance(statement, ast.ClassDef | ast.FunctionDef):
            names.add(statement.name)
        elif isinstance(statement, ast.Import):
            names.update(alias.asname or alias.name.partition(".")[0] for alias in statement.names)
        elif isinstance(statement, ast.ImportFrom):
            names.update(alias.asname or alias.name for alias in statement.names)
        elif isinstance(statement, ast.AnnAssign):
            if isinstance(statement.target, ast.Name):
                names.add(statement.target.id)
        elif isinstance(statement, ast.Assign):
            names.update(target.id for target in statement.targets if isinstance(target, ast.Name))
        elif isinstance(statement, ast.If):
            # A ``TYPE_CHECKING`` block binds into the module namespace like anything else.
            _collect_names(statement.body, names)
            _collect_names(statement.orelse, names)


def _module_level_names(source: str) -> set[str]:
    """Every name a generated module binds at module level: imports, classes, functions, values."""
    names: set[str] = set()
    _collect_names(ast.parse(source).body, names)
    return names


# Rust has no `ast` module to read a generated file back with, so the sweep is a text scan of what
# sits at column 0: an item declaration binds its own name and a `use` line binds its alias, or the
# last segment of its path where it has none.  An `impl` block matches neither, which is right — it
# binds nothing.
_RUST_ITEM_RE = re.compile(r"(?:pub(?:\([^)]*\))? )?(?:struct|enum|fn|mod|const|static|type|trait) ([A-Za-z_]\w*)")
_RUST_USE_RE = re.compile(r"use ([A-Za-z_][\w:]*)(?: as ([A-Za-z_]\w*))?;")


def _rust_module_level_names(source: str) -> set[str]:
    """Every name a generated Rust module binds at module level: items and `use` bindings."""
    names: set[str] = set()
    for line in source.splitlines():
        item = _RUST_ITEM_RE.match(line)
        if item is not None:
            names.add(item.group(1))
            continue
        used = _RUST_USE_RE.match(line)
        if used is not None:
            names.add(used.group(2) or used.group(1).rsplit("::", maxsplit=1)[-1])
    return names


class TestClaimTableExhaustiveness:
    """Every module-level name an emitter writes must have run through the claim table.

    The table's whole value is exhaustiveness: a name family added to an emitter without a claim
    is a silent clobber waiting for a sidecar rename to spell it.  Reading the emitted source back
    is what makes that failure automatic rather than something a reviewer has to notice.

    Both emitters are swept, because neither covers the other: the Rust module carries families
    the Python one has no spelling for — the alternative dispatch of a sum rule, the equality-walk
    module — and a Rust-only name is exactly the kind that escapes into a downstream consumer's
    build as a rustc duplicate-definition error rather than a generation error.

    The input set is the fixture module's own roster, so a grammar added there joins the sweep
    without anyone remembering to extend a second list.
    """

    @pytest.mark.parametrize(
        ("name", "grammar", "sidecar"), fixtures.EXAMPLES, ids=[case[0] for case in fixtures.EXAMPLES]
    )
    def test_every_name_the_python_module_defines_was_claimed(self, name: str, grammar: str, sidecar: str) -> None:
        model = configured_model(grammar, sidecar)
        source = gsm2ast.generate_ast_module(model, "app.cst", "app.parser", "app.unparser")
        unclaimed = sorted(_module_level_names(source) - set(model.claimed_names))
        assert not unclaimed, f"{name}: unclaimed generated names {unclaimed}"

    def test_the_sweep_reaches_the_per_alternative_helpers(self) -> None:
        """The one name family the shared examples would otherwise not emit at all."""
        model = configured_model(fixtures.MERGED_GRAMMAR, fixtures.MERGED_SIDECAR)
        source = gsm2ast.generate_ast_module(model, "app.cst")
        assert {"_erased_wrapped_to_cst_alt0", "_flat_bracket_to_cst_alt0"} <= _module_level_names(source)

    @pytest.mark.parametrize(
        ("name", "grammar", "sidecar"), fixtures.EXAMPLES, ids=[case[0] for case in fixtures.EXAMPLES]
    )
    def test_every_name_the_rust_module_defines_was_claimed(self, name: str, grammar: str, sidecar: str) -> None:
        model = fixtures.model_for(grammar, sidecar, ac.Backend.RUST)
        source = gsm2ast_rs.generate_ast_rs(
            model, "super::cst", parser_mod_path="super::parser", unparser_mod_path="super::unparser"
        )
        unclaimed = sorted(_rust_module_level_names(source) - set(model.claimed_names))
        assert not unclaimed, f"{name}: unclaimed generated names {unclaimed}"

    def test_the_rust_sweep_reaches_the_families_the_python_module_has_no_spelling_for(self) -> None:
        """The extractor returning an empty set would make the sweep above pass on anything."""
        model = fixtures.model_for(FOLD_GRAMMAR, FOLD_SIDECAR, ac.Backend.RUST)
        source = gsm2ast_rs.generate_ast_rs(model, "super::cst", parser_mod_path="super::parser")
        names = _rust_module_level_names(source)
        assert {"_factor_alternative", am.EQ_SUPPORT_MODULE, "_expr_drop_witness", "Expr", "cst", "parser"} <= names


RECURSIVE_GRAMMAR = """
tree := name:word , child:tree? ;
word := w:/[a-z]+/ ;
"""


class TestRecursion:
    """Which by-value edges close a cycle, and which types nest to an unbounded depth."""

    def test_a_self_reference_is_boxed(self) -> None:
        recursion = am.recursion(model_for_text(RECURSIVE_GRAMMAR))
        assert recursion.is_boxed("Tree", "Tree")
        assert recursion.boxed == frozenset({("Tree", "Tree")})

    def test_a_self_reference_nests_deeply(self) -> None:
        assert am.recursion(model_for_text(RECURSIVE_GRAMMAR)).deep == frozenset({"Tree"})

    def test_a_collection_is_an_indirection_already(self) -> None:
        """A ``Vec`` field cannot make its owner infinite, so it needs no second one."""
        recursion = am.recursion(model_for_text("tree := name:word , kids:tree* ;\nword := w:/[a-z]+/ ;\n"))
        assert recursion.boxed == frozenset()
        assert recursion.deep == frozenset()

    def test_a_keyed_collection_is_an_indirection_too(self) -> None:
        model = configured_model(
            "tree := name:word , kids:tree* ;\nword := w:/[a-z]+/ ;\n",
            "rule tree { key: name; }\nrule word { transparent; }\n",
        )
        assert am.recursion(model).boxed == frozenset()

    def test_a_reference_outside_a_cycle_stays_direct(self) -> None:
        recursion = am.recursion(model_for_text(RECURSIVE_GRAMMAR))
        assert not recursion.is_boxed("Tree", "Word")

    def test_a_mutual_cycle_boxes_both_edges(self) -> None:
        model = model_for_text("one := t:two ;\ntwo := o:one? , w:word ;\nword := w:/[a-z]+/ ;\n")
        recursion = am.recursion(model)
        assert recursion.boxed == frozenset({("One", "Two"), ("Two", "One")})
        assert recursion.deep == frozenset({"One", "Two"})

    def test_a_field_enum_is_part_of_the_graph(self) -> None:
        """A label carrying its own rule reaches the owner back through the label's enum."""
        model = model_for_text('wrap := ( a:num | a:wrap ) . ";" ;\nnum := d:/[0-9]+/ ;\n')
        recursion = am.recursion(model)
        assert recursion.boxed == frozenset({("Wrap", "WrapA"), ("WrapA", "Wrap")})
        assert recursion.deep == frozenset({"Wrap", "WrapA"})

    def test_a_sum_payload_is_an_edge(self) -> None:
        model = model_for_text('expr := lit:num | nested:group ;\ngroup := "(" , e:expr , ")" ;\nnum := d:/[0-9]+/ ;\n')
        recursion = am.recursion(model)
        assert recursion.boxed == frozenset({("Expr", "Group"), ("Group", "Expr")})

    def test_the_expression_grammar_boxes_exactly_the_three_payload_edges(self) -> None:
        """The expression grammar: ``Expr -> Term -> Factor -> Expr`` is one component."""
        recursion = am.recursion(configured_model(FOLD_GRAMMAR, FOLD_SIDECAR))
        assert recursion.boxed == frozenset({("Expr", "Term"), ("Term", "Factor"), ("Factor", "Expr")})

    def test_the_expression_grammar_needs_five_bounded_stack_types(self) -> None:
        recursion = am.recursion(configured_model(FOLD_GRAMMAR, FOLD_SIDECAR))
        assert recursion.deep == frozenset({"Expr", "Term", "Factor", "ExprBinary", "TermBinary"})

    def test_a_fold_nests_deeply_whatever_the_graph_says(self) -> None:
        """A chain is as deep as the operand count, which the boxing graph deliberately ignores."""
        model = configured(
            "e:expr",
            "rule expr { fold_left: op; }\n",
            'expr := d:num , ( , op:sign , d:num)* ;\nnum := v:/[0-9]+/ ;\nsign := p:"+" | m:"-" ;\n',
        )
        recursion = am.recursion(model)
        assert recursion.boxed == frozenset()
        assert recursion.deep == frozenset({"Expr", "ExprBinary"})

    def test_a_coerced_payload_embeds_nothing(self) -> None:
        model = configured(
            "d:num",
            "rule num { type: i64; transparent; }\n",
            "num := v:/[0-9]+/ ;\n",
        )
        assert am.embedded_types(fields_by_name(model.nodes["target"])["d"].element) == ()


# Past Python's default recursion limit of 1000, so a component walk written with call frames
# fails here where it survives every small graph above.
DEEP_CHAIN_RULES = 2000


def deep_chain(back_edge: str = "") -> str:
    """A grammar whose type graph is one ``DEEP_CHAIN_RULES``-long chain of by-value edges."""
    rules = "".join(f"r{index} := a:r{index + 1} ;\n" for index in range(DEEP_CHAIN_RULES))
    return rules + f"r{DEEP_CHAIN_RULES} := {back_edge}w:/[a-z]+/ ;\n"


class TestRecursionAtGrammarDepth:
    """The component walks must survive arbitrarily deep graphs: the depth is user input.

    Every other recursion test runs on a graph of a handful of nodes, where a recursive
    implementation would pass too.  These are the ones that fail if the walk uses call frames.
    """

    def test_a_chain_deeper_than_the_recursion_limit_needs_no_boxing(self) -> None:
        recursion = am.recursion(model_for_text(deep_chain()))
        assert recursion.boxed == frozenset()
        assert recursion.deep == frozenset()

    def test_a_cycle_deeper_than_the_recursion_limit_boxes_every_edge(self) -> None:
        """One component of ``DEEP_CHAIN_RULES + 1`` types: every edge in it closes the cycle."""
        recursion = am.recursion(model_for_text(deep_chain("a:r0 , ")))
        assert len(recursion.boxed) == DEEP_CHAIN_RULES + 1
        assert len(recursion.deep) == DEEP_CHAIN_RULES + 1

    def test_span_bearing_survives_the_same_depth(self) -> None:
        bearing = am.span_bearing(model_for_text(deep_chain()))
        assert len(bearing) == DEEP_CHAIN_RULES + 1


class TestSpanBearing:
    """A sum or fold enum has a span only where every payload it can hold does."""

    def test_a_struct_always_carries_one(self) -> None:
        bearing = am.span_bearing(model_for_text(RECURSIVE_GRAMMAR))
        assert {"Tree", "Word"} <= bearing

    def test_a_sum_over_node_payloads_carries_one(self) -> None:
        model = model_for_text("pick := a:one | b:two ;\none := x:/[a-z]+/ ;\ntwo := y:/[0-9]+/ ;\n")
        assert "Pick" in am.span_bearing(model)

    def test_an_erased_payload_takes_the_span_away(self) -> None:
        model = configured_model(
            "pick := a:one | b:two ;\none := x:/[a-z]+/ ;\ntwo := y:/[0-9]+/ ;\n",
            "rule two { transparent; }\n",
        )
        assert "Pick" not in am.span_bearing(model)

    def test_a_value_enum_carries_none(self) -> None:
        """A value enum is a bare discriminant, so nothing over it can promise a span."""
        model = model_for_text('pick := a:"a" | b:"b" ;\n')
        bearing = am.span_bearing(model)
        assert "PickValue" not in bearing
        assert "Pick" in bearing

    def test_a_field_enum_over_node_payloads_carries_one(self) -> None:
        model = model_for_text('wrap := ( a:num | a:word ) . ";" ;\nnum := d:/[0-9]+/ ;\nword := w:/[a-z]+/ ;\n')
        assert "WrapA" in am.span_bearing(model)

    def test_a_field_enum_holding_text_carries_none(self) -> None:
        """One ``Text`` variant is a plain ``String``, which has no position of its own."""
        model = model_for_text("wrap := ( a:num | a:/[a-z]+/ ) ;\nnum := d:/[0-9]+/ ;\n")
        assert "WrapA" not in am.span_bearing(model)

    def test_mutually_recursive_sums_bottom_out(self) -> None:
        """The fixpoint is the greatest one, so a cycle of sums over structs keeps its span."""
        model = model_for_text(
            "one := a:leaf | b:two ;\ntwo := c:leaf | d:one ;\nleaf := x:/[a-z]+/ ;\n",
        )
        assert {"One", "Two"} <= am.span_bearing(model)

    def test_a_fold_over_a_coerced_operand_carries_none(self) -> None:
        model = configured_model(FOLD_GRAMMAR, FOLD_SIDECAR)
        bearing = am.span_bearing(model)
        assert {"ExprBinary", "TermBinary"} <= bearing
        # `factor` erases `number` to a bare `i64`, so nothing above it can promise a span.
        assert bearing.isdisjoint({"Expr", "Term", "Factor"})


def members_of(witness: am.Witness) -> dict[str, am.Witness]:
    assert isinstance(witness, am.StructWitness)
    return {member.name: member.value for member in witness.members}


class TestWitnesses:
    """The cheap value per generated type that an iterative teardown writes back as a sentinel."""

    def test_a_struct_takes_a_witness_per_member(self) -> None:
        model = model_for_text('doc := t:/[a-z]+/ , lit:"!" , opt:"?"? , many:num* ;\nnum := d:/[0-9]+/ ;\n')
        members = members_of(am.witnesses(model)["Doc"])
        assert members["t"] == am.ScalarWitness(am.TEXT)
        assert members["lit"] == am.ScalarWitness(am.SPAN)
        # An optional labeled literal is a presence flag, which is false where it was absent.
        assert members["opt"] == am.ScalarWitness(am.BOOL)
        assert members["many"] == am.EmptyWitness(am.Container.COLLECTION)

    def test_an_optional_member_is_absent_and_a_map_is_empty(self) -> None:
        model = configured_model(
            'doc := kid:setting? , kids:setting* ;\nsetting := key:word , "=" , v:word ;\nword := w:/[a-z]+/ ;\n',
            "rule word { transparent; }\nrule setting { key: key; }\n",
        )
        members = members_of(am.witnesses(model)["Doc"])
        assert members["kid"] == am.EmptyWitness(am.Container.OPTIONAL)
        assert members["kids"] == am.EmptyWitness(am.Container.MAP)

    def test_a_coerced_terminal_carries_the_coercion_rather_than_its_text(self) -> None:
        model = configured_model("doc := n:num ;\nnum := d:/[0-9]+/ ;\n", "rule num { type: i64; }\n")
        (member,) = members_of(am.witnesses(model)["Num"]).items()
        name, value = member
        assert name == "value"
        assert isinstance(value, am.ScalarWitness)
        assert value.element == am.TransparentType("num", am.TEXT, am.BuiltinCoercion("i64"))

    def test_an_enum_shaped_rule_takes_its_value_enums_first_variant(self) -> None:
        model = model_for_text('pick := a:"a" | b:"b" ;\n')
        table = am.witnesses(model)
        assert table["PickValue"] == am.UnitWitness("PickValue", "A")
        assert members_of(table["Pick"])["value"] == am.UnitWitness("PickValue", "A")

    def test_a_bool_rule_witnesses_false(self) -> None:
        model = configured_model('flag := yes:"yes" | no:"no" ;\n', "rule flag { bool: yes; }\n")
        assert members_of(am.witnesses(model)["Flag"])["value"] == am.ScalarWitness(am.BOOL)

    def test_a_sum_skips_the_variants_nothing_constructs(self) -> None:
        """A `custom(...)` payload has no witness, so the first variant that does wins."""
        model = configured_model(
            "pick := a:item | b:num ;\nnum := d:/[0-9]+/ ;\n" + ITEM_TAIL,
            'rule item { custom(python: "pkg.mod.Item"); }\n',
        )
        witness = am.witnesses(model)["Pick"]
        assert isinstance(witness, am.VariantWitness)
        assert witness.variant == "B"

    def test_a_cycle_with_an_exit_grounds_out_through_it(self) -> None:
        """The expression grammar: every fold enum bottoms out in the coerced operand leaf."""
        table = am.witnesses(configured_model(FOLD_GRAMMAR, FOLD_SIDECAR))
        expr = table["Expr"]
        assert isinstance(expr, am.VariantWitness)
        assert expr.variant == "Operand"
        term = expr.payload
        assert isinstance(term, am.VariantWitness)
        assert term.variant == "Operand"
        factor = term.payload
        assert isinstance(factor, am.VariantWitness)
        assert factor.variant == "Num"
        assert isinstance(factor.payload, am.ScalarWitness)

    def test_a_fold_never_witnesses_its_own_chain_link(self) -> None:
        """A link needs the enum's witness for both sides, so the enum has one first."""
        table = am.witnesses(configured_model(FOLD_GRAMMAR, FOLD_SIDECAR))
        assert "ExprBinary" not in table
        assert "TermBinary" not in table

    def test_a_cycle_with_no_exit_has_no_witness(self) -> None:
        """Such a type has no finite values either, so there is nothing to refuse."""
        assert am.witnesses(model_for_text("one := x:two ;\ntwo := y:one ;\n")) == {}

    def test_a_custom_payload_blocks_the_chain_it_is_the_only_operand_of(self) -> None:
        model = configured_model(fixtures.CUSTOM_FOLD_GRAMMAR, fixtures.CUSTOM_FOLD_SIDECAR)
        table = am.witnesses(model)
        assert "Expr" not in table
        # The rest of the grammar still resolves; only what reaches the user's type does not.
        assert "SignValue" in table

    def test_a_type_custom_coercion_is_no_more_constructible_than_a_custom_rule(self) -> None:
        """The generator can name a value of the user's scalar type no more than of their node type.

        The two travel different branches of ``_element_witness``, and only the rule branch is
        covered above.  Were the coercion branch to hand back a ``ScalarWitness``, the Rust
        emitter's builtin assertion would fire as a generator crash — or worse, spell the user's
        opaque type as ``0``, which is a rustc error in a consumer's build.
        """
        model = configured_model(fixtures.MERGED_GRAMMAR, fixtures.MERGED_SIDECAR)
        table = am.witnesses(model)
        assert "Amount" not in table
        # The block propagates to the struct holding it as a required member, and no further.
        assert "Doc" not in table
        assert {"Import", "Tagged", "Choice", "Pick"} <= set(table)

    def test_a_value_enum_with_no_variants_has_no_witness(self) -> None:
        """The builder's guard: a first variant is what it names, so no variants names nothing."""
        empty = am.ValueEnum(name="Empty", rule_name="empty", variants=())
        assert am._value_enum_builder(empty)({}) is None

    def test_the_fold_table_is_keyed_by_rule_and_skips_the_blocked_ones(self) -> None:
        folds = am.fold_witnesses(configured_model(FOLD_GRAMMAR, FOLD_SIDECAR))
        assert set(folds) == {"expr", "term"}
        assert folds["expr"] == am.witnesses(configured_model(FOLD_GRAMMAR, FOLD_SIDECAR))["Expr"]
        assert am.fold_witnesses(configured_model(fixtures.CUSTOM_FOLD_GRAMMAR, fixtures.CUSTOM_FOLD_SIDECAR)) == {}
