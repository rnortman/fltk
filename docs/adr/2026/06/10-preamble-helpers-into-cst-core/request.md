# Request: preamble-helpers-into-cst-core

Style: concise, precise, no padding, no preamble-the-other-kind. Self-contained — downstream agents do not see the triage conversation.

**Type**: refactor of generated-code emission + shared crate. Behavior-preserving. Treat this request as the requirements doc; a design doc is warranted (touches an unsafe invariant and the generator) but the shape is validated.

## Background

`_preamble()` in `fltk/fegen/gsm2tree_rs.py:247-329` emits five items byte-for-byte identically (MD5-verified `207fcd9f…`) into all three independently committed generated files (`src/cst_fegen.rs:1-77`, `src/cst_generated.rs:1-77`, `tests/rust_cst_fixture/src/cst.rs:1-77`; `tests/rust_cst_fegen/src/cst.rs` is an `include!` of the first, not a fourth copy):

- `static FLTK_NATIVE_SPAN_TYPE: GILOnceCell<Py<PyType>>`
- `fn extract_span(py, obj) -> PyResult<Span>` — contains `unsafe { downcast_unchecked }` justified by the shared-rlib invariant
- `fn get_span_type(py) -> PyResult<Bound<'_, PyType>>`
- `static FLTK_NATIVE_SOURCE_TEXT_TYPE: GILOnceCell<Py<PyType>>`
- `fn get_source_text_type(py) -> PyResult<Bound<'_, PyType>>`

Any bug fix (these include unsafe code) currently propagates only by regenerating every consumer's generated code — out-of-tree consumers included. FLTK's generated output is public API for out-of-tree consumers; regeneration-as-fix-path is the worst case for them.

Validation facts (see `exploration.md` in this dir — read it; it settles the soundness questions):

- `fltk-cst-core` is `crate-type = ["rlib"]` (`crates/fltk-cst-core/Cargo.toml:7`). Each downstream cdylib statically links its own copy of rlib code and statics. Per-cdylib `GILOnceCell` copies are **correct and intended** — each cdylib independently caches the same `fltk._native` Python type objects. Precedent already in the crate: `SPAN_KIND_SPAN_CACHE` at `crates/fltk-cst-core/src/span.rs:12`.
- Moving `extract_span` into the rlib *strengthens* the shared-rlib safety invariant (helper and `Span` type in the same compilation unit).
- The six `use` lines in the preamble stay in generated files (module-scope imports for the rest of the generated code); only `use pyo3::sync::GILOnceCell;` may become droppable.

## Direction (decided at triage — do not second-guess)

- Move the three functions into `fltk-cst-core` as `pub fn` (`crates/fltk-cst-core/src/lib.rs` currently only has `mod span; pub use span::{SourceText, Span};` — a new submodule is fine). The two statics move too but stay `pub(crate)`: external code must go through the accessor functions; a `pub` static would misleadingly suggest a shared runtime instance.
- Preserve the safety-comment content on `extract_span` (the shared-rlib invariant documentation, currently emitted from `gsm2tree_rs.py:282-294`).
- Shrink `_preamble()` to emit only the needed `use` lines, including importing the moved helpers from `fltk_cst_core`.
- Regenerate all three generated files via the standard `make gencode` path, then `make fix` (generated code is not expected to be format-clean straight out of the generator; regen → `make fix` → commit is the intended flow).
- Remove the `TODO(preamble-helpers-into-cst-core)` comment (`gsm2tree_rs.py:248-251`) and the `TODO.md` entry.

## Constraints / non-goals

- Behavior-preserving: no change to any Python-visible semantics. Cross-cdylib extraction must work exactly as before (the fixture crate tests exercise this).
- Do NOT add an `extract_source_text` helper or touch the span-getter double-copy pattern — that is `span-source-as-py-crosscdylib`, sequenced after this and deliberately out of scope here.
- Public API additions to `fltk-cst-core` limited to the three functions. Statics stay crate-private.
- Out-of-tree consumers regenerate on their own schedule; old generated code (with inline helpers) must keep compiling against the new `fltk-cst-core`. Verify nothing moved breaks that (the inline copies don't reference crate internals, so they should be unaffected — confirm).

## Verification

- TDD where it applies: the existing cross-cdylib tests (`tests/test_phase4_rust_fixture.py`, fixture crate) are the contract; they must pass before and after.
- `uv run --group dev maturin develop` then `uv run pytest` green; `cargo test` for the crates if present; `uv run ruff check . && uv run pyright` clean.
- `make gencode` idempotent after the change (`git diff` empty on second run).
- Generated preamble in all three files no longer contains the five items; `grep -c 'fn extract_span' src/cst_fegen.rs` = 0; helpers exist once in `fltk-cst-core`.
- `grep -rn 'preamble-helpers-into-cst-core'` returns nothing.
