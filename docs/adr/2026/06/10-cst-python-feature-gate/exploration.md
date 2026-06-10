# Exploration: cst-python-feature-gate

Concise, precise, no padding. Audience: smart LLM/human implementing this ADR.

---

## Code surface

### fltk-cst-core (`crates/fltk-cst-core/`)

`Cargo.toml:14-15` — single dependency: `pyo3 = { version = "0.23", features = ["abi3-py310"] }`, unconditional. `crate-type = ["rlib"]`.

`src/lib.rs:1-5` — re-exports `cross_cdylib::{extract_source_text, extract_span, get_source_text_type, get_span_type, span_to_pyobject}` and `span::{SourceText, Span}`. All five cross-cdylib symbols are pyo3-entangled (GIL required).

`src/span.rs` — entire file is pyo3-entangled:
- `Span`: `#[pyclass(frozen, eq, hash)]` at line 93; `#[pymethods]` block at line 204 (Python constructors `py_new`/`with_source`/`_with_source_unchecked`, getters `get_start`/`get_end`, `text`/`text_or_raise`/`has_source`/`len`/`is_empty`/`merge`/`intersect`/`__repr__`/`kind`).
- `SourceText`: `#[pyclass(frozen)]` at line 30; `#[pymethods]` at line 49 (Python `new`, `_fltk_cst_core_abi` classattr).
- `SourceInner` (line 21) and all native methods on `Span` (`unknown`, `new_sourceless`, `new_with_source`, `start`, `end`, `source_as_py`, `source_full_text_str`) and on `SourceText` (`from_str`) are pure Rust and do not require pyo3.
- `SPAN_KIND_SPAN_CACHE: GILOnceCell<PyObject>` at line 13 — pyo3 only.
- `coerce_source` (line 194) returns `PyResult<Option<Arc<SourceInner>>>` — only because `merge`/`intersect` are `#[pymethods]`; the logic itself is pure Rust.

`src/cross_cdylib.rs` — entirely pyo3:
- `extract_source_text`, `extract_span`, `span_to_pyobject`, `get_span_type`, `get_source_text_type`.
- `FLTK_CST_CORE_ABI` constant (line 22) — pure Rust, safe to retain in python-off mode.
- Two `GILOnceCell` statics (`FLTK_NATIVE_SPAN_TYPE`, `FLTK_NATIVE_SOURCE_TEXT_TYPE`) — pyo3 only.
- All `unsafe` is in this file (`downcast_unchecked` in `extract_source_text:68` and `extract_span:169`).

`src/lib.rs` (tests) — pure-Rust tests already exist at lines 17–55, calling `Span::unknown()`, `Span::new_sourceless`, `Span::new_with_source`, `SourceText::from_str`, and `==`. These tests work today because pyo3's `#[pyclass]` macro compiles even without a live Python runtime — the issue is runtime cost and linkage, not compilability under the current unconditional `pyo3` dep.

### Generated CST files (`src/cst_fegen.rs`, `src/cst_generated.rs`, `tests/rust_cst_fixture/src/cst.rs`)

Pattern is identical across all three (generator: `fltk/fegen/gsm2tree_rs.py`).

**Preamble** (`_preamble()`, line 245):
```rust
use fltk_cst_core::{extract_span, get_span_type, span_to_pyobject, Span};
use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyList, PyTuple, PyType};
use pyo3::PyTypeInfo;
```
All five imports from fltk-cst-core and all pyo3 imports are required only when `python` feature is on.

**Per-node pyo3 surface** (for each rule/class):
- `NodeKind` enum: `#[pyclass(frozen, name = "NodeKind")]` + `#[pymethods]` with `__repr__`, `_fltk_canonical_name`, `__eq__`, `__hash__`.
- `<Class>_Label` enum: same pattern.
- `<Class>Child` enum: `to_pyobject(py)` and `extract_from_pyobject(py, obj, span_type)` methods — both pyo3-only.
- `<Class>` struct: `#[pyclass]` attribute; `#[pymethods]` block with `new`, `span` getter/setter, `kind`, `Label`, `children`, `append`, `extend`, `extend_children`, `child`, per-label quintets (`append_<l>`, `extend_<l>`, `children_<l>`, `child_<l>`, `maybe_<l>`), `__eq__`, `__hash__`, `__repr__`.
- `register_classes` fn — pyo3-only.

