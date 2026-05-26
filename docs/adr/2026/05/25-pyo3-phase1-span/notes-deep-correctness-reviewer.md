# Deep Correctness Review — Phase 1 Span

Commit reviewed: 90074aa (base 6121025). Scope: logic/control/data flow only.
Build + all 88 span tests pass. Behaviors below probed empirically on both backends.

## correctness-1 — `intersect` lacks the cross-source guard that `merge` enforces
`src/span.rs:140-153`, `fltk/fegen/pyrt/terminalsrc.py:50-56`.

`merge` raises `ValueError` when the two operands carry different sources
(`src/span.rs:124-131`; `terminalsrc.py:44-46`). `intersect` performs no such
check. When two source-bearing spans from *different* documents are intersected,
both backends silently keep `self`'s source (`or_else(other)` / `self._source if
... else other._source`) and return a span whose `text()` slices `self`'s source
at the intersected indices.

Why this is wrong: the same invariant `merge` protects — "spans from different
documents must not combine" (design line 270) — is violated by `intersect`. The
result is a span that claims to describe a region but whose `text()` is drawn from
an unrelated document.

Consequence: `Span.with_source(0,5,"hello").intersect(Span.with_source(3,8,"world"))`
returns a span with `text() == "lo"` (verified, both backends) — text from "hello"
labeled as the overlap of two spans where one was measured against "world". Any
future caller that intersects spans tracked against distinct sources gets silently
wrong text instead of the error `merge` would have raised. Latent now (Phase 1
emits no source-bearing spans on the parse path) but the capability is shipped and
tested, so callers will rely on it.

Suggested fix: mirror the `merge` source-compatibility check in `intersect` —
raise `ValueError` when both operands have sources and they are not identical
(`Arc::ptr_eq` / `is`). Decide deliberately whether disjoint-but-different-source
should raise or return `None`; raising is consistent with `merge`.

## correctness-2 — `merge`/`intersect` source identity diverges between backends due to Python string interning
`fltk/fegen/pyrt/terminalsrc.py:44`, `src/span.rs:125`.

Python detects "different sources" with `self._source is not other._source`
(object identity). Rust uses `Arc::ptr_eq`. These are *intended* to be the same
(identity), but they are not equivalent in practice: CPython interns equal string
literals and constant-folds concatenations, so two Python spans built from
same-content sources frequently share one `str` object and `merge` succeeds; two
`SourceText("hello")` handles in Rust are always distinct `Arc`s and `merge`
raises.

Why this matters: identical user code merging two spans whose sources have the same
text succeeds on the Python backend and raises `ValueError` on the Rust backend
(content-dependent and interning-dependent — fragile even within Python). The test
suite hides this: `test_span.py:142` uses different content ("hello" vs "world")
while `test_rust_span.py:172` uses same content with two `SourceText` handles, so
each backend exercises only the case that passes for it.

Consequence: cross-backend behavioral inconsistency on the merge/source-mismatch
path; a parse pipeline that swaps the Rust backend in (the stated Phase 1 goal)
can start raising on merges that previously succeeded, or vice versa. The design
("merge spans from different documents is a bug", line 270) wants identity
semantics; CPython interning means the Python backend cannot reliably distinguish
"same document" from "two documents that happen to contain equal text."

Note: design-level concern, partly acknowledged under "Hash values differ between
backends" but the interning interaction for `merge`/`intersect` identity is not
called out. Flagging because the two backends are explicitly meant to be swappable.

Suggested fix: out of pure-correctness scope to redesign, but the divergence should
be a conscious decision. Options: document that source identity is backend-defined,
or have the Python backend wrap sources in an identity-bearing handle (mirroring
`SourceText`) so `is` is meaningful regardless of interning.

## Checked, no finding
- Rust `text()` reorders the negative-index guard before the `as usize` cast
  (lines 80-87), unlike the design snippet which casts first — implementation is
  correct, design snippet would have wrapped negatives to huge `usize`.
- `text()` bounds: empty span at valid offset → `""`; empty span beyond `len` →
  `None`; both backends agree (verified).
- Mixed-sign indices, sentinel `merge`/`intersect`, char-boundary rejection,
  eq/hash excluding source: all consistent across backends.
- `len()` i64 subtraction guarded by `start<0`/`end<0`; no realistic overflow.
- `UnknownSpan` constructed via struct literal in `lib.rs:27-31` with
  `start:-1,end:-1` — matches `Span(-1,-1)`; equality holds (verified).
