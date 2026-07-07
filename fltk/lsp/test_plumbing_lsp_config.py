"""Tests for the plumbing.parse_lsp_config / parse_lsp_config_file wrappers."""

from pathlib import Path

import pytest

from fltk import plumbing
from fltk.fegen import gsm
from fltk.lsp import lsp_config

_GRAMMAR = """
greeting := kw:"hello" , name:word , "!" ;
word := /[a-z]+/ ;
"""


def _grammar() -> gsm.Grammar:
    return plumbing.parse_grammar(_GRAMMAR)


def test_parse_lsp_config_empty_text() -> None:
    resolved = plumbing.parse_lsp_config("", _grammar())
    assert resolved.node_paints == {}
    assert resolved.child_matchers == {}


def test_parse_lsp_config_valid_text() -> None:
    resolved = plumbing.parse_lsp_config("rule greeting {\n  scope kw: keyword;\n}\n", _grammar())
    matches = {m.match for m in resolved.child_matchers["greeting"]}
    assert lsp_config.ByLabel("kw") in matches


def test_parse_lsp_config_validation_offense_raises() -> None:
    with pytest.raises(lsp_config.LspConfigError):
        plumbing.parse_lsp_config("scope nonexistent: keyword;\n", _grammar())


def test_parse_lsp_config_file_reads_and_parses(tmp_path: Path) -> None:
    config_path = tmp_path / "lang.fltklsp"
    config_path.write_text("rule greeting {\n  scope kw: keyword;\n}\n")
    resolved = plumbing.parse_lsp_config_file(config_path, _grammar())
    matches = {m.match for m in resolved.child_matchers["greeting"]}
    assert lsp_config.ByLabel("kw") in matches


def test_parse_lsp_config_file_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        plumbing.parse_lsp_config_file(tmp_path / "nope.fltklsp", _grammar())
