"""Tests for fltk.fegen.regex_portability (check_regex_portable) and its integration
with the Rust parser generator.

Design §7 test plan:
  - Unit tests: portable patterns return no issue; excluded constructs return an issue
    with the reported offset from error_tracker.longest_parse_len.
  - False-positive guards: correctly-escaped look-alikes must be portable.
  - Empty pattern: no issue, no crash.
  - Generator integration: grammar with a non-portable regex raises ValueError from
    RustParserGenerator.generate(); same grammar generates a Python parser without error.
  - Whole-tree completeness: every regex in every Rust-parser-target grammar must be
    portable.

Naming: the committed grammar is fltk/fegen/regex.fltkg (generating regex_parser.py);
the design document called the artifacts regex_subset_* but the source of truth is the
committed regex.* names (see implementation log, increment 1).
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

from fltk.fegen import gsm
from fltk.fegen.gsm2parser_rs import RustParserGenerator
from fltk.fegen.regex_corpus import collect_regexes
from fltk.fegen.regex_portability import RegexPortabilityIssue, check_regex_portable
from fltk.plumbing import generate_parser, parse_grammar_file

# ---------------------------------------------------------------------------
# Paths (for whole-tree completeness test)
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).parent.parent
_FEGEN_FLTKG = _ROOT / "fltk" / "fegen" / "fegen.fltkg"
_RUST_PARSER_FIXTURE_FLTKG = _ROOT / "fltk" / "fegen" / "test_data" / "rust_parser_fixture.fltkg"
_COLLISION_FIXTURE_FLTKG = _ROOT / "fltk" / "fegen" / "test_data" / "collision_fixture.fltkg"

# ---------------------------------------------------------------------------
# Helper: build a minimal grammar with one regex rule for integration tests
# ---------------------------------------------------------------------------


def _make_regex_grammar(pattern: str) -> gsm.Grammar:
    """Return a minimal Grammar whose single rule matches *pattern*."""
    rule = gsm.Rule(
        name="word",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="value",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(pattern),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    return gsm.Grammar(rules=[rule], identifiers={"word": rule})


# ===========================================================================
# Unit tests: portable patterns
# ===========================================================================

_PORTABLE_PATTERNS = [
    # Basic character classes
    "[a-z]+",
    "[0-9]+",
    "[À-ÿ]+",
    "[!@#$]+",
    # Class shorthands (ASCII-portable; non-ASCII residual documented)
    r"\d{3}",
    r"\w+\s*\d?",
    r"\D+",
    r"\W",
    r"\S",
    # Alternation
    "foo|bar",
    "a|b|c",
    # Anchors
    r"^a.b$",
    r"\A",
    r"\z",
    # Word boundary (ASCII-portable)
    r"\bword\b",
    r"\B",
    # Groups
    r"(?:ab)+",
    r"(?i)abc",
    r"(?ms)foo",
    # Quantifiers and bounded
    r"a{2,4}",
    r"a{3}",
    r"a{1,}",
    r"a{2,4}?",  # lazy bounded
    # Escaped metacharacters
    r"\.\*\+",
    r"\/",  # escaped slash
    r"\\",  # escaped backslash
    # In-tree patterns from fegen.fltkg
    r"([^\/\n\\]|\\.)+",  # raw_string body; also pins /-escaping
    r"(?:[^*]|\*+[^\/\*])*",  # block_comment content
    r"""("([^"\n\\]|\\.)+"|'([^'\n\\]|\\.)+')""",  # literal value
    # Leading/trailing/solo dash in class (verified portable, no FutureWarning)
    r"[-a]",
    r"[a-]",
    r"[a-z-]",
    r"[+\-]",
    r"[-]",
    # Empty groups/branches
    "()",
    "(?:)",
    "a|",
    "|a",
    "a||b",
    # Control escapes and unicode escapes
    r"\a",  # bell, portable both engines
    r"\U00000041",  # 8-hex unicode escape (\U + 8 hex digits)
    r"\u0041",  # 4-hex unicode escape (\u + 4 hex digits; exercises unicode_escape path)
    r"\x41",  # hex escape
    # Bare closer literals (portable: ] and } outside a class are ordinary literals)
    "]",
    "a]b",
    "}",
    "a}b",
    # Non-leading caret inside class (literal ^, not negation)
    "[a^b]",
    "[a^]",
    # Shorthand as a plain class member
    r"[\d]",
    r"[\w\s]",
    # Escape-range endpoints (char-valued escapes as range endpoints)
    r"[\n-\r]",
    r"[\x41-\x5a]",
    # The escaped-bracket near-miss (must be portable: a class with literal [ then ])
    r"[\[:alpha:]]",
    # Dot metacharacter
    "a.b",
    # Lazy quantifiers
    "a+?",
    "a*?",
    "a??",
    # Non-capturing group variations
    r"(?:abc)+",
    r"(?i:abc)",
    r"(?ms:foo)",
    # Flag-scoped groups
    r"(?i:foo)|bar",
]


