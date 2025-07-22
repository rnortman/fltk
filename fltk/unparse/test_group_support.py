"""Tests for group support in the unparser."""

from fltk import plumbing
from fltk.unparse.combinators import LINE, Concat, Group, Text


def test_group_entire_rule():
    """Test a rule with a group around all items."""
    grammar_src = """
    expr := left:identifier . "+" . right:identifier ;
    identifier := name:/[a-z]+/ ;
    """

    fmt_src = """
    ws_allowed: bsp;
    ws_required: bsp;

    rule expr {
        group;
    }
    """

    # Parse grammar and format config
    gsm_grammar = plumbing.parse_grammar(grammar_src)
    config = plumbing.parse_format_config(fmt_src)

    # Generate parser and unparser
    parser_result = plumbing.generate_parser(gsm_grammar, capture_trivia=True)
    unparser_result = plumbing.generate_unparser(
        parser_result.grammar, parser_result.cst_module_name, formatter_config=config
    )

    # Parse and unparse
    test_input = "abc+def"
    parse_result = plumbing.parse_text(parser_result, test_input, "expr")
    assert parse_result.success

    doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "expr")

    # Check the exact structure
    assert doc == Group(Concat((Text("abc"), Text("+"), Text("def"))))


def test_group_from_anchor():
    """Test a group that starts at a specific anchor."""
    grammar_src = """
    stmt := "if" : condition:expr : "then" : body:expr ;
    expr := id:/[a-z]+/ ;
    """

    fmt_src = """
    ws_allowed: bsp;
    ws_required: bsp;

    rule stmt {
        group from "then";
    }
    """

    # Parse grammar and format config
    gsm_grammar = plumbing.parse_grammar(grammar_src)
    config = plumbing.parse_format_config(fmt_src)

    # Generate parser and unparser
    parser_result = plumbing.generate_parser(gsm_grammar, capture_trivia=True)
    unparser_result = plumbing.generate_unparser(
        parser_result.grammar, parser_result.cst_module_name, formatter_config=config
    )

    # Parse and unparse
    test_input = "if abc then def"
    parse_result = plumbing.parse_text(parser_result, test_input, "stmt")
    assert parse_result.success

    doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "stmt")

    # The result should have a group starting at "then"
    assert doc == Concat((Text("if"), LINE, Text("abc"), LINE, Group(Concat((Text("then"), LINE, Text("def"))))))


def test_group_to_anchor():
    """Test a group that ends at a specific anchor."""
    grammar_src = """
    stmt := "begin" : first:expr : ";" : second:expr : "end" ;
    expr := id:/[a-z]+/ ;
    """

    fmt_src = """
    ws_allowed: bsp;
    ws_required: bsp;

    rule stmt {
        group to ";";
    }
    """

    # Parse grammar and format config
    gsm_grammar = plumbing.parse_grammar(grammar_src)
    config = plumbing.parse_format_config(fmt_src)

    # Generate parser and unparser
    parser_result = plumbing.generate_parser(gsm_grammar, capture_trivia=True)
    unparser_result = plumbing.generate_unparser(
        parser_result.grammar, parser_result.cst_module_name, formatter_config=config
    )

    # Parse and unparse
    test_input = "begin abc ; def end"
    parse_result = plumbing.parse_text(parser_result, test_input, "stmt")
    assert parse_result.success

    doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "stmt")

    # The result should have a group from beginning to ";"
    assert doc == Concat(
        (Group(Concat((Text("begin"), LINE, Text("abc"), LINE, Text(";")))), LINE, Text("def"), LINE, Text("end"))
    )


