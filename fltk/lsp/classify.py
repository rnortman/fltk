"""Token stream and the default classification layer.

The default layer assigns a semantic-token type to every terminal span and trivia node in an
analysis-grammar CST, using only the grammar's own structure — no ``.fltklsp`` spec. A terminal
span classifies by *provenance* (which grammar item the parser matched: a ``Literal`` or a
``Regex``) and then by the matched text's shape; a trivia node paints a single ``comment`` over
its whole span. The explicit-paint painter layer is layered on top of this elsewhere.
"""

from __future__ import annotations

import dataclasses
import itertools
import re
import typing

from fltk.fegen import gsm, naming
from fltk.fegen.pyrt.span_protocol import SpanKind
from fltk.lsp import lsp_config

if typing.TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from fltk.lsp.symbols import SymbolTable


@dataclasses.dataclass(frozen=True, order=True)
class Token:
    """A classified span of source text.

    ``start``/``end`` are codepoint offsets in the same coordinate space as ``SpanProtocol``.
    ``token_type`` is a legend member; the ``none`` pseudo-token never appears in output.
    """

    start: int
    end: int
    token_type: str
    modifiers: tuple[str, ...]


# The punctuation set a word-free ``Literal`` maps to; anything else word-free is ``operator``.
_PUNCTUATION: typing.Final[frozenset[str]] = frozenset("()[]{},;:.")
# A word-shaped token starts with an identifier head; this also covers multi-word literals
# such as "execute when".
_WORD_START: typing.Final[re.Pattern[str]] = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_IDENTIFIER: typing.Final[re.Pattern[str]] = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


@dataclasses.dataclass(frozen=True)
class _TerminalTable:
    """The terminal-provenance surfaces of one grammar rule.

    ``label_literals``/``label_regexes`` are keyed by the uppercased label (matching the CST
    ``Label`` enum member name) and hold the ``Literal`` values / compiled ``Regex`` patterns of
    the items carrying that label. ``literals``/``regexes`` are the rule-wide unions used to
    resolve unlabeled spans.
    """

    label_literals: Mapping[str, frozenset[str]]
    label_regexes: Mapping[str, tuple[re.Pattern[str], ...]]
    literals: frozenset[str]
    regexes: tuple[re.Pattern[str], ...]


@dataclasses.dataclass(frozen=True)
class GrammarTables:
    """Precomputed per-rule terminal tables plus the CST-kind-to-rule map."""

    tables: Mapping[str, _TerminalTable]
    kind_to_rule: Mapping[str, gsm.Rule]


def _build_terminal_table(rule: gsm.Rule) -> _TerminalTable:
    # TODO(lsp-rule-surface-index): this per-rule item walk parallels lsp_config._index_rule;
    # unify into one rule-surface index consumed by validation, resolution, and classification.
    label_literals: dict[str, set[str]] = {}
    label_regexes: dict[str, list[re.Pattern[str]]] = {}
    literals: set[str] = set()
    regexes: list[re.Pattern[str]] = []

    def visit(_idx: int, item: gsm.Item) -> None:
        if isinstance(item.term, gsm.Literal):
            literals.add(item.term.value)
            if item.label is not None:
                label_literals.setdefault(item.label.upper(), set()).add(item.term.value)
        elif isinstance(item.term, gsm.Regex):
            pattern = re.compile(item.term.value)
            regexes.append(pattern)
            if item.label is not None:
                label_regexes.setdefault(item.label.upper(), []).append(pattern)

    for alternative in rule.alternatives:
        gsm.for_each_item(alternative, visit)

    return _TerminalTable(
        label_literals={name: frozenset(values) for name, values in label_literals.items()},
        label_regexes={name: tuple(patterns) for name, patterns in label_regexes.items()},
        literals=frozenset(literals),
        regexes=tuple(regexes),
    )


def build_grammar_tables(grammar: gsm.Grammar) -> GrammarTables:
    """Precompute every rule's terminal table and the map from CST node kind name to rule.

    ``grammar`` must already be trivia-classified (``generate_parser`` returns such a grammar as
    ``ParserResult.grammar``): rule ``is_trivia_rule`` flags drive the trivia branch of the walk.
    The kind-to-rule key is the uppercased UpperCamel class name, matching a CST node's
    ``kind.name``.
    """
    tables = {rule.name: _build_terminal_table(rule) for rule in grammar.rules}
    kind_to_rule = {naming.snake_to_upper_camel(rule.name).upper(): rule for rule in grammar.rules}
    return GrammarTables(tables=tables, kind_to_rule=kind_to_rule)


