# Deep efficiency review — fltklsp round 1 (classify + resolve + plumbing)

Commit reviewed: HEAD 0b001f2 (base debdeb6). Files in scope: `fltk/lsp/classify.py`,
`fltk/lsp/lsp_config.py` (resolve/load additions), `fltk/plumbing.py` (lsp wrappers).

Context note: `AnalysisEngine` (§4.7) is intentionally unbuilt this round. Findings 1 and 2
are about the `classify`/`default_tokens` seam the engine will call on the per-highlight hot
path, so they matter now: the current signatures force the wasteful pattern on whoever wires
up the engine.

---

## efficiency-1 — `classify`/`default_tokens` rebuild the whole grammar table (recompiling every regex) on every call

`fltk/lsp/classify.py:369` (`classify`) and `:208` (`default_tokens`) both open with
`tables = build_grammar_tables(grammar)`. `build_grammar_tables` (`:99`) walks every rule and
every item, and `_build_terminal_table` (`:71`) calls `re.compile(item.term.value)` for every
`Regex` item in the grammar (`:83`). Nothing here depends on `tree` or `text` — the tables are
a pure function of the (fixed) grammar.

Consequence: `classify` is the text→tokens hot path (per highlight request / per keystroke in
the M2 server the design explicitly builds this seam for, §4.7). Every call re-walks the entire
grammar and recompiles every terminal regex from scratch. Cost scales with grammar size × edit
frequency; for a large target grammar this is the dominant per-request cost and it is 100%
redundant across calls on the same grammar.

Fix: precompute `_GrammarTables` once per grammar and thread it through. Either add a
`tables`/cache parameter to `classify`/`default_tokens`, or memoize `build_grammar_tables` on
grammar identity. When `AnalysisEngine` is written it should build the tables once alongside the
parser (same lifetime as "grammar → parser once") and pass them into each `classify` call — the
current signature (grammar in, rebuild inside) quietly defeats that.

---

## efficiency-2 — `_winner_segments` is O(intervals²), not the O(matches log matches) the design claims

`fltk/lsp/classify.py:280` `_winner_segments`: for each adjacent boundary pair (up to `2n`
segments) it re-scans **all** `n` intervals to find the max-key cover (`:291-296`). That is
O(n²) in the number of explicit paint intervals. Design §6 ("Pathological config sizes") and
§4.6 promise "O(matches log matches) per parse" — the implementation does not deliver that.

Consequence: a spec that paints a common anchor (e.g. every keyword / every identifier) over a
large document produces one interval per occurrence; `n` in the thousands makes this millions of
containment checks per highlight. The cost lands on the same per-request path as finding 1 and
grows quadratically with document size, so it is the scale ceiling for real specs on real files.

Fix: replace the boundary×interval double loop with a sweep line — sort interval start/end
events, maintain the active set (or a max-key structure) as the sweep crosses boundaries, and
emit the winning paint per segment. That reaches the O(n log n) the design advertises.

---

## efficiency-3 — `classify` walks the analysis tree twice

`fltk/lsp/classify.py:372` calls `_explicit_intervals(tree, …)` and `:380` then iterates
`_default_intervals(tree, …)` — two independent full depth-first traversals of the same CST,
each re-resolving `tables.kind_to_rule.get(node.kind.name)` per node. Design §4.6 states the
defaults are "emitted per terminal span / trivia node during the same walk"; the implementation
splits them into two walks.

Consequence: per-request work is ~2x the necessary tree traversal plus duplicated kind→rule
lookups. Linear (not quadratic), so lower-stakes than 1–2, but it is on the same hot path and
contradicts the design's single-walk intent. Bites on large trees, additive with every highlight.

Fix: fold the default-interval emission into the `_explicit_intervals` walk (collect both interval
lists in one traversal), or accept the two-walk cost as a deliberate simplification and correct the
design's "same walk" wording so the next reader doesn't assume it.

---

