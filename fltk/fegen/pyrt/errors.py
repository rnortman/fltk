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


# Escape-set boundary constants — shared by _needs_escape and escape_control_chars.
_C0_END = 0x1F  # last C0 control codepoint
_TAB = 0x09  # TAB — kept literal
_DEL = 0x7F  # DEL
_C1_START = 0x80  # first C1 control codepoint
_C1_END = 0x9F  # last C1 control codepoint (also the \xHH/\uXXXX split point)
_ALM = 0x061C  # Arabic Letter Mark (Bidi_Control)
_ZW_START = 0x200B  # ZWSP — start of zero-width/LRM/RLM range
_ZW_END = 0x200F  # RLM — end of zero-width/LRM/RLM range
_LS_PS_START = 0x2028  # Line Separator — start of LS/PS/embedding/override range
_LS_PS_END = 0x202E  # RLO — end of LS/PS/embedding/override range
_WJ = 0x2060  # Word Joiner
_ISO_START = 0x2066  # LRI — start of bidi isolate range
_ISO_END = 0x2069  # PDI — end of bidi isolate range
_BOM = 0xFEFF  # ZWNBSP/BOM


def _needs_escape(cp: int) -> bool:
    """Return True iff codepoint cp must be escaped by escape_control_chars.

    Escape set (exhaustive):
      U+0000-U+001F except U+0009 (TAB)  — C0 controls
      U+007F                              — DEL
      U+0080-U+009F                       — C1 controls
      U+061C                              — ALM (Bidi_Control)
      U+200B-U+200F                       — ZWSP, ZWNJ, ZWJ, LRM, RLM
      U+2028-U+202E                       — LS, PS, LRE, RLE, PDF, LRO, RLO
      U+2060                              — Word Joiner
      U+2066-U+2069                       — LRI, RLI, FSI, PDI
      U+FEFF                              — ZWNBSP/BOM
    """
    return (
        (cp <= _C0_END and cp != _TAB)
        or cp == _DEL
        or _C1_START <= cp <= _C1_END
        or cp == _ALM
        or _ZW_START <= cp <= _ZW_END
        or _LS_PS_START <= cp <= _LS_PS_END
        or cp == _WJ
        or _ISO_START <= cp <= _ISO_END
        or cp == _BOM
    )


def escape_control_chars(text: str) -> str:
    """Escape control, bidi-control, line-separator, and zero-width characters.

    Escape set and representations (see _needs_escape for full codepoint list):
      cp <= U+009F in escape set  -> \\xHH (2 lowercase hex digits)
      cp > U+00FF in escape set   -> \\uXXXX (4 lowercase hex digits)

    TAB and all other characters not in the escape set pass through unchanged.
    Backslash is not escaped; output is not round-trippable (deliberate, preexisting).

    Cross-backend pinned: output is byte-identical with the Rust implementation in
    crates/fltk-cst-core/src/escape.rs:escape_control_chars.
    Pin is maintained by duplicated literal strings in tests/test_pyrt_errors.py and
    crates/fltk-cst-core/src/escape.rs #[cfg(test)].
    """
    if not any(_needs_escape(ord(ch)) for ch in text):
        return text
    result = []
    for ch in text:
        cp = ord(ch)
        if _needs_escape(cp):
            if cp <= _C1_END:
                result.append(f"\\x{cp:02x}")
            else:
                result.append(f"\\u{cp:04x}")
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
