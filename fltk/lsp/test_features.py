"""Tests for the pure feature logic in ``fltk.lsp.features``.

Semantic-token encoding is checked against hand-computed relative-encoding expectations (including
multi-line splits and utf-16 vs utf-32 columns); folding and selection are driven over small
hand-built CST-shaped trees so spans, kinds, and nesting are fully controlled.
"""

from __future__ import annotations

import itertools

from lsprotocol.types import (
    DocumentHighlightKind,
    FoldingRangeKind,
    SelectionRange,
    SymbolKind,
    TextDocumentEdit,
    TextEdit,
)

from fltk import plumbing
from fltk.fegen.pyrt.span_protocol import SpanKind
from fltk.lsp import features, symbols
from fltk.lsp.classify import Token
from fltk.lsp.conftest import HELLO_GRAMMAR
from fltk.lsp.engine import AnalysisEngine
from fltk.lsp.lsp_config import LSP_STANDARD_MODIFIERS, SOURCE_RANK_REF, TOKEN_LEGEND, Tier, load_lsp_config
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


# --- Segment / delta split ----------------------------------------------------------------------
# `encode_semantic_tokens` is now `delta_encode_segments(absolute_segments(...))`; these pin the two
# stages, and that the composition reproduces the same wire bytes the whole-token path produced.


def _seg(line: int, char: int, length: int, type_name: str, modifier_bits: int = 0) -> features.TokenSegment:
    return features.TokenSegment(
        line=line, char=char, length=length, type_index=_type(type_name), modifier_bits=modifier_bits
    )


def test_absolute_segments_produce_sorted_positions_and_split_multiline() -> None:
    text = "ab\ncd ef"
    idx = LineIndex(text)
    tokens = [Token(0, 5, "comment", ()), Token(6, 8, "variable", ())]
    segments = features.absolute_segments(tokens, idx, UTF32)
    assert segments == [
        _seg(0, 0, 2, "comment"),  # "ab"
        _seg(1, 0, 2, "comment"),  # "cd"
        _seg(1, 3, 2, "variable"),  # "ef"
    ]
    # Field-order sorting is the natural order, so a sorted token stream stays sorted here.
    assert segments == sorted(segments)


def test_absolute_segments_drops_unknown_type_and_modifier() -> None:
    text = "xy"
    idx = LineIndex(text)
    declaration_bit = 1 << features.SEMANTIC_TOKEN_MODIFIERS.index("declaration")
    tokens = [
        Token(0, 1, "not-a-legend-member", ()),  # dropped whole
        Token(1, 2, "keyword", ("declaration", "bogus")),  # unknown modifier dropped
    ]
    segments = features.absolute_segments(tokens, idx, UTF32)
    assert segments == [_seg(0, 1, 1, "keyword", declaration_bit)]


def test_delta_encode_empty_is_empty() -> None:
    assert features.delta_encode_segments([]) == []


def test_delta_after_absolute_reproduces_encode_bytes() -> None:
    # Every shape the whole-token encoder covers: multi-line split, astral utf-16 columns, and the
    # unknown-type/unknown-modifier drop paths -- the composition must be byte-identical.
    idx16 = LineIndex("\U00010400x")
    astral_tokens = [Token(0, 1, "string", ()), Token(1, 2, "variable", ())]
    idx_ml = LineIndex("ab\ncd")
    ml_tokens = [Token(0, 5, "comment", ())]
    idx_drop = LineIndex("xy")
    drop_tokens = [Token(0, 1, "not-a-legend-member", ()), Token(1, 2, "keyword", ("declaration", "bogus"))]
    for tokens, idx, enc in [
        (astral_tokens, idx16, UTF16),
        (astral_tokens, idx16, UTF32),
        (ml_tokens, idx_ml, UTF32),
        (drop_tokens, idx_drop, UTF32),
    ]:
        composed = features.delta_encode_segments(features.absolute_segments(tokens, idx, enc))
        assert composed == features.encode_semantic_tokens(tokens, idx, enc)


