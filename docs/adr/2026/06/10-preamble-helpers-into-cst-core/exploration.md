# Exploration: `preamble-helpers-into-cst-core`

Style: concise, precise, token-dense. No padding. Audience: decision-maker who has read the code.

---

## 1. Byte-identity claim — verified TRUE

The three independently-committed generated files contain identical preamble blocks (all lines before the first `// ─────` separator):

| File | Lines | MD5 |
|------|-------|-----|
| `src/cst_fegen.rs` | 77 | `207fcd9f189587e84e5bd2bc6c0780f1` |
| `src/cst_generated.rs` | 77 | `207fcd9f189587e84e5bd2bc6c0780f1` |
| `tests/rust_cst_fixture/src/cst.rs` | 77 | `207fcd9f189587e84e5bd2bc6c0780f1` |

`tests/rust_cst_fegen/src/cst.rs` is **not** a fourth copy — it is a 1-line `include!("../../../src/cst_fegen.rs")` (committed by c505f3c, `fegen-cst-rs-single-source`). So there are exactly **three independent committed copies** of the preamble.

The preamble block is emitted verbatim from `_preamble()` in `gsm2tree_rs.py:247-329`. The five items are:

- `static FLTK_NATIVE_SPAN_TYPE: GILOnceCell<Py<PyType>> = GILOnceCell::new();` — cache for `fltk._native.Span` type object
- `fn extract_span(py, obj) -> PyResult<Span>` — cross-cdylib Span extraction with fast/slow path; calls `get_span_type`
- `fn get_span_type(py) -> PyResult<Bound<'_, PyType>>` — loads FLTK_NATIVE_SPAN_TYPE once per cdylib
- `static FLTK_NATIVE_SOURCE_TEXT_TYPE: GILOnceCell<Py<PyType>> = GILOnceCell::new();` — cache for `fltk._native.SourceText`
- `fn get_source_text_type(py) -> PyResult<Bound<'_, PyType>>` — loads FLTK_NATIVE_SOURCE_TEXT_TYPE once per cdylib

The preamble block also includes 6 `use` items (`fltk_cst_core::Span`, pyo3 exceptions, prelude, `GILOnceCell`, `PyList`/`PyTuple`/`PyType`, `PyTypeInfo`). Those `use` items cannot be moved to `fltk-cst-core` — they are module-scope import declarations needed in each generated file's own module scope.

---

## 2. Linking model and static-per-cdylib semantics

**`fltk-cst-core` is an `rlib`** (`crates/fltk-cst-core/Cargo.toml:7`: `crate-type = ["rlib"]`). In Rust's linker model, an rlib's code is statically linked into each downstream cdylib — each cdylib receives its own private copy of every function and static from the rlib. There is no shared `.so` for an rlib; the rlib is an archive that is copied into each cdylib.

**Consequence for `static GILOnceCell<...>` items**: if `FLTK_NATIVE_SPAN_TYPE` moves into `fltk-cst-core`, each cdylib linking `fltk-cst-core` still gets its own private copy of that static at runtime. Three cdylibs → three runtime instances of `FLTK_NATIVE_SPAN_TYPE`. This is **identical to the current behavior** (each generated file has its own copy today). The "one definition at link time" in the TODO means one definition in one source location — not one runtime instance.

**This is correct and intended.** The statics cache the `fltk._native.Span` Python type object. Each cdylib correctly has its own cache: it imports the same Python type from `fltk._native` independently, and there is no need to share a Rust-level pointer across cdylib boundaries. The safety of `downcast_unchecked` (`extract_span`) depends on shared Rust type layout (same `fltk-cst-core` rlib), **not** on shared static instances.

**Precedent in `fltk-cst-core` already:** `span.rs:12` has `static SPAN_KIND_SPAN_CACHE: GILOnceCell<PyObject> = GILOnceCell::new()`, which caches `fltk.fegen.pyrt.terminalsrc.SpanKind.SPAN` in exactly the same per-cdylib-copy pattern. This proves the pattern is already in use and working.

---

## 3. Soundness of the move

Moving the five preamble items as `pub` items into `fltk-cst-core`:

**Functions** (`extract_span`, `get_span_type`, `get_source_text_type`): can be `pub fn` in `fltk-cst-core/src/lib.rs` (or a new submodule). Each cdylib links a private copy, which is correct. Generated code replaces `fn extract_span(...)` (module-local) with `fltk_cst_core::extract_span(...)`. The safety invariant in `extract_span` ("`both cdylibs link the same fltk-cst-core rlib`") is self-consistent — the helper itself lives in the shared rlib.

