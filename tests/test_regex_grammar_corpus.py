"""Corpus test: every regex in the in-tree .fltkg grammars must be accepted by the regex parser.

This test provides programmatic evidence that the regex grammar (fltk/fegen/regex.fltkg)
is fit as the lint recognizer for the portable subset: it runs the grammar's own generated
parser against every distinct regex that appears in real, working FLTK grammars.

The general extract/classify machinery lives in fltk.fegen.regex_corpus (the single source
of truth); this module is the committed corpus harness that exercises the *in-tree* grammars.

Out-of-tree grammars (e.g. clockwork) are exercised ad hoc via the grammar-agnostic CLI:

    uv run python -m fltk.fegen.regex_corpus <path/to/grammar.fltkg>

Nothing clockwork-specific is committed here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fltk.fegen.regex_corpus import classify_pattern, collect_regexes, run_cli
from fltk.plumbing import parse_grammar_file

# ---------------------------------------------------------------------------
# Paths to in-tree grammars under test
# ---------------------------------------------------------------------------

_FEGEN_FLTKG = Path(__file__).parent.parent / "fltk" / "fegen" / "fegen.fltkg"
_REGEX_FLTKG = Path(__file__).parent.parent / "fltk" / "fegen" / "regex.fltkg"


# ---------------------------------------------------------------------------
# Helper: build a pytest parametrize id from a pattern string
# ---------------------------------------------------------------------------


def _pattern_id(pattern: str) -> str:
    """Return a short, readable test ID for a regex pattern."""
    truncated = pattern[:40] + ("..." if len(pattern) > 40 else "")
    return truncated.replace("[", "(").replace("]", ")")  # avoid pytest bracket issues


# ---------------------------------------------------------------------------
# Corpus parametrize fixtures
# ---------------------------------------------------------------------------


def _corpus_cases(grammar_path: Path) -> list[tuple[str, str]]:
    """Parse *grammar_path* and return (pattern, grammar_name) pairs for each distinct regex."""
    grammar = parse_grammar_file(grammar_path)
    patterns = collect_regexes(grammar)
    return [(p, grammar_path.name) for p in patterns]


try:
    _FEGEN_CORPUS: list[tuple[str, str]] = _corpus_cases(_FEGEN_FLTKG)
    _REGEX_CORPUS: list[tuple[str, str]] = _corpus_cases(_REGEX_FLTKG)
except Exception as exc:
    msg = (
        f"Could not load corpus from grammar files ({_FEGEN_FLTKG}, {_REGEX_FLTKG}): {exc}\n"
        "Hint: run 'uv run --group dev maturin develop' to build the fltk._native extension."
    )
    raise pytest.UsageError(msg) from exc

_ALL_CORPUS: list[tuple[str, str]] = _FEGEN_CORPUS + _REGEX_CORPUS


@pytest.mark.parametrize("pattern,grammar_name", _ALL_CORPUS, ids=[_pattern_id(p) for p, _ in _ALL_CORPUS])
def test_corpus_pattern_is_accepted(pattern: str, grammar_name: str) -> None:
    """Every distinct regex in the in-tree corpora must be accepted by the regex grammar.

    A rejection means either:
    - The grammar under-admits (a grammar gap) -- fix regex.fltkg + regen.
    - The pattern genuinely uses a non-portable construct -- document it.
    Both outcomes are surfaced as named failures with the pattern visible in the test ID.
    """
    accepted = classify_pattern(pattern)
    assert accepted, (
        f"Pattern {pattern!r} from {grammar_name!r} was REJECTED by the regex grammar. "
        "Triage: is this a grammar gap (fix regex.fltkg) or a genuinely non-portable pattern?"
    )


# ---------------------------------------------------------------------------
# Risk-point pins (§3.3 of the design)
#
# These pins are separate from the parametric sweep so that each documented
# risk point has a name, an explaining comment, and a direct assertion.
# A future grammar edit that breaks one will fail with a clear, named test.
# ---------------------------------------------------------------------------


def test_fegen_block_comment_content() -> None:
    """fegen.fltkg block-comment content: (?:[^*]|\\*+[^\\/\\*])*

    The decoded gsm.Regex.value is `(?:[^*]|\\*+[^\\/\\*])*`.
    This exercises:
    - `(?:...)` non-capturing group (admitted via non_capturing rule)
    - `|` alternation with two branches (non-* char, or one-or-more `*` not followed by / or *)
    - Escaped slash `\\/` (the gsm.Regex.value stores the decoded body; `\\/` is
      backslash + slash, admitted via escape -> literal_char -> `\\.` path or class_char)
    - The `*` quantifier on the outer group (zero-or-more), making the whole
      pattern potentially empty (valid -- the start rule accepts empty via concatenation?)
    """
    # Decoded value as stored in gsm.Regex.value (outer /.../ stripped by fltk2gsm.visit_regex)
    pattern = r"(?:[^*]|\*+[^\/\*])*"
    assert classify_pattern(pattern), f"Block-comment content pattern should be ACCEPTED: {pattern!r}"


def test_fegen_block_comment_end() -> None:
    """fegen.fltkg block-comment end: \\*+\\/

    The decoded gsm.Regex.value is `\\*+\\/` (backslash-star + plus + backslash-slash).
    This exercises the escape path for both `*` (escaped metachar) and `/` (escaped slash
    which `.fltkg` tokenizer requires to avoid ending the terminal early).
    """
    pattern = r"\*+\/"
    assert classify_pattern(pattern), f"Block-comment end pattern should be ACCEPTED: {pattern!r}"


def test_fegen_line_comment_content() -> None:
    """fegen.fltkg line-comment content: [^\\n]*

    Exercises a negated char class with `\\n` (escaped newline shorthand) and the `*` quantifier.
    The decoded value is `[^\\n]*`.
    """
    pattern = r"[^\n]*"
    assert classify_pattern(pattern), f"Line-comment content pattern should be ACCEPTED: {pattern!r}"


def test_fegen_identifier() -> None:
    """fegen.fltkg identifier: [_a-z][_a-z0-9]*

    A basic character class with underscore, ASCII letters/digits, and `*` quantifier.
    """
    pattern = r"[_a-z][_a-z0-9]*"
    assert classify_pattern(pattern), f"Identifier pattern should be ACCEPTED: {pattern!r}"


def test_fegen_raw_string_body() -> None:
    """fegen.fltkg raw_string body: ([^\\/\\n\\\\]|\\\\.)+

    The decoded gsm.Regex.value is `([^\\/\\n\\\\]|\\\\.)+`.
    This exercises:
    - A capturing group `(...)` (admitted via capturing rule)
    - Alternation between two branches inside the group
    - Negated class with escaped metacharacters `\\/`, `\\n`, `\\\\` (slash, newline, backslash)
    - `\\\\.` -- an escape sequence matching any escaped char
    - `+` quantifier on the outer group
    Note: This is the pattern that matches the inside of a /.../ terminal in .fltkg files.
    It uses capturing groups (not non-capturing) -- both forms are admitted by the grammar.
    """
    pattern = r"([^\/\n\\]|\\.)+"
    assert classify_pattern(pattern), f"Raw-string body pattern should be ACCEPTED: {pattern!r}"


def test_fegen_literal_value() -> None:
    """fegen.fltkg literal value: (\"([^\"\\n\\\\]|\\\\.)+\"|'([^'\\n\\\\]|\\\\.)+')"

    The decoded gsm.Regex.value is the full double-or-single quoted string literal pattern.
    This exercises alternation at top level, nested capturing groups, negated classes with
    multiple escaped chars, and `+` quantifiers.
    """
    pattern = r"""("([^"\n\\]|\\.)+"|'([^'\n\\]|\\.)+')"""
    assert classify_pattern(pattern), f"Literal-value pattern should be ACCEPTED: {pattern!r}"


