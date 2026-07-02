"""Tests for SpanProtocol, AnySpan, and the backend selector module."""

import contextlib
import importlib
import sys
import types
import warnings

import pytest

import fltk._native as _fltk_native
import fltk.fegen.pyrt.span as _span_selector
import fltk.fegen.pyrt.span_protocol as _span_protocol
from fltk.fegen.pyrt.span_protocol import AnySpan, SpanProtocol
from fltk.fegen.pyrt.terminalsrc import SourceText as PySourceText
from fltk.fegen.pyrt.terminalsrc import Span as PySpan
from fltk.fegen.pyrt.terminalsrc import TerminalSource, UnknownSpan

_rust_available = hasattr(_fltk_native, "Span")


@contextlib.contextmanager
def _native_replaced(fake: object, module_to_reload: types.ModuleType):
    """Install ``fake`` at ``sys.modules["fltk._native"]`` for the block, then restore.

    Cleanup restores the *saved original module object* before the restorative reload —
    it never delete-and-reimports. The PyO3 native extension must NEVER be re-imported
    fresh in-process: a second genuine init panics with a ``BaseException``-derived
    ``PanicException`` (``UNKNOWN_SPAN already set; module initialized twice``) that
    escapes ``except Exception`` and poisons the rest of the pytest session. This
    invariant is why every backend-selector reload test funnels through this helper.

    ``fake`` may be ``None`` (forces ``ImportError`` on the probe) or a stand-in object
    such as ``_BrokenNative``.
    """
    saved = sys.modules.get("fltk._native")
    try:
        sys.modules["fltk._native"] = fake  # type: ignore[assignment]
        yield
    finally:
        if saved is not None:
            sys.modules["fltk._native"] = saved
        else:
            sys.modules.pop("fltk._native", None)
        importlib.reload(module_to_reload)  # restore real bindings for other tests


class TestBackendSelectorSilentFallback:
    """The backend probe falls back to pure-Python silently — no UserWarning."""

    def test_reload_without_native_emits_no_warning(self):
        # Reload span.py with fltk._native forced absent (and un-importable) so the
        # probe's except branch runs. It must fall back to the pure-Python backend
        # without emitting any warning. This pins the original-bug fix: a pure-Python
        # install printing a noisy warning on parser import.
        with _native_replaced(None, _span_selector):
            with warnings.catch_warnings():
                warnings.simplefilter("error")  # any warning becomes an exception
                reloaded = importlib.reload(_span_selector)
            # Fallback landed on the pure-Python backend.
            assert reloaded.Span is PySpan
            assert reloaded.SourceText is PySourceText


class _BrokenNative:
    """Fake present-but-broken native extension: attribute access raises OSError.

    The ``from ... import`` machinery only swallows ``AttributeError`` while resolving
    names, so the ``OSError`` propagates out of ``from fltk._native import ...``,
    faithfully simulating a corrupted/ABI-mismatched extension (C-level init crash).
    """

    def __getattr__(self, name: str) -> object:
        msg = "simulated broken native extension"
        raise OSError(msg)


class TestBackendSelectorBrokenNative:
    """A present-but-broken native extension must propagate loudly, not fall back silently."""

    def test_span_selector_broken_native_propagates(self):
        # With a fake broken native installed, reloading the span selector must raise the
        # underlying OSError rather than silently degrading to the pure-Python backend.
        with _native_replaced(_BrokenNative(), _span_selector), pytest.raises(OSError):
            importlib.reload(_span_selector)

    def test_span_protocol_broken_native_propagates(self):
        # Lockstep site: the AnySpan block in span_protocol.py must also propagate a
        # broken-native OSError rather than silently building a Python-only AnySpan.
        with _native_replaced(_BrokenNative(), _span_protocol), pytest.raises(OSError):
            importlib.reload(_span_protocol)

    def test_span_protocol_absent_native_falls_back_silently(self):
        # Absent native (ModuleNotFoundError, an ImportError subclass): the AnySpan block
        # must fall back silently (no warning) to the pure-Python Span. This is the AnySpan
        # analog of test_reload_without_native_emits_no_warning.
        with _native_replaced(None, _span_protocol):
            with warnings.catch_warnings():
                warnings.simplefilter("error")  # any warning becomes an exception
                reloaded = importlib.reload(_span_protocol)
            assert reloaded.AnySpan is PySpan