def test_group_from_to_anchors():
    """Test a group with both from and to anchors."""
    grammar_src = """
    func := "func" : name:identifier , "(" , params:param_list , ")" , "{" , body:stmts , "}" ;
    identifier := id:/[a-z]+/ ;
    param_list := (param , ("," . param)*)? ;
    param := p:/[a-z]+/ ;
    stmts := st:"pass" ;
    """

    fmt_src = """
    ws_allowed: bsp;
    ws_required: bsp;

    rule func {
        group from "(" to ")";
    }
    """

    # Parse grammar and format config
    gsm_grammar = plumbing.parse_grammar(grammar_src)
    config = plumbing.parse_format_config(fmt_src)

    # Generate parser and unparser
    parser_result = plumbing.generate_parser(gsm_grammar, capture_trivia=True)
    unparser_result = plumbing.generate_unparser(
        parser_result.grammar, parser_result.cst_module_name, formatter_config=config
    )

    # Parse and unparse
    test_input = "func foo (a,b) {pass}"
    parse_result = plumbing.parse_text(parser_result, test_input, "func")
    assert parse_result.success

    doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "func")

    # The result should have a group from "(" to ")"
    assert doc == Concat(
        (
            Text("func"),
            LINE,
            Text("foo"),
            LINE,
            Group(Concat((Text("("), LINE, Text("a"), LINE, Text(","), Text("b"), LINE, Text(")")))),
            LINE,
            Text("{"),
            LINE,
            Text("pass"),
            LINE,
            Text("}"),
        )
    )


def test_group_with_label_anchor():
    """Test a group using a label as anchor."""
    grammar_src = """
    assign := target:identifier : "=" : value:expr ;
    identifier := id:/[a-z]+/ ;
    expr := e:/[0-9]+/ ;
    """

    fmt_src = """
    ws_allowed: bsp;
    ws_required: bsp;

    rule assign {
        group from value;
    }
    """

    # Parse grammar and format config
    gsm_grammar = plumbing.parse_grammar(grammar_src)
    config = plumbing.parse_format_config(fmt_src)

    # Generate parser and unparser
    parser_result = plumbing.generate_parser(gsm_grammar, capture_trivia=True)
    unparser_result = plumbing.generate_unparser(
        parser_result.grammar, parser_result.cst_module_name, formatter_config=config
    )

    # Parse and unparse
    test_input = "x = 42"
    parse_result = plumbing.parse_text(parser_result, test_input, "assign")
    assert parse_result.success

    doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "assign")

    # The result should have a group starting at the value
    assert doc == Concat((Text("x"), LINE, Text("="), LINE, Group(Text("42"))))


def test_group_across_nested_alternatives():
    """Test a group that spans across nested alternative parsers."""
    grammar_src = """
    foo := a:"a" , (b:"b" , c:"c" | d:"d") , (e:"e" , f:"f" | g:"g" , h:"h") , i:"i" ;
    """

    fmt_src = """
    ws_allowed: bsp;
    ws_required: bsp;

    rule foo {
        group from b to f;
    }
    """

    # Parse grammar and format config
    gsm_grammar = plumbing.parse_grammar(grammar_src)
    config = plumbing.parse_format_config(fmt_src)

    # Generate parser and unparser
    parser_result = plumbing.generate_parser(gsm_grammar, capture_trivia=True)
    unparser_result = plumbing.generate_unparser(
        parser_result.grammar, parser_result.cst_module_name, formatter_config=config
    )

    # Test case 1: b,c path and e,f path
    test_input1 = "a b c e f i"
    parse_result1 = plumbing.parse_text(parser_result, test_input1, "foo")
    assert parse_result1.success

    doc1 = plumbing.unparse_cst(unparser_result, parse_result1.cst, test_input1, "foo")

    # Check exact structure - group should contain b through f
    assert doc1 == Concat(
        (
            Text("a"),
            LINE,
            Group(Concat((Text("b"), LINE, Text("c"), LINE, Text("e"), LINE, Text("f")))),
            LINE,
            Text("i"),
        )
    )

    # Test case 2: d path and g,h path (group should span from b=d to f=h)
    test_input2 = "a d g h i"
    parse_result2 = plumbing.parse_text(parser_result, test_input2, "foo")
    assert parse_result2.success

    doc2 = plumbing.unparse_cst(unparser_result, parse_result2.cst, test_input2, "foo")

    # The group behavior here is tricky - we don't have 'b' or 'f' in this path
    # So the group anchors won't match and we shouldn't have a group
    assert doc2 == Concat((Text("a"), LINE, Text("d"), LINE, Text("g"), LINE, Text("h"), LINE, Text("i")))
