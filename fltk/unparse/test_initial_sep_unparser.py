"""Test initial separators in unparser generation.

This test verifies that the unparser correctly handles initial_sep in alternatives
and that the WS_REQUIRED bug fix works correctly.
"""

import logging
from contextlib import contextmanager
from typing import Final

from fltk import plumbing
from fltk.fegen import gsm
from fltk.unparse.combinators import Concat, Line, Text
from fltk.unparse.fmt_config import FormatterConfig, TriviaConfig

LOG: Final = logging.getLogger(__name__)


@contextmanager
def parser_and_unparser(statement_rule: gsm.Rule):
    """Context manager that creates parser and unparser, cleaning up automatically."""
    grammar = gsm.Grammar(rules=(statement_rule,), identifiers={"statement": statement_rule})

    # Generate parser
    parser_result = plumbing.generate_parser(grammar, capture_trivia=True)

    # Generate unparser
    unparser_result = plumbing.generate_unparser(
        parser_result.grammar, parser_result.cst_module_name, formatter_config=FormatterConfig()
    )

    yield parser_result, unparser_result


def parse_and_unparse(parser_result, unparser_result, input_text: str):
    """Parse input text and then unparse it back."""
    # Parse
    parse_result = plumbing.parse_text(parser_result, input_text, "statement")
    if not parse_result.success:
        return None, f"Failed to parse: {input_text}\n{parse_result.error_message}"

    # Unparse
    doc = plumbing.unparse_cst(unparser_result, parse_result.cst, input_text, "statement")

    # Return the actual Doc combinator for testing
    return doc, None


def test_leading_ws_allowed():
    """Test that leading WS_ALLOWED separator (`,`) allows optional whitespace before items."""
    # Create grammar: statement := , "foo" "bar"
    statement_rule = gsm.Rule(
        name="statement",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="foo",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("foo"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="bar",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("bar"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS, gsm.Separator.NO_WS],
                initial_sep=gsm.Separator.WS_ALLOWED,  # Leading comma
            ),
        ],
    )

    with parser_and_unparser(statement_rule) as (parser_result, unparser_result):
        # Test 1: Input without leading whitespace should parse and unparse correctly
        result_doc, error = parse_and_unparse(parser_result, unparser_result, "foobar")
        if error:
            raise AssertionError(error)

        # Should produce concatenated text elements for "foo" and "bar"
        expected_doc = Concat((Text("foo"), Text("bar")))
        assert result_doc == expected_doc, f"Expected {expected_doc}, got {result_doc}"
        LOG.info("Successfully verified 'foobar' without leading spaces produces correct combinator")

        # Test 2: Input with leading whitespace should produce the same combinator
        # Since WS_ALLOWED means whitespace is optional, it should normalize to the same output
        result_doc, error = parse_and_unparse(parser_result, unparser_result, "  foobar")
        if error:
            raise AssertionError(error)

        # Should produce the same combinator - WS_ALLOWED means optional whitespace
        expected_doc = Concat((Text("foo"), Text("bar")))
        assert result_doc == expected_doc, f"Expected {expected_doc}, got {result_doc}"
        LOG.info("Successfully verified '  foobar' with leading spaces produces same combinator")


def test_leading_ws_required():
    """Test that leading WS_REQUIRED separator (`:`) requires whitespace before items."""
    # Create grammar: statement := : "foo" "bar"
    statement_rule = gsm.Rule(
        name="statement",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="foo",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("foo"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="bar",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("bar"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS, gsm.Separator.NO_WS],
                initial_sep=gsm.Separator.WS_REQUIRED,  # Leading colon
            ),
        ],
    )

    with parser_and_unparser(statement_rule) as (parser_result, unparser_result):
        # Test: Input with leading whitespace should parse and unparse with required whitespace
        result_doc, error = parse_and_unparse(parser_result, unparser_result, "  foobar")
        if error:
            raise AssertionError(error)

        # Should produce a Line combinator followed by the content
        # The Line combinator represents the required whitespace
        expected_doc = Concat((Line(), Text("foo"), Text("bar")))
        assert result_doc == expected_doc, f"Expected {expected_doc}, got {result_doc}"
        LOG.info("Successfully verified '  foobar' with required leading spaces produces Line combinator")


