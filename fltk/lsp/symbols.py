"""Per-document symbol table: definitions, references, lexical scopes, and resolution.

:func:`extract` walks an analysis-grammar CST once, turning ``def``-matched children into
:class:`Symbol` declarations, ``ref``-matched children into :class:`Reference` occurrences,
and namespace-rule nodes into nested lexical :class:`Scope`\\ s, then resolves each reference
to a symbol by walking outward from its innermost scope. The result is a :class:`SymbolTable`
the classifier (ref-site paint) and the LSP feature layer both consume.
"""

from __future__ import annotations

import dataclasses
import typing

from fltk.lsp import classify, lsp_config


@dataclasses.dataclass(frozen=True)
class Symbol:
    """A definition site produced by a ``def`` statement.

    ``name`` is the matched anchor child's span text; ``name_start``/``name_end`` its span
    (the LSP selection range). ``range_start``/``range_end`` are the *producing* rule node's
    span (the declaration range that drives outline nesting).
    """

    name: str
    kind: tuple[str, ...]
    name_start: int
    name_end: int
    range_start: int
    range_end: int


@dataclasses.dataclass(frozen=True)
class Reference:
    """A reference site produced by a ``ref`` statement, with its resolution result.

    ``depth`` and ``tier`` reproduce the painter precedence key so ref-site paint never has to
    re-match. ``symbol`` is the resolved definition, or ``None`` when nothing resolves.
    """

    name: str
    start: int
    end: int
    depth: int
    kinds: tuple[tuple[str, ...], ...] | typing.Literal["*"]
    tier: lsp_config.Tier
    symbol: Symbol | None


@dataclasses.dataclass
class Scope:
    """A lexical scope. Built mutably during extraction, treated as read-only afterward."""

    start: int
    end: int
    parent: Scope | None
    children: list[Scope]
    symbols: list[Symbol]


@dataclasses.dataclass(frozen=True)
class SymbolTable:
    """Every symbol, reference, and scope extracted from one document."""

    root: Scope
    symbols: tuple[Symbol, ...]
    references: tuple[Reference, ...]

    def symbol_at(self, offset: int) -> Symbol | None:
        """The definition whose name span most tightly contains ``offset``, else ``None``."""
        return _smallest_containing(
            ((s.name_start, s.name_end, s) for s in self.symbols),
            offset,
        )

    def reference_at(self, offset: int) -> Reference | None:
        """The reference whose span most tightly contains ``offset``, else ``None``."""
        return _smallest_containing(
            ((r.start, r.end, r) for r in self.references),
            offset,
        )

    def occurrences(self, symbol: Symbol) -> list[tuple[int, int]]:
        """The symbol's name span plus every resolved reference to it, deduped and sorted.

        A node-anchored ref and a span-anchored ref can name the identical range through a
        single-child chain; deduping by ``(start, end)`` keeps rename edits non-overlapping.
        """
        seen = {(symbol.name_start, symbol.name_end)}
        result = [(symbol.name_start, symbol.name_end)]
        for ref in self.references:
            if ref.symbol == symbol:
                key = (ref.start, ref.end)
                if key not in seen:
                    seen.add(key)
                    result.append(key)
        result.sort()
        return result


_T = typing.TypeVar("_T")


def _smallest_containing(candidates: typing.Iterable[tuple[int, int, _T]], offset: int) -> _T | None:
    """The value whose ``[start, end]`` span contains ``offset`` with the smallest width."""
    best: tuple[int, _T] | None = None
    for start, end, value in candidates:
        if start <= offset <= end:
            width = end - start
            if best is None or width < best[0]:
                best = (width, value)
    return best[1] if best is not None else None


@dataclasses.dataclass
class _PendingRef:
    """A reference collected during the walk, awaiting outward-scope resolution."""

    name: str
    start: int
    end: int
    depth: int
    kinds: tuple[tuple[str, ...], ...] | typing.Literal["*"]
    tier: lsp_config.Tier
    scope: Scope


def extract(
    tree: typing.Any,
    tables: classify.GrammarTables,
    resolved_config: lsp_config.ResolvedLspConfig,
    text: str,
) -> SymbolTable:
    """Build the :class:`SymbolTable` for ``tree`` under ``resolved_config``.

    One depth-first walk opens namespace scopes, creates symbols and references from matched
    children, then a resolution pass links each reference to a symbol.
    """
    root = Scope(start=0, end=len(text), parent=None, children=[], symbols=[])
    pending: list[_PendingRef] = []
    _walk(tree, 0, scope=root, tables=tables, resolved=resolved_config, text=text, pending=pending)

    # Order every scope's symbols by name position so resolution scans document order.
    _sort_scope_symbols(root)

    references = tuple(
        sorted(
            (
                Reference(
                    name=p.name,
                    start=p.start,
                    end=p.end,
                    depth=p.depth,
                    kinds=p.kinds,
                    tier=p.tier,
                    symbol=_resolve(p),
                )
                for p in pending
            ),
            key=lambda r: (r.start, r.end),
        )
    )

    all_symbols: list[Symbol] = []
    _gather_symbols(root, all_symbols)
    all_symbols.sort(key=lambda s: (s.name_start, s.name_end))

    return SymbolTable(root=root, symbols=tuple(all_symbols), references=references)


