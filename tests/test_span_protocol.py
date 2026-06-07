"""Tests for SpanProtocol, AnySpan, and the backend selector module."""

import pytest

import fltk._native as _fltk_native
import fltk.fegen.pyrt.span as _span_selector
from fltk.fegen.pyrt.span_protocol import AnySpan, SpanProtocol
from fltk.fegen.pyrt.terminalsrc import SourceText as PySourceText
from fltk.fegen.pyrt.terminalsrc import Span as PySpan

_rust_available = hasattr(_fltk_native, "Span")


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


class TestProtocolHasNoStartEnd:
    def test_span_protocol_methods_do_not_include_start_end(self):
        # SpanProtocol must not require start/end. Verify by inspecting protocol members.
        # Protocol methods are accessible as class attributes but start/end should not be.
        assert not hasattr(SpanProtocol, "start")
        assert not hasattr(SpanProtocol, "end")
        # Expected protocol methods exist on the class.
        assert callable(SpanProtocol.text)
        assert callable(SpanProtocol.len)
        assert callable(SpanProtocol.is_empty)
        assert callable(SpanProtocol.merge)
        assert callable(SpanProtocol.intersect)
