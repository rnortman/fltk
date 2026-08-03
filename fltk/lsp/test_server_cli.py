"""Startup-validation tests for the ``fltk-lsp`` CLI.

Every misconfiguration -- a missing/invalid grammar, ``.fltklsp``, or ``.fltkfmt``, or an unknown
``--rule`` -- must fail fast at startup with a stderr message and a non-zero exit, before any
protocol I/O. These drive the typer app directly via ``CliRunner`` (which never starts the stdio
loop because construction raises first). The pygls-missing path is checked by simulating the import
failure.
"""

from __future__ import annotations

import builtins
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from fltk.fegen import cst_ergonomics
from fltk.lsp import server_cli

if TYPE_CHECKING:
    from collections.abc import Iterator

_DATA = Path(__file__).parent / "test_data"
_GRAMMAR = str(_DATA / "greet.fltkg")
_LSP = str(_DATA / "greet.fltklsp")
_FMT = str(_DATA / "greet.fltkfmt")

runner = CliRunner()


@pytest.fixture(autouse=True)
def _silence_cst_generation_logging() -> Iterator[None]:
    """Keep CST generation quiet for the duration of every CliRunner invocation here.

    Emitting a record under pytest's live logging suspends and resumes the global capture,
    which swaps out the stdio streams CliRunner installed for the invocation and closes them;
    the runner then fails reading its own captured output.  Building a server for
    ``greet.fltkg`` reports a skipped ergonomic member (the grammar has a ``text`` label), so
    that one logger is raised above the live-logging threshold.  Every other logger stays
    audible, so a real error from the code under test is not swallowed.
    """
    gen_logger = logging.getLogger(cst_ergonomics.__name__)
    previous = gen_logger.level
    gen_logger.setLevel(logging.CRITICAL)
    try:
        yield
    finally:
        gen_logger.setLevel(previous)


def test_missing_grammar_file_exits_1() -> None:
    result = runner.invoke(server_cli.app, ["--grammar", "/nonexistent/does-not-exist.fltkg"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_invalid_grammar_exits_1(tmp_path: Path) -> None:
    bad = tmp_path / "bad.fltkg"
    bad.write_text("this is := not a valid grammar (\n")
    result = runner.invoke(server_cli.app, ["--grammar", str(bad)])
    assert result.exit_code == 1


def test_invalid_lsp_spec_exits_1(tmp_path: Path) -> None:
    bad = tmp_path / "bad.fltklsp"
    bad.write_text("rule nonexistent_rule { scope missing: keyword; }\n")
    result = runner.invoke(server_cli.app, ["--grammar", _GRAMMAR, "--lsp", str(bad)])
    assert result.exit_code == 1


def test_invalid_fmt_spec_exits_1(tmp_path: Path) -> None:
    bad = tmp_path / "bad.fltkfmt"
    bad.write_text("this is not valid fltkfmt syntax @@@\n")
    result = runner.invoke(server_cli.app, ["--grammar", _GRAMMAR, "--fmt", str(bad)])
    assert result.exit_code == 1


def test_unknown_rule_lists_valid_rules() -> None:
    result = runner.invoke(server_cli.app, ["--grammar", _GRAMMAR, "--rule", "no_such_rule"])
    assert result.exit_code == 1
    assert "no_such_rule" in result.output
    # The message lists the actual rule names so the user can correct the flag.
    assert "greeting" in result.output


def test_invalid_resolver_spec_exits_1() -> None:
    # A --resolver that will not load is a startup error (ResolverError is a ValueError), reported
    # on stderr with exit 1 before any protocol I/O, matching the grammar/.fltklsp/.fltkfmt policy.
    result = runner.invoke(server_cli.app, ["--grammar", _GRAMMAR, "--resolver", "no.such.module:create_resolver"])
    assert result.exit_code == 1
    assert "resolver" in result.output.lower()


def test_resolver_missing_attr_exits_1(tmp_path: Path) -> None:
    mod = tmp_path / "res.py"
    mod.write_text("x = 1\n")
    result = runner.invoke(server_cli.app, ["--grammar", _GRAMMAR, "--resolver", f"{mod}:create_resolver"])
    assert result.exit_code == 1
    assert "create_resolver" in result.output


def test_missing_pygls_prints_install_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = builtins.__import__

    def _fake_import(name: str, *args, **kwargs):
        if name == "fltk.lsp.server" or name.startswith("pygls"):
            msg = "No module named 'pygls'"
            raise ImportError(msg)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    result = runner.invoke(server_cli.app, ["--grammar", _GRAMMAR])
    assert result.exit_code == 1
    assert "fltk[lsp]" in result.output
