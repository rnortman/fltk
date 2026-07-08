"""Pure feature logic: analysis results to LSP semantic tokens, folding, and selection.

Each function maps an analysis (its CST or token stream) plus a :class:`~fltk.lsp.positions.LineIndex`
and a negotiated :class:`~fltk.lsp.positions.PositionEncoding` to lsprotocol values, with no server
state, so every feature is unit-testable in isolation. The server layer (elsewhere) owns scheduling,
stale serving, and the protocol loop; this module is the translation between FLTK's codepoint-offset
world and the LSP wire shapes.
"""

from __future__ import annotations

import dataclasses
import logging
from typing import TYPE_CHECKING, Any

from lsprotocol import types as lsp

from fltk.fegen.pyrt.span_protocol import SpanKind

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence

    from fltk.lsp import classify
    from fltk.lsp.positions import LineIndex, PositionEncoding
    from fltk.lsp.symbols import Symbol, SymbolTable

_LOGGER = logging.getLogger(__name__)


# The semantic-token legend, in a fixed wire order. Order is negotiated per session at
# ``initialize`` so it carries no cross-version compatibility burden; it is kept stable for sanity.
# ``SEMANTIC_TOKEN_TYPES`` must set-equal ``lsp_config.TOKEN_LEGEND`` (pinned by a test);
# ``punctuation``, ``text``, ``constant``, and ``label`` are server-defined types (legal per LSP —
# unthemed clients simply do not color them).
SEMANTIC_TOKEN_TYPES: tuple[str, ...] = (
    "keyword",
    "comment",
    "string",
    "number",
    "operator",
    "punctuation",
    "variable",
    "parameter",
    "property",
    "type",
    "function",
    "enumMember",
    "constant",
    "macro",
    "label",
    "text",
)

# The LSP 3.17 standard modifier set, in fixed wire order; must set-equal
# ``lsp_config.LSP_STANDARD_MODIFIERS`` (pinned by a test). ``classify`` only ever emits modifiers
# drawn from this set.
SEMANTIC_TOKEN_MODIFIERS: tuple[str, ...] = (
    "declaration",
    "definition",
    "readonly",
    "static",
    "deprecated",
    "abstract",
    "async",
    "modification",
    "documentation",
    "defaultLibrary",
)

_TYPE_INDEX: dict[str, int] = {name: i for i, name in enumerate(SEMANTIC_TOKEN_TYPES)}
_MODIFIER_BIT: dict[str, int] = {name: 1 << i for i, name in enumerate(SEMANTIC_TOKEN_MODIFIERS)}


@dataclasses.dataclass(frozen=True, order=True)
class TokenSegment:
    """One single-line semantic-token segment at an absolute LSP position.

    ``line``/``char`` are in the negotiated encoding's units against the document the segment was
    computed from; ``length`` likewise. Self-contained: no ``LineIndex`` is needed to consume it,
    which is what lets fresh and stale segments (computed against different document versions) be
    merged after each is rendered to absolute positions against its own index. Field order makes the
    natural ordering positional (``line``, ``char``, ...), so a sorted, non-overlapping token stream
    yields a sorted, non-overlapping segment list.
    """

    line: int
    char: int
    length: int
    type_index: int
    modifier_bits: int


def _modifier_bits(modifiers: tuple[str, ...]) -> int:
    """OR together the legend bits for ``modifiers``; an unknown modifier is defensively dropped.

    ``classify`` only emits standard modifiers, so an unknown name means a legend/classifier drift
    bug -- but a running server drops it rather than crashing the token handler over one token.
    """
    bits = 0
    for modifier in modifiers:
        bit = _MODIFIER_BIT.get(modifier)
        if bit is None:
            _LOGGER.warning("fltk-lsp: dropping unknown semantic-token modifier %r (legend/classifier drift)", modifier)
            continue
        bits |= bit
    return bits


