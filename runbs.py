import dataclasses
import sys

import astor  # type: ignore

from fltk import pygen
from fltk.fegen import gsm, gsm2parser, gsm2tree
from fltk.fegen.pyrt import terminalsrc
from fltk.iir.py import compiler
from fltk.iir.py import reg as pyreg

import bootstrap_cst
import bootstrap_parser
import bootstrap2gsm


def parse_grammar() -> gsm.Grammar:
    with open(sys.argv[1], "r") as grammarfile:
        terminals = terminalsrc.TerminalSource(grammarfile.read())
    parser = bootstrap_parser.Parser(terminalsrc=terminals)
    result = parser.apply__parse_grammar(0)
    print(parser.error_tracker)
    assert result
    assert result.pos == len(terminals.terminals)
    cst2gsm = bootstrap2gsm.Cst2Gsm(terminals.terminals)
    print("cst_result", result)
    grammar = cst2gsm.visit_grammar(result.result)
    return grammar


def gen_parser(grammar: gsm.Grammar) -> None:
    parser_filename, cst_filename, cst_module_name = sys.argv[2:]

    cst_module = pyreg.Module(cst_module_name.split("."))
    cstgen = gsm2tree.CstGenerator(grammar=grammar, py_module=cst_module)
    pgen = gsm2parser.ParserGenerator(grammar=grammar, cstgen=cstgen)

    parser_ast = compiler.compile_class(pgen.parser_class)
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

    print(cstgen.rule_models)


if __name__ == "__main__":
    grammar = parse_grammar()
    gen_parser(grammar)
    print(grammar)
