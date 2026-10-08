"""Pytest for the generated unparser."""

import sys
from pathlib import Path
from typing import Any

import pytest

from fltk.fegen.pyrt import terminalsrc
from fltk.plumbing import (
    generate_parser,
    generate_unparser,
    parse_format_config,
    parse_format_config_file,
    parse_grammar,
    parse_grammar_file,
    parse_text,
    render_doc,
    unparse_cst,
)
from fltk.unparse.combinators import LINE, Concat, HardLine, Line, Text, concat
from fltk.unparse.fmt_config import FormatterConfig, TriviaConfig
from fltk.unparse.renderer import RendererConfig
from tests.rust_gate_cases import OPTIONAL_BEFORE_SPEC_FORMATTER, OPTIONAL_BEFORE_SPEC_GRAMMAR


@pytest.fixture
def toy_unparser():
    """Generate parser and unparser for the toy grammar."""
    script_dir = Path(__file__).parent
    grammar_path = script_dir / "toy.fltkg"

    if not grammar_path.exists():
        pytest.fail(f"Grammar file '{grammar_path}' not found")

    with grammar_path.open() as f:
        grammar_content = f.read()

    parser_result = None
    try:
        # Parse grammar and generate parser/unparser using plumbing utilities
        grammar = parse_grammar_file(grammar_path)
        parser_result = generate_parser(grammar, capture_trivia=True)
        unparser_result = generate_unparser(parser_result.grammar, parser_result.cst_module_name)

        yield parser_result, unparser_result, grammar_content

    except Exception as e:
        pytest.fail(f"Failed to generate parser/unparser: {e}")
    finally:
        # Clean up sys.modules
        if parser_result and parser_result.cst_module_name in sys.modules:
            del sys.modules[parser_result.cst_module_name]


def parse_toy_expression(parser_result, input_text: str) -> tuple[Any, str]:
    """Parse input text as a toy expression."""
    parse_result = parse_text(parser_result, input_text, "expr")

    if not parse_result.success:
        pytest.fail(f"Failed to parse toy expression '{input_text}':\n{parse_result.error_message}")

    return parse_result.cst, input_text


def test_toy_grammar_parsing(toy_unparser):
    """Test that the toy grammar can be parsed and unparsed correctly."""
    parser_result, unparser_result, _grammar_content = toy_unparser

    # Test parsing the example toy file
    script_dir = Path(__file__).parent
    toy_path = script_dir / "example.toy"

    if not toy_path.exists():
        pytest.fail(f"Toy file '{toy_path}' not found")

    with toy_path.open() as f:
        example_content = f.read().strip()

    # Parse the example expression
    cst, input_text = parse_toy_expression(parser_result, example_content)

    # Verify CST is not None
    assert cst is not None, "Failed to parse example toy expression"

    # Unparse the CST
    doc = unparse_cst(unparser_result, cst, input_text, "expr")

    # Verify the specific combinator output for the example expression
    expected_doc = Concat(
        (
            Text("1"),
            Text("+"),
            Text("2"),
            Text("*"),
            Text("3"),
            Text("+"),
            Text("("),
            Text("4"),
            Text("+"),
            Text("5"),
            Text("*"),
            Text("6"),
            Text(")"),
        )
    )
    assert doc == expected_doc, f"Expected {expected_doc}, got {doc}"


def test_simple_expressions(toy_unparser):
    """Test parsing and unparsing simple expressions."""
    parser_result, unparser_result, _ = toy_unparser

    test_cases = [
        ("123", Text("123")),
        ("1+2", Concat((Text("1"), Text("+"), Text("2")))),
        ("1*2", Concat((Text("1"), Text("*"), Text("2")))),
        ("(1)", Concat((Text("("), Text("1"), Text(")")))),
        ("1+2*3", Concat((Text("1"), Text("+"), Text("2"), Text("*"), Text("3")))),
        ("(1+2)*3", Concat((Text("("), Text("1"), Text("+"), Text("2"), Text(")"), Text("*"), Text("3")))),
    ]

    for test_input, expected_doc in test_cases:
        # Parse the expression
        cst, input_text = parse_toy_expression(parser_result, test_input)

        # Verify parsing succeeded
        assert cst is not None, f"Failed to parse '{test_input}'"

        # Unparse the CST
        doc = unparse_cst(unparser_result, cst, input_text, "expr")

        # Verify the actual combinator output matches expected
        assert doc == expected_doc, f"For input '{test_input}', expected {expected_doc}, got {doc}"


def test_complex_expression(toy_unparser):
    """Test parsing and unparsing the complex example expression."""
    parser_result, unparser_result, _ = toy_unparser

    # Test the complex expression from example.toy
    complex_expr = "1+2*3+(4+5*6)"
    expected_doc = Concat(
        (
            Text("1"),
            Text("+"),
            Text("2"),
            Text("*"),
            Text("3"),
            Text("+"),
            Text("("),
            Text("4"),
            Text("+"),
            Text("5"),
            Text("*"),
            Text("6"),
            Text(")"),
        )
    )

    # Parse the expression
    cst, input_text = parse_toy_expression(parser_result, complex_expr)

    # Verify parsing succeeded
    assert cst is not None, f"Failed to parse complex expression '{complex_expr}'"

    # Unparse the CST
    doc = unparse_cst(unparser_result, cst, input_text, "expr")

    # Verify the actual combinator output matches expected
    assert doc == expected_doc, f"For complex expression '{complex_expr}', expected {expected_doc}, got {doc}"


def test_star_quantifier_zero_times(toy_unparser):
    """Test star quantifier with zero occurrences."""
    parser_result, unparser_result, _ = toy_unparser

    # Single number with no operators - tests * quantifier with zero matches
    test_input = "42"
    expected_doc = Text("42")

    cst, input_text = parse_toy_expression(parser_result, test_input)
    assert cst is not None, f"Failed to parse '{test_input}'"

    doc = unparse_cst(unparser_result, cst, input_text, "expr")
    assert doc == expected_doc, f"Expected {expected_doc}, got {doc}"


def test_star_quantifier_multiple_times(toy_unparser):
    """Test star quantifier with multiple occurrences."""
    parser_result, unparser_result, _ = toy_unparser

    # Multiple additions - tests * quantifier with multiple matches
    test_input = "1+2+3+4"
    expected_doc = Concat((Text("1"), Text("+"), Text("2"), Text("+"), Text("3"), Text("+"), Text("4")))

    cst, input_text = parse_toy_expression(parser_result, test_input)
    assert cst is not None, f"Failed to parse '{test_input}'"

    doc = unparse_cst(unparser_result, cst, input_text, "expr")
    assert doc == expected_doc, f"Expected {expected_doc}, got {doc}"


def test_nested_star_quantifiers(toy_unparser):
    """Test nested star quantifiers in terms and factors."""
    parser_result, unparser_result, _ = toy_unparser

    # Multiple multiplications within multiple additions
    test_input = "1*2*3+4*5*6"
    expected_doc = Concat(
        (
            Text("1"),
            Text("*"),
            Text("2"),
            Text("*"),
            Text("3"),
            Text("+"),
            Text("4"),
            Text("*"),
            Text("5"),
            Text("*"),
            Text("6"),
        )
    )

    cst, input_text = parse_toy_expression(parser_result, test_input)
    assert cst is not None, f"Failed to parse '{test_input}'"

    doc = unparse_cst(unparser_result, cst, input_text, "expr")
    assert doc == expected_doc, f"Expected {expected_doc}, got {doc}"


# Test grammar with + and ? quantifiers that toy grammar doesn't have
TEST_GRAMMAR_WITH_QUANTIFIERS = """
plus_test := item:"x"+;
optional_test := prefix:"[" , item:"y"? , suffix:"]";
mixed_quantifiers := required:"a" , optional:"b"? , multiple:"c"+;
no_ws_sep := first:"a" . second:"b" . third:"c";
ws_allowed_sep := first:"a" , second:"b" , third:"c";
ws_required_sep := first:"a" : second:"b" : third:"c";
suppress_test := keep:"a" , %"b" , keep2:"c";
include_test := item:$"x";
suppress_plus := prefix:"[" , %"x"+ , suffix:"]";
suppress_optional := prefix:"[" , %"y"? , suffix:"]";
suppress_star := prefix:"[" , %"z"* , suffix:"]";
suppress_regex_optional := prefix:"[" , %/[0-9]+/? , suffix:"]";
suppress_rule_optional := prefix:"[" , %plus_test? , suffix:"]";
"""

# Bad grammars that should fail at generation time
BAD_GRAMMAR_SUPPRESS_REGEX_REQUIRED = """
suppress_regex_required := prefix:"[" , %/[0-9]+/ , suffix:"]";
"""

BAD_GRAMMAR_SUPPRESS_RULE_REQUIRED = """
plus_test := item:"x"+;
suppress_rule_required := prefix:"[" , %plus_test , suffix:"]";
"""


@pytest.fixture
def quantifier_unparser():
    """Generate parser and unparser for quantifier test grammar."""
    parser_result = None
    try:
        # Parse grammar and generate parser/unparser using plumbing utilities
        grammar = parse_grammar(TEST_GRAMMAR_WITH_QUANTIFIERS)
        parser_result = generate_parser(grammar, capture_trivia=True)
        unparser_result = generate_unparser(parser_result.grammar, parser_result.cst_module_name)

        yield parser_result, unparser_result

    except Exception as e:
        pytest.fail(f"Failed to generate parser/unparser: {e}")
    finally:
        # Clean up sys.modules
        if parser_result and parser_result.cst_module_name in sys.modules:
            del sys.modules[parser_result.cst_module_name]


def parse_quantifier_rule(parser_result, rule_name: str, input_text: str) -> tuple[Any | None, str]:
    """Parse input text using specified quantifier rule."""
    parse_result = parse_text(parser_result, input_text, rule_name)

    if parse_result.success:
        return parse_result.cst, input_text
    return None, input_text


def test_plus_quantifier_one_item(quantifier_unparser):
    """Test + quantifier with exactly one item."""
    parser_result, unparser_result = quantifier_unparser

    cst, input_text = parse_quantifier_rule(parser_result, "plus_test", "x")
    assert cst is not None, "Failed to parse 'x'"

    doc = unparse_cst(unparser_result, cst, input_text, "plus_test")
    assert doc == Text("x"), f"Expected Text('x'), got {doc}"


