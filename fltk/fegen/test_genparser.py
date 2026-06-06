"""Tests for the gen-rust-cst CLI subcommand: source emission, sentinel decoupling, and no-double-trivia contract."""

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
    assert src.startswith("use pyo3::")


# ---------------------------------------------------------------------------
# test_gen_rust_cst_sentinel_decoupled
# ---------------------------------------------------------------------------


def test_gen_rust_cst_sentinel_decoupled(simple_grammar_file: pathlib.Path, tmp_path: pathlib.Path) -> None:
    """Emitted preamble declares a module-local GILOnceCell sentinel cache and
    fetches fltk._native.UnknownSpan at runtime (not from crate::).

    Design §Test Plan Tier 1 / §Resolved design questions artifact-build-mechanism.
    """
    output_rs = tmp_path / "sentinel_test_cst.rs"
    runner = CliRunner()
    result = runner.invoke(app, ["gen-rust-cst", str(simple_grammar_file), str(output_rs)])

    assert result.exit_code == 0, f"gen-rust-cst failed:\n{result.output}"

    src = output_rs.read_text()

    # Module-local sentinel cache declaration must be present.
    assert "static UNKNOWN_SPAN_CACHE: GILOnceCell<PyObject> = GILOnceCell::new();" in src

    # The #[new] body must fetch UnknownSpan from fltk._native at runtime.
    assert 'py.import("fltk._native")?.getattr("UnknownSpan")?.unbind()' in src

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
