"""End-to-end tests for the omit functionality in the unparser."""

import sys
from typing import Any

import pytest

from fltk.plumbing import (
    generate_parser,
    generate_unparser,
    parse_format_config,
    parse_grammar,
    parse_text,
    unparse_cst,
)
from fltk.unparse.combinators import NIL, Concat, Text

# Test grammar with various elements that can be omitted
TEST_GRAMMAR = """
// A simple expression grammar with operators and parentheses
expr := term , (add_op , term)*;
add_op := op:"+" | op:"-";
term := factor , (mul_op , factor)*;
mul_op := op:"*" | op:"/";
factor := number | "(" , expr , ")";
number := value:/[0-9]+/;

// A function call grammar with optional elements
func_call := name:/[a-zA-Z_][a-zA-Z0-9_]*/ , "(" , args? , ")";
args := expr , ("," , expr)*;

// A statement grammar with semicolons and keywords
statement := assign_stmt | if_stmt | block;
assign_stmt := var:/[a-zA-Z_][a-zA-Z0-9_]*/ , "=" , expr , ";";
if_stmt := "if" , "(" , expr , ")" , statement , else_part?;
else_part := "else" , statement;
block := "{" , statement* , "}";

// A list-like structure
list := "[" , items? , "]";
items := expr , ("," , expr)*;
"""


@pytest.fixture
def omit_parser_unparser():
    """Generate parser and unparser for the test grammar."""
    parser_result = None
    try:
        grammar = parse_grammar(TEST_GRAMMAR)
        parser_result = generate_parser(grammar, capture_trivia=True)
        yield parser_result
    finally:
        if parser_result and parser_result.cst_module_name in sys.modules:
            del sys.modules[parser_result.cst_module_name]


def parse_rule(parser_result, rule_name: str, input_text: str) -> tuple[Any, str]:
    """Parse input text using specified rule."""
    parse_result = parse_text(parser_result, input_text, rule_name)

    if not parse_result.success:
        pytest.fail(f"Failed to parse '{input_text}' with rule '{rule_name}':\n{parse_result.error_message}")

    return parse_result.cst, input_text


def test_omit_operators_in_expressions(omit_parser_unparser):
    """Test omitting operators from mathematical expressions."""
    parser_result = omit_parser_unparser

    # Formatter config that omits + and * operators
    formatter_config_text = """
    omit "+";
    omit "*";
    """

    formatter_config = parse_format_config(formatter_config_text)
    unparser_result = generate_unparser(
        parser_result.grammar, parser_result.cst_module_name, formatter_config=formatter_config
    )

    # Test expression with both + and * operators
    test_input = "1+2*3+4"
    cst, input_text = parse_rule(parser_result, "expr", test_input)

    doc = unparse_cst(unparser_result, cst, input_text, "expr")

    # Operators should be omitted, leaving only numbers
    expected = Concat((Text("1"), Text("2"), Text("3"), Text("4")))
    assert doc == expected, f"Expected {expected}, got {doc}"


def test_omit_labeled_operators(omit_parser_unparser):
    """Test omitting operators by their labels."""
    parser_result = omit_parser_unparser

    # Formatter config that omits items with label "op"
    formatter_config_text = """
    omit op;
    """

    formatter_config = parse_format_config(formatter_config_text)
    unparser_result = generate_unparser(
        parser_result.grammar, parser_result.cst_module_name, formatter_config=formatter_config
    )

    # Test expression with various operators
    test_input = "1+2-3*4/5"
    cst, input_text = parse_rule(parser_result, "expr", test_input)

    doc = unparse_cst(unparser_result, cst, input_text, "expr")

    # All operators (labeled as "op") should be omitted
    expected = Concat((Text("1"), Text("2"), Text("3"), Text("4"), Text("5")))
    assert doc == expected, f"Expected {expected}, got {doc}"


def test_omit_parentheses(omit_parser_unparser):
    """Test omitting parentheses from expressions."""
    parser_result = omit_parser_unparser

    # Formatter config that omits parentheses
    formatter_config_text = """
    omit "(";
    omit ")";
    """

    formatter_config = parse_format_config(formatter_config_text)
    unparser_result = generate_unparser(
        parser_result.grammar, parser_result.cst_module_name, formatter_config=formatter_config
    )

    # Test expression with parentheses
    test_input = "(1+2)*(3+4)"
    cst, input_text = parse_rule(parser_result, "expr", test_input)

    doc = unparse_cst(unparser_result, cst, input_text, "expr")

    # Parentheses should be omitted
    expected = Concat((Text("1"), Text("+"), Text("2"), Text("*"), Text("3"), Text("+"), Text("4")))
    assert doc == expected, f"Expected {expected}, got {doc}"


