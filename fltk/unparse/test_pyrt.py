"""Unit tests for the unparser runtime support (``fltk.unparse.pyrt``).

Distinct from ``tests/test_pyrt_errors.py``, which despite the name is scoped to
``fltk.fegen.pyrt.errors`` and cross-pinned with the Rust escape tests.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from fltk.fegen.pyrt import terminalsrc
from fltk.unparse.pyrt import count_whitespace_newlines, literal_span_matches, raise_preserved_trivia_failure


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