def test_plus_quantifier_multiple_items(quantifier_unparser):
    """Test + quantifier with multiple items."""
    parser_result, unparser_result = quantifier_unparser

    cst, input_text = parse_quantifier_rule(parser_result, "plus_test", "xxx")
    assert cst is not None, "Failed to parse 'xxx'"

    doc = unparse_cst(unparser_result, cst, input_text, "plus_test")
    expected = Concat((Text("x"), Text("x"), Text("x")))
    assert doc == expected, f"Expected {expected}, got {doc}"


def test_optional_quantifier_present(quantifier_unparser):
    """Test ? quantifier when optional item is present."""
    parser_result, unparser_result = quantifier_unparser

    cst, input_text = parse_quantifier_rule(parser_result, "optional_test", "[y]")
    assert cst is not None, "Failed to parse '[y]'"

    doc = unparse_cst(unparser_result, cst, input_text, "optional_test")
    expected = Concat((Text("["), Text("y"), Text("]")))
    assert doc == expected, f"Expected {expected}, got {doc}"


def test_optional_quantifier_absent(quantifier_unparser):
    """Test ? quantifier when optional item is absent."""
    parser_result, unparser_result = quantifier_unparser

    cst, input_text = parse_quantifier_rule(parser_result, "optional_test", "[]")
    assert cst is not None, "Failed to parse '[]'"

    doc = unparse_cst(unparser_result, cst, input_text, "optional_test")
    expected = Concat((Text("["), Text("]")))
    assert doc == expected, f"Expected {expected}, got {doc}"


def test_mixed_quantifiers(quantifier_unparser):
    """Test grammar with mixed quantifiers."""
    parser_result, unparser_result = quantifier_unparser

    cst, input_text = parse_quantifier_rule(parser_result, "mixed_quantifiers", "abccc")
    assert cst is not None, "Failed to parse 'abccc'"

    doc = unparse_cst(unparser_result, cst, input_text, "mixed_quantifiers")
    expected = Concat((Text("a"), Text("b"), Text("c"), Text("c"), Text("c")))
    assert doc == expected, f"Expected {expected}, got {doc}"


def test_no_ws_separator(quantifier_unparser):
    """Test . separator (no whitespace allowed)."""
    parser_result, unparser_result = quantifier_unparser

    cst, input_text = parse_quantifier_rule(parser_result, "no_ws_sep", "abc")
    assert cst is not None, "Failed to parse 'abc'"

    doc = unparse_cst(unparser_result, cst, input_text, "no_ws_sep")
    expected = Concat((Text("a"), Text("b"), Text("c")))
    assert doc == expected, f"Expected {expected}, got {doc}"


def test_ws_allowed_separator(quantifier_unparser):
    """Test , separator (whitespace allowed)."""
    parser_result, unparser_result = quantifier_unparser

    cst, input_text = parse_quantifier_rule(parser_result, "ws_allowed_sep", "a b c")
    assert cst is not None, "Failed to parse 'a b c'"

    doc = unparse_cst(unparser_result, cst, input_text, "ws_allowed_sep")
    expected = Concat((Text("a"), Text("b"), Text("c")))
    assert doc == expected, f"Expected {expected}, got {doc}"


def test_ws_required_separator(quantifier_unparser):
    """Test : separator (whitespace required)."""
    parser_result, unparser_result = quantifier_unparser

    cst, input_text = parse_quantifier_rule(parser_result, "ws_required_sep", "a b c")
    assert cst is not None, "Failed to parse 'a b c'"

    doc = unparse_cst(unparser_result, cst, input_text, "ws_required_sep")
    expected = Concat((Text("a"), Line(), Text("b"), Line(), Text("c")))
    assert doc == expected, f"Expected {expected}, got {doc}"


def test_suppress_disposition(quantifier_unparser):
    """Test % disposition (suppress from CST but still needed for reparsing)."""
    parser_result, unparser_result = quantifier_unparser

    cst, input_text = parse_quantifier_rule(parser_result, "suppress_test", "abc")
    assert cst is not None, "Failed to parse 'abc'"

    doc = unparse_cst(unparser_result, cst, input_text, "suppress_test")
    # Should have all "a", "b", "c" even though "b" is suppressed from CST
    # because "b" is required for the grammar to parse correctly
    expected = Concat((Text("a"), Text("b"), Text("c")))
    assert doc == expected, f"Expected {expected}, got {doc}"


def test_include_disposition(quantifier_unparser):
    """Test $ disposition (explicitly include)."""
    parser_result, unparser_result = quantifier_unparser

    cst, input_text = parse_quantifier_rule(parser_result, "include_test", "x")
    assert cst is not None, "Failed to parse 'x'"

    doc = unparse_cst(unparser_result, cst, input_text, "include_test")
    expected = Text("x")
    assert doc == expected, f"Expected {expected}, got {doc}"


def test_suppress_plus_quantifier(quantifier_unparser):
    """Test suppressed + quantifier - should output minimum required (1 occurrence)."""
    parser_result, unparser_result = quantifier_unparser

    cst, input_text = parse_quantifier_rule(parser_result, "suppress_plus", "[xxx]")
    assert cst is not None, "Failed to parse '[xxx]'"

    doc = unparse_cst(unparser_result, cst, input_text, "suppress_plus")
    # Should include brackets and exactly one x (minimum for + quantifier)
    # even though original had multiple x's, since they're suppressed from CST
    expected = Concat((Text("["), Text("x"), Text("]")))
    assert doc == expected, f"Expected {expected}, got {doc}"


def test_suppress_optional_quantifier_present(quantifier_unparser):
    """Test suppressed ? quantifier when optional item is present."""
    parser_result, unparser_result = quantifier_unparser

    cst, input_text = parse_quantifier_rule(parser_result, "suppress_optional", "[y]")
    assert cst is not None, "Failed to parse '[y]'"

    doc = unparse_cst(unparser_result, cst, input_text, "suppress_optional")
    # Should just have brackets since y? is optional and suppressed (0 occurrences)
    expected = Concat((Text("["), Text("]")))
    assert doc == expected, f"Expected {expected}, got {doc}"


def test_suppress_optional_quantifier_absent(quantifier_unparser):
    """Test suppressed ? quantifier when optional item is absent."""
    parser_result, unparser_result = quantifier_unparser

    cst, input_text = parse_quantifier_rule(parser_result, "suppress_optional", "[]")
    assert cst is not None, "Failed to parse '[]'"

    doc = unparse_cst(unparser_result, cst, input_text, "suppress_optional")
    # Should just have brackets since optional item generates 0 occurrences
    expected = Concat((Text("["), Text("]")))
    assert doc == expected, f"Expected {expected}, got {doc}"


def test_suppress_star_quantifier_zero(quantifier_unparser):
    """Test suppressed * quantifier with zero occurrences."""
    parser_result, unparser_result = quantifier_unparser

    cst, input_text = parse_quantifier_rule(parser_result, "suppress_star", "[]")
    assert cst is not None, "Failed to parse '[]'"

    doc = unparse_cst(unparser_result, cst, input_text, "suppress_star")
    # Should just have brackets since z* is optional and suppressed (0 occurrences)
    expected = Concat((Text("["), Text("]")))
    assert doc == expected, f"Expected {expected}, got {doc}"


def test_suppress_star_quantifier_multiple(quantifier_unparser):
    """Test suppressed * quantifier with multiple occurrences."""
    parser_result, unparser_result = quantifier_unparser

    cst, input_text = parse_quantifier_rule(parser_result, "suppress_star", "[zzz]")
    assert cst is not None, "Failed to parse '[zzz]'"

    doc = unparse_cst(unparser_result, cst, input_text, "suppress_star")
    # Should just have brackets since z* is optional and suppressed (0 occurrences)
    expected = Concat((Text("["), Text("]")))
    assert doc == expected, f"Expected {expected}, got {doc}"


def test_suppress_regex_optional(quantifier_unparser):
    """Test suppressed optional regex - should succeed by omitting it."""
    parser_result, unparser_result = quantifier_unparser

    cst, input_text = parse_quantifier_rule(parser_result, "suppress_regex_optional", "[123]")
    assert cst is not None, "Failed to parse '[123]'"

    doc = unparse_cst(unparser_result, cst, input_text, "suppress_regex_optional")
    # Should just have brackets since regex is optional and suppressed
    expected = Concat((Text("["), Text("]")))
    assert doc == expected, f"Expected {expected}, got {doc}"


def test_suppress_rule_optional(quantifier_unparser):
    """Test suppressed optional rule reference - should succeed by omitting it."""
    parser_result, unparser_result = quantifier_unparser

    cst, input_text = parse_quantifier_rule(parser_result, "suppress_rule_optional", "[xxx]")
    assert cst is not None, "Failed to parse '[xxx]'"

    doc = unparse_cst(unparser_result, cst, input_text, "suppress_rule_optional")
    # Should just have brackets since rule reference is optional and suppressed
    expected = Concat((Text("["), Text("]")))
    assert doc == expected, f"Expected {expected}, got {doc}"


def test_suppress_regex_required_fails_generation():
    """Test that grammars with required suppressed regex fail at generation time."""
    grammar = parse_grammar(BAD_GRAMMAR_SUPPRESS_REGEX_REQUIRED)
    parser_result = generate_parser(grammar, capture_trivia=True)

    # This should raise an exception during unparser generation
    with pytest.raises((RuntimeError, ValueError, AssertionError)) as exc_info:
        generate_unparser(parser_result.grammar, parser_result.cst_module_name)

    # Should mention that required suppressed non-literals are not allowed
    assert "suppress" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()


def test_suppress_rule_required_fails_generation():
    """Test that grammars with required suppressed rule references fail at generation time."""
    grammar = parse_grammar(BAD_GRAMMAR_SUPPRESS_RULE_REQUIRED)
    parser_result = generate_parser(grammar, capture_trivia=True)

    # This should raise an exception during unparser generation
    with pytest.raises((RuntimeError, ValueError, AssertionError)) as exc_info:
        generate_unparser(parser_result.grammar, parser_result.cst_module_name)

    # Should mention that required suppressed non-literals are not allowed
    assert "suppress" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()


# Test cases for comment preservation
COMMENT_PRESERVATION_GRAMMAR = """
expr := term , ("+" , term)*;
term := factor , ("*" , factor)*;
factor := number | "(" , expr , ")";
number := value:/[0-9]+/;
_trivia := (whitespace | line_comment | block_comment)+;
whitespace := content:/\\s+/;
line_comment := prefix:"//" . content:/[^\\n]*/ . newline:"\\n";
block_comment := start:"/*" , content:/[^*]*(?:\\*(?!\\/)[^*]*)*/ , end:"*/";
"""

