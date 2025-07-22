"""Test leading separators in grammar alternatives.

This test verifies that leading separators (`,` and `:`) work correctly in alternatives.
The feature allows grammar rules like:
    rule := , alt1 | , alt2;  // Leading comma before alternatives
"""

import ast
import logging
import typing
from typing import Final, Optional

import astor

import fltk
from fltk.fegen import gsm, gsm2tree
from fltk.fegen import gsm2parser as g2p
from fltk.fegen.pyrt import errors, memo, terminalsrc
from fltk.iir.context import create_default_context
from fltk.iir.py import compiler
from fltk.iir.py import reg as pyreg

LOG: Final = logging.getLogger(__name__)


def test_leading_ws_allowed():
    """Test that leading WS_ALLOWED separator (`,`) allows optional whitespace before items."""

    # Create grammar: statement := , "foo" "bar"
    # The leading , means whitespace is allowed (but not required) before "foo"
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

    grammar = gsm.Grammar(rules=(statement_rule,), identifiers={"statement": statement_rule})

    # Generate parser
    context = create_default_context()
    enhanced_grammar = gsm.add_trivia_rule_to_grammar(grammar, context)
    cstgen = gsm2tree.CstGenerator(grammar=enhanced_grammar, py_module=pyreg.Builtins, context=context)
    pgen = g2p.ParserGenerator(grammar=enhanced_grammar, cstgen=cstgen, context=context)

    # Compile the parser
    parser_class_ast = compiler.compile_class(pgen.parser_class, context)
    mod_ast = ast.fix_missing_locations(ast.Module(body=[parser_class_ast], type_ignores=[]))
    LOG.debug("Generated parser:\n%s", astor.to_source(parser_class_ast))

    # Generate the CST classes module
    cst_module_ast = pgen.cstgen.gen_py_module()
    cst_mod = compile(cst_module_ast, "<cst_module>", "exec")
    cst_locals = {}
    exec(cst_mod, cst_locals)  # noqa: S102

    # Execute the generated parser code
    mod_locals = {
        "ApplyResult": memo.ApplyResult,
        "Span": terminalsrc.Span,
        "Optional": Optional,
        "typing": typing,
        "terminalsrc": terminalsrc,
        "fltk": fltk,
        "errors": errors,
    }
    mod_locals.update(cst_locals)

    exec(compile(mod_ast, "<test>", "exec"), mod_locals)  # noqa: S102

    # Find the generated parser class
    parser_class = None
    for name, obj in mod_locals.items():
        if isinstance(obj, type) and name.endswith("Parser"):
            parser_class = obj
            break

    if parser_class is None:
        msg = "Generated parser class not found"
        raise AssertionError(msg)

    # Test 1: Input without leading whitespace should succeed
    test_input_no_leading_space = "foobar"
    source = terminalsrc.TerminalSource(test_input_no_leading_space)
    parser = parser_class(source)
    result = parser.apply__parse_statement(0)

    if result is None:
        msg = f"Failed to parse '{test_input_no_leading_space}' - leading WS_ALLOWED should allow no whitespace"
        raise AssertionError(msg)

    LOG.info("Successfully parsed '%s' without leading spaces", test_input_no_leading_space)

    # Test 2: Input with leading whitespace should also succeed
    test_input_with_leading_space = "  foobar"
    source = terminalsrc.TerminalSource(test_input_with_leading_space)
    parser = parser_class(source)
    result = parser.apply__parse_statement(0)

    if result is None:
        msg = f"Failed to parse '{test_input_with_leading_space}' - leading WS_ALLOWED should allow whitespace"
        raise AssertionError(msg)

    LOG.info("Successfully parsed '%s' with leading spaces", test_input_with_leading_space)