class TestProtocolConformancePython:
    def test_py_span_satisfies_protocol(self):
        s = PySpan(1, 5)
        assert isinstance(s, SpanProtocol)

    def test_py_span_with_source_satisfies_protocol(self):
        s = PySpan.with_source(0, 5, "hello")
        assert isinstance(s, SpanProtocol)


class TestAnySpanPython:
    def test_py_span_isinstance_anyspan(self):
        s = PySpan(1, 5)
        assert isinstance(s, AnySpan)


class TestProtocolConformanceRust:
    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_rust_span_satisfies_protocol(self):
        s = _fltk_native.Span(1, 5)
        assert isinstance(s, SpanProtocol)

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_rust_span_isinstance_anyspan(self):
        s = _fltk_native.Span(1, 5)
        assert isinstance(s, AnySpan)


class TestBackendSelector:
    def test_span_resolves_to_correct_backend(self):
        if _rust_available:
            assert _span_selector.Span is _fltk_native.Span
        else:
            assert _span_selector.Span is PySpan

    def test_unknown_span_resolves_to_correct_backend(self):
        if _rust_available:
            assert type(_span_selector.UnknownSpan) is _fltk_native.Span
        else:
            assert type(_span_selector.UnknownSpan) is PySpan

    def test_span_from_selector_satisfies_protocol(self):
        s = _span_selector.Span(1, 5)
        assert isinstance(s, SpanProtocol)

    def test_selector_span_exposes_start_end(self):
        # Downstream consumers access .start/.end on selector-produced spans (the backend
        # resolved at import time). Exercise that path directly rather than only the
        # backend-specific classes.
        s = _span_selector.Span(1, 5)
        assert isinstance(s, SpanProtocol)
        assert s.start == 1
        assert s.end == 5

    def test_unknown_span_equals_neg1_neg1(self):
        assert _span_selector.UnknownSpan == _span_selector.Span(-1, -1)


class TestSourceTextAndPortableWithSource:
    def test_selector_exports_source_text_as_real_class(self):
        """SourceText is a real class (not None) on both backends."""
        assert _span_selector.SourceText is not None
        assert isinstance(_span_selector.SourceText, type)

    def test_selector_source_text_is_native_on_rust_backend(self):
        if _rust_available:
            assert _span_selector.SourceText is _fltk_native.SourceText

    def test_portable_with_source_python_backend(self):
        """Portable SourceText construction works on the Python backend."""
        st = PySourceText("hello world")
        span = PySpan.with_source(6, 11, st)
        assert span.text() == "world"

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_portable_with_source_rust_backend(self):
        """Portable SourceText construction works on the Rust backend via selector."""
        st = _span_selector.SourceText("hello world")
        span = _span_selector.Span.with_source(6, 11, st)
        assert span.text() == "world"

    def test_backward_compat_str_python_backend(self):
        """Existing str callers still work on the Python backend."""
        span = PySpan.with_source(0, 5, "hello")
        assert span.text() == "hello"

    def test_python_source_text_is_frozen(self):
        """Python SourceText is frozen, matching Rust #[pyclass(frozen)]."""
        st = PySourceText("text")
        with pytest.raises((AttributeError, TypeError)):
            st._text = "other"  # type: ignore[misc]

    def test_with_source_rejects_unrecognized_type(self):
        """Passing an unrecognized type to with_source raises TypeError eagerly."""
        with pytest.raises(TypeError):
            PySpan.with_source(0, 5, 42)  # type: ignore[arg-type]