**Pure-Rust surface already present** (no pyo3 needed):
- `<Class>::new_native(span: Span) -> Self`
- `<Class>::span_native(&self) -> &Span`
- `<Class>::children_native(&self) -> &[(Option<Class_Label>, ClassChild)]`
- `<Class>::push_child_native(&mut self, label, child)`
- `PartialEq for <Class>` (structural: span + children)
- `PartialEq for <Class>Child`
- `Clone for <Class>` and `#[derive(Clone)]` on `<Class>Child`
- `<Class>_Label`: `#[derive(Clone, PartialEq, Eq, Hash)]` — pure Rust derives.
- `NodeKind`: same derives.

The `<Class>Child::to_pyobject` and `extract_from_pyobject` methods are the only non-trivial code in child enums; the data-carrying variants (`<Class>Child::Span(Span)`, `<Class>Child::<ChildName>(Box<ChildName>)`) are plain Rust.

### `tests/rust_cst_fixture/src/native_tests.rs`

Tests at lines 1–113 exercise `new_native`/`push_child_native`/`span_native`/`children_native` and structural equality with **no GIL calls**. Comment at line 6: "No `Python::with_gil`, no `pyo3::Python`, no interpreter init anywhere in this file." These are the model for what the spike crate must do.

### Root `Cargo.toml`

`Cargo.toml:8-15` — workspace members: `[".","crates/fltk-cst-core"]`. The two test crates (`tests/rust_cst_fixture`, `tests/rust_cst_fegen`) are **excluded** from the workspace (each has its own `[workspace]` declaration). The feature gate work lives in the workspace.

### CI (`.github/workflows/ci.yml`)

Steps: `make build-native build-test-user-ext build-fegen-rust-cst`, then `make check`. `make check` runs: `lint`, `format-check`, `typecheck`, `test`, `cargo-check`, `cargo-clippy`, `cargo-test` in sequence. `cargo-test` runs `cargo test -q` (workspace only — fixture crates excluded). No python-off cargo build/test step exists today.

### Generator (`fltk/fegen/gsm2tree_rs.py`)

`RustCstGenerator.generate()` at line 222 — produces a single `.rs` file string via `_preamble()` + `_node_kind_block()` + per-rule (`_label_enum_block`, `_child_enum_block`, `_node_block`) + `_register_classes_fn()`.

`_preamble()` line 244 — hardcodes all pyo3 imports. This is the single generator change point for preamble gating.

Every `#[pyclass]`, `#[pymethods]`, `#[pyo3(...)]`, `#[getter]`, `#[setter]`, `#[new]`, `#[classattr]`, `#[derive(…)]` annotation is emitted unconditionally. `register_classes` is also emitted unconditionally.

---

## Schemas/contracts

### `Span` struct layout (`src/span.rs:95-99`)
```rust
pub struct Span {
    pub(crate) start: i64,
    pub(crate) end: i64,
    pub(crate) source: Option<Arc<SourceInner>>,
}
```
24 bytes on 64-bit. `PartialEq`/`Hash` use only `(start, end)`. Source-bearing and sourceless spans at same offsets compare equal.

### `SourceText` struct layout (`src/span.rs:31-33`)
```rust
pub struct SourceText {
    pub inner: Arc<SourceInner>,
}
```

### `SourceInner` (`src/span.rs:21-23`)
```rust
pub struct SourceInner {
    pub(crate) text: String,
}
```

### Generated node struct layout (all grammars)
```rust
pub struct <ClassName> {
    span: Span,
    children: Vec<(Option<<ClassName>_Label>, <ClassName>Child)>,
}
```
No pyo3 types in the struct fields — `PyCell` wrapping happens at the pyo3 boundary, not in the stored data.

### fltk-cst-core `Cargo.toml` feature table
None currently defined. Adding `[features] python = ["pyo3/..."]` is the first change required.

---

## Invariants/constraints

1. **`cross_cdylib.rs` is the sole location of `unsafe`** in the entire codebase. Gating the file under `#[cfg(feature = "python")]` structurally eliminates all unsafe from python-off builds. The only `unsafe` calls: `obj.downcast_unchecked::<SourceText>()` at `cross_cdylib.rs:68` and `obj.downcast_unchecked::<Span>()` at `cross_cdylib.rs:169`.

2. **`Span::coerce_source` returns `PyResult`** (`src/span.rs:194`) only because `merge` and `intersect` are `#[pymethods]` — the error path uses `PyValueError`. In python-off mode, these methods need a different error type (`Result<_, String>` or a plain error enum), or `coerce_source` must be split into a native version returning `Option`/`Result` and a python wrapper.

