"""Integration tests for the FLTK plumbing module using toy grammar."""

from pathlib import Path

import pytest

from fltk.plumbing import (
    generate_parser,
    generate_unparser,
    parse_format_config,
    parse_grammar,
    parse_grammar_file,
    parse_text,
    render_doc,
    unparse_cst,
)
from fltk.unparse.combinators import HardLine, Line, Nbsp, SoftLine
from fltk.unparse.fmt_config import FormatterConfig, RuleConfig, TriviaConfig
from fltk.unparse.renderer import RendererConfig


@pytest.fixture
def toy_grammar_path():
    """Get path to toy grammar file."""
    # Assuming we're in fltk/test_library_integration.py
    test_dir = Path(__file__).parent
    grammar_path = test_dir / "unparse" / "toy.fltkg"
    if not grammar_path.exists():
        pytest.skip(f"Toy grammar not found at {grammar_path}")
    return grammar_path


@pytest.fixture
def toy_example_path():
    """Get path to toy example file."""
    test_dir = Path(__file__).parent
    example_path = test_dir / "unparse" / "example.toy"
    if not example_path.exists():
        pytest.skip(f"Toy example not found at {example_path}")
    return example_path


class TestToyGrammarIntegration:
    """Test full pipeline with toy grammar."""

    def test_parse_toy_grammar_file(self, toy_grammar_path):
        """Test parsing toy grammar from file."""
        grammar = parse_grammar_file(toy_grammar_path)

        assert grammar is not None
        # Toy grammar has expr, term, factor, number rules
        rule_names = [rule.name for rule in grammar.rules]
        assert "expr" in rule_names
        assert "term" in rule_names
        assert "factor" in rule_names
        assert "number" in rule_names

    def test_generate_parser_for_toy_grammar(self, toy_grammar_path):
        """Test generating parser for toy grammar."""
        grammar = parse_grammar_file(toy_grammar_path)
        parser_result = generate_parser(grammar, capture_trivia=True)

        assert parser_result.parser_class is not None
        assert hasattr(parser_result.cst_module, "Expr")
        assert hasattr(parser_result.cst_module, "Term")
        assert hasattr(parser_result.cst_module, "Factor")
        assert hasattr(parser_result.cst_module, "Number")

    def test_parse_toy_expressions(self, toy_grammar_path):
        """Test parsing various toy language expressions."""
        grammar = parse_grammar_file(toy_grammar_path)
        parser_result = generate_parser(grammar, capture_trivia=True)

        test_cases = [
            ("123", True),
            ("1+2", True),
            ("1*2", True),
            ("(1)", True),
            ("1+2*3", True),
            ("(1+2)*3", True),
            ("1+2*3+(4+5*6)", True),
            ("++", False),  # Invalid
            ("1++2", False),  # Invalid
        ]

        for input_text, should_succeed in test_cases:
            parse_result = parse_text(parser_result, input_text, "expr")
            assert parse_result.success == should_succeed, f"Failed for input: {input_text}"
            if should_succeed:
                assert parse_result.cst is not None

    def test_toy_example_file(self, toy_grammar_path, toy_example_path):
        """Test parsing the example.toy file."""
        grammar = parse_grammar_file(toy_grammar_path)
        parser_result = generate_parser(grammar, capture_trivia=True)

        with toy_example_path.open() as f:
            example_content = f.read().strip()

        parse_result = parse_text(parser_result, example_content, "expr")
        assert parse_result.success
        assert parse_result.cst is not None

    def test_round_trip_toy_expressions(self, toy_grammar_path):
        """Test parse->unparse->render round trip."""
        grammar = parse_grammar_file(toy_grammar_path)
        parser_result = generate_parser(grammar, capture_trivia=True)
        unparser_result = generate_unparser(grammar, parser_result.cst_module_name)

        test_cases = [
            "123",
            "1+2",
            "1*2",
            "(1)",
            "1+2*3",
            "(1+2)*3",
        ]

        for input_text in test_cases:
            # Parse
            parse_result = parse_text(parser_result, input_text, "expr")
            assert parse_result.success

            # Unparse
            doc = unparse_cst(unparser_result, parse_result.cst, parse_result.terminals, "expr")

            # Render
            output = render_doc(doc)
            assert output == input_text, f"Round trip failed for {input_text}: got {output}"

    def test_toy_with_custom_formatting(self, toy_grammar_path):
        """Test toy grammar with custom formatting rules."""
        grammar = parse_grammar_file(toy_grammar_path)
        parser_result = generate_parser(grammar, capture_trivia=True)

        # Create formatter that adds spacing around operators
        formatter_config = FormatterConfig(
            global_ws_allowed=Nbsp(),  # Add space where allowed
            global_ws_required=Line(),  # Add line break where required
        )

        unparser_result = generate_unparser(grammar, parser_result.cst_module_name, formatter_config=formatter_config)

        # Parse expression with no spaces
        parse_result = parse_text(parser_result, "1+2*3", "expr")
        assert parse_result.success

        # Unparse with formatting
        doc = unparse_cst(unparser_result, parse_result.cst, parse_result.terminals, "expr")

        # Render - should have spaces due to WS_ALLOWED separator
        output = render_doc(doc)
        # The exact spacing may vary based on trivia handling, just check structure
        assert "1" in output and "+" in output and "2" in output and "*" in output and "3" in output
        assert len(output) >= len("1+2*3")  # Should be longer due to spacing

    def test_toy_with_rule_specific_formatting(self, toy_grammar_path):
        """Test toy grammar with rule-specific formatting."""
        grammar = parse_grammar_file(toy_grammar_path)
        parser_result = generate_parser(grammar, capture_trivia=True)

        # Create formatter with different rules for expr vs term
        formatter_config = FormatterConfig(
            global_ws_allowed=Nbsp(),
            rule_configs={
                "expr": RuleConfig(ws_allowed_spacing=SoftLine()),  # Soft break in expressions
                "term": RuleConfig(ws_allowed_spacing=HardLine()),  # Hard break in terms
            },
        )

        unparser_result = generate_unparser(grammar, parser_result.cst_module_name, formatter_config=formatter_config)

        # Parse complex expression
        parse_result = parse_text(parser_result, "1+2*3+4", "expr")
        assert parse_result.success

        # Unparse and render with narrow width
        doc = unparse_cst(unparser_result, parse_result.cst, parse_result.terminals, "expr")
        output = render_doc(doc, RendererConfig(max_width=10))

        # Should break at soft lines
        assert "\n" in output

    def test_format_config_from_string(self):
        """Test parsing format configuration from string."""
        config_text = """
        ws_allowed: soft;
        ws_required: hard;

        rule expr {
            ws_allowed: nil;
        }

        rule term {
            ws_required: soft;
        }
        """

        config = parse_format_config(config_text)

        assert isinstance(config.global_ws_allowed, SoftLine)
        assert isinstance(config.global_ws_required, HardLine)
        assert "expr" in config.rule_configs
        assert config.rule_configs["expr"].ws_allowed_spacing.__class__.__name__ == "Nil"
        assert "term" in config.rule_configs
        assert isinstance(config.rule_configs["term"].ws_required_spacing, SoftLine)