def test_omit_in_specific_rule(omit_parser_unparser):
    """Test omitting elements only within a specific rule."""
    parser_result = omit_parser_unparser

    # Formatter config that omits semicolons only in assign_stmt rule
    formatter_config_text = """
    rule assign_stmt {
        omit ";";
    }
    """

    formatter_config = parse_format_config(formatter_config_text)
    unparser_result = generate_unparser(
        parser_result.grammar, parser_result.cst_module_name, formatter_config=formatter_config
    )

    # Test assignment statement
    test_input = "x=42;"
    cst, input_text = parse_rule(parser_result, "assign_stmt", test_input)

    doc = unparse_cst(unparser_result, cst, input_text, "assign_stmt")

    # Semicolon should be omitted in assign_stmt
    expected = Concat((Text("x"), Text("="), Text("42")))
    assert doc == expected, f"Expected {expected}, got {doc}"


def test_omit_function_call_syntax(omit_parser_unparser):
    """Test omitting parentheses and commas from function calls."""
    parser_result = omit_parser_unparser

    # Formatter config that omits function call syntax
    formatter_config_text = """
    rule func_call {
        omit "(";
        omit ")";
    }
    rule args {
        omit ",";
    }
    """

    formatter_config = parse_format_config(formatter_config_text)
    unparser_result = generate_unparser(
        parser_result.grammar, parser_result.cst_module_name, formatter_config=formatter_config
    )

    # Test function call with arguments
    test_input = "foo(1,2,3)"
    cst, input_text = parse_rule(parser_result, "func_call", test_input)

    doc = unparse_cst(unparser_result, cst, input_text, "func_call")

    # Parentheses and commas should be omitted
    expected = Concat((Text("foo"), Text("1"), Text("2"), Text("3")))
    assert doc == expected, f"Expected {expected}, got {doc}"


def test_omit_keywords(omit_parser_unparser):
    """Test omitting keywords like 'if' and 'else'."""
    parser_result = omit_parser_unparser

    # Formatter config that omits if/else keywords
    formatter_config_text = """
    rule if_stmt {
        omit "if";
        omit "(";
        omit ")";
    }
    rule else_part {
        omit "else";
    }
    """

    formatter_config = parse_format_config(formatter_config_text)
    unparser_result = generate_unparser(
        parser_result.grammar, parser_result.cst_module_name, formatter_config=formatter_config
    )

    # Test if statement
    test_input = "if(1){x=2;}"
    cst, input_text = parse_rule(parser_result, "if_stmt", test_input)

    doc = unparse_cst(unparser_result, cst, input_text, "if_stmt")

    # 'if' and parentheses should be omitted
    expected = Concat((Text("1"), Text("{"), Text("x"), Text("="), Text("2"), Text(";"), Text("}")))
    assert doc == expected, f"Expected {expected}, got {doc}"


def test_omit_list_syntax(omit_parser_unparser):
    """Test omitting brackets and commas from lists."""
    parser_result = omit_parser_unparser

    # Formatter config that omits list syntax
    formatter_config_text = """
    rule list {
        omit "[";
        omit "]";
    }
    rule items {
        omit ",";
    }
    """

    formatter_config = parse_format_config(formatter_config_text)
    unparser_result = generate_unparser(
        parser_result.grammar, parser_result.cst_module_name, formatter_config=formatter_config
    )

    # Test list
    test_input = "[1,2,3]"
    cst, input_text = parse_rule(parser_result, "list", test_input)

    doc = unparse_cst(unparser_result, cst, input_text, "list")

    # Brackets and commas should be omitted
    expected = Concat((Text("1"), Text("2"), Text("3")))
    assert doc == expected, f"Expected {expected}, got {doc}"


def test_empty_list_with_omit(omit_parser_unparser):
    """Test omitting brackets from an empty list."""
    parser_result = omit_parser_unparser

    # Formatter config that omits list brackets
    formatter_config_text = """
    rule list {
        omit "[";
        omit "]";
    }
    """

    formatter_config = parse_format_config(formatter_config_text)
    unparser_result = generate_unparser(
        parser_result.grammar, parser_result.cst_module_name, formatter_config=formatter_config
    )

    # Test empty list
    test_input = "[]"
    cst, input_text = parse_rule(parser_result, "list", test_input)

    doc = unparse_cst(unparser_result, cst, input_text, "list")

    # Should result in empty output since brackets are omitted and no items
    expected = NIL
    assert doc == expected, f"Expected {expected}, got {doc}"


def test_global_and_rule_omit_interaction(omit_parser_unparser):
    """Test interaction between global and rule-specific omit configurations."""
    parser_result = omit_parser_unparser

    # Formatter config with global and rule-specific omits
    formatter_config_text = """
    omit ",";  // Omit commas globally
    rule func_call {
        omit "(";
        omit ")";
    }
    """

    formatter_config = parse_format_config(formatter_config_text)
    unparser_result = generate_unparser(
        parser_result.grammar, parser_result.cst_module_name, formatter_config=formatter_config
    )

    # Test function call
    test_input = "foo(1,2,3)"
    cst, input_text = parse_rule(parser_result, "func_call", test_input)

    doc = unparse_cst(unparser_result, cst, input_text, "func_call")

    # Both global (comma) and rule-specific (parentheses) omits should apply
    expected = Concat((Text("foo"), Text("1"), Text("2"), Text("3")))
    assert doc == expected, f"Expected {expected}, got {doc}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
