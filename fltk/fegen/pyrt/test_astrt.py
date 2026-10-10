"""Tests for the AST runtime's backend-neutral pieces.

``bucket_children`` and ``CrossBackendEnumMixin`` are the two places where the runtime reads a
label's identity, and both are on the path a generated ``from_cst`` takes for a CST from any
backend.  What they may rely on is the canonical-name contract every conforming backend
implements — not ``enum.Enum``'s ``name``, which the Rust pyclasses do not have.

``terminal_to_cst`` is the split a terminal-only rule's ``to_cst`` rebuilds its children with,
exercised here over hand-built step tables.
"""

from __future__ import annotations

import dataclasses
import enum
import typing

import pytest

from fltk.fegen import fltk_cst, fltk_cst_protocol
from fltk.fegen.pyrt import astrt, terminalsrc


class _Bare:
    """A label carrying nothing but the canonical name: the whole contract, and no more."""

    def __init__(self, canonical: str) -> None:
        self._fltk_canonical_name = canonical


class _Nameless:
    """A label from no conforming backend at all."""


class TestBucketChildren:
    """The bucket keys are the ``<MEMBER>`` component of the label's canonical name."""

    def test_python_enum_labels_key_by_their_member_names(self) -> None:
        """The keys match the enum member names."""
        labels = [fltk_cst.Items.Label.ITEM, fltk_cst.Items.Label.NO_WS, fltk_cst.Items.Label.ITEM]
        buckets = astrt.bucket_children([(label, index) for index, label in enumerate(labels)])

        assert buckets == {"ITEM": [0, 2], "NO_WS": [1]}
        assert list(buckets) == [label.name for label in dict.fromkeys(labels)]

    def test_protocol_label_sentinels_key_the_same_way(self) -> None:
        """The protocol module's own Label members carry the contract, so they bucket too."""
        buckets = astrt.bucket_children(
            [
                (fltk_cst_protocol.ItemsLabel.ITEM, "a"),
                (fltk_cst_protocol.ItemsLabel.WS_ALLOWED, "b"),
            ]
        )

        assert buckets == {"ITEM": ["a"], "WS_ALLOWED": ["b"]}

    def test_the_two_flavors_land_in_one_bucket(self) -> None:
        """A key is a plain string, so nothing about which flavor produced it survives."""
        buckets = astrt.bucket_children(
            [(fltk_cst.Items.Label.ITEM, "py"), (fltk_cst_protocol.ItemsLabel.ITEM, "proto")]
        )

        assert buckets == {"ITEM": ["py", "proto"]}

    def test_a_label_with_only_a_canonical_name_is_enough(self) -> None:
        """Nothing beyond the contract is read, which is what makes an unseen backend work."""
        buckets = astrt.bucket_children([(_Bare("Widget.Label.FROB"), 1), (_Bare("Widget.Label.FROB"), 2)])

        assert buckets == {"FROB": [1, 2]}

    def test_a_canonical_name_without_dots_is_its_own_key(self) -> None:
        """The suffix of a name with no separator is the whole name."""
        assert astrt.bucket_children([(_Bare("FROB"), 1)]) == {"FROB": [1]}

    def test_source_order_is_preserved_within_a_bucket(self) -> None:
        label = fltk_cst.Items.Label.ITEM
        assert astrt.bucket_children((label, index) for index in range(4)) == {"ITEM": [0, 1, 2, 3]}

    def test_unlabeled_children_are_skipped(self) -> None:
        """Trivia and ``$``-included literals carry no label and record nothing."""
        buckets = astrt.bucket_children([(None, "trivia"), (fltk_cst.Items.Label.ITEM, "x"), (None, "more")])

        assert buckets == {"ITEM": ["x"]}

    def test_a_label_without_the_contract_names_the_attribute_it_lacks(self) -> None:
        """Only conforming backends are supported; there is no fallback to ``.name``."""
        with pytest.raises(AttributeError, match="_fltk_canonical_name"):
            astrt.bucket_children([(typing.cast("typing.Any", _Nameless()), 1)])

    def test_an_enum_label_without_the_contract_is_refused_too(self) -> None:
        """A ``.name`` is not the contract, so a pre-canonical-name CST module regenerates."""

        class Stale(enum.Enum):
            ITEM = enum.auto()

        with pytest.raises(AttributeError, match="_fltk_canonical_name"):
            astrt.bucket_children([(typing.cast("typing.Any", Stale.ITEM), 1)])


class _Colour(astrt.CrossBackendEnumMixin, enum.Enum):
    """A generated value enum, spelled the way the emitter spells one."""

    RED = enum.auto()
    GREEN = enum.auto()


_Colour.RED._fltk_canonical_name = "_Colour.RED"
_Colour.GREEN._fltk_canonical_name = "_Colour.GREEN"


