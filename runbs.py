import sys

import astor  # type: ignore

from fltk import pygen
from fltk.fegen import bootstrap2gsm, bootstrap_parser, gsm, gsm2parser, gsm2tree
from fltk.fegen.pyrt import terminalsrc
from fltk.iir.context import create_default_context
from fltk.iir.py import compiler
from fltk.iir.py import reg as pyreg


def parse_grammar() -> gsm.Grammar:
    with open(sys.argv[1]) as grammarfile:
        terminals = terminalsrc.TerminalSource(grammarfile.read())
    parser = bootstrap_parser.Parser(terminalsrc=terminals)
    result = parser.apply__parse_grammar(0)
    assert result  # noqa: S101
    assert result.pos == len(terminals.terminals)  # noqa: S101
    cst2gsm = bootstrap2gsm.Cst2Gsm(terminals.terminals)
    grammar = cst2gsm.visit_grammar(result.result)
    return grammar


def gen_parser(grammar: gsm.Grammar) -> None:
    parser_filename, cst_filename, cst_module_name = sys.argv[2:]

    context = create_default_context()

    cst_module = pyreg.Module(cst_module_name.split("."))
    cstgen = gsm2tree.CstGenerator(grammar=grammar, py_module=cst_module, context=context)
    pgen = gsm2parser.ParserGenerator(grammar=grammar, cstgen=cstgen, context=context)

    parser_ast = compiler.compile_class(pgen.parser_class, context)
    imports = [
        pyreg.Module(("collections", "abc")),
        pyreg.Module(("typing",)),
        pyreg.Module(("fltk", "fegen", "pyrt", "errors")),
        pyreg.Module(("fltk", "fegen", "pyrt", "memo")),
        cst_module,
    ]

    parser_mod = pygen.module(module.import_path for module in imports)
    parser_mod.body.append(parser_ast)

    with open(parser_filename, "w") as parser_file:
        parser_file.write(astor.to_source(parser_mod))

    cst_mod = cstgen.gen_py_module()
    with open(cst_filename, "w") as cst_file:
        cst_file.write(astor.to_source(cst_mod))


if __name__ == "__main__":
    grammar = parse_grammar()
    gen_parser(grammar)
