"""Tests for the early-success prefix CST ``parse_text`` exposes on a non-total parse."""

from __future__ import annotations

from fltk import plumbing

# Repetition-shaped grammar: a broken item N stops the repetition and the start rule succeeds
# over items 1..N-1, so a mid-document error assembles a real prefix tree.
_REP = r"""
top := , item* ;
item := kw:"x" , val:/[a-z]+/ , semi:";" , ;
"""

# A single sequence with no top-level repetition: an error makes the start rule return no result
# at all (a hard failure), so no prefix is assembled.
_HARD = 'pair := a:"a" , b:"b" ;'


def _rep_parser() -> plumbing.ParserResult:
    return plumbing.generate_parser(plumbing.parse_grammar(_REP))


def _hard_parser() -> plumbing.ParserResult:
    return plumbing.generate_parser(plumbing.parse_grammar(_HARD))


def test_mid_document_error_exposes_prefix() -> None:
    # First item parses; the second's `4` is not a `/[a-z]+/`, so the repetition stops there.
    text = "x a ;\nx 4 ;\n"
    result = plumbing.parse_text(_rep_parser(), text, "top")
    assert not result.success
    assert result.cst is None
    assert result.prefix_cst is not None
    # The prefix ends at (or just past, through trailing trivia) the end of the first item.
    assert result.prefix_pos is not None
    assert text.index("x 4") - 2 <= result.prefix_pos <= text.index("x 4")
    assert result.error_pos is not None
    assert result.error_pos >= result.prefix_pos


def test_hard_failure_has_no_prefix() -> None:
    result = plumbing.parse_text(_hard_parser(), "a x", "pair")
    assert not result.success
    assert result.cst is None
    assert result.prefix_cst is None
    assert result.prefix_pos is None
    # The existing error fields are unaffected.
    assert result.error_pos is not None


def test_success_has_no_prefix() -> None:
    result = plumbing.parse_text(_rep_parser(), "x a ;\n", "top")
    assert result.success
    assert result.cst is not None
    assert result.prefix_cst is None
    assert result.prefix_pos is None


def test_unknown_rule_has_no_prefix() -> None:
    result = plumbing.parse_text(_rep_parser(), "x a ;\n", "does_not_exist")
    assert not result.success
    assert result.error_pos is None
    assert result.prefix_cst is None
    assert result.prefix_pos is None


def test_zero_length_prefix_is_still_exposed() -> None:
    # Garbage input matches zero items; the start rule succeeds consuming nothing.
    result = plumbing.parse_text(_rep_parser(), "zzz", "top")
    assert not result.success
    assert result.prefix_pos == 0
    assert result.prefix_cst is not None
