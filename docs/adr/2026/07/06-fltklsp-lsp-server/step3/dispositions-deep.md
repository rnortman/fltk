# Deep review dispositions — step3 (.fltklsp M4)

Round base `1ad3141`. Fixes committed on top of prior HEAD `8966d8e`.
All code fixes stay within the touched `fltk/lsp/` package + its tests. Full suite green
(`uv run pytest`: 2873 passed, 1 skipped; `ruff check`/`ruff format --check`/`pyright` clean).

---

## errhandling-1

- Disposition: Fixed
- Action: `fltk/lsp/server.py` `rename_document` — the single five-condition guard is split into
  distinct raises with distinct messages: the client-race (`get_text_document(uri).version !=
  version` after the analysis await) now says "document changed during rename; retry"; the
  `analysis is None`/`line_index is None` case says "no analysis is available for the current
  document"; `analysis.error is not None` keeps the "document has parse errors" message; and the
  invariant `analysis.symbols is None` (success with no table) raises a distinct "internal error,
  the analysis produced no symbol table". All use `code=lsp.LSPErrorCodes.RequestFailed` (see
  quality-4).
- Severity assessment: The old single guard reported "the document has parse errors" for a benign,
  retryable keystroke race and for two internal-invariant breaks, so on-call could not distinguish a
  transient race from a real parse failure from an engine-contract bug.

## errhandling-2

- Disposition: Fixed
- Action: `fltk/lsp/server.py` `_debounced_analyze` catch — logs `traceback.format_exc()` (added
  `import traceback`) instead of `{exc!r}`, so an extraction/classification invariant break is
  localizable from the client's server log alone.
- Severity assessment: Fire-and-forget task whose one log line was the sole field record; M4's new
  extraction walk added a failure surface that previously collapsed to a repr with no stack.

## correctness-1

- Disposition: Fixed
- Action: `fltk/lsp/server.py` `rename_document` — `text = document.source` is now snapshotted once
  at entry (before any await) and used for both `_ensure_analyzed` and `_apply_edits`, so the
  verify-reparse and returned offsets always describe the analyzed version. Added a post-await
  live-version re-check (`get_text_document(uri).version != version`) after the analysis await and
  again after the verify-reparse await, mirroring `analyze_and_publish`'s precedent — a `didChange`
  racing either await now aborts the rename instead of splicing version-N offsets into version-N+1
  text.
- Severity assessment: Document-corruption / vacuous-verify bug on the one write path; for
  capability-less clients the server previously returned stale offsets it claimed to have verified.

## security-1

- Disposition: Fixed
- Action: Same change as correctness-1 (identical root cause: mixed document versions across the
  rename awaits). The entry-time text snapshot plus post-await version re-checks shrink the
  capability-less-client corruption window to the response wire only — the minimum LSP allows — and
  make the verify guard trustworthy for all clients.
- Severity assessment: Silent corruption of the user's buffer, triggerable by an ordinary keystroke
  (or any concurrent editor) racing a rename.

## security-2

- Disposition: Fixed
- Action: `fltk/lsp/server.py` `rename_document` — refuses (`JsonRpcException`,
  `RequestFailed`) when `document.version is None`, i.e. a URI the client never opened (disk-backed,
  where every `.source` read re-reads the file and no version can guard a concurrent on-disk
  rewrite). Rename now operates only on documents the client has opened and is syncing. Read-only
  features serving disk-backed URIs are unchanged (pre-existing, harmless).
- Severity assessment: Low likelihood but it was precisely the "stale offsets applied to current
  text" corruption §2.6 declares unacceptable, with every §2.6 safeguard inert on that path.

## test-1

- Disposition: Fixed
- Action: Added `fltk/lsp/test_features.py::test_rename_edits_empty_occurrences_document_changes`
  and `::test_rename_edits_empty_occurrences_plain_changes` (well-formed edit, zero `TextEdit`s in
  both shapes) and `fltk/lsp/test_server.py::test_rename_to_same_name_returns_empty_edit` (protocol
  round trip: rename to the current name returns an empty `documentChanges` edit).
- Severity assessment: The no-op branch (§2.6) skips the verify-reparse entirely and was previously
  exercised by no test; a regression rendering a zero-edit payload wrong would have shipped silent.

## test-2

