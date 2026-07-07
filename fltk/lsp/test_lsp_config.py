"""Tests for the CST-to-model transform in lsp_config (pre-resolution model fidelity)."""

import pytest

from fltk.fegen.pyrt import errors, terminalsrc
from fltk.lsp import lsp_config
from fltk.lsp.fltklsp_parser import Parser


def _load(text: str) -> lsp_config.LspConfig:
    terminals = terminalsrc.TerminalSource(text)
    parser = Parser(terminals)
    result = parser.apply__parse_lsp_spec(0)
    if not result or result.pos != len(terminals.terminals):
        formatted = errors.format_error_message(
            parser.error_tracker,
            terminals,
            lambda rule_id: parser.rule_names[rule_id],
        )
        msg = f"parse failed:\n{formatted}"
        raise AssertionError(msg)
    assert result.result is not None
    return lsp_config.lsp_cst_to_config(result.result, terminals)


def test_empty_config_is_empty() -> None:
    config = _load("")
    assert config.global_scopes == ()
    assert config.rule_blocks == ()


def test_comments_only_is_empty() -> None:
    config = _load("// just a comment\n// another\n")
    assert config.global_scopes == ()
    assert config.rule_blocks == ()


def test_global_scope_single_anchor() -> None:
    config = _load("scope doc: comment;\n")
    assert len(config.global_scopes) == 1
    stmt = config.global_scopes[0]
    assert stmt.token == "comment"
    assert stmt.modifiers == ()
    assert stmt.hints == ()
    assert stmt.index == 0
    assert len(stmt.anchors) == 1
    anchor = stmt.anchors[0]
    assert anchor.name == "doc"
    assert anchor.literal is None
    assert anchor.qualifier is None


def test_global_scope_multiple_anchors() -> None:
    config = _load("scope typespec, config_type, signal_type: type;\n")
    stmt = config.global_scopes[0]
    assert tuple(a.name for a in stmt.anchors) == ("typespec", "config_type", "signal_type")
    assert stmt.token == "type"


def test_literal_anchor_is_unquoted() -> None:
    config = _load('rule condition_spec {\n    scope "time_since_last_exec": function.builtin;\n}\n')
    block = config.rule_blocks[0]
    anchor = block.scopes[0].anchors[0]
    assert anchor.literal == "time_since_last_exec"
    assert anchor.name is None
    assert anchor.qualifier is None


def test_single_quoted_literal_anchor_is_unquoted() -> None:
    config = _load("scope 'foo': keyword;\n")
    anchor = config.global_scopes[0].anchors[0]
    assert anchor.literal == "foo"
    assert anchor.name is None


def test_escaped_quote_literal_anchor_is_unquoted() -> None:
    config = _load('scope "a\\"b": keyword;\n')
    anchor = config.global_scopes[0].anchors[0]
    assert anchor.literal == 'a"b'


def test_invalid_escape_literal_anchor_raises_config_error() -> None:
    with pytest.raises(lsp_config.LspConfigError, match="invalid literal"):
        _load('scope "\\x": keyword;\n')


def test_qualified_anchors() -> None:
    config = _load("scope label:mylabel: keyword;\nscope rule:myrule: type;\n")
    label_anchor = config.global_scopes[0].anchors[0]
    assert label_anchor.qualifier == "label"
    assert label_anchor.name == "mylabel"
    rule_anchor = config.global_scopes[1].anchors[0]
    assert rule_anchor.qualifier == "rule"
    assert rule_anchor.name == "myrule"


def test_scope_modifiers_and_hints_split() -> None:
    config = _load("scope foo: type.declaration.customhint;\n")
    stmt = config.global_scopes[0]
    assert stmt.token == "type"
    assert stmt.modifiers == ("declaration",)
    assert stmt.hints == ("customhint",)


def test_scope_none_token() -> None:
    config = _load("scope foo: none;\n")
    stmt = config.global_scopes[0]
    assert stmt.token == "none"
    assert stmt.modifiers == ()
    assert stmt.hints == ()


def test_rule_block_rule_name_and_scopes() -> None:
    config = _load("rule clk_generate_target { scope cpp, proto: macro; }\n")
    assert len(config.rule_blocks) == 1
    block = config.rule_blocks[0]
    assert block.rule_name == "clk_generate_target"
    assert len(block.scopes) == 1
    assert tuple(a.name for a in block.scopes[0].anchors) == ("cpp", "proto")
    assert block.scopes[0].token == "macro"
    assert not block.is_namespace


def test_def_stmt_and_namespace() -> None:
    config = _load("rule cog { def identifier: type.cog; namespace; }\n")
    block = config.rule_blocks[0]
    assert block.is_namespace
    assert len(block.defs) == 1
    def_stmt = block.defs[0]
    assert def_stmt.anchor.name == "identifier"
    assert def_stmt.kind == ("type", "cog")


def test_ref_stmt_wildcard() -> None:
    config = _load("rule expr { ref identifier: *; }\n")
    block = config.rule_blocks[0]
    assert len(block.refs) == 1
    assert block.refs[0].kinds == "*"
    assert block.refs[0].anchor.name == "identifier"


def test_ref_stmt_kinds() -> None:
    config = _load("rule signal_reference { ref identifier: variable.signal, type; }\n")
    block = config.rule_blocks[0]
    assert block.refs[0].kinds == (("variable", "signal"), ("type",))


def test_multiple_blocks_for_same_rule_accumulate() -> None:
    config = _load("rule foo { scope a: type; }\nrule foo { scope b: keyword; }\n")
    assert len(config.rule_blocks) == 2
    assert config.rule_blocks[0].rule_name == "foo"
    assert config.rule_blocks[1].rule_name == "foo"
    assert config.rule_blocks[0].scopes[0].anchors[0].name == "a"
    assert config.rule_blocks[1].scopes[0].anchors[0].name == "b"


def test_statement_indices_are_file_order_across_blocks() -> None:
    config = _load("scope g: type;\nrule foo { scope a: keyword; def x: type; }\nscope h: string;\n")
    # Global scope g = 0; rule foo's scope a = 1, def x = 2; global scope h = 3.
    assert config.global_scopes[0].index == 0
    assert config.rule_blocks[0].scopes[0].index == 1
    assert config.rule_blocks[0].defs[0].index == 2
    assert config.global_scopes[1].index == 3
