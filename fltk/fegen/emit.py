"""Write a grammar's parser module, CST module and CST protocol module to disk.

Used by both bootstrap regeneration paths: ``fltk.fegen.bootstrap`` (hand-written GSM seed) and
``runbs.py`` (bootstrap grammar file).  The full CLI (``fltk.fegen.genparser``) has its own writer
with the options this one does not offer.
"""

import os
import pathlib

import astor  # type: ignore

from fltk import pygen
from fltk.fegen import gsm, gsm2parser, gsm2tree, naming
from fltk.iir.context import create_default_context
from fltk.iir.py import compiler
from fltk.iir.py import reg as pyreg


def write_generated_modules(
    source_grammar: gsm.Grammar,
    parser_filename: str,
    cst_filename: str,
    cst_module_name: str,
) -> None:
    """Write the parser module, the CST module and the CST module's protocol sibling.

    ``source_grammar`` is run through the standard trivia augmentation first — ``ParserGenerator``
    refuses a grammar with no ``_trivia`` rule, and both steps are no-ops on a grammar that already
    carries one.
    """
    context = create_default_context()
    augmented = gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(source_grammar, context))

    cst_module = pyreg.Module(cst_module_name.split("."))
    cstgen = gsm2tree.CstGenerator(grammar=augmented, py_module=cst_module, context=context)
    pgen = gsm2parser.ParserGenerator(grammar=augmented, cstgen=cstgen, context=context)

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

    # Every module is rendered before any file is touched: a rendering failure must not truncate an
    # artifact this path exists to restore.
    parser_text = astor.to_source(parser_mod)
    cst_text = astor.to_source(cstgen.gen_py_module(naming.protocol_module_name(cst_module_name)))
    protocol_text = cstgen.gen_protocol_module_text()

    # The CST module imports NodeKind from its protocol module, so the pair must land together: a
    # fresh CST module beside a stale protocol module fails at import (or silently reuses the wrong
    # NodeKind members) as soon as the grammar's rule set changes. Each text goes to a sibling temp
    # file first and all three are moved into place at the end, so a write failure leaves every
    # target holding its previous content and the worst surviving interleaving is a fresh protocol
    # module beside a stale CST module — which still imports.
    targets = [
        (parser_filename, parser_text),
        (naming.protocol_module_path(cst_filename), protocol_text),
        (cst_filename, cst_text),
    ]
    staged: list[tuple[str, str]] = []
    try:
        for filename, text in targets:
            temp_filename = f"{filename}.tmp"
            with open(temp_filename, "w", newline="\n") as temp_file:
                temp_file.write(text)
            staged.append((temp_filename, filename))
        while staged:
            temp_filename, filename = staged.pop(0)
            os.replace(temp_filename, filename)
    finally:
        for temp_filename, _ in staged:
            pathlib.Path(temp_filename).unlink(missing_ok=True)