3. **`GILOnceCell` statics** — `SPAN_KIND_SPAN_CACHE` (`span.rs:13`), `FLTK_NATIVE_SPAN_TYPE` (`cross_cdylib.rs:143`), `FLTK_NATIVE_SOURCE_TEXT_TYPE` (`cross_cdylib.rs:200`) — all pyo3-only; they must be excluded with the feature.

4. **`source_as_py` returns `PyResult<Option<Py<SourceText>>>`** (`span.rs:165`) — pyo3-only, called only by `span_to_pyobject` in `cross_cdylib.rs`. In python-off mode, source access is `span.source.as_ref().map(|arc| arc.text.as_str())` (or similar) with no pyo3 allocation.

5. **`kind` getter on `Span`** (`span.rs:418`) imports `fltk.fegen.pyrt.terminalsrc` at runtime. This is a Python-only operation; it must be gated.

6. **`register_classes` in generated files** — emitted by `_register_classes_fn()` (generator line 916) — exclusively calls pyo3 `module.add_class`. Must be gated or absent in python-off mode.

7. **`NodeKind` and `<Class>_Label` need Python-facing `#[pyclass]`/`#[pymethods]`** only in python-on mode. Their `#[derive(Clone, PartialEq, Eq, Hash)]` is required in both modes.

8. **Existing `native_tests.rs` tests** (`tests/rust_cst_fixture`) already pass with no GIL today because pyo3 `#[pyclass]` compiles even without a Python runtime being initialized. They do NOT currently test building without the pyo3 dependency at all.

9. **fltk-cst-core `crate-type = ["rlib"]`** — can gain a feature gate on pyo3 without touching crate-type. Downstream cdylib crates (`fltk-native`, `phase4-roundtrip-cst`, `fegen-rust-cst`) each have their own `extension-module` feature that activates `pyo3/extension-module`; they also specify `default-features = false` on their fltk-cst-core dep (`Cargo.toml:20` in fixture). In python-off mode the spike crate would not depend on pyo3 at all.

10. **`Makefile` `cargo-test` target** runs `cargo test -q` — this only covers the workspace (`fltk-native` + `fltk-cst-core`). The fixture crates (`tests/rust_cst_fixture`, `tests/rust_cst_fegen`) are not workspace members and are not covered.

---

## Design decisions needed

### A. Feature name and polarity

Two idiomatic choices:
- `python` (default-on): `[features] python = ["pyo3/abi3-py310"] default = ["python"]`. Additive Cargo convention; off = `--no-default-features`. Clearest intent.
- `no-python` or `pure-rust` (default-off): less idiomatic; Cargo discourages negative-sense features.

**Recommendation by convention**: `python`, default-on.

### B. Gating mechanism for fltk-cst-core

In `span.rs`, `cross_cdylib.rs`, and `lib.rs`, the split is clean:

- `SourceInner`, `SourceText::from_str`, all native `Span` methods, `Span` struct definition, `PartialEq`/`Hash`/`Clone` impls — **python-off safe**.
- `#[pyclass]`/`#[pymethods]` blocks, `GILOnceCell` statics, `source_as_py`, `kind` getter — **python-only**.
- `cross_cdylib.rs` entirely — **python-only**.

Approach: wrap `use pyo3::...` imports and all `#[pyclass]`/`#[pymethods]`/`GILOnceCell` items in `#[cfg(feature = "python")]`. In `lib.rs`: gate the re-exports of `cross_cdylib::*` and the import of `cross_cdylib` itself.

`coerce_source` in `span.rs:194` returns `PyResult` — needs a separate native version (returning e.g. `Result<Option<Arc<SourceInner>>, String>`) for use by native `merge`/`intersect` equivalents in python-off mode, while the python-on `#[pymethods]` `merge`/`intersect` call the `PyResult`-returning wrapper.

### C. Gating mechanism for generated code

Two viable approaches:

**C1. Single-output with `#[cfg(feature = "python")]` guards** — generator emits cfg-gated annotations around pyo3 surface in the same file. Advantages: one file, one regen step. Disadvantages: significantly complicates the generator (every `#[pyclass]`, `#[pymethods]`, preamble import, per-method signature change). `#[pymethods]` blocks cannot be split; the entire `impl` block must be gated, so each node has two `impl` blocks — one unconditional (native methods) and one `#[cfg(feature = "python")] #[pymethods]`.

