"""The generated fegen Python AST module used by the pyright-gated suites.

Nothing commits a Python AST artifact, so every suite that type-checks one generates it first.
`tests/test_protocol_static_contracts.py` checks the artifact itself;
`tests/test_ast_switchable_consumer.py` writes it beside consumer fixtures that import it.  The
generation arguments live here so the two cannot drift into checking differently configured
modules.  Not a test module itself.
"""

from __future__ import annotations

import pathlib

from fltk.plumbing import generate_ast_source, parse_grammar_file

_REPO_ROOT = pathlib.Path(__file__).parent.parent

FEGEN_FLTKG = _REPO_ROOT / "fltk" / "fegen" / "fegen.fltkg"

AST_MODULE_NAME = "generated_fegen_ast"
CST_MODULE_NAME = "fltk.fegen.fltk_cst"
PARSER_MODULE_NAME = "fltk.fegen.fltk_parser"
PROTOCOL_MODULE_NAME = "fltk.fegen.fltk_cst_protocol"


def generate_fegen_ast_source() -> str:
    """Render the fegen AST module against the committed fegen CST and protocol modules."""
    return generate_ast_source(
        parse_grammar_file(FEGEN_FLTKG),
        CST_MODULE_NAME,
        PARSER_MODULE_NAME,
        protocol_module_name=PROTOCOL_MODULE_NAME,
    )


def write_fegen_ast_module(target: pathlib.Path) -> pathlib.Path:
    """Write the rendered module into ``target`` under the name consumers import it by."""
    path = target / f"{AST_MODULE_NAME}.py"
    path.write_text(generate_fegen_ast_source())
    return path