COMMENT_PRESERVATION_EXPRESSION = """1 + 2 // This is a comment
"""


@pytest.fixture
def comment_unparser():
    """Generate parser and unparser for grammar with comments."""
    parser_result = None
    try:
        # Parse grammar and generate parser/unparser using plumbing utilities
        grammar = parse_grammar(COMMENT_PRESERVATION_GRAMMAR)
        parser_result = generate_parser(grammar, capture_trivia=True)

        # Configure to preserve LineComment and BlockComment but not Whitespace
        trivia_config = TriviaConfig(preserve_node_names={"LineComment", "BlockComment"})
        formatter_config = FormatterConfig()
        formatter_config.trivia_config = trivia_config

        unparser_result = generate_unparser(
            parser_result.grammar, parser_result.cst_module_name, formatter_config=formatter_config
        )

        yield parser_result, unparser_result

    except Exception as e:
        pytest.fail(f"Failed to generate parser/unparser: {e}")
    finally:
        # Clean up sys.modules
        if parser_result and parser_result.cst_module_name in sys.modules:
            del sys.modules[parser_result.cst_module_name]


def test_line_comment_preservation(comment_unparser):
    """Test that line comments are preserved in the output."""
    parser_result, unparser_result = comment_unparser

    # Parse expression with line comments
    test_input = "1 + 2 // This is a comment\n"
    parse_result = parse_text(parser_result, test_input, "expr")

    assert parse_result.success, "Failed to parse expression with comment"

    # Unparse the expression
    doc = unparse_cst(unparser_result, parse_result.cst, test_input, "expr")

    # We expect the comment to be preserved in the output
    # The comment is now structured as separate parts from unparse__trivia
    expected_with_comment = Concat(
        (Text("1"), Text("+"), Text("2"), Text(" "), Text("//"), Text(" This is a comment"), HardLine())
    )

    assert doc == expected_with_comment, f"Comment was not preserved. Expected {expected_with_comment}, got {doc}"


def test_block_comment_preservation(comment_unparser):
    """Test that block comments are preserved in the output."""
    parser_result, unparser_result = comment_unparser

    # Parse expression with block comment
    test_input = "1 /* block comment 1 */ + /* block comment 2 */ 2"
    parse_result = parse_text(parser_result, test_input, "expr")

    assert parse_result.success, "Failed to parse expression with block comment"

    # Unparse the expression
    doc = unparse_cst(unparser_result, parse_result.cst, test_input, "expr")

    # We expect the comment to be preserved in the output
    # The comment is now structured as separate parts from unparse__trivia
    expected_with_comment = Concat(
        (
            Text("1"),
            Text(" "),
            Text("/*"),
            Text("block comment 1 "),
            Text("*/"),
            Text(" "),
            Text("+"),
            Text(" "),
            Text("/*"),
            Text("block comment 2 "),
            Text("*/"),
            Text(" "),
            Text("2"),
        )
    )

    assert doc == expected_with_comment, f"Comment was not preserved. Expected {expected_with_comment}, got {doc}"


def test_whitespace_not_preserved_by_default(comment_unparser):
    """Test that whitespace is not preserved (replaced with minimal whitespace)."""
    parser_result, unparser_result = comment_unparser

    # Parse expression with extra whitespace
    test_input = "1    +    2"
    parse_result = parse_text(parser_result, test_input, "expr")

    assert parse_result.success, "Failed to parse expression with whitespace"

    # Unparse the expression
    doc = unparse_cst(unparser_result, parse_result.cst, test_input, "expr")

    # This test SHOULD PASS - whitespace should be collapsed to minimal
    # We expect extra whitespace to be replaced with minimal whitespace
    expected_doc = Concat((Text("1"), Text("+"), Text("2")))
    assert doc == expected_doc, f"Expected minimal whitespace combinator, got: {doc}"


# Grammar for the preserved-trivia-None diagnostic (site 1 of unparser-none-path-diagnostics).
_PRESERVED_TRIVIA_NONE_GRAMMAR = """
doc := a:"a" , b:"b";
_trivia := (whitespace | comment)+;
whitespace := content:/\\s+/;
comment := prefix:"#" . content:/[^\\n]*/;
"""


def test_preserved_trivia_unparse_none_raises():
    """A confirmed-preservable comment whose unparse__trivia returns None halts with a ValueError.

    Site 1 of unparser-none-path-diagnostics: ``_has_preservable_trivia`` sees the ``Comment``
    child and returns True, but the ``Comment`` node has no children so ``unparse_comment`` (and
    therefore ``unparse__trivia``) returns None. Rather than silently dropping the comment from
    the output, the generated Python unparser must raise (parity with the Rust backend's panic).
    """
    parser_result = None
    try:
        grammar = parse_grammar(_PRESERVED_TRIVIA_NONE_GRAMMAR)
        parser_result = generate_parser(grammar, capture_trivia=True)
        formatter_config = FormatterConfig()
        formatter_config.trivia_config = TriviaConfig(preserve_node_names={"Comment"})
        unparser_result = generate_unparser(
            parser_result.grammar, parser_result.cst_module_name, formatter_config=formatter_config
        )
        mod = sys.modules[parser_result.cst_module_name]

        # A Trivia node carrying an empty (childless) Comment: preservable per
        # _has_preservable_trivia, but unparse_comment returns None (its required prefix child
        # is missing), so unparse__trivia returns None.
        comment = mod.Comment()
        trivia = mod.Trivia()
        trivia.append_comment(comment)
        doc = mod.Doc()
        doc.append_a(terminalsrc.Span(0, 1))
        doc.append(trivia, None)
        doc.append_b(terminalsrc.Span(4, 5))

        with pytest.raises(ValueError, match="refusing to silently drop comments") as exc_info:
            unparse_cst(unparser_result, doc, "a #\nb", "doc")
        msg = str(exc_info.value)
        assert "'doc'" in msg
        assert "child position 1" in msg
    finally:
        if parser_result and parser_result.cst_module_name in sys.modules:
            del sys.modules[parser_result.cst_module_name]


# Test trivia unparsing with simple whitespace trivia
SIMPLE_TRIVIA_GRAMMAR = """
statement := first:"hello" , second:"world";
_trivia := whitespace+;
whitespace := content:/\\s+/;
"""


@pytest.fixture
def simple_trivia_unparser():
    """Generate parser and unparser for simple trivia grammar."""
    parser_result = None
    try:
        # Parse grammar and generate parser/unparser with trivia capture
        grammar = parse_grammar(SIMPLE_TRIVIA_GRAMMAR)
        parser_result = generate_parser(grammar, capture_trivia=True)

        trivia_config = TriviaConfig(preserve_node_names=None)
        formatter_config = FormatterConfig()
        formatter_config.trivia_config = trivia_config

        unparser_result = generate_unparser(
            parser_result.grammar, parser_result.cst_module_name, formatter_config=formatter_config
        )

        yield parser_result, unparser_result

    except Exception as e:
        pytest.fail(f"Failed to generate parser/unparser: {e}")
    finally:
        # Clean up sys.modules
        if parser_result and parser_result.cst_module_name in sys.modules:
            del sys.modules[parser_result.cst_module_name]


def test_simple_trivia_unparsing(simple_trivia_unparser):
    """Test that simple whitespace trivia is properly unparsed."""
    parser_result, unparser_result = simple_trivia_unparser

    # Test with various amounts of whitespace
    test_input = "hello    world"
    parse_result = parse_text(parser_result, test_input, "statement")

    assert parse_result.success, "Failed to parse statement with whitespace"

    # Unparse the statement
    doc = unparse_cst(unparser_result, parse_result.cst, test_input, "statement")

    # With preserve_all=True, we expect the exact whitespace to be preserved
    expected = Concat((Text("hello"), Text("    "), Text("world")))
    assert doc == expected, f"Whitespace trivia not preserved. Expected {expected}, got {doc}"


def test_trivia_with_newlines(simple_trivia_unparser):
    """Test that trivia with newlines is properly unparsed."""
    parser_result, unparser_result = simple_trivia_unparser

    # Test with newline and spaces
    test_input = "hello\n  world"
    parse_result = parse_text(parser_result, test_input, "statement")

    assert parse_result.success, "Failed to parse statement with newline"

    # Unparse the statement
    doc = unparse_cst(unparser_result, parse_result.cst, test_input, "statement")

    # With preserve_all=True, we expect the exact whitespace to be preserved
    expected = Concat((Text("hello"), Text("\n  "), Text("world")))
    assert doc == expected, f"Newline trivia not preserved. Expected {expected}, got {doc}"


def test_trivia_with_tabs(simple_trivia_unparser):
    """Test that trivia with tabs is properly unparsed."""
    parser_result, unparser_result = simple_trivia_unparser

    # Test with tabs
    test_input = "hello\t\tworld"
    parse_result = parse_text(parser_result, test_input, "statement")

    assert parse_result.success, "Failed to parse statement with tabs"

    # Unparse the statement
    doc = unparse_cst(unparser_result, parse_result.cst, test_input, "statement")

    # With preserve_all=True, we expect the exact whitespace to be preserved
    expected = Concat((Text("hello"), Text("\t\t"), Text("world")))
    assert doc == expected, f"Tab trivia not preserved. Expected {expected}, got {doc}"


def test_trivia_rule_with_separators():
    """Test trivia rules with whitespace separators."""
    grammar_with_separator_in_trivia = """
    statement := first:"hello" , second:"world";
    _trivia := (line | line? : | block)+;
    line := prefix:"//" . content:/[^\\n]*/ . newline:"\\n";
    block := start:"/*" , content:/[^*]*(?:\\*(?!\\/)[^*]*)*/ , end:"*/";
    """

    grammar = parse_grammar(grammar_with_separator_in_trivia)
    parser_result = generate_parser(grammar, capture_trivia=True)
    try:
        trivia_config = TriviaConfig(preserve_node_names={"Line", "Block"})
        formatter_config = FormatterConfig()
        formatter_config.trivia_config = trivia_config

        unparser_result = generate_unparser(
            parser_result.grammar, parser_result.cst_module_name, formatter_config=formatter_config
        )

        test_input = "hello /* hi */ world"
        parse_result = parse_text(parser_result, test_input, "statement")
        assert parse_result.success, "Failed to parse statement"
        doc = unparse_cst(unparser_result, parse_result.cst, test_input, "statement")
        assert doc == concat([Text("hello"), LINE, Text("/*"), Text("hi "), Text("*/"), LINE, Text("world")])
    finally:
        if parser_result.cst_module_name in sys.modules:
            del sys.modules[parser_result.cst_module_name]


