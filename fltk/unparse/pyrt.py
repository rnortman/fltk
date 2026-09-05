"""Runtime support for FLTK unparsers."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, NoReturn, cast

from fltk.fegen.pyrt.terminalsrc import Span

if TYPE_CHECKING:
    import fltk.unparse.combinators
    from fltk.fegen.pyrt.span_protocol import SpanProtocol
    from fltk.unparse.accumulator import DocAccumulator


@dataclass(frozen=True, slots=True)
class UnparseResult:
    """Result from unparsing that includes both the Doc and new position.

    Attributes:
        accumulator: The DocAccumulator containing the Doc result and trivia state
        new_pos: The new position after consuming children from the CST
        cursor: The source counterpart of ``new_pos`` — the codepoint offset in the enclosing
            rule node's source that the consumed items reach, or ``None`` when the tree's
            positions stop being positions in one source and ownership cannot be decided.
    """

    accumulator: DocAccumulator
    new_pos: int
    cursor: int | None = None

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


def literal_span_matches(span: Span, allowed: Sequence[str]) -> bool:
    """True iff a labeled literal item may accept this span child.

    ``allowed`` is the set of literal texts the item's label carries in its rule, computed at
    generation time and always including the item's own text. A sourceless span (a
    synthesized child, which no parse produces) is accepted: rendering emits the grammar's
    literal text, so the canonical spelling is what comes out. A source-bearing span is
    accepted only when its text is one of those spellings, which is what lets a rival regex
    branch under the same label win the trial instead of having its text replaced.

    The caller has already established that the child is a span (the generated type check
    precedes this one), so ``text()`` is read without a guard: a child that has none is a
    contract violation and should fail loudly rather than be accepted.
    """
    text = span.text()
    if text is None:
        return True
    return text in allowed


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


def raise_dropped_trivia(rule_name: str, pos: int) -> NoReturn:
    """Halt when the winning alternative left a comment-bearing trivia child unclaimed.

    With the source cursor known, every gap's ownership was decided from source positions, so
    a trivia child no separator took is content the formatter would delete without a trace.
    With the cursor unknown the ownership question was never asked, and the generated check
    does not run at all.
    """
    msg = (
        f"unparse rule {rule_name!r}: trivia at child position {pos} was claimed by no "
        f"separator; refusing to silently drop comments"
    )
    raise ValueError(msg)


# ── Source cursor ─────────────────────────────────────────────────────────────
# The cursor is the source counterpart of the generated unparser's child index: a codepoint
# offset into the rule node's source that the alternative walk advances alongside ``pos``. It
# exists because a rule node's children are *not* index-aligned with its alternative's
# item/separator sequence — a suppressed literal contributes no child, and the parser pushes a
# trivia child only where whitespace or a comment actually matched — so a separator standing
# for an empty gap would otherwise take the trivia belonging to a later one and re-emit it
# ahead of the suppressed text between them.
#
# ``None`` means unknown: the tree's positions are not positions in one source. Then the
# generated code falls back to consuming trivia in child order, which is the behaviour with no
# ownership tracking at all, and the dropped-comment guard does not run.
#
# TODO(unparse-cursor-fallback-signal)


def cursor_start(node_span: SpanProtocol) -> int | None:
    """The source cursor at a rule node's start."""
    if node_span.has_source() and node_span.start >= 0:
        return node_span.start
    return None


def cursor_after(cursor: int | None, anchor: SpanProtocol, child: SpanProtocol) -> int | None:
    """The cursor after consuming a CST child: the child's span end.

    ``None`` when the child's positions are not positions in ``anchor``'s source — a sourceless
    or foreign-source span, or one starting behind the cursor. That is the hand-built or mutated
    tree, where the cursor resyncs at the next child carrying the anchor's source.
    """
    if cursor is None:
        return None
    if not anchor.shares_source(child):  # type: ignore[arg-type]
        return None
    if child.start < cursor or child.end < child.start:
        return None
    return child.end


def cursor_owns(cursor: int | None, anchor: SpanProtocol, child: SpanProtocol) -> bool:
    """Whether a child was written in the gap the cursor stands at."""
    if cursor is None:
        return False
    return anchor.shares_source(child) and child.start == cursor  # type: ignore[arg-type]


