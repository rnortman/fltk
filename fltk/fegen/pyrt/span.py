"""Backend selector: re-exports Span from Rust backend if available, else pure-Python.

Note: ``Span.with_source`` is intentionally excluded from ``SpanProtocol`` because
its signature differs between backends (Python takes ``str``; Rust takes ``SourceText``).
Code calling ``with_source`` must either know which backend is active or branch on
``SourceText is not None``.
TODO(backend-with-source-signature): Unify construction API in a future phase.
"""

import warnings

from fltk.fegen.pyrt.terminalsrc import Span, UnknownSpan

SourceText: type | None = None  # not available in pure-Python backend

try:
    from fltk._native import SourceText, Span, UnknownSpan  # type: ignore[assignment]
except Exception:
    warnings.warn(
        "fltk._native could not be loaded; falling back to pure-Python Span backend.",
        stacklevel=1,
    )

__all__ = ["SourceText", "Span", "UnknownSpan"]
