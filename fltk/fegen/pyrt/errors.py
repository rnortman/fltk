from collections import defaultdict
from dataclasses import dataclass, field
from enum import auto, Enum
from typing import Callable, Generic, TypeVar

from fltk.fegen.pyrt import terminalsrc

RuleId = TypeVar("RuleId")


class TokenType(Enum):
    LITERAL = auto()
    REGEX = auto()


@dataclass(frozen=True, eq=True, slots=True)
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


def format_error_message(
    tracker: ErrorTracker,
    terminals: terminalsrc.TerminalSource,
    rule_name_lookup: Callable[[int], str],
) -> str:
    error_linecol = terminals.pos_to_line_col(tracker.longest_parse_len)
    result = (
        f"Syntax error at line {error_linecol.line+1} col {error_linecol.col+1}:\n"
        f"{terminals.terminals[error_linecol.line_span.start:error_linecol.line_span.end]}\n"
        f'{" "*error_linecol.col}^\n'
        f"Expected:\n"
    )
    rule_tokens = defaultdict(set)
    for context in tracker.expected_context:
        rule_tokens[context.rule_id].add(context)
    for rule_id in rule_tokens:
        result += f'  From rule "{rule_name_lookup(rule_id)}":\n'
        for context in rule_tokens[rule_id]:
            result += f"    {context.token_type.name}: {context.token!r}\n"
    return result
