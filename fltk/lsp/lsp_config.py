"""Config model for ``.fltklsp`` files and the CST-to-model transform.

Mirrors ``fmt_config.py``'s CST-in / plain-dataclasses-out shape. This module covers
only the pre-resolution model: parsing a ``.fltklsp`` CST into plain dataclasses. Load-time
GSM validation and anchor resolution live elsewhere.
"""

from __future__ import annotations

import dataclasses
import itertools
import typing
from ast import literal_eval

from fltk.fegen import gsm
from fltk.fegen.pyrt import error_formatter, errors, terminalsrc
from fltk.lsp import fltklsp_cst as cst
from fltk.lsp.fltklsp_parser import Parser

if typing.TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from fltk.fegen.pyrt import span_protocol

# LSP 3.17 predefined semantic-token modifiers. Trailing segments of a scope's dotted name
# that name one of these are carried as modifiers; the rest are carried as hints.
LSP_STANDARD_MODIFIERS: frozenset[str] = frozenset(
    {
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
    }
)

# The round-1 token legend: the scope-token names a ``scope`` statement's first segment may
# use. The pseudo-token ``none`` (suppression) is accepted separately by validation and is not
# a member here. The default classifier and painter (classify.py) consume the same legend.
TOKEN_LEGEND: frozenset[str] = frozenset(
    {
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
    }
)


@dataclasses.dataclass(frozen=True)
class Anchor:
    """A parsed, pre-resolution anchor. Exactly one of a qualified/unqualified identifier
    (``name``) or a ``literal`` is populated."""

    qualifier: typing.Literal["label", "rule"] | None
    name: str | None
    literal: str | None
    span: span_protocol.SpanProtocol


@dataclasses.dataclass(frozen=True)
class ScopeStmt:
    anchors: tuple[Anchor, ...]
    token: str
    modifiers: tuple[str, ...]
    hints: tuple[str, ...]
    index: int
    token_span: span_protocol.SpanProtocol  # the scope dotted-name span, for error reporting


@dataclasses.dataclass(frozen=True)
class DefStmt:
    anchor: Anchor
    kind: tuple[str, ...]
    index: int


@dataclasses.dataclass(frozen=True)
class RefStmt:
    anchor: Anchor
    kinds: tuple[tuple[str, ...], ...] | typing.Literal["*"]
    index: int


@dataclasses.dataclass(frozen=True)
class RuleBlock:
    rule_name: str
    rule_name_span: span_protocol.SpanProtocol
    scopes: tuple[ScopeStmt, ...]
    defs: tuple[DefStmt, ...]
    refs: tuple[RefStmt, ...]
    is_namespace: bool


@dataclasses.dataclass(frozen=True)
class LspConfig:
    global_scopes: tuple[ScopeStmt, ...]
    rule_blocks: tuple[RuleBlock, ...]


# TODO(lsp-cst-text-helpers): consolidate the span-text / identifier / literal extraction
# helpers shared with fmt_config and unparse.pyrt into one guarded, SpanProtocol-typed helper.
def _span_text(span: object, terminal_src: terminalsrc.TerminalSource) -> str:
    """Return the source text for a span, handling both Python and Rust backends."""
    if hasattr(span, "text"):
        text = span.text()  # type: ignore[union-attr]
        if text is not None:
            return text
    return terminal_src.terminals[span.start : span.end]  # type: ignore[union-attr]


def _identifier_text(identifier: cst.Identifier, terminal_src: terminalsrc.TerminalSource) -> str:
    return _span_text(identifier.child_name(), terminal_src)


def _dotted_name(dotted: cst.DottedName, terminal_src: terminalsrc.TerminalSource) -> tuple[str, ...]:
    return tuple(_identifier_text(part, terminal_src) for part in dotted.children_part())