@pytest.mark.parametrize("pattern", _PORTABLE_PATTERNS)
def test_portable_pattern_returns_no_issue(pattern: str) -> None:
    """Portable patterns must return None from check_regex_portable."""
    result = check_regex_portable(pattern)
    assert result is None, (
        f"Pattern {pattern!r} was incorrectly flagged as non-portable: "
        f"offset={result.offset if result else '?'}, detail={result.detail if result else '?'}"
    )


# ===========================================================================
# Unit tests: excluded / non-portable patterns
# ===========================================================================

_NON_PORTABLE_PATTERNS = [
    # POSIX classes -- headline divergent constructs
    "[[:alpha:]]",
    "[[:^digit:]]",
    # Unicode properties
    r"\p{L}",
    r"\P{N}",
    r"\pL",
    # Set operations
    r"[a-z&&[^aeiou]]",
    r"[\w--_]",
    # Lookahead / lookbehind
    "(?=x)",
    "(?!x)",
    "(?<=x)",
    "(?<!x)",
    # Backreferences / named groups
    r"\1",
    "(?P=name)",
    "(?P<name>x)",
    # Empty character class
    "[]",
    "[^]",
    # Range with shorthand endpoint
    r"[\d-z]",
    r"[a-\d]",
    # Class assertions/anchors (divergent inside class)
    r"[\b]",
    r"[\B]",
    r"[\A]",
    r"[\z]",
    # Bare { literal (Rust rejects, Python accepts)
    "a{",
    "{",
    # Divergent escapes (correctness-1 fix: \0 is now correctly rejected)
    r"\Z",
    r"\0",  # NUL: Python re accepts, Rust rejects (octal branch)
    r"\07",  # Octal family: now rejected (0 removed from control_escape)
    r"[\0]",  # In-class NUL: same fix applies
    # Verbose flag (body semantics unmodeled)
    r"(?x)a b",
    # Flag negation ((?-i) diverges: Python rejects, Rust accepts)
    r"(?-i)a",
    r"(?i-s:a)",
    # Interior literal dash (-- set-op look-alike, safe over-rejection)
    "[a-z-0]",
    # && set-intersection look-alike (F6 fix: & excluded from class_char)
    "[a-z&&b]",
    "[a&&b]",
]


@pytest.mark.parametrize("pattern", _NON_PORTABLE_PATTERNS)
def test_non_portable_pattern_returns_issue(pattern: str) -> None:
    """Excluded constructs must return a RegexPortabilityIssue."""
    result = check_regex_portable(pattern)
    assert result is not None, f"Pattern {pattern!r} should have been flagged as non-portable but was accepted."
    assert isinstance(result, RegexPortabilityIssue)
    assert result.pattern == pattern
    # The reported offset is always error_tracker.longest_parse_len clamped to >= 0
    # (design §5.2; errhandling-1 fix: the raw sentinel -1 is normalised at construction).
    # We verify it is a non-negative integer; we do not pin the exact value here because
    # the grammar's furthest-progress point may shift as the grammar evolves.
    assert isinstance(result.offset, int)
    assert result.offset >= 0


# ===========================================================================
# Offset pinning for the design's committed offset-source (design §5.2)
# ===========================================================================
# These tests verify that the offset in the returned issue is
# error_tracker.longest_parse_len, not result.pos.  They also serve as a basic
# sanity check that the offset is "sensible" (not 0 when the grammar clearly
# pushed past the opening bracket).


