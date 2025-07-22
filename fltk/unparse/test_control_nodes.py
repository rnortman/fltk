"""Tests for control node resolution in unparsers."""

from fltk import plumbing
from fltk.unparse.combinators import HARDLINE, LINE, NIL, AfterSpec, BeforeSpec, Concat, SeparatorSpec, Text
from fltk.unparse.resolve_specs import resolve_spacing_specs


def test_control_node_types():
    """Test that control nodes are created correctly."""
    # Test AfterSpec
    after = AfterSpec(spacing=LINE)
    assert after.spacing == LINE
    assert repr(after) == "AfterSpec(Line)"

    # Test BeforeSpec
    before = BeforeSpec(spacing=HARDLINE)
    assert before.spacing == HARDLINE
    assert repr(before) == "BeforeSpec(HardLine)"

    # Test SeparatorSpec
    sep = SeparatorSpec(spacing=LINE, preserved_trivia=None, required=True)
    assert sep.spacing == LINE
    assert sep.preserved_trivia is None
    assert sep.required is True
    assert "SeparatorSpec" in repr(sep)


def test_resolve_spacing_specs_simple():
    """Test basic resolution of control nodes."""
    # Simple case: just text
    doc = Text("hello")
    resolved = resolve_spacing_specs(doc)
    assert resolved == Text("hello")

    # Case with AfterSpec and SeparatorSpec
    doc = Concat(
        [
            Text("a"),
            AfterSpec(spacing=LINE),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=False),
            Text("b"),
        ]
    )
    resolved = resolve_spacing_specs(doc)
    # Should get: Text("a"), LINE, Text("b")
    assert isinstance(resolved, Concat)
    assert len(resolved.docs) == 3
    assert resolved.docs[0] == Text("a")
    assert resolved.docs[1] == LINE
    assert resolved.docs[2] == Text("b")


def test_resolve_spacing_specs_with_before():
    """Test resolution with before specs."""
    # Case with AfterSpec, SeparatorSpec, and BeforeSpec
    doc = Concat(
        [
            Text("a"),
            AfterSpec(spacing=LINE),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=False),
            BeforeSpec(spacing=HARDLINE),
            Text("b"),
        ]
    )
    resolved = resolve_spacing_specs(doc)
    # Should get: Text("a"), HARDLINE (BeforeSpec wins), Text("b")
    assert isinstance(resolved, Concat)
    assert len(resolved.docs) == 3
    assert resolved.docs[0] == Text("a")
    assert resolved.docs[1] == HARDLINE  # HARDLINE wins over LINE
    assert resolved.docs[2] == Text("b")


def test_resolve_spacing_specs_preserved_trivia():
    """Test that preserved trivia overrides everything."""
    trivia_doc = Text("  # comment\n")
    doc = Concat(
        [
            Text("a"),
            AfterSpec(spacing=LINE),
            SeparatorSpec(spacing=NIL, preserved_trivia=trivia_doc, required=False),
            SeparatorSpec(spacing=NIL, preserved_trivia=trivia_doc, required=False),
            BeforeSpec(spacing=HARDLINE),
            Text("b"),
        ]
    )
    resolved = resolve_spacing_specs(doc)
    # Preserved trivia wins
    assert isinstance(resolved, Concat)
    assert resolved.docs == (Text("a"), trivia_doc, trivia_doc, Text("b"))


def test_unparser_emits_control_nodes():
    """Test that the generated unparser emits control nodes."""
    # Create a simple grammar with formatter config
    grammar_src = """
    expr := item : ("," . item)* ;
    item := x:"x" | y:"y" ;
    """

    fmt_src = """
    ws_allowed: bsp;
    ws_required: hard;

    rule expr {
        after "," { hard; }
    }
    """

    # Parse grammar
    gsm_grammar = plumbing.parse_grammar(grammar_src)

    # Parse formatter config
    config = plumbing.parse_format_config(fmt_src)

    # Generate parser
    parser_result = plumbing.generate_parser(gsm_grammar, capture_trivia=True)

    # Generate unparser
    unparser_result = plumbing.generate_unparser(
        parser_result.grammar, parser_result.cst_module_name, formatter_config=config
    )

    # The plumbing function already compiles the unparser, so we can't check
    # method names directly. Instead, test that unparsing works and produces control nodes.

    # Test that the unparser produces control nodes by parsing and unparsing a simple expression
    test_input = "x ,y"
    parse_result = plumbing.parse_text(parser_result, test_input, "expr")
    assert parse_result.success, f"Failed to parse: {parse_result.error_message}"

    # Call the unparser directly to get the raw output with control nodes
    unparser = unparser_result.unparser_class(test_input)
    result = unparser.unparse_expr(parse_result.cst)
    assert result is not None, "Unparser returned None"

    # Get the raw doc with control nodes (before resolution)
    raw_doc = result.accumulator.doc

    # Verify that control nodes are present in the output
    # We should see AfterSpec and/or SeparatorSpec nodes
    doc_str = str(raw_doc)
    assert "AfterSpec" in doc_str or "SeparatorSpec" in doc_str, f"No control nodes found in: {doc_str}"


def test_unparser_emits_before_spec():
    """Test that the generated unparser correctly emits BeforeSpec nodes."""
    # Create a grammar with a before formatter rule
    grammar_src = """
    expr := item : ("+" . item)* ;
    item := x:"x" | y:"y" ;
    """

    fmt_src = """
    ws_allowed: bsp;
    ws_required: hard;

    rule expr {
        before "+" { hard; }
    }
    """

    # Parse grammar
    gsm_grammar = plumbing.parse_grammar(grammar_src)

    # Parse formatter config
    config = plumbing.parse_format_config(fmt_src)

    # Generate parser
    parser_result = plumbing.generate_parser(gsm_grammar, capture_trivia=True)

    # Generate unparser
    unparser_result = plumbing.generate_unparser(
        parser_result.grammar, parser_result.cst_module_name, formatter_config=config
    )

    # Test that the unparser produces BeforeSpec nodes
    test_input = "x +y"
    parse_result = plumbing.parse_text(parser_result, test_input, "expr")
    assert parse_result.success, f"Failed to parse: {parse_result.error_message}"

    # Call the unparser directly to get the raw output with control nodes
    unparser = unparser_result.unparser_class(test_input)
    result = unparser.unparse_expr(parse_result.cst)
    assert result is not None, "Unparser returned None"

    # Get the raw doc with control nodes (before resolution)
    raw_doc = result.accumulator.doc
    doc_str = str(raw_doc)

    # Verify that BeforeSpec is present in the output
    assert "BeforeSpec" in doc_str, f"No BeforeSpec found in: {doc_str}"

    # Also verify the spacing is HardLine as specified in the formatter
    assert "BeforeSpec(HardLine" in doc_str, f"BeforeSpec doesn't have HardLine spacing: {doc_str}"