def test_cli_entry_point_accepts_in_tree_grammar() -> None:
    """Smoke-test the grammar-agnostic CLI entry point against an in-tree grammar.

    Calls ``run_cli`` directly with the path to ``fltk/fegen/regex.fltkg`` and
    asserts the exit code is 0 (every regex accepted).  This confirms the CLI wiring
    (argument parsing, grammar loading, collect_regexes + classify_pattern loop) works
    end-to-end without spawning a subprocess.

    The general CLI is intended for ad-hoc use against any .fltkg file (including
    out-of-tree grammars like clockwork, whose path is supplied by the developer on the
    command line and is never committed here):

        uv run python -m fltk.fegen.regex_corpus <path/to/grammar.fltkg>
    """
    exit_code = run_cli([str(_REGEX_FLTKG)])
    assert exit_code == 0, f"CLI exited {exit_code}; expected 0 (all patterns accepted) for regex.fltkg"


def test_cli_exit2_on_wrong_arg_count() -> None:
    """run_cli returns exit code 2 when called with wrong number of arguments."""
    exit_code = run_cli([])
    assert exit_code == 2, f"CLI exited {exit_code}; expected 2 (usage error) for empty argv"


def test_cli_exit2_on_nonexistent_file() -> None:
    """run_cli returns exit code 2 when the grammar file does not exist."""
    exit_code = run_cli(["nonexistent_grammar_that_does_not_exist.fltkg"])
    assert exit_code == 2, "CLI exited non-2; expected 2 (file-not-found) for nonexistent grammar"