class TestProtocolHasStartEnd:
    def test_span_protocol_includes_start_end(self):
        # SpanProtocol now exposes start/end as codepoint-index attributes on both backends.
        assert hasattr(SpanProtocol, "start")
        assert hasattr(SpanProtocol, "end")
        # Expected protocol methods still exist on the class.
        assert callable(SpanProtocol.text)
        assert callable(SpanProtocol.len)
        assert callable(SpanProtocol.is_empty)
        assert callable(SpanProtocol.merge)
        assert callable(SpanProtocol.intersect)
        # New methods from span-line-col-api design.
        assert callable(SpanProtocol.line_col)
        assert callable(SpanProtocol.line_col_or_raise)
        assert callable(SpanProtocol.filename)

    def test_object_missing_start_end_is_not_protocol(self):
        # Structural-exclusion guard: a runtime_checkable Protocol that declares start/end
        # must reject an object that lacks them. This pins start/end as real structural
        # requirements, not just class attributes that hasattr happens to find.
        class _NoStartEnd:
            def text(self) -> str | None:
                return None

        assert not isinstance(_NoStartEnd(), SpanProtocol)

    def test_py_span_exposes_start_end_via_protocol(self):
        s = PySpan(1, 5)
        assert isinstance(s, SpanProtocol)
        assert s.start == 1
        assert s.end == 5

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_rust_span_exposes_start_end_via_protocol(self):
        s = _fltk_native.Span(1, 5)
        assert isinstance(s, SpanProtocol)
        assert s.start == 1
        assert s.end == 5

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_start_end_are_codepoint_indices_cross_backend(self):
        # Multibyte source: start/end are codepoint indices on both backends, matching.
        text = "café"
        py = PySpan.with_source(0, 4, PySourceText(text))
        rs = _fltk_native.Span.with_source(0, 4, _fltk_native.SourceText(text))
        assert py.start == rs.start == 0
        assert py.end == rs.end == 4
        assert py.text() == rs.text() == "café"

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_start_end_codepoint_indices_interior_multibyte(self):
        # Discriminator for codepoint- vs byte-indexing: slice the single trailing 'é'.
        # In "café", 'é' is codepoint index 3 but byte offset 4. A codepoint-indexed
        # backend resolves Span(3, 4).text() == "é"; a byte-indexed backend would slice
        # the wrong region. start/end echo the constructor args verbatim, so the real
        # codepoint-vs-byte discriminator here is text(), which must agree across backends.
        text = "café"
        py = PySpan.with_source(3, 4, PySourceText(text))
        rs = _fltk_native.Span.with_source(3, 4, _fltk_native.SourceText(text))
        assert py.start == rs.start == 3
        assert py.end == rs.end == 4
        assert py.text() == rs.text() == "é"


class TestLineColProtocolConformance:
    """Both backends satisfy SpanProtocol.line_col / line_col_or_raise / filename after extension."""

    def test_py_span_still_satisfies_protocol_after_extension(self):
        """Python span still isinstance(s, SpanProtocol) after adding line_col/filename."""
        s = PySpan.with_source(0, 5, PySourceText("hello"))
        assert isinstance(s, SpanProtocol)

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_rust_span_still_satisfies_protocol_after_extension(self):
        """Rust span still isinstance(s, SpanProtocol) after adding line_col/filename."""
        src = _fltk_native.SourceText("hello")
        s = _fltk_native.Span.with_source(0, 5, src)
        assert isinstance(s, SpanProtocol)


