# Design — Round 3: defs/refs semantics (M4) — symbol tables, navigation, rename, namespace scoping

Status: draft for review (pre-freeze).

Provenance: the advisory docs (`README.md`, `brainstorm.md`, `fltklsp-spec.md`) remain
directional only ("NO DECISIONS HAVE BEEN MADE"). Code at HEAD (76124f9) is authoritative;
`step3/exploration.md` records the code facts, re-verified by direct reads where this design
depends on them. The step1/step2 designs are implemented and authoritative over the
brainstorm, but per the requester anything in them that no longer makes sense can change;
§2 calls out every such change.

## 1. Round-3 scope: what and why

**Scope chosen: the ADR's M4 — activating the `.fltklsp` def/ref/namespace semantics** and
the LSP features they power:

- A per-document **symbol table**: symbols from `def` statements, references from `ref`
  statements, lexical scopes from `namespace`, and same-file reference resolution.
- **Ref-site paint**: a resolved reference inherits its defining kind's token type
  (`fltklsp-spec.md` §3), completing the highlighting story for identifiers.
- New LSP features over that table: `textDocument/documentSymbol`, `definition`,
  `references`, `documentHighlight`, `prepareRename`, and same-file `rename`.
- `fltk-highlight` gains ref-site coloring for free (it flows through the token stream).

Why this cut, and not the alternatives:

- **The foundation is already poured; only the semantics are missing.** The grammar parses
  `def`/`ref`/`namespace`; the config model stores them (`lsp_config.DefStmt`/`RefStmt`/
  `RuleBlock.is_namespace`, `lsp_config.py:88-109`); validation checks their anchors
  (`lsp_config.py:430-433`); `def` already paints declaration sites
  (`lsp_config.py:625-628`). `ref` and `namespace` are the only statements still inert past
  validation — pinned by `test_lsp_resolve.py` (`test_ref_and_namespace_are_inert`). The
  step2 design planned exactly this seam: "`DocumentAnalysis` grows a symbol table next to
  `tokens`" (`step2/design.md:559-562`). This round is the payoff of that layering.
- **M3 (prefix-CST) stays out, again — and deliberately behind M4 despite the ADR's
  ordering.** Its central factual question is *still* open: whether the packrat parser's
  internals can yield a useful partial CST on failure at all
  (`step3/exploration.md`, Open factual questions — determining it "would require reading
  the packrat/memo internals in more depth"). Designing M3 now would mean designing against
  an unverified assumption; it needs its own exploration round of
  `fltk/fegen/pyrt/memo.py` and the generated-parser method shape first. M4, by contrast,
  is fully grounded in code that exists, delivers the ADR's next unit of user-visible value
  (navigation — half the reason editor tooling exists), and touches nothing M3 will touch
  (M3 changes `analyze()`'s parse step; M4 adds a stage after it).
- **`.fltklsp` files gain function without changing.** The D1 commitment — phase-1 files
  stay valid verbatim when phase 2 lands — is honored by construction: this round adds
  semantics to statements that already parse and validate; no syntax changes, no
  revalidation changes that reject previously-valid files.

Explicitly out of round 3: prefix-CST exposure (M3, needs its own exploration first),
cross-file resolution and the resolver plugin API (M5), qualified-name resolution
(spec OQ1 — §2.4), completion, hover, workspace symbols, call hierarchy, semantic-token
deltas, diagnostics for unresolved references (§5), and any change to the parse path.

## 2. Deltas: corrections and decisions this round makes

### 2.1 Namespace scoping: the construct's own name is hoisted to the enclosing scope

`fltklsp-spec.md` §3 says of `namespace`: "symbols defined in its subtree are visible only
within it." Read literally, that breaks the spec's own worked example: clockwork's
`rule cog { def identifier: type.cog; namespace; }` would trap the cog's *name* inside the
cog's scope, so no reference elsewhere in the file could ever resolve to it — go-to-def on
a cog name would never work, defeating the point of defining it. Every mainstream language
scopes this the other way: a class's name lives in the enclosing scope; its *members* live
inside.

**Decision**: a symbol whose `def` is anchored in a rule that is a namespace rule is
defined into the scope **enclosing** that rule's namespace node (the construct's name is
visible where the construct is); symbols produced by other rules inside the subtree belong
to the namespace's own scope. Namespace-ness is a property of the *rule*, not of any one
block: a rule's blocks accumulate (`RuleBlock.is_namespace` is per-block,
`lsp_config.py:102-109`, and multiple blocks for one rule are legal — pinned by
`test_multiple_rule_blocks_accumulate`), so `rule cog { def identifier: type.cog; }` plus
a separate `rule cog { namespace; }` hoists exactly as the single-block spelling does; the
resolved `namespace_rules: frozenset[str]` (§4.1) deliberately erases block identity. Self-reference still works: resolution walks
outward from the inner scope and finds the hoisted name in the parent. This is a deliberate
deviation from the advisory spec's literal wording, in service of its evident intent.