def test_cli_exit1_on_rejected_pattern(tmp_path: Path) -> None:
    """run_cli returns exit code 1 when a grammar contains a non-portable regex.

    Constructs a minimal .fltkg grammar containing a lookahead (?=x) -- a pattern
    that the regex grammar rejects -- and confirms run_cli exits 1 (some rejected).
    This guards the any_rejected flag and the exit-1 branch end-to-end.
    """
    # A minimal grammar with one rule that uses a non-portable lookahead pattern.
    # The regex /(?=x)/ is rejected by regex.fltkg (no lookahead production).
    grammar_content = "rule := /(?=x)/ ;\n"
    grammar_file = tmp_path / "test_rejected.fltkg"
    grammar_file.write_text(grammar_content)

    exit_code = run_cli([str(grammar_file)])
    assert exit_code == 1, f"CLI exited {exit_code}; expected 1 (rejected pattern) for grammar with /(?=x)/"


def test_regex_fltkg_self_referential() -> None:
    """regex.fltkg is self-describing: its own leaf regexes must be in the portable subset.

    The regex grammar uses regexes to parse regexes; its own terminals must therefore be
    accepted by the grammar it defines.  This test asserts the count of distinct regexes
    in regex.fltkg matches what we expect, as a change-detector.
    """
    # Reuse the already-computed _REGEX_CORPUS list (avoids re-parsing regex.fltkg).
    patterns = [p for p, _ in _REGEX_CORPUS]
    # As of the spike, regex.fltkg contains exactly these 12 distinct regex terminals.
    # If this set changes, update it and review the added/removed patterns.
    expected_patterns = frozenset(
        {
            "[.*+?()\\[\\]{}|^$\\/\\\\\\-]",  # metachar_char: the set of regex metacharacters
            "[0-9A-Fa-f][0-9A-Fa-f]",  # hex2: exactly 2 hex digits (e.g. \xHH)
            "[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]",  # hex4: exactly 4 hex digits (e.g. \uHHHH)
            "[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]",  # hex8
            "[0-9]+",  # octal_digits: one or more decimal digits (octal escape body)
            "[Az]",  # word_boundary_char: A or z (for \A, \z anchors)
            "[^.*+?()\\[|^$\\\\{\\n]",  # atom_char: ordinary non-metachar chars (top-level)
            "[^\\\\\\]\\[\\-\\n]",  # class_char: ordinary chars inside a character class
            "[bB]",  # word_boundary_b: b or B (for \b, \B word-boundary)
            "[dDwWsS]",  # class_shorthand: d/D/w/W/s/S shorthand escapes
            "[imsU]+",  # flag_char: one or more regex flags
            "[nrtfv0a]",  # simple_escape_char: n/r/t/f/v/0/a escape letters
        }
    )
    assert set(patterns) == expected_patterns, (
        f"regex.fltkg distinct regex terminals changed.\n"
        f"  Added:   {set(patterns) - expected_patterns!r}\n"
        f"  Removed: {expected_patterns - set(patterns)!r}\n"
        "Update expected_patterns in this test and review the change."
    )
    rejected = [p for p in patterns if not classify_pattern(p)]
    assert not rejected, (
        f"regex.fltkg has {len(rejected)} self-referential pattern(s) rejected by itself: "
        + ", ".join(repr(p) for p in rejected)
    )
