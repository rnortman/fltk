"""Tests for join support in the unparser."""

from fltk import plumbing
from fltk.unparse.combinators import HARDLINE, LINE, NBSP, SOFTLINE, Concat, Text


def test_join_entire_rule():
    """Test a rule with a join around all items."""
    grammar_src = """
    list := item , ("," , item)* ;
    item := value:/[a-z]+/ ;
    """

    fmt_src = """
    ws_allowed: bsp;
    ws_required: bsp;

    rule list {
        join hard;
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
    test_input = "abc,def,ghi"
    parse_result = plumbing.parse_text(parser_result, test_input, "list")
    assert parse_result.success

    doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "list")

    # Check the exact structure - Join should be expanded with hardline separators
    # Join replaces the grammar's default separators with its own
    assert doc == Concat(
        (
            Text("abc"),
            HARDLINE,  # from join
            Text(","),
            HARDLINE,  # from join
            Text("def"),
            HARDLINE,  # from join
            Text(","),
            HARDLINE,  # from join
            Text("ghi"),
        )
    )


def test_join_with_text_separator():
    """Test a join with a text separator."""
    grammar_src = """
    args := "(" , arg , ("," , arg)* , ")" ;
    arg := name:/[a-z]+/ ;
    """

    fmt_src = """
    ws_allowed: bsp;
    ws_required: bsp;

    rule args {
        join from after "(" to before ")" text(" | ");
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
    test_input = "(foo,bar,baz)"
    parse_result = plumbing.parse_text(parser_result, test_input, "args")
    assert parse_result.success

    doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "args")

    # Should have join from after "(" to before ")"
    # Join is expanded, so we see Text(" | ") separators between elements
    assert doc == Concat(
        (
            Text("("),
            LINE,
            Text("foo"),
            Text(" | "),  # join separator
            Text(","),
            Text(" | "),  # join separator
            Text("bar"),
            Text(" | "),  # join separator (no comma after bar in this path)
            Text(","),
            Text(" | "),  # join separator
            Text("baz"),
            LINE,
            Text(")"),
        )
    )


def test_join_from_anchor():
    """Test a join that starts at a specific anchor."""
    grammar_src = """
    stmt := "select" : fields:field_list : "from" : table:identifier ;
    field_list := field , ("," , field)* ;
    field := name:/[a-z]+/ ;
    identifier := id:/[a-z]+/ ;
    """

    fmt_src = """
    ws_allowed: bsp;
    ws_required: bsp;

    rule stmt {
        join from fields bsp;
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
    test_input = "select foo,bar from table"
    parse_result = plumbing.parse_text(parser_result, test_input, "stmt")
    assert parse_result.success

    doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "stmt")

    # The join should start from fields label
    # Join is expanded with LINE separators between all elements from fields onward
    assert doc == Concat(
        (Text("select"), LINE, Text("foo"), LINE, Text(","), LINE, Text("bar"), LINE, Text("from"), LINE, Text("table"))
    )


def test_join_to_anchor():
    """Test a join that ends at a specific anchor."""
    grammar_src = """
    block := "{" : stmt , (";" , stmt)* , ";" , "}" ;
    stmt := cmd:/[a-z]+/ ;
    """

    fmt_src = """
    ws_allowed: bsp;
    ws_required: bsp;

    rule block {
        join to before "}" hard;
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
    test_input = "{ foo ; bar ; }"
    parse_result = plumbing.parse_text(parser_result, test_input, "block")
    assert parse_result.success

    doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "block")

    # The join should go up to (but not include) "}"
    # Join is expanded with HARDLINE separators that replace grammar separators
    assert doc == Concat(
        (
            Text("{"),
            HARDLINE,  # join separator
            Text("foo"),
            HARDLINE,  # join separator
            Text(";"),
            HARDLINE,  # join separator
            Text("bar"),
            HARDLINE,  # join separator
            Text(";"),
            LINE,
            Text("}"),
        )
    )