class TestCrossBackendEnumMixin:
    """Same-type equality goes through the canonical name."""

    def test_a_member_equals_itself(self) -> None:
        member = _Colour.RED
        assert member == _Colour.RED
        assert not (member != _Colour.RED)

    def test_distinct_members_are_unequal(self) -> None:
        assert _Colour.RED != _Colour.GREEN
        assert not (_Colour.RED == _Colour.GREEN)

    def test_hash_follows_the_canonical_name(self) -> None:
        assert hash(_Colour.RED) == hash("_Colour.RED")
        assert len({_Colour.RED, _Colour.GREEN}) == 2

    def test_a_member_is_usable_as_a_dict_key(self) -> None:
        table = {_Colour.RED: "warm", _Colour.GREEN: "cool"}
        assert table[_Colour.RED] == "warm"

    def test_another_flavor_carrying_the_same_canonical_name_compares_equal(self) -> None:
        """The whole point of the mixin: a PyO3 counterpart of the same member is the same value."""
        assert _Colour.RED == _Bare("_Colour.RED")
        assert _Colour.RED != _Bare("_Colour.GREEN")

    @pytest.mark.parametrize("other", [None, 1, "_Colour.RED", object()])
    def test_an_operand_carrying_no_canonical_name_is_unequal_never_an_error(self, other: object) -> None:
        assert (_Colour.RED == other) is False
        assert (_Colour.RED != other) is True

    def test_the_mixin_leaves_the_enum_member_name_alone(self) -> None:
        """``enum.Enum`` supplies ``name``; the mixin does not re-declare it."""
        assert _Colour.RED.name == "RED"
        assert typing.get_type_hints(astrt.CrossBackendEnumMixin).keys() == {"_fltk_canonical_name"}


class _Node:
    """A terminal-only CST node class as ``terminal_to_cst`` uses one: a label enum, a span, ``append``."""

    class Label(enum.Enum):
        A = enum.auto()
        B = enum.auto()

    def __init__(self, span: terminalsrc.Span) -> None:
        self.span = span
        self.children: list[tuple[_Node.Label | None, terminalsrc.Span]] = []

    def append(self, child: terminalsrc.Span, label: _Node.Label | None) -> None:
        self.children.append((label, child))


def _re(term: str, label: str | None = "A", minimum: int = 1, maximum: float = 1) -> astrt.TerminalStep:
    return astrt.TerminalStep(term, literal=False, included=True, label=label, minimum=minimum, maximum=maximum)


def _lit(term: str, label: str | None = None, minimum: int = 1, maximum: float = 1) -> astrt.TerminalStep:
    return astrt.TerminalStep(term, literal=True, included=True, label=label, minimum=minimum, maximum=maximum)


def _suppressed(step: astrt.TerminalStep) -> astrt.TerminalStep:
    return dataclasses.replace(step, included=False, label=None)


def _walk(*steps: astrt.TerminalStep) -> astrt.TerminalAlt:
    return astrt.TerminalAlt(steps)


def _split(text: str, *alternatives: astrt.TerminalAlt, redirected: bool = False) -> _Node:
    node = astrt.terminal_to_cst(_Node, text, alternatives, "rule", redirected=redirected)
    assert isinstance(node, _Node)
    return node


def _children(node: _Node) -> list[tuple[str | None, str | None]]:
    """Each child as its label name and text, ``None`` for a sourceless span."""
    return [
        (None if label is None else label.name, span.text() if span.has_source() else None)
        for label, span in node.children
    ]


_UNMATCHED = "rule 'rule': text {text!r} is not something the rule could have matched"