def test_inline_comment_stays_on_same_line():
    """Test that inline comments stay on the same line as the code they comment.

    Bug: Comments were being moved to a separate line before the code they comment.
    Fix: Added `ws_required: nbsp` for the `_trivia` rule in format config.
    """
    # Use the real fegen grammar and format config for a realistic test
    script_dir = Path(__file__).parent.parent / "fegen"
    grammar = parse_grammar_file(script_dir / "fegen.fltkg")
    parser_result = generate_parser(grammar, capture_trivia=True)
    try:
        fmt_config = parse_format_config_file(script_dir / "fegen.fltkfmt")
        unparser_result = generate_unparser(
            parser_result.grammar, parser_result.cst_module_name, formatter_config=fmt_config
        )

        # Input with inline comment - similar to the real bug case
        test_input = 'r := a:"x" // comment\n    | b:"y" ;\n'
        parse_result = parse_text(parser_result, test_input, "grammar")
        assert parse_result.success, f"Failed to parse: {parse_result.error_message}"

        doc = unparse_cst(unparser_result, parse_result.cst, test_input, "grammar")
        output = render_doc(doc, RendererConfig(max_width=80))

        # The comment should stay on the same line as a:"x"
        assert ':"x" // comment' in output, f"Comment should stay inline. Got:\n{output}"
        # The comment should NOT be on a line by itself before the code
        lines = output.strip().split("\n")
        for i, line in enumerate(lines):
            if line.strip().startswith("//"):
                # If a line starts with //, the previous line should not end with just the item
                if i > 0:
                    assert ':"x"' not in lines[i - 1] or "//" in lines[i - 1], (
                        f"Comment on line {i} appears to be separated from code. Got:\n{output}"
                    )

    finally:
        if parser_result.cst_module_name in sys.modules:
            del sys.modules[parser_result.cst_module_name]


def test_no_blank_lines_between_alternatives_with_comments():
    """Test that there are no extra blank lines when alternatives have inline comments.

    Bug: When an alternative had an inline comment, a blank line appeared before the
    closing paren because HardLine (from comment's newline) + Line (from before ")")
    produced two newlines.
    Fix: Added post-processing to collapse HardLine + Line/SoftLine sequences.
    """
    # Use the real fegen grammar and format config for a realistic test
    script_dir = Path(__file__).parent.parent / "fegen"
    grammar = parse_grammar_file(script_dir / "fegen.fltkg")
    parser_result = generate_parser(grammar, capture_trivia=True)
    try:
        fmt_config = parse_format_config_file(script_dir / "fegen.fltkfmt")
        unparser_result = generate_unparser(
            parser_result.grammar, parser_result.cst_module_name, formatter_config=fmt_config
        )

        # Input that triggers the bug: alternatives in parens with comments
        # Needs to be long enough to force line breaking at narrow widths
        # The last comment's newline (HardLine) + before ")" (Line) caused blank line
        test_input = """spacing := (
    nil:"nil" // No space
    | nbsp:"nbsp" // Non-Breaking space (always space)
    | bsp:"bsp" // Breaking space (turns into either space or newline)
  ) ;
"""
        parse_result = parse_text(parser_result, test_input, "grammar")
        assert parse_result.success, f"Failed to parse: {parse_result.error_message}"

        doc = unparse_cst(unparser_result, parse_result.cst, test_input, "grammar")
        # Use width 40 which forces line breaking and triggers the bug
        output = render_doc(doc, RendererConfig(max_width=40))

        # Check for blank lines (lines that are empty or whitespace-only)
        lines = output.split("\n")
        for i, line in enumerate(lines):
            assert line.strip() != "" or i == len(lines) - 1, f"Found blank line at position {i} in output:\n{output}"

    finally:
        if parser_result.cst_module_name in sys.modules:
            del sys.modules[parser_result.cst_module_name]


def test_comment_between_rules_stays_with_following_rule():
    """Test that a comment on its own line between rules stays associated with the following rule.

    Bug: Comments that appear on their own line between two rules were being associated
    with the preceding rule (as trailing trivia) instead of the following rule (as leading
    trivia). This caused the comment to appear at the end of the previous rule's line
    after formatting.

    Example input:
        rule1 := "a" ;

        // This comment describes rule2
        rule2 := "b" ;

    Expected output (comment stays before rule2):
        rule1 := "a" ;
        // This comment describes rule2
        rule2 := "b" ;

    Bug output (comment moved to end of rule1):
        rule1 := "a" ; // This comment describes rule2
        rule2 := "b" ;
    """
    script_dir = Path(__file__).parent.parent / "fegen"
    grammar = parse_grammar_file(script_dir / "fegen.fltkg")
    parser_result = generate_parser(grammar, capture_trivia=True)
    try:
        fmt_config = parse_format_config_file(script_dir / "fegen.fltkfmt")
        unparser_result = generate_unparser(
            parser_result.grammar, parser_result.cst_module_name, formatter_config=fmt_config
        )

        # Input with a comment on its own line between two rules
        test_input = """rule1 := "a" ;

// This comment describes rule2
rule2 := "b" ;
"""
        parse_result = parse_text(parser_result, test_input, "grammar")
        assert parse_result.success, f"Failed to parse: {parse_result.error_message}"

        doc = unparse_cst(unparser_result, parse_result.cst, test_input, "grammar")
        output = render_doc(doc, RendererConfig(max_width=80))

        # The comment should appear on its own line before rule2, not at the end of rule1
        lines = output.strip().split("\n")

        # Find the line with the comment
        comment_line_idx = None
        for i, line in enumerate(lines):
            if "// This comment describes rule2" in line:
                comment_line_idx = i
                break

        assert comment_line_idx is not None, f"Comment not found in output:\n{output}"

        # The comment should be on its own line, not at the end of rule1
        comment_line = lines[comment_line_idx]
        assert comment_line.strip().startswith("//"), (
            f"Comment should be at the start of its line, not trailing. Got:\n{output}"
        )

        # The comment line should NOT contain rule1's content
        assert "rule1" not in comment_line and '"a"' not in comment_line, (
            f"Comment should not be on the same line as rule1. Got:\n{output}"
        )

        # The line after the comment should be rule2
        if comment_line_idx + 1 < len(lines):
            next_line = lines[comment_line_idx + 1]
            assert "rule2" in next_line, f"rule2 should follow the comment. Got:\n{output}"

    finally:
        if parser_result.cst_module_name in sys.modules:
            del sys.modules[parser_result.cst_module_name]


# Tests for preserve_blanks feature
# These tests verify blank line preservation and normalization


def test_preserve_blanks_default_collapses_blanks():
    """Test that by default (no preserve_blanks directive), blank lines are collapsed.

    When preserve_blanks is not configured (default 0), multiple newlines in the source
    should not result in blank lines in the output - they get replaced with configured spacing.
    """
    script_dir = Path(__file__).parent.parent / "fegen"
    grammar = parse_grammar_file(script_dir / "fegen.fltkg")
    parser_result = generate_parser(grammar, capture_trivia=True)
    try:
        # Use a format config WITHOUT preserve_blanks to test default behavior
        fmt_config = parse_format_config("""
trivia_preserve: LineComment, BlockComment;
ws_allowed: nil;
ws_required: bsp;
after ";" { hard; }
""")
        unparser_result = generate_unparser(
            parser_result.grammar, parser_result.cst_module_name, formatter_config=fmt_config
        )

        # Input with blank lines between rules
        test_input = """rule1 := "a" ;


rule2 := "b" ;
"""
        parse_result = parse_text(parser_result, test_input, "grammar")
        assert parse_result.success, f"Failed to parse: {parse_result.error_message}"

        doc = unparse_cst(unparser_result, parse_result.cst, test_input, "grammar")
        output = render_doc(doc, RendererConfig(max_width=80))

        # Count blank lines in output
        lines = output.strip().split("\n")
        blank_count = sum(1 for line in lines if line.strip() == "")

        # With default (preserve_blanks: 0), blank lines should be collapsed
        # The exact behavior depends on ws_required setting, but there shouldn't be
        # the original blank line preserved
        assert blank_count == 0, f"Expected no blank lines with default config, got {blank_count}:\n{output}"

    finally:
        if parser_result.cst_module_name in sys.modules:
            del sys.modules[parser_result.cst_module_name]


def test_preserve_blanks_one_normalizes_to_single_blank():
    """Test that preserve_blanks: 1 normalizes multiple blanks to exactly 1.

    When preserve_blanks is 1, any number of blank lines (2+ newlines) in the source
    should become exactly 1 blank line in the output.
    """
    script_dir = Path(__file__).parent.parent / "fegen"
    grammar = parse_grammar_file(script_dir / "fegen.fltkg")
    parser_result = generate_parser(grammar, capture_trivia=True)
    try:
        fmt_config = parse_format_config_file(script_dir / "fegen.fltkfmt")
        assert fmt_config.trivia_config is not None
        # Set preserve_blanks to 1
        fmt_config.trivia_config.preserve_blanks = 1

        unparser_result = generate_unparser(
            parser_result.grammar, parser_result.cst_module_name, formatter_config=fmt_config
        )

        # Input with multiple blank lines between rules
        test_input = """rule1 := "a" ;



rule2 := "b" ;
"""
        parse_result = parse_text(parser_result, test_input, "grammar")
        assert parse_result.success, f"Failed to parse: {parse_result.error_message}"

        doc = unparse_cst(unparser_result, parse_result.cst, test_input, "grammar")
        output = render_doc(doc, RendererConfig(max_width=80))

        # Count blank lines in output
        lines = output.strip().split("\n")
        blank_count = sum(1 for line in lines if line.strip() == "")

        # With preserve_blanks: 1, should have exactly 1 blank line
        assert blank_count == 1, f"Expected exactly 1 blank line with preserve_blanks: 1, got {blank_count}:\n{output}"

    finally:
        if parser_result.cst_module_name in sys.modules:
            del sys.modules[parser_result.cst_module_name]


