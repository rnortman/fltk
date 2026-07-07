"""Tests for the pure feature logic in ``fltk.lsp.features``.

Semantic-token encoding is checked against hand-computed relative-encoding expectations (including
multi-line splits and utf-16 vs utf-32 columns); folding and selection are driven over small
hand-built CST-shaped trees so spans, kinds, and nesting are fully controlled.
"""

from __future__ import annotations

from lsprotocol.types import FoldingRangeKind, SelectionRange

from fltk import plumbing
from fltk.fegen.pyrt.span_protocol import SpanKind
from fltk.lsp import features
from fltk.lsp.classify import Token
from fltk.lsp.conftest import HELLO_GRAMMAR
from fltk.lsp.engine import AnalysisEngine
from fltk.lsp.lsp_config import LSP_STANDARD_MODIFIERS, TOKEN_LEGEND, load_lsp_config
from fltk.lsp.positions import LineIndex, PositionEncoding

UTF16 = PositionEncoding.UTF16
UTF32 = PositionEncoding.UTF32


# --- Fake CST shapes ------------------------------------------------------------------------------
# The feature walkers touch only `.kind`, `.span`/`.start`/`.end`, and `.children`; these fakes
# reproduce exactly that surface (a span child is discriminated by `kind == SpanKind.SPAN`).


class _Span:
    """A terminal span child (leaf), as CST nodes expose them."""

    kind = SpanKind.SPAN

    def __init__(self, start: int, end: int) -> None:
        self.start = start
        self.end = end


class _Bounds:
    def __init__(self, start: int, end: int) -> None:
        self.start = start
        self.end = end


class _Kind:
    def __init__(self, name: str) -> None:
        self.name = name


class _Node:
    def __init__(self, name: str, start: int, end: int, children: list | None = None) -> None:
        self.kind = _Kind(name)
        self.span = _Bounds(start, end)
        self.children = children if children is not None else []


# --- Legend -------------------------------------------------------------------------------------


def test_semantic_token_types_set_equal_token_legend() -> None:
    assert set(features.SEMANTIC_TOKEN_TYPES) == TOKEN_LEGEND
    assert len(features.SEMANTIC_TOKEN_TYPES) == len(TOKEN_LEGEND)  # no duplicates


def test_semantic_token_modifiers_set_equal_standard_modifiers() -> None:
    assert set(features.SEMANTIC_TOKEN_MODIFIERS) == LSP_STANDARD_MODIFIERS
    assert len(features.SEMANTIC_TOKEN_MODIFIERS) == len(LSP_STANDARD_MODIFIERS)


# --- Semantic token encoding --------------------------------------------------------------------


def _type(name: str) -> int:
    return features.SEMANTIC_TOKEN_TYPES.index(name)


def test_encode_two_tokens_on_separate_lines() -> None:
    text = "abc\ndef"
    idx = LineIndex(text)
    tokens = [Token(0, 3, "keyword", ()), Token(4, 7, "variable", ())]
    data = features.encode_semantic_tokens(tokens, idx, UTF32)
    assert data == [0, 0, 3, _type("keyword"), 0, 1, 0, 3, _type("variable"), 0]


def test_encode_relative_deltas_within_a_line() -> None:
    text = "ab cd"
    idx = LineIndex(text)
    tokens = [Token(0, 2, "keyword", ()), Token(3, 5, "variable", ())]
    data = features.encode_semantic_tokens(tokens, idx, UTF32)
    # second token: same line -> deltaLine 0, deltaStart = 3 - 0 = 3
    assert data == [0, 0, 2, _type("keyword"), 0, 0, 3, 2, _type("variable"), 0]


def test_encode_splits_multiline_token_at_line_boundaries() -> None:
    text = "ab\ncd"
    idx = LineIndex(text)
    data = features.encode_semantic_tokens([Token(0, 5, "comment", ())], idx, UTF32)
    # line 0: "ab" (len 2), line 1: "cd" (len 2), the newline is skipped as an empty segment
    assert data == [0, 0, 2, _type("comment"), 0, 1, 0, 2, _type("comment"), 0]


def test_encode_token_ending_exactly_at_newline_is_single_segment() -> None:
    text = "ab\ncd"
    idx = LineIndex(text)
    data = features.encode_semantic_tokens([Token(0, 2, "keyword", ())], idx, UTF32)
    assert data == [0, 0, 2, _type("keyword"), 0]


def test_encode_modifier_bits_and_unknown_modifier_dropped() -> None:
    text = "x"
    idx = LineIndex(text)
    data = features.encode_semantic_tokens([Token(0, 1, "keyword", ("declaration", "bogus"))], idx, UTF32)
    declaration_bit = 1 << features.SEMANTIC_TOKEN_MODIFIERS.index("declaration")
    assert data == [0, 0, 1, _type("keyword"), declaration_bit]


def test_encode_unknown_token_type_is_skipped() -> None:
    text = "xy"
    idx = LineIndex(text)
    data = features.encode_semantic_tokens([Token(0, 2, "not-a-legend-member", ())], idx, UTF32)
    assert data == []


def test_encode_astral_utf16_vs_utf32_columns_and_lengths() -> None:
    # "𐐀" is U+10400: one codepoint, two utf-16 code units.
    text = "\U00010400x"
    idx = LineIndex(text)
    tokens = [Token(0, 1, "string", ()), Token(1, 2, "variable", ())]

    utf32 = features.encode_semantic_tokens(tokens, idx, UTF32)
    assert utf32 == [0, 0, 1, _type("string"), 0, 0, 1, 1, _type("variable"), 0]

    utf16 = features.encode_semantic_tokens(tokens, idx, UTF16)
    # astral char is length 2 in utf-16; the second token then starts at column 2.
    assert utf16 == [0, 0, 2, _type("string"), 0, 0, 2, 1, _type("variable"), 0]


