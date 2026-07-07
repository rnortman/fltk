# Implementation Log — step3 (M4: defs/refs/namespace semantics)

## Increment 1 — semantic-config tables + symbol extraction/resolution foundation

Through-line: the per-document symbol table and the resolved-config data it consumes —
the foundational data layer the LSP features and ref-site paint ride on in later increments.

- `lsp_config.py:473-492`: `match_applies(match, label_name, child_text, child_rule_name)`
  — the shared child-match predicate, moved here from `classify._matches` and re-keyed on
  the child rule *name* (was a `gsm.Rule`) so `symbols.py` and `classify.py` can both use it.
- `lsp_config.py:509`: `SOURCE_RANK_REF = 1` (== `SOURCE_RANK_DEF`).
- `lsp_config.py:544-564`: new `DefMatcher` (match/kind/tier) and `RefMatcher`
  (match/kinds/tier) frozen dataclasses.
- `lsp_config.py:567-596`: `ResolvedLspConfig` gains additive `def_matchers`,
  `ref_matchers` (both `Mapping[str, tuple[...]]`, keyed by parent rule name) and
  `namespace_rules: frozenset[str]`, all defaulted — empty-config short-circuit and every
  existing call site unaffected.
- `lsp_config.py:611-631`: `_resolve_local_anchor` refactored onto a new
  `_local_anchor_matches(anchor, rule_index) -> [(Match, anchor_rank)]` helper (behavior
  identical); `resolve_config` (`:695-745`) now also emits the three semantic tables —
  union-semantics anchors, `SOURCE_RANK_DEF`/`SOURCE_RANK_REF` tiers, namespace-rule
  accumulation across multiple blocks. Docstring updated (round-1 inertness claim removed).
- `classify.py`: `_GrammarTables` → public `GrammarTables`, `_rule_for_node` → public
  `rule_for_node` (§4.1 de-facto-usage ratification); `_matches` deleted, `_explicit_intervals`
  (`:236-250`) now calls `lsp_config.match_applies` with the child rule name. No behavior change.
- `symbols.py` (**new**, `fltk/lsp/symbols.py`): `Symbol`, `Reference`, `Scope`,
  `SymbolTable` (`symbol_at`/`reference_at` = smallest containing span; `occurrences` =
  name span + resolved refs, deduped by `(start,end)`), and `extract(tree, tables,
  resolved_config, text)` — one DFS walk opening namespace scopes, per-child highest-tier
  def/ref matching (def wins over ref on a child; §2.1 hoist realized by always appending
  def symbols to the current scope while recursing members into the inner scope), then an
  outward-scope resolution pass with dotted-prefix kind matching, shadowing, forward refs.
- `test_lsp_resolve.py`: `test_ref_and_namespace_are_inert` replaced by six tests covering
  the new tables (def/ref matcher kind+tier, wildcard, union anchor, namespace accumulation
  across blocks, no-semantic-statements → empty).
- `test_symbols.py` (**new**): 20 tests — symbol fields for label/rule/literal anchors,
  union→one symbol, repeated items, def-beats-ref, scope tree + namespace nesting, the §2.1
  hoist (name resolvable outside, self-ref, members stay inside), forward refs, shadowing,
  unresolved-None, duplicate-def document-order resolution, kind-prefix/wildcard/kind-list,
  `symbol_at`/`reference_at` innermost, `occurrences` dedupe over a single-child chain.

Surprise (recorded for later test authors): a bare `X*` repetition in `.fltkg` does not
admit inter-token whitespace; `( X , )*` does. Rules ending in a trailing `,` gobble their
own trailing whitespace, which is why the flat/mod fixture grammars nest cleanly under `stmt*`.

## Increment 2 — analysis-layer outputs: ref-site paint, engine wiring, feature translation

Through-line: the analysis-layer products the server's read/rename handlers consume in the
final increment — painted tokens that carry resolved-ref colors, `DocumentAnalysis` carrying
the symbol table, and the pure `SymbolTable → lsprotocol` feature-translation functions.
Engine-thread / pure logic only; no LSP protocol handlers yet.

- `classify.py:296-311`: new `_ref_intervals(symbol_table, out)` — each resolved reference
  whose `symbol.kind[0]` is in `TOKEN_LEGEND` contributes one explicit-layer interval
  `(ref.start, ref.end, Paint(token=symbol.kind[0], modifiers=()), (ref.depth, ref.tier))`.
  `classify` (`:361-403`) gains keyword-only `symbol_table: SymbolTable | None = None`,
  appended to the explicit-interval list before `_winner_segments`/`_merge_ranges` so ref
  paint participates in precedence and default suppression unchanged. `SymbolTable` is a
  TYPE_CHECKING-only import (symbols.py imports classify at runtime). The default-emission
  `TODO(lsp-classify-hotpath)` comment now notes extraction as the third O(tree) walk.
- `engine.py`: `DocumentAnalysis.symbols: symbols.SymbolTable | None = None` (additive keyword
  default). `analyze()` success path (`:150-171`) runs `symbols.extract(...)` (reusing
  `self._tables`/`self._resolved_config`) and threads the table into
  `classify(..., symbol_table=...)`, returning it on `DocumentAnalysis`; failure/recursion
  paths leave it `None` via the default. Extraction is inside the existing `RecursionError`
  guard. `symbols` imported top-level (no cycle: symbols does not import engine).