**Statics** (`FLTK_NATIVE_SPAN_TYPE`, `FLTK_NATIVE_SOURCE_TEXT_TYPE`): Rust `static` items cannot be re-exported across crate boundaries in a way that gives callers a reference to the same instance. If moved into `fltk-cst-core`, they would be `pub(crate)` or `pub` statics there, but each cdylib linking the rlib gets its own runtime copy — effectively private to each cdylib. The functions `get_span_type` and `get_source_text_type` access the static in the same compilation unit (the rlib). Generated code calls the function, not the static directly. The statics do NOT need to be `pub` — they can remain `pub(crate)` in `fltk-cst-core` if the accessor functions are `pub`.

**Generated files**: after the move, `_preamble()` would emit only the 6 `use` lines plus `use fltk_cst_core::{extract_span, get_span_type, get_source_text_type};`. The 5 items (statics + functions) would no longer be emitted. Bug fixes to `extract_span` (e.g. the cross-cdylib downcast logic, the error message) would propagate to all generated code without regeneration — which is the goal.

**Cross-cdylib invariant unchanged**: the safety argument in `extract_span` (`gsm2tree_rs.py:282-288`) depends on the shared rlib invariant. Moving the helper into the rlib actually **strengthens** this: the `Span` type and the extraction helper are now in the same compilation unit, making the invariant structural rather than doc-only.

---

## 4. Interaction with `span-source-as-py-crosscdylib`

`TODO(span-source-as-py-crosscdylib)` (TODO.md lines 27-33) calls for adding an `extract_source_text` helper to the generated preamble, analogous to `extract_span`. If `preamble-helpers-into-cst-core` executes first, `extract_source_text` should go into `fltk-cst-core` directly (not generated) — consistent with where `extract_span` would have just landed. If `span-source-as-py-crosscdylib` executes first, it adds a new preamble helper that `preamble-helpers-into-cst-core` must then also move. The two TODOs are logically independent but have a sequencing preference: doing `preamble-helpers-into-cst-core` first means `extract_source_text` lands in `fltk-cst-core` directly and never appears in generated code at all.

---

## 5. What the TODO overstates

The TODO says "all generated cdylibs call a single definition at link time." This is accurate only at the source/object-file level (one `.o` in the rlib). At runtime there are N separate copies in N cdylibs — not one shared function pointer. The phrase "single definition" is the conventional Rust/C meaning (one definition to link against, vs. N copied inline definitions), but it does not mean a shared runtime symbol. For `GILOnceCell` statics specifically: N runtime copies is correct behavior, not a limitation. The TODO's goal (bug propagation without regeneration) is fully achieved regardless.

---

## 6. The `use` items: not moveable

The six `use` statements in the preamble (`use fltk_cst_core::Span; use pyo3::exceptions::{...}; use pyo3::prelude::*; use pyo3::sync::GILOnceCell; use pyo3::types::{...}; use pyo3::PyTypeInfo;`) must remain in each generated file. After the move, the generated file still needs `use pyo3::...` for all pyo3 items used in the node structs and pymethods (which are in the generated file, not `fltk-cst-core`). Only `use pyo3::sync::GILOnceCell;` might be droppable if the statics move out. `use fltk_cst_core::Span;` stays. The `use` reduction is minor.

---

## 7. No blocker, no papering over

The TODO is sound. The cross-cdylib design (per-cdylib GILOnceCell copy, downcast_unchecked on shared-rlib-layout invariant) is unchanged by the move. The existing `SPAN_KIND_SPAN_CACHE` static in `fltk-cst-core` proves this pattern works. Moving the five items reduces the diff-surface for bug fixes and eliminates the three-file duplication. There are no hidden blockers.

The only caveat: statics (`FLTK_NATIVE_SPAN_TYPE`, `FLTK_NATIVE_SOURCE_TEXT_TYPE`) should be `pub(crate)` in `fltk-cst-core` (not `pub`), since external callers should not reference them directly — only through the `pub fn` accessors. If made `pub`, they appear in `fltk-cst-core`'s public API, which is misleading (callers get a reference to the rlib-static copy in their cdylib, not a shared instance).

---

## 8. Current file/line ground truth

- Generator: `fltk/fegen/gsm2tree_rs.py:247-329` (`_preamble()`, including the TODO comment at 248-251 and the five items at 253-328)
- Generated copies: `src/cst_fegen.rs:1-77`, `src/cst_generated.rs:1-77`, `tests/rust_cst_fixture/src/cst.rs:1-77`
- Existing precedent: `crates/fltk-cst-core/src/span.rs:12` (`SPAN_KIND_SPAN_CACHE`)
- Target location: `crates/fltk-cst-core/src/lib.rs` (currently only `mod span; pub use span::{SourceText, Span};`)
- Related TODO: `span-source-as-py-crosscdylib` at `crates/fltk-cst-core/src/span.rs:148` and `fltk/fegen/gsm2tree_rs.py` (preamble emission)