def test_preserve_blanks_no_source_blanks_no_output_blanks():
    """Test that preserve_blanks doesn't ADD blanks where none exist in source.

    When preserve_blanks is 1 but source has no blank lines (only single newlines),
    the output should not have blank lines added.
    """
    script_dir = Path(__file__).parent.parent / "fegen"
    grammar = parse_grammar_file(script_dir / "fegen.fltkg")
    parser_result = generate_parser(grammar, capture_trivia=True)
    try:
        fmt_config = parse_format_config_file(script_dir / "fegen.fltkfmt")
        assert fmt_config.trivia_config is not None
        # Set preserve_blanks to 1
        fmt_config.trivia_config.preserve_blanks = 1

        unparser_result = generate_unparser(
            parser_result.grammar, parser_result.cst_module_name, formatter_config=fmt_config
        )

        # Input with NO blank lines - just single newlines
        test_input = """rule1 := "a" ;
rule2 := "b" ;
"""
        parse_result = parse_text(parser_result, test_input, "grammar")
        assert parse_result.success, f"Failed to parse: {parse_result.error_message}"

        doc = unparse_cst(unparser_result, parse_result.cst, test_input, "grammar")
        output = render_doc(doc, RendererConfig(max_width=80))

        # Count blank lines in output
        lines = output.strip().split("\n")
        blank_count = sum(1 for line in lines if line.strip() == "")

        # With no source blanks, should have no output blanks (preserve_blanks doesn't add)
        assert blank_count == 0, f"Expected no blank lines when source has none, got {blank_count}:\n{output}"

    finally:
        if parser_result.cst_module_name in sys.modules:
            del sys.modules[parser_result.cst_module_name]


def test_preserve_blanks_two_caps_at_two_blanks():
    """preserve_blanks: 2 caps the source blank count at 2 rather than inflating to exactly 2.

    One source blank line stays one; three source blank lines come out as two.
    """
    script_dir = Path(__file__).parent.parent / "fegen"
    grammar = parse_grammar_file(script_dir / "fegen.fltkg")
    parser_result = generate_parser(grammar, capture_trivia=True)
    try:
        fmt_config = parse_format_config_file(script_dir / "fegen.fltkfmt")
        assert fmt_config.trivia_config is not None
        fmt_config.trivia_config.preserve_blanks = 2

        unparser_result = generate_unparser(
            parser_result.grammar, parser_result.cst_module_name, formatter_config=fmt_config
        )

        for source_blanks, expected in ((1, 1), (3, 2)):
            test_input = 'rule1 := "a" ;\n' + "\n" * source_blanks + 'rule2 := "b" ;\n'
            parse_result = parse_text(parser_result, test_input, "grammar")
            assert parse_result.success, f"Failed to parse: {parse_result.error_message}"

            doc = unparse_cst(unparser_result, parse_result.cst, test_input, "grammar")
            output = render_doc(doc, RendererConfig(max_width=80))

            blank_count = sum(1 for line in output.strip().split("\n") if line.strip() == "")
            assert blank_count == expected, (
                f"Expected {expected} blank lines from {source_blanks} source blanks "
                f"with preserve_blanks: 2, got {blank_count}:\n{output}"
            )

    finally:
        if parser_result.cst_module_name in sys.modules:
            del sys.modules[parser_result.cst_module_name]


# Custom-trivia grammar (gear-style): whitespace is captured as a named ``Ws`` *node* child of
# ``Trivia``, not a direct Span, so it exercises the whitespace-aware newline counting.
_CUSTOM_TRIVIA_GRAMMAR = """
doc := stmt* ;
stmt := name:/[a-z]+/ . ";" , ;
_trivia := ( ws | line_comment )+ ;
ws := chars:/\\s+/ ;
line_comment := prefix:"//" . text:/[^\\n]*/ . nl:"\\n" ;
"""


def test_preserve_blanks_parsed_config_clobbering_order_direct_span():
    """Blank lines survive when the FormatterConfig comes from parsed clobbering-order text.

    Uses a direct-span-trivia grammar (fegen), so the newline counter is not exercised and only
    the config-parsing path matters: ``preserve_blanks: 1`` listed before ``trivia_preserve`` must
    not be discarded by the later directive. Closes the parse-path hole the direct-override tests
    leave open.
    """
    script_dir = Path(__file__).parent.parent / "fegen"
    grammar = parse_grammar_file(script_dir / "fegen.fltkg")
    parser_result = generate_parser(grammar, capture_trivia=True)
    try:
        fmt_config = parse_format_config(
            "preserve_blanks: 1;\ntrivia_preserve: LineComment, BlockComment;\nws_allowed: nil;\n"
            'ws_required: bsp;\nafter ";" { hard; }\n'
        )
        unparser_result = generate_unparser(
            parser_result.grammar, parser_result.cst_module_name, formatter_config=fmt_config
        )

        test_input = 'rule1 := "a" ;\n\n\nrule2 := "b" ;\n'
        parse_result = parse_text(parser_result, test_input, "grammar")
        assert parse_result.success, f"Failed to parse: {parse_result.error_message}"

        doc = unparse_cst(unparser_result, parse_result.cst, test_input, "grammar")
        output = render_doc(doc, RendererConfig(max_width=80))

        blank_count = sum(1 for line in output.strip().split("\n") if line.strip() == "")
        assert blank_count == 1, f"Expected exactly 1 blank line from parsed clobbering-order config:\n{output}"
    finally:
        if parser_result.cst_module_name in sys.modules:
            del sys.modules[parser_result.cst_module_name]


def test_preserve_blanks_custom_trivia_node_whitespace_survives():
    """Blank lines survive on a custom-trivia grammar where whitespace is a ``Ws`` node child.

    Pins the whitespace-aware newline counting: the counter must see newlines inside node-wrapped
    whitespace, not only in direct-span trivia children. The non-clobbering statement order keeps
    the config-parsing path out of it, so this isolates the counting behavior.
    """
    grammar = parse_grammar(_CUSTOM_TRIVIA_GRAMMAR)
    parser_result = generate_parser(grammar, capture_trivia=True)
    try:
        fmt_config = parse_format_config(
            "trivia_preserve: LineComment;\npreserve_blanks: 1;\nws_allowed: nil;\n"
            'ws_required: nil;\nafter ";" { hard; }\n'
        )
        unparser_result = generate_unparser(
            parser_result.grammar, parser_result.cst_module_name, formatter_config=fmt_config
        )

        test_input = "foo;\n\nbar;\n"
        parse_result = parse_text(parser_result, test_input, "doc")
        assert parse_result.success, f"Failed to parse: {parse_result.error_message}"

        doc = unparse_cst(unparser_result, parse_result.cst, test_input, "doc")
        output = render_doc(doc, RendererConfig(max_width=80))

        blank_count = sum(1 for line in output.strip().split("\n") if line.strip() == "")
        assert blank_count == 1, f"Expected the blank line between items to survive:\n{output}"
    finally:
        if parser_result.cst_module_name in sys.modules:
            del sys.modules[parser_result.cst_module_name]


def test_preserve_blanks_custom_trivia_comment_terminator_not_counted():
    """Comment-terminator newlines are not miscounted as blank lines when the node holds a comment.

    On the custom-trivia grammar, a gap holding two consecutive unpreserved ``//`` line comments
    and no source blank line must render with no blank line: each comment node's ``\\n`` terminator
    is not whitespace-only, so it contributes nothing to the newline count. Two comments are used
    (not one) so that dropping the whitespace-only check would mis-count their two terminators to 2,
    crossing the ``>= 2`` blank-line threshold -- the input actually discriminates the whitespace
    guard from its absence.
    """
    grammar = parse_grammar(_CUSTOM_TRIVIA_GRAMMAR)
    parser_result = generate_parser(grammar, capture_trivia=True)
    try:
        # Comments are NOT preserved here, so the gap routes through the no-preservable newline count.
        fmt_config = parse_format_config(
            'preserve_blanks: 1;\nws_allowed: nil;\nws_required: nil;\nafter ";" { hard; }\n'
        )
        unparser_result = generate_unparser(
            parser_result.grammar, parser_result.cst_module_name, formatter_config=fmt_config
        )

        test_input = "foo; // c1\n// c2\nbar;\n"
        parse_result = parse_text(parser_result, test_input, "doc")
        assert parse_result.success, f"Failed to parse: {parse_result.error_message}"

        doc = unparse_cst(unparser_result, parse_result.cst, test_input, "doc")
        output = render_doc(doc, RendererConfig(max_width=80))

        blank_count = sum(1 for line in output.strip().split("\n") if line.strip() == "")
        assert blank_count == 0, f"Comment-terminator newline must not create a blank line:\n{output}"
    finally:
        if parser_result.cst_module_name in sys.modules:
            del sys.modules[parser_result.cst_module_name]


# Blank-line preservation across preserved comments.

_PRESERVING_CONFIG = (
    "trivia_preserve: LineComment, BlockComment;\npreserve_blanks: 1;\n"
    'ws_allowed: nil;\nws_required: bsp;\nafter ";" { hard; }\n'
)


def _format_fegen(test_input: str, config_text: str) -> str:
    """Parse and reformat a fegen grammar source under a parsed format config."""
    script_dir = Path(__file__).parent.parent / "fegen"
    grammar = parse_grammar_file(script_dir / "fegen.fltkg")
    parser_result = generate_parser(grammar, capture_trivia=True)
    try:
        fmt_config = parse_format_config(config_text)
        unparser_result = generate_unparser(
            parser_result.grammar, parser_result.cst_module_name, formatter_config=fmt_config
        )
        parse_result = parse_text(parser_result, test_input, "grammar")
        assert parse_result.success, f"Failed to parse: {parse_result.error_message}"
        doc = unparse_cst(unparser_result, parse_result.cst, test_input, "grammar")
        return render_doc(doc, RendererConfig(max_width=80))
    finally:
        if parser_result.cst_module_name in sys.modules:
            del sys.modules[parser_result.cst_module_name]


def _blank_count(output: str) -> int:
    return sum(1 for line in output.strip().split("\n") if line.strip() == "")


def test_preserve_blanks_blank_after_preserved_comment_survives():
    """A blank line between a preserved comment and the following code is kept."""
    output = _format_fegen('rule1 := "a" ;\n// c\n\nrule2 := "b" ;\n', _PRESERVING_CONFIG)

    assert "// c\n\nrule2" in output, f"The blank must land between the comment and rule2:\n{output}"
    assert _blank_count(output) == 1, f"Expected exactly one blank after the comment:\n{output}"


def test_preserve_blanks_blank_between_preserved_comments_survives():
    """A blank line between two preserved comments is kept.

    The first comment's terminating newline is inside its own span, so the whitespace span
    between them holds only one newline; without the terminator adjustment the blank measures
    as absent.
    """
    output = _format_fegen('rule1 := "a" ;\n// c1\n\n// c2\nrule2 := "b" ;\n', _PRESERVING_CONFIG)

    assert "// c1\n\n// c2\nrule2" in output, f"The blank must land between the two comments:\n{output}"
    assert _blank_count(output) == 1, f"Expected exactly one blank between the comments:\n{output}"


