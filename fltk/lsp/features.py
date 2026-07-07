"""Pure feature logic: analysis results to LSP semantic tokens, folding, and selection.

Each function maps an analysis (its CST or token stream) plus a :class:`~fltk.lsp.positions.LineIndex`
and a negotiated :class:`~fltk.lsp.positions.PositionEncoding` to lsprotocol values, with no server
state, so every feature is unit-testable in isolation. The server layer (elsewhere) owns scheduling,
stale serving, and the protocol loop; this module is the translation between FLTK's codepoint-offset
world and the LSP wire shapes.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from lsprotocol import types as lsp

from fltk.fegen.pyrt.span_protocol import SpanKind

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence

    from fltk.lsp import classify
    from fltk.lsp.positions import LineIndex, PositionEncoding

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


def encode_semantic_tokens(tokens: Iterable[classify.Token], line_index: LineIndex, enc: PositionEncoding) -> list[int]:
    """Encode a sorted, non-overlapping token stream into the LSP relative token format.

    Returns the flat ``data`` array: five ints per emitted segment -- ``deltaLine``,
    ``deltaStartChar``, ``length``, ``tokenType`` index, ``tokenModifiers`` bitset -- with columns
    and lengths in ``enc`` units. Multi-line tokens are split at line boundaries; a token whose type
    is not a legend member is defensively skipped (``classify`` never emits one).
    """
    data: list[int] = []
    prev_line = 0
    prev_char = 0
    for token in tokens:
        type_index = _TYPE_INDEX.get(token.token_type)
        if type_index is None:
            _LOGGER.warning("fltk-lsp: dropping token of unknown type %r (legend/classifier drift)", token.token_type)
            continue
        modifier_bits = _modifier_bits(token.modifiers)
        for line, char_start, length in _line_segments(token, line_index, enc):
            delta_line = line - prev_line
            delta_char = char_start - prev_char if delta_line == 0 else char_start
            data.extend((delta_line, delta_char, length, type_index, modifier_bits))
            prev_line = line
            prev_char = char_start
    return data


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
