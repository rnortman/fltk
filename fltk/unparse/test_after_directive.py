#!/usr/bin/env python3
"""Comprehensive tests for after directive functionality in formatter configuration."""

import pytest

from fltk import plumbing
from fltk.unparse.combinators import HARDLINE, NBSP, NIL, SOFTLINE
from fltk.unparse.fmt_config import ItemSelector, OperationType


def test_after_directive_label():
    """Test after directive with label selector."""
    config_text = """
rule expr {
    after operator { nbsp; }
}
"""

    config = plumbing.parse_format_config(config_text)

    # Check that rule config was created
    assert "expr" in config.rule_configs
    rule_config = config.rule_configs["expr"]

    # Check that after config was stored correctly in anchor_configs
    assert "after:label:operator" in rule_config.anchor_configs
    anchor_config = rule_config.anchor_configs["after:label:operator"]

    assert anchor_config.selector_type == ItemSelector.LABEL
    assert anchor_config.selector_value == "operator"
    # Verify it has SPACING operation with NBSP
    assert len(anchor_config.operations) == 1
    assert anchor_config.operations[0].operation_type == OperationType.SPACING
    assert anchor_config.operations[0].spacing is NBSP


def test_after_directive_literal():
    """Test after directive with literal selector."""
    config_text = """
rule expr {
    after "+" { soft; }
}
"""

    config = plumbing.parse_format_config(config_text)

    # Check that rule config was created
    assert "expr" in config.rule_configs
    rule_config = config.rule_configs["expr"]

    # Check that after config was stored correctly in anchor_configs
    assert "after:literal:+" in rule_config.anchor_configs
    anchor_config = rule_config.anchor_configs["after:literal:+"]

    assert anchor_config.selector_type == ItemSelector.LITERAL
    assert anchor_config.selector_value == "+"
    # Verify it has SPACING operation with SOFTLINE
    assert len(anchor_config.operations) == 1
    assert anchor_config.operations[0].operation_type == OperationType.SPACING
    assert anchor_config.operations[0].spacing is SOFTLINE


def test_multiple_after_directives():
    """Test multiple after directives in the same rule."""
    config_text = """
rule expr {
    after operator { nbsp; }
    after "+" { soft; }
    after identifier { nil; }
}
"""

    config = plumbing.parse_format_config(config_text)

    # Check that rule config was created
    assert "expr" in config.rule_configs
    rule_config = config.rule_configs["expr"]

    # Check all three after configs in anchor_configs
    assert len(rule_config.anchor_configs) == 3

    # Check label-based config
    assert "after:label:operator" in rule_config.anchor_configs
    operator_config = rule_config.anchor_configs["after:label:operator"]
    assert operator_config.selector_type == ItemSelector.LABEL
    assert operator_config.selector_value == "operator"

    # Check literal-based config
    assert "after:literal:+" in rule_config.anchor_configs
    plus_config = rule_config.anchor_configs["after:literal:+"]
    assert plus_config.selector_type == ItemSelector.LITERAL
    assert plus_config.selector_value == "+"

    # Check identifier config
    assert "after:label:identifier" in rule_config.anchor_configs
    id_config = rule_config.anchor_configs["after:label:identifier"]
    assert id_config.selector_type == ItemSelector.LABEL
    assert id_config.selector_value == "identifier"


def test_mixed_rule_statements():
    """Test after directives mixed with default statements."""
    config_text = """
rule expr {
    ws_allowed: nil;
    after operator { nbsp; }
    ws_required: hard;
    after "+" { soft; }
}
"""

    config = plumbing.parse_format_config(config_text)

    # Check that rule config was created
    assert "expr" in config.rule_configs
    rule_config = config.rule_configs["expr"]

    # Check default spacing configs
    assert rule_config.ws_allowed_spacing is NIL
    assert rule_config.ws_required_spacing is HARDLINE

    # Check after configs in anchor_configs
    assert len(rule_config.anchor_configs) == 2
    assert "after:label:operator" in rule_config.anchor_configs
    assert "after:literal:+" in rule_config.anchor_configs


def test_global_after_directive_only():
    """Test global after directive without rule overrides."""
    config_text = """
    after operator { nbsp; }
    """
    config = plumbing.parse_format_config(config_text)

    # Should have global after config in global_anchor_configs
    assert len(config.anchor_configs) == 1
    assert "after:label:operator" in config.anchor_configs

    global_config = config.anchor_configs["after:label:operator"]
    assert global_config.selector_type == ItemSelector.LABEL
    assert global_config.selector_value == "operator"
    assert len(global_config.operations) == 1
    assert global_config.operations[0].operation_type == OperationType.SPACING
    assert global_config.operations[0].spacing is NBSP


