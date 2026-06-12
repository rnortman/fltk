"""Tests for fltk.fegen.pyrt.errors — escape_control_chars and format_error_message.

Expected strings are cross-pinned with the Rust unit tests in
crates/fltk-parser-core/src/errors.rs to verify byte-identical output.
"""

from fltk.fegen.pyrt import terminalsrc
from fltk.fegen.pyrt.errors import ErrorTracker, escape_control_chars, format_error_message

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
    assert escape_control_chars("→") == "→"


def test_escape_control_chars_mixed():
    assert escape_control_chars("ab\x1bcd") == "ab\\x1bcd"


def test_escape_control_chars_empty():
    assert escape_control_chars("") == ""


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
    ts = _ts("\x00\x01\x1b\r\x7fabc\n")
    t = ErrorTracker()
    t.fail_literal(0, 0, "x")
    msg = format_error_message(t, ts, _rule_name)
    for ch in msg:
        cp = ord(ch)
        assert not ((cp < 0x20 and cp not in (0x09, 0x0A)) or cp == 0x7F or (0x80 <= cp <= 0x9F)), (
            f"raw control char U+{cp:04X} found in message: {msg!r}"
        )


def test_format_error_message_col_minus_one():
    # col == -1: max(col, 0) = 0, empty prefix, pad = 0.
    # "abc" (3 chars, no newline): sentinel quirk → line_span=[0,2), line_text="ab".
    ts = _ts("abc")
    t = ErrorTracker()  # longest_parse_len = -1
    msg = format_error_message(t, ts, _rule_name)
    expected = "Syntax error at line 1 col 0:\nab\n^\nExpected:\n"
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
    # sentinel quirk: "hello world" (11 chars, no newline) → line_span excludes last char
    expected = "Syntax error at line 1 col 6:\nhello worl\n     ^\nExpected:\n  From rule \"expr\":\n    LITERAL: '!'\n"
    assert msg == expected, f"got: {msg!r}"