# --- Stale-segment merge ------------------------------------------------------------------------


def test_merge_fresh_only_when_stale_empty() -> None:
    fresh = [_seg(0, 0, 3, "keyword"), _seg(1, 0, 2, "variable")]
    assert features.merge_stale_segments(fresh, [], (5, 0)) == fresh


def test_merge_stale_only_boundary_origin_keeps_all() -> None:
    # Zero-length prefix: empty fresh, boundary (0,0) -> every stale segment survives.
    stale = [_seg(0, 0, 3, "keyword"), _seg(2, 4, 2, "variable")]
    assert features.merge_stale_segments([], stale, (0, 0)) == stale


def test_merge_clips_stale_before_boundary_keeps_at_boundary() -> None:
    fresh = [_seg(0, 0, 4, "keyword")]  # line 0
    stale = [
        _seg(1, 0, 3, "variable"),  # before boundary line 2 -> dropped
        _seg(2, 0, 3, "type"),  # exactly at boundary (2,0) -> kept
        _seg(3, 2, 2, "number"),  # past boundary -> kept
    ]
    merged = features.merge_stale_segments(fresh, stale, (2, 0))
    assert merged == [_seg(0, 0, 4, "keyword"), _seg(2, 0, 3, "type"), _seg(3, 2, 2, "number")]


def test_merge_floor_from_last_fresh_beats_earlier_boundary() -> None:
    # Boundary is (1,0), but the last fresh segment ends at (1,5); a stale segment starting at (1,2)
    # would overlap the fresh tail, so the floor from the last fresh segment drops it.
    fresh = [_seg(1, 0, 5, "keyword")]  # ends at (1,5)
    stale = [_seg(1, 2, 2, "variable"), _seg(1, 5, 3, "type")]
    merged = features.merge_stale_segments(fresh, stale, (1, 0))
    assert merged == [_seg(1, 0, 5, "keyword"), _seg(1, 5, 3, "type")]


def test_merge_result_sorted_and_non_overlapping() -> None:
    # An edit shrank the document so stale coordinates sit before the boundary; the merge stays
    # sorted and non-overlapping regardless.
    fresh = [_seg(0, 0, 2, "keyword"), _seg(0, 3, 2, "variable")]  # ends at (0,5)
    stale = [_seg(0, 1, 1, "type"), _seg(0, 6, 2, "number"), _seg(1, 0, 4, "string")]
    merged = features.merge_stale_segments(fresh, stale, (0, 5))
    assert merged == sorted(merged)
    for a, b in itertools.pairwise(merged):
        # non-overlapping: each segment ends at or before the next one's start
        assert (a.line, a.char + a.length) <= (b.line, b.char)


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


# --- Symbol navigation, outline, and rename -------------------------------------------------------

URI = "file:///doc"
IDX = LineIndex("x" * 60)  # single line, so utf-32 character == codepoint offset


def _sym(name: str, kind: tuple[str, ...], name_span: tuple[int, int], range_span: tuple[int, int]) -> symbols.Symbol:
    return symbols.Symbol(
        name=name,
        kind=kind,
        name_start=name_span[0],
        name_end=name_span[1],
        range_start=range_span[0],
        range_end=range_span[1],
    )


def _table(symbol_list: list[symbols.Symbol], references: tuple[symbols.Reference, ...] = ()) -> symbols.SymbolTable:
    root = symbols.Scope(start=0, end=60, parent=None, children=[], symbols=list(symbol_list))
    return symbols.SymbolTable(root=root, symbols=tuple(symbol_list), references=references)


def _ref(name: str, span: tuple[int, int], symbol: symbols.Symbol | None) -> symbols.Reference:
    return symbols.Reference(
        name=name,
        start=span[0],
        end=span[1],
        depth=1,
        kinds="*",
        tier=Tier(SOURCE_RANK_REF, 1, 1, 0),
        symbol=symbol,
    )


