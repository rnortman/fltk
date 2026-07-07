"""Tests for the top-level load_lsp_config loader: parse + transform + validate + resolve."""

import pytest

from fltk import plumbing
from fltk.fegen import gsm
from fltk.lsp import lsp_config

# A small target grammar exercising labels, invoked rules, and literals.
_GRAMMAR = """
greeting := kw:"hello" , name:word , "!" ;
word := /[a-z]+/ ;
"""


def _grammar() -> gsm.Grammar:
    return plumbing.parse_grammar(_GRAMMAR)


def test_empty_text_short_circuits_to_empty_config() -> None:
    resolved = lsp_config.load_lsp_config("", _grammar())
    assert resolved.node_paints == {}
    assert resolved.child_matchers == {}
    assert resolved.global_child_matchers == ()


def test_whitespace_only_text_short_circuits_to_empty_config() -> None:
    resolved = lsp_config.load_lsp_config("   \n\t\n", _grammar())
    assert resolved.node_paints == {}
    assert resolved.child_matchers == {}
    assert resolved.global_child_matchers == ()


def test_valid_config_resolves_end_to_end() -> None:
    config_text = 'scope rule:greeting: keyword;\nrule greeting {\n  scope kw: keyword;\n  scope "!": punctuation;\n}\n'
    resolved = lsp_config.load_lsp_config(config_text, _grammar())
    # Global rule-name anchor => node paint on `greeting`.
    assert set(resolved.node_paints) == {"greeting"}
    # Rule-block anchors => child matchers on `greeting`.
    matches = {m.match for m in resolved.child_matchers["greeting"]}
    assert lsp_config.ByLabel("kw") in matches
    assert lsp_config.ByLiteralText("!") in matches


def test_comments_only_text_resolves_to_empty_config() -> None:
    resolved = lsp_config.load_lsp_config("// just a comment\n", _grammar())
    assert resolved.node_paints == {}
    assert resolved.child_matchers == {}
    assert resolved.global_child_matchers == ()


def test_validation_offense_raises_lsp_config_error() -> None:
    # `nonexistent` is neither a grammar rule name nor an item label.
    with pytest.raises(lsp_config.LspConfigError):
        lsp_config.load_lsp_config("scope nonexistent: keyword;\n", _grammar())


def test_unknown_rule_block_raises_lsp_config_error() -> None:
    with pytest.raises(lsp_config.LspConfigError):
        lsp_config.load_lsp_config("rule nosuchrule {\n  scope x: keyword;\n}\n", _grammar())


def test_parse_failure_raises_lsp_config_error() -> None:
    # Missing terminating `;` is a grammar-level parse failure; the message must carry the
    # "parse failed" marker and the caret-rendered offending line so an author can locate it.
    with pytest.raises(lsp_config.LspConfigError) as exc_info:
        lsp_config.load_lsp_config("scope kw: keyword\n", _grammar())
    message = str(exc_info.value)
    assert ".fltklsp config parse failed:" in message
    assert "scope kw: keyword" in message
    assert "^" in message