def test_preserve_blanks_blank_before_preserved_comment_survives():
    """Regression pin: a blank line before a preserved comment is kept."""
    output = _format_fegen('rule1 := "a" ;\n\n// c\nrule2 := "b" ;\n', _PRESERVING_CONFIG)

    assert "\n\n// c\nrule2" in output, f"The blank must land before the comment:\n{output}"
    assert _blank_count(output) == 1, f"Expected exactly one blank before the comment:\n{output}"


def test_preserve_blanks_adjacent_preserved_comments_invent_no_blank():
    """Two preserved comments on consecutive lines produce no blank line.

    The terminator adjustment must not overshoot into inventing a blank that the source
    does not have.
    """
    output = _format_fegen('rule1 := "a" ;\n// c1\n// c2\nrule2 := "b" ;\n', _PRESERVING_CONFIG)

    assert "// c1\n// c2\nrule2" in output, f"No blank line may be invented between the comments:\n{output}"


def test_preserve_blanks_blank_after_preserved_block_comment_survives():
    """A blank line after a preserved block comment is kept.

    A block comment's span does not end in a newline, so it consumes none and the whitespace
    span holds the full two newlines on its own.
    """
    output = _format_fegen('rule1 := "a" ;\n/* c */\n\nrule2 := "b" ;\n', _PRESERVING_CONFIG)

    assert "/* c */\n\nrule2" in output, f"The blank must land between the block comment and rule2:\n{output}"
    assert _blank_count(output) == 1, f"Expected exactly one blank after the block comment:\n{output}"


def test_preserve_blanks_zero_collapses_blanks_around_preserved_comments():
    """The canonical form has no blank lines when ``preserve_blanks`` is left at its default.

    Preserved comments are the configuration the terminator adjustment touches, so the
    collapse arm has to stay free of it: comments survive, every blank around them goes.
    """
    config = (
        "trivia_preserve: LineComment, BlockComment;\npreserve_blanks: 0;\n"
        'ws_allowed: nil;\nws_required: bsp;\nafter ";" { hard; }\n'
    )

    output = _format_fegen('rule1 := "a" ;\n\n// c1\n\n// c2\n\nrule2 := "b" ;\n', config)

    assert "// c1\n// c2\nrule2" in output, f"The comments must survive, with no blanks:\n{output}"
    assert _blank_count(output) == 0, f"preserve_blanks: 0 must collapse every blank:\n{output}"


def test_preserve_blanks_rule_level_zero_suppresses_blanks():
    """A rule-level ``preserve_blanks: 0`` collapses blanks in that rule's own gaps.

    The gap after a rule's terminating ``;`` belongs to the ``rule`` rule, so overriding it to
    0 under a global 1 collapses blanks between rules while a blank inside a rule body, which
    belongs to ``items``, still survives.
    """
    config = (
        'preserve_blanks: 1;\nws_allowed: nil;\nws_required: bsp;\nafter ";" { hard; }\n'
        "rule rule { preserve_blanks: 0; }\n"
    )

    between = _format_fegen('rule1 := "a" ;\n\nrule2 := "b" ;\n', config)
    assert ";\nrule2" in between, f"Rule-level 0 must collapse blanks between rules:\n{between}"
    assert _blank_count(between) == 0, f"Rule-level 0 must collapse blanks between rules:\n{between}"

    inside = _format_fegen('rule1 := "a" ,\n\n"b" ;\n', config)
    assert _blank_count(inside) == 1, f"A blank inside a rule keeps the global value:\n{inside}"


def test_preserve_blanks_rule_level_nonzero_over_global_zero():
    """A rule-level ``preserve_blanks: 1`` takes effect under a global default of 0."""
    config = 'ws_allowed: nil;\nws_required: bsp;\nafter ";" { hard; }\nrule rule { preserve_blanks: 1; }\n'

    output = _format_fegen('rule1 := "a" ;\n\n\nrule2 := "b" ;\n', config)
    assert ";\n\nrule2" in output, f"Rule-level 1 must keep the blank between the rules:\n{output}"
    assert _blank_count(output) == 1, f"Rule-level 1 must preserve the blank under a global 0:\n{output}"


# A trivia rule whose comment and following whitespace can be consumed by the *same*
# alternative, so the terminator adjustment must be visible within one loop iteration.
_SAME_ARM_TRIVIA_GRAMMAR = """
doc := stmt* ;
stmt := name:/[a-z]+/ . ";" , ;
_trivia := ( line_comment? : )+ ;
line_comment := prefix:"//" . text:/[^\\n]*/ . nl:"\\n" ;
"""


def test_preserve_blanks_same_arm_comment_and_whitespace():
    """A blank after a comment survives when both sit in one trivia alternative."""
    grammar = parse_grammar(_SAME_ARM_TRIVIA_GRAMMAR)
    parser_result = generate_parser(grammar, capture_trivia=True)
    try:
        fmt_config = parse_format_config(
            "trivia_preserve: LineComment;\npreserve_blanks: 1;\nws_allowed: nil;\n"
            'ws_required: nil;\nafter ";" { hard; }\n'
        )
        unparser_result = generate_unparser(
            parser_result.grammar, parser_result.cst_module_name, formatter_config=fmt_config
        )

        test_input = "foo;\n// c\n\nbar;\n"
        parse_result = parse_text(parser_result, test_input, "doc")
        assert parse_result.success, f"Failed to parse: {parse_result.error_message}"

        doc = unparse_cst(unparser_result, parse_result.cst, test_input, "doc")
        output = render_doc(doc, RendererConfig(max_width=80))

        assert "// c\n\nbar" in output, f"The blank must land between the comment and bar:\n{output}"
        assert _blank_count(output) == 1, f"Expected exactly one blank after the comment:\n{output}"
    finally:
        if parser_result.cst_module_name in sys.modules:
            del sys.modules[parser_result.cst_module_name]


# Which gap a Trivia child was written in, around a *suppressed* terminator. The parser pushes a
# Trivia child only where whitespace or a comment matched, and a suppressed literal contributes no
# child, so the children are not index-aligned with the alternative's separators: the gap before
# `%";"` is empty in every one of these inputs, and taking the trivia that follows the `;` there
# is what strands the terminator on a line of its own. `list` ends on a suppressed `]` and
# `opt_tail` on an absent optional, the two shapes whose accumulators end differently at the
# terminator's gap. Twin of the Rust backend's `trivia_ownership` gate case.

_TRIVIA_OWNERSHIP_GRAMMAR = (
    "doc := stmt* ;\n"
    'stmt := val:value , %";" , ;\n'
    "value := list:list | opt:opt_tail ;\n"
    'list := %"[" , word:word , %"]" ;\n'
    "opt_tail := word:word , tail:list? ;\n"
    "word := chars:/[a-z]+/ ;\n"
    "_trivia := ( line_comment | line_comment? : )+ ;\n"
    'line_comment := prefix:"//" . text:/[^\\n]*/ . nl:"\\n" ;\n'
)

_TRIVIA_OWNERSHIP_CONFIG = (
    "preserve_blanks: 1;\ntrivia_preserve: LineComment;\nws_allowed: nil;\n"
    "ws_required: bsp;\nrule _trivia { ws_required: nbsp; }\n"
)


@pytest.fixture
def trivia_ownership_unparser():
    """Parser and unparser over the suppressed-terminator grammar."""
    grammar = parse_grammar(_TRIVIA_OWNERSHIP_GRAMMAR)
    parser_result = generate_parser(grammar, capture_trivia=True)
    try:
        unparser_result = generate_unparser(
            parser_result.grammar,
            parser_result.cst_module_name,
            formatter_config=parse_format_config(_TRIVIA_OWNERSHIP_CONFIG),
        )
        yield parser_result, unparser_result
    finally:
        if parser_result.cst_module_name in sys.modules:
            del sys.modules[parser_result.cst_module_name]


def _render_ownership(unparser_result, cst, source: str) -> str:
    doc = unparse_cst(unparser_result, cst, source, "doc")
    return render_doc(doc, RendererConfig(max_width=80))


def _format_ownership(parser_result, unparser_result, source: str) -> str:
    """Format once and assert the output is a fixed point."""
    parse_result = parse_text(parser_result, source, "doc")
    assert parse_result.success, f"Failed to parse {source!r}: {parse_result.error_message}"
    once = _render_ownership(unparser_result, parse_result.cst, source)

    again = parse_text(parser_result, once, "doc")
    assert again.success, f"Failed to reparse {once!r}: {again.error_message}"
    twice = _render_ownership(unparser_result, again.cst, once)
    assert twice == once, f"the layout must be a fixed point: {once!r} -> {twice!r}"
    return once


def test_blank_line_after_the_terminator_stays_after_it(trivia_ownership_unparser):
    """A blank line written after `;` renders after it, not ahead of it."""
    parser_result, unparser_result = trivia_ownership_unparser
    rendered = _format_ownership(parser_result, unparser_result, "a;\n\nb;\n")
    assert rendered == "a;\n\nb;\n", repr(rendered)


def test_value_ending_on_a_suppressed_closer_keeps_its_terminator(trivia_ownership_unparser):
    """The `]` case: the closer's own gap owns no trivia, so the terminator stays put."""
    parser_result, unparser_result = trivia_ownership_unparser
    rendered = _format_ownership(parser_result, unparser_result, "[a];\n\nb;\n")
    assert rendered == "[a];\n\nb;\n", repr(rendered)


def test_value_ending_on_an_absent_optional_keeps_its_terminator(trivia_ownership_unparser):
    """The nested-rule case: the child's accumulator ends in a default spec, and the parent's
    gap still takes the trivia it owns."""
    parser_result, unparser_result = trivia_ownership_unparser
    rendered = _format_ownership(parser_result, unparser_result, "a [b];\n\nc;\n")
    assert rendered == "a[b];\n\nc;\n", repr(rendered)


def test_comment_after_the_terminator_stays_after_it(trivia_ownership_unparser):
    """A trailing comment is written after `;` and renders there."""
    parser_result, unparser_result = trivia_ownership_unparser
    rendered = _format_ownership(parser_result, unparser_result, "a; // c\nb;\n")
    assert rendered == "a; // c\nb;\n", repr(rendered)


def test_comment_before_the_terminator_stays_before_it(trivia_ownership_unparser):
    """A comment written before `;` keeps its place ahead of the terminator."""
    parser_result, unparser_result = trivia_ownership_unparser
    rendered = _format_ownership(parser_result, unparser_result, "a // c\n;\nb;\n")
    assert rendered == "a // c\n;\nb;\n", repr(rendered)