def test_symbol_kinds_table_and_object_fallback() -> None:
    assert features._symbol_kind(("type", "cog")) is SymbolKind.Class
    assert features._symbol_kind(("function",)) is SymbolKind.Function
    assert features._symbol_kind(("namespace",)) is SymbolKind.Namespace
    # An open-vocabulary first segment renders as Object.
    assert features._symbol_kind(("widget", "thing")) is SymbolKind.Object
    assert features._symbol_kind(()) is SymbolKind.Object


def test_document_symbols_nest_by_declaration_range_containment() -> None:
    # Container name child trails its members: its name_start (25) is later than the members', so a
    # name-start-ordered stack would mis-nest; range-sort keeps the members inside.
    outer = _sym("Outer", ("type",), (25, 30), (0, 30))
    a = _sym("a", ("variable",), (2, 7), (2, 10))
    b = _sym("b", ("variable",), (12, 17), (12, 20))
    roots = features.document_symbols(_table([a, b, outer]), IDX, UTF32)
    assert [r.name for r in roots] == ["Outer"]
    assert roots[0].children is not None
    assert [c.name for c in roots[0].children] == ["a", "b"]


def test_document_symbols_equal_ranges_are_siblings() -> None:
    s1 = _sym("s1", ("type",), (0, 3), (0, 10))
    s2 = _sym("s2", ("type",), (4, 7), (0, 10))
    roots = features.document_symbols(_table([s1, s2]), IDX, UTF32)
    assert [r.name for r in roots] == ["s1", "s2"]
    assert roots[0].children == []


def test_document_symbols_fields() -> None:
    sym = _sym("x", ("type", "cog"), (4, 5), (0, 7))
    (node,) = features.document_symbols(_table([sym]), IDX, UTF32)
    assert node.name == "x"
    assert node.detail == "type.cog"
    assert node.kind is SymbolKind.Class
    assert (node.range.start.character, node.range.end.character) == (0, 7)
    assert (node.selection_range.start.character, node.selection_range.end.character) == (4, 5)


def test_document_symbols_flat_shape() -> None:
    a = _sym("a", ("variable",), (4, 5), (0, 7))
    b = _sym("b", ("type",), (12, 13), (8, 15))
    infos = features.document_symbols_flat(_table([a, b]), URI, IDX, UTF32)
    assert [i.name for i in infos] == ["a", "b"]
    assert infos[0].kind is SymbolKind.Variable
    assert infos[0].location.uri == URI
    assert (infos[0].location.range.start.character, infos[0].location.range.end.character) == (0, 7)


def _nav_table() -> tuple[symbols.SymbolTable, symbols.Symbol]:
    sym = _sym("x", ("variable",), (4, 5), (0, 7))
    refs = (_ref("x", (12, 13), sym), _ref("x", (20, 21), sym), _ref("y", (30, 31), None))
    return _table([sym], refs), sym


def test_definition_on_reference_returns_the_declaration_name_span() -> None:
    table, sym = _nav_table()
    loc = features.definition_location(table, 12, URI, IDX, UTF32)  # cursor on the first ref
    assert loc is not None
    assert (loc.range.start.character, loc.range.end.character) == (sym.name_start, sym.name_end)


def test_definition_on_the_definition_returns_itself() -> None:
    table, sym = _nav_table()
    loc = features.definition_location(table, 4, URI, IDX, UTF32)  # cursor on the def name
    assert loc is not None
    assert (loc.range.start.character, loc.range.end.character) == (sym.name_start, sym.name_end)


def test_definition_on_nothing_and_on_unresolved_ref_is_none() -> None:
    table, _ = _nav_table()
    assert features.definition_location(table, 50, URI, IDX, UTF32) is None  # empty region
    assert features.definition_location(table, 30, URI, IDX, UTF32) is None  # unresolved ref `y`