class TestLineColCrossBackend:
    """Cross-backend line_col() / line_col_or_raise() equivalence."""

    _SOURCE = "hello\nworld\ncafé\n"

    def _make_py_span(self, start: int, end: int, filename: str | None = None) -> PySpan:
        src = PySourceText(self._SOURCE, filename=filename)
        return PySpan.with_source(start, end, src)

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def _make_rs_span(self, start: int, end: int, filename: str | None = None):  # type: ignore[return]
        src = _fltk_native.SourceText(self._SOURCE, filename=filename)
        return _fltk_native.Span.with_source(start, end, src)

    def _assert_line_col_equal(self, py_span, rs_span):
        """Assert that Python and Rust spans return identical line/col/line_span offsets."""
        py_lc = py_span.line_col()
        rs_lc = rs_span.line_col()
        assert py_lc is not None, "Python span.line_col() returned None unexpectedly"
        assert rs_lc is not None, "Rust span.line_col() returned None unexpectedly"
        assert py_lc.line == rs_lc.line, f"line mismatch: py={py_lc.line} rs={rs_lc.line}"
        assert py_lc.col == rs_lc.col, f"col mismatch: py={py_lc.col} rs={rs_lc.col}"
        assert py_lc.line_span.start == rs_lc.line_span.start, (
            f"line_span.start mismatch: py={py_lc.line_span.start} rs={rs_lc.line_span.start}"
        )
        assert py_lc.line_span.end == rs_lc.line_span.end, (
            f"line_span.end mismatch: py={py_lc.line_span.end} rs={rs_lc.line_span.end}"
        )

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_line0_start(self):
        """Line 0, start of line: both backends agree."""
        py = self._make_py_span(0, 1)
        rs = self._make_rs_span(0, 1)
        self._assert_line_col_equal(py, rs)

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_line0_mid(self):
        """Line 0, mid-line: col matches."""
        py = self._make_py_span(3, 4)
        rs = self._make_rs_span(3, 4)
        self._assert_line_col_equal(py, rs)
        py_lc = py.line_col()
        assert py_lc is not None
        assert py_lc.line == 0
        assert py_lc.col == 3

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_line1_start(self):
        """Line 1, col 0: both backends agree."""
        # "hello\n" is 6 chars (0-5, \n=5), so "world" starts at 6
        py = self._make_py_span(6, 7)
        rs = self._make_rs_span(6, 7)
        self._assert_line_col_equal(py, rs)
        py_lc = py.line_col()
        assert py_lc is not None
        assert py_lc.line == 1
        assert py_lc.col == 0

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_multibyte_column(self):
        """Multibyte source (café): column counts codepoints, not bytes."""
        # "hello\nworld\ncafé\n": café starts at pos 12
        # 'é' is at codepoint 15 (c=12, a=13, f=14, é=15)
        py = self._make_py_span(15, 16)
        rs = self._make_rs_span(15, 16)
        self._assert_line_col_equal(py, rs)
        py_lc = py.line_col()
        assert py_lc is not None
        assert py_lc.line == 2
        assert py_lc.col == 3  # c=0, a=1, f=2, é=3

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_eof_clamp(self):
        """start == len(source): both backends clamp to last codepoint."""
        src_len = len(self._SOURCE)  # codepoint count
        py = self._make_py_span(src_len, src_len)
        rs = self._make_rs_span(src_len, src_len)
        # Should not be None (EOF is valid, clamped to last char)
        assert py.line_col() is not None
        assert rs.line_col() is not None
        self._assert_line_col_equal(py, rs)

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_line_span_text_works(self):
        """line_span is source-bearing on both backends and covers the full line text.

        The test source ends with '\\n', so "world" on line 1 is followed by '\\n' at
        position 11 and the line_span is Span(6, 11), yielding text = "world".
        Both backends use the newline position as the line_end, so they agree exactly.
        """
        py = self._make_py_span(6, 7)  # 'w' in "world"
        rs = self._make_rs_span(6, 7)
        py_lc = py.line_col()
        rs_lc = rs.line_col()
        assert py_lc is not None
        assert rs_lc is not None
        # Both line_spans should be source-bearing
        assert py_lc.line_span.has_source()
        assert rs_lc.line_span.has_source()
        # line_span text should be exactly "world"
        py_text = py_lc.line_span.text() or ""
        rs_text = rs_lc.line_span.text() or ""
        assert py_text == "world", f"py line_span text {py_text!r} should be 'world'"
        assert rs_text == "world", f"rs line_span text {rs_text!r} should be 'world'"
        # Both backends must agree on line_span offsets
        assert py_lc.line_span.start == rs_lc.line_span.start
        assert py_lc.line_span.end == rs_lc.line_span.end

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_sourceless_returns_none(self):
        """Sourceless span returns None on both backends."""
        py = PySpan(0, 5)
        rs = _fltk_native.Span(0, 5)
        assert py.line_col() is None
        assert rs.line_col() is None

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_unknown_span_returns_none(self):
        """UnknownSpan (start=-1) returns None on both backends."""
        py = UnknownSpan
        rs = _fltk_native.UnknownSpan
        assert py.line_col() is None
        assert rs.line_col() is None

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_out_of_domain_returns_none(self):
        """start > len(source) returns None on both backends."""
        src_len = len(self._SOURCE)
        py = self._make_py_span(src_len + 10, src_len + 11)
        rs = self._make_rs_span(src_len + 10, src_len + 11)
        assert py.line_col() is None
        assert rs.line_col() is None

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_line_col_or_raise_sourceless_raises(self):
        """line_col_or_raise raises ValueError for sourceless spans on both backends."""
        py = PySpan(0, 5)
        rs = _fltk_native.Span(0, 5)
        with pytest.raises(ValueError):
            py.line_col_or_raise()
        with pytest.raises(ValueError):
            rs.line_col_or_raise()

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_no_trailing_newline_sentinel(self):
        """Cross-backend: last line without trailing \\n uses sentinel=len on both backends.

        This is the regression guard for the off-by-one fix (design §2.5 note 3).
        Source 'hello\\nworld' — 'world' starts at pos 6, len=11.
        sentinel=len means line_span.end==11, covering all 5 chars of 'world'.
        sentinel=len-1 (old bug) would give line_span.end==10, truncating the last char.
        Both backends must agree and must pin the value as 11 (not 10).
        """
        source = "hello\nworld"
        src_len = len(source)  # codepoint count = 11
        # Query 'w' at position 6 on the last line (no trailing \n)
        py_src = PySourceText(source)
        py_span = PySpan.with_source(6, 7, py_src)
        rs_src = _fltk_native.SourceText(source)
        rs_span = _fltk_native.Span.with_source(6, 7, rs_src)
        py_lc = py_span.line_col()
        rs_lc = rs_span.line_col()
        assert py_lc is not None
        assert rs_lc is not None
        # Both must agree on line_span.end = len = 11 (sentinel=len, not len-1=10).
        assert py_lc.line_span.end == src_len, (
            f"Python line_span.end={py_lc.line_span.end}, expected {src_len} (sentinel=len)"
        )
        assert rs_lc.line_span.end == src_len, (
            f"Rust line_span.end={rs_lc.line_span.end}, expected {src_len} (sentinel=len)"
        )
        # Both backends agree with each other.
        assert py_lc.line_span.end == rs_lc.line_span.end
        # line_span text must cover the full last line including 'd'.
        assert py_lc.line_span.text() == "world"
        assert rs_lc.line_span.text() == "world"

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_empty_source_cross_backend(self):
        """Cross-backend: empty source SourceText('') returns col=-1 on both backends.

        start==len==0, EOF clamp fires (pos=start-1=-1), sentinel push is -1.
        Both backends must agree and return LineColPos(line=0, col=-1).
        """
        py_src = PySourceText("")
        py_span = PySpan.with_source(0, 0, py_src)
        rs_src = _fltk_native.SourceText("")
        rs_span = _fltk_native.Span.with_source(0, 0, rs_src)
        py_lc = py_span.line_col()
        rs_lc = rs_span.line_col()
        assert py_lc is not None, "Python empty source should return LineColPos, not None"
        assert rs_lc is not None, "Rust empty source should return LineColPos, not None"
        assert py_lc.line == 0
        assert py_lc.col == -1
        assert rs_lc.line == 0
        assert rs_lc.col == -1
        assert py_lc.line == rs_lc.line
        assert py_lc.col == rs_lc.col

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_zero_width_span_cross_backend(self):
        """Cross-backend: zero-width span Span(p,p) reports line/col of p, not None."""
        # _SOURCE = "hello\nworld\ncafé\n"; pos=3 is 'l' in "hello", line=0, col=3.
        py = self._make_py_span(3, 3)
        rs = self._make_rs_span(3, 3)
        self._assert_line_col_equal(py, rs)
        py_lc = py.line_col()
        assert py_lc is not None, "Zero-width span should return LineColPos, not None"
        assert py_lc.line == 0
        assert py_lc.col == 3