def _line_segments(
    token: classify.Token, line_index: LineIndex, enc: PositionEncoding
) -> Iterator[tuple[int, int, int]]:
    """Split ``token`` at line boundaries into ``(line, char_start, length)`` in ``enc`` units.

    A multi-line token yields one segment per covered line (its first line from the token start to
    that line's content end, whole middle lines, its last line from column 0 to the token end),
    skipping empty segments. Splitting unconditionally is legal whether or not the client advertises
    ``multilineTokenSupport`` and keeps a single code path.
    """
    start_line = line_index.line_of(token.start)
    end_line = line_index.line_of(token.end)
    for line in range(start_line, end_line + 1):
        content_start, content_end = line_index.line_bounds(line)
        seg_start = token.start if line == start_line else content_start
        seg_end = token.end if line == end_line else content_end
        if seg_end <= seg_start:
            continue
        _, char_start = line_index.offset_to_position(seg_start, enc)
        _, char_end = line_index.offset_to_position(seg_end, enc)
        length = char_end - char_start
        if length <= 0:
            continue
        yield (line, char_start, length)


def absolute_segments(
    tokens: Iterable[classify.Token], line_index: LineIndex, enc: PositionEncoding
) -> list[TokenSegment]:
    """Render a sorted, non-overlapping token stream into absolute :class:`TokenSegment`s.

    Legend lookup and the multi-line split happen here: a token whose type is not a legend member is
    defensively dropped-and-warned (``classify`` never emits one), and each token contributes one
    segment per covered line. ``line``/``char``/``length`` are in ``enc`` units against ``line_index``.
    The output is sorted and non-overlapping because the input token stream is.
    """
    segments: list[TokenSegment] = []
    for token in tokens:
        type_index = _TYPE_INDEX.get(token.token_type)
        if type_index is None:
            _LOGGER.warning("fltk-lsp: dropping token of unknown type %r (legend/classifier drift)", token.token_type)
            continue
        modifier_bits = _modifier_bits(token.modifiers)
        for line, char_start, length in _line_segments(token, line_index, enc):
            segments.append(
                TokenSegment(
                    line=line, char=char_start, length=length, type_index=type_index, modifier_bits=modifier_bits
                )
            )
    return segments


def delta_encode_segments(segments: Iterable[TokenSegment]) -> list[int]:
    """Delta-encode absolute segments into the LSP relative token ``data`` array.

    Returns five ints per segment -- ``deltaLine``, ``deltaStartChar``, ``length``, ``tokenType``
    index, ``tokenModifiers`` bitset. Segments must be sorted and non-overlapping (as produced by
    :func:`absolute_segments` and preserved by :func:`merge_stale_segments`).
    """
    data: list[int] = []
    prev_line = 0
    prev_char = 0
    for seg in segments:
        delta_line = seg.line - prev_line
        delta_char = seg.char - prev_char if delta_line == 0 else seg.char
        data.extend((delta_line, delta_char, seg.length, seg.type_index, seg.modifier_bits))
        prev_line = seg.line
        prev_char = seg.char
    return data


def encode_semantic_tokens(tokens: Iterable[classify.Token], line_index: LineIndex, enc: PositionEncoding) -> list[int]:
    """Encode a sorted, non-overlapping token stream into the LSP relative token format.

    Returns the flat ``data`` array: five ints per emitted segment -- ``deltaLine``,
    ``deltaStartChar``, ``length``, ``tokenType`` index, ``tokenModifiers`` bitset -- with columns
    and lengths in ``enc`` units. Multi-line tokens are split at line boundaries; a token whose type
    is not a legend member is defensively skipped (``classify`` never emits one).
    """
    return delta_encode_segments(absolute_segments(tokens, line_index, enc))


def merge_stale_segments(
    fresh: list[TokenSegment],
    stale: list[TokenSegment],
    boundary: tuple[int, int],
) -> list[TokenSegment]:
    """Fresh prefix segments plus the stale segments at or past ``boundary``.

    ``fresh`` is computed against the current text, ``stale`` against the last successfully analyzed
    text; ``boundary`` is the ``(line, char)`` of the fresh prefix's end in the current text. A stale
    segment is kept iff its ``(line, char)`` start is ``>=`` the floor -- the max of ``boundary`` and
    the end position of the last fresh segment -- so the result stays sorted and non-overlapping even
    when an edit shifted the stale coordinates backward. No attempt is made to shift stale positions:
    the server uses full-document sync and has no edit deltas, so kept stale segments carry positions
    from the old text, clamped or ignored client-side past the current document's end.
    """
    floor = boundary
    if fresh:
        last = fresh[-1]
        floor = max(boundary, (last.line, last.char + last.length))
    result = list(fresh)
    for seg in stale:
        if (seg.line, seg.char) >= floor:
            result.append(seg)
    return result


