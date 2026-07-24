"""Cross-backend parity tests: Python fixture parser vs rust_parser_fixture.Parser.

Requires rust_parser_fixture to be built: run 'make build-rust-parser-fixture' first.
A CI lane where every test here is skipped is a failure signal.
"""

from __future__ import annotations

from pathlib import Path

import pytest

rust_parser_fixture = pytest.importorskip(
    "rust_parser_fixture",
    reason="rust_parser_fixture not built; run 'make build-rust-parser-fixture' first",
)

from fltk.fegen.pyrt import terminalsrc as tsrc  # noqa: E402
from fltk.plumbing import generate_parser, parse_grammar_file  # noqa: E402
from tests.parser_parity import FAIL, PARTIAL, SUCCESS, run_parity_corpus_entry  # noqa: E402

_FIXTURE_FLTKG = Path(__file__).parent.parent / "fltk" / "fegen" / "test_data" / "rust_parser_fixture.fltkg"

_py_parser_no_trivia = None
_py_parser_trivia = None


def _get_py_parser_class(capture_trivia: bool):  # noqa: FBT001
    """Return cached generated Python parser class for the fixture grammar."""
    global _py_parser_no_trivia, _py_parser_trivia  # noqa: PLW0603
    if capture_trivia:
        if _py_parser_trivia is None:
            _py_parser_trivia = generate_parser(parse_grammar_file(_FIXTURE_FLTKG), capture_trivia=True).parser_class
        return _py_parser_trivia
    else:
        if _py_parser_no_trivia is None:
            _py_parser_no_trivia = generate_parser(
                parse_grammar_file(_FIXTURE_FLTKG), capture_trivia=False
            ).parser_class
        return _py_parser_no_trivia


def _py_parser(text: str, capture_trivia: bool):  # noqa: FBT001
    parser_class = _get_py_parser_class(capture_trivia)
    ts = tsrc.TerminalSource(text)
    return parser_class(terminalsrc=ts)


def _rust_parser(text: str, capture_trivia: bool):  # noqa: FBT001
    return rust_parser_fixture.parser.Parser(text, capture_trivia=capture_trivia)