**C2. Dual-output mode** — generator emits two variants when requested, or always emits a shared-native section plus a python section. Out-of-tree consumers would need both for their default (python-on) builds.

C1 is preferred for its single-file simplicity. The generator needs:
- Conditional preamble: emit pyo3 imports inside `#[cfg(feature = "python")]` or as a module-level `#[cfg(feature = "python")] use pyo3::...;` (latter is cleaner).
- The native `impl` block (already emitted) stays unconditional.
- The `#[pymethods] impl` block is wrapped in `#[cfg(feature = "python")]`.
- `NodeKind` and `<Class>_Label` struct definitions keep `#[derive(Clone, PartialEq, Eq, Hash)]` unconditionally; the `#[pyclass]`/`#[pymethods]` attributes and blocks are gated.
- `register_classes` fn is gated.
- `<Class>Child::to_pyobject` and `extract_from_pyobject` are gated (the entire `impl <Class>Child` block containing them is python-only; the enum definition and PartialEq/Clone are not).

### D. Spike crate location

Options:
- New workspace member: `crates/fltk-cst-spike/` — stays in `cargo test` coverage.
- New standalone crate outside workspace (like the fixture crates): not in `cargo test` without Makefile/CI additions.
- `#[cfg(test)] mod pure_rust_spike;` in `fltk-cst-core` — test-only, cleaner, auto-covered by `cargo test`.

The request says "a test crate (or `cargo test` target)." A `#[cfg(test)]` module in `fltk-cst-core` (with `#[cfg(not(feature = "python"))]` guard) is the simplest option and is auto-covered by the workspace `cargo test --no-default-features`. A separate new workspace crate (`crates/fltk-cst-core-spike` or similar) is cleaner for `#![forbid(unsafe_code)]` declaration. Either works.

The spike must use `cst_generated.rs` nodes (PoC grammar: `Identifier`, `Items`, `Trivia`) or the phase4 fixture nodes (`Entry`, `Identifier`, `Operator`, `Literal`, `Trivia`). Because generated files live in `src/` (the `fltk-native` cdylib), the spike can't import them directly from another crate without them being exported. Options:
- Run a separate `gen-rust-cst` step for the spike crate, generating a dedicated `cst.rs` from `poc_grammar.fltkg` (same as `src/cst_generated.rs` but in a new crate).
- Move the PoC or phase4 grammar's generated output into a `fltk-cst-poc` rlib crate in the workspace, then have both `fltk-native` and the spike depend on it.

The second option is architecturally cleaner (one generated file, two consumers). The first is simpler to implement and matches what `tests/rust_cst_fixture` already does.

### E. `#![forbid(unsafe_code)]` placement

On the spike crate or module, not on `fltk-cst-core` itself (which still contains `unsafe` in `cross_cdylib.rs` for python-on mode). The CI step that runs `--no-default-features` on the spike validates structural exclusion.

### F. Verifying "no pyo3 in dependency graph"

`cargo tree --no-default-features -p <spike-crate> | grep pyo3` — expected: no output. Can be added as a CI `--no-default-features` check step.

---

## Open factual questions

1. `Span::merge` and `Span::intersect` return `PyResult` today. In python-off mode, what error type should the native equivalents return? (`Result<Span, String>`, `Option<Span>` for intersect, or a custom error type?) — needs a decision before design is final.

2. `Span::text` and `Span::text_or_raise` are currently `#[pymethods]` only. Should they be exposed as pure-Rust fns in python-off mode? (The spike needs `span.text()` to "read span text" as required by the request.) — yes, they should; `text()` is pure Rust logic wrapped in a pymethods block solely for Python visibility.

3. Does the spike crate live inside the workspace (new `crates/` member) or as a `#[cfg(test)]` module inside `fltk-cst-core`? — affects Makefile/CI integration.

4. `<Class>Child` in python-off mode has no `to_pyobject`/`extract_from_pyobject`. The PoC grammar's `Identifier`/`Items`/`Trivia` nodes are already usable via native API. But `Items` has a `Span` child variant (`ItemsChild::Span`): in python-off mode the `Span` variant is available as a plain Rust `Span` without any Python wrapping — this is the desired behavior and requires no special handling.

5. Should `Span::kind` (which imports `fltk.fegen.pyrt.terminalsrc`) have a native equivalent? The spike does not require it (`kind` is a Python-side discriminant), but it may be needed for completeness of the Python-on feature parity check.
