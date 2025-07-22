"""Test trivia whitespace capture functionality within trivia rules."""

import logging
from typing import Final

from fltk import plumbing

LOG: Final = logging.getLogger(__name__)


def test_trivia_rule_whitespace_capture():
    """Test that whitespace inside trivia rules is captured as unlabeled Spans when capture_trivia=True."""
    # Create a grammar with a custom trivia rule that has whitespace separators
    grammar_text = r"""
    main := first:"hello" , second:"world";
    _trivia := (comment | : comment?)+;
    comment := comment:/#[^\n]*\n/;
    """

    # Parse grammar and generate parser with trivia capture enabled
    grammar = plumbing.parse_grammar(grammar_text)
    parser_result = plumbing.generate_parser(grammar, capture_trivia=True)

    # Test parsing with trivia that contains both whitespace and comments
    test_input = "hello  # comment\n  world"
    parse_result = plumbing.parse_text(parser_result, test_input, "main")

    assert parse_result.success, f"Failed to parse '{test_input}': {parse_result.error_message}"

    # Check the trivia node structure
    root_node = parse_result.cst
    assert root_node is not None, "Expected parse result to have a CST"
    LOG.info("Root node type: %s", type(root_node).__name__)
    LOG.info("Root node children count: %d", len(root_node.children))

    # Find the trivia node between "hello" and "world"
    trivia_node = None
    assert hasattr(root_node, "children"), "Root node should have children attribute"
    for i, (label, child) in enumerate(root_node.children):
        LOG.info("Child %d: label=%s, type=%s", i, label, type(child).__name__)
        if hasattr(child, "__class__") and "Trivia" in child.__class__.__name__:
            trivia_node = child
            LOG.info("Found trivia node at index %d", i)
            break

    assert trivia_node is not None, "Expected to find a trivia node"

    # Check that the trivia node has children (including unlabeled spans for whitespace)
    LOG.info("Trivia node children count: %d", len(trivia_node.children))

    # Look for unlabeled children (these should be the whitespace spans)
    unlabeled_children = []
    labeled_children = []
    for label, child in trivia_node.children:
        if label is None:
            unlabeled_children.append(child)
            LOG.info("Found unlabeled child: type=%s, span=%s", type(child).__name__, getattr(child, "span", "no span"))
        else:
            labeled_children.append((label, child))
            LOG.info("Found labeled child: label=%s, type=%s", label, type(child).__name__)

    # We expect at least one unlabeled span for the whitespace
    assert len(unlabeled_children) > 0, "Expected unlabeled spans for whitespace inside trivia rule"

    # Verify the unlabeled spans are actually Span objects
    for child in unlabeled_children:
        assert hasattr(child, "start") and hasattr(child, "end"), f"Expected Span object, got {type(child)}"
        LOG.info(
            "Unlabeled span: start=%d, end=%d, text='%s'", child.start, child.end, test_input[child.start : child.end]
        )


def test_trivia_rule_whitespace_no_capture():
    """Test that whitespace inside trivia rules is NOT captured when capture_trivia=False."""
    # Use the same grammar as above
    grammar_text = r"""
    main := first:"hello" , second:"world";
    _trivia := (comment | : comment?)+;
    comment := comment:/#[^\n]*\n/;
    """

    # Parse grammar and generate parser with trivia capture disabled
    grammar = plumbing.parse_grammar(grammar_text)
    parser_result = plumbing.generate_parser(grammar, capture_trivia=False)

    # Test parsing with trivia that contains both whitespace and comments
    test_input = "hello  # comment\n  world"
    parse_result = plumbing.parse_text(parser_result, test_input, "main")

    assert parse_result.success, f"Failed to parse '{test_input}': {parse_result.error_message}"

    # Check that no trivia nodes exist at all
    root_node = parse_result.cst
    assert root_node is not None, "Expected parse result to have a CST"
    LOG.info("Root node children count: %d", len(root_node.children))

    # Should only have the two literal nodes
    assert hasattr(root_node, "children"), "Root node should have children attribute"
    trivia_count = sum(
        1 for _, child in root_node.children if hasattr(child, "__class__") and "Trivia" in child.__class__.__name__
    )
    assert trivia_count == 0, f"Expected no trivia nodes when capture_trivia=False, found {trivia_count}"


if __name__ == "__main__":
    # Enable debug logging for testing
    logging.basicConfig(level=logging.INFO)

    test_trivia_rule_whitespace_capture()
    test_trivia_rule_whitespace_no_capture()
