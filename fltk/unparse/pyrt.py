"""Runtime support for FLTK unparsers."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, NoReturn, cast

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


def raise_preserved_trivia_failure(rule_name: str, pos: int) -> NoReturn:
    """Halt with a diagnostic when confirmed-preservable trivia fails to unparse.

    Called from the generated Python unparser's trivia-processing site when
    ``_has_preservable_trivia`` confirmed a trivia node carries preservable
    comments but ``unparse__trivia`` returned ``None``. Silently dropping the
    comment is the failure this refuses to commit; raise instead, naming the
    rule and child position. Message wording is aligned with the Rust backend's
    equivalent ``panic!`` (no node/span contents, matching the Rust ``Span``
    ``Debug`` convention of eliding source text).
    """
    msg = (
        f"unparse rule {rule_name!r}: trivia at child position {pos} has "
        f"preservable comments but unparse__trivia returned None; "
        f"refusing to silently drop comments"
    )
    raise ValueError(msg)


def count_span_newlines(span: Span, terminals: str) -> int:
    """Count newline characters in a span's text.

    Uses extract_span_text to handle both Python and Rust backends.
    """
    return extract_span_text(span, terminals).count("\n")


# C0 information separators U+001C-U+001F: Python's str.isspace() treats them as
# whitespace, but Rust's char::is_whitespace (Unicode White_Space property) does not.
# Excluding them keeps the whitespace-only classification identical in both backends.
_C0_SEPARATORS = "\x1c\x1d\x1e\x1f"


def _is_unicode_whitespace_only(text: str) -> bool:
    """True iff text is non-empty and every character is Unicode White_Space.

    Mirrors Rust's ``char::is_whitespace`` rather than Python's broader
    ``str.isspace()`` (which also accepts the C0 information separators), so a
    trivia node classifies as whitespace-only identically across backends.
    """
    return bool(text) and all(ch.isspace() and ch not in _C0_SEPARATORS for ch in text)


def count_whitespace_newlines(child: object, terminals: str) -> int:
    """Count the newlines a Trivia child contributes toward blank-line detection.

    A direct span child contributes all of its newlines (via ``count_span_newlines``).
    A node child (e.g. a grammar that wraps whitespace in a named trivia rule)
    contributes its newlines only when its span text is non-empty and entirely
    whitespace; a node holding any non-whitespace (a comment) or an empty span
    contributes 0, degrading to the direct-span-only behavior and never over-counting.
    """
    if is_span(child):
        return count_span_newlines(cast(Span, child), terminals)
    span = getattr(child, "span", None)
    if span is None:
        return 0
    text = extract_span_text(cast(Span, span), terminals)
    if _is_unicode_whitespace_only(text):
        return text.count("\n")
    return 0


def is_span(obj: object) -> bool:
    """Return True if obj is a span object from either backend.

    Recognizes the Python-backend ``terminalsrc.Span`` directly and the
    Rust-backend ``fltk._native.Span`` lazily — only when that module has
    already been imported (``sys.modules.get``). This keeps ``pyrt`` purely
    Python-importable (no top-level ``fltk._native`` import) and never fires
    the ``span.py`` process-wide backend probe, while letting a generated
    unparser accept whichever span backend the CST it consumes actually
    carries.

    ``fltk._native`` can be present in ``sys.modules`` as a namespace package
    without a ``Span`` attribute in a pure-Python build (the package directory
    ships only a ``.pyi`` stub, no compiled module), so resolve ``Span``
    defensively with ``getattr`` rather than assuming it exists.
    """
    if isinstance(obj, Span):
        return True
    native_span = getattr(sys.modules.get("fltk._native"), "Span", None)
    return native_span is not None and isinstance(obj, native_span)