def _classify_literal_text(text: str) -> str:
    if _WORD_START.match(text):
        return "keyword"
    if text in _PUNCTUATION:
        return "punctuation"
    return "operator"


def _classify_regex_text(text: str) -> str:
    first = text[0]
    if first in ('"', "'"):
        return "string"
    if first.isdigit():
        return "number"
    if _IDENTIFIER.fullmatch(text):
        return "variable"
    return "text"


def _classify_span_text(
    full_text: str, start: int, end: int, label_name: str | None, table: _TerminalTable
) -> str | None:
    r"""Classify one terminal span by provenance (literal-first) then text shape.

    A labeled span resolves against only its label's items; an unlabeled span (or a label with no
    terminal items) resolves against the rule-wide literal/regex unions. Regex provenance is tested
    positionally -- ``pattern.match(full_text, start)`` ending exactly at ``end`` -- so a
    context-dependent pattern (lookahead/lookbehind/``\B``) resolves the same way the parser matched
    it, rather than failing a ``fullmatch`` on the isolated slice. ``None`` means no provenance was
    found, so the default layer emits no token.
    """
    segment = full_text[start:end]
    if label_name is not None and (label_name in table.label_literals or label_name in table.label_regexes):
        literals = table.label_literals.get(label_name, frozenset())
        regexes = table.label_regexes.get(label_name, ())
    else:
        literals = table.literals
        regexes = table.regexes

    if segment in literals:
        return _classify_literal_text(segment)
    for pattern in regexes:
        m = pattern.match(full_text, start)
        if m is not None and m.end() == end:
            return _classify_regex_text(segment)
    return None


def rule_for_node(node: typing.Any, tables: GrammarTables) -> gsm.Rule:
    """Resolve the grammar rule of a CST node kind; a miss is an invariant violation.

    Every non-span CST node's ``kind.name`` is by construction the uppercased UpperCamel name of a
    grammar rule, so a lookup miss means the kind/grammar/naming derivations have diverged -- a bug
    to surface loudly, not a node to silently skip.
    """
    rule = tables.kind_to_rule.get(node.kind.name)
    if rule is None:
        msg = f"no grammar rule for CST node kind {node.kind.name!r}"
        raise AssertionError(msg)
    return rule


def child_surface(
    label: typing.Any,
    child: typing.Any,
    text: str,
    tables: GrammarTables,
) -> tuple[bool, int, int, str | None, str | None, str | None]:
    """Decode one ``(label, child)`` pair into the fields matcher dispatch needs.

    Returns ``(is_span, start, end, child_text, child_rule_name, label_name)``: for a span child
    ``child_text`` is its source slice and ``child_rule_name`` is ``None``; for a node child the
    reverse. The paint walk and the symbol-extraction walk share this so both decode a child
    identically before calling :func:`~fltk.lsp.lsp_config.match_applies`.
    """
    is_span = child.kind == SpanKind.SPAN
    if is_span:
        cstart, cend = child.start, child.end
        child_text: str | None = text[cstart:cend]
        child_rule_name: str | None = None
    else:
        cstart, cend = child.span.start, child.span.end
        child_text = None
        child_rule_name = rule_for_node(child, tables).name
    label_name = label.name if label is not None else None
    return is_span, cstart, cend, child_text, child_rule_name, label_name


def _default_intervals(node: typing.Any, tables: GrammarTables, text: str) -> Iterator[tuple[int, int, str]]:
    """Yield ``(start, end, token_type)`` default intervals for a CST node, depth-first.

    A trivia node emits at most one ``comment`` interval over its whole span and is not descended
    into (so terminals inside a comment never repaint). Every other node classifies its own
    terminal (span) children and recurses into its node children.
    """
    rule = rule_for_node(node, tables)
    if rule.is_trivia_rule:
        start, end = node.span.start, node.span.end
        if text[start:end].strip():
            yield (start, end, "comment")
        return

    table = tables.tables[rule.name]
    for label, child in node.children:
        if child.kind == SpanKind.SPAN:
            start, end = child.start, child.end
            if not text[start:end].strip():
                continue
            label_name = label.name if label is not None else None
            token_type = _classify_span_text(text, start, end, label_name, table)
            if token_type is not None:
                yield (start, end, token_type)
        else:
            yield from _default_intervals(child, tables, text)


