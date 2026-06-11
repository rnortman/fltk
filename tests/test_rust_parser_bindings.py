"""Binding surface tests for fegen_rust_cst.Parser (§2.6 of Phase 3 design).

These tests check the Python-visible surface of the Rust-backed parser,
with no Python-backend counterpart.

Requires fegen_rust_cst to be built: run 'make build-fegen-rust-cst' first.
"""

from __future__ import annotations

import pytest

fegen_rust_cst = pytest.importorskip(
    "fegen_rust_cst",
    reason="fegen_rust_cst not built; run 'make build-fegen-rust-cst' first",
)

import fltk.fegen.fltk_parser as py_parser_mod  # noqa: E402
from fltk.fegen.pyrt import terminalsrc as tsrc  # noqa: E402


def test_constructor_default_capture_trivia():
    p = fegen_rust_cst.Parser("x := y ;")
    assert p.capture_trivia is False


def test_constructor_capture_trivia_positional():
    p = fegen_rust_cst.Parser("x := y ;", True)
    assert p.capture_trivia is True


def test_constructor_capture_trivia_keyword():
    p = fegen_rust_cst.Parser("x := y ;", capture_trivia=True)
    assert p.capture_trivia is True


def test_constructor_non_str_raises_type_error():
    with pytest.raises(TypeError):
        fegen_rust_cst.Parser(42)


def test_pos_validation_negative_raises_value_error():
    p = fegen_rust_cst.Parser("hello")
    with pytest.raises(ValueError):
        p.apply__parse_grammar(-1)


def test_pos_validation_too_large_raises_value_error():
    text = "x := y ;"
    p = fegen_rust_cst.Parser(text)
    with pytest.raises(ValueError):
        p.apply__parse_grammar(len(text) + 1)


def test_pos_at_len_valid_nullable_or_not():
    """pos == len(text) must not raise ValueError."""
    text = "x := y ;"
    p = fegen_rust_cst.Parser(text)
    result = p.apply__parse_grammar(len(text))
    assert result is None


def test_apply_result_pos_attribute():
    p = fegen_rust_cst.Parser('x := "a" ;')
    r = p.apply__parse_rule(0)
    assert r is not None
    assert isinstance(r.pos, int)
    assert r.pos == len('x := "a" ;')


def test_apply_result_result_is_cst_node():
    p = fegen_rust_cst.Parser('x := "a" ;')
    r = p.apply__parse_rule(0)
    assert r is not None
    assert isinstance(r.result, fegen_rust_cst.Rule)


def test_apply_result_twice_same_object():
    """Two apply__ calls at same pos return the same .result object (registry identity)."""
    p = fegen_rust_cst.Parser('x := "a" ;')
    r1 = p.apply__parse_rule(0)
    r2 = p.apply__parse_rule(0)
    assert r1 is not None and r2 is not None
    assert r1.result is r2.result


def test_rule_names_indexable():
    p = fegen_rust_cst.Parser("")
    names = p.rule_names
    assert len(names) > 0
    assert names[0] == "grammar"


def test_rule_names_matches_python_parser():
    """rule_names must match Python parser's rule_names element-wise."""
    text = ""
    ts = tsrc.TerminalSource(text)
    py_p = py_parser_mod.Parser(terminalsrc=ts)
    rust_p = fegen_rust_cst.Parser(text)
    assert list(rust_p.rule_names) == list(py_p.rule_names)


def test_error_position_none_on_fresh_parser():
    p = fegen_rust_cst.Parser("")
    assert p.error_position() is None


def test_error_message_on_fresh_parser():
    """error_message() must return the no-failure form (same as Python backend) before any parse.

    Both backends format a stub 'Syntax error at line 1 col 0' message when no parse error
    has been recorded (longest_parse_len == -1); this pins that the Rust backend matches.
    """
    from fltk.fegen.pyrt import errors as py_errors  # noqa: PLC0415
    from fltk.fegen.pyrt import terminalsrc as tsrc  # noqa: PLC0415

    text = ""
    ts = tsrc.TerminalSource(text)
    py_p = py_parser_mod.Parser(terminalsrc=ts)
    py_msg = py_errors.format_error_message(py_p.error_tracker, ts, lambda rid: py_p.rule_names[rid])

    rust_p = fegen_rust_cst.Parser(text)
    rust_msg = rust_p.error_message()
    assert rust_msg == py_msg, f"No-failure message mismatch:\nPython: {py_msg!r}\nRust: {rust_msg!r}"


def test_error_position_after_failed_parse():
    text = "broken :="
    p = fegen_rust_cst.Parser(text)
    p.apply__parse_grammar(0)
    pos = p.error_position()
    assert pos is not None
    assert isinstance(pos, int)
    assert 0 <= pos <= len(text)


def test_error_message_after_failed_parse():
    text = "broken :="
    p = fegen_rust_cst.Parser(text)
    p.apply__parse_grammar(0)
    msg = p.error_message()
    assert isinstance(msg, str)
    assert len(msg) > 0
    assert "Syntax error" in msg
    assert "Expected" in msg
