# Deep security review — Rust CST native span

Concise. Precise. Audience: smart LLM/human.
Range f8fdb53..1b54878. Trust boundary: untrusted source text parsed; PyO3 FFI; unsafe Rust.

## Scope examined
- `crates/fltk-cst-core/src/span.rs` — native `Span`/`SourceText`, byte-offset slicing.
- `src/cst_generated.rs`, `src/cst_fegen.rs` — generated PyO3 boundary (span getter/setter, child extract, the one `unsafe` block).
- Generated parser/tree code, fixtures.
- No filesystem / process / env / network access introduced anywhere in the new Rust code (grep-confirmed). No deserialization, no crypto, no auth surface. No secrets in diff.

## Findings

### security-1 — `downcast_unchecked` soundness rests on an unenforced cross-cdylib invariant
- File: `src/cst_generated.rs:30`, `src/cst_fegen.rs:30` (generated; identical block emitted per file).
- Issue: `extract_span` confirms `obj.is_instance(&fltk._native.Span)` then does
  `unsafe { obj.downcast_unchecked::<Span>() }.borrow().clone()`, reinterpreting the PyCell payload as the *locally-compiled* `fltk_cst_core::Span`. Soundness depends on the invariant that every cdylib in the process links a byte-layout-identical copy of `fltk-cst-core`'s `Span`. The comment documents this; nothing enforces it.
- Trust boundary / data flow: `obj` is an arbitrary Python object reaching the span setter / child-append path from Python-level callers (and ultimately from parsing). The `is_instance` gate is against the *Python type object* `fltk._native.Span`, not against the local `Span` Rust layout.
- Consequence: if a downstream consumer crate (the explicitly supported out-of-tree use case) links a `fltk-cst-core` whose `Span` layout differs from `fltk._native`'s — e.g. version skew between the installed `fltk._native` wheel and the consumer's pinned `fltk-cst-core` rev, or a future field add/reorder/`repr` change — then `is_instance` still passes (same registered Python class name) but `downcast_unchecked` reinterprets mismatched memory → UB (out-of-bounds `Arc` pointer deref, type confusion). Attacker leverage is low (requires controlling the build/dependency graph, not runtime input), but the failure is silent memory-unsafety rather than a clean error, and the supported multi-crate topology is exactly where skew arises.
- Suggested fix: (a) the safe path — replace `downcast_unchecked` with a checked `downcast::<Span>()` (the `is_instance` already paid the type check; checked downcast adds no meaningful cost and removes the UB cliff). If a checked downcast cannot succeed cross-cdylib (distinct type objects), then the value must be marshalled through a stable ABI (read `start`/`end`/source via the Python `text()`/getter surface and reconstruct a local `Span`) rather than reinterpreting raw memory. (b) Add a compile-time/runtime version guard (e.g. a `fltk-cst-core` ABI-version symbol checked at module init) so layout skew fails loudly at load, not as UB on first cross-cdylib span. Generator change in `gsm2tree_rs.py` preamble emission.

### security-2 (informational) — span byte-offset slicing is correctly hardened
- File: `crates/fltk-cst-core/src/span.rs:157-168` (`text_str`), `221-238` (`text`), `243-281` (`text_or_raise`), `222-238` (offset path).
- Untrusted source text is sliced by `start`/`end` byte offsets. All three paths check negative indices, `start > end`, `end > len`, and `is_char_boundary(start/end)` before `src[start..end]`. No panic path on malformed offsets; out-of-range / non-boundary → `None` or `ValueError`. This closes the panic-as-DoS and OOB-slice vectors for untrusted input. No action — recorded as the positive control for the parse-path trust boundary.

## No other findings
- `expect()` calls (`span.rs:263`; per-label `child_*` accessors) are guarded post-condition invariants, not reachable on malformed input.
- Setter (`set_span`) rejects non-`Span` via `extract_span` → `TypeError`; no silent untyped store.
- `SourceText` round-trip in the span getter copies full text per call (efficiency, not security — out of lane).
