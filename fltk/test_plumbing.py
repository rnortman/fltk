"""Unit tests for the FLTK plumbing module."""

import sys

import pytest

from fltk.plumbing import (
    generate_parser,
    generate_unparser,
    parse_format_config,
    parse_grammar,
    parse_text,
    render_doc,
    unparse_cst,
)
from fltk.unparse.combinators import HARDLINE, LINE, NBSP, NIL, SOFTLINE, Concat, Line, Nbsp, Text
from fltk.unparse.fmt_config import FormatterConfig, TriviaConfig
from fltk.unparse.renderer import RendererConfig


class TestGrammarParsing:
    """Test grammar parsing functions."""

    def test_parse_simple_grammar(self):
        """Test parsing a simple grammar."""
        grammar_text = """
        expr := term , ("+" , term)*;
        term := number;
        number := value:/[0-9]+/;
        """
        grammar = parse_grammar(grammar_text)

        assert grammar is not None
        assert len(grammar.rules) == 3
        assert grammar.rules[0].name == "expr"
        assert grammar.rules[1].name == "term"
        assert grammar.rules[2].name == "number"

    def test_parse_invalid_grammar(self):
        """Test parsing invalid grammar raises error."""
        with pytest.raises(ValueError, match="Grammar parse failed"):
            parse_grammar("this is not valid grammar syntax")

    def test_parse_empty_grammar(self):
        """Test parsing empty grammar raises error."""
        with pytest.raises(ValueError, match="Grammar parse failed"):
            parse_grammar("")


class TestParserGeneration:
    """Test parser generation functions."""

    def test_generate_parser_with_trivia(self):
        """Test generating parser with trivia capture."""
        grammar_text = """
        expr := number;
        number := value:/[0-9]+/;
        """
        grammar = parse_grammar(grammar_text)
        parser_result = generate_parser(grammar, capture_trivia=True)

        assert parser_result.parser_class is not None
        assert parser_result.cst_module is not None
        assert parser_result.cst_module_name in sys.modules
        assert parser_result.capture_trivia is True
        assert hasattr(parser_result.cst_module, "Expr")
        assert hasattr(parser_result.cst_module, "Number")

    def test_generate_parser_without_trivia(self):
        """Test generating parser without trivia capture."""
        grammar_text = """
        expr := number;
        number := value:/[0-9]+/;
        """
        grammar = parse_grammar(grammar_text)
        parser_result = generate_parser(grammar, capture_trivia=False)

        assert parser_result.parser_class is not None
        assert parser_result.capture_trivia is False

    def test_parser_module_cleanup(self):
        """Test that generated modules are properly registered."""
        grammar = parse_grammar('test := value:"hello";')  # Include item to avoid empty model
        parser_result = generate_parser(grammar)

        # Module should be in sys.modules
        assert parser_result.cst_module_name in sys.modules
        assert sys.modules[parser_result.cst_module_name] is parser_result.cst_module


class TestParsing:
    """Test text parsing functions."""

    def test_parse_simple_expression(self):
        """Test parsing a simple expression."""
        grammar_text = """
        expr := number , ("+" , number)*;
        number := value:/[0-9]+/;
        """
        grammar = parse_grammar(grammar_text)
        parser_result = generate_parser(grammar)

        parse_result = parse_text(parser_result, "123+456", "expr")

        assert parse_result.success is True
        assert parse_result.cst is not None
        assert parse_result.error_message is None

    def test_parse_with_auto_rule(self):
        """Test parsing with auto-detected start rule."""
        grammar_text = """
        expr := number;
        number := value:/[0-9]+/;
        """
        grammar = parse_grammar(grammar_text)
        parser_result = generate_parser(grammar)

        # Should use "expr" as first rule
        parse_result = parse_text(parser_result, "123")

        assert parse_result.success is True
        assert parse_result.cst is not None

    def test_parse_failure(self):
        """Test parsing failure returns error message."""
        grammar_text = """
        expr := value:"hello";
        """
        grammar = parse_grammar(grammar_text)
        parser_result = generate_parser(grammar)

        parse_result = parse_text(parser_result, "goodbye", "expr")

        assert parse_result.success is False
        assert parse_result.cst is None
        assert parse_result.error_message is not None
        assert "hello" in parse_result.error_message

    def test_parse_invalid_rule(self):
        """Test parsing with invalid rule name."""
        grammar = parse_grammar('expr := value:"test";')
        parser_result = generate_parser(grammar)

        parse_result = parse_text(parser_result, "test", "nonexistent")

        assert parse_result.success is False
        assert parse_result.error_message is not None
        assert "No parse method for rule 'nonexistent'" in parse_result.error_message