def test_global_after_directive_multiple():
    """Test multiple global after directives."""
    config_text = """
    after operator { nbsp; }
    after ";" { hard; }
    after identifier { soft; }
    """
    config = plumbing.parse_format_config(config_text)

    # Should have three global after configs in global_anchor_configs
    assert len(config.anchor_configs) == 3

    # Check label-based
    assert "after:label:operator" in config.anchor_configs
    assert config.anchor_configs["after:label:operator"].operations[0].spacing is NBSP

    assert "after:label:identifier" in config.anchor_configs
    assert config.anchor_configs["after:label:identifier"].operations[0].spacing is SOFTLINE

    # Check literal-based
    assert "after:literal:;" in config.anchor_configs
    assert config.anchor_configs["after:literal:;"].operations[0].spacing is HARDLINE


def test_global_and_rule_after_directives_different_items():
    """Test global and rule after directives for different items."""
    config_text = """
    after operator { nbsp; }
    after ";" { hard; }

    rule expr {
        after identifier { soft; }
    }
    """
    config = plumbing.parse_format_config(config_text)

    # Should have global after configs in global_anchor_configs
    assert len(config.anchor_configs) == 2
    assert "after:label:operator" in config.anchor_configs
    assert "after:literal:;" in config.anchor_configs

    # Should have rule-specific config
    assert "expr" in config.rule_configs
    rule_config = config.rule_configs["expr"]
    assert len(rule_config.anchor_configs) == 1
    assert "after:label:identifier" in rule_config.anchor_configs


def test_rule_overrides_global_after_directive():
    """Test that rule-scoped after directives override global ones."""
    config_text = """
    after operator { nbsp; }

    rule expr {
        after operator { hard; }
    }
    """
    config = plumbing.parse_format_config(config_text)

    # Should have global after config in global_anchor_configs
    assert len(config.anchor_configs) == 1
    assert "after:label:operator" in config.anchor_configs
    assert config.anchor_configs["after:label:operator"].operations[0].spacing is NBSP

    # Should have rule-specific config that overrides global
    assert "expr" in config.rule_configs
    rule_config = config.rule_configs["expr"]
    assert len(rule_config.anchor_configs) == 1
    assert "after:label:operator" in rule_config.anchor_configs
    assert rule_config.anchor_configs["after:label:operator"].operations[0].spacing is HARDLINE


def test_multiple_rules_with_different_overrides():
    """Test multiple rules with different after directive overrides."""
    config_text = """
    after operator { nbsp; }
    after ";" { hard; }

    rule expr {
        after operator { soft; }
    }

    rule statement {
        after ";" { nil; }
    }
    """
    config = plumbing.parse_format_config(config_text)

    # Should have global after configs in global_anchor_configs
    assert len(config.anchor_configs) == 2
    assert config.anchor_configs["after:label:operator"].operations[0].spacing is NBSP
    assert config.anchor_configs["after:literal:;"].operations[0].spacing is HARDLINE

    # expr rule should override operator but inherit semicolon
    expr_config = config.rule_configs["expr"]
    assert len(expr_config.anchor_configs) == 1
    assert expr_config.anchor_configs["after:label:operator"].operations[0].spacing is SOFTLINE

    # statement rule should override semicolon but inherit operator
    stmt_config = config.rule_configs["statement"]
    assert len(stmt_config.anchor_configs) == 1
    assert stmt_config.anchor_configs["after:literal:;"].operations[0].spacing is NIL


def test_mixed_label_and_literal_after_directives():
    """Test mixed label and literal after directives at both scopes."""
    config_text = """
    after operator { nbsp; }
    after ";" { hard; }

    rule expr {
        after "+" { soft; }
        after identifier { nil; }
    }
    """
    config = plumbing.parse_format_config(config_text)

    # Should have both global configs in global_anchor_configs
    assert len(config.anchor_configs) == 2
    assert "after:label:operator" in config.anchor_configs
    assert "after:literal:;" in config.anchor_configs

    # Should have both rule configs
    rule_config = config.rule_configs["expr"]
    assert len(rule_config.anchor_configs) == 2
    assert "after:literal:+" in rule_config.anchor_configs
    assert "after:label:identifier" in rule_config.anchor_configs


