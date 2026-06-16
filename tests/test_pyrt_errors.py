"""Tests for fltk.fegen.pyrt.errors — escape_control_chars and format_error_message.

Expected strings are cross-pinned with the Rust unit tests in
crates/fltk-cst-core/src/escape.rs to verify byte-identical output.
"""

from fltk.fegen.pyrt import terminalsrc
from fltk.fegen.pyrt.errors import ErrorTracker, _needs_escape, escape_control_chars, format_error_message

# ── escape_control_chars ──────────────────────────────────────────────────────


def test_escape_control_chars_c0():
    assert escape_control_chars("\x00") == "\\x00"
    assert escape_control_chars("\x1b") == "\\x1b"
    assert escape_control_chars("\r") == "\\x0d"
    assert escape_control_chars("\n") == "\\x0a"


def test_escape_control_chars_del():
    assert escape_control_chars("\x7f") == "\\x7f"


def test_escape_control_chars_c1():
    assert escape_control_chars("\u009b") == "\\x9b"
    assert escape_control_chars("\u0080") == "\\x80"
    assert escape_control_chars("\u009f") == "\\x9f"


def test_escape_control_chars_tab_passthrough():
    assert escape_control_chars("\t") == "\t"


def test_escape_control_chars_printable_passthrough():
    assert escape_control_chars("hello") == "hello"


def test_escape_control_chars_multibyte_passthrough():
    assert escape_control_chars("→") == "→"  # →


def test_escape_control_chars_mixed():
    assert escape_control_chars("ab\x1bcd") == "ab\\x1bcd"


def test_escape_control_chars_empty():
    assert escape_control_chars("") == ""


# ── New rows: bidi embedding/override ────────────────────────────────────────


def test_escape_bidi_embedding_override():
    assert escape_control_chars("\u202a") == "\\u202a"  # LRE
    assert escape_control_chars("\u202b") == "\\u202b"  # RLE
    assert escape_control_chars("\u202c") == "\\u202c"  # PDF
    assert escape_control_chars("\u202d") == "\\u202d"  # LRO
    assert escape_control_chars("\u202e") == "\\u202e"  # RLO


# ── New rows: bidi isolates ───────────────────────────────────────────────────


def test_escape_bidi_isolates():
    assert escape_control_chars("\u2066") == "\\u2066"  # LRI
    assert escape_control_chars("\u2067") == "\\u2067"  # RLI
    assert escape_control_chars("\u2068") == "\\u2068"  # FSI
    assert escape_control_chars("\u2069") == "\\u2069"  # PDI


# ── New rows: implicit bidi marks (ALM, LRM, RLM) ────────────────────────────


def test_escape_bidi_implicit_marks():
    assert escape_control_chars("\u200e") == "\\u200e"  # LRM
    assert escape_control_chars("\u200f") == "\\u200f"  # RLM
    assert escape_control_chars("\u061c") == "\\u061c"  # ALM


# ── New rows: line/paragraph separators ──────────────────────────────────────


def test_escape_line_paragraph_separators():
    assert escape_control_chars("\u2028") == "\\u2028"  # LS
    assert escape_control_chars("\u2029") == "\\u2029"  # PS


# ── New rows: zero-width characters ──────────────────────────────────────────


def test_escape_zero_width_chars():
    assert escape_control_chars("\u200b") == "\\u200b"  # ZWSP
    assert escape_control_chars("\u200c") == "\\u200c"  # ZWNJ
    assert escape_control_chars("\u200d") == "\\u200d"  # ZWJ
    assert escape_control_chars("\u2060") == "\\u2060"  # Word Joiner
    assert escape_control_chars("\ufeff") == "\\ufeff"  # ZWNBSP/BOM


# ── Boundary passthroughs (must NOT be escaped) ───────────────────────────────