def test_references_with_and_without_declaration() -> None:
    table, _ = _nav_table()
    with_decl = features.reference_locations(table, 12, URI, IDX, UTF32, include_declaration=True)
    assert with_decl is not None
    starts = sorted(loc.range.start.character for loc in with_decl)
    assert starts == [4, 12, 20]  # the def name plus both references
    without = features.reference_locations(table, 12, URI, IDX, UTF32, include_declaration=False)
    assert without is not None
    assert sorted(loc.range.start.character for loc in without) == [12, 20]


def test_document_highlights_write_on_declaration_read_on_references() -> None:
    table, _ = _nav_table()
    highlights = features.document_highlights(table, 4, IDX, UTF32)
    assert highlights is not None
    by_start = {h.range.start.character: h.kind for h in highlights}
    assert by_start[4] is DocumentHighlightKind.Write
    assert by_start[12] is DocumentHighlightKind.Read
    assert by_start[20] is DocumentHighlightKind.Read


def test_prepare_rename_range_on_target_and_none_otherwise() -> None:
    table, _ = _nav_table()
    # On the def name: the name span.
    on_def = features.prepare_rename(table, 4, IDX, UTF32)
    assert on_def is not None
    assert (on_def.start.character, on_def.end.character) == (4, 5)
    # On a resolved reference: the reference span.
    on_ref = features.prepare_rename(table, 12, IDX, UTF32)
    assert on_ref is not None
    assert (on_ref.start.character, on_ref.end.character) == (12, 13)
    # On an unresolved reference and on empty space: None.
    assert features.prepare_rename(table, 30, IDX, UTF32) is None
    assert features.prepare_rename(table, 50, IDX, UTF32) is None


def test_rename_occurrences_returns_symbol_and_deduped_spans() -> None:
    table, sym = _nav_table()
    result = features.rename_occurrences(table, 12)
    assert result is not None
    got_symbol, occ = result
    assert got_symbol is sym
    assert sorted(occ) == [(4, 5), (12, 13), (20, 21)]
    assert features.rename_occurrences(table, 30) is None  # unresolved ref


def test_rename_edits_versioned_document_changes() -> None:
    _, _sym = _nav_table()
    occ = [(4, 5), (12, 13), (20, 21)]
    edit = features.rename_edits(URI, 7, occ, "z", line_index=IDX, enc=UTF32, document_changes=True)
    assert edit.changes is None
    assert edit.document_changes is not None
    (text_document_edit,) = edit.document_changes
    assert isinstance(text_document_edit, TextDocumentEdit)
    assert text_document_edit.text_document.uri == URI
    assert text_document_edit.text_document.version == 7
    new_texts: list[str] = []
    for e in text_document_edit.edits:
        assert isinstance(e, TextEdit)
        new_texts.append(e.new_text)
    assert new_texts == ["z", "z", "z"]


def test_rename_edits_plain_changes_fallback() -> None:
    occ = [(4, 5), (12, 13)]
    edit = features.rename_edits(URI, 7, occ, "z", line_index=IDX, enc=UTF32, document_changes=False)
    assert edit.document_changes is None
    assert edit.changes is not None
    edits = edit.changes[URI]
    assert [e.new_text for e in edits] == ["z", "z"]
    assert (edits[0].range.start.character, edits[0].range.end.character) == (4, 5)


def test_rename_edits_empty_occurrences_document_changes() -> None:
    # A no-op rename renders a well-formed edit carrying zero TextEdits.
    edit = features.rename_edits(URI, 7, [], "z", line_index=IDX, enc=UTF32, document_changes=True)
    assert edit.changes is None
    assert edit.document_changes is not None
    (text_document_edit,) = edit.document_changes
    assert isinstance(text_document_edit, TextDocumentEdit)
    assert list(text_document_edit.edits) == []


def test_rename_edits_empty_occurrences_plain_changes() -> None:
    edit = features.rename_edits(URI, 7, [], "z", line_index=IDX, enc=UTF32, document_changes=False)
    assert edit.document_changes is None
    assert edit.changes is not None
    assert edit.changes[URI] == []
