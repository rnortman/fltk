import bisect
import re
from dataclasses import dataclass, field
from typing import Final


@dataclass(frozen=True, eq=True, slots=True)
class Span:
    """Span of elements in the range [start, end)"""

    start: int
    end: int
    _source: str | None = field(default=None, repr=False, compare=False, hash=False)

    def text(self) -> str | None:
        """Return the source text slice ``[start, end)``, or ``None`` if no source is attached or indices are
        invalid."""
        if self._source is None:
            return None
        start, end = self.start, self.end
        if start < 0 or end < 0 or start > end:
            return None
        if end > len(self._source):
            return None
        return self._source[start:end]

    def text_or_raise(self) -> str:
        """Return the source text slice ``[start, end)``, raising ``ValueError`` if the text cannot be returned."""
        if self._source is None:
            msg = f"Span({self.start}, {self.end}) has no source"
            raise ValueError(msg)
        if self.start < 0 or self.end < 0:
            msg = f"Span({self.start}, {self.end}) has negative indices"
            raise ValueError(msg)
        if self.start > self.end:
            msg = f"Span({self.start}, {self.end}) has inverted range"
            raise ValueError(msg)
        if self.end > len(self._source):
            msg = f"Span({self.start}, {self.end}) is out of bounds for source of length {len(self._source)}"
            raise ValueError(msg)
        return self._source[self.start : self.end]

    def has_source(self) -> bool:
        """Return ``True`` if a source string is attached to this span."""
        return self._source is not None

    def len(self) -> int:
        """Return the span length in codepoints.

        Returns 0 for sentinel/unknown spans with negative indices.
        """
        if self.start < 0 or self.end < 0:
            return 0
        return max(0, self.end - self.start)

    def is_empty(self) -> bool:
        """Return ``True`` if the span covers no elements (``start >= end``), including sentinel spans."""
        return self.start >= self.end

    def _coerce_source(self, other: "Span") -> "str | None":
        """Return the shared source, or raise if both spans have different sources."""
        if self._source is not None and other._source is not None and self._source != other._source:
            msg = "cannot merge spans from different sources"
            raise ValueError(msg)
        return self._source if self._source is not None else other._source

    def merge(self, other: "Span") -> "Span":
        """Return the smallest span that covers both ``self`` and ``other``.

        Raises ``ValueError`` if both spans carry different source strings.
        """
        source = self._coerce_source(other)
        return Span(min(self.start, other.start), max(self.end, other.end), source)

    def intersect(self, other: "Span") -> "Span":
        """Return the overlapping region of ``self`` and ``other``, or the ``UnknownSpan`` sentinel
        (``Span(-1, -1)``) if they are disjoint.

        Raises ``ValueError`` if both spans carry different source strings.
        """
        source = self._coerce_source(other)
        s = max(self.start, other.start)
        e = min(self.end, other.end)
        if s >= e:
            return UnknownSpan
        return Span(s, e, source)

    @classmethod
    def with_source(cls, start: int, end: int, source: str) -> "Span":
        """Construct a source-bearing span.  ``source`` is a plain Python ``str``; no copy is made."""
        return cls(start=start, end=end, _source=source)


UnknownSpan: Final = Span(-1, -1)


@dataclass(frozen=True, eq=True, slots=True)
class LineColPos:
    line: int
    col: int
    line_span: Span


class TerminalSource:
    def __init__(self, terminals: str):
        self.terminals: Final = terminals
        self.terminals_len: Final = len(terminals)
        self.line_ends: list[int] = []

    def consume_literal(self, pos: int, literal: str) -> Span | None:
        literal_len = len(literal)
        if pos + literal_len > self.terminals_len:
            return None
        for i in range(literal_len):
            if self.terminals[pos + i] != literal[i]:
                return None
        return Span(pos, pos + len(literal))

    def consume_regex(self, pos: int, regex: str) -> Span | None:
        if match := re.compile(regex).match(self.terminals, pos=pos):
            assert match.start() == pos  # noqa: S101
            return Span(pos, match.end())
        return None

    def pos_to_line_col(self, pos: int) -> LineColPos:
        if pos > len(self.terminals):
            msg = f"pos {pos} beyond end of terminals"
            raise ValueError(msg)
        if pos == len(self.terminals):
            pos -= 1
        if not self.line_ends:
            self.line_ends = [idx for idx, c in enumerate(self.terminals) if c == "\n"]
            if not self.line_ends or self.line_ends[-1] != len(self.terminals) - 1:
                self.line_ends.append(len(self.terminals) - 1)
        idx = bisect.bisect_left(self.line_ends, pos)
        assert idx < len(self.line_ends)  # noqa: S101
        if idx > 0:
            col = pos - self.line_ends[idx - 1] - 1
            line_span = Span(self.line_ends[idx - 1] + 1, self.line_ends[idx])
        else:
            col = pos
            line_span = Span(0, self.line_ends[0])
        return LineColPos(
            line=idx,
            col=col,
            line_span=line_span,
        )
