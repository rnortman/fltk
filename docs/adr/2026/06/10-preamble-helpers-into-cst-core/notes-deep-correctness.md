# Deep correctness review — preamble-helpers-into-cst-core

Commit reviewed: 5e29293 (base 87bf19e).

No findings.

Verification performed:
- `crates/fltk-cst-core/src/cross_cdylib.rs` is byte-identical to the removed preamble block except the specified visibility changes (`pub fn` x3, `pub(crate) static` x2) and module-local imports; SAFETY/INVARIANT comment preserved verbatim.
- Regenerated all three Rust CST files from grammars; `diff` against committed `src/cst_fegen.rs`, `src/cst_generated.rs`, `tests/rust_cst_fixture/src/cst.rs` is empty (gencode idempotency holds; the `.pyi` raw-vs-committed diff is the intended ruff-normalization flow, not drift).
- All three imported helpers (`extract_span`, `get_span_type`, `get_source_text_type`) have call sites in every committed generated file; no leftover `GILOnceCell`/`FLTK_NATIVE_*`/`py.import("fltk._native")`/local `fn` definitions in generated bodies.
- `cargo check` clean (no warnings): fltk-cst-core, workspace (fltk-native), rust_cst_fixture, rust_cst_fegen (`include!` shim unchanged).
- No external module-path references to the previously-private helpers (`grep` across src/ and fixture crates).
- `uv run pytest tests/test_gsm2tree_rs.py fltk/fegen/test_genparser.py` → 122 passed; rebuilt all three extensions via `maturin develop`, `tests/test_phase4_rust_fixture.py` → 40 passed (cross-cdylib `extract_span` exercised at runtime, unchanged tests).
- Per-cdylib `GILOnceCell` static duplication semantics unchanged (rlib statically linked into each cdylib, same as before the move).
- TODO slug removed from both join points (`TODO.md` and code comment); `span.rs` TODO wording update is doc-only.
