"""Tests for gen-rust-cst, gen-rust-parser, and gen-rust-lib CLI subcommands."""

from __future__ import annotations

import pathlib

import pytest
from typer.testing import CliRunner

from fltk.fegen import gsm
from fltk.fegen.genparser import _parse_grammar_raw, app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FEGEN_FLTKG = pathlib.Path(__file__).parent / "fegen.fltkg"

# A small grammar that does NOT define a _trivia rule, for double-trivia testing.
_SIMPLE_GRAMMAR_SRC = """\
word := value:/[a-z]+/ ;
"""


@pytest.fixture(scope="module")
def simple_grammar_file(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    """Write a minimal .fltkg file (no _trivia rule) to a temp directory."""
    d = tmp_path_factory.mktemp("genparser_test")
    p = d / "simple.fltkg"
    p.write_text(_SIMPLE_GRAMMAR_SRC)
    return p


# ---------------------------------------------------------------------------
# test_gen_rust_cst_command_emits_source  (AC6 Python half)
# ---------------------------------------------------------------------------


def test_gen_rust_cst_command_emits_source(simple_grammar_file: pathlib.Path, tmp_path: pathlib.Path) -> None:
    """Run gen-rust-cst on a small grammar and assert the output is correct Rust source.

    Design §Test Plan Tier 1: output contains `pub fn register_classes`, the class
    name ("Word"), and no `use crate::UNKNOWN_SPAN;`.
    """
    output_rs = tmp_path / "simple_cst.rs"
    runner = CliRunner()
    result = runner.invoke(app, ["gen-rust-cst", str(simple_grammar_file), str(output_rs)])

    assert result.exit_code == 0, f"gen-rust-cst failed:\n{result.output}\n{result.exception}"
    assert output_rs.exists(), "Expected .rs output file was not created"

    src = output_rs.read_text()

    # Must contain the register_classes entry point.
    assert "pub fn register_classes" in src

    # Must contain the node class name from the grammar rule "word".
    assert "Word" in src

    # Must NOT contain the crate::UNKNOWN_SPAN linkage (standalone artifact requirement).
    assert "use crate::UNKNOWN_SPAN;" not in src

    # Sanity: it's valid-ish Rust (starts with use declarations).
    # Phase 2: CstError is imported first in the preamble; Span follows.
    assert src.startswith("use fltk_cst_core::CstError;\n")
    assert "use fltk_cst_core::Span;\n" in src


# ---------------------------------------------------------------------------
# test_gen_rust_cst_sentinel_decoupled
# ---------------------------------------------------------------------------


def test_gen_rust_cst_sentinel_decoupled(simple_grammar_file: pathlib.Path, tmp_path: pathlib.Path) -> None:
    """Emitted preamble uses native Span::unknown() sentinel — no PyOnceLock cache, no
    fltk._native.UnknownSpan runtime import, no crate:: linkage.

    Design §2.2 (native span sentinel) / §Test Plan item 2.
    """
    output_rs = tmp_path / "sentinel_test_cst.rs"
    runner = CliRunner()
    result = runner.invoke(app, ["gen-rust-cst", str(simple_grammar_file), str(output_rs)])

    assert result.exit_code == 0, f"gen-rust-cst failed:\n{result.output}"

    src = output_rs.read_text()

    # Native sentinel: Span::unknown() — no Python import for span default.
    assert "Span::unknown" in src
    assert "UNKNOWN_SPAN_CACHE" not in src
    assert 'py.import("fltk._native")?.getattr("UnknownSpan")' not in src

    # The old crate-internal linkage patterns must be absent.
    assert "use crate::UNKNOWN_SPAN;" not in src
    assert "UNKNOWN_SPAN.get(py)" not in src


# ---------------------------------------------------------------------------
# test_gen_rust_cst_no_double_trivia
# ---------------------------------------------------------------------------


def test_gen_rust_cst_no_double_trivia(simple_grammar_file: pathlib.Path) -> None:
    """_parse_grammar_raw feeds RustCstGenerator a grammar with no pre-existing _trivia rule.

    Design §Test Plan Tier 1 and §genparser.py emit subcommand (double-trivia caveat):
    _parse_grammar_raw must NOT call add_trivia_rule_to_grammar. The grammar it
    returns must therefore lack _trivia when the .fltkg source does not define one.
    RustCstGenerator applies trivia processing internally; receiving a pre-processed
    grammar would double-apply (idempotent but the test guards the contract).
    """
    grammar = _parse_grammar_raw(simple_grammar_file)

    # _parse_grammar_raw must not have added the _trivia rule.
    assert gsm.TRIVIA_RULE_NAME not in grammar.identifiers, (
        "_parse_grammar_raw must NOT add the _trivia rule; that is RustCstGenerator's job"
    )

    # Sanity: the grammar parsed the expected rule.
    assert "word" in grammar.identifiers


# ---------------------------------------------------------------------------
# test_gsm2parser_extend_children_emission  (§2.3/§2.5 parser-generator change)
# ---------------------------------------------------------------------------

# Grammar with a repeating term that becomes inline_to_parent.
# The repeated labeled `item:word+` produces a sub-rule result merged via extend_children.
_INLINE_GRAMMAR_SRC = """\
items := item:word+ ;
word := value:/[a-z]+/ ;
"""


def test_gsm2parser_extend_children_call_site(tmp_path: pathlib.Path) -> None:
    """gsm2parser emits extend_children calls, not .children.extend(), for inline-to-parent sites.

    Design §2.3 parser-generator note / §2.5 partial: generated parsers must route
    child mutations through the node's own extend_children method so the native Vec
    is updated (not a throwaway rebuilt PyList from the getter).
    """
    grammar_file = tmp_path / "inline.fltkg"
    grammar_file.write_text(_INLINE_GRAMMAR_SRC)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["generate", str(grammar_file), "inline", "inline_cst", "--output-dir", str(tmp_path), "--no-trivia-only"],
    )

    assert result.exit_code == 0, f"generate failed:\n{result.output}\n{result.exception}"
    parser_py = tmp_path / "inline_parser.py"
    assert parser_py.exists(), "Expected inline_parser.py was not created"
    src = parser_py.read_text()

    # The generated parser must use extend_children, not getter-mutation.
    assert "extend_children" in src, (
        "Parser generator must emit extend_children calls for inline-to-parent child extension"
    )
    # Must NOT have the old getter-mutation pattern (which mutated a throwaway PyList).
    assert ".children.extend(" not in src, (
        "Parser generator must not emit .children.extend() (getter-mutation is a no-op on Rust backend)"
    )


