"""Pytest for unparser edge cases that expose bugs in quantified vs non-quantified handling."""

import signal

import pytest

from fltk.plumbing import generate_parser, generate_unparser, parse_grammar, parse_text, unparse_cst
from fltk.unparse.combinators import Concat, Text
from fltk.unparse.fmt_config import FormatterConfig, TriviaConfig

# Test grammar with various edge cases
TEST_GRAMMAR = """
sequence_rule := first:"a" , second:"b" , third:"c";
quantified_single := item:"x"+;
optional_single := item:"y"?;
mixed := prefix:"[" , (elem:"e" , sep:",")+ , suffix:"]";
alt_sequence := ("(" , inner:expr , ")") | number;
expr := term;
term := factor;
factor := value:/[0-9]+/;
number := value:/[0-9]+/;
"""


@pytest.fixture
def temp_unparser():
    """Generate parser and unparser following test_unparser.py pattern."""
    # Parse grammar and generate parser/unparser using plumbing utilities
    grammar = parse_grammar(TEST_GRAMMAR)
    parser_result = generate_parser(grammar, capture_trivia=True)

    # Configure to preserve LineComment and BlockComment but not Whitespace
    trivia_config = TriviaConfig(preserve_node_names={"LineComment", "BlockComment"})
    formatter_config = FormatterConfig()
    formatter_config.trivia_config = trivia_config

    unparser_result = generate_unparser(
        parser_result.grammar, parser_result.cst_module_name, formatter_config=formatter_config
    )

    yield parser_result, unparser_result


def parse_rule(parser_result, rule_name: str, input_text: str):
    """Parse input text using specified rule."""

    parse_result = parse_text(parser_result, input_text, rule_name)
    if parse_result.success:
        return parse_result.cst
    return None


def test_sequence_rule_works(temp_unparser):
    """Test that non-quantified sequences work correctly."""
    parser_result, unparser_result = temp_unparser

    tree = parse_rule(parser_result, "sequence_rule", "abc")
    assert tree is not None, "Failed to parse 'abc'"

    doc = unparse_cst(unparser_result, tree, "abc", "sequence_rule")

    expected = Concat((Text("a"), Text("b"), Text("c")))
    assert doc == expected


def test_quantified_single_hangs(temp_unparser):
    """Test that quantified singular terms cause issues (should hang/fail)."""
    parser_result, unparser_result = temp_unparser

    tree = parse_rule(parser_result, "quantified_single", "xxx")
    assert tree is not None, "Failed to parse 'xxx'"

    # This should hang or fail - we'll use a timeout in pytest
    timeout_msg = "Unparser hung - infinite loop detected"

    def timeout_handler(_signum, _frame):
        raise TimeoutError(timeout_msg)

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(3)  # 3 second timeout

    try:
        doc = unparse_cst(unparser_result, tree, "xxx", "quantified_single")
        signal.alarm(0)  # Cancel alarm

        # If we get here without hanging, check if result is correct
        expected = Concat((Text("x"), Text("x"), Text("x")))
        assert doc == expected
    except TimeoutError:
        signal.alarm(0)
        pytest.fail("Quantified singular unparser hangs (infinite loop)")


def test_optional_single(temp_unparser):
    """Test optional singular terms."""
    parser_result, unparser_result = temp_unparser

    tree = parse_rule(parser_result, "optional_single", "y")
    assert tree is not None, "Failed to parse 'y'"

    timeout_msg = "Unparser hung"

    def timeout_handler(_signum, _frame):
        raise TimeoutError(timeout_msg)

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(3)

    try:
        doc = unparse_cst(unparser_result, tree, "y", "optional_single")
        signal.alarm(0)

        expected = Text("y")
        assert doc == expected
    except TimeoutError:
        signal.alarm(0)
        pytest.fail("Optional singular unparser hangs")


def test_mixed_pattern(temp_unparser):
    """Test mixed patterns with nested sequences."""
    parser_result, unparser_result = temp_unparser

    tree = parse_rule(parser_result, "mixed", "[e,e,e,]")
    assert tree is not None, "Failed to parse '[e,e,e,]'"

    timeout_msg = "Unparser hung"

    def timeout_handler(_signum, _frame):
        raise TimeoutError(timeout_msg)

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(3)

    try:
        result = unparse_cst(unparser_result, tree, "[e,e,e,]", "mixed")
        signal.alarm(0)

        expected = Concat((Text("["), Text("e"), Text(","), Text("e"), Text(","), Text("e"), Text(","), Text("]")))
        assert result == expected
    except TimeoutError:
        signal.alarm(0)
        pytest.fail("Mixed pattern unparser hangs")


def test_alt_sequence(temp_unparser):
    """Test alternative with sequence (non-quantified)."""
    parser_result, unparser_result = temp_unparser

    tree = parse_rule(parser_result, "alt_sequence", "(123)")
    assert tree is not None, "Failed to parse '(123)'"

    timeout_msg = "Unparser hung"

    def timeout_handler(_signum, _frame):
        raise TimeoutError(timeout_msg)

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(3)

    try:
        result = unparse_cst(unparser_result, tree, "(123)", rule_name="alt_sequence")
        signal.alarm(0)

        expected = Concat((Text("("), Text("123"), Text(")")))
        assert result == expected
    except TimeoutError:
        signal.alarm(0)
        pytest.fail("Alt sequence unparser hangs")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