class TestFilenameCrossBackend:
    """Cross-backend filename() / SourceText filename constructor equivalence."""

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_with_filename_both_backends(self):
        """span.filename() returns the supplied filename on both backends."""
        text = "hello"
        py_span = PySpan.with_source(0, 5, PySourceText(text, filename="test.fltkg"))
        rs_src = _fltk_native.SourceText(text, filename="test.fltkg")  # type: ignore[call-arg]
        rs_span = _fltk_native.Span.with_source(0, 5, rs_src)
        assert py_span.filename() == "test.fltkg"
        assert rs_span.filename() == "test.fltkg"
        assert py_span.filename() == rs_span.filename()

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_without_filename_both_backends(self):
        """span.filename() returns None when no filename on both backends."""
        text = "hello"
        py_span = PySpan.with_source(0, 5, PySourceText(text))
        rs_src = _fltk_native.SourceText(text)
        rs_span = _fltk_native.Span.with_source(0, 5, rs_src)
        assert py_span.filename() is None
        assert rs_span.filename() is None

    def test_sourceless_filename_none_python(self):
        """Sourceless Python span returns filename() == None."""
        span = PySpan(0, 5)
        assert span.filename() is None

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_sourceless_filename_none_rust(self):
        """Sourceless Rust span returns filename() == None."""
        span = _fltk_native.Span(0, 5)
        assert span.filename() is None

    def test_parser_produced_span_filename_python(self):
        """Python parser-produced spans carry the filename from TerminalSource.

        This test is not gated on Rust availability — the Python parser is always
        importable when fltk is installed regardless of the Rust extension.
        """
        from fltk.fegen import fltk_parser  # noqa: PLC0415

        text = "rule := 'foo';"
        ts = TerminalSource(text, filename="grammar.fltkg")
        parser = fltk_parser.Parser(ts)
        result = parser.apply__parse_rule(0)
        assert result is not None
        span = result.result.span
        assert span.filename() == "grammar.fltkg"

    def test_parser_produced_span_filename_rust(self):
        """Rust parser-produced spans carry the filename from Parser(text, filename=...)."""
        # The Rust parser is in crates/fegen-rust and registered as fegen_rust_cst module.
        # The PyParser in fegen-rust is used via the fegen_rust_cst package.
        try:
            import fegen_rust_cst  # type: ignore[import]  # noqa: PLC0415
        except ImportError:
            pytest.skip("fegen_rust_cst not available")
        # fegen_rust_cst's parser module should have Parser class; if fegen_rust_cst is
        # importable but lacks .parser, that is a broken install — assert rather than skip.
        parser_mod = fegen_rust_cst.parser
        parser_cls = parser_mod.Parser
        text = "rule := 'foo';"
        parser = parser_cls(text, filename="grammar.fltkg")  # type: ignore[call-arg]
        result = parser.apply__parse_rule(0)
        assert result is not None
        span = result.result.span
        assert span.filename() == "grammar.fltkg"


