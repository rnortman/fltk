import bisect
from dataclasses import dataclass
import re
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
        l = len(literal)
        if pos + l >= self.terminals_len:
            return None
        for i in range(l):
            if self.terminals[pos + i] != literal[i]:
                return None
        return Span(pos, pos + len(literal))

    def consume_regex(self, pos: int, regex: str) -> Optional[Span]:
        if match := re.compile(regex).match(self.terminals, pos=pos):
            assert match.start() == pos
            return Span(pos, match.end())
        return None

    def pos_to_line_col(self, pos: int) -> LineColPos:
        if pos >= len(self.terminals):
            raise ValueError(f"pos {pos} beyond end of terminals")
        if not self.line_ends:
            self.line_ends = [idx for idx, c in enumerate(self.terminals) if c == "\n"]
            if not self.line_ends or self.line_ends[-1] != len(self.terminals) - 1:
                self.line_ends.append(len(self.terminals) - 1)
        idx = bisect.bisect_left(self.line_ends, pos)
        assert idx < len(self.line_ends)
        return LineColPos(
            line=idx,
            col=pos - self.line_ends[idx - 1] - 1,
            line_span=Span(self.line_ends[idx - 1] + 1, self.line_ends[idx]),
        )