def _parse_anchor(anchor: cst.Anchor, terminal_src: terminalsrc.TerminalSource) -> Anchor:
    literal = anchor.maybe_literal()
    if literal is not None:
        quoted = _span_text(literal.child_value(), terminal_src)
        try:
            value = literal_eval(quoted)
        except (SyntaxError, ValueError) as exc:
            offense = _render_offense(anchor.span, terminal_src, f"invalid literal {quoted!r}: {exc}")
            raise LspConfigError("1 error(s) validating .fltklsp config:" + offense) from exc
        return Anchor(qualifier=None, name=None, literal=value, span=anchor.span)

    qualifier: typing.Literal["label", "rule"] | None = None
    qual = anchor.maybe_qualifier()
    if qual is not None:
        if qual.maybe_label() is not None:
            qualifier = "label"
        else:
            assert qual.maybe_rule() is not None, f"qualifier node has neither label nor rule: {qual!r}"
            qualifier = "rule"
    name = _identifier_text(anchor.child_name(), terminal_src)
    return Anchor(qualifier=qualifier, name=name, literal=None, span=anchor.span)


def _parse_scope_stmt(scope: cst.ScopeStmt, terminal_src: terminalsrc.TerminalSource, index: int) -> ScopeStmt:
    anchor_list = scope.child_anchor_list()
    anchors = tuple(_parse_anchor(a, terminal_src) for a in anchor_list.children_anchor())
    scope_name = scope.child_scope()
    segments = _dotted_name(scope_name, terminal_src)
    assert segments, "dotted name must have at least one segment"
    token = segments[0]
    modifiers = tuple(s for s in segments[1:] if s in LSP_STANDARD_MODIFIERS)
    hints = tuple(s for s in segments[1:] if s not in LSP_STANDARD_MODIFIERS)
    return ScopeStmt(
        anchors=anchors,
        token=token,
        modifiers=modifiers,
        hints=hints,
        index=index,
        token_span=scope_name.span,
    )


def _parse_def_stmt(def_stmt: cst.DefStmt, terminal_src: terminalsrc.TerminalSource, index: int) -> DefStmt:
    anchor = _parse_anchor(def_stmt.child_anchor(), terminal_src)
    kind = _dotted_name(def_stmt.child_kind(), terminal_src)
    return DefStmt(anchor=anchor, kind=kind, index=index)


def _parse_ref_stmt(ref_stmt: cst.RefStmt, terminal_src: terminalsrc.TerminalSource, index: int) -> RefStmt:
    anchor = _parse_anchor(ref_stmt.child_anchor(), terminal_src)
    kind_list = ref_stmt.child_kind_list()
    kinds: tuple[tuple[str, ...], ...] | typing.Literal["*"]
    if kind_list.maybe_wildcard() is not None:
        kinds = "*"
    else:
        kinds = tuple(_dotted_name(dn, terminal_src) for dn in kind_list.children_kind())
    return RefStmt(anchor=anchor, kinds=kinds, index=index)


def _parse_rule_block(
    rule_config: cst.RuleConfig, terminal_src: terminalsrc.TerminalSource, counter: Iterator[int]
) -> RuleBlock:
    rule_name_id = rule_config.child_rule_name()
    rule_name = _identifier_text(rule_name_id, terminal_src)

    scopes: list[ScopeStmt] = []
    defs: list[DefStmt] = []
    refs: list[RefStmt] = []
    is_namespace = False

    for rule_statement in rule_config.children_rule_statement():
        if (scope := rule_statement.maybe_scope_stmt()) is not None:
            scopes.append(_parse_scope_stmt(scope, terminal_src, next(counter)))
        elif (def_stmt := rule_statement.maybe_def_stmt()) is not None:
            defs.append(_parse_def_stmt(def_stmt, terminal_src, next(counter)))
        elif (ref_stmt := rule_statement.maybe_ref_stmt()) is not None:
            refs.append(_parse_ref_stmt(ref_stmt, terminal_src, next(counter)))
        elif rule_statement.maybe_namespace_stmt() is not None:
            is_namespace = True
        else:
            msg = f"unhandled rule_statement CST node: {rule_statement!r}"
            raise AssertionError(msg)

    return RuleBlock(
        rule_name=rule_name,
        rule_name_span=rule_name_id.span,
        scopes=tuple(scopes),
        defs=tuple(defs),
        refs=tuple(refs),
        is_namespace=is_namespace,
    )


