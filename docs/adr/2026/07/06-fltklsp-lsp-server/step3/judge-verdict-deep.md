# Judge verdict — deep review

Phase: deep. Base 1ad3141..HEAD 7576e26e7727fe83bdfca19e1ce5304955534df7 (fix commit 7576e26 on top of reviewed HEAD 8966d8e). Round 1.
Notes: 7 reviewer files; 22 findings (18 Fixed, 2 TODO, 2 Won't-Do).
Verified: `uv run pytest fltk/lsp/` 265 passed; `ruff check fltk/lsp/` clean; `pyright fltk/lsp/` clean.

## Added TODOs walk

No new TODO slugs were added; two findings are dispositioned onto the pre-existing tracked `TODO(lsp-classify-hotpath)` (entry confirmed at `TODO.md:67`; code comment at `classify.py:416-418` explicitly names `symbols.extract` as the third O(tree) walk absorbed by the planned unification).

### efficiency-1 — TODO(lsp-classify-hotpath), engine.py:152
Q1 (worth doing): yes — extraction is genuine new blocking work on the per-keystroke analyze path.
Q2 (design/owner input required): yes — folding the three walks (extraction, explicit paints, defaults) into one is the design-stage sweep-line/walk-fusion rewrite `TODO.md` already scopes; design §4.4 explicitly commits the third walk to this TODO rather than to this round.
Not a silent deferral of an iteration-created problem: the frozen design sanctions the cost and extends the existing TODO by name; the reviewer's own finding states "No separate action needed."
Assessment: TODO acceptable.

### efficiency-2 — TODO(lsp-classify-hotpath), symbols.py:191/214
Q1 (worth doing now, standalone): effectively no — one redundant `kind_to_rule.get` per interior node; the reviewer calls it "individually cheap," and the same pattern predates the round in `classify._explicit_intervals`. The standalone micro-fix (threading a pre-resolved `gsm.Rule` through the recursive `_walk` signature) would be obsoleted by the tracked walk-fusion rewrite that owns the real fix.
Q2 (for the real fix): yes — same walk unification as efficiency-1, design work already tracked.
Assessment: TODO acceptable; the tracked slug's comment covers extraction, so the join key is honest.

## Other findings walk

### errhandling-1 — Fixed
Claim: one five-condition guard in `rename_document` mislabeled a client race and two invariant breaks as "document has parse errors"; on-call could not distinguish them.
Code at `server.py:405-426`: guard split into distinct raises — disk-backed/no-version refusal, "document changed during rename; retry" (live-version re-check after the analysis await), "no analysis is available" (`analysis is None or line_index is None` — legitimately reachable via the epoch-bump/close path, so a non-internal message is right), "document has parse errors" reserved for `analysis.error is not None`, and a distinct "internal error, the analysis produced no symbol table" for `analysis.symbols is None`. All carry `RequestFailed`.
Assessment: each cause now has its own message and the race gets a retryable signal — exactly the split asked for. Accept.

### errhandling-2 — Fixed
Claim: `_debounced_analyze`'s catch logged `{exc!r}` only — no stack — while M4's new extraction walk added a failure surface that collapses there.
Code at `server.py:321-331`: `import traceback` added; message now embeds `traceback.format_exc()`, comment explains the stack is how parse/extraction/classification stages are told apart.
Assessment: fix addresses the consequence at the named line. Accept.

### correctness-1 — Fixed
Claim: rename applied version-N occurrence offsets to a live `document.source` re-read after awaits, and the staleness check compared only against the entry-time captured state — a `didChange` racing either await produced a garbage verify and, for `changes`-fallback clients, corrupting edits.
Code at `server.py:400-449`: `text = document.source` snapshotted once at entry before any await; that snapshot feeds both `_ensure_analyzed` and `_apply_edits`; live-version re-checks (`get_text_document(uri).version != version`) after the analysis await (`:412`) and after the verify-reparse await (`:444`), mirroring `analyze_and_publish`'s precedent. The dropped `state.analyzed_version != version` check is subsumed: `_store` either sets `analyzed_version = version`, keeps a newer version (in which case the live version differs and the re-check fires), or returns an empty `_DocState` on an epoch bump (caught by the "no analysis" raise).
Assessment: the verify now always runs against the analyzed text and any raced rename aborts. Pinned by `test_rename_refuses_when_version_advances_during_analysis`. Accept.

### security-1 — Fixed
Claim: same root cause as correctness-1 from the trust-boundary angle (client-timed `didChange` → corrupting edits for capability-less clients).
Same change as correctness-1; the corruption window is now the response wire only, the minimum LSP allows, matching the reviewer's suggested fix verbatim.
Assessment: accept.

### security-2 — Fixed
Claim: `version is None` (never-opened, disk-backed URI) disabled every rename safety mechanism — version guard vacuous (`None != None`), two independent disk reads, `version=None` in the payload meaning "do not version-check."
Code at `server.py:405-410`: rename refuses with `RequestFailed` when `version is None`, before any analysis; read-only features unchanged as the reviewer scoped.
Assessment: the write path is now restricted to synced documents. Accept.

### test-1 — Fixed
Claim: the design-called-out no-op rename branch (§2.6) had zero tests.
Code: `test_features.py::test_rename_edits_empty_occurrences_document_changes` / `_plain_changes` (well-formed edit, zero `TextEdit`s, both shapes) and `test_server.py::test_rename_to_same_name_returns_empty_edit` (protocol round trip asserting `edit.edits == []`). All pass.
Assessment: matches the reviewer's requested shape. Accept.

### test-2 — Fixed
Claim: the §2.6 version-race guard had no test exercising the race it exists for.
Code: `test_server.py::test_rename_refuses_when_version_advances_during_analysis` — fake workspace returns version 1 at entry then version 2 after the (stubbed) analysis await; asserts `JsonRpcException` matching "changed during rename". This is the reviewer's proposed narrower unit-test variant, retargeted at the post-fix semantics (the raced rename now refuses rather than returning a versioned edit) — the corruption class the finding names cannot regress silently.
Assessment: accept.

### test-3 — Fixed
Claim: RecursionError-during-extraction was asserted in prose only (existing test raised it in `parse_text`, before extraction is reached).
Code: `test_engine_analyze.py::test_analyze_extraction_recursion_error_reports_offset_none` monkeypatches `engine_module.symbols.extract` on a cleanly-parsing document; asserts `tree`/`tokens`/`symbols` all `None`, `error.offset is None`, message pinned. Passes.
Assessment: exactly the requested test. Accept.

### test-4 — Fixed
Claim: the §4.3 identical-span nested-namespace chain had no pinning test.
Code: `test_symbols.py::test_identical_span_nested_namespaces_nest_and_resolve_outward` — `outer := inner ;` with both rules namespaces; asserts two distinct scopes with coinciding bounds, `inner_scope.parent is outer_scope`, and a reference inside resolving outward through both to a root-level symbol.
Assessment: pins precisely the "skip the redundant scope" regression the reviewer described. Accept.

### reuse-1 — Fixed
Claim: ~12-line per-child decode block duplicated between `symbols._walk` and `classify._explicit_intervals`.
Code: `classify.child_surface` (`classify.py:178-202`) added and consumed by both walks (`classify.py:278`, `symbols.py:205-207`); the stale `SpanKind` import dropped from `symbols.py`.
Assessment: duplication removed; single decode owner. Accept.

### reuse-2 — Fixed
Claim: `test_server._line_col` hand-rolled a narrower position-math reimplementation instead of `LineIndex.offset_to_position`.
Code: `_line_col` now delegates to `LineIndex(text).offset_to_position(offset, encoding)` with a `PositionEncodingKind → PositionEncoding` map; tests assert against the server's own math.
Assessment: accept.

### quality-1 — Fixed
Claim: nine copies of the pull-handler preamble.
Code: `FltkLanguageServer._serveable_for` (`server.py:358-370`) added; the seven read-only pull handlers (folding_range, selection_range, document_symbol, definition, references, document_highlight, prepare_rename) collapsed onto it. `semantic_tokens_full`/`_range` retain their own preamble — justified: their none-case returns `SemanticTokens(data=[])`, not `None`, and range needs the raw state.
Assessment: serving policy now has a single owner; the retained copies have genuinely distinct semantics. Accept.

### quality-2 — Fixed
Same duplication as reuse-1; same `child_surface` fix, with the trivia-descent difference deliberately left per-walk as the finding specified. Accept.

### quality-3 — Fixed
Claim: `resolve_config`'s def branch expanded each anchor twice and built the same `Tier` in two places, risking paint/extraction precedence drift.
Code at `lsp_config.py:687-701`: one loop over `_local_anchor_matches` builds each `Tier` once and emits both the `ChildMatcher` (when the kind's first segment is in the legend) and the `DefMatcher` from it. Behavior equivalence pinned by the existing paint-resolution tests (suite green; design pins declaration paint bit-identical).
Assessment: accept.

### quality-4 — Fixed
Claim: bare `JsonRpcException` defaulted to `-32603` InternalError for deliberate domain refusals.
Code: every `rename_document` raise now carries `code=lsp.LSPErrorCodes.RequestFailed` (`server.py:410,416,420,423,426,443,446`).
Assessment: accept.

### quality-5 — Fixed
`_symbol` renamed to `symbol` at `server.py:432-434`; it is used in the no-op check. Accept.

### quality-6 — Fixed
Claim: `prepare_rename` re-derived the lookup and needed an assert because `symbol_target` discarded the span.
Code: `features.target_span` (`features.py:259-271`) added as the span-carrying primitive; `symbol_target` is its projection; `prepare_rename` (`features.py:328-334`) uses it directly — second/third lookups and the cross-function assert are gone.
Assessment: exactly the proposed shape. Accept.

### quality-7 — Fixed
Claim: `# type: ignore[arg-type]` masking a widening annotation.
Code: `rename_edits` builds `edits: list[lsp.TextEdit | lsp.AnnotatedTextEdit]` in the `document_changes` branch; ignore removed; plain-`changes` branch keeps its own `list[lsp.TextEdit]`. Pyright clean.
Assessment: accept.

### efficiency-3 — Won't-Do
Claim: rename's verify-reparse runs full `analyze` (parse + extract + classify) when only parse success is consulted. Reviewer's own severity: "Low priority... design §2.6 explicitly accepts 'one extra classification pass.'"
Rationale check: design §4.6 states verbatim that verify runs "via `engine.analyze` on the worker thread — one extra classification pass on an explicit user action is acceptable." A parse-only entry point would widen `AnalysisEngine`'s public surface — per CLAUDE.md, out-of-tree consumers construct engines, so surface additions carry a real compatibility cost — and fork the analyze path's error handling, for savings on an infrequent explicit action.
Assessment: the design explicitly accepts the cost and the refusal argues active harm, not mere inconvenience. Sound Won't-Do.

### efficiency-4 — Won't-Do
Claim: `symbol_at`/`reference_at` scan linearly where design §4.3 said "bisect-over-sorted-starts." Reviewer's own severity: "impact is negligible today... No action required unless symbol counts grow" — flagged purely as a design-note deviation.
Rationale check: technically correct — the query is *smallest containing span*, span ends are not monotonic in starts (a wide node-anchored def can start before and contain a deeper name — the codebase's own `test_symbol_at_and_reference_at_select_innermost` exercises this nesting), so a start-bisect still requires an O(n)-worst-case scan of the qualifying prefix plus nesting-aware window management. Trading an obviously-correct linear scan on a cold, user-initiated path for a subtler bisect with no asymptotic win is a net loss; behavior is identical to the design's requirement.
Assessment: the rationale shows the design's implementation note was optimistic, not that the responder is dodging work. Sound Won't-Do; the deviation is recorded in the dispositions doc.

## Disputed items

None.

## Approved

22 findings: 18 Fixed verified against source and tests at HEAD, 2 TODO dispositions acceptable (pre-existing tracked slug, design-sanctioned deferral), 2 Won't-Do sound.

---

## Verdict: APPROVED

All dispositions acceptable. Fix commit 7576e26; `fltk/lsp` suite (265 tests), ruff, and pyright verified clean.
