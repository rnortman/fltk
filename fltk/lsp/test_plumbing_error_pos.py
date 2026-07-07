"""Tests for ``ParseResult.error_pos`` -- the surfaced furthest-failure offset."""

from __future__ import annotations

from fltk import plumbing

# Self-contained grammar with labeled terminals so the standard-disposition parser (which
# suppresses unlabeled literals/regexes) still yields non-empty CST node classes.
_GREETING = r"""
greeting := kw:"hello" , name:/[a-z]+/ , punct:"!" ;
"""


def _parser() -> plumbing.ParserResult:
    return plumbing.generate_parser(plumbing.parse_grammar(_GREETING))


def test_success_leaves_error_pos_none() -> None:
    result = plumbing.parse_text(_parser(), "hello world !", "greeting")
    assert result.success
    assert result.error_pos is None


def test_mid_input_terminal_failure_has_offset() -> None:
    # Missing the required trailing "!": the parse fails after consuming "hello world".
    text = "hello world"
    result = plumbing.parse_text(_parser(), text, "greeting")
    assert not result.success
    assert result.error_pos is not None
    assert 0 <= result.error_pos <= len(text)


def test_early_success_without_full_consumption_has_offset() -> None:
    # `top := x:"a"` matches "a" and succeeds outright, consuming only the first char of "ab"; the
    # ErrorTracker never records a terminal failure (longest_parse_len == -1), so error_pos falls
    # through to `result.pos` -- the distinct `elif result` branch, not the tracker branch.
    parser = plumbing.generate_parser(plumbing.parse_grammar('top := x:"a" ;'))
    result = plumbing.parse_text(parser, "ab", "top")
    assert not result.success
    assert result.error_pos == 1


def test_unknown_rule_leaves_error_pos_none() -> None:
    result = plumbing.parse_text(_parser(), "hello world !", "does_not_exist")
    assert not result.success
    assert result.error_pos is None