def lsp_cst_to_config(lsp_spec: cst.LspSpec, terminal_src: terminalsrc.TerminalSource) -> LspConfig:
    """Transform a parsed ``.fltklsp`` CST into the pre-resolution :class:`LspConfig` model."""
    # Monotonic file-order statement index, shared across global and rule-block statements.
    counter = itertools.count()
    global_scopes: list[ScopeStmt] = []
    rule_blocks: list[RuleBlock] = []

    for statement in lsp_spec.children_statement():
        if (scope := statement.maybe_scope_stmt()) is not None:
            global_scopes.append(_parse_scope_stmt(scope, terminal_src, next(counter)))
        elif (rule_config := statement.maybe_rule_config()) is not None:
            rule_blocks.append(_parse_rule_block(rule_config, terminal_src, counter))
        else:
            msg = f"unhandled statement CST node: {statement!r}"
            raise AssertionError(msg)

    return LspConfig(global_scopes=tuple(global_scopes), rule_blocks=tuple(rule_blocks))


@dataclasses.dataclass(frozen=True)
class RuleIndex:
    """The anchor-matchable surfaces of one grammar rule.

    ``labels`` are every ``Item.label`` — explicit or the implicit label that fltk2gsm
    assigns to an unlabeled rule invocation (equal to the invoked rule name). ``literals``
    are every ``Literal`` term value; ``invoked_rules`` every ``Identifier`` (rule
    invocation) term value. All three recurse through ``Sequence[Items]`` sub-expressions.
    """

    labels: frozenset[str]
    literals: frozenset[str]
    invoked_rules: frozenset[str]


@dataclasses.dataclass(frozen=True)
class GrammarIndex:
    """Per-rule and grammar-wide anchor-matchable surfaces, consumed by anchor validation.

    ``rules`` maps each grammar rule name to its :class:`RuleIndex`. ``rule_names`` is every
    rule name in the grammar; ``all_labels`` and ``all_literals`` are the grammar-wide unions
    of every rule's labels and literals.
    """

    rules: Mapping[str, RuleIndex]
    rule_names: frozenset[str]
    all_labels: frozenset[str]
    all_literals: frozenset[str]


def _index_rule(rule: gsm.Rule) -> RuleIndex:
    # TODO(lsp-rule-surface-index): this per-rule item walk parallels classify._build_terminal_table;
    # unify into one rule-surface index consumed by validation, resolution, and classification.
    labels: set[str] = set()
    literals: set[str] = set()
    invoked_rules: set[str] = set()

    def visit(_idx: int, item: gsm.Item) -> None:
        if item.label is not None:
            labels.add(item.label)
        if isinstance(item.term, gsm.Literal):
            literals.add(item.term.value)
        elif isinstance(item.term, gsm.Identifier):
            invoked_rules.add(item.term.value)

    for alternative in rule.alternatives:
        gsm.for_each_item(alternative, visit)

    return RuleIndex(
        labels=frozenset(labels),
        literals=frozenset(literals),
        invoked_rules=frozenset(invoked_rules),
    )


def build_grammar_index(grammar: gsm.Grammar) -> GrammarIndex:
    """Precompute the anchor-matchable surfaces of ``grammar`` for load-time anchor validation."""
    rules = {rule.name: _index_rule(rule) for rule in grammar.rules}
    all_labels: set[str] = set()
    all_literals: set[str] = set()
    for rule_index in rules.values():
        all_labels |= rule_index.labels
        all_literals |= rule_index.literals
    return GrammarIndex(
        rules=rules,
        rule_names=frozenset(grammar.identifiers),
        all_labels=frozenset(all_labels),
        all_literals=frozenset(all_literals),
    )


class LspConfigError(ValueError):
    """Raised when a parsed ``.fltklsp`` config fails load-time GSM validation.

    The message renders every collected offense with a ``file:line:col`` caret annotation, so a
    single raise reports all validation errors in one pass rather than fail-fast.
    """


def _render_offense(span: span_protocol.SpanProtocol, terminals: terminalsrc.TerminalSource, message: str) -> str:
    """Format one offense against the ``.fltklsp`` source.

    The stored config spans come from the Python-backend parser and carry no source, so the
    source is re-attached here from ``terminals`` before rendering the caret line.
    """
    source_span = terminalsrc.Span.with_source(
        span.start, span.end, terminalsrc.SourceText(terminals.terminals, terminals.filename)
    )
    return error_formatter.format_source_line(source_span, message)


def _validate_scope_token(
    scope: ScopeStmt,
    offenses: list[tuple[span_protocol.SpanProtocol, str]],
) -> None:
    """The scope token's first segment must be in the legend, or be a sole ``none``."""
    if scope.token == "none":
        if scope.modifiers or scope.hints:
            offenses.append((scope.token_span, "scope 'none' must be the only segment (no modifiers or hints)"))
        return
    if scope.token not in TOKEN_LEGEND:
        offenses.append((scope.token_span, f"unknown scope token {scope.token!r} (not in the token legend)"))


