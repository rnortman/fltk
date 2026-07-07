"""End-to-end tests for the ``fltk-highlight`` CLI."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from fltk.lsp.conftest import HELLO_GRAMMAR as _GRAMMAR
from fltk.lsp.conftest import HELLO_LSP as _LSP
from fltk.lsp.highlight_cli import _RESET, _THEME, app
from fltk.lsp.lsp_config import TOKEN_LEGEND


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text)
    return path


def _colored(token_type: str, segment: str) -> str:
    return f"\x1b[{_THEME[token_type]}m{segment}{_RESET}"


def test_defaults_only_ansi_output(tmp_path: Path) -> None:
    grammar = _write(tmp_path, "lang.fltkg", _GRAMMAR)
    src = _write(tmp_path, "in.txt", "hello world !")

    result = CliRunner().invoke(app, [str(src), "--grammar", str(grammar), "--rule", "top"])

    assert result.exit_code == 0
    # keyword `hello`, variable `world`, operator `!`, whitespace passed through uncolored.
    expected = _colored("keyword", "hello") + " " + _colored("variable", "world") + " " + _colored("operator", "!")
    assert result.stdout == expected


def test_explicit_spec_repaints(tmp_path: Path) -> None:
    grammar = _write(tmp_path, "lang.fltkg", _GRAMMAR)
    lsp = _write(tmp_path, "lang.fltklsp", _LSP)
    src = _write(tmp_path, "in.txt", "hello world !")

    result = CliRunner().invoke(app, [str(src), "--grammar", str(grammar), "--lsp", str(lsp), "--rule", "top"])

    assert result.exit_code == 0
    # The scope repaints `world` from the default `variable` to `type`.
    assert _colored("type", "world") in result.stdout
    assert _colored("variable", "world") not in result.stdout


def test_parse_failure_exits_1(tmp_path: Path) -> None:
    grammar = _write(tmp_path, "lang.fltkg", _GRAMMAR)
    src = _write(tmp_path, "in.txt", "hello world")  # missing the required `!`

    result = CliRunner().invoke(app, [str(src), "--grammar", str(grammar), "--rule", "top"])

    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr != ""


def test_bad_lsp_spec_exits_1(tmp_path: Path) -> None:
    grammar = _write(tmp_path, "lang.fltkg", _GRAMMAR)
    # `no_such_rule` is not a grammar rule -> load-time validation error.
    lsp = _write(tmp_path, "lang.fltklsp", "rule no_such_rule {\n  scope kw: keyword;\n}\n")
    src = _write(tmp_path, "in.txt", "hello world !")

    result = CliRunner().invoke(app, [str(src), "--grammar", str(grammar), "--lsp", str(lsp), "--rule", "top"])

    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr != ""


def test_def_site_rendered_bold(tmp_path: Path) -> None:
    grammar = _write(tmp_path, "lang.fltkg", _GRAMMAR)
    # `def name: variable;` paints the `name` child (`world`) as `variable` + `declaration`.
    lsp = _write(tmp_path, "lang.fltklsp", "rule greeting {\n  def name: variable;\n}\n")
    src = _write(tmp_path, "in.txt", "hello world !")

    result = CliRunner().invoke(app, [str(src), "--grammar", str(grammar), "--lsp", str(lsp), "--rule", "top"])

    assert result.exit_code == 0
    # The `declaration` modifier adds the bold `1;` SGR prefix; the plain form must not appear.
    assert f"\x1b[1;{_THEME['variable']}mworld{_RESET}" in result.stdout
    assert _colored("variable", "world") not in result.stdout


def test_missing_grammar_exits_1(tmp_path: Path) -> None:
    src = _write(tmp_path, "in.txt", "hello world !")

    result = CliRunner().invoke(app, [str(src), "--grammar", str(tmp_path / "nope.fltkg"), "--rule", "top"])

    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr != ""


def test_missing_lsp_exits_1(tmp_path: Path) -> None:
    grammar = _write(tmp_path, "lang.fltkg", _GRAMMAR)
    src = _write(tmp_path, "in.txt", "hello world !")

    result = CliRunner().invoke(
        app, [str(src), "--grammar", str(grammar), "--lsp", str(tmp_path / "nope.fltklsp"), "--rule", "top"]
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr != ""


def test_missing_input_file_exits_1(tmp_path: Path) -> None:
    grammar = _write(tmp_path, "lang.fltkg", _GRAMMAR)

    result = CliRunner().invoke(app, [str(tmp_path / "nope.txt"), "--grammar", str(grammar), "--rule", "top"])

    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr != ""


def test_theme_covers_the_legend() -> None:
    # The theme must map exactly the legend members, so a legend change that forgets a theme
    # entry (silently rendering that type uncolored) is caught here rather than by a squinting user.
    assert set(_THEME) == TOKEN_LEGEND