def default_tokens(
    tree: typing.Any, grammar: gsm.Grammar, text: str, *, tables: GrammarTables | None = None
) -> list[Token]:
    """Classify ``tree`` using only the built-in default table (the ``.fltklsp``-free baseline).

    ``grammar`` must be the trivia-classified grammar the analysis parser was generated from
    (``ParserResult.grammar``). Pass ``tables`` (from :func:`build_grammar_tables`) to reuse a
    precomputed grammar table across calls; when omitted it is built from ``grammar``. Returns a
    sorted, non-overlapping, adjacent-merged token stream with empty modifiers, all within
    ``[0, len(text))``.
    """
    if tables is None:
        tables = build_grammar_tables(grammar)
    intervals = _default_intervals(tree, tables, text)
    return _merge_tokens([Token(start, end, token_type, ()) for start, end, token_type in intervals])


# --- Explicit painter layer -----------------------------------------------------------------------

# An explicit interval and its precedence key. The key is (tree depth of the matched node/child,
# resolution-time tier); larger wins, so an innermost match and a higher-tier statement win.
_Key: typing.TypeAlias = "tuple[int, lsp_config.Tier]"
_Interval: typing.TypeAlias = "tuple[int, int, lsp_config.Paint, _Key]"


def _explicit_intervals(
    node: typing.Any,
    depth: int,
    tables: GrammarTables,
    resolved: lsp_config.ResolvedLspConfig,
    text: str,
    out: list[_Interval],
) -> None:
    """Collect explicit paint intervals over ``node`` and its subtree, depth-first.

    A whole-node paint (from a global rule-name anchor) is recorded at the node's own depth; a
    child match (from a rule-block or global label/literal/rule anchor) is recorded at the child's
    depth (``depth + 1``), so a deeper match outranks a shallower one over their overlap.
    """
    rule = rule_for_node(node, tables)
    for node_paint in resolved.node_paints.get(rule.name, ()):
        out.append((node.span.start, node.span.end, node_paint.paint, (depth, node_paint.tier)))
    matchers = resolved.child_matchers.get(rule.name, ())

    child_depth = depth + 1
    for label, child in node.children:
        is_span, cstart, cend, child_text, child_rule_name, label_name = child_surface(label, child, text, tables)
        for matcher in itertools.chain(matchers, resolved.global_child_matchers):
            if lsp_config.match_applies(matcher.match, label_name, child_text, child_rule_name):
                out.append((cstart, cend, matcher.paint, (child_depth, matcher.tier)))
        if not is_span:
            _explicit_intervals(child, child_depth, tables, resolved, text, out)


def _ref_intervals(symbol_table: SymbolTable, out: list[_Interval]) -> None:
    """Append one explicit-layer interval per resolved, in-legend reference to ``out``.

    A resolved reference inherits its defining kind's first segment as its token; the extractor
    already carried the reference's ``depth`` and ``tier`` so the painter never re-matches. A
    reference enters at ``SOURCE_RANK_REF`` (below ``SOURCE_RANK_SCOPE``), so an explicit ``scope``
    on the same element always wins. Unresolved references and out-of-legend kinds contribute
    nothing and fall through to the defaults.
    """
    for ref in symbol_table.references:
        symbol = ref.symbol
        if symbol is None or not symbol.kind or symbol.kind[0] not in lsp_config.TOKEN_LEGEND:
            continue
        paint = lsp_config.Paint(token=symbol.kind[0], modifiers=())
        out.append((ref.start, ref.end, paint, (ref.depth, ref.tier)))


