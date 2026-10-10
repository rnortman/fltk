"""Tests for the CST-to-model transform in lsp_config (pre-resolution model fidelity)."""

from typing import Any

import pytest

from fltk.fegen.pyrt import terminalsrc
from fltk.lsp import lsp_config
from fltk.lsp.fltklsp_parser import Parser


def test_empty_config_is_empty() -> None:
    config = lsp_config.parse_lsp_config_text("")
    assert config.global_scopes == ()
    assert config.rule_blocks == ()


def test_comments_only_is_empty() -> None:
    config = lsp_config.parse_lsp_config_text("// just a comment\n// another\n")
    assert config.global_scopes == ()
    assert config.rule_blocks == ()


def test_parse_failure_raises_config_error_with_caret() -> None:
    with pytest.raises(lsp_config.LspConfigError) as excinfo:
        lsp_config.parse_lsp_config_text("scope kw: keyword\n")
    message = str(excinfo.value)
    assert message.startswith(".fltklsp config parse failed:\n")
    assert "scope kw: keyword" in message
    assert "^" in message


def test_trailing_garbage_after_valid_statement_is_a_parse_failure() -> None:
    with pytest.raises(lsp_config.LspConfigError, match=r"^\.fltklsp config parse failed:\n"):
        lsp_config.parse_lsp_config_text("scope kw: keyword;\ngarbage\n")


def test_unknown_anchor_and_token_are_accepted_by_the_model_entry() -> None:
    config = lsp_config.parse_lsp_config_text("scope nosuchanchor: nosuchtoken;\n")
    assert config.rule_blocks == ()
    assert len(config.global_scopes) == 1
    stmt = config.global_scopes[0]
    assert stmt.token == "nosuchtoken"
    assert tuple(a.name for a in stmt.anchors) == ("nosuchanchor",)


def test_global_scope_single_anchor() -> None:
    config = lsp_config.parse_lsp_config_text("scope doc: comment;\n")
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
    config = lsp_config.parse_lsp_config_text("scope typespec, config_type, signal_type: type;\n")
    stmt = config.global_scopes[0]
    assert tuple(a.name for a in stmt.anchors) == ("typespec", "config_type", "signal_type")
    assert stmt.token == "type"


def test_literal_anchor_is_unquoted() -> None:
    config = lsp_config.parse_lsp_config_text(
        'rule condition_spec {\n    scope "time_since_last_exec": function.builtin;\n}\n'
    )
    block = config.rule_blocks[0]
    anchor = block.scopes[0].anchors[0]
    assert anchor.literal == "time_since_last_exec"
    assert anchor.name is None
    assert anchor.qualifier is None


def test_single_quoted_literal_anchor_is_unquoted() -> None:
    config = lsp_config.parse_lsp_config_text("scope 'foo': keyword;\n")
    anchor = config.global_scopes[0].anchors[0]
    assert anchor.literal == "foo"
    assert anchor.name is None


def test_escaped_quote_literal_anchor_is_unquoted() -> None:
    config = lsp_config.parse_lsp_config_text('scope "a\\"b": keyword;\n')
    anchor = config.global_scopes[0].anchors[0]
    assert anchor.literal == 'a"b'


def test_invalid_escape_literal_anchor_raises_config_error() -> None:
    with pytest.raises(lsp_config.LspConfigError, match="invalid literal"):
        lsp_config.parse_lsp_config_text('scope "\\x": keyword;\n')


def test_qualified_anchors() -> None:
    config = lsp_config.parse_lsp_config_text("scope label:mylabel: keyword;\nscope rule:myrule: type;\n")
    label_anchor = config.global_scopes[0].anchors[0]
    assert label_anchor.qualifier == "label"
    assert label_anchor.name == "mylabel"
    rule_anchor = config.global_scopes[1].anchors[0]
    assert rule_anchor.qualifier == "rule"
    assert rule_anchor.name == "myrule"


