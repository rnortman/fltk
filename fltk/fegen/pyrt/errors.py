from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Generic, TypeVar

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


_C0_END = 0x1F  # last C0 control codepoint
_TAB = 0x09  # TAB — kept literal
_DEL = 0x7F  # DEL
_C1_START = 0x80  # first C1 control codepoint
_C1_END = 0x9F  # last C1 control codepoint


def escape_control_chars(text: str) -> str:
    """Escape control characters in text using \\xHH notation (lowercase hex).

    Escaped ranges: U+0000-U+001F (except U+0009 TAB), U+007F (DEL), U+0080-U+009F (C1).
    TAB passes through unchanged. All other characters pass through unchanged.
    Cross-backend pinned: output is byte-identical with the Rust implementation.

    TODO(error-msg-bidi-escape): bidi controls (U+202A-U+202E, U+2066-U+2069) and
    U+2028/U+2029 pass through unescaped; accepted risk per design §Open questions A1.
    TODO(error-msg-escape-zero-copy): Rust zero-alloc Cow variant deferred; see TODO.md.
    """
    if not any(((cp := ord(ch)) <= _C0_END and cp != _TAB) or cp == _DEL or _C1_START <= cp <= _C1_END for ch in text):
        return text
    result = []
    for ch in text:
        cp = ord(ch)
        if (cp <= _C0_END and cp != _TAB) or cp == _DEL or (_C1_START <= cp <= _C1_END):
            result.append(f"\\x{cp:02x}")
        else:
            result.append(ch)
    return "".join(result)


def format_error_message(
    tracker: ErrorTracker,
    terminals: terminalsrc.TerminalSource,
    rule_name_lookup: Callable[[int], str],
) -> str:
    error_linecol = terminals.pos_to_line_col(tracker.longest_parse_len)
    col = error_linecol.col
    line_text = terminals.terminals[error_linecol.line_span.start : error_linecol.line_span.end]
    prefix = line_text[: max(col, 0)]
    suffix = line_text[max(col, 0) :]
    escaped_prefix = escape_control_chars(prefix)
    escaped_suffix = escape_control_chars(suffix)
    pad = len(escaped_prefix)
    result = (
        f"Syntax error at line {error_linecol.line + 1} col {error_linecol.col + 1}:\n"
        f"{escaped_prefix}{escaped_suffix}\n"
        f"{' ' * pad}^\n"
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