class TestFormatConfig:
    """Test format configuration parsing."""

    def test_parse_empty_config(self):
        """Test parsing empty format config."""
        config = parse_format_config("")
        assert isinstance(config.global_ws_allowed, type(NIL))
        assert isinstance(config.global_ws_required, type(LINE))
        assert len(config.rule_configs) == 0

    def test_parse_global_config(self):
        """Test parsing global format config."""
        config_text = """
        ws_allowed: nbsp;
        ws_required: hard;
        """
        config = parse_format_config(config_text)

        assert isinstance(config.global_ws_allowed, type(NBSP))
        assert isinstance(config.global_ws_required, type(HARDLINE))

    def test_parse_rule_config(self):
        """Test parsing rule-specific format config."""
        config_text = """
        rule expr {
            ws_allowed: soft;
            ws_required: bsp;
        }
        """
        config = parse_format_config(config_text)

        assert "expr" in config.rule_configs
        assert isinstance(config.rule_configs["expr"].ws_allowed_spacing, type(SOFTLINE))
        assert isinstance(config.rule_configs["expr"].ws_required_spacing, type(LINE))

    def test_parse_invalid_config(self):
        """Test parsing invalid format config raises error."""
        with pytest.raises(ValueError, match="Format config parse failed"):
            parse_format_config("this is not valid format syntax")


class TestUnparserGeneration:
    """Test unparser generation functions."""

    def test_generate_basic_unparser(self):
        """Test generating basic unparser."""
        grammar_text = """
        expr := value:"hello";
        """
        grammar = parse_grammar(grammar_text)
        parser_result = generate_parser(grammar, capture_trivia=True)

        unparser_result = generate_unparser(grammar, parser_result.cst_module_name)

        assert unparser_result.unparser_class is not None
        assert hasattr(unparser_result.unparser_class, "__init__")
        assert hasattr(unparser_result.unparser_class, "unparse_expr")

    def test_generate_unparser_with_formatter(self):
        """Test generating unparser with formatter config."""
        grammar = parse_grammar('expr := a:"a" , b:"b";')
        parser_result = generate_parser(grammar, capture_trivia=True)

        formatter_config = FormatterConfig()
        formatter_config.global_ws_allowed = Nbsp()

        unparser_result = generate_unparser(grammar, parser_result.cst_module_name, formatter_config=formatter_config)

        assert unparser_result.formatter_config is formatter_config

    def test_generate_unparser_with_trivia_config(self):
        """Test generating unparser with trivia config."""
        grammar = parse_grammar('expr := value:"test";')
        parser_result = generate_parser(grammar, capture_trivia=True)

        trivia_config = TriviaConfig(preserve_node_names={"LineComment"})
        formatter_config = FormatterConfig()
        formatter_config.trivia_config = trivia_config

        unparser_result = generate_unparser(grammar, parser_result.cst_module_name, formatter_config=formatter_config)

        assert unparser_result.trivia_config is trivia_config


