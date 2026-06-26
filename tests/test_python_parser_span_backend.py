"""Generated Python parser constructs pure-Python terminalsrc spans (design §2.1).

A generated Python parser must produce pure-Python ``terminalsrc.Span`` /
``terminalsrc.SourceText`` objects at runtime, regardless of whether ``fltk._native`` is
importable in the process.  Before §2.1 the construction sites resolved through the type
registry's ``span``-module entry, so with native built they silently produced
``fltk._native.Span`` — the core bug.  These tests would fail on that pre-§2.1 code (when
native is importable) and pass after the construction sites are retargeted to ``terminalsrc``.
"""

from __future__ import annotations

import pytest

from fltk.fegen import gsm
from fltk.fegen.pyrt import terminalsrc
from fltk.plumbing import generate_parser, generate_unparser, parse_text, render_doc, unparse_cst

try:
    from fltk._native import Span as NativeSpan
except Exception:  # pragma: no cover - pure-Python install without the native extension
    NativeSpan = None


def _make_word_grammar() -> gsm.Grammar:
    """doc := word:r'[a-z]+' — single labeled regex terminal (yields one span-typed child)."""
    rule = gsm.Rule(
        name="doc",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="word",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[a-z]+"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    return gsm.Grammar(rules=[rule], identifiers={"doc": rule})


def test_root_node_span_is_pure_python() -> None:
    """The root node's span is constructed as a pure-Python terminalsrc.Span."""
    pr = generate_parser(_make_word_grammar(), capture_trivia=False)
    result = parse_text(pr, "hello")
    assert result.success, result.error_message
    assert result.cst is not None
    assert type(result.cst.span) is terminalsrc.Span


def test_span_typed_child_is_pure_python() -> None:
    """A span-typed child (the labeled terminal) is a pure-Python terminalsrc.Span."""
    pr = generate_parser(_make_word_grammar(), capture_trivia=False)
    result = parse_text(pr, "hello")
    assert result.success, result.error_message
    assert result.cst is not None
    # children is a list of (label, value); the labeled terminal value is a Span.
    span_children = [value for (_label, value) in result.cst.children]
    assert span_children, "expected at least one child"
    for child in span_children:
        assert type(child) is terminalsrc.Span


def test_source_text_is_pure_python() -> None:
    """The parser's _source_text field is constructed as a pure-Python terminalsrc.SourceText."""
    pr = generate_parser(_make_word_grammar(), capture_trivia=False)
    parser = pr.parser_class(terminalsrc.TerminalSource("hello"))
    assert type(parser._source_text) is terminalsrc.SourceText


def test_not_native_span_when_native_present() -> None:
    """When fltk._native is importable, the produced span is NOT a native Span (the core bug).

    This is the determinism guarantee: backend selection follows which parser is imported,
    not whether the native extension happens to be loadable in the process.
    """
    if NativeSpan is None:
        # Pure-Python install: nothing to disambiguate; the type-identity tests above suffice.
        return
    pr = generate_parser(_make_word_grammar(), capture_trivia=False)
    result = parse_text(pr, "hello")
    assert result.success, result.error_message
    assert result.cst is not None
    assert type(result.cst.span) is not NativeSpan
    assert terminalsrc.Span is not NativeSpan


def test_native_present_unparse_round_trip() -> None:
    """Native-present unparse round-trip regression (design §4 / delta D6).

    This is the §2.1-exposed gap (edge case 7): before §2.6 the generated unparser's probe-bound
    span guards rejected ``terminalsrc.Span`` children whenever ``fltk._native`` was importable, so
    ``unparse_cst`` raised ``ValueError("Unparsing failed")``.  ``is_span`` recognizes
    ``terminalsrc.Span`` regardless of native presence, so the round-trip succeeds.

    The three properties — native importable (the precondition that triggers the original bug), the
    parser still produces a pure-Python ``terminalsrc.Span``, and unparse→render succeeds with the
    expected text — are asserted together so the regression is pinned in one native-present test
    (the design's "the case that raises ValueError on the §2.1-only tree").  Split across files, the
    unparse path carries no native-present precondition and passes trivially where the bug cannot
    manifest.
    """
    if NativeSpan is None:
        pytest.skip("fltk._native not built in this environment")
    grammar = _make_word_grammar()
    parser_result = generate_parser(grammar, capture_trivia=True)
    parse_result = parse_text(parser_result, "hello")
    assert parse_result.success, parse_result.error_message
    assert parse_result.cst is not None
    assert type(parse_result.cst.span) is terminalsrc.Span
    unparser_result = generate_unparser(grammar, parser_result.cst_module_name)
    doc = unparse_cst(unparser_result, parse_result.cst, parse_result.terminals)
    assert render_doc(doc) == "hello"
