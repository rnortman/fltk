"""SpanProtocol and AnySpan union type for backend-agnostic span usage."""

from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

import fltk.fegen.pyrt.terminalsrc as _pymod

# ``LineColPos`` is re-exported for backward compatibility: ``span_protocol.LineColPos`` is an
# importable public name and out-of-tree consumers may import it from here. It is not named by
# any annotation in this module (the protocols use ``LineColPosProtocol``), so it is marked below
# as a deliberate re-export rather than an accidental unused import.
from fltk.fegen.pyrt.terminalsrc import (
    LineColPos,  # noqa: F401 -- deliberate re-export, see comment above
    SpanKind,
)

if TYPE_CHECKING:
    # `Self` types ``merge``/``intersect`` so a concrete span value is statically assignable to
    # ``SpanProtocol``. Imported under TYPE_CHECKING only: ``runtime_checkable`` checks member
    # *presence*, never signatures, so ``Self`` is never needed at runtime and this adds no runtime
    # dependency on ``typing_extensions``. Project targets 3.10, so not ``typing.Self``.
    from typing_extensions import Self


@runtime_checkable
class LineColPosProtocol(Protocol):
    """Structural protocol satisfied by both backends' ``LineColPos`` return types.

    Bridges the two nominally distinct ``LineColPos`` classes (the pure-Python
    ``terminalsrc.LineColPos`` dataclass and the native ``fltk._native.LineColPos``) the same way
    ``SpanProtocol`` bridges the two ``Span`` types, so ``SpanProtocol.line_col`` can be annotated
    backend-agnostically. All three members are 0-based codepoint semantics shared by both backends.

    Members are **read-only properties**: a plain protocol attribute is invariant and would reject
    the covariant ``line_span`` return (``terminalsrc.Span`` on the Python side); a read-only
    property permits the covariant match. Being ``runtime_checkable``, ``isinstance`` against this
    protocol verifies member *presence* only, never signatures — the same limitation ``SpanProtocol``
    documents for itself.
    """

    @property
    def line(self) -> int:
        """0-based codepoint line index of the position."""
        ...

    @property
    def col(self) -> int:
        """0-based codepoint column index of the position."""
        ...

    @property
    def line_span(self) -> "SpanProtocol":
        """Span covering the entire line, exclusive of the trailing ``\\n``."""
        ...


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

    @property
    def kind(self) -> Literal[SpanKind.SPAN]:
        """Discriminant enabling Shape-2 ``match``/``case`` dispatch over span children.

        Both backends expose ``kind == SpanKind.SPAN``; a protocol-only consumer narrows a span
        child out of a mixed child union with ``case proto_cst.Span.kind:``.
        """
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

    def merge(self, other: "Self") -> "Self":
        """Return the smallest span that covers both ``self`` and ``other``.

        ``other`` is typed ``Self``: each backend's ``merge`` accepts only its own span type and
        raises at runtime on a foreign-source span, so "merge with your own backend's span" is the
        true contract — and it makes concrete spans assignable to ``SpanProtocol``.

        Raises ``ValueError`` if both spans carry different source references.
        """
        ...

    def intersect(self, other: "Self") -> "Self":
        """Return the overlapping region of ``self`` and ``other``, or the ``UnknownSpan`` sentinel
        (``Span(-1, -1)``) if they are disjoint.

        Raises ``ValueError`` if both spans carry different source references.
        """
        ...

    def line_col(self) -> "LineColPosProtocol | None":
        """Return the line/column position for the span's start, or ``None``.

        Returns ``None`` when the span is sourceless, has a negative start, or has a
        start that exceeds the source length. Line and column are 0-based codepoint indices.
        """
        ...

    def line_col_or_raise(self) -> "LineColPosProtocol":
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
except ImportError:
    # In lockstep with span.py: `ImportError` means the native backend is absent
    # (pure-Python install) and the fallback is intentionally silent; any other exception
    # means a present-but-broken extension and propagates.
    AnySpan = _pymod.Span  # type: ignore[assignment,misc]
