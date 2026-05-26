# Efficiency Review — Phase 1 Span (commit 90074aa, base 6121025)

Scope: `git diff 6121025..90074aa`. Diff is additive: Python `Span` methods/`_source` field, Rust `Span`/`SourceText`, protocol/selector modules, tests.

## efficiency-1
File: `fltk/fegen/pyrt/terminalsrc.py:13` (`_source` slot added to `Span`)

Problem: `Span` is constructed ~80x per parse and stored both as a node field and as a leaf child in `children` lists. Adding a third `slots` field grows every Span instance by one pointer (8 bytes) and adds a third assignment in the generated `__init__`, for every span in every parse — even though no Phase 1 parse path ever sets `_source` (design line 183: "No production parse path emits source-bearing spans in this phase").

Consequence: Per-parse memory and allocation cost on the hottest object in the parser, paid universally for a capability nothing currently uses. On large inputs with many CST nodes this is a constant-factor tax on the whole parse. Magnitude is small (one slot + one `None` store per span); it is the unconditional, zero-current-benefit nature that flags it.

Direction: Acceptable as-is given the design explicitly defers wiring and the cost is one pointer/store per span. No change required if the team accepts the tax now to avoid a layout change later. If parse-time footprint matters, the field is the minimal possible form already (`None` default, no wrapper object on the Python side). No action beyond awareness.

## efficiency-2
File: `fltk/fegen/pyrt/terminalsrc.py:43-48` (`merge`)

Problem: `merge` calls `min(self.start, other.start)` and `max(self.end, other.end)` — two builtin `min`/`max` calls with the function-call overhead, plus a 3-field positional `Span(...)` construct. Not a hot path in Phase 1 (no caller wires it), so cost is latent.

Consequence: None today — `merge`/`intersect` have no production callers in this phase. Flagged only so it is on record: if a future phase calls `merge` inside a per-node fold (e.g. computing enclosing spans bottom-up over the CST), the `min`/`max` builtin overhead per node becomes per-node hot-path cost. Inline comparisons (`a if a < b else b`) avoid the builtin dispatch.

Direction: Leave as-is for Phase 1. Revisit only if a future phase puts `merge` in a per-node loop.

## efficiency-3 — non-finding (verified clean)
- `text()` (both backends): early-returns on sourceless/invalid before any slice. No redundant work. Rust slices UTF-8 by byte index O(1) with a char-boundary guard — no O(N) codepoint conversion (design line 564 confirms the old O(N) `is_ascii`/char-index path was intentionally eliminated). Good.
- Backend selection (`span.py`, `span_protocol.py`): import-time only, runs once. Not per-request.
- `SourceText` copies the Python `str` into UTF-8 once per construction — unavoidable at the boundary (Python str is not UTF-8), one-time per parse, shared via `Arc` across all spans. Correct design.
- No new file reads, no new concurrency opportunities, no polling loops, no existence-checks, no unbounded structures introduced by this diff.
- `re.compile(regex)` in `consume_regex` (terminalsrc.py:89) recompiles per call and is NOT cached, but it is preexisting code (not in this diff) — out of lane.

## Summary
No blocking efficiency issues in the Phase 1 diff. efficiency-1 is the only real-cost item (per-span memory/init tax for a deferred capability) and is a deliberate, accepted design tradeoff. efficiency-2 is a latent note for future phases.

Note for downstream readers: concise/precise, no padding — findings only.
