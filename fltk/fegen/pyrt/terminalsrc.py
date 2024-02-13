import bisect
import re
from dataclasses import dataclass
from typing import Final, Optional


@dataclass(frozen=True, eq=True, slots=True)
class Span:
    """Span of elements in the range [start, end)"""

    start: int
    end: int


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

    def consume_literal(self, pos: int, literal: str) -> Optional[Span]:
        literal_len = len(literal)
        if pos + literal_len >= self.terminals_len:
            return None
        for i in range(literal_len):
            if self.terminals[pos + i] != literal[i]:
                return None
        return Span(pos, pos + len(literal))

    def consume_regex(self, pos: int, regex: str) -> Optional[Span]:
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