def test_whitespace_before_the_terminator_collapses(trivia_ownership_unparser):
    """Whitespace-only trivia before `;` is owned by that gap and renders as the gap's
    configured spacing, which is nothing."""
    parser_result, unparser_result = trivia_ownership_unparser
    rendered = _format_ownership(parser_result, unparser_result, "a ;\nb;\n")
    assert rendered == "a;\nb;\n", repr(rendered)


def test_sourceless_node_span_falls_back_to_child_order(trivia_ownership_unparser):
    """A hand-built or mutated tree: the cursor cannot decide ownership, so trivia is taken in
    child order -- and nothing is refused."""
    parser_result, unparser_result = trivia_ownership_unparser
    source = "[a];\n\nb;\n"
    parse_result = parse_text(parser_result, source, "doc")
    assert parse_result.success, parse_result.error_message
    assert parse_result.cst is not None

    stmt = parse_result.cst.children[0][1]
    stmt.span = terminalsrc.Span(0, 4)

    rendered = _render_ownership(unparser_result, parse_result.cst, source)
    assert rendered == "[a]\n\n;b;\n", f"child order strands the terminator: {rendered!r}"


_SECOND_STATEMENT_SOURCE = "[a];\n\n[b];\n"


def _second_statement_value_span(parser_result, source: str, span):
    """Parse ``source`` and give the second statement's value child ``span``."""
    parse_result = parse_text(parser_result, source, "doc")
    assert parse_result.success, parse_result.error_message
    assert parse_result.cst is not None
    stmt = parse_result.cst.children[1][1]
    stmt.children[0][1].span = span
    return parse_result.cst


def test_a_child_span_behind_the_cursor_falls_back_to_child_order(trivia_ownership_unparser):
    """A mutator that repoints a child at *earlier* text in the same source: the cursor cannot
    be both past this statement's start and before its first child, so it goes unknown rather
    than answering ownership from a position it no longer trusts."""
    parser_result, unparser_result = trivia_ownership_unparser
    source = _SECOND_STATEMENT_SOURCE
    cst = _second_statement_value_span(parser_result, source, terminalsrc.Span.with_source(0, 3, source))
    rendered = _render_ownership(unparser_result, cst, source)
    assert rendered == "[a];\n\n[b]\n;", f"child order strands the terminator: {rendered!r}"


def test_an_inverted_child_span_falls_back_to_child_order(trivia_ownership_unparser):
    """A child whose span ends before it starts describes no region of the source, so the
    cursor after it is unknown -- and the first statement, untouched, keeps its exact one."""
    parser_result, unparser_result = trivia_ownership_unparser
    source = _SECOND_STATEMENT_SOURCE
    cst = _second_statement_value_span(parser_result, source, terminalsrc.Span.with_source(9, 6, source))
    rendered = _render_ownership(unparser_result, cst, source)
    assert rendered == "[a];\n\n[b]\n;", f"child order strands the terminator: {rendered!r}"


def test_trivia_no_gap_claims_is_refused_not_dropped(trivia_ownership_unparser):
    """The drop guard fires: a comment-bearing trivia child moved past every gap of its
    statement is claimed by nobody, and the unparse halts naming the rule and the position
    rather than rendering the statement with the comment gone."""
    parser_result, unparser_result = trivia_ownership_unparser
    source = "a; // c\nb;\n"
    parse_result = parse_text(parser_result, source, "doc")
    assert parse_result.success, parse_result.error_message
    assert parse_result.cst is not None

    stmt = parse_result.cst.children[0][1]
    trivia = stmt.children[1][1]
    trivia.span = terminalsrc.Span.with_source(9, 10, source)

    with pytest.raises(ValueError, match="claimed by no separator"):
        _render_ownership(unparser_result, parse_result.cst, source)


def test_trivia_behind_the_cursor_is_refused_with_its_position(trivia_ownership_unparser):
    """A trivia child the walk already stepped over is an inconsistency, not an empty gap: the
    diagnostic names the rule, the child position and where in the source it sits."""
    parser_result, unparser_result = trivia_ownership_unparser
    source = "a; // c\nb;\n"
    parse_result = parse_text(parser_result, source, "doc")
    assert parse_result.success, parse_result.error_message
    assert parse_result.cst is not None

    stmt = parse_result.cst.children[0][1]
    trivia = stmt.children[1][1]
    trivia.span = terminalsrc.Span.with_source(0, 8, source)

    expected = r"'stmt': trivia at child position 1 starts at 0, behind the source cursor 1 \(line 1, col 1\)"
    with pytest.raises(ValueError, match=expected):
        _render_ownership(unparser_result, parse_result.cst, source)


# A literal that occupies source but no child position advances the cursor only when the source
# there really spells it. An unlabeled alternation of equivalent spellings renders its canonical
# one, so unparsing `use` under `("import" | "use")` emits `import` over three fewer codepoints:
# how much source the token occupies is then unknown, the cursor is, and trivia falls back to
# child order for the rest of that rule node. Twin of the Rust backend's
# `literal_canonicalization` gate case; the expected strings are shared between them.

_LITERAL_CANONICALIZATION_GRAMMAR = (
    "doc := kw:kw_stmt* ;\n"
    'kw_stmt := ( "import" | "use" ) : name:word , %";" , ;\n'
    "word := chars:/[a-z]+/ ;\n"
    "_trivia := ( line_comment | line_comment? : )+ ;\n"
    'line_comment := prefix:"//" . text:/[^\\n]*/ . nl:"\\n" ;\n'
)

_LITERAL_CANONICALIZATION_CONFIG = (
    "preserve_blanks: 1;\ntrivia_preserve: LineComment;\nws_allowed: nil;\n"
    "ws_required: nbsp;\nrule _trivia { ws_required: nbsp; }\n"
)


@pytest.fixture
def literal_canonicalization_unparser():
    """Parser and unparser over the equivalent-spellings grammar."""
    grammar = parse_grammar(_LITERAL_CANONICALIZATION_GRAMMAR)
    parser_result = generate_parser(grammar, capture_trivia=True)
    try:
        unparser_result = generate_unparser(
            parser_result.grammar,
            parser_result.cst_module_name,
            formatter_config=parse_format_config(_LITERAL_CANONICALIZATION_CONFIG),
        )
        yield parser_result, unparser_result
    finally:
        if parser_result.cst_module_name in sys.modules:
            del sys.modules[parser_result.cst_module_name]


def test_the_canonical_spelling_keeps_the_cursor_exact(literal_canonicalization_unparser):
    """Source and emitted text agree, so the terminator keeps its place."""
    parser_result, unparser_result = literal_canonicalization_unparser
    rendered = _format_ownership(parser_result, unparser_result, "import x;\n\nimport y;\n")
    assert rendered == "import x;\n\nimport y;\n"


def test_a_rewritten_spelling_falls_back_to_child_order(literal_canonicalization_unparser):
    """`use` renders as `import`, so the cursor goes unknown for the rest of that statement: its
    trailing trivia is taken in child order, which is where the terminator lands behind it. Never
    worse than a cursorless unparser, and the following statement's cursor is exact again."""
    parser_result, unparser_result = literal_canonicalization_unparser
    rendered = _format_ownership(parser_result, unparser_result, "use x;\n\nimport y;\n")
    assert rendered == "import x\n\n;import y;\n"


def test_a_rewritten_spelling_still_keeps_every_comment(literal_canonicalization_unparser):
    """The fallback loses placement precision, never content."""
    parser_result, unparser_result = literal_canonicalization_unparser
    rendered = _format_ownership(parser_result, unparser_result, "use x; // c\nuse y;\n")
    assert "// c" in rendered, rendered


# A grammar literal that is exactly a newline is a layout break; any other literal, and every regex
# span, is token bytes.


@pytest.mark.parametrize(
    ("grammar_text", "source", "expected"),
    [
        pytest.param('line := text:/[a-z]+/ . "\\n" ;\n', "ab\n", Concat((Text("ab"), HardLine())), id="inline"),
        pytest.param('line := text:/[a-z]+/ . nl:"\\n" ;\n', "ab\n", Concat((Text("ab"), HardLine())), id="labeled"),
        pytest.param('line := text:/[a-z]+/ . %"\\n" ;\n', "ab\n", Concat((Text("ab"), HardLine())), id="suppressed"),
        pytest.param(
            'line := text:/[a-z]+/ . ";\\n" ;\n', "ab;\n", Concat((Text("ab"), Text(";\n"))), id="mixed_bytes"
        ),
    ],
)
def test_newline_literal_is_a_hardline(grammar_text: str, source: str, expected: Concat):
    parser_result = generate_parser(parse_grammar(grammar_text), capture_trivia=True)
    try:
        unparser_result = generate_unparser(parser_result.grammar, parser_result.cst_module_name)
        parse_result = parse_text(parser_result, source, "line")
        assert parse_result.success, parse_result.error_message
        assert unparse_cst(unparser_result, parse_result.cst, source, "line") == expected
    finally:
        if parser_result.cst_module_name in sys.modules:
            del sys.modules[parser_result.cst_module_name]


# A raw-string token (an opening literal, a regex payload that may span lines, a closing literal)
# inside a nest: the payload is token content, so the formatter never writes the nest indent into
# it. The Rust backend's `verbatim_text` gate case asserts the same bytes.

_VERBATIM_TEXT_GRAMMAR = (
    "doc := item* ;\n"
    'item := name:word : "{" , entry* , "}" , ;\n'
    'entry := value:raw , ";" , ;\n'
    'raw := %"\\"\\"\\"" . text:/([^"]|"[^"]|""[^"])*/ . %"\\"\\"\\"" ;\n'
    "word := chars:/[a-z]+/ ;\n"
    "_trivia := ( line_comment | line_comment? : | block_comment )+ ;\n"
    'line_comment := prefix:"//" . text:/[^\\n]*/ . "\\n" ;\n'
    'block_comment := start:"/*" . text:/(?:[^*]|\\*+[^\\/\\*])*/ . end:/\\*+\\// ;\n'
)

_VERBATIM_TEXT_CONFIG = (
    "ws_allowed: nil;\nws_required: nbsp;\npreserve_blanks: 1;\n"
    "trivia_preserve: LineComment, BlockComment;\n"
    'after ";" { hard; }\n'
    'rule item { after "{" { hard; } before "}" { hard; } after "}" { hard; } nest from after "{" to before "}"; }\n'
    "rule _trivia { ws_required: nbsp; }\n"
)

