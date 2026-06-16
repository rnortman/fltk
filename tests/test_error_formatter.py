"""Tests for fltk.fegen.pyrt.error_formatter.format_source_line."""

from __future__ import annotations

import pytest

import fltk._native as _fltk_native
from fltk.fegen.pyrt.error_formatter import format_source_line
from fltk.fegen.pyrt.terminalsrc import SourceText as PySourceText
from fltk.fegen.pyrt.terminalsrc import Span as PySpan
from fltk.fegen.pyrt.terminalsrc import TerminalSource, UnknownSpan

_rust_available = hasattr(_fltk_native, "Span")


class TestOutputShape:
    """format_source_line output shape and content."""

    def test_with_explicit_filename(self):
        """Header uses 'In <file>:<line+1>:<col+1>:' when filename is supplied.

        The sentinel is now `len` for the last line without trailing '\\n', so
        line_span covers the full last line including the last character.
        """
        src = PySourceText("hello\nworld", filename="test.fltkg")
        span = PySpan.with_source(6, 7, src)
        result = format_source_line(span, "boom", filename="explicit.fltkg")
        lines = result.split("\n")
        assert lines[0] == ""
        assert lines[1] == "In explicit.fltkg:2:1:"
        assert lines[2] == "world"  # full last line (sentinel=len, not len-1)
        assert lines[3] == "^"
        assert lines[4] == "boom"
        assert lines[5] == ""  # trailing newline

    def test_full_string_literal(self):
        """Assert the full multi-line string literally (output shape test).

        The sentinel for the last line without trailing '\\n' is now `len` (exclusive),
        so line_span covers the entire last line including the last character.
        For 'hello\\nworld', line_span for 'world' is Span(6, 11) = 'world' (all 5 chars).
        """
        src = PySourceText("hello\nworld")
        span = PySpan.with_source(6, 7, src)
        result = format_source_line(span, "unexpected token", filename="f.clk")
        expected = "\nIn f.clk:2:1:\nworld\n^\nunexpected token\n"
        assert result == expected

    def test_mid_line_caret(self):
        """Caret at column 3 puts 3 spaces before the caret."""
        src = PySourceText("hello world")
        span = PySpan.with_source(3, 4, src)  # 'l', line 0, col 3
        result = format_source_line(span, "err", filename="x.f")
        lines = result.split("\n")
        assert lines[3] == "   ^"  # 3 spaces

    def test_header_1based_line_and_col(self):
        """Header renders 1-based line and column (0-based + 1)."""
        src = PySourceText("abc\ndef")
        span = PySpan.with_source(5, 6, src)  # 'e', line 1, col 1
        result = format_source_line(span, "err", filename="f")
        assert "2:2:" in result  # line 2, col 2

    def test_line_text_in_output(self):
        """The offending line text appears in the output.

        Use a source with trailing \\n to get a clean line_span (sentinel = last \\n).
        """
        src = PySourceText("first line\nsecond line\nthird\n")
        # "first line\n" = 11 chars (0-10 + \n=10), "second line\n" starts at 11
        # pos 11 = 's' in "second line"
        span = PySpan.with_source(11, 12, src)
        result = format_source_line(span, "err", filename="f")
        assert "second line" in result

    def test_trailing_newline(self):
        """Output always ends with a newline."""
        src = PySourceText("abc")
        span = PySpan.with_source(0, 1, src)
        result = format_source_line(span, "msg", filename="f")
        assert result.endswith("\n")


class TestFilenamePrecedence:
    """Filename resolution: explicit arg > span.filename() > None."""

    def test_explicit_filename_wins_over_span_filename(self):
        """Explicit filename= argument wins over span.filename()."""
        src = PySourceText("hello", filename="span-file.fltkg")
        span = PySpan.with_source(0, 1, src)
        result = format_source_line(span, "msg", filename="override.fltkg")
        assert "In override.fltkg:" in result
        assert "span-file" not in result

    def test_span_filename_used_when_no_explicit(self):
        """span.filename() is used when no explicit filename argument is given."""
        src = PySourceText("hello", filename="from-span.fltkg")
        span = PySpan.with_source(0, 1, src)
        result = format_source_line(span, "msg")
        assert "In from-span.fltkg:" in result

    def test_no_filename_degrades_to_at_line(self):
        """When neither explicit filename nor span.filename(), header uses 'At line N, column M:'."""
        src = PySourceText("hello")
        span = PySpan.with_source(0, 1, src)
        result = format_source_line(span, "msg")
        assert result.startswith("\nAt line 1, column 1:")
        assert "In " not in result

    def test_explicit_none_falls_back_to_span_filename(self):
        """Passing filename=None explicitly falls back to span.filename()."""
        src = PySourceText("hello", filename="fallback.fltkg")
        span = PySpan.with_source(0, 1, src)
        result = format_source_line(span, "msg", filename=None)
        assert "In fallback.fltkg:" in result

    def test_explicit_filename_wins_even_when_span_has_filename(self):
        """Explicit filename replaces span filename (not both emitted)."""
        src = PySourceText("hello", filename="original.fltkg")
        span = PySpan.with_source(0, 1, src)
        result = format_source_line(span, "msg", filename="replacement.fltkg")
        assert "replacement.fltkg" in result
        assert "original.fltkg" not in result


