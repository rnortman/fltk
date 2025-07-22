"""Tests for Nest support in unparsers."""

from fltk import plumbing
from fltk.plumbing import generate_unparser, parse_grammar
from fltk.unparse.combinators import Concat, Nest, Text
from fltk.unparse.fmt_config import (
    AnchorConfig,
    FormatOperation,
    FormatterConfig,
    ItemSelector,
    OperationType,
    RuleConfig,
)


class TestNestSupport:
    """Test nest support in generated unparsers."""

    def test_whole_rule_nest(self):
        """Test nesting an entire rule with default indent."""
        grammar_text = """
expr := "let" : name:identifier : "=" : value:identifier : "in" : body:identifier ;
identifier := value:/[a-zA-Z_][a-zA-Z0-9_]*/;
"""

        fmt_config = FormatterConfig()
        rule_config = RuleConfig()

        # Add nest operations at rule start and end
        start_anchor = AnchorConfig(
            selector_type=ItemSelector.RULE_START,
            selector_value="",
            operations=[FormatOperation(OperationType.NEST_BEGIN, indent=2)],
        )
        rule_config.anchor_configs["before:rule_start:"] = start_anchor

        end_anchor = AnchorConfig(
            selector_type=ItemSelector.RULE_END,
            selector_value="",
            operations=[FormatOperation(OperationType.NEST_END)],
        )
        rule_config.anchor_configs["after:rule_end:"] = end_anchor

        fmt_config.rule_configs["expr"] = rule_config

        grammar = parse_grammar(grammar_text)
        parser_result = plumbing.generate_parser(grammar, capture_trivia=True)
        # Generate the unparser
        unparser_result = generate_unparser(parser_result.grammar, parser_result.cst_module_name, fmt_config)

        # Parse some text and try to unparse it
        test_input = "let x = y in z"
        parse_result = plumbing.parse_text(parser_result, test_input, "expr")
        assert parse_result.success

        # Unparse and check if nest is applied
        doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "expr")

        # The test passes because Nest is now implemented
        assert isinstance(doc, Nest)

    def test_nest_with_from_anchor(self):
        """Test nesting from a specific anchor to end of rule."""
        grammar_text = """
block := "{" , stmts:stmt* , "}" ;
stmt := identifier ;
identifier := value:/[a-zA-Z_][a-zA-Z0-9_]*/;
"""

        fmt_config = FormatterConfig()
        rule_config = RuleConfig()

        # Add nest begin after "stmts" label
        from_anchor = AnchorConfig(
            selector_type=ItemSelector.LABEL,
            selector_value="stmts",
            operations=[FormatOperation(OperationType.NEST_BEGIN, indent=4)],
        )
        rule_config.anchor_configs["after:label:stmts"] = from_anchor

        # Add nest end at rule end
        end_anchor = AnchorConfig(
            selector_type=ItemSelector.RULE_END,
            selector_value="",
            operations=[FormatOperation(OperationType.NEST_END)],
        )
        rule_config.anchor_configs["after:rule_end:"] = end_anchor

        fmt_config.rule_configs["block"] = rule_config

        grammar = parse_grammar(grammar_text)
        parser_result = plumbing.generate_parser(grammar, capture_trivia=True)

        # Generate the unparser
        unparser_result = generate_unparser(parser_result.grammar, parser_result.cst_module_name, fmt_config)

        # Parse some text and try to unparse it
        test_input = "{ }"
        parse_result = plumbing.parse_text(parser_result, test_input, "block")
        assert parse_result.success

        # Unparse and check if nest is applied
        doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "block")

        # For empty block, nest starts from stmts and continues to end
        # So the } should be nested
        assert isinstance(doc, Concat)
        assert doc.docs[0] == Text("{")
        assert isinstance(doc.docs[-1], Nest)
        assert doc.docs[-1].content == Text("}")

    def test_nest_with_to_anchor(self):
        """Test nesting from beginning to a specific anchor."""
        grammar_text = """
func := "def" : name:identifier : "(" , params:identifier* , ")" : body:identifier ;
identifier := value:/[a-zA-Z_][a-zA-Z0-9_]*/;
"""

        fmt_config = FormatterConfig()
        rule_config = RuleConfig()

        # Add nest begin at rule start
        start_anchor = AnchorConfig(
            selector_type=ItemSelector.RULE_START,
            selector_value="",
            operations=[FormatOperation(OperationType.NEST_BEGIN, indent=2)],
        )
        rule_config.anchor_configs["before:rule_start:"] = start_anchor

        # Add nest end before ")" literal
        to_anchor = AnchorConfig(
            selector_type=ItemSelector.LITERAL,
            selector_value=")",
            operations=[FormatOperation(OperationType.NEST_END)],
        )
        rule_config.anchor_configs["before:literal:)"] = to_anchor

        fmt_config.rule_configs["func"] = rule_config

        grammar = parse_grammar(grammar_text)
        parser_result = plumbing.generate_parser(grammar, capture_trivia=True)
        # Generate the unparser
        unparser_result = generate_unparser(parser_result.grammar, parser_result.cst_module_name, fmt_config)

        # Parse some text and try to unparse it
        test_input = "def foo ( ) body"
        parse_result = plumbing.parse_text(parser_result, test_input, "func")
        assert parse_result.success

        # Unparse and check if nest is applied
        doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "func")

        # Should have nested content up to and including )
        assert isinstance(doc, Concat)
        assert any(isinstance(item, Nest) for item in doc.docs)

    def test_nest_with_both_anchors(self):
        """Test nesting with both from and to anchors."""
        grammar_text = """
if_stmt := "if" : cond:identifier : "then" : then_part:identifier : "else" : else_part:identifier ;
identifier := value:/[a-zA-Z_][a-zA-Z0-9_]*/;
"""

        fmt_config = FormatterConfig()
        rule_config = RuleConfig()

        # Add nest begin after "then" literal
        from_anchor = AnchorConfig(
            selector_type=ItemSelector.LITERAL,
            selector_value="then",
            operations=[FormatOperation(OperationType.NEST_BEGIN, indent=4)],
        )
        rule_config.anchor_configs["after:literal:then"] = from_anchor

        # Add nest end before "then_part" label
        to_anchor = AnchorConfig(
            selector_type=ItemSelector.LABEL,
            selector_value="then_part",
            operations=[FormatOperation(OperationType.NEST_END)],
        )
        rule_config.anchor_configs["before:label:then_part"] = to_anchor

        fmt_config.rule_configs["if_stmt"] = rule_config

        grammar = parse_grammar(grammar_text)
        parser_result = plumbing.generate_parser(grammar, capture_trivia=True)
        # Generate the unparser
        unparser_result = generate_unparser(parser_result.grammar, parser_result.cst_module_name, fmt_config)

        # Parse some text and try to unparse it
        test_input = "if cond then body else other"
        parse_result = plumbing.parse_text(parser_result, test_input, "if_stmt")
        assert parse_result.success

        # Unparse and check if nest is applied
        doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "if_stmt")

        # Should have nested content from "then" to then_part
        assert isinstance(doc, Concat)
        assert any(isinstance(item, Nest) for item in doc.docs)

    def test_nest_with_nested_alternatives(self):
        """Test nest with complex nested alternatives."""
        grammar_text = """
expr := a:identifier , (b:identifier , c:identifier | d:identifier) ,
    (e:identifier , f:identifier | g:identifier , h:identifier) ;
identifier := value:/[a-zA-Z_][a-zA-Z0-9_]*/;
"""

        fmt_config = FormatterConfig()
        rule_config = RuleConfig()

        # Add nest begin after "b" label
        from_anchor = AnchorConfig(
            selector_type=ItemSelector.LABEL,
            selector_value="b",
            operations=[FormatOperation(OperationType.NEST_BEGIN, indent=2)],
        )
        rule_config.anchor_configs["after:label:b"] = from_anchor

        # Add nest end before "f" label
        to_anchor = AnchorConfig(
            selector_type=ItemSelector.LABEL,
            selector_value="f",
            operations=[FormatOperation(OperationType.NEST_END)],
        )
        rule_config.anchor_configs["before:label:f"] = to_anchor

        fmt_config.rule_configs["expr"] = rule_config

        grammar = parse_grammar(grammar_text)
        parser_result = plumbing.generate_parser(grammar, capture_trivia=True)
        # Generate the unparser
        unparser_result = generate_unparser(parser_result.grammar, parser_result.cst_module_name, fmt_config)

        # Parse some text and try to unparse it - this path has both b and f
        test_input = "a b c e f"
        parse_result = plumbing.parse_text(parser_result, test_input, "expr")
        assert parse_result.success

        # Unparse and check if nest is applied
        doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "expr")

        # Should have nested content from b to f
        assert isinstance(doc, Concat)
        assert any(isinstance(item, Nest) for item in doc.docs)
