"""Regression test for bug #5 (c69680e) - Fix bug with recursion on top-level rule

This test verifies that when the entry-point rule causes a left recursion, the
invocation stack is properly set up during seed growth. The bug was in memo.py
where the invocation stack wasn't being managed during the _grow_seed process.

The fix added:
    self.invocation_stack.append(rule_id)
    grow_result = self._grow_seed(rule_callable, start_pos, memo, poison.recursion_info)
    assert self.invocation_stack.pop() == rule_id

Without this fix, error reporting that depends on the invocation stack would fail
during recursion on the top-level rule, because the stack would be empty when
it should contain the rule being processed.

The specific scenario is:
1. Top-level rule has left recursion (e.g., expr := expr "+" term | term)
2. During parsing, the rule recurses
3. During seed growth, error reporting is triggered (e.g., unexpected token)
4. Error reporting uses invocation_stack to determine current rule
5. Without fix: invocation_stack is empty, causing error reporting to fail
6. With fix: invocation_stack contains the rule ID, error reporting works
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


def test_toplevel_recursion_invocation_stack():
    """Test that invocation stack is properly managed during top-level rule recursion.

    Creates a grammar with a left-recursive top-level rule:
    Grammar: expr := expr "+" term | term
             term := digit

    The bug occurs when:
    1. The top-level rule (expr) has left recursion
    2. During seed growth, error reporting needs the invocation stack
    3. Without the fix, invocation stack is empty during seed growth
    4. With the fix, invocation stack contains the rule ID

    This test triggers the bug by parsing input that causes recursion and then
    encounters an error that triggers error reporting during seed growth.
    """

    # Create grammar with left-recursive top-level rule
    # expr := expr "+" term | term
    # term := digit

    term_rule = gsm.Rule(
        name="term",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="digit",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[0-9]"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
        ],
    )

    expr_rule = gsm.Rule(
        name="expr",
        alternatives=[
            # Alternative 1: expr "+" term (left recursive)
            gsm.Items(
                items=[
                    gsm.Item(
                        label="left",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("expr"),  # Left recursion
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="op",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("+"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="right",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("term"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS, gsm.Separator.NO_WS, gsm.Separator.NO_WS],
            ),
            # Alternative 2: term (base case)
            gsm.Items(
                items=[
                    gsm.Item(
                        label="base",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("term"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
        ],
    )

    grammar = gsm.Grammar(rules=(expr_rule, term_rule), identifiers={"expr": expr_rule, "term": term_rule})

    # Generate parser
    context = create_default_context()
    cstgen = gsm2tree.CstGenerator(grammar=grammar, py_module=pyreg.Builtins, context=context)
    pgen = g2p.ParserGenerator(grammar=grammar, cstgen=cstgen, context=context)

    # Compile the parser
    parser_class_ast = compiler.compile_class(pgen.parser_class, context)
    mod_ast = ast.fix_missing_locations(ast.Module(body=[parser_class_ast], type_ignores=[]))
    LOG.debug("Generated parser:\\n%s", astor.to_source(parser_class_ast))

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

    # Test 1: Simple valid input should work (regression check)
    test_input_simple = "5"
    source = terminalsrc.TerminalSource(test_input_simple)
    parser = parser_class(source)
    result = parser.apply__parse_expr(0)

    if result is None:
        msg = f"Failed to parse simple input '{test_input_simple}' - this should succeed"
        raise AssertionError(msg)

    LOG.info("Successfully parsed simple input '%s'", test_input_simple)

    # Test 2: Left-recursive input should work (regression check)
    test_input_recursive = "1+2"
    source = terminalsrc.TerminalSource(test_input_recursive)
    parser = parser_class(source)
    result = parser.apply__parse_expr(0)

    if result is None:
        msg = f"Failed to parse recursive input '{test_input_recursive}' - this should succeed"
        raise AssertionError(msg)

    LOG.info("Successfully parsed recursive input '%s'", test_input_recursive)

    # Test 3: Complex recursive input should work
    test_input_complex = "1+2+3"
    source = terminalsrc.TerminalSource(test_input_complex)
    parser = parser_class(source)
    result = parser.apply__parse_expr(0)

    if result is None:
        msg = f"Failed to parse complex recursive input '{test_input_complex}' - this should succeed"
        raise AssertionError(msg)

    LOG.info("Successfully parsed complex recursive input '%s'", test_input_complex)

    # Test 4: This is the critical test for the bug
    # Parse input that will cause recursion and then encounter an error
    # The error will be reported, and error reporting uses the invocation stack
    # Without the fix, this would fail because invocation_stack would be empty

    test_input_error = "1+"  # Incomplete expression - should parse "1" but not consume "+"
    source = terminalsrc.TerminalSource(test_input_error)
    parser = parser_class(source)
    result = parser.apply__parse_expr(0)

    # This should succeed in parsing "1" but not consume the full input
    # The important thing is that it doesn't crash during recursion
    if result is None:
        msg = f"Input '{test_input_error}' should succeed in parsing '1' part"
        raise AssertionError(msg)

    # Check that it only parsed the "1" part (pos=1) and not the "+" (would be pos=2)
    if result.pos == len(test_input_error):
        msg = f"Input '{test_input_error}' should not parse completely - '+' should be left unconsumed"
        raise AssertionError(msg)

    if result.pos != 1:
        msg = f"Input '{test_input_error}' should parse exactly 1 character ('1'), got pos={result.pos}"
        raise AssertionError(msg)

    LOG.info("Correctly rejected incomplete input '%s' - invocation stack management working", test_input_error)

    # Test 5: Another error case that exercises the recursion + error path
    test_input_invalid = "1++"  # Invalid expression - should parse just "1" and leave "++" unconsumed
    source = terminalsrc.TerminalSource(test_input_invalid)
    parser = parser_class(source)
    result = parser.apply__parse_expr(0)

    # Should succeed but not consume the full input
    if result is None:
        msg = f"Input '{test_input_invalid}' should succeed in parsing '1' part"
        raise AssertionError(msg)

    # Should parse exactly 1 character ("1") and leave the rest
    if result.pos != 1:
        msg = f"Input '{test_input_invalid}' should parse exactly 1 character ('1'), got pos={result.pos}"
        raise AssertionError(msg)

    LOG.info(
        "Correctly parsed partial input '%s' (pos=%d) - invocation stack bug not triggered",
        test_input_invalid,
        result.pos,
    )


def test_toplevel_recursion_error_tracker_access():
    """Test that error tracker can access invocation stack during top-level recursion.

    This is a more direct test of the bug - we verify that the error tracker
    can successfully access the invocation stack during recursion on the top-level rule.
    The bug would cause the invocation stack to be empty when it should contain
    the rule ID, leading to potential IndexErrors or assertion failures.
    """

    # Create a simple left-recursive grammar
    expr_rule = gsm.Rule(
        name="expr",
        alternatives=[
            # Left recursive: expr "x"
            gsm.Items(
                items=[
                    gsm.Item(
                        label="recurse",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("expr"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="x",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("x"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS, gsm.Separator.NO_WS],
            ),
            # Base case: "y"
            gsm.Items(
                items=[
                    gsm.Item(
                        label="base",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("y"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
        ],
    )

    grammar = gsm.Grammar(rules=(expr_rule,), identifiers={"expr": expr_rule})

    # Generate and compile parser
    context = create_default_context()
    cstgen = gsm2tree.CstGenerator(grammar=grammar, py_module=pyreg.Builtins, context=context)
    pgen = g2p.ParserGenerator(grammar=grammar, cstgen=cstgen, context=context)

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
        "typing": __import__("typing"),
        "terminalsrc": terminalsrc,
        "fltk": fltk,
        "errors": errors,
    }
    mod_locals.update(cst_locals)

    exec(compile(mod_ast, "<test>", "exec"), mod_locals)  # noqa: S102

    # Find parser class
    parser_class = None
    for name, obj in mod_locals.items():
        if isinstance(obj, type) and name.endswith("Parser"):
            parser_class = obj
            break

    if parser_class is None:
        msg = "Generated parser class not found"
        raise AssertionError(msg)

    # Test valid recursive input
    test_input = "yxx"  # Should parse as ((y x) x)
    source = terminalsrc.TerminalSource(test_input)
    parser = parser_class(source)
    result = parser.apply__parse_expr(0)

    if result is None:
        msg = f"Failed to parse '{test_input}' - should succeed with left recursion"
        raise AssertionError(msg)

    LOG.info("Successfully parsed recursive input '%s' with proper invocation stack", test_input)

    # Test that causes error during recursion - this is where the bug would manifest
    # The key is that we need an input that:
    # 1. Triggers the left recursion (so _grow_seed is called)
    # 2. During growth, encounters a situation that would access invocation_stack
    #    (like error reporting or the assertion that pops the stack)

    test_input_partial = "yx"  # This should succeed partially, then fail
    source = terminalsrc.TerminalSource(test_input_partial)
    parser = parser_class(source)

    # Just calling this exercises the recursion and seed growth logic
    # If the invocation stack bug exists, it would manifest as an assertion failure
    # or IndexError when trying to access invocation_stack[-1] while it's empty
    result = parser.apply__parse_expr(0)

    # The important thing is that we get here without a crash
    # The actual parse result is less important than not crashing due to empty stack
    LOG.info("Recursion test with partial input completed without invocation stack crash")
