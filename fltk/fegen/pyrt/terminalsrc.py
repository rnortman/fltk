from dataclasses import dataclass
import re
from typing import Final, Optional


@dataclass(frozen=True, eq=True, slots=True)
class Span:
    """Span of elements in the range [start, end)"""

    start: int
    end: int


UnknownSpan: Final = Span(-1, -1)


class TerminalSource:
    def __init__(self, terminals: str):
        self.terminals: Final = terminals
        self.terminals_len: Final = len(terminals)

    def consume_literal(self, pos: int, literal: str) -> Optional[Span]:
        print(f"literal: {pos} {literal!r}")
        l = len(literal)
        if pos + l >= self.terminals_len:
            return None
        for i in range(l):
            if self.terminals[pos + i] != literal[i]:
                return None
        return Span(pos, pos + len(literal))

    def consume_regex(self, pos: int, regex: str) -> Optional[Span]:
        print(f"regex: {pos} {regex!r}")
        if match := re.compile(regex).match(self.terminals, pos=pos):
            assert match.start() == pos
            print(match)
            return Span(pos, match.end())
        return None
