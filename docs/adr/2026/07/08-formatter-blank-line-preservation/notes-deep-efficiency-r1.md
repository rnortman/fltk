# Efficiency review — formatter blank-line preservation (r1)

Commit reviewed: 5864ae1 (base ef8f727)

No findings.

Notes (non-issues, recorded for completeness):
- `pyrt.count_whitespace_newlines` and the generated `_count_newlines_in_trivia` (Python
  and Rust) run only on the `preserve_blanks > 0` path, once per inter-item trivia gap
  during on-demand formatting — not a per-render/per-request hot path. Trivia gap spans
  are tiny. The double scan of the gap text (`.isspace()` then `.count("\n")` in Python;
  `chars().all(char::is_whitespace)` then `matches('\n').count()` in Rust) is linear,
  one-time, and bounded by gap size — negligible, not worth an early-exit rewrite.
- The Python generated loop now calls the helper unconditionally (dropping the emitted
  `is_span` conditional); the helper re-does the `is_span` check internally, so per-child
  cost is unchanged. No new allocations beyond the pre-existing `extract_span_text` slice.
- No redundant I/O, no N+1, no missed concurrency, no unbounded growth, no new startup work.