def _validate_local_anchor(
    anchor: Anchor,
    rule_name: str,
    rule_index: RuleIndex,
    offenses: list[tuple[span_protocol.SpanProtocol, str]],
) -> None:
    """An anchor inside ``rule X`` must match one of ``X``'s items (a label, invoked rule, or literal)."""
    if anchor.literal is not None:
        if anchor.literal not in rule_index.literals:
            offenses.append(
                (anchor.span, f"literal {anchor.literal!r} does not match any literal in rule {rule_name!r}")
            )
        return
    name = anchor.name
    if anchor.qualifier == "label":
        matched = name in rule_index.labels
        message = f"no item labeled {name!r} in rule {rule_name!r}"
    elif anchor.qualifier == "rule":
        matched = name in rule_index.invoked_rules
        message = f"rule {rule_name!r} does not invoke a rule named {name!r}"
    else:
        matched = name in rule_index.labels or name in rule_index.invoked_rules
        message = f"no item labeled {name!r} and no invoked rule {name!r} in rule {rule_name!r}"
    if not matched:
        offenses.append((anchor.span, message))


def _validate_global_anchor(
    anchor: Anchor,
    index: GrammarIndex,
    offenses: list[tuple[span_protocol.SpanProtocol, str]],
) -> None:
    """A global anchor matches the union of grammar rule names, item labels, and literals."""
    if anchor.literal is not None:
        if anchor.literal not in index.all_literals:
            offenses.append((anchor.span, f"literal {anchor.literal!r} does not appear in the grammar"))
        return
    name = anchor.name
    if anchor.qualifier == "label":
        matched = name in index.all_labels
        message = f"{name!r} is not an item label anywhere in the grammar"
    elif anchor.qualifier == "rule":
        matched = name in index.rule_names
        message = f"{name!r} is not a grammar rule name"
    else:
        matched = name in index.rule_names or name in index.all_labels
        message = f"{name!r} is not a grammar rule name or an item label"
    if not matched:
        offenses.append((anchor.span, message))


def validate_config(config: LspConfig, index: GrammarIndex, terminals: terminalsrc.TerminalSource) -> None:
    """Validate a parsed ``LspConfig`` against a grammar's :class:`GrammarIndex`.

    Collects every offense rather than failing on the first, and raises a single
    :class:`LspConfigError` whose message renders each with a ``file:line:col`` caret annotation.
    The def/ref kind vocabulary is intentionally open, so kinds are not validated here.
    """
    offenses: list[tuple[span_protocol.SpanProtocol, str]] = []

    for scope in config.global_scopes:
        _validate_scope_token(scope, offenses)
        for anchor in scope.anchors:
            _validate_global_anchor(anchor, index, offenses)

    for block in config.rule_blocks:
        rule_index = index.rules.get(block.rule_name)
        if rule_index is None:
            # Unknown rule. The block's anchors reference this rule's items, so without a rule
            # index there is nothing to check them against — skip them (the unknown-rule error stands).
            offenses.append((block.rule_name_span, f"unknown grammar rule {block.rule_name!r}"))
        for scope in block.scopes:
            _validate_scope_token(scope, offenses)
            if rule_index is not None:
                for anchor in scope.anchors:
                    _validate_local_anchor(anchor, block.rule_name, rule_index, offenses)
        if rule_index is not None:
            for def_stmt in block.defs:
                _validate_local_anchor(def_stmt.anchor, block.rule_name, rule_index, offenses)
            for ref_stmt in block.refs:
                _validate_local_anchor(ref_stmt.anchor, block.rule_name, rule_index, offenses)

    if offenses:
        offenses.sort(key=lambda offense: (offense[0].start, offense[0].end))
        header = f"{len(offenses)} error(s) validating .fltklsp config:"
        body = "".join(_render_offense(span, terminals, message) for span, message in offenses)
        raise LspConfigError(header + body)