def _winner_segments(intervals: list[_Interval]) -> list[tuple[int, int, lsp_config.Paint]]:
    """Resolve overlapping explicit intervals into a partition of winning paints.

    Between consecutive interval endpoints the covering set is constant; the max-key interval wins
    (including a ``none`` paint, which still occupies the segment so it occludes losers and
    suppresses defaults). Adjacent segments with the same paint are merged.
    """
    # TODO(lsp-classify-hotpath): this rescans all intervals per boundary pair (O(n^2)); a
    # sweep line maintaining the active set would reach the intended O(n log n).
    if not intervals:
        return []
    boundaries = sorted({b for start, end, _, _ in intervals for b in (start, end)})
    segments: list[tuple[int, int, lsp_config.Paint]] = []
    for a, b in itertools.pairwise(boundaries):
        best: tuple[_Key, lsp_config.Paint] | None = None
        for start, end, paint, key in intervals:
            if start <= a and b <= end and (best is None or key > best[0]):
                best = (key, paint)
        if best is not None:
            paint = best[1]
            if segments and segments[-1][2] == paint and segments[-1][1] == a:
                prev_start = segments[-1][0]
                segments[-1] = (prev_start, b, paint)
            else:
                segments.append((a, b, paint))
    return segments


def _merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge a list of ``[start, end)`` ranges into sorted, non-overlapping coverage."""
    merged: list[tuple[int, int]] = []
    for start, end in sorted(ranges):
        if start >= end:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _subtract(interval: tuple[int, int], covered: list[tuple[int, int]]) -> Iterator[tuple[int, int]]:
    """Yield the parts of ``interval`` not overlapping any range in sorted, merged ``covered``."""
    start, end = interval
    cursor = start
    for cstart, cend in covered:
        if cend <= cursor:
            continue
        if cstart >= end:
            break
        if cstart > cursor:
            yield (cursor, min(cstart, end))
        cursor = max(cursor, cend)
        if cursor >= end:
            return
    if cursor < end:
        yield (cursor, end)


def _merge_tokens(tokens: list[Token]) -> list[Token]:
    """Sort tokens and merge contiguous runs sharing a token type and modifiers."""
    tokens.sort(key=lambda t: (t.start, t.end))
    merged: list[Token] = []
    for token in tokens:
        if (
            merged
            and merged[-1].end == token.start
            and merged[-1].token_type == token.token_type
            and merged[-1].modifiers == token.modifiers
        ):
            prev = merged[-1]
            merged[-1] = Token(prev.start, token.end, prev.token_type, prev.modifiers)
        else:
            merged.append(token)
    return merged


def classify(
    tree: typing.Any,
    grammar: gsm.Grammar,
    resolved_config: lsp_config.ResolvedLspConfig,
    text: str,
    *,
    tables: GrammarTables | None = None,
    symbol_table: SymbolTable | None = None,
) -> list[Token]:
    """Classify ``tree`` under an ``.fltklsp`` spec, layering explicit paints over the defaults.

    ``grammar`` must be the trivia-classified analysis grammar the parser was generated from
    (``ParserResult.grammar``). Pass ``tables`` (from :func:`build_grammar_tables`) to reuse a
    precomputed grammar table across calls -- the hot-path caller (``AnalysisEngine``) builds it
    once per grammar; when omitted it is built from ``grammar``. Pass ``symbol_table`` (from
    :func:`~fltk.lsp.symbols.extract`) to paint resolved references with their defining kind's
    token; omitting it (the default) reproduces the reference-free output exactly. Explicit paints
    win over defaults across their whole span (a ``none`` paint suppresses both defaults and losing
    paints but emits no token); positions no explicit paint covers fall back to the built-in
    defaults. Returns a sorted, non-overlapping, adjacent-merged token stream, all within
    ``[0, len(text))``.
    """
    if tables is None:
        tables = build_grammar_tables(grammar)

    explicit: list[_Interval] = []
    _explicit_intervals(tree, 0, tables, resolved_config, text, explicit)
    if symbol_table is not None:
        _ref_intervals(symbol_table, explicit)
    covered = _merge_ranges([(start, end) for start, end, _, _ in explicit])

    tokens: list[Token] = []
    for start, end, paint in _winner_segments(explicit):
        if paint.token != "none":
            tokens.append(Token(start, end, paint.token, paint.modifiers))

    # TODO(lsp-classify-hotpath): second full tree traversal; fold default emission into the
    # explicit walk above. With symbol extraction (symbols.extract) this is the third O(tree)
    # walk per analysis (extraction, explicit paints, defaults); the same unification folds it in.
    for start, end, token_type in _default_intervals(tree, tables, text):
        for dstart, dend in _subtract((start, end), covered):
            tokens.append(Token(dstart, dend, token_type, ()))

    return _merge_tokens(tokens)