## efficiency-4 — `ByLabel` matcher re-uppercases its name on every child comparison

`fltk/lsp/classify.py:232` `_matches`: `return label_name is not None and label_name == match.name.upper()`.
`match.name.upper()` is recomputed on every matcher×child comparison during the explicit walk,
even though `match.name` is fixed at resolution time.

Consequence: minor but on the hot path and multiplied by (children × matchers). Redundant string
allocation per comparison.

Fix: store the uppercased form once when the `ByLabel` is built in `resolve_config`
(`lsp_config.py` `_resolve_local_anchor`/`_resolve_global_anchor`), or normalize `name` to
uppercase in `ByLabel` construction, so the compare is a bare `==`.

---

## efficiency-5 — `parse_lsp_config_file` pre-checks existence before opening (TOCTOU)

`fltk/plumbing.py:290-296`: `if not config_path.exists(): raise FileNotFoundError(...)` then
`config_path.open()`. This is the pre-check-then-operate pattern — the `open()` already raises
`FileNotFoundError` on a missing path.

Consequence: minor (config is loaded once, not on a hot path) and there is a TOCTOU gap, but the
extra stat call and the branch buy nothing over letting `open()` raise. Listed for completeness
per the existence-check catch.

Fix: drop the `exists()` guard and call `open()` directly; if a custom message is wanted, catch
`FileNotFoundError` and re-raise with the friendlier text.

---

# Final round — slice: AnalysisEngine (§4.7), fltk-highlight CLI (§4.8), dogfood (§8)

Commit reviewed: HEAD 9a085e9 (base 87dbc0d). Files in scope this round: `fltk/lsp/engine.py`,
`fltk/lsp/highlight_cli.py`, `fltk/lsp/test_dogfood.py`, `fltk/lsp/fltklsp.fltklsp`.

## efficiency-6 — `AnalysisEngine.highlight` did not hoist the per-grammar table build; it rebuilds (recompiling every regex) on every call

`fltk/lsp/engine.py:75-85` — `highlight` is now the concrete per-request hot path the earlier
findings anticipated (§4.7: "text → tokens many times"; the M2 server calls it per edit). The
engine caches the parser (`self._parser_result`) and resolved config in `__init__`, but not the
grammar's classification tables. So `classify.classify` (`classify.py:372`) still calls
`build_grammar_tables(self._parser_result.grammar)` on every `highlight`, re-walking every rule
and re-`re.compile`-ing every `Regex` term (`classify.py:85`) of a grammar that is fixed for the
engine's lifetime. This is exactly the wiring efficiency-1 (above) told the engine author to
avoid ("build the tables once alongside the parser … and pass them into each classify call"); the
engine as written does not do it.

Consequence: redundant per-request CPU proportional to grammar size, dominated by repeated regex
compilation, on the interactive-latency path — the M2 server re-pays it on every keystroke.
Diverges from design §4.6 ("build … once") and §4.3 ("precomputes per-rule tables once").

Fix: in `AnalysisEngine.__init__`, compute
`classify.build_grammar_tables(self._parser_result.grammar)` (grammar is stable there) and thread
the cached `_GrammarTables` into `classify` via a new optional parameter, so `highlight` reuses it
across calls. This is the engine-seam half of `TODO(lsp-classify-hotpath)`; the O(n²)
`_winner_segments` (efficiency-2) and double-walk (efficiency-3) remain internal to `classify.py`.

## Not findings this round (checked)

- `AnalysisEngine.__init__` generating one parser via `generate_parser` — one-time startup cost,
  the ADR's accepted profile (§4.7). Not hot-path.
- `from_paths` reading grammar + `.fltklsp` once — startup; fine.
- `highlight_cli._render` — single `file.read_text()`, one list-build + `join`, no redundant
  slicing beyond output. Fine.
- `test_dogfood._token_type`'s `text.index` per assertion — test-only cost (test-reviewer's lane),
  not a runtime path.