- Disposition: Fixed
- Action: Added `fltk/lsp/test_server.py::test_rename_refuses_when_version_advances_during_analysis`
  — a fake workspace whose `get_text_document` returns version 1 then version 2 (simulating a
  `didChange` landing during the analysis await) with `_ensure_analyzed` stubbed; asserts
  `rename_document` raises `JsonRpcException` matching "changed during rename". This pins the guard
  fixed under correctness-1/security-1.
- Severity assessment: The load-bearing safety property of the whole rename feature had no test
  exercising the race it exists for.

## test-3

- Disposition: Fixed
- Action: Added `fltk/lsp/test_engine_analyze.py::test_analyze_extraction_recursion_error_reports_offset_none`
  — monkeypatches `engine_module.symbols.extract` to raise `RecursionError` on a
  cleanly-parsing document (so extraction is actually reached, unlike the pre-existing parse-time
  test) and asserts `analyze()` degrades to `tree`/`tokens`/`symbols` all `None` with
  `offset=None`.
- Severity assessment: Extraction's unbounded `_walk` recursion is a genuine stack-blowup surface;
  the guard covering it was asserted only in prose.

## test-4

- Disposition: Fixed
- Action: Added `fltk/lsp/test_symbols.py::test_identical_span_nested_namespaces_nest_and_resolve_outward`
  — grammar `outer := inner ;` with both rules namespaces gives two scopes with coinciding spans;
  asserts `root.children` holds one outer scope containing one inner scope with equal bounds and
  `inner.parent is outer`, and that a reference inside `inner` resolves outward through both scopes
  to a root-level symbol.
- Severity assessment: A plausible "skip the redundant scope" optimization would silently change
  shadowing semantics for chained single-child namespace rules, with nothing failing today.

## reuse-1

- Disposition: Fixed
- Action: Extracted `classify.child_surface(label, child, text, tables) -> (is_span, start, end,
  child_text, child_rule_name, label_name)` (`fltk/lsp/classify.py`) and consumed it in both
  `classify._explicit_intervals` and `symbols._walk` (`fltk/lsp/symbols.py`), removing the
  duplicated per-child decode block. Dropped the now-unused `SpanKind` import from `symbols.py`.
- Severity assessment: Two copies of the child-shape decode could diverge (new `SpanKind`,
  Rust-backend span access) and silently make paint and symbol extraction disagree about which
  child a matcher hits.

## reuse-2

- Disposition: Fixed
- Action: `fltk/lsp/test_server.py` `_line_col` now delegates to
  `LineIndex(text).offset_to_position(offset, enc)` (with a `PositionEncodingKind` →
  `PositionEncoding` map) instead of hand-rolling line/utf-16 math, so the test asserts against the
  same conversion the server uses.
- Severity assessment: A second position-math implementation could diverge from `LineIndex` (e.g.
  `\r\n` fixtures) and mask a real regression while both looked self-consistent.

## quality-1

- Disposition: Fixed
- Action: Added `FltkLanguageServer._serveable_for(uri) -> tuple[_GoodAnalysis, PositionEncoding] |
  None` (fetch + ensure-analyzed + last-good fallback + encoding) and collapsed the seven read-only
  pull handlers (`document_symbol`, `definition`, `references`, `document_highlight`,
  `prepare_rename`, `folding_range`, `selection_range`) onto it. `semantic_tokens_full`/`_range`
  keep their own preamble (distinct none-semantics: empty tokens, range bisect).
- Severity assessment: Nine copies of the serving preamble meant any serving-policy change had nine
  edit sites and could drift at one.

## quality-2

- Disposition: Fixed
- Action: Same shared `classify.child_surface` helper as reuse-1 (the two findings name the same
  duplication). The trivia-descent difference between the two walks stays a per-walk decision; only
  the decode is unified.
- Severity assessment: `match_applies` only means the same thing in both modules if both decode the
  child identically; the walks already diverge on trivia, so a decode tweak in one could silently
  desync paint and extraction.

## quality-3