_VERBATIM_TEXT_CASES = [
    pytest.param(
        'box {\n"""\nfirst\n  second\n""";\n}\n',
        'box {\n    """\nfirst\n  second\n""";\n}\n',
        id="multi_line",
    ),
    pytest.param('box {\n"""\n""";\n}\n', 'box {\n    """\n""";\n}\n', id="newline_only"),
    pytest.param('box {\n"""""";\n}\n', 'box {\n    """""";\n}\n', id="empty"),
    pytest.param('box {\n"""\nabc""";\n}\n', 'box {\n    """\nabc""";\n}\n', id="newline_leading"),
    pytest.param('box {\n"""\n\n""";\n}\n', 'box {\n    """\n\n""";\n}\n', id="two_newlines"),
    pytest.param(
        'box {\n"""a""";\n/* l1\n   l2 */\n"""b""";\n}\n',
        'box {\n    """a""";\n    /* l1\n   l2 */\n    """b""";\n}\n',
        id="block_comment",
    ),
    pytest.param(
        'box {\n"""a""";\n// c1\n// c2\n"""b""";\n}\n',
        'box {\n    """a""";\n    // c1\n    // c2\n    """b""";\n}\n',
        id="two_line_comments",
    ),
]


@pytest.fixture
def verbatim_text_unparser():
    """Parser and unparser over the raw-string grammar."""
    grammar = parse_grammar(_VERBATIM_TEXT_GRAMMAR)
    parser_result = generate_parser(grammar, capture_trivia=True)
    try:
        unparser_result = generate_unparser(
            parser_result.grammar,
            parser_result.cst_module_name,
            formatter_config=parse_format_config(_VERBATIM_TEXT_CONFIG),
        )
        yield parser_result, unparser_result
    finally:
        if parser_result.cst_module_name in sys.modules:
            del sys.modules[parser_result.cst_module_name]


@pytest.mark.parametrize(("source", "expected"), _VERBATIM_TEXT_CASES)
def test_newline_spanning_token_renders_verbatim(verbatim_text_unparser, source: str, expected: str):
    """The token's bytes survive inside the nest, and the output is a fixed point."""
    parser_result, unparser_result = verbatim_text_unparser

    def render(text: str) -> str:
        parse_result = parse_text(parser_result, text, "doc")
        assert parse_result.success, f"Failed to parse {text!r}: {parse_result.error_message}"
        doc = unparse_cst(unparser_result, parse_result.cst, text, "doc")
        return render_doc(doc, RendererConfig(max_width=80, indent_width=4))

    once = render(source)
    assert once == expected
    assert render(once) == once


# `before X` on an optional item. An included optional item's before-spacing is part of its
# attempt: it is emitted only when `X` is, and an absent `?` or zero-occurrence `*` leaves the
# accumulator -- trivia state included -- as if no `before X` were configured. Spacing anchored to
# a suppressed optional item fires whether or not the source carried the token. The grammar and
# config are the Rust backend's `optional_before_spec` gate case's, so both backends witness the
# same inputs; each backend states its expected text independently.


class _Formatter:
    """A generated parser and unparser pair over one grammar and one format config."""

    def __init__(self, parser_result, unparser_result):
        self.parser_result = parser_result
        self.unparser_result = unparser_result

    def parse(self, rule: str, text: str):
        parse_result = parse_text(self.parser_result, text, rule)
        assert parse_result.success, f"Failed to parse {text!r} as {rule}: {parse_result.error_message}"
        assert parse_result.cst is not None
        return parse_result.cst

    def render(self, rule: str, cst, text: str) -> str:
        doc = unparse_cst(self.unparser_result, cst, text, rule)
        return render_doc(doc, RendererConfig(max_width=80))

    def format(self, rule: str, text: str) -> str:
        """Format ``text`` as ``rule`` and assert the output is a fixed point."""
        once = self.render(rule, self.parse(rule, text), text)
        twice = self.render(rule, self.parse(rule, once), once)
        assert twice == once, f"the layout must be a fixed point: {text!r} -> {once!r} -> {twice!r}"
        return once


def _formatter(grammar_text: str, config_text: str):
    grammar = parse_grammar(grammar_text)
    parser_result = generate_parser(grammar, capture_trivia=True)
    try:
        unparser_result = generate_unparser(
            parser_result.grammar,
            parser_result.cst_module_name,
            formatter_config=parse_format_config(config_text),
        )
        yield _Formatter(parser_result, unparser_result)
    finally:
        if parser_result.cst_module_name in sys.modules:
            del sys.modules[parser_result.cst_module_name]


@pytest.fixture
def optional_before():
    """Formatter over the optional-item before-spacing grammar."""
    yield from _formatter(OPTIONAL_BEFORE_SPEC_GRAMMAR, OPTIONAL_BEFORE_SPEC_FORMATTER)


@pytest.mark.parametrize(("text", "expected"), [("xz", "xz"), ("xaz", "x az")])
def test_optional_item_before_spacing_only_when_present(optional_before, text, expected):
    """`before a` on `a:"a"?` spaces a present `a` and contributes nothing when `a` is absent."""
    assert optional_before.format("opt", text) == expected


@pytest.mark.parametrize(("text", "expected"), [("xz", "xz"), ("xaz", "x az"), ("xaaz", "x aaz")])
def test_repetition_item_before_spacing_only_ahead_of_a_nonempty_run(optional_before, text, expected):
    """`before a` on `a:"a"*`: nothing for zero occurrences, one spacing ahead of a run."""
    assert optional_before.format("rep", text) == expected


@pytest.mark.parametrize("text", ["xz", "x z", "x // c\nz", "x // c\n// d\nz"])
def test_absent_optional_after_trivia_matches_unconfigured_twin(optional_before, text):
    """An absent item after a trivia-bearing gap leaves the gap's trivia state as it was."""
    assert optional_before.format("opt", text) == optional_before.format("opt_twin", text)


@pytest.mark.parametrize("text", ["xz", "x z", "x // c\nz"])
def test_consecutive_absent_optionals_match_unconfigured_twin(optional_before, text):
    """Two configured optionals, both absent, render exactly as two unconfigured ones do."""
    assert optional_before.format("two", text) == optional_before.format("two_twin", text)


@pytest.mark.parametrize(("text", "expected"), [("xaz", "x az"), ("xbz", "x bz"), ("xabz", "x a bz")])
def test_consecutive_optionals_space_each_present_item(optional_before, text, expected):
    """Each present configured optional gets its own before-spacing; an absent neighbour adds none."""
    assert optional_before.format("two", text) == expected


def _drop_absent_item(fmt: _Formatter, rule: str, text: str, label: str):
    """Parse ``text`` as ``rule``, then remove the ``label`` child and the node's source.

    The result is a tree whose ``label`` item is absent and whose source cursor is unknown, so
    trivia children are consumed in child order rather than by source position.
    """
    cst = fmt.parse(rule, text)
    cst.children[:] = [(lbl, child) for lbl, child in cst.children if lbl is None or lbl.name != label.upper()]
    cst.span = terminalsrc.Span(0, len(text))
    return cst


def test_absent_optional_with_unknown_cursor_matches_unconfigured_twin(optional_before):
    """With the cursor unknown, the gap after an absent item takes trivia exactly as if no
    `before` were configured: the attempt leaves the accumulator's trivia state untouched.

    Both rules drop `// d`: the gap before the absent item takes `// c` and sets the trivia flag,
    so the gap after it takes nothing, and the dropped-trivia guard does not run without a cursor.
    TODO(unparse-cursor-fallback-signal): the expected text loses a comment.
    """
    text = "x // c\na // d\nz"
    configured = optional_before.render("opt", _drop_absent_item(optional_before, "opt", text, "a"), text)
    twin = optional_before.render("opt_twin", _drop_absent_item(optional_before, "opt_twin", text, "a"), text)
    assert configured == twin
    assert configured == "x\n// c\nz", repr(configured)


@pytest.mark.parametrize(("rule", "present", "absent"), [("sup", "a;b", "ab"), ("sup_rep", "a,,b", "ab")])
def test_suppressed_optional_spacing_is_unconditional(optional_before, rule, present, absent):
    """Spacing anchored to a suppressed optional token fires whether or not the source carried it."""
    with_token = optional_before.format(rule, present)
    without_token = optional_before.format(rule, absent)
    assert with_token == without_token
    assert with_token != optional_before.format(f"{rule}_twin", absent)


_DISPOSED_OPTIONAL_GRAMMAR = (
    'om := "x" , a:"a"? , "z" ;\n'
    'om_twin := "x" , a:"a"? , "z" ;\n'
    'ra := "x" , a:"a"? , "z" ;\n'
    'ra_twin := "x" , a:"a"? , "z" ;\n'
)

_DISPOSED_OPTIONAL_FORMATTER = (
    "ws_allowed: nil;\n"
    "rule om { before a { hard; } omit a; }\n"
    "rule om_twin { omit a; }\n"
    "rule ra { before a { hard; } render a as bsp; }\n"
    "rule ra_twin { render a as bsp; }\n"
)


@pytest.fixture
def disposed_optional():
    """Formatter over optional items carrying both a `before` spacing and an omit/render disposition."""
    yield from _formatter(_DISPOSED_OPTIONAL_GRAMMAR, _DISPOSED_OPTIONAL_FORMATTER)


@pytest.mark.parametrize("rule", ["om", "ra"])
@pytest.mark.parametrize("text", ["xz", "xaz"])
def test_omit_render_as_optional_ignores_before_spacing(disposed_optional, rule, text):
    """An omitted or rendered-as optional item emits no `before` spacing, present or absent.

    Rendered once rather than formatted: dropping or replacing a present item is not a fixed point.
    """
    twin = f"{rule}_twin"
    configured = disposed_optional.render(rule, disposed_optional.parse(rule, text), text)
    assert configured == disposed_optional.render(twin, disposed_optional.parse(twin, text), text)


def test_block_ended_statement_closes_without_a_blank(optional_before):
    """A `}`-ended statement without `;` leaves no spec behind, so the enclosing `}` follows on
    the next line."""
    rendered = optional_before.format("doc", "x{x;x{x;}}")
    assert rendered == "x{\n    x;\n    x{\n        x;\n    }\n}\n", repr(rendered)


def test_authored_blank_after_block_ended_statement_survives(optional_before):
    """An authored blank after a `}`-ended statement is kept under `preserve_blanks: 1`."""
    rendered = optional_before.format("doc", "x{x{x;}\n\nx;}")
    assert rendered == "x{\n    x{\n        x;\n    }\n\n    x;\n}\n", repr(rendered)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