class TestTerminalToCst:
    """The split replays the generated parser's consumption of the node's own text."""

    def test_one_regex_takes_the_whole_text(self) -> None:
        node = _split("42", _walk(_re("[0-9]+")))
        assert _children(node) == [("A", "42")]
        assert node.span.text() == "42"

    def test_a_suppressed_literal_consumes_and_appends_nothing(self) -> None:
        quote = _suppressed(_lit('"'))
        assert _children(_split('"hi"', _walk(quote, _re('[^"]*'), quote))) == [("A", "hi")]

    def test_an_included_literal_appends_a_sourceless_child(self) -> None:
        """The sentinel span ``ast-synthesised-literal-spans`` tracks."""
        node = _split("#host", _walk(_lit("#"), _re("[a-z]+")))
        assert _children(node) == [(None, None), ("A", "host")]
        assert node.children[0][1] is terminalsrc.UnknownSpan

    def test_a_plus_step_appends_one_child_per_occurrence(self) -> None:
        node = _split("abc", _walk(_re("[a-z]", maximum=astrt.UNBOUNDED)))
        assert _children(node) == [("A", "a"), ("A", "b"), ("A", "c")]

    def test_a_star_step_may_take_no_occurrence(self) -> None:
        node = _split("42", _walk(_re("[a-z]", minimum=0, maximum=astrt.UNBOUNDED), _re("[0-9]+", "B")))
        assert _children(node) == [("B", "42")]

    @pytest.mark.parametrize(
        ("text", "children"),
        [("ab5!", [("A", "ab"), ("B", "5"), (None, None)]), ("ab", [("A", "ab")])],
        ids=["present", "absent"],
    )
    def test_an_optional_step_appears_only_when_present(
        self, text: str, children: list[tuple[str | None, str | None]]
    ) -> None:
        alternative = _walk(_re("[a-z]+"), _re("[0-9]", "B", minimum=0), _lit("!", minimum=0))
        assert _children(_split(text, alternative)) == children

    def test_a_nullable_single_step_is_appended_empty(self) -> None:
        assert _children(_split("b", _walk(_re("a*"), _re("b", "B")))) == [("A", ""), ("B", "b")]
        assert _children(_split("b", _walk(_re("a*", minimum=0), _re("b", "B")))) == [("A", ""), ("B", "b")]
        assert _children(_split("", _walk(_re("a*")))) == [("A", "")]

    def test_a_nullable_plus_step_fails_on_no_progress(self) -> None:
        with pytest.raises(astrt.AstError) as caught:
            _split("", _walk(_re("a*", maximum=astrt.UNBOUNDED)))
        assert caught.value.message == _UNMATCHED.format(text="")

    def test_a_repeat_never_gives_back_what_it_took(self) -> None:
        """``a+`` takes both, leaving ``a`` nothing, though a backtracking regex would split them."""
        with pytest.raises(astrt.AstError) as caught:
            _split("aa", _walk(_re("a+"), _re("a", "B")))
        assert caught.value.message == _UNMATCHED.format(text="aa")

    def test_the_first_alternative_that_matches_is_committed_to(self) -> None:
        with pytest.raises(astrt.AstError) as caught:
            _split("ab", _walk(_re("a")), _walk(_re("ab", "B")))
        assert caught.value.message == (
            "rule 'rule': text 'ab' is not something the rule could have matched — alternative 0 matches "
            "only its first 1 codepoint(s), and the parser commits to the first alternative that matches "
            "rather than trying the next"
        )

    def test_a_failed_alternative_falls_through_in_grammar_order(self) -> None:
        alternatives = (_walk(_re("[0-9]+")), _walk(_re("[a-z]+", "B")), _walk(_re("[a-z]")))
        assert _children(_split("abc", *alternatives)) == [("B", "abc")]

    def test_a_repeated_literal_appends_one_sourceless_child_per_occurrence(self) -> None:
        node = _split("!!!x", _walk(_lit("!", maximum=astrt.UNBOUNDED), _re("[a-z]")))
        assert _children(node) == [(None, None), (None, None), (None, None), ("A", "x")]

    def test_the_split_is_measured_in_codepoints(self) -> None:
        node = _split("café bar", _walk(_re("[^ ]+"), _suppressed(_lit(" ")), _re("[^ ]+", "B")))
        assert _children(node) == [("A", "café"), ("B", "bar")]
        assert node.children[0][1].end == 4
        repeated = _split("Àé", _walk(_re("[À-ÿ]", maximum=astrt.UNBOUNDED)))
        assert [span.end for _label, span in repeated.children] == [1, 1]
        with pytest.raises(astrt.AstError, match="matches only its first 2 codepoint"):
            _split("éé x", _walk(_re("[^ ]+")))

    def test_a_later_step_sees_what_precedes_it(self) -> None:
        """``^`` holds only at the start of the text, as in the parser's own match."""
        with pytest.raises(astrt.AstError):
            _split("a1", _walk(_re("[a-z]"), _re("^[0-9]", "B")))

    def test_an_unsupported_alternative_is_passed_over(self) -> None:
        alternatives = (astrt.TerminalAlt(None), _walk(_re("[0-9]+")))
        assert _children(_split("42", *alternatives)) == [("A", "42")]
        with pytest.raises(astrt.AstError) as caught:
            _split("a1", *alternatives)
        assert caught.value.message == _UNMATCHED.format(text="a1")

    def test_every_alternative_unsupported_is_refused_before_the_text_is_read(self) -> None:
        with pytest.raises(astrt.AstError, match="every alternative holds a sub-expression"):
            astrt.terminal_to_cst(_Node, 42, [astrt.TerminalAlt(None)], "rule")

    def test_text_that_is_not_a_string_is_refused(self) -> None:
        with pytest.raises(astrt.AstError, match="rule 'rule': text is int, not text"):
            astrt.terminal_to_cst(_Node, 42, [_walk(_re("[0-9]+"))], "rule")

    def test_a_redirected_text_is_matched_whole_against_its_own_terminal(self) -> None:
        redirect = astrt.TerminalAlt(None, "(?P<_ast_g1>[a-z]+)", ((None, None), ("A", "_ast_g1"), (None, None)))
        node = _split("abc", astrt.TerminalAlt(None), redirect, redirected=True)
        assert node.span is terminalsrc.UnknownSpan
        assert _children(node) == [(None, None), ("A", "abc"), (None, None)]
        with pytest.raises(astrt.AstError):
            _split("ab1", redirect, redirected=True)