def test_leading_no_ws():
    """Test that leading NO_WS separator (`.`) prohibits whitespace before items."""
    # Create grammar: statement := . "foo" "bar"
    statement_rule = gsm.Rule(
        name="statement",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="foo",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("foo"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="bar",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("bar"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS, gsm.Separator.NO_WS],
                initial_sep=gsm.Separator.NO_WS,  # Leading dot
            ),
        ],
    )

    with parser_and_unparser(statement_rule) as (parser_result, unparser_result):
        # Test: Input without leading whitespace should parse and unparse correctly
        result_doc, error = parse_and_unparse(parser_result, unparser_result, "foobar")
        if error:
            raise AssertionError(error)

        # Should produce concatenated text elements with no whitespace
        expected_doc = Concat((Text("foo"), Text("bar")))
        assert result_doc == expected_doc, f"Expected {expected_doc}, got {result_doc}"
        LOG.info("Successfully verified 'foobar' with NO_WS initial separator produces correct combinator")


def test_multiple_alternatives_with_leading_separators():
    """Test that multiple alternatives can each have different leading separators."""
    # Create grammar: expr := , "a" | : "b" | "c"
    expr_rule = gsm.Rule(
        name="statement",  # Use statement to match our parser method name
        alternatives=[
            # Alternative 1: leading comma (WS_ALLOWED)
            gsm.Items(
                items=[
                    gsm.Item(
                        label="a",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("a"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
                initial_sep=gsm.Separator.WS_ALLOWED,
            ),
            # Alternative 2: leading colon (WS_REQUIRED)
            gsm.Items(
                items=[
                    gsm.Item(
                        label="b",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("b"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
                initial_sep=gsm.Separator.WS_REQUIRED,
            ),
            # Alternative 3: no leading separator (NO_WS)
            gsm.Items(
                items=[
                    gsm.Item(
                        label="c",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("c"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
                initial_sep=gsm.Separator.NO_WS,
            ),
        ],
    )

    with parser_and_unparser(expr_rule) as (parser_class, unparser_class):
        # Test cases for unparsing each alternative
        test_cases = [
            # Alternative 1: leading comma (WS_ALLOWED) - should unparse without leading trivia
            ("a", Text("a")),
            ("  a", Text("a")),  # WS_ALLOWED normalizes to no leading trivia
            # Alternative 2: leading colon (WS_REQUIRED) - should unparse with Line()
            ("  b", Concat((Line(), Text("b")))),
            # Alternative 3: no leading separator (NO_WS) - should unparse without leading trivia
            ("c", Text("c")),
        ]

        for test_input, expected_doc in test_cases:
            result_doc, error = parse_and_unparse(parser_class, unparser_class, test_input)
            if error:
                error_msg = f"Expected '{test_input}' to parse successfully: {error}"
                raise AssertionError(error_msg)

            assert result_doc == expected_doc, f"For '{test_input}', expected {expected_doc}, got {result_doc}"
            LOG.info(f"Successfully verified '{test_input}' produces correct combinator")


def test_ws_required_bug_fix():
    """Test that WS_REQUIRED doesn't add duplicate whitespace when trivia exists."""
    # Create grammar: statement := "a" : "b"
    # This tests the inter-item separator, not initial_sep, to verify the bug fix
    statement_rule = gsm.Rule(
        name="statement",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="a",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("a"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="b",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("b"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.WS_REQUIRED, gsm.Separator.NO_WS],
                initial_sep=gsm.Separator.NO_WS,
            ),
        ],
    )

    with parser_and_unparser(statement_rule) as (parser_result, unparser_result):
        # Test: Input with whitespace between a and b should produce correct combinator
        # This tests that WS_REQUIRED correctly adds Line() without duplicating
        result_doc, error = parse_and_unparse(parser_result, unparser_result, "a b")
        if error:
            raise AssertionError(error)

        # Should produce: Text("a") + Line() + Text("b")
        # The Line() is from the WS_REQUIRED separator between items
        expected_doc = Concat((Text("a"), Line(), Text("b")))
        assert result_doc == expected_doc, f"Expected {expected_doc}, got {result_doc}"
        LOG.info("WS_REQUIRED correctly produces single Line combinator without duplication")


def test_leading_separators_with_multi_term_alternatives():
    """Test that leading separators work correctly with multi-term alternatives."""
    # Create grammar: statement := , "start" "middle" "end" | : "begin" , "center" , "finish"
    statement_rule = gsm.Rule(
        name="statement",
        alternatives=[
            # Alternative 1: leading comma, no separators between terms
            gsm.Items(
                items=[
                    gsm.Item(
                        label="start",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("start"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="middle",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("middle"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="end",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("end"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS, gsm.Separator.NO_WS, gsm.Separator.NO_WS],
                initial_sep=gsm.Separator.WS_ALLOWED,  # Leading comma
            ),
            # Alternative 2: leading colon, commas between terms
            gsm.Items(
                items=[
                    gsm.Item(
                        label="begin",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("begin"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="center",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("center"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="finish",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("finish"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.WS_ALLOWED, gsm.Separator.WS_ALLOWED, gsm.Separator.NO_WS],
                initial_sep=gsm.Separator.WS_REQUIRED,  # Leading colon
            ),
        ],
    )

    with parser_and_unparser(statement_rule) as (parser_class, unparser_class):
        # Test a few key cases with expected combinators
        # Alternative 1: "startmiddleend" - leading WS_ALLOWED, no separators between terms
        result_doc, error = parse_and_unparse(parser_class, unparser_class, "startmiddleend")
        if error:
            raise AssertionError(error)
        expected_doc = Concat((Text("start"), Text("middle"), Text("end")))
        assert result_doc == expected_doc, f"Expected {expected_doc}, got {result_doc}"

        # Alternative 2: "  begincenterfinish" - leading WS_REQUIRED
        result_doc, error = parse_and_unparse(parser_class, unparser_class, "  begincenterfinish")
        if error:
            raise AssertionError(error)
        expected_doc = Concat((Line(), Text("begin"), Text("center"), Text("finish")))
        assert result_doc == expected_doc, f"Expected {expected_doc}, got {result_doc}"

        LOG.info("Multi-term alternatives with initial separators work correctly")


def test_leading_separators_with_actual_comments():
    """Test that leading separators work correctly with actual comment trivia nodes.

    This test creates a grammar with proper _trivia rule that includes comments,
    and verifies that initial_sep correctly handles comment trivia in the leading position.
    """

    # Create a grammar with proper _trivia rule including comments
    comment_grammar = """
    statement := , content:"content";
    _trivia := (whitespace | line_comment | block_comment)+;
    whitespace := content:/\\s+/;
    line_comment := prefix:"//" . content:/[^\\n]*/ . newline:"\\n";
    block_comment := start:"/*" , content:/[^*]*(?:\\*(?!\\/)[^*]*)*/ , end:"*/";
    """

    # Parse the grammar
    grammar = plumbing.parse_grammar(comment_grammar)

    # Generate parser
    parser_result = plumbing.generate_parser(grammar, capture_trivia=True)

    # Generate unparser with trivia configuration
    trivia_config = TriviaConfig(preserve_node_names={"LineComment", "BlockComment"})
    formatter_config = FormatterConfig(trivia_config=trivia_config)

    unparser_result = plumbing.generate_unparser(
        parser_result.grammar, parser_result.cst_module_name, formatter_config=formatter_config
    )

    # Test cases for WS_ALLOWED initial separator with comments and whitespace
    test_cases = [
        # Line comment before content - should preserve comment (now structured)
        ("// A comment\ncontent", Concat((Text("//"), Text(" A comment"), Text("\n"), Text("content")))),
        # Block comment before content - should preserve comment (now structured)
        ("/* A comment */content", Concat((Text("/*"), Text("A comment "), Text("*/"), Text("content")))),
        # Whitespace before content - WS_ALLOWED normalizes to no leading trivia
        ("  content", Text("content")),
        # No trivia before content - should produce just content
        ("content", Text("content")),
    ]

    for test_input, expected_doc in test_cases:
        # Parse using plumbing
        parse_result = plumbing.parse_text(parser_result, test_input, "statement")

        if not parse_result.success:
            msg = f"Failed to parse '{test_input}': {parse_result.error_message}"
            raise AssertionError(msg)

        # Unparse using plumbing
        doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "statement")

        # Verify the unparser output matches expected combinator
        assert doc == expected_doc, f"For '{test_input}', expected {expected_doc}, got {doc}"
        LOG.info(f"Successfully verified comment handling: '{test_input}'")


def test_leading_separators_ws_required_with_comments():
    """Test that WS_REQUIRED initial separator requires leading trivia including comments."""

    # Create a grammar with WS_REQUIRED initial separator
    comment_grammar = """
    statement := : content:"content";
    _trivia := (whitespace | line_comment | block_comment)+;
    whitespace := content:/\\s+/;
    line_comment := prefix:"//" . content:/[^\\n]*/ . newline:"\\n";
    block_comment := start:"/*" , content:/[^*]*(?:\\*(?!\\/)[^*]*)*/ , end:"*/";
    """

    # Parse the grammar
    grammar = plumbing.parse_grammar(comment_grammar)

    # Generate parser
    parser_result = plumbing.generate_parser(grammar, capture_trivia=True)

    # Generate unparser with trivia configuration
    trivia_config = TriviaConfig(preserve_node_names={"LineComment", "BlockComment"})
    formatter_config = FormatterConfig(trivia_config=trivia_config)

    unparser_result = plumbing.generate_unparser(
        parser_result.grammar, parser_result.cst_module_name, formatter_config=formatter_config
    )

    # Test cases for WS_REQUIRED initial separator with comments and whitespace
    test_cases = [
        # Line comment before content - comment fulfills WS_REQUIRED, no Line combinator needed
        # Now expecting structured output from unparse__trivia
        ("// A comment\ncontent", Concat((Text("//"), Text(" A comment"), Text("\n"), Text("content")))),
        # Block comment before content - comment fulfills WS_REQUIRED, no Line combinator needed
        # Now expecting structured output from unparse__trivia
        ("/* A comment */content", Concat((Text("/*"), Text("A comment "), Text("*/"), Text("content")))),
        # Whitespace before content - should add Line combinator for WS_REQUIRED
        ("  content", Concat((Line(), Text("content")))),
    ]

    for test_input, expected_doc in test_cases:
        # Parse using plumbing
        parse_result = plumbing.parse_text(parser_result, test_input, "statement")

        if not parse_result.success:
            msg = f"Failed to parse '{test_input}': {parse_result.error_message}"
            raise AssertionError(msg)

        # Unparse using plumbing
        doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "statement")

        # Verify the unparser output matches expected combinator
        assert doc == expected_doc, f"For '{test_input}', expected {expected_doc}, got {doc}"
        LOG.info(f"Successfully verified WS_REQUIRED comment handling: '{test_input}'")


def test_leading_separators_no_ws_with_comments():
    """Test that NO_WS initial separator correctly unparsers with no leading trivia."""

    # Create a grammar with NO_WS initial separator
    comment_grammar = """
    statement := . content:"content";
    _trivia := (whitespace | line_comment | block_comment)+;
    whitespace := content:/\\s+/;
    line_comment := prefix:"//" . content:/[^\\n]*/ . newline:"\\n";
    block_comment := start:"/*" , content:/[^*]*(?:\\*(?!\\/)[^*]*)*/ , end:"*/";
    """

    # Parse the grammar
    grammar = plumbing.parse_grammar(comment_grammar)

    # Generate parser
    parser_result = plumbing.generate_parser(grammar, capture_trivia=True)

    # Generate unparser with comment preservation
    trivia_config = TriviaConfig(preserve_node_names={"LineComment", "BlockComment"})
    formatter_config = FormatterConfig()
    formatter_config.trivia_config = trivia_config

    unparser_result = plumbing.generate_unparser(
        parser_result.grammar, parser_result.cst_module_name, formatter_config=formatter_config
    )

    # Test unparsing: NO_WS means no leading trivia should be output
    test_input = "content"  # Only test valid input for NO_WS

    # Parse
    parse_result = plumbing.parse_text(parser_result, test_input, "statement")

    if not parse_result.success:
        msg = f"Failed to parse '{test_input}'"
        raise AssertionError(msg)

    # Call the unparser directly to get the raw output
    unparser = unparser_result.unparser_class(test_input)
    unparse_result = unparser.unparse_statement(parse_result.cst)

    if unparse_result is None:
        msg = f"Failed to unparse '{test_input}'"
        raise AssertionError(msg)

    # Verify NO_WS produces just the content with no leading trivia
    expected_doc = Text("content")
    assert unparse_result.doc == expected_doc, f"Expected {expected_doc}, got {unparse_result.doc}"

    LOG.info("Successfully verified NO_WS unparser produces no leading trivia")


def test_leading_separators_with_mixed_trivia():
    """Test that leading separators work with mixed trivia (different amounts of whitespace)."""
    # Create grammar: statement := : "content"
    statement_rule = gsm.Rule(
        name="statement",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="content",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("content"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
                initial_sep=gsm.Separator.WS_REQUIRED,  # Leading colon - requires whitespace
            ),
        ],
    )

    with parser_and_unparser(statement_rule) as (parser_class, unparser_class):
        # Test cases with different amounts of whitespace (mixed trivia)
        # All these should unparse to the same result: Line() + Text("content")
        test_cases = [
            "  content",  # Simple spaces
            "    content",  # More spaces
            "\tcontent",  # Tab character
            "\n  content",  # Newline and spaces
            "  \n  content",  # Spaces, newline, more spaces
            "\t  \n  content",  # Tab, spaces, newline, spaces
        ]

        for test_input in test_cases:
            result_doc, error = parse_and_unparse(parser_class, unparser_class, test_input)
            if error:
                error_msg = f"Expected '{test_input}' to parse successfully: {error}"
                raise AssertionError(error_msg)

            # Verify the result has the expected combinator structure
            # For WS_REQUIRED, we should have a Line combinator followed by Text("content")
            expected_doc = Concat((Line(), Text("content")))
            assert result_doc == expected_doc, f"Expected {expected_doc}, got {result_doc}"

            LOG.info(f"Successfully verified mixed trivia unparsing: '{test_input!r}'")