class TestMultibyteCaret:
    """Caret alignment for multibyte (non-ASCII) sources."""

    def test_multibyte_caret_alignment(self):
        """A span after a multibyte char puts caret at the correct codepoint column."""
        # "café\nrésumé": café = 4 codepoints (c=0, a=1, f=2, é=3), \n=4, r=5...
        src = PySourceText("café\nrésumé")
        # 'é' in "café" is codepoint 3, line 0
        span = PySpan.with_source(3, 4, src)
        result = format_source_line(span, "here", filename="f")
        lines = result.split("\n")
        assert lines[2] == "café"
        assert lines[3] == "   ^"  # 3 spaces (col=3)

    def test_multibyte_second_line(self):
        """Multibyte on second line: col counts codepoints, not bytes.

        Use trailing \\n to avoid sentinel truncation of the last line.
        """
        src = PySourceText("abc\nrésumé\n")
        # 'é' in "résumé": r=4(start of line 2), é=5, line 1, col 1
        span = PySpan.with_source(5, 6, src)
        result = format_source_line(span, "err", filename="f")
        lines = result.split("\n")
        # With trailing \n, the \n at end of "résumé\n" is a real line_end
        # so line_span covers the full word
        assert "résumé" in lines[2]
        assert lines[3] == " ^"  # 1 space (col=1)


class TestControlCharEscaping:
    """format_source_line escapes control/bidi characters in source line and filename."""

    def test_control_char_in_source_line_is_escaped(self):
        """ESC in source line is replaced by 'U+001B', not passed through raw."""
        src = PySourceText("hello\x1b[2Jworld")  # ESC sequence in source
        span = PySpan.with_source(0, 1, src)
        result = format_source_line(span, "err", filename="f")
        assert "\x1b" not in result, "Raw ESC must not appear in formatter output"
        assert "U+001B" in result

    def test_cr_in_source_line_is_escaped(self):
        """CR (\\r) in source line is escaped."""
        src = PySourceText("hello\rworld")
        span = PySpan.with_source(0, 1, src)
        result = format_source_line(span, "err", filename="f")
        assert "\r" not in result
        assert "U+000D" in result

    def test_bidi_override_in_source_line_is_escaped(self):
        """U+202E (RLO bidi override) in source line is escaped."""
        rlo = chr(0x202E)  # RIGHT-TO-LEFT OVERRIDE — avoid literal bidi char in source
        src = PySourceText(f"hello{rlo}world")
        span = PySpan.with_source(0, 1, src)
        result = format_source_line(span, "err", filename="f")
        assert rlo not in result
        assert "U+202E" in result

    def test_newline_in_filename_is_escaped(self):
        """A newline in the filename is escaped so the header remains a single line.

        The raw \\n in the filename is replaced by 'U+000A', keeping the 'In <file>:L:C:'
        header on one line rather than injecting a second line into the output.
        """
        src = PySourceText("hello")
        span = PySpan.with_source(0, 1, src)
        result = format_source_line(span, "err", filename="file\nrm -rf ~")
        lines = result.split("\n")
        # With escaping, the raw \n is gone from the output (replaced by 'U+000A').
        assert "\n" not in result.split("\n")[1], "Escaped filename must not contain a raw newline"
        # The header line should contain the escaped representation, not raw newline.
        header_line = lines[1]
        assert "U+000A" in header_line, f"Escaped newline 'U+000A' should appear in header: {header_line!r}"
        # No raw newline embedded in the filename means the header is one line.
        assert header_line.startswith("In "), f"Header should start with 'In ': {header_line!r}"

    def test_clean_source_passes_through(self):
        """Normal ASCII source is not mangled by escaping."""
        src = PySourceText("hello world")
        span = PySpan.with_source(6, 7, src)
        result = format_source_line(span, "err", filename="f.clk")
        assert "hello world" in result

    def test_caret_still_aligns_after_escaping(self):
        """Caret aligns with escaped text, not original text width."""
        # ESC at col 0 expands to 6 chars "U+001B"; caret should be at col 0 (0 spaces).
        src = PySourceText("\x1b!")
        span = PySpan.with_source(0, 1, src)
        result = format_source_line(span, "err", filename="f")
        lines = result.split("\n")
        # Caret line (lines[3]) should start with "^" (0 spaces, col=0).
        assert lines[3] == "^", f"Caret line should be '^' but got {lines[3]!r}"