# ---------------------------------------------------------------------------
# gen-rust-cst --protocol-module / --pyi-output CLI tests
# ---------------------------------------------------------------------------


def test_gen_rust_cst_no_protocol_module_no_pyi(simple_grammar_file: pathlib.Path, tmp_path: pathlib.Path) -> None:
    """Without --protocol-module no .pyi is emitted (backward compatible)."""
    output_rs = tmp_path / "simple_cst.rs"
    runner = CliRunner()
    result = runner.invoke(app, ["gen-rust-cst", str(simple_grammar_file), str(output_rs)])

    assert result.exit_code == 0, f"gen-rust-cst failed:\n{result.output}"
    # No .pyi by default
    pyi = output_rs.with_suffix(".pyi")
    assert not pyi.exists(), "No .pyi should be emitted without --protocol-module"


def test_gen_rust_cst_protocol_module_emits_pyi(simple_grammar_file: pathlib.Path, tmp_path: pathlib.Path) -> None:
    """With --protocol-module the .pyi is written next to the .rs.

    Note: this test uses a simple single-rule grammar (word := /[a-z]+/) with
    fltk_cst_protocol as the protocol module — a mismatched pair (fltk_cst_protocol
    is the fegen grammar's protocol). The test verifies CLI file-emission plumbing
    only, not type-level correctness. The pyright conformance tests in
    TestGeneratePyiConformance use the matched fegen grammar + fltk_cst_protocol pair.
    """
    import ast  # noqa: PLC0415

    output_rs = tmp_path / "simple_cst.rs"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "gen-rust-cst",
            str(simple_grammar_file),
            str(output_rs),
            "--protocol-module",
            "fltk.fegen.fltk_cst_protocol",
        ],
    )

    assert result.exit_code == 0, f"gen-rust-cst failed:\n{result.output}"
    assert output_rs.exists(), ".rs file must still be written"
    pyi = tmp_path / "simple_cst.pyi"
    assert pyi.exists(), ".pyi should be emitted when --protocol-module is given"
    pyi_text = pyi.read_text()
    assert "import fltk.fegen.fltk_cst_protocol as _proto" in pyi_text
    assert "class Word:" in pyi_text
    # Verify the emitted stub is at least syntactically valid Python
    ast.parse(pyi_text)  # raises SyntaxError if the stub text is malformed