def test_join_from_to_anchors():
    """Test a join with both from and to anchors."""
    grammar_src = """
    array := "[" , elem , ("," , elem)* , "]" ;
    elem := val:/[0-9]+/ ;
    """

    fmt_src = """
    ws_allowed: bsp;
    ws_required: bsp;

    rule array {
        join from after "[" to before "]" concat([text(","), soft]);
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
    test_input = "[1,2,3]"
    parse_result = plumbing.parse_text(parser_result, test_input, "array")
    assert parse_result.success

    doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "array")

    # The join should be from after "[" to before "]"
    # Join is expanded with concat([text(","), soft]) as separator
    assert doc == Concat(
        (
            Text("["),
            LINE,
            Text("1"),
            Text(","),  # join separator
            SOFTLINE,  # join separator
            Text(","),  # grammar comma
            Text(","),  # join separator
            SOFTLINE,  # join separator
            Text("2"),
            Text(","),  # join separator
            SOFTLINE,  # join separator
            Text(","),  # grammar comma
            Text(","),  # join separator
            SOFTLINE,  # join separator
            Text("3"),
            LINE,
            Text("]"),
        )
    )


def test_join_with_label_anchor():
    """Test a join using a label as anchor."""
    grammar_src = """
    func := "def" : name:identifier , "(" , params:param_list , ")" , ":" ;
    identifier := id:/[a-z]+/ ;
    param_list := (param , ("," , param)*)? ;
    param := p:/[a-z]+/ ;
    """

    fmt_src = """
    ws_allowed: bsp;
    ws_required: bsp;

    rule func {
        join from params to ")" nbsp;
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
    test_input = "def foo(a,b,c):"
    parse_result = plumbing.parse_text(parser_result, test_input, "func")
    assert parse_result.success

    doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "func")

    # The join should be from params to ")"
    # Join is expanded with NBSP separators that replace grammar separators
    assert doc == Concat(
        (
            Text("def"),
            LINE,
            Text("foo"),
            LINE,
            Text("("),
            LINE,
            Text("a"),
            NBSP,  # join separator
            Text(","),
            NBSP,  # join separator
            Text("b"),
            NBSP,  # join separator
            Text(","),
            NBSP,  # join separator
            Text("c"),
            NBSP,  # join separator
            Text(")"),
            LINE,
            Text(":"),
        )
    )


def test_multiple_joins_in_rule():
    """Test multiple join operations in a single rule."""
    grammar_src = """
    record := "{" : fields:field_list , ";" , methods:method_list , "}" ;
    field_list := field , ("," , field)* ;
    method_list := method , ("," , method)* ;
    field := f:/[a-z]+/ ;
    method := m:/[A-Z]+/ ;
    """

    fmt_src = """
    ws_allowed: bsp;
    ws_required: bsp;

    rule record {
        join from fields to before ";" soft;
        join from methods to before "}" hard;
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
    test_input = "{ foo , bar ; GET , POST }"
    parse_result = plumbing.parse_text(parser_result, test_input, "record")
    assert parse_result.success

    doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "record")

    # Should have two separate joins
    # First join from fields to ";", second join from methods to "}"
    assert doc == Concat(
        (
            Text("{"),
            LINE,
            Text("foo"),  # Start of first join
            SOFTLINE,  # join separator
            Text(","),
            SOFTLINE,  # join separator
            Text("bar"),
            # Final separator here comes from ws_allowed
            LINE,
            Text(";"),  # End of first join
            LINE,
            Text("GET"),  # Start of second join
            HARDLINE,  # join separator
            Text(","),
            HARDLINE,  # join separator
            Text("POST"),
            # Final separator from ws_allowed
            LINE,
            Text("}"),  # End of second join
        )
    )


def test_empty_join():
    """Test join behavior with empty content."""
    grammar_src = """
    maybe_list := "[" , (item , ("," , item)*)? , "]" ;
    item := val:/[a-z]+/ ;
    """

    fmt_src = """
    ws_allowed: soft;
    ws_required: bsp;

    rule maybe_list {
        join from after "[" to before "]" hard;
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

    # Parse and unparse empty list
    test_input = "[]"
    parse_result = plumbing.parse_text(parser_result, test_input, "maybe_list")
    assert parse_result.success

    doc = plumbing.unparse_cst(unparser_result, parse_result.cst, test_input, "maybe_list")

    # Join with no elements should just have the brackets
    # Since join is expanded and there's nothing between [ and ], only the ws_allowed-created separator appears.
    assert doc == Concat((Text("["), SOFTLINE, Text("]")))