def _walk_nodes(node: Any) -> Iterator[Any]:
    """Yield every non-span CST node in ``node``'s subtree, pre-order (outermost first)."""
    yield node
    for _label, child in node.children:
        if child.kind != SpanKind.SPAN:
            yield from _walk_nodes(child)


def folding_ranges(tree: Any, trivia_kind_names: frozenset[str], line_index: LineIndex) -> list[lsp.FoldingRange]:
    """Emit a folding range for every CST node covering more than one line.

    A node's fold runs from the line of its span start to the line of its last covered codepoint;
    single-line nodes are skipped. Nodes whose ``kind`` names a trivia rule get
    ``FoldingRangeKind.Comment``; others get no kind. Duplicate ``(start_line, end_line)`` extents
    (nested nodes sharing line bounds) keep the first, outermost node.
    """
    seen: set[tuple[int, int]] = set()
    out: list[lsp.FoldingRange] = []
    for node in _walk_nodes(tree):
        span = node.span
        start_line = line_index.line_of(span.start)
        end_line = line_index.line_of(max(span.start, span.end - 1))
        if end_line <= start_line:
            continue
        key = (start_line, end_line)
        if key in seen:
            continue
        seen.add(key)
        kind = lsp.FoldingRangeKind.Comment if node.kind.name in trivia_kind_names else None
        out.append(lsp.FoldingRange(start_line=start_line, end_line=end_line, kind=kind))
    return out


# --- Symbol navigation, outline, and rename -------------------------------------------------------

# The fixed kind-first-segment -> LSP SymbolKind table (spec-defined). The def/ref kind vocabulary
# stays open; a first segment with no entry renders as ``Object`` but is still an exact-match ref
# target. Extending the table later is additive.
SYMBOL_KINDS: dict[str, lsp.SymbolKind] = {
    "type": lsp.SymbolKind.Class,
    "function": lsp.SymbolKind.Function,
    "variable": lsp.SymbolKind.Variable,
    "constant": lsp.SymbolKind.Constant,
    "field": lsp.SymbolKind.Field,
    "enumMember": lsp.SymbolKind.EnumMember,
    "namespace": lsp.SymbolKind.Namespace,
    "property": lsp.SymbolKind.Property,
    "enum": lsp.SymbolKind.Enum,
    "struct": lsp.SymbolKind.Struct,
    "interface": lsp.SymbolKind.Interface,
    "module": lsp.SymbolKind.Module,
    "method": lsp.SymbolKind.Method,
}


def _symbol_kind(kind: tuple[str, ...]) -> lsp.SymbolKind:
    """Map a dotted kind's first segment to an LSP ``SymbolKind`` (``Object`` fallback)."""
    first = kind[0] if kind else ""
    return SYMBOL_KINDS.get(first, lsp.SymbolKind.Object)


def _strictly_contains(outer: Symbol, inner: Symbol) -> bool:
    """Whether ``outer``'s declaration range strictly encloses ``inner``'s (equal ranges are siblings)."""
    return (
        outer.range_start <= inner.range_start
        and inner.range_end <= outer.range_end
        and (outer.range_start, outer.range_end) != (inner.range_start, inner.range_end)
    )


def document_symbols(table: SymbolTable, line_index: LineIndex, enc: PositionEncoding) -> list[lsp.DocumentSymbol]:
    """The hierarchical document outline: one :class:`DocumentSymbol` per definition, nested by containment.

    Nesting is by declaration-range containment via a stack over symbols sorted by
    ``(range_start, -range_end)`` -- not name-start order, so a container whose name child trails its
    members still parents them. ``range`` is the declaration range, ``selection_range`` the name span
    (contained in ``range`` by construction). Equal ranges are siblings.
    """
    ordered = sorted(table.symbols, key=lambda s: (s.range_start, -s.range_end))
    roots: list[lsp.DocumentSymbol] = []
    stack: list[tuple[Symbol, list[lsp.DocumentSymbol]]] = []
    for symbol in ordered:
        children: list[lsp.DocumentSymbol] = []
        node = lsp.DocumentSymbol(
            name=symbol.name,
            detail=".".join(symbol.kind),
            kind=_symbol_kind(symbol.kind),
            range=_render_range(symbol.range_start, symbol.range_end, line_index, enc),
            selection_range=_render_range(symbol.name_start, symbol.name_end, line_index, enc),
            children=children,
        )
        while stack and not _strictly_contains(stack[-1][0], symbol):
            stack.pop()
        if stack:
            stack[-1][1].append(node)
        else:
            roots.append(node)
        stack.append((symbol, children))
    return roots