class TestDriftAnchor:
    """Drift anchor: span.line_col() and TerminalSource.pos_to_line_col() agree at non-negative positions."""

    def test_py_span_line_col_agrees_with_terminalsrc_pos_to_line_col(self):
        """Python span.line_col() agrees with TerminalSource.pos_to_line_col() at non-negative positions.

        Both implementations now use sentinel=len (exclusive past-end) for the final line
        when there is no trailing newline (design §2.5 note 3 fixed both).  We use text
        ending with '\\n' here to additionally confirm the newline-terminated case (no
        sentinel push) also produces identical results and to avoid any future sentinel
        divergence masking itself in this anchor.

        The only deliberate divergence between the two implementations is at negative
        positions: Span.line_col() returns None for any start<0, while the legacy
        TerminalSource.pos_to_line_col(-1) returns LineColPos(line=0, col=-1).
        That divergence is pinned separately in test_span.py::test_line_col_negative_diverges_from_pos_to_line_col.
        """
        text = "hello\nworld\ncafé\n"
        ts = TerminalSource(text)
        # Test a few positions (all on non-final lines, so sentinel doesn't matter here)
        for pos in [0, 3, 6, 10, 12, 14]:
            src = PySourceText(text)
            span = PySpan.with_source(pos, pos + 1, src)
            lc_span = span.line_col()
            lc_ts = ts.pos_to_line_col(pos)
            assert lc_span is not None, f"span.line_col() returned None for pos={pos}"
            assert lc_span.line == lc_ts.line, f"line mismatch at pos={pos}: {lc_span.line} vs {lc_ts.line}"
            assert lc_span.col == lc_ts.col, f"col mismatch at pos={pos}: {lc_span.col} vs {lc_ts.col}"
            assert lc_span.line_span.start == lc_ts.line_span.start, f"line_span.start mismatch at pos={pos}"
            assert lc_span.line_span.end == lc_ts.line_span.end, f"line_span.end mismatch at pos={pos}"