def _walk(
    node: typing.Any,
    depth: int,
    *,
    scope: Scope,
    tables: classify.GrammarTables,
    resolved: lsp_config.ResolvedLspConfig,
    text: str,
    pending: list[_PendingRef],
) -> None:
    """Collect symbols, references, and scopes over ``node`` and its subtree, depth-first.

    Symbols defined by ``node`` always append to ``scope`` (the current scope): a def anchored
    in a namespace rule thereby hoists to the scope enclosing that node's own namespace scope,
    while a def in an ordinary rule lands in the current scope -- both are ``scope``. Node
    children recurse into the inner scope when ``node`` is a namespace node, so members defined
    deeper belong to the namespace's own scope.
    """
    rule = classify.rule_for_node(node, tables)
    if rule.is_trivia_rule:
        return  # defs/refs inside comments do not exist

    if rule.name in resolved.namespace_rules:
        child_scope = Scope(start=node.span.start, end=node.span.end, parent=scope, children=[], symbols=[])
        scope.children.append(child_scope)
    else:
        child_scope = scope

    def_matchers = resolved.def_matchers.get(rule.name, ())
    ref_matchers = resolved.ref_matchers.get(rule.name, ())
    child_depth = depth + 1

    for label, child in node.children:
        is_span, cstart, cend, child_text, child_rule_name, label_name = classify.child_surface(
            label, child, text, tables
        )

        def_match = _best_match(def_matchers, label_name, child_text, child_rule_name)
        if def_match is not None:
            scope.symbols.append(
                Symbol(
                    name=text[cstart:cend],
                    kind=def_match.kind,
                    name_start=cstart,
                    name_end=cend,
                    range_start=node.span.start,
                    range_end=node.span.end,
                )
            )
        else:
            ref_match = _best_match(ref_matchers, label_name, child_text, child_rule_name)
            if ref_match is not None:
                pending.append(
                    _PendingRef(
                        name=text[cstart:cend],
                        start=cstart,
                        end=cend,
                        depth=child_depth,
                        kinds=ref_match.kinds,
                        tier=ref_match.tier,
                        scope=child_scope,
                    )
                )

        if not is_span:
            _walk(child, child_depth, scope=child_scope, tables=tables, resolved=resolved, text=text, pending=pending)


_M = typing.TypeVar("_M", lsp_config.DefMatcher, lsp_config.RefMatcher)


def _best_match(
    matchers: typing.Sequence[_M],
    label_name: str | None,
    child_text: str | None,
    child_rule_name: str | None,
) -> _M | None:
    """The highest-``tier`` matcher applying to a child, or ``None``.

    Collapses union-semantics duplicates from one statement and genuine multi-statement
    collisions into one winner; later statements win ties via ``stmt_index``.
    """
    best: _M | None = None
    for matcher in matchers:
        if lsp_config.match_applies(matcher.match, label_name, child_text, child_rule_name):
            if best is None or matcher.tier > best.tier:
                best = matcher
    return best


def _resolve(ref: _PendingRef) -> Symbol | None:
    """Resolve a reference by scanning its scope and each enclosing scope outward.

    In each scope, the first document-order symbol whose name matches and whose kind is
    matched by the reference's kinds wins and stops the outward walk (inner shadows outer).
    """
    scope: Scope | None = ref.scope
    while scope is not None:
        for symbol in scope.symbols:
            if symbol.name == ref.name and _kind_matches(ref.kinds, symbol.kind):
                return symbol
        scope = scope.parent
    return None


def _kind_matches(
    ref_kinds: tuple[tuple[str, ...], ...] | typing.Literal["*"],
    symbol_kind: tuple[str, ...],
) -> bool:
    """Whether a reference's kinds accept ``symbol_kind`` (dotted-prefix on segment boundaries)."""
    if ref_kinds == "*":
        return True
    return any(symbol_kind[: len(k)] == k for k in ref_kinds)


def _sort_scope_symbols(scope: Scope) -> None:
    scope.symbols.sort(key=lambda s: (s.name_start, s.name_end))
    for child in scope.children:
        _sort_scope_symbols(child)


def _gather_symbols(scope: Scope, out: list[Symbol]) -> None:
    out.extend(scope.symbols)
    for child in scope.children:
        _gather_symbols(child, out)
