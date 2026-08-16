"""The AST -> CST -> AST round trip is broken for a `fold` rule whose operands carry spans.

`to_cst()` synthesises each node's span against its own source text, one text per node, and
`Span.merge` refuses operands from different sources by construction — so re-converting a
reverse-constructed fold raises instead of returning the value it started from.  Pre-existing and
backend-independent (`to_cst` is Python-backend-only either way).

This pins the current failure so that fixing it is a visible event: closing
`TODO(astrt-fold-roundtrip-span-merge)` means inverting these tests into a round-trip identity.
"""

from __future__ import annotations

import pytest

from fltk import plumbing
from fltk.fegen.ast_config import Backend
from fltk.fegen.pyrt import astrt
from tests import fixture_ast_layer

_MERGE_MESSAGE = "the operands of a fold come from different sources, so their spans cannot merge"


@pytest.fixture(scope="module")
def layer() -> fixture_ast_layer.AstLayer:
    """The fixture grammar's Python AST layer.

    `sum_chain := term:num , ( , op:/[-+]/ , term:num)*` folds left over `num` operands, and `num`
    is a node type with a span of its own — which is what the merge needs and what the round trip
    cannot supply.
    """
    return fixture_ast_layer.build()


@pytest.mark.parametrize("text", ["1+2", "1-2+3-4"])
def test_fold_roundtrip_raises_on_span_merge(layer: fixture_ast_layer.AstLayer, text: str) -> None:
    """TODO(astrt-fold-roundtrip-span-merge): invert this to a round-trip identity when it closes."""
    value = layer.convert_text("sum_chain", text)
    rebuilt = value.to_cst()
    with pytest.raises(astrt.AstError, match=_MERGE_MESSAGE):
        layer.ast.sum_chain_from_cst(rebuilt)


def test_a_single_operand_fold_round_trips(layer: fixture_ast_layer.AstLayer) -> None:
    """One operand means no merge, and that case works — the defect starts at the first merge.

    A `sum_chain` of one term folds to the term itself, so the value is a `num` and `to_cst()`
    rebuilds a `num` node; `num_from_cst` is therefore the round trip's other half.
    """
    value = layer.convert_text("sum_chain", "1")
    rebuilt = value.to_cst()
    assert rebuilt.kind is layer.parser.cst_module.NodeKind.NUM
    assert layer.ast.num_from_cst(rebuilt) == value


def test_the_forward_direction_and_to_cst_both_succeed(layer: fixture_ast_layer.AstLayer) -> None:
    """Only re-conversion fails, which is why the defect is easy to miss: nothing raises earlier.

    `to_cst()` rebuilds the whole chain — the operands and operators are all there, and each
    operand converts back on its own. Only merging their spans into the parent's fails.
    """
    value = layer.convert_text("sum_chain", "1+2-3")
    rebuilt = value.to_cst()

    assert rebuilt.kind is layer.parser.cst_module.NodeKind.SUMCHAIN
    terms = list(rebuilt.children_term())
    assert len(terms) == 3
    assert len(list(rebuilt.children_op())) == 2
    assert [layer.ast.num_from_cst(term).text for term in terms] == ["1", "2", "3"]


def test_a_fold_over_erased_operands_still_round_trips() -> None:
    """The defect needs operand spans, so it is narrower than "every fold rule".

    A sidecar that erases the operands to plain scalars leaves nothing to merge, and that shape
    round-trips today — so a fix must not be validated on such a grammar alone.
    """
    from fltk.fegen import ast_test_grammars as fixtures  # noqa: PLC0415

    grammar = plumbing.parse_grammar(fixtures.FOLD_GRAMMAR)
    config = plumbing.parse_ast_config(fixtures.FOLD_SIDECAR, grammar, {Backend.PYTHON})
    parser = plumbing.generate_parser(grammar, capture_trivia=False)
    module = plumbing.generate_ast(
        parser.grammar,
        parser.cst_module_name,
        ast_config=config,
        protocol_module_name=parser.protocol_module_name,
    ).ast_module

    result = plumbing.parse_text(parser, "1 + 2 + 3", "expr")
    assert result.success, result.error_message
    value = module.expr_from_cst(result.cst)
    assert module.expr_from_cst(value.to_cst()) == value