_CORPUS = [
    # Basic rules
    ("num", "123", SUCCESS),
    ("name", "hello", SUCCESS),
    ("atom", "42", SUCCESS),
    ("atom", "world", SUCCESS),
    # Direct left recursion
    ("expr", "1+2+3", SUCCESS),
    # Trailing-character pair: same input with trailing whitespace; expr stops before unmatched space
    ("expr", "1+2+3 ", PARTIAL(5)),
    ("expr", "x", SUCCESS),
    # Indirect left recursion
    ("lval", "x", SUCCESS),
    ("rval", "1", SUCCESS),
    # Quantifiers: items := item:atom+ (no separator, so "123" parses as one num)
    ("items", "123", SUCCESS),
    # + on empty input must fail (not vacuously succeed)
    ("items", "", FAIL),
    ("zero_items", "", SUCCESS),
    ("zero_items", "1", SUCCESS),
    # WS_REQUIRED
    ("stmt", "x = y", SUCCESS),
    # Suppressed/included
    ("tagged", "tagword", SUCCESS),
    # Union label
    ("val", "42", SUCCESS),
    ("val", "hello", SUCCESS),
    ("val", "!@#$", SUCCESS),
    # Multibyte
    ("arrow", "→x", SUCCESS),
    ("latin_word", "àáâ", SUCCESS),
    # paren_expr
    ("paren_expr", "(42)", SUCCESS),
    ("paren_expr", "( hello )", SUCCESS),
    # leading_ws rule (initial_sep = WS_ALLOWED)
    ("leading_ws", "42", SUCCESS),
    ("leading_ws", "   42", SUCCESS),
    # grouped sub-expression with separators
    ("grouped", "(42)", SUCCESS),
    ("grouped", "( hello )", SUCCESS),
    # rec_via_sub recursion through sub-expression:
    # "1x" → sub-expr: inner:atom("1"), suffix:name("x")
    ("rec_via_sub", "1x", SUCCESS),
    # "1x+y" → sub-expr: inner:rec_via_sub("1x") . "+", suffix:name("y")
    ("rec_via_sub", "1x+y", SUCCESS),
    # nest: right-recursive nesting (depth-limit rules, §5)
    ("nest", "42", SUCCESS),
    ("nest", "(42)", SUCCESS),
    ("nest", "((42))", SUCCESS),
    # nest_sum: left-recursive sum of nests (depth-limit rules, §5)
    ("nest_sum", "42", SUCCESS),
    ("nest_sum", "42+99", SUCCESS),
    ("nest_sum", "1+(2)", SUCCESS),
    # nest/nest_sum failures: unclosed paren / no leading operand
    ("nest", "(42", FAIL),
    ("nest_sum", "+42", FAIL),
    # Portable-but-tricky regex parity cases (design §5.6)
    # digit_seq: ASCII \d shorthand
    ("digit_seq", "123", SUCCESS),
    ("digit_seq", "abc", FAIL),
    # word_seq: ASCII \w shorthand
    ("word_seq", "hello_42", SUCCESS),
    ("word_seq", "!!", FAIL),
    # ws_seq: ASCII \s shorthand
    ("ws_seq", "   ", SUCCESS),
    ("ws_seq", "abc", FAIL),
    # three_to_five_digits: bounded quantifier {3,5}
    ("three_to_five_digits", "123", SUCCESS),
    ("three_to_five_digits", "12345", SUCCESS),
    ("three_to_five_digits", "12", FAIL),
    ("three_to_five_digits", "123456", PARTIAL(5)),
    # exactly_two_digits: exact-count bounded {2}
    ("exactly_two_digits", "42", SUCCESS),
    ("exactly_two_digits", "4", FAIL),
    ("exactly_two_digits", "123", PARTIAL(2)),
    # escaped_metas: literal dot/star/plus
    ("escaped_metas", ".*+", SUCCESS),
    ("escaped_metas", "abc", FAIL),
    # latin_range: non-ASCII range [À-Ö]+
    ("latin_range", "ÀÁÂ", SUCCESS),
    ("latin_range", "abc", FAIL),
    # nc_group_alt: non-capturing group with alternation
    ("nc_group_alt", "abab", SUCCESS),
    ("nc_group_alt", "cdcd", SUCCESS),
    ("nc_group_alt", "efgh", FAIL),
    # case_insensitive: (?i) flag
    ("case_insensitive", "hello", SUCCESS),
    ("case_insensitive", "HELLO", SUCCESS),
    ("case_insensitive", "123", FAIL),
    # anchored_word: ^[a-z]+$ anchors
    ("anchored_word", "hello", SUCCESS),
    ("anchored_word", "hello123", FAIL),
    # Failures
    ("num", "abc", FAIL),
    ("name", "123", FAIL),
    ("stmt", "x=y", FAIL),
    # Control characters in failing line — exercises escape_control_chars in error messages.
    # num fails at pos 0; the quoted line contains \x1b[31m (ESC + "[31m").
    ("num", "\x1b[31mabc", FAIL),
    # stmt: name matches "x", WS_REQUIRED separators consume each \r (\s matches \r),
    # rhs:atom fails at pos 4 ('@'); two \r chars before the caret get escaped.
    ("stmt", "x\r=\r@", FAIL),
    # Bidi/invisible characters in failing input — exercises the extended escape set.
    # num fails at pos 0; U+202E (RLO bidi override) in the quoted line must be escaped as \u202e.
    ("num", "\u202e123", FAIL),
    # name fails at pos 0; LRI (U+2066) + ZWSP (U+200B) are both invisible and must be escaped.
    ("name", "\u2066\u200babc", FAIL),
    # stmt: name matches "x", WS_REQUIRED separators consume each U+2028 LS (\s matches it),
    # rhs:atom fails at pos 4 ('@'); two \u2028 escapes before the caret are produced.
    # Also pins that the parity comparator's str.splitlines() sees no raw LS in the message.
    ("stmt", "x\u2028=\u2028@", FAIL),
]

_CORPUS_IDS = [f"{r}-{i}" for i, (r, _, _) in enumerate(_CORPUS)]


@pytest.mark.parametrize("capture_trivia", [False, True])
@pytest.mark.parametrize("rule,text,expected", _CORPUS, ids=_CORPUS_IDS)
def test_parity(rule, text, expected, capture_trivia):
    py_p = _py_parser(text, capture_trivia)
    rust_p = _rust_parser(text, capture_trivia)
    ts = tsrc.TerminalSource(text)
    run_parity_corpus_entry(py_p, rust_p, ts, rule=rule, text=text, expected=expected)
