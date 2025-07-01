"""Regression test for bug #4 (3d8fa19) - Fix bug with detecting empty N-ary nodes

This test verifies that the empty check for N-ary nodes with + quantifier (one or more)
is properly placed to detect when no items are matched. The bug was in gsm2parser.py
where the empty check was inside the loop block instead of after the loop.

The buggy code was:
    if item.quantifier.min() != gsm.Arity.ZERO:
        loop.block.if_(iir.IsEmpty(result_var.fld.children)).block.return_(iir.Failure(result_type))

This should be:
    if item.quantifier.min() != gsm.Arity.ZERO:
        result.block.if_(iir.IsEmpty(result_var.fld.children)).block.return_(iir.Failure(result_type))

Because the empty check was inside the loop, it was never executed when the loop never ran
(i.e., when there were no matching items), causing the parser to incorrectly succeed when
parsing items with + quantifier that matched zero items.
"""

import ast
import logging
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


def test_empty_nary_quantifier_plus():
    """Test that + quantifier properly fails when no items match.

    Creates a grammar where a + quantifier should fail if no items are matched:
    Grammar: numbers := digit+

    With the bug, the empty check is inside the loop block, so it never executes
    when the loop doesn't run (i.e., when there are no matching digits).
    This causes the parser to incorrectly succeed when parsing text that contains
    no digits, when it should fail because + requires at least one match.

    Test inputs:
    - "123 " (contains digits) - should parse successfully
    - "abc " (no digits) - should fail to parse due to + quantifier requiring at least one digit
    """

    # Create grammar: numbers := digit+
    # digit is a regex pattern that matches single digits
    numbers_rule = gsm.Rule(
        name="numbers",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="digits",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[0-9]"),
                        quantifier=gsm.ONE_OR_MORE,  # + quantifier - requires at least one match
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
        ],
    )

    grammar = gsm.Grammar(rules=(numbers_rule,), identifiers={"numbers": numbers_rule})

    # Generate parser
    context = create_default_context()
    cstgen = gsm2tree.CstGenerator(grammar=grammar, py_module=pyreg.Builtins, context=context)
    pgen = g2p.ParserGenerator(grammar=grammar, cstgen=cstgen, context=context)

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
        "typing": __import__("typing"),
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

    # Test 1: Input with digits should succeed
    test_input_with_digits = "123 "
    source = terminalsrc.TerminalSource(test_input_with_digits)
    parser = parser_class(source)
    result = parser.apply__parse_numbers(0)

    if result is None:
        msg = f"Failed to parse '{test_input_with_digits}' - this should succeed when digits are present"
        raise AssertionError(msg)

    LOG.info("Successfully parsed '%s' with digits", test_input_with_digits)

    # Test 2: Input without digits should fail
    test_input_no_digits = "abc "
    source = terminalsrc.TerminalSource(test_input_no_digits)
    parser = parser_class(source)
    result = parser.apply__parse_numbers(0)

    if result is not None:
        msg = (
            f"Empty N-ary bug detected! Input '{test_input_no_digits}' should fail to parse "
            f"because + quantifier requires at least one digit match, but it parsed successfully. "
            f"This indicates the empty check is in the wrong location (inside loop instead of after loop)."
        )
        raise AssertionError(msg)

    LOG.info("Correctly rejected '%s' without digits - + quantifier empty check is working", test_input_no_digits)