def test_scope_modifiers_and_hints_split() -> None:
    config = lsp_config.parse_lsp_config_text("scope foo: type.declaration.customhint;\n")
    stmt = config.global_scopes[0]
    assert stmt.token == "type"
    assert stmt.modifiers == ("declaration",)
    assert stmt.hints == ("customhint",)


def test_scope_none_token() -> None:
    config = lsp_config.parse_lsp_config_text("scope foo: none;\n")
    stmt = config.global_scopes[0]
    assert stmt.token == "none"
    assert stmt.modifiers == ()
    assert stmt.hints == ()


def test_rule_block_rule_name_and_scopes() -> None:
    config = lsp_config.parse_lsp_config_text("rule clk_generate_target { scope cpp, proto: macro; }\n")
    assert len(config.rule_blocks) == 1
    block = config.rule_blocks[0]
    assert block.rule_name == "clk_generate_target"
    assert len(block.scopes) == 1
    assert tuple(a.name for a in block.scopes[0].anchors) == ("cpp", "proto")
    assert block.scopes[0].token == "macro"
    assert not block.is_namespace


def test_def_stmt_and_namespace() -> None:
    config = lsp_config.parse_lsp_config_text("rule cog { def identifier: type.cog; namespace; }\n")
    block = config.rule_blocks[0]
    assert block.is_namespace
    assert len(block.defs) == 1
    def_stmt = block.defs[0]
    assert def_stmt.anchor.name == "identifier"
    assert def_stmt.kind == ("type", "cog")


def test_ref_stmt_wildcard() -> None:
    config = lsp_config.parse_lsp_config_text("rule expr { ref identifier: *; }\n")
    block = config.rule_blocks[0]
    assert len(block.refs) == 1
    assert block.refs[0].kinds == "*"
    assert block.refs[0].anchor.name == "identifier"


def test_ref_stmt_kinds() -> None:
    config = lsp_config.parse_lsp_config_text("rule signal_reference { ref identifier: variable.signal, type; }\n")
    block = config.rule_blocks[0]
    assert block.refs[0].kinds == (("variable", "signal"), ("type",))


def test_multiple_blocks_for_same_rule_accumulate() -> None:
    config = lsp_config.parse_lsp_config_text("rule foo { scope a: type; }\nrule foo { scope b: keyword; }\n")
    assert len(config.rule_blocks) == 2
    assert config.rule_blocks[0].rule_name == "foo"
    assert config.rule_blocks[1].rule_name == "foo"
    assert config.rule_blocks[0].scopes[0].anchors[0].name == "a"
    assert config.rule_blocks[1].scopes[0].anchors[0].name == "b"


def test_statement_indices_are_file_order_across_blocks() -> None:
    config = lsp_config.parse_lsp_config_text(
        "scope g: type;\nrule foo { scope a: keyword; def x: type; }\nscope h: string;\n"
    )
    # Global scope g = 0; rule foo's scope a = 1, def x = 2; global scope h = 3.
    assert config.global_scopes[0].index == 0
    assert config.rule_blocks[0].scopes[0].index == 1
    assert config.rule_blocks[0].defs[0].index == 2
    assert config.global_scopes[1].index == 3


def _poison_terminal_spans(node: Any) -> None:
    """Replace every terminal span under ``node`` with a source-bearing span whose offsets
    run past its source, so ``text()`` is ``None`` while ``has_source()`` is ``True``."""
    for index, (label, child) in enumerate(node.children):
        if isinstance(child, terminalsrc.Span):
            node.children[index] = (label, terminalsrc.Span.with_source(child.start, child.start + 10_000, "x"))
        elif hasattr(child, "children"):
            _poison_terminal_spans(child)


def test_inconsistent_source_bearing_span_raises_value_error_not_config_error() -> None:
    terminals = terminalsrc.TerminalSource("scope kw: keyword;\n")
    result = Parser(terminals).apply__parse_lsp_spec(0)
    assert result is not None
    _poison_terminal_spans(result.result)
    with pytest.raises(ValueError, match=r"source-bearing span") as excinfo:
        lsp_config.lsp_cst_to_config(result.result, terminals)
    assert not isinstance(excinfo.value, lsp_config.LspConfigError)
