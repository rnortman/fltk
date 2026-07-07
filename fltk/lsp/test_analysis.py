"""Tests for the analysis-grammar transform (`prepare_analysis_grammar`)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from fltk.fegen import gsm
from fltk.fegen.pyrt.span_protocol import SpanKind
from fltk.lsp.analysis import prepare_analysis_grammar
from fltk.plumbing import generate_parser, parse_grammar, parse_text

# `top` exercises all three suppression sources: an unlabeled literal (`":"`), an
# unlabeled regex (`/[0-9]+/`), and an explicitly-suppressed rule invocation (`%tail`).
_GRAMMAR = """
top := a:word . ":" . /[0-9]+/ . %tail ;
word := name:/[a-z]+/ ;
tail := "!" . mark:word ;
"""

_INPUT = "abc:123!x"


def _iter_node_spans(node: Any) -> Iterator[tuple[Any, int, int]]:
    """Yield (kind, start, end) for every CST node (not span children), depth-first."""
    yield (node.kind, node.span.start, node.span.end)
    for _label, child in node.children:
        if child.kind == SpanKind.SPAN:
            continue
        yield from _iter_node_spans(child)


def _iter_span_texts(node: Any) -> Iterator[str]:
    """Yield the source text of every span child anywhere in the tree."""
    for _label, child in node.children:
        if child.kind == SpanKind.SPAN:
            text = child.text()
            if text is not None:
                yield text
        else:
            yield from _iter_span_texts(child)


def test_suppressed_terminals_and_subtree_surface_as_children():
    grammar = parse_grammar(_GRAMMAR)

    std_result = parse_text(generate_parser(grammar), _INPUT, "top")
    ana_result = parse_text(generate_parser(prepare_analysis_grammar(grammar)), _INPUT, "top")

    assert std_result.success
    assert ana_result.success

    std_span_texts = set(_iter_span_texts(std_result.cst))
    ana_span_texts = set(_iter_span_texts(ana_result.cst))

    # Suppressed literal, suppressed regex, and the literal inside the suppressed subtree
    # are all absent from the standard tree but present in the analysis tree.
    for surfaced in (":", "123", "!"):
        assert surfaced not in std_span_texts
        assert surfaced in ana_span_texts


def test_node_spans_unchanged():
    grammar = parse_grammar(_GRAMMAR)

    std_result = parse_text(generate_parser(grammar), _INPUT, "top")
    ana_result = parse_text(generate_parser(prepare_analysis_grammar(grammar)), _INPUT, "top")

    assert std_result.cst is not None
    assert ana_result.cst is not None

    # Full consumption implies identical top-level spans.
    assert std_result.cst.span.start == ana_result.cst.span.start == 0
    assert std_result.cst.span.end == ana_result.cst.span.end == len(_INPUT)

    # Every node the standard parser produced appears with an identical span in the
    # analysis tree (which additionally contains the surfaced suppressed subtree nodes).
    std_nodes = set(_iter_node_spans(std_result.cst))
    ana_nodes = set(_iter_node_spans(ana_result.cst))
    assert std_nodes <= ana_nodes


def test_transform_is_idempotent():
    grammar = parse_grammar(_GRAMMAR)
    once = prepare_analysis_grammar(grammar)
    twice = prepare_analysis_grammar(once)

    # The transform changes the grammar (suppress -> include) but is a fixed point.
    assert once != grammar
    assert twice == once


def test_inline_grammar_rejected_with_clean_error():
    grammar = parse_grammar(
        """
        top := a:word . !tail ;
        word := name:/[a-z]+/ ;
        tail := mark:word ;
        """
    )

    with pytest.raises(ValueError, match="inline"):
        prepare_analysis_grammar(grammar)


def test_inline_detection_recurses_into_subexpressions():
    # The `!` sits inside a parenthesized sub-expression, so the up-front scan must recurse.
    grammar = parse_grammar(
        """
        top := a:word . ( !tail )? ;
        word := name:/[a-z]+/ ;
        tail := mark:word ;
        """
    )

    with pytest.raises(ValueError, match="inline"):
        prepare_analysis_grammar(grammar)


def test_transform_recurses_into_subexpressions():
    # A suppressed literal nested in a sub-expression must be promoted too.
    grammar = parse_grammar(
        """
        top := a:word . ( ":" . b:word )? ;
        word := name:/[a-z]+/ ;
        """
    )
    prepared = prepare_analysis_grammar(grammar)

    ana_result = parse_text(generate_parser(prepared), "abc:def", "top")
    assert ana_result.success
    assert ":" in set(_iter_span_texts(ana_result.cst))


def test_original_grammar_disposition_unchanged():
    # The grammar module frozen dataclasses must not be mutated in place.
    grammar = parse_grammar(_GRAMMAR)
    dispositions_before = _collect_dispositions(grammar)
    prepare_analysis_grammar(grammar)
    assert _collect_dispositions(grammar) == dispositions_before
    assert gsm.Disposition.SUPPRESS in dispositions_before


def _collect_dispositions(grammar: gsm.Grammar) -> list[gsm.Disposition]:
    collected: list[gsm.Disposition] = []
    for rule in grammar.rules:
        for alt in rule.alternatives:
            gsm.for_each_item(alt, lambda _idx, item: collected.append(item.disposition))
    return collected