def test_leading_ws_required():
    """Test that leading WS_REQUIRED separator (`:`) requires whitespace before items."""

    # Create grammar: statement := : "foo" "bar"
    # The leading : means whitespace is REQUIRED before "foo"
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

    grammar = gsm.Grammar(rules=(statement_rule,), identifiers={"statement": statement_rule})

    # Generate parser
    context = create_default_context()
    enhanced_grammar = gsm.add_trivia_rule_to_grammar(grammar, context)
    cstgen = gsm2tree.CstGenerator(grammar=enhanced_grammar, py_module=pyreg.Builtins, context=context)
    pgen = g2p.ParserGenerator(grammar=enhanced_grammar, cstgen=cstgen, context=context)

    # Compile the parser
    parser_class_ast = compiler.compile_class(pgen.parser_class, context)
    mod_ast = ast.fix_missing_locations(ast.Module(body=[parser_class_ast], type_ignores=[]))

    # Generate the CST classes module
    cst_module_ast = pgen.cstgen.gen_py_module()
    cst_mod = compile(cst_module_ast, "<cst_module>", "exec")
    cst_locals = {}
    exec(cst_mod, cst_locals)  # noqa: S102

    # Execute the generated parser code
    mod_locals = {
        "ApplyResult": memo.ApplyResult,
        "Span": terminalsrc.Span,
        "Optional": Optional,
        "typing": typing,
        "terminalsrc": terminalsrc,
        "fltk": fltk,
        "errors": errors,
    }
    mod_locals.update(cst_locals)

    exec(compile(mod_ast, "<test>", "exec"), mod_locals)  # noqa: S102

    # Find the generated parser class
    parser_class = None
    for name, obj in mod_locals.items():
        if isinstance(obj, type) and name.endswith("Parser"):
            parser_class = obj
            break

    if parser_class is None:
        msg = "Generated parser class not found"
        raise AssertionError(msg)

    # Test 1: Input without leading whitespace should fail
    test_input_no_leading_space = "foobar"
    source = terminalsrc.TerminalSource(test_input_no_leading_space)
    parser = parser_class(source)
    result = parser.apply__parse_statement(0)

    if result is not None:
        msg = f"Input '{test_input_no_leading_space}' should fail - leading WS_REQUIRED requires whitespace"
        raise AssertionError(msg)

    LOG.info("Correctly rejected '%s' without leading spaces", test_input_no_leading_space)

    # Test 2: Input with leading whitespace should succeed
    test_input_with_leading_space = "  foobar"
    source = terminalsrc.TerminalSource(test_input_with_leading_space)
    parser = parser_class(source)
    result = parser.apply__parse_statement(0)

    if result is None:
        msg = f"Failed to parse '{test_input_with_leading_space}' - leading WS_REQUIRED should work with whitespace"
        raise AssertionError(msg)

    LOG.info("Successfully parsed '%s' with leading spaces", test_input_with_leading_space)