def test_gen_rust_cst_pyi_output_override(simple_grammar_file: pathlib.Path, tmp_path: pathlib.Path) -> None:
    """--pyi-output overrides the default .pyi path."""
    output_rs = tmp_path / "cst_fegen.rs"
    pyi_override = tmp_path / "fegen_cst.pyi"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "gen-rust-cst",
            str(simple_grammar_file),
            str(output_rs),
            "--protocol-module",
            "fltk.fegen.fltk_cst_protocol",
            "--pyi-output",
            str(pyi_override),
        ],
    )

    assert result.exit_code == 0, f"gen-rust-cst failed:\n{result.output}"
    assert output_rs.exists(), ".rs file must still be written"
    # Default path (cst_fegen.pyi) must NOT exist; custom path must exist.
    assert not (tmp_path / "cst_fegen.pyi").exists(), "Default .pyi path must not exist when --pyi-output given"
    assert pyi_override.exists(), "--pyi-output path must be written"
    assert "class Word:" in pyi_override.read_text()


def test_gen_rust_cst_rs_unchanged_with_protocol_module(
    simple_grammar_file: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    """Adding --protocol-module does not change the .rs output (additive, non-goal per design)."""
    output_rs_no_pyi = tmp_path / "no_pyi" / "cst.rs"
    output_rs_with_pyi = tmp_path / "with_pyi" / "cst.rs"
    output_rs_no_pyi.parent.mkdir()
    output_rs_with_pyi.parent.mkdir()

    runner = CliRunner()
    result1 = runner.invoke(app, ["gen-rust-cst", str(simple_grammar_file), str(output_rs_no_pyi)])
    assert result1.exit_code == 0, f"gen-rust-cst (no --protocol-module) failed:\n{result1.output}"
    result2 = runner.invoke(
        app,
        [
            "gen-rust-cst",
            str(simple_grammar_file),
            str(output_rs_with_pyi),
            "--protocol-module",
            "fltk.fegen.fltk_cst_protocol",
        ],
    )
    assert result2.exit_code == 0, f"gen-rust-cst (with --protocol-module) failed:\n{result2.output}"

    assert output_rs_no_pyi.read_text() == output_rs_with_pyi.read_text(), (
        "--protocol-module must not change .rs output"
    )


# ---------------------------------------------------------------------------
# gen-rust-parser CLI tests  (design §4 item 2)
# ---------------------------------------------------------------------------


def test_gen_rust_parser_happy_path(simple_grammar_file: pathlib.Path, tmp_path: pathlib.Path) -> None:
    """gen-rust-parser happy path: writes the output file, exits 0, and emits valid content."""
    output_rs = tmp_path / "parser.rs"
    runner = CliRunner()
    result = runner.invoke(app, ["gen-rust-parser", str(simple_grammar_file), str(output_rs)])

    assert result.exit_code == 0, f"gen-rust-parser failed:\n{result.output}\n{result.exception}"
    assert output_rs.exists(), "Expected .rs output file was not created"

    src = output_rs.read_text()
    assert "pub fn apply__parse_word(" in src
    assert "Parser" in src


def test_gen_rust_parser_missing_grammar_file(tmp_path: pathlib.Path) -> None:
    """gen-rust-parser with a non-existent grammar file exits 1."""
    missing = tmp_path / "no_such.fltkg"
    output_rs = tmp_path / "parser.rs"
    runner = CliRunner()
    result = runner.invoke(app, ["gen-rust-parser", str(missing), str(output_rs)])

    assert result.exit_code != 0, "Expected non-zero exit for missing grammar file"
    assert not output_rs.exists(), "No output file should be created on error"


def test_gen_rust_parser_generation_error_no_partial_file(tmp_path: pathlib.Path) -> None:
    """gen-rust-parser exits 1 on generation error and leaves no partial output file."""
    # A grammar that triggers NotImplementedError: use INLINE disposition on an identifier.
    bad_grammar = tmp_path / "bad.fltkg"
    bad_grammar.write_text("parent := !child:child ;\nchild := value:/[a-z]+/ ;\n")
    output_rs = tmp_path / "parser.rs"
    runner = CliRunner()
    result = runner.invoke(app, ["gen-rust-parser", str(bad_grammar), str(output_rs)])

    assert result.exit_code != 0, "Expected non-zero exit for unsupported grammar feature"
    assert not output_rs.exists(), "No partial output file should be created on generation error"


def test_gen_rust_parser_invalid_cst_mod_path(simple_grammar_file: pathlib.Path, tmp_path: pathlib.Path) -> None:
    """gen-rust-parser rejects invalid --cst-mod-path with exit 1 and no output file."""
    output_rs = tmp_path / "parser.rs"
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["gen-rust-parser", str(simple_grammar_file), str(output_rs), "--cst-mod-path", "123bad"],
    )

    assert result.exit_code != 0, "Expected non-zero exit for invalid --cst-mod-path"
    assert not output_rs.exists(), "No output file should be created when --cst-mod-path is invalid"


