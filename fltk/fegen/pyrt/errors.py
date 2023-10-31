from dataclasses import dataclass, field
from enum import auto, Enum
from typing import Generic, TypeVar

RuleId = TypeVar("RuleId")


class TokenType(Enum):
    LITERAL = auto()
    REGEX = auto()


@dataclass
class ParseContext(Generic[RuleId]):
    rule_id: RuleId
    token_type: TokenType
    token: str


@dataclass
class ErrorTracker(Generic[RuleId]):
    longest_parse_len: int = -1
    expected_context: list[ParseContext] = field(default_factory=list)

    def fail_literal(self, pos: int, rule_id: RuleId, literal: str) -> None:
        if pos < self.longest_parse_len:
            return
        context = ParseContext(rule_id, TokenType.LITERAL, literal)
        if pos == self.longest_parse_len:
            self.expected_context.append(context)
        else:
            self.expected_context = [context]
        self.longest_parse_len = pos
        return

    def fail_regex(self, pos: int, rule_id: RuleId, regex: str) -> None:
        if pos < self.longest_parse_len:
            return
        context = ParseContext(rule_id, TokenType.REGEX, regex)
        if pos == self.longest_parse_len:
            self.expected_context.append(context)
        else:
            self.expected_context = [context]
        self.longest_parse_len = pos
        return