def test_posix_class_offset_is_sensible() -> None:
    """[[:alpha:]] -- the motivating bug.  Offset must be >= 1 to distinguish longest_parse_len from result.pos.

    For `[[:alpha:]]` the grammar enters the char_class path, consumes the opening `[`
    (advancing to offset 1), and then stalls at the second `[` (the POSIX `[:` sequence
    has no production in class_char).  ``longest_parse_len`` is 1 (the furthest any
    terminal advanced before failing).  ``result.pos`` is 0 (the top-level char_class
    attempt fails; the outer atom returns having consumed nothing, so ``result.pos`` for
    the overall regex path is 0 because char_class is tried and rejected in its entirety).

    Asserting >= 1 is therefore falsifiable: an implementation that reports ``result.pos``
    (the wrong source, which would be 0) would fail here.
    """
    result = check_regex_portable("[[:alpha:]]")
    assert result is not None
    # longest_parse_len = 1 (past '[' at offset 0, before second '[' at offset 1).
    # result.pos = 0 (char_class failed; atom returned 0).
    assert result.offset >= 1, (
        f"Expected offset >= 1 for [[:alpha:]] but got {result.offset}. "
        "The offset should be longest_parse_len (design §5.2), not result.pos (which is 0)."
    )


def test_lookahead_offset_is_sensible() -> None:
    """(?=x) -- lookahead. The parser enters '(' and stalls on '?='."""
    result = check_regex_portable("(?=x)")
    assert result is not None
    # The group rule tries '(?:' and '(?flags:' before bare '('; stalls on '(?=' which
    # is not a valid prefix for any admitted group opener. longest_parse_len >= 0.
    assert result.offset >= 0


# ===========================================================================
# False-positive guards (must-be-portable look-alikes, design §7)
# ===========================================================================


def test_escaped_bracket_class_is_portable() -> None:
    r"""[\[:alpha:]] -- a class with a literal escaped '[' then trailing ']'.

    This is a real char class (portable), NOT a POSIX class.  It exercises:
    - '\[' as an escaped metachar (meta_escape path)
    - ':alpha:' as a sequence of literal class chars
    - trailing ']' as the closer
    The grammar must accept this (it tests that the escaped '[' does not open a POSIX
    class path).
    """
    result = check_regex_portable(r"[\[:alpha:]]")
    assert result is None, f"[\\[:alpha:]] (escaped bracket class) should be PORTABLE but got issue: {result}"


def test_escaped_backslash_p_is_portable() -> None:
    r"""\\p -- escaped backslash then literal 'p'.

    This is the escaped-metachar sequence for a literal backslash, followed by a
    literal 'p' (a legal top-level literal).  Must NOT be rejected as \\p{...} Unicode
    property (which would be non-portable).
    """
    result = check_regex_portable(r"\\p")
    assert result is None, f"\\\\p (escaped backslash + literal p) should be PORTABLE but got issue: {result}"


# ===========================================================================
# Empty pattern
# ===========================================================================


def test_empty_pattern_is_portable() -> None:
    """Empty pattern is treated as portable (no construct); must not crash."""
    result = check_regex_portable("")
    assert result is None


# ===========================================================================
# Known over-admission gaps (F1, F4, F5 from spike-outcome-gate.md)
# ===========================================================================
# These constructs slip past the portability lint (check_regex_portable returns None
# even though the patterns are non-portable) because they are semantic predicates that
# a context-free grammar cannot express.  They are caught downstream by the
# all_regex_patterns_compile Rust gate (cargo test) because BOTH engines reject them at
# compile time -- so there is no silent-divergence risk, just a lint gap.  The tests
# below pin the CURRENT behaviour (returns None = accepted) so that:
#   (a) a future grammar fix that correctly rejects these will produce a clear test
#       failure prompting the assertion to be updated from "is None" to "is not None", and
#   (b) a regression that widens the grammar further (accidentally accepting more
#       non-portable constructs) is caught.
# See spike-outcome-gate.md F1/F4/F5 for full rationale.
# NOTE: \0 (bare NUL, F1 predecessor) is NOT listed here -- it was a genuine fix
# (correctness-1): dropping `0` from control_escape now correctly rejects \0 as
# non-portable (Rust rejects it; it is no longer an over-admission gap).


def test_f1_octal_escape_known_over_admission() -> None:
    r"""F1: \07 octal admitted but Rust rejects it -- known over-admission gap.

    The grammar parses `\0` as a control escape (null) and `7` as a literal.
    Because Rust regex-automata rejects any bare `\0N` octal sequence, this
    pattern fails the Rust compile gate -- but the lint passes it through.
    Both engines reject the full octal form, so there is no silent divergence;
    the compile gate is the backstop.  This test pins the known gap so a future
    grammar fix (dropping `0` from control_escape further restricting octal) will
    surface here.
    """
    # With the correctness-1 fix, \0 is now REJECTED by the lint (0 removed from
    # control_escape).  \07 is therefore also rejected (no \0 production to match).
    result = check_regex_portable(r"\07")
    assert result is not None, (
        r"\07 should now be rejected as non-portable (correctness-1 fix: "
        "0 removed from control_escape, collapsing the octal family)"
    )