def test_gen_rust_parser_custom_cst_mod_path(simple_grammar_file: pathlib.Path, tmp_path: pathlib.Path) -> None:
    """gen-rust-parser --cst-mod-path propagates to the generated use statement."""
    output_rs = tmp_path / "parser.rs"
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["gen-rust-parser", str(simple_grammar_file), str(output_rs), "--cst-mod-path", "my::cst"],
    )

    assert result.exit_code == 0, f"gen-rust-parser failed:\n{result.output}"
    src = output_rs.read_text()
    assert "use my::cst;" in src


# ---------------------------------------------------------------------------
# gen-rust-lib CLI tests  (design §2.3 / §4)
# ---------------------------------------------------------------------------


def test_gen_rust_lib_standard_output(tmp_path: pathlib.Path) -> None:
    """gen-rust-lib writes a standard lib.rs with cst and parser submodules."""
    output_rs = tmp_path / "lib.rs"
    runner = CliRunner()
    result = runner.invoke(app, ["gen-rust-lib", str(output_rs), "--module-name", "clockwork_native"])

    assert result.exit_code == 0, f"gen-rust-lib failed:\n{result.output}\n{result.exception}"
    assert output_rs.exists(), "Expected lib.rs output file was not created"

    src = output_rs.read_text()

    # Required imports and declarations
    assert "use fltk_cst_core::register_submodule;" in src
    assert "use pyo3::prelude::*;" in src
    assert "mod cst;" in src
    assert "mod parser;" in src
    assert "fn clockwork_native(" in src
    assert 'register_submodule(m, "cst", cst::register_classes)' in src
    assert 'register_submodule(m, "parser", parser::register_classes)' in src
    assert "Ok(())" in src

    # Must NOT contain span/native-only items
    assert "recursion_limit" not in src
    assert "Span" not in src
    assert "SourceText" not in src
    assert "UnknownSpan" not in src
    assert "UNKNOWN_SPAN" not in src


def test_gen_rust_lib_no_parser(tmp_path: pathlib.Path) -> None:
    """gen-rust-lib --no-parser omits mod parser; and its registration."""
    output_rs = tmp_path / "lib.rs"
    runner = CliRunner()
    result = runner.invoke(app, ["gen-rust-lib", str(output_rs), "--module-name", "my_module", "--no-parser"])

    assert result.exit_code == 0, f"gen-rust-lib --no-parser failed:\n{result.output}"
    src = output_rs.read_text()

    # CST must still be present
    assert "mod cst;" in src
    assert 'register_submodule(m, "cst", cst::register_classes)' in src

    # Parser must be absent
    assert "mod parser;" not in src
    assert '"parser"' not in src


def test_gen_rust_lib_invalid_module_name_empty(tmp_path: pathlib.Path) -> None:
    """gen-rust-lib rejects empty --module-name with exit 1."""
    output_rs = tmp_path / "lib.rs"
    runner = CliRunner()
    result = runner.invoke(app, ["gen-rust-lib", str(output_rs), "--module-name", ""])

    assert result.exit_code != 0, "Expected non-zero exit for empty --module-name"
    assert not output_rs.exists(), "No output file should be created on error"
    assert "''" in result.output, "Error message should name the empty module_name value"


def test_gen_rust_lib_invalid_module_name_starts_with_digit(tmp_path: pathlib.Path) -> None:
    """gen-rust-lib rejects module names starting with a digit."""
    output_rs = tmp_path / "lib.rs"
    runner = CliRunner()
    result = runner.invoke(app, ["gen-rust-lib", str(output_rs), "--module-name", "1bad"])

    assert result.exit_code != 0, "Expected non-zero exit for '1bad' module name"
    assert not output_rs.exists(), "No output file should be created on error"
    assert "1bad" in result.output


