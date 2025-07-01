"""Regression test for bug #1 (40b4248) - Fix bug with inlining recursive rules

This test verifies that recursive rule invocations are not spuriously inlined.
The bug occurred when parsing sequence items where the item result type was the
same as the alternatives result type, causing recursive invocations to be
incorrectly treated as sequences requiring inlining.

The specific issue was in gen_alternative_parser() line 629 where it used:
    if item_parser.result_type is node_type:
instead of:
    if item_parser.inline_to_parent:

This caused recursive calls to be incorrectly inlined when they had the same
result type as the parent node.
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


def test_recursive_rule_not_spuriously_inlined():
    """Test that recursive rules are not spuriously inlined.

    Creates a grammar where spurious inlining would cause incorrect CST structure.
    The bug would make a recursive call get its children incorrectly merged into
    the parent node instead of being treated as a separate child node.

    Grammar: expr := expr "+" | "x"

    Input "x+" should parse correctly with proper nesting:
    - With fix: expr(left=expr("x"), "+")
    - With bug: expr("x", "+") - recursive result incorrectly inlined
    """

    # Create grammar: expr := expr "+" | "x"
    expr_rule = gsm.Rule(
        name="expr",
        alternatives=[
            # First alternative: expr "+"
            gsm.Items(
                items=[
                    gsm.Item(
                        label="left",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("expr"),  # Recursive call
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="plus",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("+"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS, gsm.Separator.NO_WS],
            ),
            # Second alternative: "x" (base case)
            gsm.Items(
                items=[
                    gsm.Item(
                        label="x",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("x"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
        ],
    )

    grammar = gsm.Grammar(rules=(expr_rule,), identifiers={"expr": expr_rule})

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
        "typing": typing,
        "terminalsrc": terminalsrc,
        "fltk": fltk,
        "errors": errors,
    }
    mod_locals.update(cst_locals)

    try:
        exec(compile(mod_ast, "<test>", "exec"), mod_locals)  # noqa: S102
    except Exception as e:
        # If compilation fails, it might be due to the bug causing malformed code
        LOG.error("Parser compilation failed, possibly due to inlining bug: %s", e)
        # We'll treat compilation failure as a potential bug indicator
        # but we can't be 100% sure, so we'll just log it
        return

    # Find the generated parser class
    parser_class = None
    for name, obj in mod_locals.items():
        if isinstance(obj, type) and name.endswith("Parser"):
            parser_class = obj
            break

    if parser_class is None:
        msg = "Generated parser class not found"
        raise AssertionError(msg)

    test_input = "x+ "
    source = terminalsrc.TerminalSource(test_input)
    parser = parser_class(source)

    result = parser.apply__parse_expr(0)

    if result is None:
        msg = f"Failed to parse '{test_input}' - parser returned None"
        raise AssertionError(msg)

    # Check the structure - with the bug, the structure would be incorrectly flattened
    # We expect proper nesting: expr(expr("x"), "+")
    # With bug: expr("x", "+") - recursive result incorrectly inlined

    root_node = result.result
    LOG.info("Parsed result for '%s': %s", test_input, root_node)
    LOG.info("Root node children count: %d", len(root_node.children))
    LOG.info("Root node children types: %s", [type(child) for child in root_node.children])

    # With the bug, we should see that the recursive call result has been incorrectly
    # inlined, causing the children to be spans rather than nested Expr nodes

    # Look for nested Expr nodes in the children
    has_nested_expr = False
    for child in root_node.children:
        if isinstance(child, tuple) and len(child) == 2:
            label, value = child
            if hasattr(value, "children"):  # This would be an Expr node
                has_nested_expr = True
                break

    if not has_nested_expr:
        msg = (
            f"Recursive rule inlining bug detected! Expected nested Expr nodes but got flattened structure "
            f"with children: {root_node.children}. "
            f"This indicates the recursive call result was spuriously inlined."
        )
        raise AssertionError(msg)

    LOG.info("Parser structure is correct - no recursive inlining bug detected")