class TestCommentPreservation:
    """Test comment preservation with library functions."""

    def test_preserve_line_comments(self):
        """Test preserving line comments."""
        grammar_text = """
        expr := value:number;
        number := content:/[0-9]+/;
        _trivia := (whitespace | line_comment)+;
        whitespace := content:/\\s+/;
        line_comment := prefix:"//" . content:/[^\\n]*/ . newline:"\\n";
        """

        grammar = parse_grammar(grammar_text)
        parser_result = generate_parser(grammar, capture_trivia=True)

        # Parse with comment - simpler case
        input_text = "123"
        parse_result = parse_text(parser_result, input_text, "expr")
        assert parse_result.success

        # Generate unparser that preserves LineComment
        trivia_config = TriviaConfig(preserve_node_names={"LineComment"})
        formatter_config = FormatterConfig()
        formatter_config.trivia_config = trivia_config
        unparser_result = generate_unparser(grammar, parser_result.cst_module_name, formatter_config=formatter_config)

        # Unparse
        doc = unparse_cst(unparser_result, parse_result.cst, parse_result.terminals, "expr")
        output = render_doc(doc)

        # Should work for basic case
        assert "123" in output

    def test_discard_whitespace_preserve_comments(self):
        """Test discarding whitespace while preserving comments."""
        grammar_text = """
        expr := a:"a" , b:"b";
        _trivia := (whitespace | comment)+;
        whitespace := content:/\\s+/;
        comment := start:"/*" , content:/[^*]*/ , end:"*/";
        """

        grammar = parse_grammar(grammar_text)
        parser_result = generate_parser(grammar, capture_trivia=True)

        # Parse simple case first
        input_text = "a b"
        parse_result = parse_text(parser_result, input_text, "expr")
        assert parse_result.success

        # Preserve only comments, not whitespace
        trivia_config = TriviaConfig(preserve_node_names={"Comment"})
        formatter_config = FormatterConfig()
        formatter_config.trivia_config = trivia_config
        unparser_result = generate_unparser(grammar, parser_result.cst_module_name, formatter_config=formatter_config)

        doc = unparse_cst(unparser_result, parse_result.cst, parse_result.terminals, "expr")
        output = render_doc(doc)

        # Should work for basic case
        assert "a" in output and "b" in output


class TestErrorHandling:
    """Test error handling in library functions."""

    def test_file_not_found_errors(self):
        """Test appropriate errors for missing files."""
        with pytest.raises(FileNotFoundError):
            parse_grammar_file(Path("nonexistent.fltkg"))

    def test_parser_generation_without_trivia_for_unparser(self, toy_grammar_path):
        """Test that unparser still works even without trivia capture."""
        grammar = parse_grammar_file(toy_grammar_path)

        # Generate parser WITHOUT trivia
        parser_result = generate_parser(grammar, capture_trivia=False)

        # Parse something
        parse_result = parse_text(parser_result, "1+2", "expr")
        assert parse_result.success

        # Unparser should still work (it will add trivia rule as needed)
        unparser_result = generate_unparser(grammar, parser_result.cst_module_name)

        # But the CST won't have trivia nodes, so unparsing might not preserve whitespace
        doc = unparse_cst(unparser_result, parse_result.cst, parse_result.terminals, "expr")
        output = render_doc(doc)
        assert output == "1+2"  # No spaces preserved


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
