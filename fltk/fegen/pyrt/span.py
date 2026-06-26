"""Backend selector: re-exports Span from Rust backend if available, else pure-Python.

Note: ``Span.with_source`` is intentionally excluded from ``SpanProtocol`` because
its signature is backend-concrete (Python accepts ``str | SourceText``; Rust accepts
only ``SourceText``).  The portable form is always ``Span.with_source(s, e, SourceText(text))``.
"""

# TODO(span-selector-broken-native-diagnostic): `except Exception` swallows ANY native-import
# failure (ABI mismatch / corrupted .so / C init crash → OSError/SystemError), not just the
# expected absent-native ImportError, falling back silently with no diagnostic. Decide between
# narrowing the catch (propagate a genuinely broken extension) and logging the swallowed
# exception; keep the AnySpan block in span_protocol.py in lockstep. See TODO.md.
try:
    from fltk._native import SourceText, Span, UnknownSpan  # type: ignore[assignment]
except Exception:
    # Pure-Python install: the native backend is simply absent. Fall back silently to
    # the pure-Python backend, matching span_protocol.py. There is nothing wrong with
    # _native being missing, so no warning is emitted.
    from fltk.fegen.pyrt.terminalsrc import SourceText, Span, UnknownSpan

__all__ = ["SourceText", "Span", "UnknownSpan"]
