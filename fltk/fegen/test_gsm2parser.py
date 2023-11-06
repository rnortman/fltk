"""Unit tests for memo.py"""

# ruff: noqa: S101, PLR2004

import ast
import logging
from typing import Final, Optional
from unittest import mock

import astor  # type: ignore

from fltk.fegen import bootstrap, gsm, gsm2tree
from fltk.fegen import gsm2parser as g2p
from fltk.fegen.pyrt import memo, terminalsrc
from fltk.iir import model as iir
from fltk.iir.py import compiler
from fltk.iir.py import reg as pyreg

LOG: Final = logging.getLogger(__name__)


def test_single() -> None:
    return
    pgen = g2p.ParserGenerator(grammar=gsm.Grammar(rules=(), vars=(), identifiers={}))
    LITERAL: Final = "as'\\\"df"  # noqa: N806 Make sure escaping works well
    item = gsm.Item(
        label="testlabel",
        disposition=gsm.Disposition.INCLUDE,
        term=gsm.Literal(LITERAL),
        quantifier=gsm.REQUIRED,
    )
    parser_info = pgen.gen_item_parser(path=("itemfoo",), item=item)
    method = pgen.parser_class.block.get_leaf_scope().lookup(name=parser_info.apply_name, recursive=False)
    LOG.info("method: %s", method)
    assert isinstance(method, iir.Method)
    assert method.name is not None
    method_ast = compiler.compile_function(method)
    LOG.info(astor.dump_tree(method_ast))
    LOG.info(astor.to_source(method_ast))

    mod_ast = ast.fix_missing_locations(ast.Module(body=[method_ast], type_ignores=[]))
    mod = compile(mod_ast, "<string>", "exec")
    mod_locals = {"ApplyResult": memo.ApplyResult, "Span": terminalsrc.Span, "Optional": Optional}
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
    LOG.info(compiler.compile_class(pgen.parser_class))
    LOG.info(astor.to_source(compiler.compile_class(pgen.parser_class)))


def test_bootstrap() -> None:
    pgen = g2p.ParserGenerator(
        grammar=bootstrap.grammar,
        cstgen=gsm2tree.CstGenerator(grammar=bootstrap.grammar, py_module=pyreg.Builtins),
    )
    LOG.info(pgen)
    LOG.info(pgen.parser_class)
    LOG.info(compiler.compile_class(pgen.parser_class))
    LOG.info(astor.dump_tree(compiler.compile_class(pgen.parser_class)))
    LOG.info(astor.to_source(compiler.compile_class(pgen.parser_class)))
