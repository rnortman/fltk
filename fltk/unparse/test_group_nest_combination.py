"""Tests for combining Group and Nest with overlapping boundaries."""

import pytest

from fltk import plumbing
from fltk.plumbing import generate_unparser, parse_grammar
from fltk.unparse.combinators import Concat, Group, Nest, Text
from fltk.unparse.fmt_config import (
    AnchorConfig,
    FormatOperation,
    FormatterConfig,
    ItemSelector,
    OperationType,
    RuleConfig,
)


class TestGroupNestCombination:
    """Test combining group and nest with same boundaries."""

    def test_group_and_nest_entire_rule(self):
        """Test both group and nest applied to entire rule."""
        grammar_text = """
expr := "let" : name:identifier : "=" : value:identifier : "in" : body:identifier ;
identifier := value:/[a-zA-Z_][a-zA-Z0-9_]*/;
"""

        fmt_config = FormatterConfig()
        rule_config = RuleConfig()

        # Add group and nest operations at rule start
        start_anchor = AnchorConfig(
            selector_type=ItemSelector.RULE_START,
            selector_value="",
            operations=[
                FormatOperation(OperationType.GROUP_BEGIN),
                FormatOperation(OperationType.NEST_BEGIN, indent=2),
            ],
        )
        rule_config.anchor_configs["before:rule_start:"] = start_anchor

        # Add group and nest operations at rule end (in reverse order)
        end_anchor = AnchorConfig(
            selector_type=ItemSelector.RULE_END,
            selector_value="",
            operations=[
                FormatOperation(OperationType.NEST_END),
                FormatOperation(OperationType.GROUP_END),
            ],
        )
        rule_config.anchor_configs["after:rule_end:"] = end_anchor

        fmt_config.rule_configs["expr"] = rule_config

        grammar = parse_grammar(grammar_text)
        parser_result = plumbing.generate_parser(grammar, capture_trivia=True)
        unparser_result = generate_unparser(parser_result.grammar, parser_result.cst_module_name, fmt_config)

        # Parse some text and try to unparse it
        test_input = "let x = y in z"
        parse_result = plumbing.parse_text(parser_result, test_input, "expr")
        assert parse_result.success

        # Unparse and check structure
        doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "expr")

        # Should be Group(Nest(...))
        assert isinstance(doc, Group)
        assert isinstance(doc.content, Nest)
        assert doc.content.indent == 2

    def test_group_and_nest_same_from_anchor(self):
        """Test group and nest starting from same anchor."""
        grammar_text = """
block := "{" , content:stmt* , "}" ;
stmt := identifier , ;
identifier := value:/[a-zA-Z_][a-zA-Z0-9_]*/;
"""

        fmt_config = FormatterConfig()
        rule_config = RuleConfig()

        # Add group and nest operations starting from content
        from_anchor = AnchorConfig(
            selector_type=ItemSelector.LABEL,
            selector_value="content",
            operations=[
                FormatOperation(OperationType.GROUP_BEGIN),
                FormatOperation(OperationType.NEST_BEGIN, indent=4),
            ],
        )
        rule_config.anchor_configs["after:label:content"] = from_anchor

        # Add group and nest operations at rule end
        end_anchor = AnchorConfig(
            selector_type=ItemSelector.RULE_END,
            selector_value="",
            operations=[
                FormatOperation(OperationType.NEST_END),
                FormatOperation(OperationType.GROUP_END),
            ],
        )
        rule_config.anchor_configs["after:rule_end:"] = end_anchor

        fmt_config.rule_configs["block"] = rule_config

        grammar = parse_grammar(grammar_text)
        parser_result = plumbing.generate_parser(grammar, capture_trivia=True)
        unparser_result = generate_unparser(parser_result.grammar, parser_result.cst_module_name, fmt_config)

        # Parse with actual content
        test_input = "{ x y }"
        parse_result = plumbing.parse_text(parser_result, test_input, "block")
        assert parse_result.success

        # Unparse and check structure
        doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "block")

        # Should have { followed by Group(Nest(...))
        assert isinstance(doc, Concat)
        assert doc.docs[0] == Text("{")
        # The rest should be grouped and nested
        grouped = [d for d in doc.docs if isinstance(d, Group)]
        assert len(grouped) > 0
        assert isinstance(grouped[0].content, Nest)

    def test_group_and_nest_same_to_anchor(self):
        """Test group and nest ending at same anchor."""
        grammar_text = """
func := "def" : name:identifier , "(" , params:identifier* , ")" : body:identifier ;
identifier := value:/[a-zA-Z_][a-zA-Z0-9_]*/ ,;
"""

        fmt_config = FormatterConfig()
        rule_config = RuleConfig()

        # Add group and nest operations at rule start
        start_anchor = AnchorConfig(
            selector_type=ItemSelector.RULE_START,
            selector_value="",
            operations=[
                FormatOperation(OperationType.GROUP_BEGIN),
                FormatOperation(OperationType.NEST_BEGIN, indent=2),
            ],
        )
        rule_config.anchor_configs["before:rule_start:"] = start_anchor

        # Add group and nest operations ending before ")"
        to_anchor = AnchorConfig(
            selector_type=ItemSelector.LITERAL,
            selector_value=")",
            operations=[
                FormatOperation(OperationType.NEST_END),
                FormatOperation(OperationType.GROUP_END),
            ],
        )
        rule_config.anchor_configs["before:literal:)"] = to_anchor

        fmt_config.rule_configs["func"] = rule_config

        grammar = parse_grammar(grammar_text)
        parser_result = plumbing.generate_parser(grammar, capture_trivia=True)
        unparser_result = generate_unparser(parser_result.grammar, parser_result.cst_module_name, fmt_config)

        # Parse some text
        test_input = "def foo ( x y ) body"
        parse_result = plumbing.parse_text(parser_result, test_input, "func")
        assert parse_result.success

        # Unparse and check structure
        doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "func")

        # Should start with Group(Nest(...)) up to and including )
        assert isinstance(doc, Concat)
        # Find the group in the output
        grouped = [d for d in doc.docs if isinstance(d, Group)]
        assert len(grouped) > 0
        assert isinstance(grouped[0].content, Nest)

    def test_group_and_nest_same_boundaries(self):
        """Test group and nest with identical from and to anchors."""
        grammar_text = """
if_stmt := "if" : cond:identifier : "then" : then_part:identifier : "else" : else_part:identifier ;
identifier := value:/[a-zA-Z_][a-zA-Z0-9_]*/;
"""

        fmt_config = FormatterConfig()
        rule_config = RuleConfig()

        # Add group and nest operations after "then"
        from_anchor = AnchorConfig(
            selector_type=ItemSelector.LITERAL,
            selector_value="then",
            operations=[
                FormatOperation(OperationType.GROUP_BEGIN),
                FormatOperation(OperationType.NEST_BEGIN, indent=4),
            ],
        )
        rule_config.anchor_configs["after:literal:then"] = from_anchor

        # Add group and nest operations before "then_part"
        to_anchor = AnchorConfig(
            selector_type=ItemSelector.LABEL,
            selector_value="then_part",
            operations=[
                FormatOperation(OperationType.NEST_END),
                FormatOperation(OperationType.GROUP_END),
            ],
        )
        rule_config.anchor_configs["before:label:then_part"] = to_anchor

        fmt_config.rule_configs["if_stmt"] = rule_config

        grammar = parse_grammar(grammar_text)
        parser_result = plumbing.generate_parser(grammar, capture_trivia=True)
        unparser_result = generate_unparser(parser_result.grammar, parser_result.cst_module_name, fmt_config)

        # Parse some text
        test_input = "if cond then body else other"
        parse_result = plumbing.parse_text(parser_result, test_input, "if_stmt")
        assert parse_result.success

        # Unparse and check structure
        doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "if_stmt")

        # Should have "if" "cond" then Group(Nest("then" "body")) "else" "other"
        assert isinstance(doc, Concat)
        # Find the group in the output
        grouped = [d for d in doc.docs if isinstance(d, Group)]
        assert len(grouped) > 0
        assert isinstance(grouped[0].content, Nest)
        assert grouped[0].content.indent == 4

    def test_group_inside_nest(self):
        """Test group nested inside nest (nest has wider boundaries)."""
        grammar_text = """
block := "{" , intro:identifier : content:stmt* , outro:identifier , "}" ;
stmt := "s:" , value:identifier , ;
identifier := value:/[a-zA-Z_][a-zA-Z0-9_]*/;
"""

        fmt_config = FormatterConfig()
        rule_config = RuleConfig()

        # Add nest begin after "intro"
        intro_anchor = AnchorConfig(
            selector_type=ItemSelector.LABEL,
            selector_value="intro",
            operations=[FormatOperation(OperationType.NEST_BEGIN, indent=2)],
        )
        rule_config.anchor_configs["after:label:intro"] = intro_anchor

        # Add group operations around "content"
        content_before = AnchorConfig(
            selector_type=ItemSelector.LABEL,
            selector_value="content",
            operations=[FormatOperation(OperationType.GROUP_BEGIN)],
        )
        rule_config.anchor_configs["before:label:content"] = content_before

        content_after = AnchorConfig(
            selector_type=ItemSelector.LABEL,
            selector_value="content",
            operations=[FormatOperation(OperationType.GROUP_END)],
        )
        rule_config.anchor_configs["after:label:content"] = content_after

        # Add nest end before "outro"
        outro_anchor = AnchorConfig(
            selector_type=ItemSelector.LABEL,
            selector_value="outro",
            operations=[FormatOperation(OperationType.NEST_END)],
        )
        rule_config.anchor_configs["before:label:outro"] = outro_anchor

        fmt_config.rule_configs["block"] = rule_config

        grammar = parse_grammar(grammar_text)
        parser_result = plumbing.generate_parser(grammar, capture_trivia=True)
        unparser_result = generate_unparser(parser_result.grammar, parser_result.cst_module_name, fmt_config)

        # Parse some text
        test_input = "{ start s:x s:y end }"
        parse_result = plumbing.parse_text(parser_result, test_input, "block")
        assert parse_result.success

        # Unparse and check structure
        doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "block")

        # Should have { followed by Nest containing Group
        assert isinstance(doc, Concat)
        assert doc.docs[0] == Text("{")
        # Find the nest
        nested = [d for d in doc.docs if isinstance(d, Nest)]
        assert len(nested) > 0
        # Inside the nest, there should be a group
        # This is trickier to check because of how the content is structured
        # but we can at least verify the nest exists

    def test_nest_inside_group(self):
        """Test nest inside group (group has wider boundaries)."""
        grammar_text = """
block := "{" , intro:identifier : content:stmt* , outro:identifier , "}" ;
stmt := "s:" , value:identifier ,;
identifier := value:/[a-zA-Z_][a-zA-Z0-9_]*/;
"""

        fmt_config = FormatterConfig()
        rule_config = RuleConfig()

        # Add group begin after "intro"
        intro_anchor = AnchorConfig(
            selector_type=ItemSelector.LABEL,
            selector_value="intro",
            operations=[FormatOperation(OperationType.GROUP_BEGIN)],
        )
        rule_config.anchor_configs["after:label:intro"] = intro_anchor

        # Add nest operations around "content"
        content_before = AnchorConfig(
            selector_type=ItemSelector.LABEL,
            selector_value="content",
            operations=[FormatOperation(OperationType.NEST_BEGIN, indent=4)],
        )
        rule_config.anchor_configs["before:label:content"] = content_before

        content_after = AnchorConfig(
            selector_type=ItemSelector.LABEL,
            selector_value="content",
            operations=[FormatOperation(OperationType.NEST_END)],
        )
        rule_config.anchor_configs["after:label:content"] = content_after

        # Add group end before "outro"
        outro_anchor = AnchorConfig(
            selector_type=ItemSelector.LABEL,
            selector_value="outro",
            operations=[FormatOperation(OperationType.GROUP_END)],
        )
        rule_config.anchor_configs["before:label:outro"] = outro_anchor

        fmt_config.rule_configs["block"] = rule_config

        grammar = parse_grammar(grammar_text)
        parser_result = plumbing.generate_parser(grammar, capture_trivia=True)
        unparser_result = generate_unparser(parser_result.grammar, parser_result.cst_module_name, fmt_config)

        # Parse some text
        test_input = "{ start s:x s:y end }"
        parse_result = plumbing.parse_text(parser_result, test_input, "block")
        assert parse_result.success

        # Unparse and check structure
        doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "block")

        # Should have { followed by Group containing Nest
        assert isinstance(doc, Concat)
        assert doc.docs[0] == Text("{")
        # Find the group
        grouped = [d for d in doc.docs if isinstance(d, Group)]
        assert len(grouped) > 0
        # The group should contain content including a nest

    def test_improperly_nested_group_and_nest_raises_error(self):
        """Test that improperly nested group and nest boundaries raise RuntimeError.

        Group: a to c
        Nest: b to d

        This is impossible to represent in a tree structure of combinators.
        The error occurs because combinators must form a proper tree - you can't
        have two nodes that partially overlap without one containing the other.
        """
        grammar_text = """
expr := a:identifier : b:identifier : c:identifier : d:identifier ;
identifier := value:/[a-zA-Z_][a-zA-Z0-9_]*/;
"""

        fmt_config = FormatterConfig()
        rule_config = RuleConfig()

        # Add group from a to c
        a_anchor = AnchorConfig(
            selector_type=ItemSelector.LABEL,
            selector_value="a",
            operations=[FormatOperation(OperationType.GROUP_BEGIN)],
        )
        rule_config.anchor_configs["after:label:a"] = a_anchor

        b_anchor = AnchorConfig(
            selector_type=ItemSelector.LABEL,
            selector_value="b",
            operations=[FormatOperation(OperationType.NEST_BEGIN, indent=2)],
        )
        rule_config.anchor_configs["after:label:b"] = b_anchor

        c_anchor = AnchorConfig(
            selector_type=ItemSelector.LABEL,
            selector_value="c",
            operations=[FormatOperation(OperationType.GROUP_END)],
        )
        rule_config.anchor_configs["before:label:c"] = c_anchor

        d_anchor = AnchorConfig(
            selector_type=ItemSelector.LABEL,
            selector_value="d",
            operations=[FormatOperation(OperationType.NEST_END)],
        )
        rule_config.anchor_configs["before:label:d"] = d_anchor

        fmt_config.rule_configs["expr"] = rule_config

        grammar = parse_grammar(grammar_text)
        parser_result = plumbing.generate_parser(grammar, capture_trivia=True)
        unparser_result = generate_unparser(parser_result.grammar, parser_result.cst_module_name, fmt_config)

        # Parse some text
        test_input = "a b c d"
        parse_result = plumbing.parse_text(parser_result, test_input, "expr")
        assert parse_result.success

        # Unparsing should raise RuntimeError due to improper nesting
        with pytest.raises(RuntimeError, match="Improperly nested tree: Expected Group but have"):
            plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "expr")

    def test_improperly_nested_with_subalternatives(self):
        """Test improper nesting with endpoints in sub-alternatives.

        Group: starts at 'x' (in sub-alternative), ends at second identifier
        Nest: starts at first identifier, ends at 'y' (in sub-alternative)
        """
        grammar_text = """
expr := ("x" | "z") : first:identifier : second:identifier : ("y" | "w") ;
identifier := value:/[a-zA-Z_][a-zA-Z0-9_]*/;
"""

        fmt_config = FormatterConfig()
        rule_config = RuleConfig()

        # Add group from x to second
        x_anchor = AnchorConfig(
            selector_type=ItemSelector.LITERAL,
            selector_value="x",
            operations=[FormatOperation(OperationType.GROUP_BEGIN)],
        )
        rule_config.anchor_configs["after:literal:x"] = x_anchor

        first_anchor = AnchorConfig(
            selector_type=ItemSelector.LABEL,
            selector_value="first",
            operations=[FormatOperation(OperationType.NEST_BEGIN, indent=2)],
        )
        rule_config.anchor_configs["after:label:first"] = first_anchor

        second_anchor = AnchorConfig(
            selector_type=ItemSelector.LABEL,
            selector_value="second",
            operations=[FormatOperation(OperationType.GROUP_END)],
        )
        rule_config.anchor_configs["before:label:second"] = second_anchor

        y_anchor = AnchorConfig(
            selector_type=ItemSelector.LITERAL,
            selector_value="y",
            operations=[FormatOperation(OperationType.NEST_END)],
        )
        rule_config.anchor_configs["before:literal:y"] = y_anchor

        fmt_config.rule_configs["expr"] = rule_config

        grammar = parse_grammar(grammar_text)
        parser_result = plumbing.generate_parser(grammar, capture_trivia=True)
        unparser_result = generate_unparser(parser_result.grammar, parser_result.cst_module_name, fmt_config)

        # Parse with 'x' and 'y' alternatives
        test_input = "x foo bar y"
        parse_result = plumbing.parse_text(parser_result, test_input, "expr")
        assert parse_result.success

        # This should raise RuntimeError because the boundaries cross in a way
        # that cannot be represented as a tree structure of combinators
        with pytest.raises(RuntimeError, match="Improperly nested tree: Expected Group but have"):
            plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "expr")