def test_comprehensive_integration_global_scope():
    """Test end-to-end integration with global after directives."""
    # Simple grammar for testing
    grammar_text = """
    expr := term , (operator:'+' , term)*;
    term := value:/[0-9]+/;
    """

    # Global after directive
    formatter_text = """
    after operator { nbsp; }
    """

    # Parse and generate
    grammar = plumbing.parse_grammar(grammar_text)
    parser_result = plumbing.generate_parser(grammar, capture_trivia=True)
    formatter_config = plumbing.parse_format_config(formatter_text)
    unparser_result = plumbing.generate_unparser(
        grammar, parser_result.cst_module_name, formatter_config=formatter_config
    )

    # Test parsing and unparsing
    test_input = "1+2+3"
    parse_result = plumbing.parse_text(parser_result, test_input, "expr")
    assert parse_result.success

    # Unparse and check result
    doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "expr")
    rendered = plumbing.render_doc(doc)

    # Should have spacing after operators from global config (replaces separator spacing)
    assert "1+ 2+ 3" == rendered  # nbsp replaces separator spacing


def test_comprehensive_integration_rule_override():
    """Test end-to-end integration with rule overriding global after directive."""
    # Simple grammar for testing
    grammar_text = """
    expr := term , (operator:'+' , term)*;
    term := value:/[0-9]+/;
    """

    # Global after directive with rule override
    formatter_text = """
    after operator { hard; }

    rule expr {
        after operator { nbsp; }
    }
    """

    # Parse and generate
    grammar = plumbing.parse_grammar(grammar_text)
    parser_result = plumbing.generate_parser(grammar, capture_trivia=True)
    formatter_config = plumbing.parse_format_config(formatter_text)
    unparser_result = plumbing.generate_unparser(
        grammar, parser_result.cst_module_name, formatter_config=formatter_config
    )

    # Test parsing and unparsing
    test_input = "1+2+3"
    parse_result = plumbing.parse_text(parser_result, test_input, "expr")
    assert parse_result.success

    # Unparse and check result
    doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "expr")
    rendered = plumbing.render_doc(doc)

    # Should use rule override (nbsp) not global (hardline), replacing separator spacing
    assert "1+ 2+ 3" == rendered  # nbsp replaces separator spacing


def test_after_directive_replaces_default_separator_explicitly():
    """Test that after directive completely replaces default separator behavior."""

    # Grammar with comma separator
    grammar_text = """
    list := item , (',' , item ,)*;
    item := value:/[a-z]+/;
    """

    # Format config with global default AND after directive override
    formatter_text = """
    ws_allowed: hard;

    rule list {
        after "," { nbsp; }
    }
    """

    # Parse and generate
    grammar = plumbing.parse_grammar(grammar_text)
    parser_result = plumbing.generate_parser(grammar, capture_trivia=True)
    formatter_config = plumbing.parse_format_config(formatter_text)
    unparser_result = plumbing.generate_unparser(
        grammar, parser_result.cst_module_name, formatter_config=formatter_config
    )

    # Test input
    test_input = "a,b,c"
    parse_result = plumbing.parse_text(parser_result, test_input, "list")
    assert parse_result.success

    # Unparse and check result
    doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "list")
    rendered = plumbing.render_doc(doc)

    # If separator default was used: "a,\nb,\nc" (hardlines)
    # If after directive works: "a, b, c" (single spaces)
    assert "a\n, b\n, c\n" == rendered, f"Expected single spaces after commas, got: {rendered}"


def test_separator_default_without_after_directive():
    """Control test: verify separator default works when no after directive."""

    # Same grammar
    grammar_text = """
    list := item , (',' , item ,)*;
    item := value:/[a-z]+/;
    """

    # Format config with only global default (no after directive)
    formatter_text = """
    ws_allowed: hard;
    """

    # Parse and generate
    grammar = plumbing.parse_grammar(grammar_text)
    parser_result = plumbing.generate_parser(grammar, capture_trivia=True)
    formatter_config = plumbing.parse_format_config(formatter_text)
    unparser_result = plumbing.generate_unparser(
        grammar, parser_result.cst_module_name, formatter_config=formatter_config
    )

    # Test input
    test_input = "a,b,c"
    parse_result = plumbing.parse_text(parser_result, test_input, "list")
    assert parse_result.success

    # Unparse and check result
    doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "list")
    rendered = plumbing.render_doc(doc)

    # Should use separator default (hardlines)
    assert "a\n,\nb\n,\nc\n" == rendered, f"Expected hardlines after commas, got: {rendered}"


def test_error_cases():
    """Test error handling for invalid after directives."""
    # Test empty after directive (should fail)
    with pytest.raises(ValueError, match="exactly one position_spec_statement"):
        plumbing.parse_format_config("""
rule expr {
    after operator { }
}
""")

    # Test multiple spacing in after block uses first
    config_text = """
    after operator {
        nbsp;
        hard;
    }
    """
    # Determine selector type and value from the anchor
    with pytest.raises(ValueError, match="Expected at most one position_spec_statement child but have 2"):
        plumbing.parse_format_config(config_text)