# --- Folding ------------------------------------------------------------------------------------

_FOLD_TEXT = "line0\nline1\nline2\nline3\n"  # four lines, starts at 0, 6, 12, 18


def test_folding_multiline_nodes_fold_and_single_line_nodes_do_not() -> None:
    idx = LineIndex(_FOLD_TEXT)
    inner = _Node("INNER", 6, 11, [(None, _Span(6, 11))])  # line 1 only -> no fold
    block = _Node("COMMENTBLOCK", 12, 24, [(None, _Span(12, 24))])  # lines 2-3 -> fold, trivia
    root = _Node("TOP", 0, 24, [(None, inner), (None, block)])  # lines 0-3 -> fold
    folds = features.folding_ranges(root, frozenset({"COMMENTBLOCK"}), idx)
    got = [(f.start_line, f.end_line, f.kind) for f in folds]
    assert got == [(0, 3, None), (2, 3, FoldingRangeKind.Comment)]


def test_folding_deduplicates_shared_extents_keeping_outermost() -> None:
    idx = LineIndex(_FOLD_TEXT)
    child = _Node("B", 0, 18, [(None, _Span(0, 18))])
    parent = _Node("A", 0, 18, [(None, child)])  # same line extents as child
    folds = features.folding_ranges(parent, frozenset(), idx)
    # one fold only; the outermost (A, non-trivia -> no kind) is kept.
    assert [(f.start_line, f.end_line, f.kind) for f in folds] == [(0, 2, None)]


def test_folding_over_real_engine_tree() -> None:
    # A multi-greeting document spanning several lines folds at the top node.
    grammar = plumbing.parse_grammar(HELLO_GRAMMAR)
    engine = AnalysisEngine(grammar, load_lsp_config("", grammar), start_rule="top")
    text = "hello a !\nhello b !\n"
    analysis = engine.analyze(text)
    assert analysis.tree is not None
    idx = LineIndex(text)
    folds = features.folding_ranges(analysis.tree, engine.trivia_kind_names, idx)
    # The `top` node covers both lines, so at least one multi-line fold exists.
    assert any(f.end_line > f.start_line for f in folds)


# --- Selection ----------------------------------------------------------------------------------


def _greeting_tree() -> _Node:
    # "hello world !": "hello"[0,5), "world"[6,11), "!"[12,13)
    kw = _Span(0, 5)
    name = _Span(6, 11)
    punct = _Span(12, 13)
    greeting = _Node("GREETING", 0, 13, [(None, kw), (None, name), (None, punct)])
    return _Node("TOP", 0, 13, [(None, greeting)])


def test_selection_innermost_span_is_head_and_widens_strictly() -> None:
    text = "hello world !"
    idx = LineIndex(text)
    root = _greeting_tree()
    ranges = features.selection_ranges(root, [7], idx, UTF32)  # offset inside "world"
    assert len(ranges) == 1
    head = ranges[0]
    # head is the terminal span "world" [6,11)
    assert (head.range.start.character, head.range.end.character) == (6, 11)
    # parent widens to the whole document [0,13); TOP and GREETING share a span so are collapsed.
    parent = head.parent
    assert parent is not None
    assert (parent.range.start.character, parent.range.end.character) == (0, 13)
    assert parent.parent is None
    # strictly widening: head is narrower than its parent.
    assert head.range != parent.range


def test_selection_offset_at_end_of_document_yields_zero_width_range() -> None:
    text = "hello world !"
    idx = LineIndex(text)
    root = _greeting_tree()
    ranges = features.selection_ranges(root, [len(text)], idx, UTF32)
    assert len(ranges) == 1
    head = ranges[0]
    assert head.parent is None
    assert head.range.start == head.range.end
    assert (head.range.start.line, head.range.start.character) == (0, 13)


def _nested_tree() -> _Node:
    # Three genuinely distinct enclosing spans plus a terminal span, so the selection chain has a
    # real multi-level recursive shape (no collapsing): DOCUMENT[0,20) > ITEM[0,12) > GREETING[0,11)
    # > name span[6,11).
    name = _Span(6, 11)
    greeting = _Node("GREETING", 0, 11, [(None, _Span(0, 5)), (None, name)])
    item = _Node("ITEM", 0, 12, [(None, greeting)])
    return _Node("DOCUMENT", 0, 20, [(None, item)])


def test_selection_three_distinct_levels_widen_in_order() -> None:
    text = "x" * 20
    idx = LineIndex(text)
    root = _nested_tree()
    ranges = features.selection_ranges(root, [7], idx, UTF32)  # inside name span [6,11)
    assert len(ranges) == 1
    spans: list[tuple[int, int]] = []
    node: SelectionRange | None = ranges[0]
    while node is not None:
        spans.append((node.range.start.character, node.range.end.character))
        node = node.parent
    # innermost (the terminal span) to document-root, each strictly widening.
    assert spans == [(6, 11), (0, 11), (0, 12), (0, 20)]


def test_selection_multiple_offsets_return_one_chain_each() -> None:
    text = "hello world !"
    idx = LineIndex(text)
    root = _greeting_tree()
    ranges = features.selection_ranges(root, [2, 7], idx, UTF32)
    assert len(ranges) == 2
    # offset 2 -> "hello" [0,5)
    assert (ranges[0].range.start.character, ranges[0].range.end.character) == (0, 5)
    # offset 7 -> "world" [6,11)
    assert (ranges[1].range.start.character, ranges[1].range.end.character) == (6, 11)
