"""The AST -> CST -> AST round trip of a `fold` rule, and the span each link carries.

`to_cst()` synthesises every leaf with its own single-token source and every composite with
`UnknownSpan`, so a re-converted chain has operands that share no source: each of its links is
`UnknownSpan`.  A parsed chain's operands lie in order in one document, so each of its links is
the cover of the operands below it.  Value equality ignores spans, so every round trip here also
asserts the link spans, on the re-converted chain and on the parsed one it came from.
"""

from __future__ import annotations

import typing

import pytest

from fltk import plumbing
from fltk.fegen.ast_config import Backend
from fltk.fegen.pyrt import terminalsrc
from tests import fixture_ast_layer
from tests.rust_gate_cases import AST_GUIDE_GRAMMAR, AST_GUIDE_SIDECAR

if typing.TYPE_CHECKING:
    import types

    from fltk.plumbing_types import ParserResult


@pytest.fixture(scope="module")
def layer() -> fixture_ast_layer.AstLayer:
    """The fixture grammar's Python AST layer.

    `sum_chain := term:num , ( , op:/[-+]/ , term:num)*` folds left over `num` operands, and `num`
    is the sourced, terminal-shaped operand the link-span rule is exercised on — parsed, its spans
    share the document; synthesised, each carries its own text.
    """
    return fixture_ast_layer.build()


def _left_links(value: typing.Any, binary: type) -> list[typing.Any]:
    """The links of a left-nested chain, outermost first."""
    links = []
    while isinstance(value, binary):
        links.append(value)
        value = value.lhs
    return links


def _assert_unknown(span: typing.Any) -> None:
    assert span == terminalsrc.UnknownSpan
    assert not span.has_source()


@pytest.mark.parametrize(
    ("text", "covers"),
    [("1+2", ["1+2"]), ("1+1", ["1+1"]), ("1-2+3-4", ["1-2+3-4", "1-2+3", "1-2"])],
)
def test_a_synthesised_chain_round_trips_with_unknown_link_spans(
    layer: fixture_ast_layer.AstLayer, text: str, covers: list[str]
) -> None:
    value = layer.convert_text("sum_chain", text)
    again = layer.ast.sum_chain_from_cst(value.to_cst())
    assert again == value

    parsed = _left_links(value, layer.ast.SumChainBinary)
    assert [link.span.text() for link in parsed] == covers

    synthesised = _left_links(again, layer.ast.SumChainBinary)
    assert len(synthesised) == len(covers)
    for link in synthesised:
        _assert_unknown(link.span)


def test_a_single_operand_fold_round_trips(layer: fixture_ast_layer.AstLayer) -> None:
    """One operand builds no link, so no link span is computed; the value is the `num` itself.

    `to_cst()` therefore rebuilds a `num` node, and `num_from_cst` is the round trip's other half.
    """
    value = layer.convert_text("sum_chain", "1")
    rebuilt = value.to_cst()
    assert rebuilt.kind is layer.parser.cst_module.NodeKind.NUM
    assert layer.ast.num_from_cst(rebuilt) == value


def test_to_cst_rebuilds_the_whole_run(layer: fixture_ast_layer.AstLayer) -> None:
    """The synthesised node is the flat run the grammar spells: every operand and operator, in order."""
    value = layer.convert_text("sum_chain", "1+2-3")
    rebuilt = value.to_cst()

    assert rebuilt.kind is layer.parser.cst_module.NodeKind.SUMCHAIN
    terms = list(rebuilt.children_term())
    assert len(terms) == 3
    assert len(list(rebuilt.children_op())) == 2
    assert [layer.ast.num_from_cst(term).text for term in terms] == ["1", "2", "3"]


def _generate(grammar_text: str, sidecar_text: str) -> tuple[ParserResult, types.ModuleType]:
    grammar = plumbing.parse_grammar(grammar_text)
    config = plumbing.parse_ast_config(sidecar_text, grammar, {Backend.PYTHON})
    parser = plumbing.generate_parser(grammar, capture_trivia=False)
    module = plumbing.generate_ast(
        parser.grammar,
        parser.cst_module_name,
        ast_config=config,
        protocol_module_name=parser.protocol_module_name,
    ).ast_module
    return parser, module


def test_a_fold_over_erased_operands_still_round_trips() -> None:
    """Every operand of this fold is an unknown-span composite, so this is the all-unknown edge
    of the link-span rule, not evidence about sourced operands."""
    from fltk.fegen import ast_test_grammars as fixtures  # noqa: PLC0415

    parser, module = _generate(fixtures.FOLD_GRAMMAR, fixtures.FOLD_SIDECAR)
    result = plumbing.parse_text(parser, "1 + 2 + 3", "expr")
    assert result.success, result.error_message
    value = module.expr_from_cst(result.cst)
    again = module.expr_from_cst(value.to_cst())
    assert again == value

    parsed = _left_links(value, module.ExprBinary)
    # A parsed `term` operand's span ends after the whitespace its own trailing `,` consumed.
    assert [link.span.text() for link in parsed] == ["1 + 2 + 3", "1 + 2 "]

    synthesised = _left_links(again, module.ExprBinary)
    assert len(synthesised) == 2
    for link in synthesised:
        _assert_unknown(link.span)


@pytest.fixture(scope="module")
def quick_start() -> tuple[ParserResult, types.ModuleType]:
    """The AST guide's quick start: a left fold over a `transparent;` integer operand."""
    return _generate(AST_GUIDE_GRAMMAR, AST_GUIDE_SIDECAR)


@pytest.mark.parametrize(("text", "covers"), [("1 + 2 - 3", ["1 + 2 - 3", "1 + 2"]), ("1 + 1", ["1 + 1"])])
def test_the_quick_start_chain_round_trips_with_unknown_link_spans(
    quick_start: tuple[ParserResult, types.ModuleType], text: str, covers: list[str]
) -> None:
    parser, module = quick_start
    result = plumbing.parse_text(parser, text, "expr")
    assert result.success, result.error_message
    value = module.expr_from_cst(result.cst)
    again = module.expr_from_cst(value.to_cst())
    assert again == value

    parsed = _left_links(value, module.ExprBinary)
    assert [link.span.text() for link in parsed] == covers

    synthesised = _left_links(again, module.ExprBinary)
    assert len(synthesised) == len(covers)
    for link in synthesised:
        _assert_unknown(link.span)