### 2.2 Ref-site paint needs per-document resolution; `classify` gains a symbol-table input

The spec's "a resolved ref inherits the defining kind's token type" cannot be precomputed
at config-resolution time the way every existing paint is: which kind a reference resolves
to depends on the *document* (which defs exist, in which scopes). So the paint pipeline
grows one input: the engine builds the symbol table first, then passes it to `classify`,
which turns each *resolved* reference into an explicit-layer paint interval (§4.4). The
painter's precedence machinery (`Tier`, depth keys, `_winner_segments`) is reused
unchanged; "explicit `scope` always wins" holds because ref paint enters at
`SOURCE_RANK_REF = 1 < SOURCE_RANK_SCOPE = 2`, exactly parallel to def paint today.
`classify`'s existing signature keeps working (the new parameter defaults to `None` =
no ref paint), so round-1/2 callers and tests are untouched.

### 2.3 Round-1 inertness pins flip, deliberately

`resolve_config`'s docstring ("`ref` and `namespace` are inert in round 1",
`lsp_config.py:604-606`) and `test_lsp_resolve.py`'s `test_ref_and_namespace_are_inert`
pin behavior this round exists to replace. Both are updated: the docstring describes the
new outputs; the test is replaced by tests asserting the matchers/namespace sets are
produced. This is the planned activation the pin was guarding, not a compatibility break —
no `.fltklsp` file changes meaning except that its `ref`/`namespace` statements now do
what the spec always said they would.

### 2.4 Qualified names (spec OQ1) resolve as flat text this round — degrade, don't block

