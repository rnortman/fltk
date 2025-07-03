"""Unit tests for memo.py"""

import ast
import logging
import typing
from typing import Final, Optional, cast
from unittest import mock

import astor  # type: ignore

import fltk
from fltk.fegen import bootstrap, gsm, gsm2tree
from fltk.fegen import gsm2parser as g2p
from fltk.fegen.pyrt import memo, terminalsrc
from fltk.iir import model as iir
from fltk.iir.context import CompilerContext, create_default_context
from fltk.iir.py import compiler
from fltk.iir.py import reg as pyreg

LOG: Final = logging.getLogger(__name__)


def create_parser_generator(grammar: gsm.Grammar, context: CompilerContext | None = None) -> g2p.ParserGenerator:
    """Helper function to create ParserGenerator with trivia rule added."""
    if context is None:
        context = create_default_context()
    # Add trivia rule to grammar
    enhanced_grammar = gsm.add_trivia_rule_to_grammar(grammar, context)
    cstgen = gsm2tree.CstGenerator(grammar=enhanced_grammar, py_module=pyreg.Builtins, context=context)
    return g2p.ParserGenerator(grammar=enhanced_grammar, cstgen=cstgen, context=context)


def test_single() -> None:
    context = create_default_context()
    empty_grammar = gsm.Grammar(rules=(), identifiers={})
    pgen = create_parser_generator(empty_grammar, context)
    LITERAL: Final = "as'\\\"df"  # noqa: N806 Make sure escaping works well
    item = gsm.Item(
        label="testlabel",
        disposition=gsm.Disposition.INCLUDE,
        term=gsm.Literal(LITERAL),
        quantifier=gsm.REQUIRED,
    )
    parser_info = pgen.gen_item_parser(path=("itemfoo",), node_type=cast(iir.Type, None), item=item)
    method = pgen.parser_class.block.get_leaf_scope().lookup(name=parser_info.apply_name, recursive=False)
    LOG.info("method: %s", method)
    assert isinstance(method, iir.Method)
    assert method.name is not None
    method_ast = compiler.compile_function(method, context)
    LOG.info(astor.dump_tree(method_ast))
    LOG.info(astor.to_source(method_ast))

    mod_ast = ast.fix_missing_locations(ast.Module(body=[method_ast], type_ignores=[]))
    mod = compile(mod_ast, "<string>", "exec")
    mod_locals = {
        "ApplyResult": memo.ApplyResult,
        "Span": terminalsrc.Span,
        "Optional": Optional,
        "typing": typing,
        "fltk": fltk,
    }
    exec(mod, mod_locals)  # noqa: S102
    LOG.info(mod_locals.keys())
    item_parser = mod_locals[method.name]
    assert callable(item_parser)

    parser = mock.Mock(spec_set=["consume_literal"])
    EXPECT: Final = memo.ApplyResult(42, terminalsrc.Span(0, 42))  # noqa: N806
    parser.consume_literal = mock.Mock(return_value=EXPECT)
    assert item_parser(parser, 0) == EXPECT
    assert parser.consume_literal.mock_calls == [mock.call(pos=0, literal=LITERAL)]
    parser.consume_literal.return_value = None
    parser.consume_literal.reset_mock()
    assert item_parser(parser, 11) is None
    assert parser.consume_literal.mock_calls == [mock.call(pos=11, literal=LITERAL)]
    LOG.info(pgen.parser_class)
    LOG.info(compiler.compile_class(pgen.parser_class, context))
    LOG.info(astor.to_source(compiler.compile_class(pgen.parser_class, context)))


def test_bootstrap() -> None:
    context = create_default_context()
    pgen = create_parser_generator(bootstrap.grammar, context)
    LOG.info(pgen)
    LOG.info(pgen.parser_class)
    LOG.info(compiler.compile_class(pgen.parser_class, context))
    LOG.info(astor.dump_tree(compiler.compile_class(pgen.parser_class, context)))
    LOG.info(astor.to_source(compiler.compile_class(pgen.parser_class, context)))
