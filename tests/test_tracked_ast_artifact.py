"""The committed ``tests/rust_parser_fixture/src/ast.rs`` is what the generator emits today.

That artifact is tracked, compiled and executed by the fixture crate's own tests, so an emitter
change that is not followed by a regeneration leaves a stale module that still compiles and still
passes every fixture case — the suite would go green over generator output that no longer exists,
and the divergence would first surface in a downstream consumer who regenerates.

This test reruns the ``gencode`` recipe's ``gen-rust-ast`` invocation into a scratch path and
compares bytes, so the drift fails here instead.
"""

from __future__ import annotations

import pathlib

import pytest
from typer.testing import CliRunner

from fltk.fegen.genparser import app

_REPO_ROOT = pathlib.Path(__file__).parent.parent

# The `gencode` recipe's arguments, spelled as the Makefile spells them: the grammar path is
# echoed into the generated module's header, so it is part of the compared bytes.
_GRAMMAR = "fltk/fegen/test_data/rust_parser_fixture.fltkg"
_AST_CONFIG = "tests/rust_parser_fixture/rust_parser_fixture.fltkast"
_COMMITTED = "tests/rust_parser_fixture/src/ast.rs"
_GOAL = "nest_sum"
_PARSER_MOD_PATH = "super::parser"
_UNPARSER_MOD_PATH = "super::unparser"


def test_the_committed_fixture_ast_module_is_what_the_generator_emits(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale tracked artifact is a drift bug, not a passing suite."""
    monkeypatch.chdir(_REPO_ROOT)
    output = tmp_path / "ast.rs"
    result = CliRunner().invoke(
        app,
        [
            "gen-rust-ast",
            _GRAMMAR,
            str(output),
            "--ast-config",
            _AST_CONFIG,
            "--parser-mod-path",
            _PARSER_MOD_PATH,
            "--unparser-mod-path",
            _UNPARSER_MOD_PATH,
            "--goal",
            _GOAL,
        ],
    )
    assert result.exit_code == 0, f"gen-rust-ast failed:\n{result.output}\n{result.exception}"

    committed = (_REPO_ROOT / _COMMITTED).read_text()
    assert output.read_text() == committed, f"{_COMMITTED} is out of date with the generator; run `make gencode`"
