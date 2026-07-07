"""Tests for ``LineIndex`` -- LSP-conformant offset <-> position math."""

from __future__ import annotations

import pytest

from fltk.lsp.positions import LineIndex, PositionEncoding

UTF16 = PositionEncoding.UTF16
UTF32 = PositionEncoding.UTF32

# U+1D400 MATHEMATICAL BOLD CAPITAL A: one codepoint, two utf-16 code units.
ASTRAL = "\U0001d400"


def test_single_line_no_terminator() -> None:
    idx = LineIndex("abc")
    assert idx.line_of(0) == 0
    assert idx.line_of(3) == 0
    assert idx.line_bounds(0) == (0, 3)
    assert idx.offset_to_position(2, UTF32) == (0, 2)
    assert idx.end_position(UTF32) == (0, 3)


def test_lf_separator() -> None:
    idx = LineIndex("a\nb")
    assert idx.line_of(0) == 0
    assert idx.line_of(2) == 1
    assert idx.line_bounds(0) == (0, 1)
    assert idx.line_bounds(1) == (2, 3)


def test_all_three_separators_mixed() -> None:
    # "a\nb\r\nc\rd" -> four lines a, b, c, d with \n, \r\n and a lone \r.
    idx = LineIndex("a\nb\r\nc\rd")
    assert idx.line_bounds(0) == (0, 1)  # a  (\n)
    assert idx.line_bounds(1) == (2, 3)  # b  (\r\n)
    assert idx.line_bounds(2) == (5, 6)  # c  (lone \r)
    assert idx.line_bounds(3) == (7, 8)  # d  (eof)
    assert idx.line_of(3) == 1  # the \r of the \r\n belongs to line 1
    assert idx.line_of(4) == 1  # the \n of the \r\n belongs to line 1
    assert idx.line_of(5) == 2


def test_empty_text() -> None:
    idx = LineIndex("")
    assert idx.line_of(0) == 0
    assert idx.line_bounds(0) == (0, 0)
    assert idx.offset_to_position(0, UTF32) == (0, 0)
    assert idx.end_position(UTF32) == (0, 0)


def test_trailing_newline_creates_empty_last_line() -> None:
    idx = LineIndex("a\n")
    assert idx.line_bounds(0) == (0, 1)
    assert idx.line_bounds(1) == (2, 2)
    assert idx.end_position(UTF32) == (1, 0)


def test_astral_columns_utf16_vs_utf32() -> None:
    text = f"a{ASTRAL}b"  # a, astral, b -> offsets 0,1,2 ; len 3
    idx = LineIndex(text)
    # utf-32 columns are codepoint counts.
    assert idx.offset_to_position(2, UTF32) == (0, 2)
    assert idx.end_position(UTF32) == (0, 3)
    # utf-16 counts the astral char as two code units.
    assert idx.offset_to_position(2, UTF16) == (0, 3)
    assert idx.end_position(UTF16) == (0, 4)


def test_position_to_offset_utf16_astral_roundtrip() -> None:
    text = f"a{ASTRAL}b"
    idx = LineIndex(text)
    assert idx.position_to_offset(0, 3, UTF16) == 2
    assert idx.position_to_offset(0, 4, UTF16) == 3


def test_position_to_offset_clamps_inside_surrogate_pair() -> None:
    text = f"a{ASTRAL}b"
    idx = LineIndex(text)
    # Column 2 (utf-16) lands in the middle of the astral pair -> clamps to its start.
    assert idx.position_to_offset(0, 2, UTF16) == 1


@pytest.mark.parametrize("enc", [UTF16, UTF32])
def test_offset_position_roundtrip_lf_only(enc: PositionEncoding) -> None:
    text = "hello\nworld\nfoo"
    idx = LineIndex(text)
    for offset in range(len(text) + 1):
        line, char = idx.offset_to_position(offset, enc)
        assert idx.position_to_offset(line, char, enc) == offset


def test_clamp_offset_past_eof() -> None:
    idx = LineIndex("abc")
    assert idx.offset_to_position(100, UTF32) == (0, 3)


def test_clamp_character_past_line_end() -> None:
    idx = LineIndex("abc\ndef")
    assert idx.position_to_offset(0, 100, UTF32) == 3  # end of "abc", excluding the \n


def test_clamp_line_past_last() -> None:
    idx = LineIndex("abc")
    assert idx.position_to_offset(5, 0, UTF32) == 3


def test_clamp_negative_inputs() -> None:
    idx = LineIndex("abc")
    assert idx.offset_to_position(-1, UTF32) == (0, 0)
    assert idx.position_to_offset(-1, 0, UTF32) == 0
    assert idx.position_to_offset(0, -5, UTF32) == 0
