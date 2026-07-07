r"""LSP position math: codepoint offsets <-> LSP positions in the negotiated encoding.

FLTK works purely in codepoint offsets; LSP columns are counted either in utf-16 code
units or utf-32 codepoints, per the session's negotiated encoding.  ``LineIndex`` builds a
line table once per document text -- recognizing all three LSP line separators (``\n``,
``\r\n``, and a lone ``\r``), unlike the parser's ``\n``-only utilities -- and converts
between codepoint offsets and LSP ``(line, character)`` positions, clamping out-of-bounds
inputs the way a racy LSP server must (client and server momentarily disagree while an edit
is in flight).
"""

from __future__ import annotations

import bisect
import enum

# Highest Basic Multilingual Plane codepoint; anything above needs a utf-16 surrogate pair.
_BMP_MAX = 0xFFFF


class PositionEncoding(enum.Enum):
    """The LSP position encodings ``LineIndex`` supports (``utf-8`` is deliberately absent)."""

    UTF16 = "utf-16"
    UTF32 = "utf-32"


class LineIndex:
    """A line table over one document text, converting offsets to/from LSP positions.

    Built once per analyzed document; all conversions clamp rather than raise. Columns are
    codepoints under ``UTF32`` (free, since FLTK offsets are codepoints) and utf-16 code
    units under ``UTF16`` (astral characters count as two units).
    """

    def __init__(self, text: str) -> None:
        self._text = text
        starts = [0]
        i = 0
        n = len(text)
        while i < n:
            ch = text[i]
            if ch == "\n":
                starts.append(i + 1)
                i += 1
            elif ch == "\r":
                if i + 1 < n and text[i + 1] == "\n":
                    starts.append(i + 2)
                    i += 2
                else:
                    starts.append(i + 1)
                    i += 1
            else:
                i += 1
        self._line_starts = starts

    def line_of(self, offset: int) -> int:
        """The 0-based line containing ``offset`` (clamped into ``[0, len(text)]``)."""
        offset = max(0, min(offset, len(self._text)))
        return bisect.bisect_right(self._line_starts, offset) - 1

    def line_bounds(self, line: int) -> tuple[int, int]:
        """The ``[start, end)`` codepoint span of ``line``'s content, excluding its terminator."""
        line = max(0, min(line, len(self._line_starts) - 1))
        start = self._line_starts[line]
        if line + 1 < len(self._line_starts):
            end = self._line_starts[line + 1]
            if end > start and self._text[end - 1] == "\n":
                end -= 1
                if end > start and self._text[end - 1] == "\r":
                    end -= 1
            elif end > start and self._text[end - 1] == "\r":
                end -= 1
        else:
            end = len(self._text)
        return (start, end)

    def _column(self, start: int, offset: int, enc: PositionEncoding) -> int:
        prefix = self._text[start:offset]
        if enc is PositionEncoding.UTF32:
            return len(prefix)
        return sum(1 + (ord(c) > _BMP_MAX) for c in prefix)

    def offset_to_position(self, offset: int, enc: PositionEncoding) -> tuple[int, int]:
        """Convert a codepoint ``offset`` to an LSP ``(line, character)`` in ``enc`` units."""
        offset = max(0, min(offset, len(self._text)))
        line = self.line_of(offset)
        start = self._line_starts[line]
        return (line, self._column(start, offset, enc))

    def position_to_offset(self, line: int, character: int, enc: PositionEncoding) -> int:
        """Convert an LSP ``(line, character)`` in ``enc`` units to a codepoint offset.

        A line past the last maps to end-of-text; a character past the line's content maps to
        the line's last valid offset; a character landing inside a surrogate pair clamps to
        that codepoint's start.
        """
        if line < 0:
            return 0
        if line >= len(self._line_starts):
            return len(self._text)
        start, end = self.line_bounds(line)
        if character <= 0:
            return start
        if enc is PositionEncoding.UTF32:
            return min(start + character, end)
        units = 0
        offset = start
        while offset < end and units < character:
            width = 1 + (ord(self._text[offset]) > _BMP_MAX)
            if units + width > character:
                break
            units += width
            offset += 1
        return offset

    def end_position(self, enc: PositionEncoding) -> tuple[int, int]:
        """The LSP ``(line, character)`` of the end of the document."""
        return self.offset_to_position(len(self._text), enc)