def test_gen_rust_lib_invalid_module_name_has_space(tmp_path: pathlib.Path) -> None:
    """gen-rust-lib rejects module names with spaces."""
    output_rs = tmp_path / "lib.rs"
    runner = CliRunner()
    result = runner.invoke(app, ["gen-rust-lib", str(output_rs), "--module-name", "has space"])

    assert result.exit_code != 0, "Expected non-zero exit for 'has space' module name"
    assert not output_rs.exists(), "No output file should be created on error"
    assert "has space" in result.output, "Error message should name the offending module_name value"


def test_gen_rust_lib_invalid_module_name_has_hyphen(tmp_path: pathlib.Path) -> None:
    """gen-rust-lib rejects module names with hyphens."""
    output_rs = tmp_path / "lib.rs"
    runner = CliRunner()
    result = runner.invoke(app, ["gen-rust-lib", str(output_rs), "--module-name", "a-b"])

    assert result.exit_code != 0, "Expected non-zero exit for 'a-b' module name"
    assert not output_rs.exists(), "No output file should be created on error"


def test_gen_rust_lib_missing_module_name(tmp_path: pathlib.Path) -> None:
    """gen-rust-lib exits non-zero when --module-name is omitted entirely."""
    output_rs = tmp_path / "lib.rs"
    runner = CliRunner()
    result = runner.invoke(app, ["gen-rust-lib", str(output_rs)])

    assert result.exit_code != 0, "Expected non-zero exit when --module-name is omitted"


# ---------------------------------------------------------------------------
# gen-rust-lib span-only path (--no-cst --register-span-types --unknown-span-static)
# ---------------------------------------------------------------------------


def test_gen_rust_lib_span_only_output(tmp_path: pathlib.Path) -> None:
    """gen-rust-lib --no-cst --register-span-types --unknown-span-static writes a runtime-only layout."""
    output_rs = tmp_path / "lib.rs"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "gen-rust-lib",
            str(output_rs),
            "--module-name",
            "_native",
            "--no-cst",
            "--register-span-types",
            "--unknown-span-static",
        ],
    )

    assert result.exit_code == 0, f"gen-rust-lib span-only failed:\n{result.output}\n{result.exception}"
    assert output_rs.exists(), "Expected lib.rs output file was not created"

    src = output_rs.read_text()

    # Span/SourceText/UnknownSpan registrations
    assert "mod span;" in src
    assert "use span::{SourceText, Span};" in src
    assert "pyo3::sync::PyOnceLock" in src
    assert "m.add_class::<Span>()" in src
    assert "m.add_class::<SourceText>()" in src
    assert 'm.add("UnknownSpan"' in src

    # UNKNOWN_SPAN static and once-init
    assert "UNKNOWN_SPAN" in src
    assert "UNKNOWN_SPAN already set; module initialized twice" in src

    # No submodule registrations — runtime-only, no grammar CST
    assert "register_submodule" not in src
    assert "poc_cst" not in src
    assert "fegen_cst" not in src

    # Module function name
    assert "fn _native(" in src


def test_gen_rust_lib_no_cst_without_span_flags_fails(tmp_path: pathlib.Path) -> None:
    """gen-rust-lib --no-cst without span flags fails: empty spec is invalid."""
    output_rs = tmp_path / "lib.rs"
    runner = CliRunner()
    result = runner.invoke(app, ["gen-rust-lib", str(output_rs), "--module-name", "_native", "--no-cst"])

    assert result.exit_code != 0, "Expected non-zero exit for --no-cst without span flags"
    assert not output_rs.exists(), "No output file should be created on error"


def test_gen_rust_lib_unknown_span_without_register_span_types_fails(tmp_path: pathlib.Path) -> None:
    """gen-rust-lib --unknown-span-static without --register-span-types fails (requires span types)."""
    output_rs = tmp_path / "lib.rs"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "gen-rust-lib",
            str(output_rs),
            "--module-name",
            "_native",
            "--no-cst",
            "--unknown-span-static",
        ],
    )

    assert result.exit_code != 0, "Expected non-zero exit for --unknown-span-static without --register-span-types"
    assert not output_rs.exists(), "No output file should be created on error"


def test_gen_rust_lib_span_and_submodules_fails(tmp_path: pathlib.Path) -> None:
    """gen-rust-lib --register-span-types without --no-cst is rejected (unsupported combination)."""
    output_rs = tmp_path / "lib.rs"
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["gen-rust-lib", str(output_rs), "--module-name", "my_module", "--register-span-types"],
    )

    assert result.exit_code != 0, "Expected non-zero exit for --register-span-types without --no-cst"
    assert not output_rs.exists(), "No output file should be created on error"
