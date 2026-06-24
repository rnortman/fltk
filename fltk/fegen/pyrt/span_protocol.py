"""SpanProtocol and AnySpan union type for backend-agnostic span usage."""

from typing import Protocol, runtime_checkable

import fltk.fegen.pyrt.terminalsrc as _pymod
from fltk.fegen.pyrt.terminalsrc import LineColPos


@runtime_checkable
class SpanProtocol(Protocol):
    """Structural protocol satisfied by both the pure-Python and Rust Span backends.

    Backend-agnostic code should annotate with ``SpanProtocol`` rather than a
    concrete ``Span`` type.  ``start`` and ``end`` are codepoint indices on both
    backends.
    """

    @property
    def start(self) -> int:
        """Start codepoint index of the half-open range ``[start, end)``."""
        ...

    @property
    def end(self) -> int:
        """End codepoint index (exclusive) of the half-open range ``[start, end)``."""
        ...

    def text(self) -> str | None:
        """Return the source text slice ``[start, end)``, or ``None`` if no source is attached or indices are
        invalid."""
        ...

    def text_or_raise(self) -> str:
        """Return the source text slice ``[start, end)``, raising ``ValueError`` if the text cannot be returned."""
        ...

    def has_source(self) -> bool:
        """Return ``True`` if a source string is attached to this span."""
        ...

    def len(self) -> int:
        """Return the span length in codepoints (``end - start``).

        Returns 0 for sentinel/unknown spans with negative indices.
        """
        ...

    def is_empty(self) -> bool:
        """Return ``True`` if the span covers no elements (``start >= end``), including sentinel spans."""
        ...

    def merge(self, other: "SpanProtocol") -> "SpanProtocol":
        """Return the smallest span that covers both ``self`` and ``other``.

        Raises ``ValueError`` if both spans carry different source references.
        """
        ...

    def intersect(self, other: "SpanProtocol") -> "SpanProtocol":
        """Return the overlapping region of ``self`` and ``other``, or the ``UnknownSpan`` sentinel
        (``Span(-1, -1)``) if they are disjoint.

        Raises ``ValueError`` if both spans carry different source references.
        """
        ...

    def line_col(self) -> "LineColPos | None":
        """Return the line/column position for the span's start, or ``None``.

        Returns ``None`` when the span is sourceless, has a negative start, or has a
        start that exceeds the source length. Line and column are 0-based codepoint indices.
        """
        ...

    def line_col_or_raise(self) -> "LineColPos":
        """Return the line/column position for the span's start, raising ``ValueError`` if it
        cannot be resolved (same conditions as ``line_col()``).
        """
        ...

    def filename(self) -> "str | None":
        """Return the optional filename associated with this span's source, or ``None``.

        Returns ``None`` when the span is sourceless or the source has no filename.
        """
        ...


try:
    from fltk._native import Span as _RustSpan

    AnySpan = _pymod.Span | _RustSpan
except Exception:
    AnySpan = _pymod.Span  # type: ignore[assignment,misc]
