"""Regression test for bug #2 (c28a2c1) - Fix bug in WS_REQUIRED

This test verifies that the WS_REQUIRED separator (`:`) correctly requires whitespace
between grammar items. The bug was in the walrus operator precedence in gsm2parser.py
lines 612 and 627.

The specific issues were:
1. Line 612: if sep := alternative.sep_after[item_idx] != gsm.Separator.NO_WS:
   Should be: if (sep := alternative.sep_after[item_idx]) != gsm.Separator.NO_WS:

2. Line 627: orelse=sep == gsm.Separator.WS_REQUIRED,
   Should be: orelse=(sep == gsm.Separator.WS_REQUIRED),

Due to operator precedence, `sep` was being assigned a boolean value instead of the
actual Separator enum value, causing WS_REQUIRED logic to fail.
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


def test_ws_required_separator():
    """Test that WS_REQUIRED separator correctly requires whitespace between items.

    Creates a grammar where WS_REQUIRED should force whitespace between items:
    Grammar: statement := "if" : "true" : "then"

    With the bug, the WS_REQUIRED logic fails because `sep` gets assigned a boolean
    instead of the Separator enum value, so the required whitespace check doesn't work.

    Test inputs:
    - "if true then" (with spaces) - should parse successfully
    - "iftruethen" (no spaces) - should fail to parse due to WS_REQUIRED
    """

    # Create grammar: statement := "if" : "true" : "then"
    # The : separator means whitespace is REQUIRED between items
    statement_rule = gsm.Rule(
        name="statement",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="if_kw",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("if"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="condition",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("true"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="then_kw",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("then"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                # WS_REQUIRED after first two items
                sep_after=[gsm.Separator.WS_REQUIRED, gsm.Separator.WS_REQUIRED, gsm.Separator.NO_WS],
            ),
        ],
    )

    grammar = gsm.Grammar(rules=(statement_rule,), identifiers={"statement": statement_rule})

    # Generate parser
    context = create_default_context()
    # Add trivia rule to grammar
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

    try:
        exec(compile(mod_ast, "<test>", "exec"), mod_locals)  # noqa: S102
    except Exception as e:
        LOG.error("Parser compilation failed: %s", e)
        raise

    # Find the generated parser class
    parser_class = None
    for name, obj in mod_locals.items():
        if isinstance(obj, type) and name.endswith("Parser"):
            parser_class = obj
            break

    if parser_class is None:
        msg = "Generated parser class not found"
        raise AssertionError(msg)

    # Test 1: Input with required whitespace should succeed
    test_input_with_spaces = "if true then "
    source = terminalsrc.TerminalSource(test_input_with_spaces)
    parser = parser_class(source)
    result = parser.apply__parse_statement(0)

    if result is None:
        msg = f"Failed to parse '{test_input_with_spaces}' - this should succeed with proper WS_REQUIRED handling"
        raise AssertionError(msg)

    LOG.info("Successfully parsed '%s' with spaces", test_input_with_spaces)

    # Test 2: Input without required whitespace should fail
    test_input_no_spaces = "iftruethen "
    source = terminalsrc.TerminalSource(test_input_no_spaces)
    parser = parser_class(source)
    result = parser.apply__parse_statement(0)

    if result is not None:
        msg = (
            f"WS_REQUIRED bug detected! Input '{test_input_no_spaces}' should fail to parse "
            f"because whitespace is required between 'if', 'true', and 'then', but it parsed successfully. "
            f"This indicates the WS_REQUIRED logic is not working due to the walrus operator precedence bug."
        )
        raise AssertionError(msg)

    LOG.info("Correctly rejected '%s' without spaces - WS_REQUIRED is working", test_input_no_spaces)


def test_ws_required_vs_ws_allowed():
    """Test that WS_REQUIRED behaves differently from WS_ALLOWED.

    Creates two similar grammars to demonstrate the difference:
    - ws_required_rule: "a" : "b" (whitespace required)
    - ws_allowed_rule: "a" , "b" (whitespace allowed but not required)
    """

    # Grammar 1: WS_REQUIRED
    ws_required_rule = gsm.Rule(
        name="ws_required",
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
            ),
        ],
    )

    # Grammar 2: WS_ALLOWED
    ws_allowed_rule = gsm.Rule(
        name="ws_allowed",
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
                sep_after=[gsm.Separator.WS_ALLOWED, gsm.Separator.NO_WS],
            ),
        ],
    )

    def test_grammar(rule, rule_name, should_parse_without_ws):
        grammar = gsm.Grammar(rules=(rule,), identifiers={rule_name: rule})
        context = create_default_context()
        # Add trivia rule to grammar
        enhanced_grammar = gsm.add_trivia_rule_to_grammar(grammar, context)
        cstgen = gsm2tree.CstGenerator(grammar=enhanced_grammar, py_module=pyreg.Builtins, context=context)
        pgen = g2p.ParserGenerator(grammar=enhanced_grammar, cstgen=cstgen, context=context)

        parser_class_ast = compiler.compile_class(pgen.parser_class, context)
        mod_ast = ast.fix_missing_locations(ast.Module(body=[parser_class_ast], type_ignores=[]))

        cst_module_ast = pgen.cstgen.gen_py_module()
        cst_mod = compile(cst_module_ast, "<cst_module>", "exec")
        cst_locals = {}
        exec(cst_mod, cst_locals)  # noqa: S102

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

        parser_class = None
        for name, obj in mod_locals.items():
            if isinstance(obj, type) and name.endswith("Parser"):
                parser_class = obj
                break

        if parser_class is None:
            msg = f"Generated parser class not found for {rule_name}"
            raise AssertionError(msg)

        # Test parsing "ab " (no whitespace between items, but trailing space for parser)
        source = terminalsrc.TerminalSource("ab ")
        parser = parser_class(source)
        result = parser.apply__parse_ws_required(0) if rule_name == "ws_required" else parser.apply__parse_ws_allowed(0)

        if should_parse_without_ws:
            if result is None:
                msg = f"Grammar {rule_name} should parse 'ab' but failed"
                raise AssertionError(msg)
        elif result is not None:
            msg = f"Grammar {rule_name} should NOT parse 'ab' but succeeded"
            raise AssertionError(msg)

    # WS_ALLOWED should parse "ab " (no spaces between items)
    test_grammar(ws_allowed_rule, "ws_allowed", should_parse_without_ws=True)
    LOG.info("WS_ALLOWED correctly parsed 'ab ' without spaces between items")

    # WS_REQUIRED should NOT parse "ab " (no spaces between items)
    test_grammar(ws_required_rule, "ws_required", should_parse_without_ws=False)
    LOG.info("WS_REQUIRED correctly rejected 'ab ' without spaces between items")
