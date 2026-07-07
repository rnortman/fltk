# Deep correctness review — step3 M4 (defs/refs semantics)

Reviewed: `git diff 1ad3141..8966d8ee42840c5f7fbf26090b14ef20eafc28e0` (fltk/lsp/symbols.py,
lsp_config.py, classify.py, engine.py, features.py, server.py + tests), read against
`step3/design.md` (frozen) and the full current contents of every touched source file.

## correctness-1

- **File:line**: `fltk/lsp/server.py:382-408` (`FltkLanguageServer.rename_document`)
- **What's wrong**: The rename handler's verify-reparse guard applies the version-N
  occurrence offsets to a *re-read* of the live document text, and its staleness check
  compares the analyzed version against a version captured *before* the await — so a
  `didChange` processed while the analysis await is pending slips past both.
- **Why** (trace):
  1. Line 382-383: `document = self.workspace.get_text_document(uri)`; `version = document.version`
     captures version N. `document` is pygls's *live* `TextDocument` — its `.source` and
     `.version` mutate when a `didChange` is processed.
  2. Line 384: `state = await self._ensure_analyzed(uri, version, document.source)`. The
     `document.source` argument is evaluated at call time (text_N, correct). But when the
     analysis actually runs on the worker (state not already current — e.g. rename issued
     inside the 200 ms debounce window after an edit), this `await` yields to the loop, and a
     `didChange` to version N+1 can be processed there: pygls updates `document` to
     (N+1, text_{N+1}) and `schedule_debounced` only *schedules* the N+1 analysis (0.2 s
     sleep), so by the time the rename coroutine resumes, `state.analyzed_version == N`.
  3. Line 387: the guard checks `state.analyzed_version != version` — both sides are N, so
     the check passes even though the document is now at N+1. (Contrast
     `analyze_and_publish`, server.py:302-304, which re-reads `document.version` after its
     await for exactly this reason.)
  4. Line 397-400: `occurrences` are codepoint spans in text_N (from the N analysis).
  5. Line 406: `renamed = _apply_edits(document.source, occurrences, new_name)` — but
     `document.source` is now text_{N+1}. Version-N offsets are spliced into version-N+1
     text: the in-memory "renamed" document is garbage relative to both versions.
- **Consequence**: The verify-reparse guard — the safety mechanism design §2.6 introduces
  specifically so rename never commits edits whose applied result was not checked — runs
  against the wrong text whenever a keystroke races the rename's first worker await:
  - If the mangled splice fails to parse, a *valid* rename is rejected with
    "the new name would leave the document unparseable" (spurious user-facing error).
  - If the mangled splice happens to parse, the guard reports success for a text that is
    neither what the client will produce nor what was analyzed — the verification is
    vacuous. For clients with `workspace.workspaceEdit.documentChanges` the versioned edit
    still saves the apply (client refuses version N against N+1), but for the plain
    `changes` fallback the server returns stale offsets it *claims* to have verified,
    producing exactly the document corruption §2.6 exists to prevent. The design accepts a
    residual client-side race only for capability-less clients *after* a correct server-side
    verify; here the server-side verify itself is broken.
- **Suggested fix**: Capture `text = document.source` once at entry (before the first
  await); pass that `text` to `_ensure_analyzed` and to `_apply_edits`. After the first
  await, re-read the live document and fail (or retry) if
  `self.workspace.get_text_document(uri).version != version`, mirroring
  `analyze_and_publish`'s post-await version re-check. (The second await — the verify
  reparse — is already covered by the versioned `documentChanges` payload, per design §2.6.)

## Checked and found sound (no findings)

- `symbols._walk`: hoist semantics (symbols always append to the *enclosing* `scope`,
  node children recurse with the namespace's `child_scope`) exactly implement design §2.1;
  refs carry the inner scope, so self-reference resolves via the outward walk.
- `_best_match` tier tie-breaking, def-beats-ref per child, union-anchor collapse — all
  match §4.2; tiers are unique per rule (distinct `stmt_index` across statements, distinct
  `anchor_rank` within one), so the strict `>` cannot pick nondeterministically.
- `_resolve` outward walk + `_kind_matches` segment-boundary prefix (`symbol_kind[:len(k)] == k`)
  match §4.2/spec §3; `_sort_scope_symbols` before resolution gives document-order-first
  duplicates; forward references resolve (whole-scope visibility) as designed.
- `occurrences` dedupe (pre-seeded with the declaration span) keeps rename edits
  non-overlapping; `_apply_edits` applies back-to-front over sorted spans — offset math sound.
- `classify._ref_intervals`: appended before `covered` is computed, so ref paint suppresses
  defaults; `(ref.depth, ref.tier)` reproduces the extractor's key (both walks count depth
  identically from root 0); `SOURCE_RANK_REF=1 < SOURCE_RANK_SCOPE=2` gives "explicit scope
  wins"; `symbol_table=None` default keeps round-2 output byte-identical.
- `resolve_config`: def paint emission unchanged (bit-identical tiers); `def_matchers`/
  `ref_matchers`/`namespace_rules` accumulation across multiple blocks for one rule is
  correct, including the `del child_matchers[...]`-when-empty interplay.
- `engine.analyze`: `extract` runs inside the existing `RecursionError` try; failure paths
  leave `symbols=None`; success path threads the table into `classify`.
- `features.document_symbols`: the `(range_start, -range_end)` sort plus strict-containment
  stack handles the trailing-name-anchor case and equal-range siblings (CST spans are
  laminar, so partial overlap is impossible).
- `_smallest_containing` inclusive-end containment is the standard cursor-at-word-end LSP
  convention; ties resolve deterministically (sorted inputs, strict `<`).
- `JsonRpcException(msg)` is valid in the pinned pygls (message-only ctor, `CODE` default
  -32603); `get_capability` paths match lsprotocol's snake_case attribute names (exercised
  by the new server tests).

One finding total.
