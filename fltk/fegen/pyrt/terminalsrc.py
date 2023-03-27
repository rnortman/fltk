from dataclasses import dataclass
from typing import Generic, Optional, Sequence, TypeVar

TerminalType = TypeVar("TerminalType")


@dataclass(frozen=True, eq=True, slots=True)
class Span:
    """Span of elements in the range [start, end)"""
    start: int
    end: int


class TerminalSource(Generic[TerminalType]):
    def __init__(self, terminals: Sequence[TerminalType]):
        self.terminals = terminals

    def consume_literal(self, pos: int, literal: Sequence[TerminalType]) -> Optional[Span]:
        for i in range(len(literal)):
            if self.terminals[pos + i] != literal[i]:
                return None
        return Span(pos, pos + len(literal))
