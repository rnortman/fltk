import sys

from fltk.fegen import bootstrap2gsm, bootstrap_parser, emit, gsm
from fltk.fegen.pyrt import terminalsrc


def parse_grammar() -> gsm.Grammar:
    with open(sys.argv[1]) as grammarfile:
        terminals = terminalsrc.TerminalSource(grammarfile.read())
    parser = bootstrap_parser.Parser(terminalsrc=terminals)
    result = parser.apply__parse_grammar(0)
    assert result
    assert result.pos == len(terminals.terminals)
    cst2gsm = bootstrap2gsm.Cst2Gsm(terminals.terminals)
    grammar = cst2gsm.visit_grammar(result.result)
    return grammar


def gen_parser(grammar: gsm.Grammar) -> None:
    parser_filename, cst_filename, cst_module_name = sys.argv[2:]
    emit.write_generated_modules(grammar, parser_filename, cst_filename, cst_module_name)


if __name__ == "__main__":
    grammar = parse_grammar()
    gen_parser(grammar)