class TestSentinelSpanRaises:
    """format_source_line raises ValueError for non-source-bearing spans."""

    def test_unknown_span_raises_value_error(self):
        """UnknownSpan (sourceless sentinel) raises ValueError."""
        with pytest.raises(ValueError):
            format_source_line(UnknownSpan, "msg")

    def test_sourceless_span_raises_value_error(self):
        """A sourceless Python span raises ValueError."""
        span = PySpan(0, 5)
        with pytest.raises(ValueError):
            format_source_line(span, "msg")

    def test_negative_start_raises_value_error(self):
        """A source-bearing span with negative start raises ValueError."""
        src = PySourceText("hello")
        span = PySpan.with_source(-1, 0, src)
        with pytest.raises(ValueError):
            format_source_line(span, "msg")


class TestCrossBackend:
    """Cross-backend: Python and Rust backends produce identical output."""

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_same_output_both_backends(self):
        """format_source_line returns identical string for Python and Rust spans."""
        text = "hello\nworld\n"
        # Python span
        py_src = PySourceText(text, filename="test.fltkg")
        py_span = PySpan.with_source(6, 7, py_src)  # 'w', line 1, col 0
        py_result = format_source_line(py_span, "err")

        # Rust span
        rust_source_text_cls = _fltk_native.SourceText
        rust_span_cls = _fltk_native.Span
        rs_src = rust_source_text_cls(text, filename="test.fltkg")  # type: ignore[call-arg]
        rs_span = rust_span_cls.with_source(6, 7, rs_src)
        rs_result = format_source_line(rs_span, "err")

        assert py_result == rs_result

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_span_filename_header_both_backends(self):
        """span.filename() fallback path produces 'In <file>:' header on both backends."""
        text = "abc\ndef\n"
        # Python
        py_src = PySourceText(text, filename="from-span.fltkg")
        py_span = PySpan.with_source(4, 5, py_src)
        py_result = format_source_line(py_span, "msg")  # no explicit filename

        # Rust
        rust_source_text_cls = _fltk_native.SourceText
        rust_span_cls = _fltk_native.Span
        rs_src = rust_source_text_cls(text, filename="from-span.fltkg")  # type: ignore[call-arg]
        rs_span = rust_span_cls.with_source(4, 5, rs_src)
        rs_result = format_source_line(rs_span, "msg")

        assert py_result == rs_result
        assert "In from-span.fltkg:" in py_result

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_no_filename_both_backends_degrade_identically(self):
        """No filename on either backend produces identical 'At line N, column M:' header."""
        text = "hello"
        py_span = PySpan.with_source(1, 2, PySourceText(text))
        rust_span_cls = _fltk_native.Span
        rust_source_text_cls = _fltk_native.SourceText
        rs_span = rust_span_cls.with_source(1, 2, rust_source_text_cls(text))  # type: ignore[call-arg]

        py_result = format_source_line(py_span, "err")
        rs_result = format_source_line(rs_span, "err")
        assert py_result == rs_result
        assert py_result.startswith("\nAt line 1, column 2:")

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_same_output_no_trailing_newline(self):
        """Cross-backend formatter output matches for a span on the last line without trailing \\n.

        This is the regression guard for the sentinel off-by-one fix: if one backend
        uses sentinel=len-1 (old bug) and the other uses sentinel=len, the displayed
        source line would differ (truncated vs full), making py_result != rs_result.
        Source 'hello\\nworld', last line 'world' at pos 6; sentinel=len=11 → text='world'.
        """
        text = "hello\nworld"  # no trailing newline
        py_src = PySourceText(text, filename="t.fltkg")
        py_span = PySpan.with_source(6, 7, py_src)  # 'w', line 1, col 0
        py_result = format_source_line(py_span, "err")

        rs_src = _fltk_native.SourceText(text, filename="t.fltkg")  # type: ignore[call-arg]
        rs_span = _fltk_native.Span.with_source(6, 7, rs_src)
        rs_result = format_source_line(rs_span, "err")

        assert py_result == rs_result, (
            f"Backend mismatch on no-trailing-newline source:\npy={py_result!r}\nrs={rs_result!r}"
        )
        # Confirm the full last line (not truncated) appears in the output.
        assert "world" in py_result, "Expected 'world' (full last line) in formatter output"

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_parser_produced_span_filename_python_backend(self):
        """Python-parser-produced span carries the filename set on TerminalSource."""
        from fltk.fegen import fltk_parser  # noqa: PLC0415

        text = "rule := 'foo';"
        ts = TerminalSource(text, filename="grammar.fltkg")
        parser = fltk_parser.Parser(ts)
        result = parser.apply__parse_rule(0)
        assert result is not None
        span = result.result.span
        # span.filename() must return the filename threaded from TerminalSource
        assert span.filename() == "grammar.fltkg"
        # format_source_line should render the filename
        fmt = format_source_line(span, "test error")
        assert "In grammar.fltkg:" in fmt