Clockwork's `ns::Type` / `a.b.c` references: a `ref` anchored on such a node compares its
whole span text (`ns::Type`) against symbol names and simply doesn't resolve — graceful
degradation, no error, defaults paint the span. A `qualified ref` language form
("resolve segment 1, then walk namespaces") is real design work entangled with the M5
resolver question (the spec itself asks whether it is "resolver-hook territory from day
one") and is deferred to the round that designs the resolver. Practical guidance recorded
for spec authors: if the grammar labels the segments, anchor the `ref` on the segment
label to get single-segment resolution now.

### 2.5 Two features beyond the ADR's M4 list: `documentHighlight` and `prepareRename`

The ADR lists document symbols, go-to-def, find-references, same-file rename. Two
adjacent features fall out of the same occurrence query at near-zero marginal cost and are
included: **documentHighlight** (cursor-on-symbol highlights all its occurrences — the
same `(symbol, occurrences)` set find-references computes) and **prepareRename** (the
standard guard that tells the editor *whether* the thing under the cursor is renamable and
what its exact range is, preventing rename attempts on keywords/punctuation). Both are
called-out scope additions, challengeable in review.

### 2.6 Rename safety: current-version analysis required, plus a verify-reparse guard

Rename is the one M4 feature that **edits the document**, so it gets a stricter policy
than the read-only features (which keep the current-or-last-good stale-serving of ADR D6):

- Rename refuses to run against a stale tree. If the current document version has no
  successful analysis, the request fails with an error message ("cannot rename while the
  document has parse errors") rather than computing edit offsets against text that is no
  longer on screen — stale offsets applied to current text is a corruption bug, not a
  degraded mode.
- Before returning edits, the server applies them to the current text in memory and
  reparses (same worker thread). If the result does not parse — e.g. the new name collides
  with a contextual keyword and derails the parse — the request fails with an explanatory
  error and no edits. This mirrors the formatting pipeline's verify-reparse guard
  (`server.py:373-417`) and its rationale. The reparse cannot catch a rename that still
  parses but *reparses differently* (the contextual-keyword hazard inherent to scannerless
  grammars); that residual risk is documented, and the next analysis pass immediately
  repaints, making any such shift visible.
- The returned edit is **versioned** against the client-side race the two policies above
  cannot see: the handler awaits the worker twice (analysis, then verify-reparse), and a
  `didChange` can be processed on the loop between those awaits — a plain
  `WorkspaceEdit.changes` payload carries no version, so the client would apply version-N
  offsets to version-N+1 text, exactly the corruption this section exists to prevent. When
  the client advertises `workspace.workspaceEdit.documentChanges` (captured at initialize),
  the server returns `documentChanges` with a `TextDocumentEdit` whose
  `OptionalVersionedTextDocumentIdentifier` carries the analyzed document version, so a
  conforming client refuses a stale edit. Clients without that capability get the plain
  `changes` fallback; for them alone the race is a residual risk LSP gives no way to close.

## 3. Deliverables and file layout

All changes inside the existing `fltk/lsp/` package plus its tests; no plumbing, fegen,
Rust, packaging, or Bazel changes. No generated artifacts change (the `.fltklsp` grammar
is untouched).

| File | Change |
|---|---|
| `fltk/lsp/symbols.py` | **New**: `Symbol`, `Reference`, `Scope`, `SymbolTable`, `extract()` — extraction walk, scope tree, resolution (§4.2–4.3) |
| `fltk/lsp/lsp_config.py` | `ResolvedLspConfig` gains `def_matchers`, `ref_matchers`, `namespace_rules` (+ `DefMatcher`/`RefMatcher`, `SOURCE_RANK_REF`); `resolve_config` emits them; the child-match predicate moves here next to the `Match` types (§4.1) |
| `fltk/lsp/classify.py` | `classify(..., symbol_table=None)`: resolved-ref paint intervals join the explicit layer (§4.4); `_GrammarTables`/`_rule_for_node` promoted to public `GrammarTables`/`rule_for_node` (§4.1) |
| `fltk/lsp/engine.py` | `DocumentAnalysis` gains `symbols: SymbolTable \| None = None`; `analyze()` builds the table and threads it into `classify` (§4.6) |
| `fltk/lsp/features.py` | `SYMBOL_KINDS` mapping; pure functions for document symbols (hierarchical + flat), definition, references, highlights, prepare-rename, rename occurrences (§4.5) |
| `fltk/lsp/server.py` | `_GoodAnalysis` gains `symbols`; six new feature handlers; rename policy (§4.6, §2.6) |
| `fltk/lsp/test_*.py`, `conftest.py`, `test_data/` | new tests + fixture extensions (§6) |

Everything added is new public surface (out-of-tree consumers may construct
`AnalysisEngine`s and read `DocumentAnalysis`); all changes to existing types are
additive fields with defaults — no renames, no annotation churn, per CLAUDE.md.

## 4. Proposed approach

### 4.1 Resolved-config extensions (`lsp_config.py`)

`resolve_config` currently folds `def` statements into paint-only `ChildMatcher`s and
drops `ref`/`namespace` (`lsp_config.py:599-636`). It now *additionally* emits the
semantic tables:

```python
@dataclasses.dataclass(frozen=True)
class DefMatcher:
    match: Match                      # ByLabel | ByLiteralText | ByChildRule, as today
    kind: tuple[str, ...]             # the def's dotted kind, verbatim
    tier: Tier                        # SOURCE_RANK_DEF; used to pick one winner per child

@dataclasses.dataclass(frozen=True)
class RefMatcher:
    match: Match
    kinds: tuple[tuple[str, ...], ...] | Literal["*"]
    tier: Tier                        # SOURCE_RANK_REF

SOURCE_RANK_REF = 1                   # == SOURCE_RANK_DEF; scope (2) beats both

@dataclasses.dataclass(frozen=True)
class ResolvedLspConfig:
    node_paints: ...                                   # unchanged
    child_matchers: ...                                # unchanged (incl. def-site paint)
    global_child_matchers: ...                         # unchanged
    def_matchers: Mapping[str, tuple[DefMatcher, ...]] = ...   # keyed by parent rule name
    ref_matchers: Mapping[str, tuple[RefMatcher, ...]] = ...
    namespace_rules: frozenset[str] = frozenset()
```

- `def`/`ref` are grammar-restricted to rule blocks, so both maps key on the block's rule
  name only — no global variants exist or need designing.
- Unqualified anchors keep union semantics: an anchor that is both a label and an invoked
  rule name yields two matchers *from the same statement* (same `stmt_index`, different
  `anchor_rank`), exactly as `_resolve_local_anchor` does today. Extraction dedupes per
  child by tier (§4.2), so the union never double-defines a symbol.
- Def-site *paint* resolution is unchanged — it stays in `child_matchers` with
  `SOURCE_RANK_DEF` and the `declaration` modifier, so highlighting of declaration sites
  is bit-identical to round 1/2.
- The new fields carry defaults, so the empty-config short-circuit
  (`load_lsp_config`, `lsp_config.py:646-647`) and every existing constructor call site
  keep working unmodified.
- The child-match predicate (`classify._matches`, `classify.py:229-245`) moves to
  `lsp_config` beside the `Match` types (as `match_applies(match, label_name, child_text,
  child_rule_name)`, taking the rule *name* instead of a `gsm.Rule`), because
  `symbols.py` and `classify.py` now both need it and neither should reach into the
  other's privates. `classify` calls the moved function; behavior is unchanged.
- The same rule applies to the grammar tables the extraction walk needs:
  `classify._GrammarTables` and `_rule_for_node` (`classify.py:63-68, 162-173`) are
  promoted to public names `GrammarTables` / `rule_for_node` in `classify.py`.
  `build_grammar_tables` already hands `_GrammarTables` across the module boundary to
  `engine.py` (`engine.py:86`), so the promotion ratifies de-facto usage rather than
  widening it; `symbols.extract`'s `tables` parameter is that `GrammarTables`, and
  extraction uses `rule_for_node` for kind→rule resolution (rule name for matcher lookup,
  node-child rule names for `match_applies`, `is_trivia_rule` for the trivia skip).
  Pure rename of private to public; no behavior change; the eventual
  `TODO(lsp-rule-surface-index)` unification absorbs this surface later.

### 4.2 Symbol model and extraction (`symbols.py`)

```python
@dataclasses.dataclass(frozen=True)
class Symbol:
    name: str                        # span text of the matched anchor child
    kind: tuple[str, ...]            # the def's dotted kind
    name_start: int                  # selection range: the anchor child's span
    name_end: int
    range_start: int                 # declaration range: the producing rule node's span
    range_end: int

@dataclasses.dataclass(frozen=True)
class Reference:
    name: str                        # span text of the matched anchor child
    start: int
    end: int
    depth: int                       # CST depth of the matched child (painter precedence)
    kinds: tuple[tuple[str, ...], ...] | Literal["*"]
    tier: lsp_config.Tier            # the winning RefMatcher's tier (painter precedence)
    symbol: Symbol | None            # resolution result; None = unresolved

@dataclasses.dataclass
class Scope:                         # built mutably, treated as read-only after extract()
    start: int
    end: int
    parent: Scope | None
    children: list[Scope]
    symbols: list[Symbol]            # document order

@dataclasses.dataclass(frozen=True)
class SymbolTable:
    root: Scope                      # spans [0, len(text)); namespace scopes nest inside
    symbols: tuple[Symbol, ...]      # all symbols, document order (by name_start)
    references: tuple[Reference, ...]  # all references, document order

    def symbol_at(self, offset: int) -> Symbol | None: ...       # innermost def-name span
    def reference_at(self, offset: int) -> Reference | None: ... # innermost ref span
    def occurrences(self, symbol: Symbol) -> list[tuple[int, int]]: ...

def extract(tree, tables, resolved_config, text) -> SymbolTable
```

`extract` is one depth-first walk of the analysis tree (the same structural walk shape as
`classify._explicit_intervals`), doing three things per node:

1. **Scope opening.** If the node's rule name is in `namespace_rules`, open a scope for
   its span nested in the current scope.
2. **Def matching.** For each child, try the parent rule's `def_matchers` (via
   `match_applies`, same child-shape handling as the painter: span children match by
   label/literal text, node children by label/child-rule). If any match, exactly **one**
   symbol is created from the highest-`tier` matcher (this collapses both the
   union-semantics duplicate from one statement and genuine multi-statement collisions;
   later statements win ties via `stmt_index`, consistent with the painter). The symbol's
   `name` is the child's span text; `name_start/end` its span; `range_start/end` the
   *parent node's* span (the producing rule — drives outline nesting and "declaration
   range", per spec §3). The symbol is appended to the **current scope**, except for the
   §2.1 hoist: when the parent node's own rule is a namespace rule, the symbol goes to the
   scope *enclosing* that node's scope.
3. **Ref matching.** For each child **not** already matched by a def (a def'd occurrence
   is a declaration, not additionally a reference — `include_declaration` handles its
   membership in find-references), try `ref_matchers` the same way; the highest-tier match
   creates one `Reference` with the child's span text, span, depth, kinds, and tier.

**Resolution** runs after the walk, per reference: find the innermost scope containing the
reference's span (descend the scope tree), then walk outward; in each scope, scan symbols
in document order for the first whose `name` equals the reference's text and whose `kind`
is matched by the reference's kinds (`*` matches everything; otherwise a ref kind `K`
matches symbol kind `S` iff `S[:len(K)] == K` — dotted-prefix on segment boundaries, per
spec §3). First match wins and stops the outward walk (inner shadows outer). Visibility is
whole-scope — forward references resolve, matching how declaration-order-free DSLs behave;
duplicate same-name defs in one scope both exist as symbols, and references resolve to the
document-order-first one (whether duplicates are an *error* is the DSL's own semantic
concern, not the generic tooling's).

Notes on deliberate simplicity:

- A `def "literal": kind;` (literal anchor) is legal today and stays legal: every
  occurrence defines a symbol named by that literal's text. Odd but harmless; not worth a
  new validation rule.
- Multiple children of one node matching the same def (a repeated labeled item) each
  define their own symbol — the natural reading.
- The walk does not descend into trivia nodes (same rule as the default classifier,
  `classify.py:183-188`) — defs/refs inside comments don't exist.

### 4.3 Scope tree details

- The root scope is `(0, len(text))` — not the root node's span — so offsets in leading or
  trailing trivia still land in a scope.
- Sibling namespace nodes are CST siblings, hence non-overlapping; nested namespace nodes
  nest by walk order. Identical-span parent/child namespace chains (rule `A := b` where
  both are namespace rules) nest inner-inside-outer by walk order; resolution semantics
  are unaffected because the outward walk visits both.
- `symbol_at`/`reference_at` pick the **smallest** containing span when spans nest (a def
  anchored on a node child can contain another def's name deeper in the subtree); lookups
  are bisect-over-sorted-starts with a containment check.
- `occurrences(symbol)` = the symbol's name span plus the span of every reference whose
  `symbol` is that symbol, **deduplicated by `(start, end)`** — a node-anchored ref and a
  span-anchored ref can name the identical text range through a single-child chain, and
  rename must not emit two overlapping edits for one range.

### 4.4 Ref-site paint (`classify.py`)

`classify` gains a keyword-only `symbol_table: SymbolTable | None = None`. When provided,
each reference with `symbol is not None` and `symbol.kind[0] in TOKEN_LEGEND` contributes
one explicit-layer interval:

```
(ref.start, ref.end, Paint(token=symbol.kind[0], modifiers=()), (ref.depth, ref.tier))
```

appended to the same `_Interval` list `_explicit_intervals` fills, before
`_winner_segments` runs. Consequences, all falling out of the existing machinery:

- Explicit `scope` on the same element wins (`SOURCE_RANK_SCOPE=2 > SOURCE_RANK_REF=1`) —
  the spec's "explicit `scope` always wins".
- An explicit paint on a *descendant* still beats ref paint via `depth`, and vice versa —
  same two-clause reading as def paint (`step1/design.md` §4.6).
- Ref paint suppresses defaults over its span (it participates in `covered`).
- A resolved ref whose kind's first segment is not in the legend (open vocabulary) gets no
  paint; unresolved refs get no paint; both fall through to defaults. No new failure mode.

The `Reference` carries `depth` and `tier` precisely so `classify` never re-matches or
re-walks for refs — extraction is the single owner of def/ref matching. This adds a third
tree walk per analysis (symbols, explicit paints, defaults); the existing
`TODO(lsp-classify-hotpath)` entry is extended to note the third walk as part of the same
planned unification, not a new TODO.

### 4.5 Feature translation (`features.py`)

All new functions are pure `(SymbolTable, LineIndex, PositionEncoding, ...)` → lsprotocol
values, in the established style.

**`SYMBOL_KINDS: Mapping[str, lsp.SymbolKind]`** — the fixed first-segment table (spec §3),
pinned by test: `type`→Class, `function`→Function, `variable`→Variable,
`constant`→Constant, `field`→Field, `enumMember`→EnumMember, `namespace`→Namespace,
`property`→Property, `enum`→Enum, `struct`→Struct, `interface`→Interface,
`module`→Module, `method`→Method; any other first segment → `Object` (still an exact-match
ref target — the kind vocabulary stays open, only its LSP rendering has a fallback).
Extending the table later is additive.

**`document_symbols(table, line_index, enc) -> list[lsp.DocumentSymbol]`** — hierarchical.
`name` = symbol name, `detail` = the dotted kind joined with `.` (e.g. `type.cog`),
`kind` via `SYMBOL_KINDS`, `range` = declaration range, `selection_range` = name span
(contained in `range` by construction — the anchor child is a child of the producing
node). Nesting is by **declaration-range containment** computed with a stack over symbols
sorted by `(range_start, -range_end)`. That sort — not `SymbolTable.symbols`' name-start
order — is what makes the stack correct: declaration ranges are CST node spans, hence
properly nesting (laminar), but a def anchored on a *trailing* name child (e.g.
`outer := "{" , member* , "}" , "as" , name:ident`) gives the container a later
`name_start` than its members, and a name-start-ordered stack would emit those members as
siblings instead of children. Children render in the range order, which is document order
of the declarations. Nesting is independent of namespace scoping, so a `schema_field`
nests under its `schema` whether or not `schema_field` rules are namespaces. Equal ranges
are siblings (strict containment nests).

**`document_symbols_flat(table, uri, ...) -> list[lsp.SymbolInformation]`** — the fallback
for clients without `hierarchicalDocumentSymbolSupport`; the server picks per the client
capability at initialize.

**`symbol_target(table, offset) -> Symbol | None`** — the shared occurrence-query head:
the symbol whose name span contains `offset`, else the resolved symbol of the reference
containing `offset`, else `None`. Everything below builds on it plus
`table.occurrences(...)`:

- **`definition_location(table, offset, uri, ...) -> lsp.Location | None`** — the target
  symbol's name span (go-to-def on the definition itself returns itself, the conventional
  editor behavior); `None` for unresolved refs and non-symbol positions.
- **`reference_locations(table, offset, uri, ..., include_declaration) -> list[lsp.Location] | None`**
  — the occurrence set, with the name span included per the flag.
- **`document_highlights(table, offset, ...) -> list[lsp.DocumentHighlight] | None`** —
  the same set; the declaration gets `DocumentHighlightKind.Write`, references
  `DocumentHighlightKind.Read` (the common convention).
- **`prepare_rename(table, offset, ...) -> lsp.Range | None`** — the exact span under the
  cursor (name span or ref span) when a target exists, else `None` (editor shows "cannot
  rename this element").
- **`rename_occurrences(table, offset) -> tuple[Symbol, list[tuple[int, int]]] | None`** —
  the raw codepoint occurrence set. The server (not features.py) turns it into a
  `WorkspaceEdit` after the verify-reparse guard, because the guard needs the raw offsets
  to apply edits in memory (§2.6; that in-memory application goes back-to-front so earlier
  offsets stay valid); a small `rename_edits(...)` helper renders the final
  `WorkspaceEdit` (one `TextEdit` per occurrence — non-overlapping after the §4.3 dedupe,
  as LSP requires — packaged as versioned `documentChanges` or plain `changes` per the
  client capability, §2.6). Every occurrence's
  text equals the old name by construction (resolution matches by exact span text), so the
  edits are textually well-formed.

### 4.6 Engine and server wiring

**Engine** (`engine.py`): `DocumentAnalysis` gains `symbols: symbols.SymbolTable | None =
None` (keyword default — additive; existing constructor call sites and out-of-tree readers
unaffected). `analyze()` on the success path runs `symbols.extract(...)` (reusing
`self._tables` and `self._resolved_config`) and passes the table to `classify(...,
symbol_table=table)`; on failure `symbols` is `None` like `tree`/`tokens`. The
`RecursionError` catch already wraps the whole success path and now also covers
extraction. `highlight()` is untouched.

**Server** (`server.py`):

- `_GoodAnalysis` gains `symbols: SymbolTable` (populated only on success, so
  non-optional there); `_store`'s success branch requires it like `tree`/`tokens`.
- Six new handlers, all the established pull pattern (`_ensure_analyzed` →
  `_serveable`): `textDocument/documentSymbol` (hierarchical vs flat per the client
  capability captured at initialize), `definition`, `references`, `documentHighlight`,
  `prepareRename`, `rename`. Read-only features serve current-or-last-good per ADR D6 —
  a slightly stale outline or navigation target is the same accepted tradeoff as stale
  tokens.
- **Rename** applies §2.6: it uses `state.analysis` for the *current* version only —
  if that analysis is missing or errored, the request fails with a message; otherwise
  `rename_occurrences` + in-memory edit application + reparse (via `engine.analyze`
  on the worker thread — one extra classification pass on an explicit user action is
  acceptable) + `WorkspaceEdit` on success, versioned to the analyzed document version
  via `documentChanges` when the client's `workspace.workspaceEdit.documentChanges`
  capability (captured at initialize, alongside the hierarchical-symbol capability) allows
  it (§2.6). A no-op rename (new name == old name) returns an empty edit.
- Capabilities: pygls derives the document-symbol/definition/references/document-highlight
  provider capabilities from the decorated handlers; the rename feature is registered with
  `lsp.RenameOptions(prepare_provider=True)` so clients route through `prepareRename`.

## 5. Edge cases and failure modes

- **Unresolved references** — silent: no paint, no diagnostic, `definition` returns
  `None`. With cross-file resolution absent until M5, unresolved is the *normal* state for
  imported names; diagnosing it would be sustained false-positive noise. Recorded as a
  deliberate decision; M5's resolver is the layer that could upgrade this.
- **Reference resolving through a namespace's own name** (self-reference, recursion) —
  works via the §2.1 hoist: the name lives in the enclosing scope, which the outward walk
  reaches.
- **Same child matched by both a def and a ref matcher** — def wins; the child is a
  declaration only (§4.2). Documented, tested.
- **Duplicate same-name defs in one scope** — both appear in the outline; refs resolve to
  the document-order-first (§4.2). Not an error at this layer.
- **Overlapping occurrence spans** (node-anchored ref over the same text as a
  span-anchored ref through a single-child chain) — deduped in `occurrences`, so rename
  never emits overlapping edits (§4.3).
- **Rename to a contextual keyword or otherwise parse-breaking name** — caught by the
  verify-reparse guard, request fails with a message, document untouched (§2.6). A rename
  that parses but *re-means* (scannerless-grammar hazard) is beyond the guard; documented
  residual risk, immediately visible via repaint.
- **Rename on a stale analysis** — refused (§2.6); read-only features keep stale-serving.
- **Rename racing a keystroke** (a `didChange` lands between the handler's worker awaits) —
  the versioned `documentChanges` payload lets a conforming client refuse the stale edit
  (§2.6); only capability-less clients retain the race, via the `changes` fallback.
- **Multi-line symbol names** — theoretically possible via node-anchored defs; nothing
  breaks (spans are spans), and `prepare_rename` returning the exact range keeps the
  editor honest.
- **Defs/refs inside trivia** — cannot occur (extraction skips trivia subtrees, §4.2).
- **Empty document / no defs** — empty table; every feature returns its empty value.
- **Kind not in legend** (`variable.channel` paints; `widget.thing` doesn't) — paint-only
  effect; symbol/navigation semantics are identical either way. Already the def-paint rule
  today; now symmetric for refs.
- **Performance** — extraction is one additional O(tree) walk plus O(refs × scope-depth ×
  scope-size) resolution; fine at the scale the debounced server operates. Folded into the
  existing `TODO(lsp-classify-hotpath)` unification plan (§4.4).

## 6. Test plan (TDD; colocated in `fltk/lsp/`)

- **`test_symbols.py`** (new) — extraction and resolution against purpose-built
  mini-grammars: symbol fields (name/selection/declaration ranges) for label-, literal-,
  and rule-anchored defs; union-semantics anchors produce one symbol; highest-tier def
  wins per child; def-beats-ref on one child; repeated labeled items define one symbol
  each; scope tree shape (root spans whole text, namespaces nest); the §2.1 hoist
  (construct name resolvable from outside; self-reference resolves; member symbols stay
  inside); shadowing (inner def wins over outer); forward references; kind-prefix matching
  (`type` sees `type.cog`; `type.cog` doesn't see `type`), wildcard, kind-list "any of";
  duplicate-def resolution order; unresolved stays `None`; `symbol_at`/`reference_at`
  innermost selection; `occurrences` dedupe.
- **`test_lsp_resolve.py`** — `test_ref_and_namespace_are_inert` replaced by assertions
  that `def_matchers`/`ref_matchers`/`namespace_rules` are populated correctly (tiers,
  union duplication, namespace flag accumulation across multiple blocks for one rule);
  existing paint-resolution tests unchanged and green.
- **`test_classify_painter.py`** additions — resolved ref paints with the defining kind's
  token; explicit `scope` beats ref paint at the same node; deeper explicit paint beats
  shallower ref paint and vice versa; unresolved / out-of-legend-kind refs fall through to
  defaults; `none` occludes ref paint; token-stream invariants hold with ref paint in
  play; `classify` without `symbol_table` is byte-identical to round-2 output (regression
  pin).
- **`test_features.py`** additions — `SYMBOL_KINDS` table pinned (incl. Object fallback);
  hierarchical `document_symbols` nesting by containment, **including a
  name-anchor-after-members grammar shape** (container `name_start` later than its
  members' — the §4.5 range-sort case), equal-range siblings,
  detail/kind/range/selection fields; flat fallback shape; definition on a ref, on the def
  itself, on nothing; references with/without declaration; highlight kinds (Write on the
  def, Read on refs); prepare-rename range vs `None`; rename occurrence sets and edit
  rendering.
- **`test_engine_analyze.py`** additions — `analyze()` carries a populated `SymbolTable`
  on success and `None` on failure; `highlight()` regression pin still byte-identical.
- **`test_server.py`** additions (pytest-lsp, fixture language extended with
  defs/refs/namespace) — documentSymbol (hierarchical and, with a
  no-hierarchy-capability client, flat); definition/references/documentHighlight round
  trips in both utf-16 and utf-32 encodings on astral-bearing text; rename: successful
  round trip whose applied edits reparse, returned as versioned `documentChanges` when the
  client advertises `workspace.workspaceEdit.documentChanges` and as plain `changes`
  otherwise; rename on a broken document → error, no edits;
  rename to a parse-breaking name → error, no edits (verify-reparse); prepareRename on a
  keyword → null; read-only features served from last-good after a breaking edit.
- **`test_dogfood.py`** — end-to-end semantics over the real `fltklsp.fltkg` grammar. The
  committed `fltklsp.fltklsp` contains only `scope` statements (no def/ref/namespace) and
  stays untouched — what a good symbol vocabulary for the `.fltklsp` language itself looks
  like (e.g. whether repeated `rule X {}` blocks should each "define" X) is its own design
  decision, not a test-time improvisation on a public example file. The test instead loads
  a purpose-built test-local spec adding `def`/`ref`/`namespace` statements against
  `fltklsp.fltkg` and asserts a sample `.fltklsp` document's symbols extract and a
  reference resolves.
- Existing suites stay green: `uv run pytest`, `uv run ruff check . && uv run pyright`.

## 7. How round 3 lays the roadmap foundation

- **M5 resolver plugin**: the resolver's job becomes precisely "given this file's
  `SymbolTable` (its unresolved references and its exported symbols) and other files,
  produce cross-file resolutions" — this round defines the data model that API will
  consume. Unresolved references being silent first-class values (not errors) is exactly
  the seam a resolver later fills.
- **M3 prefix-CST**: untouched and unblocked; when a partial tree exists, `extract` and
  `classify` already operate on any subtree. M3's prerequisite exploration
  (packrat/memo internals) is the recorded next step for that milestone.
- **Qualified names (spec OQ1)**: deferred to the resolver round with a concrete
  degradation story and author guidance (§2.4).
- **Workspace symbols / call hierarchy / completion**: all future consumers of the same
  `SymbolTable`; nothing here needs reshaping for them.

## 8. Open questions

None requiring user judgment. The judgment calls were decided with recorded rationale for
review to challenge: the namespace hoist (§2.1), flat-text qualified-name degradation
(§2.4), the two added features (§2.5), the rename safety policy (§2.6), silent unresolved
references (§5), and first-in-document-order duplicate resolution (§4.2).
