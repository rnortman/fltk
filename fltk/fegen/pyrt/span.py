"""Backend selector: re-exports Span from Rust backend if available, else pure-Python.

Note: ``Span.with_source`` is intentionally excluded from ``SpanProtocol`` because
its signature is backend-concrete (Python accepts ``str | SourceText``; Rust accepts
only ``SourceText``).  The portable form is always ``Span.with_source(s, e, SourceText(text))``.
"""

try:
    from fltk._native import SourceText, Span, UnknownSpan  # type: ignore[assignment]
except ImportError:
    # `ImportError` means the native backend is simply absent (pure-Python install):
    # fall back silently to the pure-Python backend, matching span_protocol.py. There is
    # nothing wrong with _native being missing, so no warning is emitted. Any other
    # exception from importing fltk._native means a present-but-broken extension (ABI
    # mismatch / corrupted .so / C-level init crash) and propagates rather than degrading
    # silently to pure-Python.
    from fltk.fegen.pyrt.terminalsrc import SourceText, Span, UnknownSpan

__all__ = ["SourceText", "Span", "UnknownSpan"]