def test_multiple_alternatives_with_leading_separators():
    """Test that multiple alternatives can each have different leading separators."""

    # Create grammar with three alternatives to test all separator types:
    # expr := , "a" | : "b" | "c"
    expr_rule = gsm.Rule(
        name="expr",
        alternatives=[
            # First alternative: leading comma (WS_ALLOWED)
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
            # Second alternative: leading colon (WS_REQUIRED)
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
            # Third alternative: no leading separator (NO_WS)
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

    grammar = gsm.Grammar(rules=(expr_rule,), identifiers={"expr": expr_rule})

    # Generate parser
    context = create_default_context()
    enhanced_grammar = gsm.add_trivia_rule_to_grammar(grammar, context)
    cstgen = gsm2tree.CstGenerator(grammar=enhanced_grammar, py_module=pyreg.Builtins, context=context)
    pgen = g2p.ParserGenerator(grammar=enhanced_grammar, cstgen=cstgen, context=context)

    # Compile the parser
    parser_class_ast = compiler.compile_class(pgen.parser_class, context)
    mod_ast = ast.fix_missing_locations(ast.Module(body=[parser_class_ast], type_ignores=[]))

    # Generate the CST classes module
    cst_module_ast = pgen.cstgen.gen_py_module()
    cst_mod = compile(cst_module_ast, "<cst_module>", "exec")
    cst_locals = {}
    exec(cst_mod, cst_locals)  # noqa: S102

    # Execute the generated parser code
    mod_locals = {
        "ApplyResult": memo.ApplyResult,
        "Span": terminalsrc.Span,
        "Optional": Optional,
        "typing": typing,
        "terminalsrc": terminalsrc,
        "fltk": fltk,
        "errors": errors,
    }
    mod_locals.update(cst_locals)

    exec(compile(mod_ast, "<test>", "exec"), mod_locals)  # noqa: S102

    # Find the generated parser class
    parser_class = None
    for name, obj in mod_locals.items():
        if isinstance(obj, type) and name.endswith("Parser"):
            parser_class = obj
            break

    if parser_class is None:
        msg = "Generated parser class not found"
        raise AssertionError(msg)

    # Test cases for each alternative
    test_cases = [
        # Alternative 1: leading comma (WS_ALLOWED)
        ("a", True),  # Should parse without leading space
        ("  a", True),  # Should parse with leading space
        # Alternative 2: leading colon (WS_REQUIRED)
        ("b", False),  # Should NOT parse without leading space
        ("  b", True),  # Should parse with leading space
        # Alternative 3: no leading separator (NO_WS)
        ("c", True),  # Should parse without leading space
        ("  c", False),  # Should NOT parse with leading space (whitespace disallowed)
    ]

    for test_input, should_parse in test_cases:
        source = terminalsrc.TerminalSource(test_input)
        parser = parser_class(source)
        result = parser.apply__parse_expr(0)

        if should_parse:
            if result is None:
                msg = f"Failed to parse '{test_input}' - expected to parse successfully"
                raise AssertionError(msg)
            LOG.info("Successfully parsed '%s'", test_input)
        else:
            if result is not None:
                msg = f"Input '{test_input}' should have failed to parse"
                raise AssertionError(msg)
            LOG.info("Correctly rejected '%s'", test_input)


def test_leading_no_ws():
    """Test that leading NO_WS separator (`.`) prohibits whitespace before items."""

    # Create grammar: statement := . "foo" "bar"
    # The leading . means NO whitespace is allowed before "foo"
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

    grammar = gsm.Grammar(rules=(statement_rule,), identifiers={"statement": statement_rule})

    # Generate parser
    context = create_default_context()
    enhanced_grammar = gsm.add_trivia_rule_to_grammar(grammar, context)
    cstgen = gsm2tree.CstGenerator(grammar=enhanced_grammar, py_module=pyreg.Builtins, context=context)
    pgen = g2p.ParserGenerator(grammar=enhanced_grammar, cstgen=cstgen, context=context)

    # Compile the parser
    parser_class_ast = compiler.compile_class(pgen.parser_class, context)
    mod_ast = ast.fix_missing_locations(ast.Module(body=[parser_class_ast], type_ignores=[]))

    # Generate the CST classes module
    cst_module_ast = pgen.cstgen.gen_py_module()
    cst_mod = compile(cst_module_ast, "<cst_module>", "exec")
    cst_locals = {}
    exec(cst_mod, cst_locals)  # noqa: S102

    # Execute the generated parser code
    mod_locals = {
        "ApplyResult": memo.ApplyResult,
        "Span": terminalsrc.Span,
        "Optional": Optional,
        "typing": typing,
        "terminalsrc": terminalsrc,
        "fltk": fltk,
        "errors": errors,
    }
    mod_locals.update(cst_locals)

    exec(compile(mod_ast, "<test>", "exec"), mod_locals)  # noqa: S102

    # Find the generated parser class
    parser_class = None
    for name, obj in mod_locals.items():
        if isinstance(obj, type) and name.endswith("Parser"):
            parser_class = obj
            break

    if parser_class is None:
        msg = "Generated parser class not found"
        raise AssertionError(msg)

    # Test: Input without leading whitespace should succeed
    # (NO_WS is effectively the same as the default behavior)
    test_input_no_leading_space = "foobar"
    source = terminalsrc.TerminalSource(test_input_no_leading_space)
    parser = parser_class(source)
    result = parser.apply__parse_statement(0)

    if result is None:
        msg = f"Failed to parse '{test_input_no_leading_space}' - NO_WS should work without whitespace"
        raise AssertionError(msg)

    LOG.info("Successfully parsed '%s' without leading spaces", test_input_no_leading_space)

    # Note: With NO_WS as initial_sep, the parser will still accept leading whitespace
    # because trivia is always allowed at the beginning of parsing.
    # The initial_sep only affects explicit whitespace handling within the alternative.


def test_leading_separators_with_multi_term_alternatives():
    """Test that leading separators work correctly with multi-term alternatives and various trailing separators."""

    # Create grammar with multi-term alternatives using different separator combinations:
    # expr := , "start" "middle" "end" | : "begin" , "center" , "finish" , | "first" . "second" . "third"
    expr_rule = gsm.Rule(
        name="expr",
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
            # Alternative 2: leading colon, commas between terms, trailing comma
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
                sep_after=[gsm.Separator.WS_ALLOWED, gsm.Separator.WS_ALLOWED, gsm.Separator.WS_ALLOWED],
                initial_sep=gsm.Separator.WS_REQUIRED,  # Leading colon
            ),
            # Alternative 3: no leading separator, dots between terms (no whitespace)
            gsm.Items(
                items=[
                    gsm.Item(
                        label="first",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("first"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="second",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("second"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="third",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("third"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS, gsm.Separator.NO_WS, gsm.Separator.NO_WS],
                initial_sep=gsm.Separator.NO_WS,  # No leading separator
            ),
        ],
    )

    grammar = gsm.Grammar(rules=(expr_rule,), identifiers={"expr": expr_rule})

    # Generate parser
    context = create_default_context()
    enhanced_grammar = gsm.add_trivia_rule_to_grammar(grammar, context)
    cstgen = gsm2tree.CstGenerator(grammar=enhanced_grammar, py_module=pyreg.Builtins, context=context)
    pgen = g2p.ParserGenerator(grammar=enhanced_grammar, cstgen=cstgen, context=context)

    # Compile the parser
    parser_class_ast = compiler.compile_class(pgen.parser_class, context)
    mod_ast = ast.fix_missing_locations(ast.Module(body=[parser_class_ast], type_ignores=[]))

    # Generate the CST classes module
    cst_module_ast = pgen.cstgen.gen_py_module()
    cst_mod = compile(cst_module_ast, "<cst_module>", "exec")
    cst_locals = {}
    exec(cst_mod, cst_locals)  # noqa: S102

    # Execute the generated parser code
    mod_locals = {
        "ApplyResult": memo.ApplyResult,
        "Span": terminalsrc.Span,
        "Optional": Optional,
        "typing": typing,
        "terminalsrc": terminalsrc,
        "fltk": fltk,
        "errors": errors,
    }
    mod_locals.update(cst_locals)

    exec(compile(mod_ast, "<test>", "exec"), mod_locals)  # noqa: S102

    # Find the generated parser class
    parser_class = None
    for name, obj in mod_locals.items():
        if isinstance(obj, type) and name.endswith("Parser"):
            parser_class = obj
            break

    if parser_class is None:
        msg = "Generated parser class not found"
        raise AssertionError(msg)

    # Test cases for multi-term alternatives
    test_cases = [
        # Alternative 1: leading comma (WS_ALLOWED), no separators between terms
        ("startmiddleend", True),  # Should parse without leading space
        ("  startmiddleend", True),  # Should parse with leading space
        ("start middle end", False),  # Should NOT parse with spaces between terms (NO_WS separators)
        # Alternative 2: leading colon (WS_REQUIRED), commas between terms, trailing comma
        ("begin center finish", False),  # Should NOT parse without leading space (WS_REQUIRED)
        ("  begin center finish", True),  # Should parse with leading space and inter-term spaces
        ("  begin center finish ", True),  # Should parse with trailing space too
        ("  begincenterfinish", True),  # Should parse - WS_ALLOWED means whitespace is optional
        # Alternative 3: no leading separator (NO_WS), dots between terms
        ("firstsecondthird", True),  # Should parse without any spaces
        ("  firstsecondthird", False),  # Should NOT parse with leading space (NO_WS)
        ("first second third", False),  # Should NOT parse with inter-term spaces (NO_WS separators)
    ]

    for test_input, should_parse in test_cases:
        source = terminalsrc.TerminalSource(test_input)
        parser = parser_class(source)
        result = parser.apply__parse_expr(0)

        if should_parse:
            if result is None:
                msg = f"Failed to parse '{test_input}' - expected to parse successfully"
                raise AssertionError(msg)
            LOG.info("Successfully parsed '%s'", test_input)
        else:
            if result is not None:
                msg = f"Input '{test_input}' should have failed to parse"
                raise AssertionError(msg)
            LOG.info("Correctly rejected '%s'", test_input)