class TestUnparsing:
    """Test unparsing functions."""

    def test_unparse_simple_expression(self):
        """Test unparsing a simple expression."""
        grammar_text = """
        expr := hello:"hello" , world:"world";
        """
        grammar = parse_grammar(grammar_text)
        parser_result = generate_parser(grammar, capture_trivia=True)
        parse_result = parse_text(parser_result, "helloworld", "expr")

        unparser_result = generate_unparser(grammar, parser_result.cst_module_name)
        doc = unparse_cst(unparser_result, parse_result.cst, parse_result.terminals, "expr")

        assert doc is not None
        # Should be Concat([Text("hello"), Text("world")])
        assert isinstance(doc, Concat)
        assert len(doc.docs) == 2
        assert isinstance(doc.docs[0], Text)
        assert doc.docs[0].content == "hello"
        assert isinstance(doc.docs[1], Text)
        assert doc.docs[1].content == "world"

    def test_unparse_with_auto_rule(self):
        """Test unparsing with auto-detected rule."""
        grammar_text = """
        expr := value:"test";
        """
        grammar = parse_grammar(grammar_text)
        parser_result = generate_parser(grammar, capture_trivia=True)
        parse_result = parse_text(parser_result, "test")

        unparser_result = generate_unparser(grammar, parser_result.cst_module_name)
        doc = unparse_cst(unparser_result, parse_result.cst, parse_result.terminals)

        assert doc is not None
        assert isinstance(doc, Text)
        assert doc.content == "test"

    def test_unparse_invalid_rule(self):
        """Test unparsing with invalid rule name."""
        grammar = parse_grammar('expr := value:"test";')
        parser_result = generate_parser(grammar, capture_trivia=True)
        parse_result = parse_text(parser_result, "test")

        unparser_result = generate_unparser(grammar, parser_result.cst_module_name)

        with pytest.raises(ValueError, match="No unparse method for rule 'nonexistent'"):
            unparse_cst(unparser_result, parse_result.cst, parse_result.terminals, "nonexistent")


class TestRendering:
    """Test rendering functions."""

    def test_render_simple_doc(self):
        """Test rendering a simple doc."""
        doc = Text("hello world")
        output = render_doc(doc)
        assert output == "hello world"

    def test_render_concat_doc(self):
        """Test rendering concatenated docs."""
        doc = Concat([Text("hello"), Line(), Text("world")])
        output = render_doc(doc)
        assert output == "hello world"

    def test_render_with_config(self):
        """Test rendering with custom config."""
        doc = Concat([Text("hello"), Line(), Text("world")])
        config = RendererConfig(indent_width=2, max_width=5)
        output = render_doc(doc, config)
        # Should break due to max_width
        assert output == "hello\nworld"


class TestIntegration:
    """Test full pipeline integration."""

    def test_full_pipeline(self):
        """Test complete parse->unparse->render pipeline."""
        # Define grammar
        grammar_text = """
        expr := term , ("+" , term)*;
        term := number;
        number := value:/[0-9]+/;
        """

        # Parse grammar and generate parser
        grammar = parse_grammar(grammar_text)
        parser_result = generate_parser(grammar, capture_trivia=True)

        # Parse input
        parse_result = parse_text(parser_result, "1+2+3", "expr")
        assert parse_result.success

        # Generate unparser
        unparser_result = generate_unparser(grammar, parser_result.cst_module_name)

        # Unparse to doc
        doc = unparse_cst(unparser_result, parse_result.cst, parse_result.terminals, "expr")

        # Render
        output = render_doc(doc)
        assert output == "1+2+3"

    def test_pipeline_with_formatting(self):
        """Test pipeline with custom formatting."""
        grammar_text = """
        expr := a:"a" , b:"b" : c:"c";
        """

        # Parse grammar and generate parser
        grammar = parse_grammar(grammar_text)
        parser_result = generate_parser(grammar, capture_trivia=True)

        # Parse with whitespace
        parse_result = parse_text(parser_result, "a b c", "expr")
        assert parse_result.success

        # Create formatter config
        formatter_config = FormatterConfig()
        formatter_config.global_ws_allowed = Nbsp()
        formatter_config.global_ws_required = Line()

        # Generate unparser with formatter
        unparser_result = generate_unparser(grammar, parser_result.cst_module_name, formatter_config=formatter_config)

        # Unparse to doc
        doc = unparse_cst(unparser_result, parse_result.cst, parse_result.terminals, "expr")

        # Render - should have nbsp and line
        output = render_doc(doc)
        assert output == "a b c"  # Nbsp renders as space, Line renders as space in flat mode


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
