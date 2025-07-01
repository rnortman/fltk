"""Test case for parser trailing character bug.

This test demonstrates a bug where generated parsers fail to consume the entire
input when the input doesn't end with whitespace. The parser correctly parses
partial input but fails to reach the end of the source text.

For example:
- "x+" parses only "x" (stops at position 1 instead of 2)
- "x+ " parses the complete "x+" (reaches position 2)

This suggests the parser has difficulty consuming the final non-whitespace
character in the input stream.
"""

import ast
import logging
from typing import Final, Optional

import fltk
from fltk.fegen import gsm, gsm2tree
from fltk.fegen import gsm2parser as g2p
from fltk.fegen.pyrt import errors, memo, terminalsrc
from fltk.iir.context import create_default_context
from fltk.iir.py import compiler
from fltk.iir.py import reg as pyreg

LOG: Final = logging.getLogger(__name__)


def test_trailing_character_parsing():
    """Test that demonstrates the trailing character parsing bug.

    Creates a simple grammar and tests inputs with and without trailing whitespace
    to show the parser's inability to consume final non-whitespace characters.
    """

    # Create simple grammar: expr := "x" "+"
    expr_rule = gsm.Rule(
        name="expr",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="x",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("x"),
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

    # Test 1: Input WITH trailing whitespace (expected to work)
    test_input_with_space = "x+ "
    source = terminalsrc.TerminalSource(test_input_with_space)
    parser = parser_class(source)
    result_with_space = parser.apply__parse_expr(0)

    if result_with_space is None:
        msg = f"Failed to parse '{test_input_with_space}' - this should succeed"
        raise AssertionError(msg)

    LOG.info(
        "Input with trailing space '%s': parsed to position %d (expected %d)",
        test_input_with_space,
        result_with_space.pos,
        len("x+"),
    )

    # Test 2: Input WITHOUT trailing whitespace (demonstrates the bug)
    test_input_no_space = "x+"
    source = terminalsrc.TerminalSource(test_input_no_space)
    parser = parser_class(source)
    result_no_space = parser.apply__parse_expr(0)

    if result_no_space is None:
        # This is the bug - parser fails completely on input without trailing whitespace
        msg = (
            f"TRAILING CHARACTER BUG CONFIRMED! "
            f"Parser failed to parse '{test_input_no_space}' without trailing whitespace, "
            f"but successfully parsed '{test_input_with_space}' with trailing whitespace. "
            f"This demonstrates that the parser requires trailing whitespace to complete parsing."
        )
        raise AssertionError(msg)

    LOG.info(
        "Input without trailing space '%s': parsed to position %d (expected %d)",
        test_input_no_space,
        result_no_space.pos,
        len(test_input_no_space),
    )

    # Check if partial parsing occurred (shouldn't reach here due to the None check above)
    expected_pos = len(test_input_no_space)  # Should be 2 for "x+"
    actual_pos = result_no_space.pos

    if actual_pos != expected_pos:
        msg = (
            f"Partial trailing character parsing bug detected! "
            f"Input '{test_input_no_space}' (length {len(test_input_no_space)}) "
            f"was only parsed to position {actual_pos}, expected position {expected_pos}. "
            f"This indicates the parser cannot consume the final non-whitespace character."
        )
        raise AssertionError(msg)

    LOG.info("No trailing character bug detected - parser correctly consumed entire input")


def test_multiple_trailing_character_cases():
    """Test various cases to confirm the trailing character behavior."""

    # Create grammar: simple := "a" "b" "c"
    simple_rule = gsm.Rule(
        name="simple",
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
                    gsm.Item(
                        label="c",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("c"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS, gsm.Separator.NO_WS, gsm.Separator.NO_WS],
            ),
        ],
    )

    grammar = gsm.Grammar(rules=(simple_rule,), identifiers={"simple": simple_rule})

    # Generate parser
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

    parser_class = None
    for name, obj in mod_locals.items():
        if isinstance(obj, type) and name.endswith("Parser"):
            parser_class = obj
            break

    if parser_class is None:
        msg = "Generated parser class not found"
        raise AssertionError(msg)

    # Test cases to confirm the pattern
    test_cases = [
        ("abc", "abc"),  # No trailing space
        ("abc ", "abc"),  # With trailing space
        ("abc\n", "abc"),  # With trailing newline
        ("abc\t", "abc"),  # With trailing tab
    ]

    bugs_found = []

    for test_input, expected_content in test_cases:
        source = terminalsrc.TerminalSource(test_input)
        parser = parser_class(source)
        result = parser.apply__parse_simple(0)

        if result is None:
            LOG.error("Failed to parse '%s'", repr(test_input))
            continue

        expected_pos = len(expected_content)
        actual_pos = result.pos

        LOG.info("Input %s: parsed to position %d (expected %d)", repr(test_input), actual_pos, expected_pos)

        if actual_pos != expected_pos:
            bugs_found.append(
                {
                    "input": test_input,
                    "expected_pos": expected_pos,
                    "actual_pos": actual_pos,
                    "content": expected_content,
                }
            )

    if bugs_found:
        bug_details = []
        for bug in bugs_found:
            bug_details.append(f"Input {bug['input']!r}: parsed to {bug['actual_pos']}, expected {bug['expected_pos']}")

        msg = (
            "Trailing character parsing bugs detected:\n"
            + "\n".join(bug_details)
            + "\nThis confirms the parser has difficulty consuming final non-whitespace characters."
        )
        raise AssertionError(msg)

    LOG.info("All test cases parsed correctly - no trailing character bugs found")


if __name__ == "__main__":
    test_trailing_character_parsing()
    test_multiple_trailing_character_cases()