def test_empty_nary_quantifier_star():
    """Test that * quantifier properly succeeds when no items match.

    Creates a grammar where a * quantifier should succeed even if no items are matched:
    Grammar: maybe_numbers := digit*

    This test ensures that our fix for + quantifier doesn't break * quantifier behavior.

    Test inputs:
    - "123 " (contains digits) - should parse successfully
    - "abc " (no digits) - should also parse successfully because * allows zero matches
    """

    # Create grammar: maybe_numbers := digit*
    maybe_numbers_rule = gsm.Rule(
        name="maybe_numbers",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="digits",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[0-9]"),
                        quantifier=gsm.ZERO_OR_MORE,  # * quantifier - allows zero matches
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
        ],
    )

    grammar = gsm.Grammar(rules=(maybe_numbers_rule,), identifiers={"maybe_numbers": maybe_numbers_rule})

    # Generate parser
    context = create_default_context()
    cstgen = gsm2tree.CstGenerator(grammar=grammar, py_module=pyreg.Builtins, context=context)
    pgen = g2p.ParserGenerator(grammar=grammar, cstgen=cstgen, context=context)

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
        "typing": __import__("typing"),
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

    # Test 1: Input with digits should succeed
    test_input_with_digits = "123 "
    source = terminalsrc.TerminalSource(test_input_with_digits)
    parser = parser_class(source)
    result = parser.apply__parse_maybe_numbers(0)

    if result is None:
        msg = f"Failed to parse '{test_input_with_digits}' - this should succeed when digits are present"
        raise AssertionError(msg)

    LOG.info("Successfully parsed '%s' with digits using * quantifier", test_input_with_digits)

    # Test 2: Input without digits should also succeed (different from + quantifier)
    test_input_no_digits = "abc "
    source = terminalsrc.TerminalSource(test_input_no_digits)
    parser = parser_class(source)
    result = parser.apply__parse_maybe_numbers(0)

    if result is None:
        msg = f"Failed to parse '{test_input_no_digits}' - * quantifier should succeed even with no digit matches"
        raise AssertionError(msg)

    LOG.info("Successfully parsed '%s' without digits using * quantifier - zero matches allowed", test_input_no_digits)


def test_empty_nary_edge_cases():
    """Test edge cases for empty N-ary node detection.

    Tests more complex scenarios to ensure the empty check works correctly
    in various contexts.
    """

    # Create grammar with multiple quantifiers: complex := word+ space* digit+
    complex_rule = gsm.Rule(
        name="complex",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="words",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[a-zA-Z]+"),
                        quantifier=gsm.ONE_OR_MORE,  # + quantifier
                    ),
                    gsm.Item(
                        label="spaces",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r" "),
                        quantifier=gsm.ZERO_OR_MORE,  # * quantifier
                    ),
                    gsm.Item(
                        label="digits",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[0-9]+"),
                        quantifier=gsm.ONE_OR_MORE,  # + quantifier
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS, gsm.Separator.NO_WS, gsm.Separator.NO_WS],
            ),
        ],
    )

    grammar = gsm.Grammar(rules=(complex_rule,), identifiers={"complex": complex_rule})

    # Generate parser
    context = create_default_context()
    cstgen = gsm2tree.CstGenerator(grammar=grammar, py_module=pyreg.Builtins, context=context)
    pgen = g2p.ParserGenerator(grammar=grammar, cstgen=cstgen, context=context)

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
        "typing": __import__("typing"),
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

    # Test valid input: words, optional spaces, digits
    test_input_valid = "hello123 "
    source = terminalsrc.TerminalSource(test_input_valid)
    parser = parser_class(source)
    result = parser.apply__parse_complex(0)

    if result is None:
        msg = f"Failed to parse '{test_input_valid}' - this should succeed"
        raise AssertionError(msg)

    LOG.info("Successfully parsed '%s' with complex grammar", test_input_valid)

    # Test invalid input: no words (first + quantifier should fail)
    test_input_no_words = "123 "
    source = terminalsrc.TerminalSource(test_input_no_words)
    parser = parser_class(source)
    result = parser.apply__parse_complex(0)

    if result is not None:
        msg = f"Should have failed to parse '{test_input_no_words}' - first + quantifier requires words"
        raise AssertionError(msg)

    LOG.info("Correctly rejected '%s' - first + quantifier empty check working", test_input_no_words)

    # Test invalid input: words but no digits (last + quantifier should fail)
    test_input_no_digits = "hello "
    source = terminalsrc.TerminalSource(test_input_no_digits)
    parser = parser_class(source)
    result = parser.apply__parse_complex(0)

    if result is not None:
        msg = f"Should have failed to parse '{test_input_no_digits}' - last + quantifier requires digits"
        raise AssertionError(msg)

    LOG.info("Correctly rejected '%s' - last + quantifier empty check working", test_input_no_digits)
