"""SpanProtocol and AnySpan union type for backend-agnostic span usage."""

from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

import fltk.fegen.pyrt.terminalsrc as _pymod
from fltk.fegen.pyrt.terminalsrc import LineColPos, SpanKind

if TYPE_CHECKING:
    # `Self` types ``merge``/``intersect`` so a concrete span value is statically assignable to
    # ``SpanProtocol``. Imported under TYPE_CHECKING only: ``runtime_checkable`` checks member
    # *presence*, never signatures, so ``Self`` is never needed at runtime and this adds no runtime
    # dependency on ``typing_extensions``. Project targets 3.10, so not ``typing.Self``.
    from typing_extensions import Self


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

    # TODO(spanprotocol-native-linecol): line_col/line_col_or_raise are typed to return
    # terminalsrc.LineColPos, so fltk._native.Span (whose line_col returns the native LineColPos, a
    # distinct nominal class) is NOT statically assignable to SpanProtocol — native conforms only by
    # runtime isinstance + .pyi declaration. Unifying LineColPos across backends closes the gap.
    # CONSTRAINT when closing this: the generated pipeline (parser/CST/protocol/unparser) imports
    # SpanProtocol, and its R2 stub-stability is guaranteed structurally only because SpanProtocol's
    # own definition names no fltk._native symbol (D5.1). If a fix introduces a native reference into
    # SpanProtocol's structural surface, that stub-stability becomes transitive and the source-level
    # "names no native" tests (test_cst_protocol.py etc.) would NOT catch a regression — add a
    # differential/structural stub-stability guard for the generated pipeline at that time.
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
