"""Shared error formatter for fltk span-based error reporting.

Provides ``format_source_line``, a backend-agnostic function that renders the
offending source line with a caret annotation and a message. This is the
shared implementation of what clockwork's ``format_line_with_error`` does
(``clockwork/dsl/ir/cst_util.py:70-92``), minus the clockwork-specific
``ModuleID`` path-rendering (which stays in clockwork).

Usage::

    from fltk.fegen.pyrt.error_formatter import format_source_line

    msg = format_source_line(span, "unexpected token", filename="foo.fltkg")
    print(msg)

Output format::

    \\nIn <file>:<line+1>:<col+1>:\\n<line text>\\n<col spaces>^\\n<message>\\n

When no filename is resolvable, the header degrades to::

    \\nAt line <line+1>, column <col+1>:\\n<line text>\\n<col spaces>^\\n<message>\\n
"""

import unicodedata

from fltk.fegen.pyrt.span_protocol import SpanProtocol

# DEL character codepoint (not a "Cc" in unicodedata but still a control character).
_DEL_CODEPOINT = 0x7F

# Bidi-override and invisible-formatting codepoints that must be escaped.
# U+202A-U+202E: LRE, RLE, PDF, LRO, RLO (directional embedding/override markers).
# U+2066-U+2069: LRI, RLI, FSI, PDI (directional isolate markers).
# U+200B: ZERO WIDTH SPACE, U+200C: ZWNJ, U+200D: ZWJ, U+FEFF: BOM/ZWNBSP.
_BIDI_OR_INVISIBLE_CODEPOINTS: frozenset[int] = frozenset(
    [*range(0x202A, 0x202F), *range(0x2066, 0x206A), 0x200B, 0x200C, 0x200D, 0xFEFF]
)


def _escape_for_display(text: str) -> str:
    """Escape control and bidi-override characters in ``text`` for safe display.

    Mirrors the ``escape_control_chars`` function used in the Rust
    ``format_error_message`` path (``errors.rs:144-145``), keeping raw ESC,
    CR, bidi-override (U+202A-U+202E, U+2066-U+2069), and other C0/C1 control
    characters out of terminal and log output.

    Each problematic character is replaced by its Unicode escape form
    (e.g. ``U+001B``, ``U+202E``).
    """
    result = []
    for ch in text:
        cat = unicodedata.category(ch)
        cp = ord(ch)
        # Control characters (Cc): C0 (0x00-0x1F), C1 (0x80-0x9F), plus DEL (0x7F).
        # Formatting characters that are bidi-override or isolate markers (Cf).
        is_control = cat == "Cc" or cp == _DEL_CODEPOINT
        is_bidi_or_invisible = cat == "Cf" and cp in _BIDI_OR_INVISIBLE_CODEPOINTS
        if is_control or is_bidi_or_invisible:
            result.append(f"U+{cp:04X}")
        else:
            result.append(ch)
    return "".join(result)


def format_source_line(
    span: SpanProtocol,
    message: str,
    *,
    filename: str | None = None,
) -> str:
    """Render the offending source line with a caret annotation and a message.

    Args:
        span: The span to report. Must be source-bearing; raises ``ValueError``
            (via ``line_col_or_raise``) if the span has no source, has negative
            indices, or is out of bounds.
        message: The error message body appended after the caret line.
        filename: Optional filename override. When provided, wins over
            ``span.filename()``. When both are ``None``, the header degrades to
            ``At line N, column M:`` (no ``In <file>:`` prefix).

    Returns:
        A multi-line string with a trailing newline, suitable for printing to
        stderr or embedding in an exception message.

    Raises:
        ValueError: If the span cannot resolve a line/column (sourceless, negative
            start, or out-of-bounds start).
    """
    lc = span.line_col_or_raise()
    # Escape control/bidi characters in the source line text so that crafted
    # inputs cannot inject terminal escape sequences or spoof log output.
    # Mirrors the escape_control_chars hardening in the Rust format_error_message
    # path (errors.rs:144-145).
    line_text = _escape_for_display(lc.line_span.text() or "")
    # Filename: explicit arg wins; fall back to span.filename().
    # Escape the filename too so a newline-bearing path cannot split the header line.
    raw_filename = filename if filename is not None else span.filename()
    resolved_filename = _escape_for_display(raw_filename) if raw_filename is not None else None
    # Header: 1-based line and column for human display.
    line_1based = lc.line + 1
    col_1based = lc.col + 1
    if resolved_filename is not None:
        header = f"In {resolved_filename}:{line_1based}:{col_1based}:"
    else:
        header = f"At line {line_1based}, column {col_1based}:"
    # Caret indent: 0-based col (Python `' ' * -1 == ''`, so col=-1 is safe).
    # After escaping, each original codepoint may expand to "U+XXXX" (6 chars).
    # Recount the caret offset from the escaped prefix so the caret aligns with
    # the escaped text.  col counts codepoints in the *original* line; after
    # escaping, each kept codepoint maps to itself (1 char) or to "U+XXXX" (6
    # chars).  We measure the visible width of the escaped prefix up to col.
    raw_line = lc.line_span.text() or ""
    col = max(lc.col, 0)  # guard against col=-1 empty-source corner
    prefix_original = raw_line[:col]
    escaped_prefix = _escape_for_display(prefix_original)
    caret_indent = " " * len(escaped_prefix)
    return f"\n{header}\n{line_text}\n{caret_indent}^\n{message}\n"