@dataclasses.dataclass(frozen=True)
class ByLabel:
    """Match a child by the label its owning rule assigned to it."""

    name: str
    # Uppercased ``name``, matching the CST ``Label`` enum member name the classifier compares
    # against. Cached at construction; excluded from equality/repr so the by-value identity stays
    # keyed on ``name`` alone.
    name_upper: str = dataclasses.field(init=False, compare=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name_upper", self.name.upper())


@dataclasses.dataclass(frozen=True)
class ByLiteralText:
    """Match a child span whose source text equals a literal value."""

    text: str


@dataclasses.dataclass(frozen=True)
class ByChildRule:
    """Match a child node produced by an invocation of the named rule."""

    name: str


Match = ByLabel | ByLiteralText | ByChildRule


def match_applies(
    match: Match,
    label_name: str | None,
    child_text: str | None,
    child_rule_name: str | None,
) -> bool:
    """Whether a resolved matcher applies to one child of a CST node.

    ``label_name`` is the uppercased label the parent rule assigned the child (``None`` when
    unlabeled). ``child_text`` is the source text of a span child (``None`` for a node child);
    ``child_rule_name`` is the rule name of a node child (``None`` for a span child). The
    classifier and the symbol extractor share this predicate.
    """
    if isinstance(match, ByLabel):
        return label_name is not None and label_name == match.name_upper
    if isinstance(match, ByLiteralText):
        return child_text == match.text
    # ByChildRule: a node child produced by an invocation of the named rule.
    return child_rule_name is not None and child_rule_name == match.name


@dataclasses.dataclass(frozen=True)
class Paint:
    """A resolved paint: a legend token (or the ``none`` pseudo-token) plus modifiers."""

    token: str
    modifiers: tuple[str, ...]


# Precedence ranks composing a paint's Tier. The classifier prepends the matched node's tree
# depth and compares the full tuple (depth, source_rank, anchor_rank, block_rank, stmt_index),
# max wins. Explicit ``scope`` outranks def-derived paint at the same node; a label/literal
# anchor outranks a rule-name anchor; a rule-block anchor outranks a global one; later
# statements win ties.
SOURCE_RANK_SCOPE = 2
SOURCE_RANK_DEF = 1
SOURCE_RANK_REF = 1  # == SOURCE_RANK_DEF; explicit scope (2) beats both in ref-site paint
ANCHOR_RANK_LABEL_LITERAL = 1
ANCHOR_RANK_RULE_NAME = 0
BLOCK_RANK_RULE = 1
BLOCK_RANK_GLOBAL = 0


@dataclasses.dataclass(frozen=True, order=True)
class Tier:
    """The resolution-time portion of a paint's precedence key, in comparison order."""

    source_rank: int
    anchor_rank: int
    block_rank: int
    stmt_index: int


@dataclasses.dataclass(frozen=True)
class NodePaint:
    """A whole-node paint from a global rule-name anchor."""

    paint: Paint
    tier: Tier


@dataclasses.dataclass(frozen=True)
class ChildMatcher:
    """A matcher the classifier tries against a parent node's children."""

    match: Match
    paint: Paint
    tier: Tier


@dataclasses.dataclass(frozen=True)
class DefMatcher:
    """A ``def`` statement's semantic matcher: which child it defines and the symbol's kind.

    Distinct from the def's *paint* matcher (a ``ChildMatcher`` in ``child_matchers``): this
    drives symbol extraction, keyed by the block's rule name. ``tier`` picks one winner per
    child when several defs match, matching the painter's precedence.
    """

    match: Match
    kind: tuple[str, ...]
    tier: Tier


@dataclasses.dataclass(frozen=True)
class RefMatcher:
    """A ``ref`` statement's matcher: which child is a reference and which kinds it may resolve to."""

    match: Match
    kinds: tuple[tuple[str, ...], ...] | typing.Literal["*"]
    tier: Tier


@dataclasses.dataclass(frozen=True)
class ResolvedLspConfig:
    """The classifier's precomputed matcher tables plus the semantic def/ref/namespace tables.

    ``node_paints`` maps a grammar rule name to whole-node paints (from global rule-name
    anchors). ``child_matchers`` maps a *parent* rule name to the matchers to try against its
    children (from anchors inside that rule's block). ``global_child_matchers`` are label/literal
    matchers from global scopes; they apply to any parent's children.

    ``def_matchers``/``ref_matchers`` map a *parent* rule name to the semantic matchers the
    symbol extractor tries against that rule's children (``def``/``ref`` are grammar-restricted
    to rule blocks, so there is no global variant). ``namespace_rules`` is the set of rule names
    whose nodes open a lexical scope.
    """

    node_paints: Mapping[str, tuple[NodePaint, ...]]
    child_matchers: Mapping[str, tuple[ChildMatcher, ...]]
    global_child_matchers: tuple[ChildMatcher, ...]
    def_matchers: Mapping[str, tuple[DefMatcher, ...]] = dataclasses.field(default_factory=dict)
    ref_matchers: Mapping[str, tuple[RefMatcher, ...]] = dataclasses.field(default_factory=dict)
    namespace_rules: frozenset[str] = frozenset()


def _local_anchor_matches(anchor: Anchor, rule_index: RuleIndex) -> list[tuple[Match, int]]:
    """Expand a local anchor into its ``(match, anchor_rank)`` readings.

    An unqualified identifier that is both a label and an invoked rule name resolves to the
    union of both readings (two matches), matching validation's union semantics.
    """
    if anchor.literal is not None:
        return [(ByLiteralText(anchor.literal), ANCHOR_RANK_LABEL_LITERAL)]
    name = anchor.name
    assert name is not None, "identifier anchor has no name"
    if anchor.qualifier == "label":
        return [(ByLabel(name), ANCHOR_RANK_LABEL_LITERAL)]
    if anchor.qualifier == "rule":
        return [(ByChildRule(name), ANCHOR_RANK_RULE_NAME)]
    out: list[tuple[Match, int]] = []
    if name in rule_index.labels:
        out.append((ByLabel(name), ANCHOR_RANK_LABEL_LITERAL))
    if name in rule_index.invoked_rules:
        out.append((ByChildRule(name), ANCHOR_RANK_RULE_NAME))
    return out


def _resolve_local_anchor(
    anchor: Anchor,
    paint: Paint,
    *,
    source_rank: int,
    stmt_index: int,
    rule_index: RuleIndex,
    out: list[ChildMatcher],
) -> None:
    """Emit the child matcher(s) for an anchor inside a ``rule X`` block."""
    for match, anchor_rank in _local_anchor_matches(anchor, rule_index):
        out.append(ChildMatcher(match, paint, Tier(source_rank, anchor_rank, BLOCK_RANK_RULE, stmt_index)))


def _resolve_global_anchor(
    anchor: Anchor,
    paint: Paint,
    *,
    stmt_index: int,
    index: GrammarIndex,
    node_paints: dict[str, list[NodePaint]],
    global_out: list[ChildMatcher],
) -> None:
    """Emit the node paint and/or global child matcher for an anchor in a global ``scope``.

    An unqualified identifier that is both a rule name and a label resolves to the union: a
    whole-node paint on the rule plus a global by-label child matcher.
    """
    source_rank = SOURCE_RANK_SCOPE  # global anchors only come from scope statements
    label_tier = Tier(source_rank, ANCHOR_RANK_LABEL_LITERAL, BLOCK_RANK_GLOBAL, stmt_index)
    rule_tier = Tier(source_rank, ANCHOR_RANK_RULE_NAME, BLOCK_RANK_GLOBAL, stmt_index)
    if anchor.literal is not None:
        global_out.append(ChildMatcher(ByLiteralText(anchor.literal), paint, label_tier))
        return
    name = anchor.name
    assert name is not None, "identifier anchor has no name"
    if anchor.qualifier == "label":
        global_out.append(ChildMatcher(ByLabel(name), paint, label_tier))
    elif anchor.qualifier == "rule":
        node_paints.setdefault(name, []).append(NodePaint(paint, rule_tier))
    else:
        if name in index.rule_names:
            node_paints.setdefault(name, []).append(NodePaint(paint, rule_tier))
        if name in index.all_labels:
            global_out.append(ChildMatcher(ByLabel(name), paint, label_tier))


def resolve_config(config: LspConfig, index: GrammarIndex) -> ResolvedLspConfig:
    """Resolve a validated ``LspConfig`` into the classifier's matcher tables.

    Assumes ``config`` already passed :func:`validate_config` against ``index``; membership
    checks here only pick the reading(s) of union-eligible anchors. ``def`` contributes both a
    declaration-site paint (when its kind's first segment is a legend token) and a semantic
    :class:`DefMatcher`; ``ref`` contributes a :class:`RefMatcher`; a namespace rule block adds
    its rule name to ``namespace_rules``.
    """
    node_paints: dict[str, list[NodePaint]] = {}
    child_matchers: dict[str, list[ChildMatcher]] = {}
    global_child_matchers: list[ChildMatcher] = []
    def_matchers: dict[str, list[DefMatcher]] = {}
    ref_matchers: dict[str, list[RefMatcher]] = {}
    namespace_rules: set[str] = set()

    for scope in config.global_scopes:
        paint = Paint(token=scope.token, modifiers=scope.modifiers)
        for anchor in scope.anchors:
            _resolve_global_anchor(
                anchor,
                paint,
                stmt_index=scope.index,
                index=index,
                node_paints=node_paints,
                global_out=global_child_matchers,
            )

    for block in config.rule_blocks:
        rule_index = index.rules.get(block.rule_name)
        if rule_index is None:
            continue  # unknown rule; validation already flagged it
        out = child_matchers.setdefault(block.rule_name, [])
        for scope in block.scopes:
            paint = Paint(token=scope.token, modifiers=scope.modifiers)
            for anchor in scope.anchors:
                _resolve_local_anchor(
                    anchor, paint, source_rank=SOURCE_RANK_SCOPE, stmt_index=scope.index, rule_index=rule_index, out=out
                )
        for def_stmt in block.defs:
            # One expansion of the anchor builds each match's tier once, then emits both the
            # declaration-site paint (when the kind's first segment is a legend token) and the
            # semantic DefMatcher from it, so the two share an identical precedence key.
            paint = (
                Paint(token=def_stmt.kind[0], modifiers=("declaration",))
                if def_stmt.kind and def_stmt.kind[0] in TOKEN_LEGEND
                else None
            )
            for match, anchor_rank in _local_anchor_matches(def_stmt.anchor, rule_index):
                tier = Tier(SOURCE_RANK_DEF, anchor_rank, BLOCK_RANK_RULE, def_stmt.index)
                if paint is not None:
                    out.append(ChildMatcher(match, paint, tier))
                def_matchers.setdefault(block.rule_name, []).append(DefMatcher(match, def_stmt.kind, tier))
        for ref_stmt in block.refs:
            for match, anchor_rank in _local_anchor_matches(ref_stmt.anchor, rule_index):
                tier = Tier(SOURCE_RANK_REF, anchor_rank, BLOCK_RANK_RULE, ref_stmt.index)
                ref_matchers.setdefault(block.rule_name, []).append(RefMatcher(match, ref_stmt.kinds, tier))
        if block.is_namespace:
            namespace_rules.add(block.rule_name)
        if not out:
            del child_matchers[block.rule_name]

    return ResolvedLspConfig(
        node_paints={name: tuple(paints) for name, paints in node_paints.items()},
        child_matchers={name: tuple(matchers) for name, matchers in child_matchers.items()},
        global_child_matchers=tuple(global_child_matchers),
        def_matchers={name: tuple(matchers) for name, matchers in def_matchers.items()},
        ref_matchers={name: tuple(matchers) for name, matchers in ref_matchers.items()},
        namespace_rules=frozenset(namespace_rules),
    )


def load_lsp_config(config_text: str, grammar: gsm.Grammar) -> ResolvedLspConfig:
    """Parse, transform, validate, and resolve ``.fltklsp`` text against ``grammar`` in one call.

    Empty or whitespace-only text short-circuits to an empty resolved config (the built-in
    defaults alone are a usable baseline). A parse failure or any validation offense raises
    :class:`LspConfigError`.
    """
    if not config_text.strip():
        return ResolvedLspConfig(node_paints={}, child_matchers={}, global_child_matchers=())

    terminals = terminalsrc.TerminalSource(config_text)
    parser = Parser(terminals)
    result = parser.apply__parse_lsp_spec(0)
    if not result or result.pos != len(terminals.terminals):
        error_msg = errors.format_error_message(
            parser.error_tracker,
            terminals,
            lambda rule_id: parser.rule_names[rule_id],
        )
        msg = f".fltklsp config parse failed:\n{error_msg}"
        raise LspConfigError(msg)

    config = lsp_cst_to_config(result.result, terminals)
    index = build_grammar_index(grammar)
    validate_config(config, index, terminals)
    return resolve_config(config, index)