def document_symbols_flat(
    table: SymbolTable, uri: str, line_index: LineIndex, enc: PositionEncoding
) -> list[lsp.SymbolInformation]:
    """The flat document outline, for clients without hierarchical-symbol support.

    One :class:`SymbolInformation` per definition in document order, located at its declaration range.
    """
    return [
        lsp.SymbolInformation(
            name=symbol.name,
            kind=_symbol_kind(symbol.kind),
            location=lsp.Location(uri=uri, range=_render_range(symbol.range_start, symbol.range_end, line_index, enc)),
        )
        for symbol in table.symbols
    ]


def target_span(table: SymbolTable, offset: int) -> tuple[Symbol, tuple[int, int]] | None:
    """The addressed symbol and the exact span under the cursor, or ``None``.

    The span is the definition name span when a definition is under the cursor, else the
    reference span when a resolved reference is. An unresolved reference (or empty space)
    yields ``None``.
    """
    symbol = table.symbol_at(offset)
    if symbol is not None:
        return symbol, (symbol.name_start, symbol.name_end)
    reference = table.reference_at(offset)
    if reference is not None and reference.symbol is not None:
        return reference.symbol, (reference.start, reference.end)
    return None


def symbol_target(table: SymbolTable, offset: int) -> Symbol | None:
    """The symbol the cursor addresses: the definition under it, else a reference's resolved symbol."""
    result = target_span(table, offset)
    return result[0] if result is not None else None


def definition_location(
    table: SymbolTable, offset: int, uri: str, line_index: LineIndex, enc: PositionEncoding
) -> lsp.Location | None:
    """The target symbol's name span (go-to-def on the definition itself returns itself), else ``None``."""
    symbol = symbol_target(table, offset)
    if symbol is None:
        return None
    return lsp.Location(uri=uri, range=_render_range(symbol.name_start, symbol.name_end, line_index, enc))


def reference_locations(
    table: SymbolTable,
    offset: int,
    uri: str,
    line_index: LineIndex,
    enc: PositionEncoding,
    *,
    include_declaration: bool,
) -> list[lsp.Location] | None:
    """Every occurrence of the target symbol; the declaration span is included per ``include_declaration``."""
    symbol = symbol_target(table, offset)
    if symbol is None:
        return None
    declaration = (symbol.name_start, symbol.name_end)
    locations: list[lsp.Location] = []
    for start, end in table.occurrences(symbol):
        if not include_declaration and (start, end) == declaration:
            continue
        locations.append(lsp.Location(uri=uri, range=_render_range(start, end, line_index, enc)))
    return locations


def document_highlights(
    table: SymbolTable, offset: int, line_index: LineIndex, enc: PositionEncoding
) -> list[lsp.DocumentHighlight] | None:
    """Highlight every occurrence of the target symbol: ``Write`` on the declaration, ``Read`` on references."""
    symbol = symbol_target(table, offset)
    if symbol is None:
        return None
    declaration = (symbol.name_start, symbol.name_end)
    highlights: list[lsp.DocumentHighlight] = []
    for start, end in table.occurrences(symbol):
        kind = lsp.DocumentHighlightKind.Write if (start, end) == declaration else lsp.DocumentHighlightKind.Read
        highlights.append(lsp.DocumentHighlight(range=_render_range(start, end, line_index, enc), kind=kind))
    return highlights


def prepare_rename(table: SymbolTable, offset: int, line_index: LineIndex, enc: PositionEncoding) -> lsp.Range | None:
    """The exact renamable span under the cursor (name span or ref span), or ``None`` when nothing resolves."""
    result = target_span(table, offset)
    if result is None:
        return None
    _symbol, (start, end) = result
    return _render_range(start, end, line_index, enc)