- Disposition: Fixed
- Action: `fltk/lsp/lsp_config.py` `resolve_config` def branch — one loop over
  `_local_anchor_matches(def_stmt.anchor, rule_index)` builds each `Tier` once and emits both the
  declaration-site `ChildMatcher` (when the kind's first segment is a legend token) and the
  semantic `DefMatcher` from it, replacing the two independent expansions/`Tier` constructions.
- Severity assessment: Two independent `Tier` builds for one `def` could drift under a future
  precedence change, making declaration-site paint and symbol extraction pick different winners for
  the same child.

## quality-4

- Disposition: Fixed
- Action: All `rename_document` refusals raise `JsonRpcException(msg,
  code=lsp.LSPErrorCodes.RequestFailed)` (`-32803`) instead of the default `-32603`
  (InternalError).
- Severity assessment: `-32603` reads as a server crash to clients/telemetry; routine rename
  refusals were indistinguishable from real internal errors in client logs, and some editors prompt
  a bug report on it.

## quality-5

- Disposition: Fixed
- Action: `fltk/lsp/server.py` `rename_document` — `_symbol` renamed to `symbol` (it is used, in the
  no-op `new_name == symbol.name` check).
- Severity assessment: The leading underscore signalled "unused" to readers and lint conventions,
  inviting a cleanup that would break the no-op check.

## quality-6

- Disposition: Fixed
- Action: `fltk/lsp/features.py` — added `target_span(table, offset) -> tuple[Symbol, tuple[int,
  int]] | None` (symbol + the exact span under the cursor) as the primitive; `symbol_target` is now
  its projection and `prepare_rename` uses it directly, removing the second/third containment
  lookups and the `assert reference is not None` that papered over the discarded span.
- Severity assessment: The assert encoded a cross-function invariant that an M5 cross-file change to
  `symbol_target` could silently violate, turning it into a crash path; the recompute pattern would
  be copied by the next feature needing the addressed span.

## quality-7

- Disposition: Fixed
- Action: `fltk/lsp/features.py` `rename_edits` — the `document_changes` branch builds `edits:
  list[lsp.TextEdit | lsp.AnnotatedTextEdit]` via an annotated comprehension (bidirectional
  inference widens each element), dropping `# type: ignore[arg-type]`; the plain-`changes` branch
  builds its own `list[lsp.TextEdit]`.
- Severity assessment: The blanket `type: ignore` suppressed all future arg-type errors at that call
  site and normalized ignores where a one-token annotation sufficed.

## efficiency-1

- Disposition: TODO(lsp-classify-hotpath)
- Action: No code change. Already tracked: `fltk/lsp/classify.py:400-402` and the `TODO.md`
  `lsp-classify-hotpath` entry both call out the third `O(tree)` walk (extraction) and the planned
  single-walk unification. The finding itself states "No separate action needed."
- Severity assessment: One extra tree traversal per debounced analysis; real but bounded, and the
  design (§4.4/§5) deliberately defers the walk fusion to the tracked TODO.

## efficiency-2

- Disposition: TODO(lsp-classify-hotpath)
- Action: No code change. The double `rule_for_node` lookup for each non-span node in `symbols._walk`
  is a single `dict.get` + guard per node and is absorbed by the same walk-unification the existing
  `TODO(lsp-classify-hotpath)` owns (its comment already names `symbols.extract` as the third walk).
  Threading a pre-resolved `gsm.Rule` through `_walk` now would add signature complexity ahead of
  that planned rewrite for a negligible saving.
- Severity assessment: A redundant dict lookup per interior node per keystroke; negligible, and the
  same pattern predates this round in `classify._explicit_intervals`.

## efficiency-3

- Disposition: Won't-Do
- Action: No change.
- Severity assessment: Rename's verify-reparse runs a full `engine.analyze` (parse + extract +
  classify) when only parse success is consulted.
- Rationale (Won't-Do): Design §2.6 explicitly accepts "one extra classification pass on an explicit
  user action." Rename is infrequent and user-initiated, so the wasted extract/classify is
  immaterial. Adding a parse-only entry point to `AnalysisEngine` to avoid it would widen the
  engine's public surface (out-of-tree consumers construct `AnalysisEngine`s) and fork the analyze
  path's error handling — a net loss in clarity and a new API-compatibility burden for a saving on a
  rare action.

## efficiency-4

- Disposition: Won't-Do
- Action: No change (`symbol_at`/`reference_at` keep the linear `_smallest_containing` scan).
- Severity assessment: Design §4.3 mentioned "bisect-over-sorted-starts"; the implementation scans
  linearly. Behaviorally identical; these are user-initiated (not per-keystroke) paths over modest
  symbol counts.
- Rationale (Won't-Do): The query is *smallest containing span*, and a span's end offset is not
  monotonic in its start (a wide node-anchored def can start before and contain a deeper name), so a
  bisect on sorted starts still needs an O(n)-worst-case scan of the qualifying prefix and adds
  window-management complexity that must correctly handle nesting. Replacing an obviously-correct
  linear scan with a subtler bisect for zero asymptotic gain on a cold path trades a real
  correctness-risk for no measurable benefit.