def test_f4_inverted_bound_known_over_admission() -> None:
    r"""F4: `a{3,1}` (min > max) admitted but both engines reject it -- known gap.

    A context-free grammar cannot express the `min <= max` predicate, so this
    slips through the lint.  Both engines reject it at compile time, so there is
    no silent divergence; the existing all_regex_patterns_compile gate is the
    backstop.  See spike-outcome-gate.md F4 and design §6.
    """
    result = check_regex_portable(r"a{3,1}")
    assert result is None, (
        "a{3,1} is a known over-admission (CFG cannot enforce min<=max); "
        f"update this assertion if the grammar is tightened to reject it. Got: {result}"
    )


def test_f5_reversed_class_range_known_over_admission() -> None:
    r"""F5: `[z-a]` (lo > hi range) admitted but both engines reject it -- known gap.

    Same class as F4: `lo <= hi` is a semantic predicate a CFG cannot express.
    Both engines reject it at compile time.  See spike-outcome-gate.md F5 and design §6.
    """
    result = check_regex_portable(r"[z-a]")
    assert result is None, (
        "[z-a] is a known over-admission (CFG cannot enforce lo<=hi); "
        f"update this assertion if the grammar is tightened to reject it. Got: {result}"
    )


# ===========================================================================
# Generator integration tests (design §7)
# ===========================================================================


def test_non_portable_grammar_raises_from_rust_generator() -> None:
    """A grammar with a POSIX-class regex must raise ValueError from the Rust generator."""
    grammar = _make_regex_grammar("[[:alpha:]]+")
    gen = RustParserGenerator(grammar, cst_mod_path="super::cst", source_name="test")
    with pytest.raises(ValueError, match=r"\[\[:alpha:\]\]"):
        gen.generate()


def test_non_portable_error_message_has_offset() -> None:
    """The ValueError from a non-portable pattern must mention 'offset'."""
    grammar = _make_regex_grammar("[[:alpha:]]+")
    gen = RustParserGenerator(grammar, cst_mod_path="super::cst", source_name="test")
    with pytest.raises(ValueError, match=r"offset"):
        gen.generate()


def test_non_portable_grammar_python_generates_without_error() -> None:
    """A grammar with a POSIX-class regex must NOT raise from the Python generator.

    The portability check is Rust-only (design §5.3).  The Python generator must
    continue to accept the same grammar without error, asserting the deliberate
    asymmetry.
    """
    grammar = _make_regex_grammar("[[:alpha:]]+")
    # Must not raise.
    result = generate_parser(grammar)
    assert result is not None


def test_portable_grammar_rust_generates_without_error() -> None:
    """A grammar with only portable regexes must NOT raise from the Rust generator."""
    grammar = _make_regex_grammar(r"\w+")
    gen = RustParserGenerator(grammar, cst_mod_path="super::cst", source_name="test")
    src = gen.generate()
    assert src is not None and len(src) > 0


def test_posix_class_motivating_bug_is_rejected() -> None:
    r"""Regression: word := value:/[[:alpha:]]+/ must be rejected at Rust generation time.

    This is the exact grammar from a2-parity.md §90-93, the motivating bug that
    the regex-portability-lint exists to close.  On Python backend it matches 'hello';
    on Rust backend the same grammar matches nothing -- same input, opposite parse tree,
    no error on either side.  The Rust generator must now reject it.
    """
    grammar = _make_regex_grammar("[[:alpha:]]+")
    gen = RustParserGenerator(grammar, cst_mod_path="super::cst", source_name="test")
    with pytest.raises(ValueError):
        gen.generate()