- `features.py:174-360`: `SYMBOL_KINDS` (13-entry first-segment→`SymbolKind` table),
  `_symbol_kind` (`Object` fallback), `_strictly_contains`; `document_symbols` (hierarchical,
  nesting by declaration-range containment via a stack over symbols sorted `(range_start,
  -range_end)`, equal ranges siblings); `document_symbols_flat`; `symbol_target` (def under
  cursor, else a reference's resolved symbol); `definition_location`; `reference_locations`
  (include_declaration flag); `document_highlights` (Write on decl, Read on refs);
  `prepare_rename`; `rename_occurrences`; `rename_edits` (versioned `documentChanges` when the
  client supports it, else plain `changes`). All pure `(SymbolTable, …) → lsprotocol`.
- `test_classify_painter.py`: 9 ref-paint tests (resolved ref inherits kind; `scope` beats ref
  at same node; deeper explicit beats shallower ref and vice versa via a nesting grammar;
  unresolved / out-of-legend fall through; `none` occludes ref paint; no-`symbol_table`
  regression pin; token-stream invariants with ref paint).
- `test_engine_analyze.py`: 3 tests (populated table + resolved ref on success; empty config →
  empty table; failure → `symbols` None). Existing `highlight()` regression pins unchanged.
- `test_features.py`: 15 tests over directly-built `SymbolTable`s (SYMBOL_KINDS incl. `Object`;
  hierarchical nesting incl. the name-anchor-after-members range-sort case + equal-range
  siblings; field/detail/kind/range/selection; flat fallback; definition on ref/def/nothing;
  references with/without declaration; highlight Write/Read; prepare-rename range vs None;
  rename occurrence sets; versioned-vs-plain edit rendering).

Deviation: `document_symbols` keeps each node's mutable children list in the stack (not the
node), so `DocumentSymbol.children` (typed `Sequence`) is never mutated post-construction —
satisfies pyright without a cast.

## Increment 3 — server protocol handlers + rename policy + end-to-end tests

Through-line: the LSP protocol surface (§4.6, §2.6) that exposes the increment-1/2 data
layer to editors — the six new handlers, the rename safety policy, client-capability
routing, and the pytest-lsp + dogfood end-to-end coverage. Final increment; the server was
the only stage left after engine+features.

- `server.py:26-27`: import `get_capability` and `JsonRpcException` from pygls.
- `server.py:35`: TYPE_CHECKING import of `symbols`. `_GoodAnalysis` gains non-optional
  `symbols: symbols.SymbolTable` (`:102`); `_store` success branch (`:225-241`) now also
  requires `analysis.symbols is not None` and populates it.
- `server.py:355-372`: `_hierarchical_symbols()` / `_document_changes()` read the two client
  capabilities off `self.client_capabilities` via `get_capability` (post-initialize values;
  reading per request equals caching them — no fragile `initialize` override).
- `server.py:376-421`: `rename_document()` implements §2.6 — requires a successful analysis
  of the *current* version (else raises `JsonRpcException` "…document has parse errors"),
  maps the position to an offset, `features.rename_occurrences`, no-op rename returns the
  empty edit, otherwise applies the edits in memory back-to-front (`_apply_edits`, `:425-433`)
  and reparses on the worker via `self._engine.analyze`; a failed reparse raises
  `JsonRpcException`. Returns versioned `documentChanges` or plain `changes` per capability
  through `features.rename_edits`.
- `server.py:589-664`: six handlers on the established `_ensure_analyzed`→`_serveable` pull
  pattern — `documentSymbol` (hierarchical vs flat per capability), `definition`,
  `references` (honoring `context.include_declaration`), `documentHighlight`, `prepareRename`
  (all read-only, current-or-last-good per ADR D6), and `rename`, registered with
  `RenameOptions(prepare_provider=True)`.
- `test_data/greet.fltkg`: extended with `definition`/`usage`/`module` items (module is a
  namespace-opening block) so the live fixture language exercises def/ref/namespace; existing
  greet/note syntax and all prior server tests unchanged and green.
- `test_data/greet.fltklsp`: added `def`/`ref`/`namespace` rule blocks for the new items
  (`definition`→`variable`, `usage`→`*`, `module`→`namespace` + `namespace;`).
- `test_server.py`: `_init_params` gains `hierarchical`/`document_changes` capability toggles;
  `_line_col` helper (codepoint offset → encoded `Position`); 11 new tests — hierarchical vs
  flat documentSymbol, definition-from-reference in utf-16 and utf-32 over astral text,
  references (±declaration) + highlight kinds, rename versioned `documentChanges` vs plain
  `changes`, rename on broken doc → error, rename to parse-breaking name → error, prepareRename
  keyword → null, navigation served from last-good after a breaking edit.
- `test_dogfood.py`: `test_dogfood_semantics_extract_and_resolve_over_real_grammar` — a
  test-local `.fltklsp` spec adds def/ref/namespace over the real `fltklsp.fltkg`
  (`rule_config` rule-name → namespace def, `anchor` name → ref); asserts a sample document's
  symbols extract and the anchor reference resolves. Committed `fltklsp.fltklsp` untouched.

Deviation: rename failures are signaled by raising `JsonRpcException` with a user-facing
message (LSP response error), the conventional way an editor surfaces a rename refusal; the
design says "fails with an error message" without prescribing the mechanism.
Deviation: client capabilities are read per request from `self.client_capabilities` rather
than captured into fields at `initialize` — same values (they are fixed for the session),
avoids overriding pygls's built-in `initialize` handler.
