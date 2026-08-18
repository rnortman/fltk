"""Unit tests for the unparser runtime support (``fltk.unparse.pyrt``).

Distinct from ``tests/test_pyrt_errors.py``, which despite the name is scoped to
``fltk.fegen.pyrt.errors`` and cross-pinned with the Rust escape tests.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from fltk.fegen.pyrt import terminalsrc
from fltk.unparse.pyrt import (
    capped_blank_lines,
    count_whitespace_newlines,
    literal_span_matches,
    preceding_comment_trailing_newline,
    raise_preserved_trivia_failure,
)


@dataclass
class _FakeNode:
    """Minimal stand-in for a CST node child: carries only a ``.span`` attribute."""

    span: terminalsrc.Span


def _span(text: str) -> terminalsrc.Span:
    return terminalsrc.Span.with_source(0, len(text), text)


class TestCountWhitespaceNewlines:
    """`count_whitespace_newlines` counts spans and whitespace-only nodes, nothing else."""

    def test_span_child_counts_all_newlines(self):
        # A direct span child contributes every newline (unchanged span semantics).
        assert count_whitespace_newlines(_span("\n\n"), "") == 2

    def test_whitespace_only_node_child_counts_newlines(self):
        # A node whose span text is entirely whitespace contributes its newlines.
        assert count_whitespace_newlines(_FakeNode(_span("\n\n")), "") == 2

    def test_comment_node_child_counts_zero(self):
        # A node holding non-whitespace (a comment) contributes nothing, even with a newline.
        assert count_whitespace_newlines(_FakeNode(_span("// hi\n")), "") == 0

    def test_empty_span_node_child_counts_zero(self):
        # A node with an empty span contributes nothing (never over-counts).
        assert count_whitespace_newlines(_FakeNode(_span("")), "") == 0

    def test_c0_separator_node_child_counts_zero(self):
        # C0 separators are not Unicode White_Space, so a node whose span mixes them with
        # newlines is not whitespace-only and contributes 0 -- matching Rust's
        # char::is_whitespace gate (str.isspace() alone would wrongly count 2 here).
        assert count_whitespace_newlines(_FakeNode(_span("\n\x1c\n")), "") == 0


class TestLiteralSpanMatches:
    """A labeled literal item accepts a span child by text, or unconditionally when sourceless."""

    def test_the_items_own_spelling_matches(self):
        assert literal_span_matches(_span("gray"), ["gray", "grey"]) is True

    def test_a_sibling_spelling_of_the_same_label_matches(self):
        assert literal_span_matches(_span("grey"), ["gray", "grey"]) is True

    def test_other_text_does_not_match(self):
        # The rival-regex case: the literal declines, so the regex branch takes the child.
        assert literal_span_matches(_span("42"), ["null"]) is False

    def test_a_sourceless_span_matches(self):
        # Synthesized children (to_cst) carry no source; rendering emits the canonical spelling.
        assert literal_span_matches(terminalsrc.Span(0, 4), ["gray", "grey"]) is True

    def test_a_child_that_is_not_a_span_raises(self):
        # The generated type check runs before this one, so a non-span cannot reach it. Should
        # some other child kind ever get here, accepting it would render the literal over that
        # child's text -- exactly the corruption the text check exists to stop -- so the missing
        # text() is left to raise.
        with pytest.raises(AttributeError):
            literal_span_matches(object(), ["gray"])  # type: ignore[arg-type]


def test_raise_preserved_trivia_failure_names_rule_and_pos() -> None:
    """The helper raises ValueError naming the rule and child position, refusing to drop comments."""
    with pytest.raises(ValueError, match="refusing to silently drop comments") as exc_info:
        raise_preserved_trivia_failure("my_rule", 3)
    msg = str(exc_info.value)
    assert "my_rule" in msg
    assert "child position 3" in msg
    assert "unparse__trivia returned None" in msg


def _children(*texts: str) -> list[tuple[object, object]]:
    """Trivia children in ``(label, child)`` form, one node per span text."""
    return [(None, _FakeNode(_span(text))) for text in texts]


class TestPrecedingCommentTrailingNewline:
    """The child before ``pos`` contributes 1 only when it is a comment ending in a newline."""

    def test_line_comment_before_pos_contributes_one(self):
        # The terminating newline lives in the comment's span, so it is added back.
        assert preceding_comment_trailing_newline(_children("// c\n", "\n"), 1, "") == 1

    def test_position_zero_contributes_nothing(self):
        # Nothing precedes the first child.
        assert preceding_comment_trailing_newline(_children("// c\n"), 0, "") == 0

    def test_position_past_the_end_raises(self):
        # A stale pos is a generated-code invariant violation; both backends fail loudly.
        with pytest.raises(IndexError):
            preceding_comment_trailing_newline(_children("// c\n"), 2, "")

    def test_child_with_no_span_contributes_nothing(self):
        assert preceding_comment_trailing_newline([(None, object())], 1, "") == 0

    def test_whitespace_child_ending_in_newline_contributes_nothing(self):
        # The guard that stops consecutive whitespace children inflating the count by one
        # per gap: a whitespace run is not a comment, however it ends.
        assert preceding_comment_trailing_newline(_children("\n\n", "\n"), 1, "") == 0

    def test_block_comment_contributes_nothing(self):
        # A block comment's span does not end in a newline, so it consumed none.
        assert preceding_comment_trailing_newline(_children("/* c */", "\n\n"), 1, "") == 0

    def test_c0_separator_child_counts_as_a_comment(self):
        # C0 separators are not Unicode White_Space, so a child mixing them with newlines is
        # not whitespace-only and contributes its terminator -- the same answer Rust's
        # char::is_whitespace gives in the generated `_comment_trailing_newline`.
        # `count_whitespace_newlines` classifies the same child as non-whitespace too, so the
        # two helpers agree: it counts 0 newlines of its own and yields 1 here.
        child = _children("\n\x1c\n")
        assert count_whitespace_newlines(child[0][1], "") == 0
        assert preceding_comment_trailing_newline([*child, (None, _FakeNode(_span("\n")))], 1, "") == 1


class TestCappedBlankLines:
    """``k`` newlines yield ``k - 1`` blank lines, clamped to ``[0, cap]``."""

    def test_two_newlines_yield_one_blank(self):
        assert capped_blank_lines(2, 2) == 1

    def test_the_cap_is_a_maximum(self):
        assert capped_blank_lines(5, 2) == 2

    def test_a_single_newline_yields_no_blank(self):
        assert capped_blank_lines(1, 2) == 0

    def test_zero_newlines_clamp_to_zero_rather_than_negative(self):
        assert capped_blank_lines(0, 2) == 0

    def test_a_zero_cap_yields_no_blanks(self):
        assert capped_blank_lines(5, 0) == 0