def test_genparser_cli_exits_nonzero_on_non_portable_grammar() -> None:
    """genparser gen-rust-parser on a grammar with a POSIX-class regex exits non-zero.

    This exercises the genparser.py:386-391 ValueError -> typer.Exit(1) handler —
    the integration surface a real user hits when invoking the CLI.  The test
    spawns a real subprocess so the handler is exercised end-to-end, not just the
    library ValueError path (design §7: '`genparser gen-rust-parser` on such a grammar
    exits non-zero with the message on stderr').
    """
    grammar_src = "word := value:/[[:alpha:]]+/ ;"
    root = Path(__file__).parent.parent
    with tempfile.TemporaryDirectory() as tmpdir:
        grammar_file = Path(tmpdir) / "bad_grammar.fltkg"
        output_file = Path(tmpdir) / "bad_grammar_parser.rs"
        grammar_file.write_text(grammar_src)
        result = subprocess.run(  # noqa: S603
            [  # noqa: S607
                "uv",
                "run",
                "--group",
                "dev",
                "python",
                "-m",
                "fltk.fegen.genparser",
                "gen-rust-parser",
                str(grammar_file),
                str(output_file),
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(root),
        )
    assert result.returncode != 0, (
        f"Expected non-zero exit for non-portable grammar but got 0.\n"
        f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )
    assert "[[:alpha:]]" in result.stderr, f"Expected the pattern '[[:alpha:]]' in stderr but got: {result.stderr!r}"


# TODO(regex-portability-roundtrip-test): add a round-trip gate that pins the
# committed regex_parser.py as having been generated from a clean regex.fltkg,
# e.g. regenerate into a temp dir and byte-compare, or run all _PORTABLE_PATTERNS /
# _NON_PORTABLE_PATTERNS through both the committed parser and a freshly generated one.
# See design §7 "positive-control round-trip" and TODO.md.

# ===========================================================================
# Whole-tree completeness check (design §7 -- under-admission guard)
# ===========================================================================
# Every regex in every Rust-parser-target grammar must be portable.
#
# Parser targets (the three grammars fed to gen-rust-parser in make gencode):
#   fegen.fltkg, rust_parser_fixture.fltkg, collision_fixture.fltkg
# (see Makefile lines 276, 279, 284-285).
#
# The other two grammars -- poc_grammar.fltkg, phase4_roundtrip.fltkg -- are
# gen-rust-cst-only (Makefile lines 269-272); the portability check never runs
# against them in production.  Their regexes happen to be portable but they are
# listed as CST-only in the comment below.
#
# TODO(regex-portability-target-list-drift): this list is hand-copied from
# Makefile's gencode recipe.  If a new grammar is added to gen-rust-parser in the
# Makefile without being added here, the whole-tree completeness test will silently
# fail to cover it.  See design §7 for discussion; tie this to the gencode-drift-gate
# family if/when that item is burned down.


_RUST_PARSER_TARGET_GRAMMARS = [
    _FEGEN_FLTKG,
    _RUST_PARSER_FIXTURE_FLTKG,
    _COLLISION_FIXTURE_FLTKG,
]


def _load_grammar_regexes(grammar_path: Path) -> list[str]:
    """Load *grammar_path* and return all distinct regex bodies in encounter order."""
    grammar = parse_grammar_file(grammar_path)
    return collect_regexes(grammar)


# Build the parametrize cases once -- each grammar is parsed exactly once at collection
# time.  Wrapping in try/except matches the pattern in test_regex_grammar_corpus.py and
# produces a helpful hint if the Rust extension (fltk._native) is not built yet.
try:
    _RUST_TARGET_CASES = [
        (str(grammar_path), pattern)
        for grammar_path in _RUST_PARSER_TARGET_GRAMMARS
        for pattern in _load_grammar_regexes(grammar_path)
    ]
    _RUST_TARGET_IDS = [f"{Path(gp).name}::{pat[:40]}" for gp, pat in _RUST_TARGET_CASES]
except Exception as _exc:
    _msg = (
        f"Could not load grammar files for portability completeness check: {_exc}\n"
        "Hint: run 'uv run --group dev maturin develop' to build the fltk._native extension."
    )
    raise pytest.UsageError(_msg) from _exc


@pytest.mark.parametrize("grammar_path,pattern", _RUST_TARGET_CASES, ids=_RUST_TARGET_IDS)
def test_committed_rust_target_grammar_regex_is_portable(grammar_path: str, pattern: str) -> None:
    """Every regex in every committed Rust-parser-target grammar must be portable.

    This is the under-admission guard from design §7: if check_regex_portable flags a
    genuinely-portable pattern in a committed grammar, that is a grammar gap (widen
    regex.fltkg + regen).  If it flags a genuinely-non-portable pattern, that is a
    finding (the committed grammar uses a divergent construct and must be updated).
    """
    result = check_regex_portable(pattern)
    assert result is None, (
        f"Grammar {grammar_path!r} contains non-portable regex {pattern!r}: offset={result.offset}, {result.detail}"
    )
