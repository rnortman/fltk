"""Unit tests for memo.py"""
import ast
import astor  # type: ignore
import logging
from typing import Final

from fltk.fegen import gsm
from fltk.fegen import gsm2parser as g2p
from fltk.iir import model as iir
from fltk.iir.py import compiler

LOG: Final = logging.getLogger(__name__)


def test_single() -> None:
    pgen = g2p.ParserGenerator(grammar=gsm.Grammar(rules=(), vars=(), identifiers={}))
    item = gsm.Item(
        label='label',
        disposition=gsm.Disposition.INCLUDE,
        term=gsm.Literal("asdf"),
        quantifier=gsm.REQUIRED
    )
    for thing in pgen.gen_item_parser_single_or_optional(item=item,
                                                         base_name='foo',
                                                         pos_param=iir.Param(name="pos",
                                                                             typ=iir.UInt64,
                                                                             ref_type=iir.RefType.VALUE,
                                                                             mutable=False),
                                                         consume_term_expr=iir.FalseBool,
                                                         term_result_type=iir.Bool):
        LOG.info("thing: %s", thing)
        assert isinstance(thing, iir.Method)
        py_ast = compiler.compile_function(thing)
        LOG.info("py_ast: %s", py_ast)
        LOG.info(astor.dump_tree(py_ast))
        LOG.info(astor.to_source(py_ast))
        LOG.info(ast.unparse(py_ast))