def test_escape_passthrough_boundary_chars():
    assert escape_control_chars("\u200a") == "\u200a"  # U+200A hair space
    assert escape_control_chars("\u2010") == "\u2010"  # U+2010 hyphen
    assert escape_control_chars("\u2027") == "\u2027"  # U+2027 hyphenation point
    assert escape_control_chars("\u202f") == "\u202f"  # U+202F narrow no-break space
    assert escape_control_chars("\u205f") == "\u205f"  # U+205F math space
    assert escape_control_chars("\u2065") == "\u2065"  # U+2065 boundary before LRI range
    assert escape_control_chars("\u206a") == "\u206a"  # U+206A boundary above LRI range (U+2069)
    assert escape_control_chars("\ufffd") == "\ufffd"  # U+FFFD replacement character
    assert escape_control_chars("\U0001f600") == "\U0001f600"  # astral (emoji)
    assert escape_control_chars("\t") == "\t"  # TAB explicitly excluded


# ── Mixed \xHH and \uXXXX in same string ─────────────────────────────────────


def test_escape_mixed_xhh_and_uxxxx():
    # ESC (C0) + RLO (bidi) + plain text
    assert escape_control_chars("\x1b\u202eabc") == "\\x1b\\u202eabc"
    # C1 (\x80) + LRM (bidi mark) + TAB (passthrough) + plain text
    assert escape_control_chars("\x80\u200e\tabc") == "\\x80\\u200e\tabc"


# ── format_error_message ──────────────────────────────────────────────────────


def _ts(text: str) -> terminalsrc.TerminalSource:
    return terminalsrc.TerminalSource(text)


def _rule_name(rule_id: int) -> str:
    names = ["rule"]
    return names[rule_id] if rule_id < len(names) else f"<unknown rule {rule_id}>"


def test_format_error_message_with_controls_in_line():
    # Failing line contains \x1b[31m; error at col 0.
    ts = _ts("\x1b[31mabc")
    t = ErrorTracker()
    t.fail_literal(0, 0, "x")
    msg = format_error_message(t, ts, _rule_name)
    assert "\\x1b[31m" in msg, f"ESC should be escaped: {msg!r}"
    assert "\x1b" not in msg, f"raw ESC must not appear in message: {msg!r}"
    # caret at col 0 → no leading spaces before ^
    lines = msg.splitlines()
    assert lines[2] == "^", f"caret at col 0: {msg!r}"


def test_format_error_message_caret_alignment_with_escaped_prefix():
    # Line: "ab\x1bcd\n", error at col 3 ('c').
    # Prefix = "ab\x1b" (3 chars) → escaped "ab\\x1b" (6 chars) → pad = 6.
    ts = _ts("ab\x1bcd\n")
    t = ErrorTracker()
    t.fail_literal(3, 0, "x")
    msg = format_error_message(t, ts, _rule_name)
    lines = msg.splitlines()
    assert lines[1] == "ab\\x1bcd", f"escaped line: {msg!r}"
    assert lines[2] == "      ^", f"pad=6 spaces then ^: {msg!r}"


def test_format_error_message_caret_at_control_char():
    # Error column is itself a control character: caret lands on the '\' of its escape.
    # Line: "ab\x1bcd\n", error at col 2 (the ESC).
    # Prefix = "ab" (2 chars, no controls) → escaped_prefix = "ab" → pad = 2.
    # Escaped line = "ab\\x1bcd"; caret line = "  ^".
    ts = _ts("ab\x1bcd\n")
    t = ErrorTracker()
    t.fail_literal(2, 0, "x")  # col=2, the ESC
    msg = format_error_message(t, ts, _rule_name)
    lines = msg.splitlines()
    assert lines[1] == "ab\\x1bcd", f"escaped line: {msg!r}"
    assert lines[2] == "  ^", f"pad=2 spaces then ^: {msg!r}"


def test_format_error_message_no_raw_controls_in_output():
    # Assert no raw C0 (except \t/\n), no U+007F, no U+0080-U+009F in output.
    ts = _ts("\x00\x01\x1b\r\x7f\u009babc\n")
    t = ErrorTracker()
    t.fail_literal(0, 0, "x")
    msg = format_error_message(t, ts, _rule_name)
    for ch in msg:
        cp = ord(ch)
        assert not ((cp < 0x20 and cp not in (0x09, 0x0A)) or cp == 0x7F or (0x80 <= cp <= 0x9F)), (
            f"raw control char U+{cp:04X} found in message: {msg!r}"
        )


