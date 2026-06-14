"""Tests for nullable-repetition infinite-loop guard + validator gap.

Test order follows design §5: §5.1 (backend guard), §5.2 (validator gap),
§5.3 (generator rejection), §5.4 (source-text guard placement).

Trigger grammar: rule := (r"a*" .)+
  - outer item: ONE_OR_MORE over a sub-expression
  - inner item: REQUIRED with term Regex(r"a*") — always matches, including empty string
  - current validator passes it (Item.can_be_nil ignores term)
  - current loop has no progress guard → infinite loop on empty match
"""

from __future__ import annotations

import ast
import pathlib
import shutil
import subprocess
import sys
import textwrap

import pytest

from fltk.fegen import gsm, gsm2parser, gsm2tree
from fltk.fegen.gsm2parser_rs import RustParserGenerator
from fltk.fegen.gsm2tree_rs import RustCstGenerator
from fltk.iir.context import create_default_context
from fltk.iir.py import compiler
from fltk.iir.py import reg as pyreg
from fltk.plumbing import generate_parser

# ---------------------------------------------------------------------------
# Trigger grammar construction (shared by all tests)
# ---------------------------------------------------------------------------


def _make_trigger_grammar() -> gsm.Grammar:
    """Build the trigger grammar: rule := (r"a*" .)+

    Outer item is ONE_OR_MORE over a sub-expression whose only inner item is
    REQUIRED with term Regex(r"a*").  The inner item always matches (including
    empty string) because `a*` can match zero characters.

    Item.can_be_nil() checks both the quantifier and the term: REQUIRED + nullable
    Regex → True, so validate_no_repeated_nil_items raises ValueError.
    """
    inner_items = gsm.Items(
        items=[
            gsm.Item(
                label="content",
                disposition=gsm.Disposition.INCLUDE,
                term=gsm.Regex(r"a*"),
                quantifier=gsm.REQUIRED,
            )
        ],
        sep_after=[gsm.Separator.NO_WS],
    )
    rule = gsm.Rule(
        name="rule",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INCLUDE,
                        term=[inner_items],  # sub-expression (list of Items)
                        quantifier=gsm.ONE_OR_MORE,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    return gsm.Grammar(rules=[rule], identifiers={"rule": rule})


def _make_trigger_grammar_empty_literal() -> gsm.Grammar:
    """Variant: REQUIRED item with Literal("") (empty string literal)."""
    inner_items = gsm.Items(
        items=[
            gsm.Item(
                label="content",
                disposition=gsm.Disposition.INCLUDE,
                term=gsm.Literal(""),
                quantifier=gsm.REQUIRED,
            )
        ],
        sep_after=[gsm.Separator.NO_WS],
    )
    rule = gsm.Rule(
        name="rule",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INCLUDE,
                        term=[inner_items],
                        quantifier=gsm.ONE_OR_MORE,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    return gsm.Grammar(rules=[rule], identifiers={"rule": rule})


def _make_trigger_grammar_nil_rule_ref() -> gsm.Grammar:
    """Variant: REQUIRED item with Identifier referencing a nil-able rule."""
    nullable_rule = gsm.Rule(
        name="nullable",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="v",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"a*"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    inner_items = gsm.Items(
        items=[
            gsm.Item(
                label="content",
                disposition=gsm.Disposition.INCLUDE,
                term=gsm.Identifier("nullable"),
                quantifier=gsm.REQUIRED,
            )
        ],
        sep_after=[gsm.Separator.NO_WS],
    )
    outer_rule = gsm.Rule(
        name="rule",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INCLUDE,
                        term=[inner_items],
                        quantifier=gsm.ONE_OR_MORE,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    return gsm.Grammar(
        rules=[nullable_rule, outer_rule],
        identifiers={"nullable": nullable_rule, "rule": outer_rule},
    )


# ---------------------------------------------------------------------------
# §5.1 Python backend hang/guard test
# ---------------------------------------------------------------------------

# The subprocess script builds the trigger grammar, monkeypatches
# validate_no_repeated_nil_items to a no-op (isolating the loop guard layer),
# generates the parser, then calls apply__parse_rule on "aab" and "b".
# Expected: returns pos=2 for "aab" (empty iteration discarded) and None for "b".

_PYTHON_HANG_SCRIPT = textwrap.dedent("""\
    from fltk.fegen import gsm
    from fltk.fegen.pyrt import terminalsrc
    from fltk.plumbing import generate_parser

    # Build trigger grammar: rule := (r"a*" .)+
    inner_items = gsm.Items(
        items=[
            gsm.Item(
                label="content",
                disposition=gsm.Disposition.INCLUDE,
                term=gsm.Regex(r"a*"),
                quantifier=gsm.REQUIRED,
            )
        ],
        sep_after=[gsm.Separator.NO_WS],
    )
    rule = gsm.Rule(
        name="rule",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INCLUDE,
                        term=[inner_items],
                        quantifier=gsm.ONE_OR_MORE,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    grammar = gsm.Grammar(rules=[rule], identifiers={"rule": rule})

    # Monkeypatch: bypass validate_no_repeated_nil_items so the loop guard
    # layer is tested in isolation (without the validator preventing codegen).
    import fltk.fegen.gsm as gsm_mod
    gsm_mod.validate_no_repeated_nil_items = lambda g: None

    # generate_parser calls classify_trivia_rules (which calls the patched validator),
    # then generates and execs the parser class.
    pr = generate_parser(grammar)
    Parser = pr.parser_class

    # Test 1: "aab" — iteration 1 consumes "aa" (pos 0→2), iteration 2 tries at pos 2
    # and matches empty "a*" → guard fires: break, return ApplyResult(pos=2).
    terminals1 = terminalsrc.TerminalSource("aab")
    parser1 = Parser(terminalsrc=terminals1)
    result1 = parser1.apply__parse_rule(0)
    print(f"aab result: {result1}")
    assert result1 is not None, "Expected Some result for 'aab'"
    assert result1.pos == 2, f"Expected pos=2 for 'aab', got pos={result1.pos}"

    # Test 2: "b" — first iteration matches empty string immediately (pos 0);
    # guard fires: break immediately, pos==span_start → + check fails → None.
    terminals2 = terminalsrc.TerminalSource("b")
    parser2 = Parser(terminalsrc=terminals2)
    result2 = parser2.apply__parse_rule(0)
    print(f"b result: {result2}")
    assert result2 is None, f"Expected None for 'b' (no progress on first iter), got {result2}"

    print("PASS")
""")


def test_python_backend_guard():
    """§5.1 Python backend: loop terminates on empty-match iteration.

    The subprocess monkeypatches the validator to a no-op so the loop guard is tested
    in isolation; the guard fires and the subprocess prints PASS.
    """
    try:
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-c", _PYTHON_HANG_SCRIPT],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired:
        pytest.fail("Python backend hung on nullable repetition (infinite loop — loop guard missing)")

    assert result.returncode == 0, (
        f"Python backend guard test failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "PASS" in result.stdout, f"Expected PASS in output:\nstdout: {result.stdout}\nstderr: {result.stderr}"


# ---------------------------------------------------------------------------
# §5.1 Rust backend hang/guard test
# ---------------------------------------------------------------------------

_RUST_MAIN_RS = textwrap.dedent("""\
    mod cst;
    mod parser;

    use parser::Parser;

    fn main() {
        // Test 1: "aab" — should return Some(pos=2) after guard fires on empty iteration.
        let src = "aab";
        let mut p = Parser::new(src, false);
        let result = p.apply__parse_rule(0);
        match &result {
            Some(r) => {
                println!("aab result: pos={}", r.pos);
                assert_eq!(r.pos, 2, "Expected pos=2 for 'aab', got pos={}", r.pos);
            }
            None => {
                // The validator rejects this grammar before we get here; if cargo builds
                // cleanly then either the guard works or validator rejected it.
                println!("aab result: None (may be expected if grammar was rejected by validator)");
                std::process::exit(1);
            }
        }

        // Test 2: "b" — first iteration matches empty, guard fires, + check → None.
        let src2 = "b";
        let mut p2 = Parser::new(src2, false);
        let result2 = p2.apply__parse_rule(0);
        match result2 {
            Some(r) => {
                println!("b result: Some(pos={}), expected None", r.pos);
                std::process::exit(1);
            }
            None => {
                println!("b result: None (correct)");
            }
        }

        println!("PASS");
    }
""")

_RUST_CARGO_TOML_TEMPLATE = """\
[workspace]

[package]
name = "nullable-loop-test"
version = "0.1.0"
edition = "2021"

[[bin]]
name = "nullable-loop-test"
path = "src/main.rs"

[dependencies]
fltk-cst-core = {{ path = "{fltk_cst_core_path}", default-features = false }}
fltk-parser-core = {{ path = "{fltk_parser_core_path}" }}
"""


@pytest.fixture(scope="module")
def _repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).parent.parent


def test_rust_backend_guard(tmp_path: pathlib.Path, _repo_root: pathlib.Path):
    """§5.1 Rust backend: loop terminates on empty-match iteration.

    The validator is monkeypatched to a no-op so the loop guard is tested in isolation;
    the compiled binary is expected to print PASS.

    Skipped if `cargo` is not on PATH (toolchain is a documented repo requirement;
    cargo absence signals environment misconfiguration, not a test failure).
    """
    if not shutil.which("cargo"):
        pytest.skip("cargo not on PATH — Rust toolchain required (see CLAUDE.md)")

    # Generate parser.rs and cst.rs for the trigger grammar with validator bypassed.
    trigger_grammar = _make_trigger_grammar()

    # Bypass validation: we monkeypatch at Python level before passing to generator.
    # RustParserGenerator calls classify_trivia_rules which calls validate_no_repeated_nil_items.
    # To test the loop guard layer in isolation, we must prevent validator rejection.
    orig_validate = gsm.validate_no_repeated_nil_items
    try:
        gsm.validate_no_repeated_nil_items = lambda _: None  # type: ignore[method-assign]

        gen = RustParserGenerator(trigger_grammar)
        parser_rs = gen.generate()

        cst_gen = RustCstGenerator(trigger_grammar)
        cst_rs = cst_gen.generate()
    finally:
        gsm.validate_no_repeated_nil_items = orig_validate  # type: ignore[method-assign]

    # Write the temporary Rust binary crate.
    crate_dir = tmp_path / "nullable-loop-test"
    src_dir = crate_dir / "src"
    src_dir.mkdir(parents=True)

    (src_dir / "parser.rs").write_text(parser_rs)
    (src_dir / "cst.rs").write_text(cst_rs)
    (src_dir / "main.rs").write_text(_RUST_MAIN_RS)

    fltk_cst_core_path = (_repo_root / "crates" / "fltk-cst-core").resolve()
    fltk_parser_core_path = (_repo_root / "crates" / "fltk-parser-core").resolve()
    cargo_toml = _RUST_CARGO_TOML_TEMPLATE.format(
        fltk_cst_core_path=fltk_cst_core_path,
        fltk_parser_core_path=fltk_parser_core_path,
    )
    (crate_dir / "Cargo.toml").write_text(cargo_toml)

    # Build (long timeout — debug cargo build can be slow).
    # Reuse a persistent CARGO_TARGET_DIR under the repo root so dependency crates
    # (fltk-parser-core, fltk-cst-core, regex-automata) are only compiled once
    # across test sessions rather than cold-rebuilt in every tmp_path.
    # The repo's existing .gitignore covers target/ already.
    cargo_target_dir = _repo_root / "target" / "nullable-loop-guard-test"
    cargo_bin = shutil.which("cargo") or "cargo"
    build_result = subprocess.run(  # noqa: S603
        [cargo_bin, "build"],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
        cwd=crate_dir,
        env={**__import__("os").environ, "CARGO_TARGET_DIR": str(cargo_target_dir)},
    )
    assert build_result.returncode == 0, (
        f"cargo build failed:\nstdout: {build_result.stdout}\nstderr: {build_result.stderr}"
    )

    binary = cargo_target_dir / "debug" / "nullable-loop-test"

    # Run binary with short timeout — a hang indicates an infinite loop (missing loop guard).
    try:
        run_result = subprocess.run(  # noqa: S603
            [str(binary)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        pytest.fail("Rust backend hung on nullable repetition (infinite loop — loop guard missing)")

    assert run_result.returncode == 0, (
        f"Rust backend guard test failed:\nstdout: {run_result.stdout}\nstderr: {run_result.stderr}"
    )
    assert "PASS" in run_result.stdout, (
        f"Expected PASS in output:\nstdout: {run_result.stdout}\nstderr: {run_result.stderr}"
    )


def test_cross_backend_parity():
    """§5.1 Cross-backend parity: assert expected outcomes shared by both backends.

    Documents the concrete values that test_python_backend_guard (subprocess) and
    test_rust_backend_guard (cargo binary) must both produce.  Does not re-run Python
    generation; it consults _RUST_MAIN_RS to verify Rust assertions match.

    The actual runtime demonstration is in test_python_backend_guard (subprocess) and
    test_rust_backend_guard (cargo); this test is a lightweight cross-reference check.
    """
    # Both backends must: return pos=2 for "aab" and None for "b".
    # Verify that _RUST_MAIN_RS encodes those same expectations.
    assert "assert_eq!(r.pos, 2" in _RUST_MAIN_RS, (
        "Rust main.rs must assert pos=2 for 'aab' — cross-backend parity requires identical expectations"
    )
    assert "std::process::exit(1)" in _RUST_MAIN_RS, "Rust main.rs must exit(1) on unexpected None for 'aab'"
    # "b" should produce None in both backends — verified in both individual tests.
    assert '"b result: None (correct)"' in _RUST_MAIN_RS, (
        "Rust main.rs must accept None for 'b' as correct — cross-backend parity"
    )


# ---------------------------------------------------------------------------
# §5.2 Validator gap tests
# ---------------------------------------------------------------------------


class TestValidatorGap:
    """§5.2 Item.can_be_nil is term-aware."""

    def test_item_required_nullable_regex_can_be_nil(self):
        """REQUIRED item + nullable Regex(r"a*") → can_be_nil True."""
        grammar = gsm.Grammar(rules=[], identifiers={})
        item = gsm.Item(
            label=None,
            disposition=gsm.Disposition.INCLUDE,
            term=gsm.Regex(r"a*"),
            quantifier=gsm.REQUIRED,
        )
        assert item.can_be_nil(grammar) is True

    def test_item_required_empty_literal_can_be_nil(self):
        """REQUIRED item + Literal("") → can_be_nil True."""
        grammar = gsm.Grammar(rules=[], identifiers={})
        item = gsm.Item(
            label=None,
            disposition=gsm.Disposition.INCLUDE,
            term=gsm.Literal(""),
            quantifier=gsm.REQUIRED,
        )
        assert item.can_be_nil(grammar) is True

    def test_item_required_nil_rule_ref_can_be_nil(self):
        """REQUIRED item referencing a nil-able rule → can_be_nil True."""
        nullable_rule = gsm.Rule(
            name="nullable",
            alternatives=[
                gsm.Items(
                    items=[
                        gsm.Item(
                            label="v",
                            disposition=gsm.Disposition.INCLUDE,
                            term=gsm.Regex(r"a*"),
                            quantifier=gsm.REQUIRED,
                        )
                    ],
                    sep_after=[gsm.Separator.NO_WS],
                )
            ],
        )
        grammar = gsm.Grammar(rules=[nullable_rule], identifiers={"nullable": nullable_rule})
        item = gsm.Item(
            label=None,
            disposition=gsm.Disposition.INCLUDE,
            term=gsm.Identifier("nullable"),
            quantifier=gsm.REQUIRED,
        )
        # nullable_rule.can_be_nil(grammar) is True (its inner REQUIRED item has Regex(r"a*")
        # which is nullable).
        assert item.can_be_nil(grammar) is True

    def test_item_required_non_nullable_term_not_nil(self):
        """REQUIRED item + non-nullable regex → can_be_nil False."""
        grammar = gsm.Grammar(rules=[], identifiers={})
        item = gsm.Item(
            label=None,
            disposition=gsm.Disposition.INCLUDE,
            term=gsm.Regex(r"a+"),
            quantifier=gsm.REQUIRED,
        )
        assert item.can_be_nil(grammar) is False

    def test_item_optional_quantifier_always_nil(self):
        """Optional quantifier → can_be_nil True regardless of term (unchanged)."""
        grammar = gsm.Grammar(rules=[], identifiers={})
        item = gsm.Item(
            label=None,
            disposition=gsm.Disposition.INCLUDE,
            term=gsm.Regex(r"a+"),  # non-nullable term
            quantifier=gsm.NOT_REQUIRED,
        )
        assert item.can_be_nil(grammar) is True

    def test_validate_no_repeated_nil_rejects_trigger_grammar(self):
        """validate_no_repeated_nil_items raises ValueError for the trigger grammar."""
        trigger = _make_trigger_grammar()
        with pytest.raises(ValueError, match="Repeated potentially-nil"):
            gsm.validate_no_repeated_nil_items(trigger)

    def test_validate_no_repeated_nil_rejects_empty_literal_variant(self):
        """validate_no_repeated_nil_items rejects repeated REQUIRED Literal("") variant."""
        trigger = _make_trigger_grammar_empty_literal()
        with pytest.raises(ValueError, match="Repeated potentially-nil"):
            gsm.validate_no_repeated_nil_items(trigger)

    def test_validate_no_repeated_nil_rejects_nil_rule_ref_variant(self):
        """validate_no_repeated_nil_items rejects repeated REQUIRED nil-able Identifier variant."""
        trigger = _make_trigger_grammar_nil_rule_ref()
        with pytest.raises(ValueError, match="Repeated potentially-nil"):
            gsm.validate_no_repeated_nil_items(trigger)


# The test below updates the assertions in test_nil_validation.py's
# test_item_nil_detection_with_quantifiers that encode the old (buggy) behavior.
# These must be checked here since we cannot modify the existing test file in this increment.
class TestItemNilDetectionUpdated:
    """Correct assertions for Item.can_be_nil (design §4 last bullet)."""

    def test_required_empty_literal_is_nil(self):
        """REQUIRED + empty literal IS nil (contradicts old test assertion)."""
        grammar = gsm.Grammar(rules=[], identifiers={})
        required_item = gsm.Item(
            label=None,
            disposition=gsm.Disposition.INCLUDE,
            term=gsm.Literal(""),
            quantifier=gsm.REQUIRED,
        )
        # Old test said False; correct answer is True (term is nil).
        assert required_item.can_be_nil(grammar) is True

    def test_one_or_more_empty_literal_is_nil(self):
        """ONE_OR_MORE + empty literal: Item.can_be_nil() returns True.

        Formula: ``is_optional() OR term_can_be_nil(term, grammar)``
        = ``False OR True`` = ``True``.

        The item has quantifier ONE_OR_MORE (min=1, so is_optional()=False), but its
        term ``Literal("")`` is nullable.  Because every iteration matches zero bytes,
        the ONE_OR_MORE item itself can complete without consuming any input — it is nil.
        The guard in both backends discards such zero-progress iterations, so the
        item never actually accumulates children, but at the item-nil level the
        term-aware check correctly returns True.
        """
        grammar = gsm.Grammar(rules=[], identifiers={})
        one_or_more_item = gsm.Item(
            label=None,
            disposition=gsm.Disposition.INCLUDE,
            term=gsm.Literal(""),
            quantifier=gsm.ONE_OR_MORE,
        )
        assert one_or_more_item.can_be_nil(grammar) is True


# ---------------------------------------------------------------------------
# §5.3 Generator-level rejection
# ---------------------------------------------------------------------------


class TestGeneratorRejection:
    """§5.3 Both generator entry points reject the trigger grammar."""

    def test_python_generate_parser_rejects_trigger_grammar(self):
        """generate_parser raises ValueError for the trigger grammar (validator wired in)."""
        trigger = _make_trigger_grammar()
        # classify_trivia_rules → validate_no_repeated_nil_items → ValueError.
        with pytest.raises(ValueError, match="Repeated potentially-nil"):
            generate_parser(trigger)

    def test_rust_parser_generator_rejects_trigger_grammar(self):
        """RustParserGenerator raises ValueError at construction for the trigger grammar."""
        trigger = _make_trigger_grammar()
        # __init__ → classify_trivia_rules → validate_no_repeated_nil_items → ValueError.
        with pytest.raises(ValueError, match="Repeated potentially-nil"):
            RustParserGenerator(trigger)


# ---------------------------------------------------------------------------
# §5.4 Source-text guard placement (cheap; always runs)
# ---------------------------------------------------------------------------


def _make_simple_plus_grammar() -> gsm.Grammar:
    """Minimal grammar with a + quantifier: items := item:r[a-z]+ .+

    This grammar is VALID (non-nullable term), so generators accept it.
    The generated loop must contain the guard line.
    """
    rule = gsm.Rule(
        name="items",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="item",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[a-z]+"),
                        quantifier=gsm.ONE_OR_MORE,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    return gsm.Grammar(rules=[rule], identifiers={"items": rule})


def _make_simple_star_grammar() -> gsm.Grammar:
    """Minimal grammar with a * quantifier: items := item:r[a-z]* .*"""
    rule = gsm.Rule(
        name="items",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="item",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[a-z]+"),
                        quantifier=gsm.ZERO_OR_MORE,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    return gsm.Grammar(rules=[rule], identifiers={"items": rule})


class TestRustGuardPlacement:
    """§5.4 Rust: generated parser.rs contains the guard immediately after loop opener."""

    def test_plus_loop_has_guard_before_pos_update(self):
        """parser.rs for a + grammar contains 'if one_result.pos <= pos { break; }'
        immediately after '} {' and before 'pos = one_result.pos'."""
        gen = RustParserGenerator(_make_simple_plus_grammar())
        src = gen.generate()

        lines = src.splitlines()
        # Find the loop opener line '        } {'
        opener_idx = None
        for i, line in enumerate(lines):
            if line.strip() == "} {":
                opener_idx = i
                break
        assert opener_idx is not None, f"Loop opener '}} {{' not found in generated parser.rs:\n{src}"

        # The very next non-empty line after the opener must be the guard.
        guard_line = lines[opener_idx + 1].strip()
        assert guard_line == "if one_result.pos <= pos { break; }", (
            f"Expected guard immediately after loop opener, got: {guard_line!r}\n"
            f"Context:\n" + "\n".join(lines[max(0, opener_idx - 2) : opener_idx + 5])
        )

        # The guard must appear before 'pos = one_result.pos'.
        guard_pos_in_src = src.index("if one_result.pos <= pos { break; }")
        pos_update_pos_in_src = src.index("pos = one_result.pos;")
        assert guard_pos_in_src < pos_update_pos_in_src, (
            "Guard must appear before 'pos = one_result.pos;' in generated source"
        )

    def test_star_loop_has_guard(self):
        """* grammar also gets the guard (with <= for robustness against position regression)."""
        gen = RustParserGenerator(_make_simple_star_grammar())
        src = gen.generate()
        assert "if one_result.pos <= pos { break; }" in src, (
            f"Guard missing in generated parser.rs for * grammar:\n{src}"
        )

    def test_todo_nullable_loop_comment_removed(self):
        """The TODO(nullable-loop) comment block is removed from generated output."""
        gen = RustParserGenerator(_make_simple_plus_grammar())
        src = gen.generate()
        assert "TODO(nullable-loop)" not in src, "TODO(nullable-loop) comment must not appear in generated output"


class TestPythonGuardPlacement:
    """§5.4 Python: compiled parser contains the guard before pos assignment."""

    def _compile_parser_source(self, grammar: gsm.Grammar) -> str:
        """Compile grammar to Python source via IIR → ast.unparse."""
        context = create_default_context()
        grammar_with_trivia = gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(grammar, context))
        cstgen = gsm2tree.CstGenerator(grammar=grammar_with_trivia, py_module=pyreg.Builtins, context=context)
        pgen = gsm2parser.ParserGenerator(grammar=grammar_with_trivia, cstgen=cstgen, context=context)
        class_ast = compiler.compile_class(pgen.parser_class, context)
        return ast.unparse(ast.fix_missing_locations(class_ast))

    def test_plus_loop_has_guard(self):
        """Python parser source for + grammar contains a '<=' guard (compiled as
        'if not one_result.pos > pos: break') before 'pos = one_result.pos'."""
        src = self._compile_parser_source(_make_simple_plus_grammar())

        # The guard is compiled from LogicalNegation(GreaterThan(...)).
        # ast.unparse produces: if not one_result.pos > pos:\n    break
        assert "not one_result.pos > pos" in src, (
            f"Guard condition 'not one_result.pos > pos' not found in Python parser source:\n{src}"
        )
        # Assert 'break' appears in the guard body.
        guard_idx = src.index("not one_result.pos > pos")
        # The break must appear after the condition and before the pos update.
        pos_update_pos = src.index("pos = one_result.pos")
        guard_region = src[guard_idx:pos_update_pos]
        assert "break" in guard_region, f"'break' not found between guard condition and pos update:\n{guard_region!r}"
        # Guard must appear before pos update.
        assert guard_idx < pos_update_pos, "Guard must appear before 'pos = one_result.pos' in Python parser source"

    def test_star_loop_has_guard(self):
        """* grammar also gets the Python guard, with break before pos update."""
        src = self._compile_parser_source(_make_simple_star_grammar())
        assert "not one_result.pos > pos" in src, f"Guard missing in Python parser source for * grammar:\n{src}"
        # Guard must appear before pos update (placement is load-bearing).
        guard_idx = src.index("not one_result.pos > pos")
        pos_update_pos = src.index("pos = one_result.pos")
        assert guard_idx < pos_update_pos, (
            "Guard must appear before 'pos = one_result.pos' in Python parser source for * grammar"
        )
