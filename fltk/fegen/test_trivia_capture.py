"""Test trivia node capture functionality."""

import ast
import logging
from typing import Final, Optional

import fltk
from fltk.fegen import gsm, gsm2tree
from fltk.fegen import gsm2parser as g2p
from fltk.fegen.pyrt import errors, memo, terminalsrc

# TriviaNode is now generated from grammar rules, not imported
from fltk.iir.context import create_default_context
from fltk.iir.py import compiler
from fltk.iir.py import reg as pyreg

LOG: Final = logging.getLogger(__name__)


def test_trivia_capture_enabled():
    """Test that trivia nodes appear when capture_trivia=True."""
    # Create simple grammar: hello , world
    rule = gsm.Rule(
        name="test_rule",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="first",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("hello"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="second",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("world"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.WS_ALLOWED, gsm.Separator.NO_WS],
            ),
        ],
    )

    grammar = gsm.Grammar(rules=(rule,), identifiers={"test_rule": rule})

    # Create context with trivia capture enabled
    context = create_default_context()
    context.capture_trivia = True

    # Enhance grammar with built-in trivia rule
    enhanced_grammar = gsm.add_trivia_rule_to_grammar(grammar, context)

    # Generate and compile parser
    cstgen = gsm2tree.CstGenerator(grammar=enhanced_grammar, py_module=pyreg.Builtins, context=context)
    pgen = g2p.ParserGenerator(grammar=enhanced_grammar, cstgen=cstgen, context=context)

    parser_class_ast = compiler.compile_class(pgen.parser_class, context)
    mod_ast = ast.fix_missing_locations(ast.Module(body=[parser_class_ast], type_ignores=[]))

    # Generate CST classes
    cst_module_ast = pgen.cstgen.gen_py_module()
    cst_mod = compile(cst_module_ast, "<cst_module>", "exec")
    cst_locals = {}
    exec(cst_mod, cst_locals)  # noqa: S102

    # Execute generated code
    mod_locals = {
        "ApplyResult": memo.ApplyResult,
        "Span": terminalsrc.Span,
        "Optional": Optional,
        "typing": __import__("typing"),
        "terminalsrc": terminalsrc,
        "fltk": fltk,
        "errors": errors,
        # TriviaNode is now generated and available in cst_locals
    }
    mod_locals.update(cst_locals)

    exec(compile(mod_ast, "<test>", "exec"), mod_locals)  # noqa: S102

    # Find parser class
    parser_class = None
    for name, obj in mod_locals.items():
        if isinstance(obj, type) and name.endswith("Parser"):
            parser_class = obj
            break

    assert parser_class is not None, "Could not find generated parser class"

    # Test parsing with whitespace
    test_input = "hello world"
    source = terminalsrc.TerminalSource(test_input)
    parser = parser_class(source)
    result = parser.apply__parse_test_rule(0)

    assert result is not None, f"Failed to parse '{test_input}'"

    # Check for trivia nodes in result
    root_node = result.result
    LOG.info("Root node children count: %d", len(root_node.children))
    LOG.info("Root node children: %s", root_node.children)

    # Look for trivia nodes (either TriviaNode or generated Trivia)
    has_trivia_nodes = False
    for child in root_node.children:
        if isinstance(child, tuple) and len(child) == 2:
            label, value = child
            if hasattr(value, "__class__") and (
                "TriviaNode" in value.__class__.__name__ or "Trivia" in value.__class__.__name__
            ):
                has_trivia_nodes = True
                LOG.info("Found trivia node: %s with span: %s", value, value.span)
                break

    assert has_trivia_nodes, "Expected trivia nodes when capture_trivia=True"


def test_trivia_capture_disabled():
    """Test that trivia nodes don't appear when capture_trivia=False."""
    # Create same grammar as above
    rule = gsm.Rule(
        name="test_rule",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="first",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("hello"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="second",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("world"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.WS_ALLOWED, gsm.Separator.NO_WS],
            ),
        ],
    )

    grammar = gsm.Grammar(rules=(rule,), identifiers={"test_rule": rule})

    # Create context with trivia capture disabled (default)
    context = create_default_context()
    assert not context.capture_trivia, "Expected capture_trivia to default to False"

    # Enhance grammar (no trivia rule will be added since capture_trivia=False)
    enhanced_grammar = gsm.add_trivia_rule_to_grammar(grammar, context)

    # Generate and compile parser
    cstgen = gsm2tree.CstGenerator(grammar=enhanced_grammar, py_module=pyreg.Builtins, context=context)
    pgen = g2p.ParserGenerator(grammar=enhanced_grammar, cstgen=cstgen, context=context)

    parser_class_ast = compiler.compile_class(pgen.parser_class, context)
    mod_ast = ast.fix_missing_locations(ast.Module(body=[parser_class_ast], type_ignores=[]))

    # Generate CST classes
    cst_module_ast = pgen.cstgen.gen_py_module()
    cst_mod = compile(cst_module_ast, "<cst_module>", "exec")
    cst_locals = {}
    exec(cst_mod, cst_locals)  # noqa: S102

    # Execute generated code
    mod_locals = {
        "ApplyResult": memo.ApplyResult,
        "Span": terminalsrc.Span,
        "Optional": Optional,
        "typing": __import__("typing"),
        "terminalsrc": terminalsrc,
        "fltk": fltk,
        "errors": errors,
        # TriviaNode is now generated and available in cst_locals
    }
    mod_locals.update(cst_locals)

    exec(compile(mod_ast, "<test>", "exec"), mod_locals)  # noqa: S102

    # Find parser class
    parser_class = None
    for name, obj in mod_locals.items():
        if isinstance(obj, type) and name.endswith("Parser"):
            parser_class = obj
            break

    assert parser_class is not None, "Could not find generated parser class"

    # Test parsing with whitespace
    test_input = "hello world"
    source = terminalsrc.TerminalSource(test_input)
    parser = parser_class(source)
    result = parser.apply__parse_test_rule(0)

    assert result is not None, f"Failed to parse '{test_input}'"

    # Check that no trivia nodes exist
    root_node = result.result
    LOG.info("Root node children count: %d", len(root_node.children))
    LOG.info("Root node children: %s", root_node.children)

    # Look for trivia nodes (should not find any)
    has_trivia_nodes = False
    for child in root_node.children:
        if isinstance(child, tuple) and len(child) == 2:
            label, value = child
            if hasattr(value, "__class__") and "TriviaNode" in value.__class__.__name__:
                has_trivia_nodes = True
                break

    assert not has_trivia_nodes, "Expected no trivia nodes when capture_trivia=False"


if __name__ == "__main__":
    # Enable debug logging for testing
    logging.basicConfig(level=logging.INFO)

    test_trivia_capture_enabled()
    test_trivia_capture_disabled()