def rename_occurrences(table: SymbolTable, offset: int) -> tuple[Symbol, list[tuple[int, int]]] | None:
    """The target symbol and its raw codepoint occurrence set, or ``None`` when nothing resolves.

    The server (not this module) renders the :class:`WorkspaceEdit`, because its verify-reparse guard
    needs the raw offsets to apply the edits in memory before committing them.
    """
    symbol = symbol_target(table, offset)
    if symbol is None:
        return None
    return symbol, table.occurrences(symbol)


def rename_edits(
    uri: str,
    version: int | None,
    occurrences: Sequence[tuple[int, int]],
    new_name: str,
    line_index: LineIndex,
    enc: PositionEncoding,
    *,
    document_changes: bool,
) -> lsp.WorkspaceEdit:
    """Render a :class:`WorkspaceEdit` renaming every occurrence to ``new_name``.

    Occurrences are non-overlapping (deduped upstream), so the edits are well-formed. When
    ``document_changes`` (the client advertised ``workspace.workspaceEdit.documentChanges``), the
    edit is versioned against the analyzed document so a conforming client refuses a stale apply;
    otherwise the plain ``changes`` fallback is returned.
    """
    if document_changes:
        edits: list[lsp.TextEdit | lsp.AnnotatedTextEdit] = [
            lsp.TextEdit(range=_render_range(start, end, line_index, enc), new_text=new_name)
            for start, end in occurrences
        ]
        return lsp.WorkspaceEdit(
            document_changes=[
                lsp.TextDocumentEdit(
                    text_document=lsp.OptionalVersionedTextDocumentIdentifier(uri=uri, version=version),
                    edits=edits,
                )
            ]
        )
    changes = [
        lsp.TextEdit(range=_render_range(start, end, line_index, enc), new_text=new_name) for start, end in occurrences
    ]
    return lsp.WorkspaceEdit(changes={uri: changes})


def _spans_containing(node: Any, offset: int) -> list[tuple[int, int]]:
    """Codepoint ``(start, end)`` spans on the root-to-innermost path whose ``[start, end)`` holds ``offset``.

    CST children are sorted and non-overlapping, so at most one child on each level contains
    ``offset``; a terminal ``Span`` child is the innermost element (word-level selection).
    """
    start, end = node.span.start, node.span.end
    if not (start <= offset < end):
        return []
    chain: list[tuple[int, int]] = [(start, end)]
    for _label, child in node.children:
        if child.kind == SpanKind.SPAN:
            if child.start <= offset < child.end:
                chain.append((child.start, child.end))
                break
        elif child.span.start <= offset < child.span.end:
            chain.extend(_spans_containing(child, offset))
            break
    return chain


def _render_range(start: int, end: int, line_index: LineIndex, enc: PositionEncoding) -> lsp.Range:
    """Build an LSP ``Range`` from codepoint offsets in ``enc`` units."""
    start_line, start_char = line_index.offset_to_position(start, enc)
    end_line, end_char = line_index.offset_to_position(end, enc)
    return lsp.Range(
        start=lsp.Position(line=start_line, character=start_char),
        end=lsp.Position(line=end_line, character=end_char),
    )


def selection_ranges(
    tree: Any, offsets: Sequence[int], line_index: LineIndex, enc: PositionEncoding
) -> list[lsp.SelectionRange]:
    """For each requested codepoint ``offset``, the innermost-to-outermost ``SelectionRange`` chain.

    The head range is the innermost element containing the offset; each ``parent`` widens strictly
    outward (ancestors with an identical span are collapsed, since LSP requires strictly-widening
    ranges). An offset that no element contains (e.g. end-of-document) yields a zero-width range at
    that position.
    """
    result: list[lsp.SelectionRange] = []
    for offset in offsets:
        chain = _spans_containing(tree, offset)
        unique: list[tuple[int, int]] = []
        for span in chain:
            if not unique or unique[-1] != span:
                unique.append(span)
        selection: lsp.SelectionRange | None = None
        for start, end in unique:  # outermost first, building parent links inward
            selection = lsp.SelectionRange(range=_render_range(start, end, line_index, enc), parent=selection)
        if selection is None:
            line, char = line_index.offset_to_position(offset, enc)
            position = lsp.Position(line=line, character=char)
            selection = lsp.SelectionRange(range=lsp.Range(start=position, end=position), parent=None)
        result.append(selection)
    return result
