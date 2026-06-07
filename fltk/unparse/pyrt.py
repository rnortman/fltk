"""Runtime support for FLTK unparsers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fltk.fegen.pyrt.terminalsrc import Span

if TYPE_CHECKING:
    import fltk.unparse.combinators
    from fltk.unparse.accumulator import DocAccumulator


@dataclass(frozen=True, slots=True)
class UnparseResult:
    """Result from unparsing that includes both the Doc and new position.

    Attributes:
        accumulator: The DocAccumulator containing the Doc result and trivia state
        new_pos: The new position after consuming children from the CST
    """

    accumulator: DocAccumulator
    new_pos: int

    @property
    def doc(self) -> fltk.unparse.combinators.Doc:
        """Backward compatibility property to access the doc from the accumulator."""
        return self.accumulator.doc


def extract_span_text(span: Span, terminals: str) -> str:
    """Extract the text content from a span using the terminals string.

    Handles both Python-backend terminalsrc.Span (uses .start/.end slice) and
    Rust-backend fltk._native.Span (uses .text() which carries its own source).
    """
    text = span.text() if hasattr(span, "text") else None
    if text is not None:
        return text
    # Fallback: sourceless Python-backend span — slice from terminals directly.
    # Guard: only fall back for spans without source. A source-bearing span
    # whose text() returns None indicates invalid byte offsets, not a missing
    # source; use the terminals slice only for genuinely sourceless spans.
    if hasattr(span, "has_source") and span.has_source():
        msg = f"span.text() returned None for source-bearing span {span!r}; codepoint offsets may be out of range"
        raise ValueError(msg)
    return terminals[span.start : span.end]


def count_span_newlines(span: Span, terminals: str) -> int:
    """Count newline characters in a span's text.

    Uses extract_span_text to handle both Python and Rust backends.
    """
    return extract_span_text(span, terminals).count("\n")
