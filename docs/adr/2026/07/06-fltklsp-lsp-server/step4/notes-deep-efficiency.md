# Deep efficiency review — step4 (M3 prefix-CST / degraded-mode serving)

Commit reviewed: dcac826..1060867

No findings.

Checked and cleared:
- Worker vs loop-thread split preserved. `_analyze_blocking` keeps the full semantic-token
  pipeline (absolute segments, stale-tail merge, delta encoding) on the worker thread; the
  new partial-analysis merge adds no loop-thread cost. Success path cost is unchanged
  (`absolute_segments` + `delta_encode_segments` == old `encode_semantic_tokens`).
- `semantic_tokens_full` serves precomputed `served.encoded` (== old precomputed
  `encoded_tokens`). `semantic_tokens_range` keeps its two-bisect + slice-encode shape at
  O(log n + k); switched to position-tuple keys, no line-index round-trips added.
- Engine partial path runs the same two tree walks (`symbols.extract` + `classify.classify`)
  the success path runs, on the smaller prefix tree — no new per-analysis walks.
- Memory neutral: `_GoodAnalysis` drops `tokens`/`encoded_tokens` for `segments` (shared by
  reference with `_ServedTokens.segments` on the complete path); merged partial segment lists
  are replaced each analysis, so no accumulation across repeated partial edits.
- `merge_stale_segments` linearly scans all stale segments, but the subsequent
  `delta_encode_segments` is already O(total segments) and both run off the protocol loop, so
  bisecting the merge would save nothing asymptotically. Not worth changing.