def test_format_error_message_no_raw_extended_set_in_output():
    # Assert no raw codepoint from the full extended escape set appears in the
    # formatted message when the input contains one char from every class.
    # Input: NUL, ESC, CR, DEL, C1(U+009B), ALM, ZWSP, LRM, LS, RLO, WJ, LRI, BOM, "abc\n"
    ts = _ts("\x00\x1b\r\x7f\u009b\u061c\u200b\u200e\u2028\u202e\u2060\u2066\ufeffabc\n")
    t = ErrorTracker()
    t.fail_literal(0, 0, "x")
    msg = format_error_message(t, ts, _rule_name)
    for ch in msg:
        cp = ord(ch)
        # Use _needs_escape as the oracle so the sweep cannot drift from the implementation.
        # LF (0x0A) is a C0 control that _needs_escape would flag, but it appears
        # raw as a line separator in the formatted message — exclude it.
        assert not (_needs_escape(cp) and cp != 0x0A), f"raw escaped-set char U+{cp:04X} found in message: {msg!r}"


def test_format_error_message_bidi_golden():
    # Failing line contains U+202E (RLO bidi override); error at col 0.
    # Escaped line starts with "\\u202e"; caret at col 0 → no pad.
    ts = _ts("\u202e123")
    t = ErrorTracker()
    t.fail_literal(0, 0, "x")
    msg = format_error_message(t, ts, _rule_name)
    lines = msg.splitlines()
    assert lines[1].startswith("\\u202e"), f"escaped line starts with \\u202e: {msg!r}"
    assert lines[2] == "^", f"caret at col 0: {msg!r}"
    assert "\u202e" not in msg, f"raw U+202E must not appear: {msg!r}"


def test_format_error_message_bidi_caret_alignment():
    # Line: U+202E (RLO) + "abc\n"; error at col 1 (the 'a').
    # Prefix = U+202E (1 codepoint) → escaped "\\u202e" (6 chars) → pad = 6.
    ts = _ts("\u202eabc\n")
    t = ErrorTracker()
    t.fail_literal(1, 0, "x")  # col=1, the 'a'
    msg = format_error_message(t, ts, _rule_name)
    lines = msg.splitlines()
    assert lines[1] == "\\u202eabc", f"escaped line: {msg!r}"
    assert lines[2] == "      ^", f"pad=6 spaces (\\u202e = 6 chars): {msg!r}"


def test_format_error_message_col_minus_one():
    # col == -1: max(col, 0) = 0, empty prefix, pad = 0.
    # "abc" (3 chars, no newline): sentinel = len = 3, line_span=[0,3), line_text="abc".
    ts = _ts("abc")
    t = ErrorTracker()  # longest_parse_len = -1
    msg = format_error_message(t, ts, _rule_name)
    expected = "Syntax error at line 1 col 0:\nabc\n^\nExpected:\n"
    assert msg == expected, f"got: {msg!r}"


def test_format_error_message_empty_input():
    # Empty input: sentinel quirk → line_text="", pad=0.
    ts = _ts("")
    t = ErrorTracker()
    msg = format_error_message(t, ts, _rule_name)
    expected = "Syntax error at line 1 col 0:\n\n^\nExpected:\n"
    assert msg == expected, f"got: {msg!r}"


def test_format_error_message_ascii_clean_unchanged():
    # ASCII-clean input: output identical to pre-escape behavior.
    ts = _ts("hello world")
    t = ErrorTracker()
    t.fail_literal(5, 0, "!")
    msg = format_error_message(t, ts, lambda _rid: "expr")
    # sentinel = len = 11, line_span=[0,11), line_text="hello world" (full line)
    expected = (
        "Syntax error at line 1 col 6:\nhello world\n     ^\nExpected:\n  From rule \"expr\":\n    LITERAL: '!'\n"
    )
    assert msg == expected, f"got: {msg!r}"
