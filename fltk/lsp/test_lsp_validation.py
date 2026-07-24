"""Tests for load-time GSM validation of a parsed .fltklsp config."""

import pytest

from fltk import plumbing
from fltk.fegen.pyrt import terminalsrc
from fltk.lsp import lsp_config
from fltk.lsp.fltklsp_parser import Parser

# A small target grammar exercising labels, invoked rules, and literals.
#   greeting: labels {kw, name}, literals {"hello", "!"}, invoked rules {word}
#   word:     no labels/literals/invoked rules
_GRAMMAR = """
greeting := kw:"hello" , name:word , "!" ;
word := /[a-z]+/ ;
"""


def _index() -> lsp_config.GrammarIndex:
    return lsp_config.build_grammar_index(plumbing.parse_grammar(_GRAMMAR))


# TODO(lsp-test-parse-helper): fold this parse boilerplate into plumbing.parse_lsp_config once
# that wrapper lands (shared with test_lsp_config._load, which reports failures with a caret).
def _parse(config_text: str) -> tuple[lsp_config.LspConfig, terminalsrc.TerminalSource]:
    terminals = terminalsrc.TerminalSource(config_text)
    result = Parser(terminals).apply__parse_lsp_spec(0)
    assert result is not None and result.pos == len(terminals.terminals), "config text failed to parse"
    return lsp_config.lsp_cst_to_config(result.result, terminals), terminals


def _validate(config_text: str) -> None:
    config, terminals = _parse(config_text)
    lsp_config.validate_config(config, _index(), terminals)


def test_valid_config_passes() -> None:
    _validate(
        "scope kw: keyword;\n"
        "rule greeting {\n"
        "  scope kw: keyword;\n"
        "  scope name: variable;\n"
        '  scope "!": punctuation;\n'
        "}\n"
    )


def test_unknown_rule() -> None:
    with pytest.raises(lsp_config.LspConfigError, match="unknown grammar rule 'bogus'"):
        _validate("rule bogus {\n  scope kw: keyword;\n}\n")


def test_unknown_scope_token() -> None:
    with pytest.raises(lsp_config.LspConfigError, match="unknown scope token 'bogustoken'"):
        _validate("scope kw: bogustoken;\n")


def test_legend_token_and_none_are_accepted() -> None:
    _validate("scope kw: keyword;\nscope name: none;\n")


def test_none_token_with_modifiers_is_rejected() -> None:
    with pytest.raises(lsp_config.LspConfigError, match="'none' must be the only segment"):
        _validate("scope kw: none.declaration;\n")


def test_local_label_anchor_valid_and_invalid() -> None:
    _validate("rule greeting {\n  scope name: variable;\n}\n")
    match = "no item labeled 'bogus' and no invoked rule 'bogus' in rule 'greeting'"
    with pytest.raises(lsp_config.LspConfigError, match=match):
        _validate("rule greeting {\n  scope bogus: variable;\n}\n")


def test_local_literal_anchor_valid_and_invalid() -> None:
    _validate('rule greeting {\n  scope "hello": keyword;\n}\n')
    with pytest.raises(lsp_config.LspConfigError, match="literal 'bye' does not match any literal in rule 'greeting'"):
        _validate('rule greeting {\n  scope "bye": keyword;\n}\n')


def test_local_qualifier_restriction() -> None:
    # `name` is a label but the invoked rule is `word`.
    _validate("rule greeting {\n  scope label:name: variable;\n}\n")
    _validate("rule greeting {\n  scope rule:word: variable;\n}\n")
    with pytest.raises(lsp_config.LspConfigError, match="rule 'greeting' does not invoke a rule named 'name'"):
        _validate("rule greeting {\n  scope rule:name: variable;\n}\n")
    with pytest.raises(lsp_config.LspConfigError, match="no item labeled 'word' in rule 'greeting'"):
        _validate("rule greeting {\n  scope label:word: variable;\n}\n")


def test_global_anchor_union_and_qualifiers() -> None:
    # `greeting` is a rule name; `kw` is a label; both resolve unqualified.
    _validate("scope greeting: keyword;\nscope kw: keyword;\n")
    _validate("scope rule:greeting: keyword;\nscope label:kw: keyword;\n")
    with pytest.raises(lsp_config.LspConfigError, match=r"'kw' is not a grammar rule name\b"):
        _validate("scope rule:kw: keyword;\n")
    with pytest.raises(lsp_config.LspConfigError, match="'greeting' is not an item label anywhere in the grammar"):
        _validate("scope label:greeting: keyword;\n")
    with pytest.raises(lsp_config.LspConfigError, match="'nope' is not a grammar rule name or an item label"):
        _validate("scope nope: keyword;\n")


def test_global_literal_anchor() -> None:
    _validate('scope "!": punctuation;\n')
    with pytest.raises(lsp_config.LspConfigError, match="literal '\\?' does not appear in the grammar"):
        _validate('scope "?": punctuation;\n')


def test_def_and_ref_anchors_are_validated() -> None:
    _validate("rule greeting {\n  def name: symbol.function;\n  ref name: symbol.function;\n}\n")
    with pytest.raises(lsp_config.LspConfigError, match="no item labeled 'bogus'"):
        _validate("rule greeting {\n  def bogus: symbol.function;\n}\n")


def test_unknown_rule_block_validates_scope_token_but_skips_anchors() -> None:
    # The unknown rule and the bad scope token are reported, but the block's def/ref anchors
    # are not validated against the missing rule (no complaint about `x` or `y`).
    with pytest.raises(lsp_config.LspConfigError) as excinfo:
        _validate("rule bogus {\n  scope kw: bogustoken;\n  def x: type;\n  ref y: *;\n}\n")
    message = str(excinfo.value)
    assert "unknown grammar rule 'bogus'" in message
    assert "bogustoken" in message
    assert "'x'" not in message
    assert "'y'" not in message


def test_multiple_errors_collected() -> None:
    with pytest.raises(lsp_config.LspConfigError) as excinfo:
        _validate("scope kw: bogustoken;\nrule missing {\n  scope kw: keyword;\n}\n")
    message = str(excinfo.value)
    assert "2 error(s)" in message
    assert "bogustoken" in message
    assert "missing" in message


def test_error_message_carries_line_and_column() -> None:
    with pytest.raises(lsp_config.LspConfigError) as excinfo:
        _validate("scope kw: keyword;\nscope kw: bogustoken;\n")
    message = str(excinfo.value)
    # Second line, offending token — header renders 1-based line/column with a caret.
    assert "line 2" in message
    assert "^" in message
