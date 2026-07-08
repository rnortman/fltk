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
from fltk.unparse.combinators import LINE, Concat, Line, Text, concat
from fltk.unparse.fmt_config import FormatterConfig, TriviaConfig
from fltk.unparse.renderer import RendererConfig


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
    parser_result, unparser_result, grammar_content = toy_unparser

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
        (Text("1"), Text("+"), Text("2"), Text(" "), Text("//"), Text(" This is a comment"), Text("\n"))
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


def test_preserve_blanks_two_normalizes_to_two_blanks():
    """Test that preserve_blanks: 2 normalizes any blanks to exactly 2.

    When preserve_blanks is 2, any number of blank lines in source should become
    exactly 2 blank lines in output.
    """
    script_dir = Path(__file__).parent.parent / "fegen"
    grammar = parse_grammar_file(script_dir / "fegen.fltkg")
    parser_result = generate_parser(grammar, capture_trivia=True)
    try:
        fmt_config = parse_format_config_file(script_dir / "fegen.fltkfmt")
        assert fmt_config.trivia_config is not None
        # Set preserve_blanks to 2
        fmt_config.trivia_config.preserve_blanks = 2

        unparser_result = generate_unparser(
            parser_result.grammar, parser_result.cst_module_name, formatter_config=fmt_config
        )

        # Input with just 1 blank line (but we want 2 in output)
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

        # With preserve_blanks: 2, should have exactly 2 blank lines
        assert blank_count == 2, f"Expected exactly 2 blank lines with preserve_blanks: 2, got {blank_count}:\n{output}"

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
