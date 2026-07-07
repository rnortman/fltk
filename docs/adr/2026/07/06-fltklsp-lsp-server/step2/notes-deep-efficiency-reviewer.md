# Deep efficiency review — round-2 (M2 fltk-lsp server)

Base 9719bab7 · HEAD d9ab841. LSP server: keystroke-scale latency and event-loop
responsiveness are the yardstick — CPU work that lands on the asyncio loop thread, or
work repeated per edit, is what matters here.

## efficiency-1 — Semantic-token encoding runs on the event loop, per analysis, unconditionally

`server.py:147-163` (`_store`), called from `_analysis_for` at `server.py:183` *after*
`await future`. The `run_in_executor` boundary is the `await`; everything after it runs on
the asyncio loop thread. So `features.encode_semantic_tokens(...)` (line 161) — the single
most expensive translation in the module — executes on the protocol loop, not the worker.

Encoding is O(tokens × line-prefix): `_line_segments` calls `offset_to_position` ~4× per
token, and each call under UTF-16 slices `self._text[start:offset]` and sums `ord()` over
every prefix char (`positions.py:78-89`). For a large document — especially the whole-doc
`comment` paints the design calls out (clockwork `doc` subtrees, multi-line-split into many
segments) with any astral text — this is a non-trivial synchronous burst on the loop.

Two compounding wastes: (a) it happens on **every** successful analysis (didOpen, every
settled edit, every pull-triggered analysis), and (b) it happens even for a diagnostics-only
client that never issues `semanticTokens/full` — the encode is pure dead work there.

This also contradicts the module's own stated contract (`server.py:5-7`, `:93`: "All
parsing/classification runs on a single worker thread so the protocol loop is never
blocked").

**Consequence:** every edit that settles into a successful parse blocks the asyncio loop for
the encode duration, delaying diagnostics publication and every concurrent request/response
for other URIs — visible as keystroke-scale stalls on large files, and paid even by clients
that don't consume semantic tokens.

**Fix:** compute `encoded_tokens` (and the `_GoodAnalysis` snapshot) inside
`_analyze_blocking` on the worker thread. The encoding kind is fixed after `initialize`, so
capture `self._encoding()` at submit time and pass it into the worker; `_store` then only
assigns already-computed fields. Optionally defer/skip the encode when the client didn't
advertise the semantic-tokens capability.

## efficiency-2 — Debounced analysis re-parses a version a pull handler already analyzed

Pull handlers (`semantic_tokens_full`, `folding_range`, etc.) call `_ensure_analyzed`
(`server.py:185-190`), which analyzes the *current* version immediately — the debounce
(`_DEBOUNCE_SECONDS`, `server.py:242-247`) gates only the push/diagnostics path, not pulls.
So a semantic-token / folding / selection request arriving during the 0.2s window triggers a
full parse+classify right away and stores `analyzed_version == version`. When the debounce
timer then fires, `_debounced_analyze` → `analyze_and_publish` → `_analysis_for`
(`server.py:224-240`) re-submits the **same version** unconditionally — `_analysis_for` only
dedups against a still-*in-flight* future (`:171-172`), not against an already-completed,
stored result. The inflight one is gone by then, so the document is parsed and classified a
second time.

Editors commonly request semantic tokens right after an edit, so this double-analysis is the
common case, not a corner case.

**Consequence:** a redundant full parse + classify per settled edit on the single-worker
executor — doubles the per-edit CPU cost and pushes back the next document's analysis in the
serialized queue.

**Fix:** have the debounce/publish path go through `_ensure_analyzed` (which short-circuits
when `state.analyzed_version == version and state.analysis is not None`) instead of calling
`_analysis_for` directly; still publish diagnostics from the returned state.

## efficiency-3 — `semanticTokens/range` linearly scans all tokens, then re-encodes on the loop

`server.py:380-392`. The subset filter `[token for token in good.tokens if token.start < end
and token.end > start]` is O(all tokens) per request, and the subsequent
`encode_semantic_tokens` (line 392) again runs on the event-loop thread. Range requests fire
repeatedly on scroll, so both costs recur at interaction frequency on large files.

`good.tokens` is sorted by `start` and non-overlapping (so `end` is monotonic too), so both
range bounds are `bisect`-findable — the scan can be O(log n + subset) instead of O(n).

**Consequence:** per-scroll O(n) scan plus an on-loop encode on large documents; not
catastrophic but recurs at high frequency and lands on the protocol thread (same class as
efficiency-1).

**Fix:** `bisect` the sorted token list for the overlap window; and, per efficiency-1, keep
the encode off the loop (or accept it here since the subset is small — at minimum bisect the
filter).

## efficiency-4 — Duplicated `offset_to_position` work per token in `_line_segments` (minor)

`features.py:83-106`. For a single-line token the function computes `token.start`'s column
twice — once via `offset_to_position(token.start)` (line 93, char discarded to get the line)
and again via `offset_to_position(seg_start)` where `seg_start == token.start` (line 101) —
and each call re-slices the line prefix and re-counts UTF-16 units from the line start. Across
every token in a document this is repeated O(column) work.

**Consequence:** constant-factor overhead multiplying the efficiency-1 cost on every encode;
small per token but paid for every token on every analysis.

**Fix:** compute the column once and reuse it; or track a running column cursor within the
line while walking segments, avoiding the per-call re-slice from the line start.

## Non-findings (checked, fine)

- `LineIndex` is built once per analysis on the worker (`_analyze_blocking`, `server.py:145`)
  — correct placement.
- Single-flight (`_inflight`) correctly shares one worker submission across concurrent pulls
  for the same version (each awaiter still re-runs `_store`, so two awaiters re-encode the
  same tokens — folds into efficiency-1's fix once encoding moves to the worker).
- `_GoodAnalysis` snapshots the matching `LineIndex`/tokens/encoded data, so encoding is
  memoized for `semanticTokens/full` reuse — good.
- Per-URI state (`_docs`, `_debounce`, `_inflight`) is cleaned on `drop`; no unbounded growth.
- Formatting rebuilds a `LineIndex(text)` at `server.py:325` and reparses for the verify
  guard — both real extra work, but formatting is an explicit, low-frequency (on-save)
  action, so not worth optimizing.
</content>
</invoke>
