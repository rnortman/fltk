# Deep Security Review — pyo3-phase1-span

Commit reviewed: 90074aa (base 6121025).
Scope: `src/span.rs`, `src/lib.rs`, `fltk/fegen/pyrt/{span.py,span_protocol.py,terminalsrc.py}`, tests.

Note: this is a parser/compiler library. No network, FS, subprocess, deserialization, auth, or template surface in the diff. The only memory-safety-relevant code is the Rust string indexing in `Span::text` and the `i64 -> usize` casts. Those are reviewed below.

## Findings

No findings.

### Reviewed, found safe

- **`src/span.rs:78-96` `Span::text` — string slicing.** `start`/`end` are `i64` from Python (untrusted: `Span(start, end)` / `with_source` take arbitrary ints). Slice `src[start..end]` is reached only after: `start < 0 || end < 0` guard, `start > end` guard, `end > src.len()` guard, and `is_char_boundary(start) && is_char_boundary(end)` guard. No `unsafe`. Out-of-range or mid-codepoint indices return `None` rather than panicking. Slicing is sound. No DoS beyond an O(n) copy bounded by source length.
- **`src/span.rs:83-84,111-115` `i64 as usize` casts.** Cast occurs only after the `< 0` guard, so no negative-to-huge wraparound feeds the bounds check. `len()` returns 0 for negative indices; otherwise `(end-start).max(0)`.
- **`src/span.rs:122-138` `merge` / `:140-153` `intersect`.** Source-identity check uses `Arc::ptr_eq` (correct: merging spans from different source buffers raises). No memory issue; sentinel/negative inputs produce odd spans but cannot violate safety (text() re-guards).
- **`fltk/fegen/pyrt/terminalsrc.py:15-23` Python `text`.** Bounds-guarded; Python slicing is memory-safe regardless. `merge` source-identity via `is` matches Rust `ptr_eq` semantics.
- **`src/lib.rs:27-32` `UnknownSpan`.** Module-level `Span(-1,-1)` constant; no exposed mutation (`#[pyclass(frozen)]`).
- **Secrets / info leak.** `__repr__` and Python `repr` (`_source` has `repr=False`) emit only `start`/`end`, never source text. No secrets in diff.
- **`SourceText::new`** copies `&str` into an `Arc<SourceInner>`; immutable, `Send + Sync`. No aliasing of Python-owned memory.
