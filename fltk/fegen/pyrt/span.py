"""Backend selector: re-exports Span from Rust backend if available, else pure-Python.

Note: ``Span.with_source`` is intentionally excluded from ``SpanProtocol`` because
its signature is backend-concrete (Python accepts ``str | SourceText``; Rust accepts
only ``SourceText``).  The portable form is always ``Span.with_source(s, e, SourceText(text))``.
"""

import warnings

from fltk.fegen.pyrt.terminalsrc import SourceText, Span, UnknownSpan

try:
    from fltk._native import SourceText, Span, UnknownSpan  # type: ignore[assignment]
except Exception:
    warnings.warn(
        "fltk._native could not be loaded; falling back to pure-Python Span backend.",
        stacklevel=1,
    )

__all__ = ["SourceText", "Span", "UnknownSpan"]