def cursor_behind(cursor: int | None, anchor: SpanProtocol, child: SpanProtocol) -> bool:
    """Whether a child sits *behind* the cursor in the cursor's own source.

    A parser-produced tree never does: the walk advances the cursor only to the end of what it
    consumed, so an unconsumed child starts at or after it. Behind means the walk ran past a gap
    without claiming the trivia written in it, and the ownership answers from here on are guesses.
    """
    if cursor is None:
        return False
    return anchor.shares_source(child) and child.start < cursor  # type: ignore[arg-type]


def cursor_check_not_behind(
    rule_name: str,
    pos: int,
    cursor: int | None,
    anchor: SpanProtocol,
    child: SpanProtocol,
) -> None:
    """Halt when the trivia child at ``pos`` was written behind the cursor.

    Not the "empty gap, a later separator owns it" case the ownership test is for: this is
    trivia the walk already stepped over. Left alone it makes the alternative fail on the child
    and surfaces as an unlocatable "unparser returned None"; say where instead.
    """
    if not cursor_behind(cursor, anchor, child):
        return
    line_col = child.line_col()
    where = f"line {line_col.line + 1}, col {line_col.col + 1}" if line_col else "an unresolvable position"
    msg = (
        f"unparse rule {rule_name!r}: trivia at child position {pos} starts at {child.start}, "
        f"behind the source cursor {cursor} ({where}); the unparse walk passed the gap that "
        f"owns it — refusing to guess where it belongs"
    )
    raise ValueError(msg)


def cursor_probe(cursor: int | None, anchor: SpanProtocol, literal: str) -> int | None:
    """The cursor past an *optional* literal that occupies no child position.

    The literal was matched iff the source at the cursor spells it: the parser is greedy at an
    optional and does not backtrack out of a successful match. A miss means the literal is
    absent and occupies nothing, so the cursor stays put and stays known.
    """
    if cursor is None:
        return None
    if anchor.spells_at(cursor, literal):
        return cursor + len(literal)
    return cursor


def cursor_expect(cursor: int | None, anchor: SpanProtocol, literal: str) -> int | None:
    """The cursor past a *required* literal that occupies no child position.

    A miss means the source does not spell what is being emitted — an alternation of equivalent
    spellings renders its canonical one, so an unparse of ``use x`` under
    ``("import" | "use")`` emits ``import`` over a source three codepoints shorter. How much
    source the token really occupies is then unknown, so the cursor is, and trivia falls back
    to child order from there.
    """
    if cursor is None:
        return None
    if anchor.spells_at(cursor, literal):
        return cursor + len(literal)
    return None


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


def _child_span_text(child: object, terminals: str) -> str | None:
    """Return the source text of a Trivia child's span, or None when it has no span.

    A child is either a direct span or a node carrying one; both reach the same text.
    """
    span = child if is_span(child) else getattr(child, "span", None)
    if span is None:
        return None
    return extract_span_text(cast(Span, span), terminals)


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
    text = _child_span_text(child, terminals)
    if text is not None and _is_unicode_whitespace_only(text):
        return text.count("\n")
    return 0


def preceding_comment_trailing_newline(children: Sequence[tuple[object, object]], pos: int, terminals: str) -> int:
    """Return 1 when the trivia child before ``pos`` is a comment ending in a newline.

    A line comment's terminating newline belongs to the comment child's span, not to the
    whitespace span that follows it, so a gap rendered as ``// c\\n`` + ``'\\n'`` holds one
    fewer newline than the source visually shows. This restores it. Whitespace-only children
    and empty spans return 0, so consecutive whitespace never inflates the count, and a block
    comment (whose span does not end in a newline) consumes no newline and returns 0 too.

    A ``pos`` past the end of ``children`` is a caller invariant violation and raises
    ``IndexError``, the same loud failure the Rust helper gives, rather than formatting on
    with a silently wrong blank count.
    """
    if pos <= 0:
        return 0
    text = _child_span_text(children[pos - 1][1], terminals)
    # endswith is O(1) and answers 0 for most gaps; the per-character whitespace
    # classification runs only for text that could still qualify.
    if text is None or not text.endswith("\n"):
        return 0
    return 0 if _is_unicode_whitespace_only(text) else 1


def capped_blank_lines(newline_count: int, cap: int) -> int:
    """Blank lines to emit for a gap holding ``newline_count`` newlines, capped at ``cap``.

    ``k`` newlines separate ``k - 1`` blank lines; the result is clamped to ``[0, cap]``, so
    blanks are never invented and never exceed the configured maximum.
    """
    blanks = newline_count - 1
    if blanks < 0:
        return 0
    return min(blanks, cap)


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
