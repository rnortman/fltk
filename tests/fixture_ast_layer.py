"""The Python AST layer over the `rust_parser_fixture` grammar, built once per configuration.

`rust_parser_fixture` is the richest committed grammar/sidecar pair — sums, products, folds,
coercions, transparent rules, keyed collections, inline splices — so several suites want an AST
module generated from it. They build it identically, and the build is four `plumbing` calls whose
arguments have to stay in step with `generate_ast`'s signature, so it lives here. Not a test module
itself.
"""

from __future__ import annotations

import pathlib
import typing

from fltk import plumbing
from fltk.fegen.ast_config import Backend

if typing.TYPE_CHECKING:
    import types

    from fltk.plumbing_types import ParserResult

_REPO_ROOT = pathlib.Path(__file__).parent.parent

FIXTURE_FLTKG = _REPO_ROOT / "fltk" / "fegen" / "test_data" / "rust_parser_fixture.fltkg"
FIXTURE_SIDECAR = _REPO_ROOT / "tests" / "rust_parser_fixture" / "rust_parser_fixture.fltkast"


class AstLayer(typing.NamedTuple):
    """A Python parser for the fixture grammar and the AST module generated from it."""

    parser: ParserResult
    ast: types.ModuleType

    def py_cst(self, rule: str, text: str) -> typing.Any:
        result = plumbing.parse_text(self.parser, text, rule)
        assert result.success, result.error_message
        return result.cst

    def convert(self, rule: str, node: typing.Any) -> typing.Any:
        return getattr(self.ast, f"{rule}_from_cst")(node)

    def convert_text(self, rule: str, text: str) -> typing.Any:
        """Parse ``text`` as ``rule`` with the Python backend and convert the result."""
        return self.convert(rule, self.py_cst(rule, text))


def build(*, capture_trivia: bool = False, config_prefix: str = "") -> AstLayer:
    """Generate the fixture grammar's parser and AST module.

    ``config_prefix`` is prepended to the sidecar text, so a caller can override a directive.
    """
    grammar = plumbing.parse_grammar_file(FIXTURE_FLTKG)
    config = plumbing.parse_ast_config(config_prefix + FIXTURE_SIDECAR.read_text(), grammar, {Backend.PYTHON})
    parser = plumbing.generate_parser(grammar, capture_trivia=capture_trivia)
    ast_result = plumbing.generate_ast(
        parser.grammar,
        parser.cst_module_name,
        ast_config=config,
        protocol_module_name=parser.protocol_module_name,
    )
    return AstLayer(parser=parser, ast=ast_result.ast_module)
