# Phase 2 Implementation Log

## Increment 1 — Rust implementation: cst_poc.rs + lib.rs registration (commit b043a0c)

- `src/cst_poc.rs` (new, 627 lines): `Identifier_Label` and `Items_Label` enums with `#[pyclass(eq, hash, frozen)]`, `__repr__`; `Identifier` and `Items` structs with `#[pyo3(get, set)]` span, `#[pyo3(get)]` children (`Py<PyList>`), `#[new]` with keyword-only `span` defaulting to `UnknownSpan` via runtime import, `#[classattr] Label` returning the label type object, generic `append`/`extend`/`child`, per-label methods (`append_<label>`, `extend_<label>`, `children_<label>`, `child_<label>`, `maybe_<label>`), `__eq__`/`__hash__`/`__repr__`.
- `src/lib.rs`: Added `mod cst_poc;` and registered `Identifier_Label`, `Identifier`, `Items_Label`, `Items` via `m.add_class::<T>()`.
- Deviation: design showed `#[classattr]` returning `Py<PyType>` but `Py<T>::type_object` is a trait method needing `use pyo3::PyTypeInfo`. Shipped returning `PyObject` via `.into_any().unbind()` — same runtime behavior, simpler type. `#[allow(non_camel_case_types)]` and `#[allow(non_snake_case)]` added for intentional naming (`Identifier_Label`, `Label` method). `bool.into_pyobject(py)` returns `Borrowed` not `Bound`; fixed with `.to_owned()` before `.unbind()`.
- All 453 existing tests pass.

## Increment 2 — Test file: tests/test_rust_cst_poc.py (commit f5ce817)

- `tests/test_rust_cst_poc.py` (new, 44 tests): All 27 ACs covered, organized into 10 test classes matching the design's test plan: `TestLabelSemantics` (AC-1–5), `TestChildrenListSemantics` (AC-6–8), `TestAppendAndAccessors` (AC-9–15), `TestGenericMethods` (AC-16–19), `TestTypeIdentity` (AC-20), `TestSpanField` (AC-21–22), `TestEquality` (AC-23), `TestHashability` (AC-24), `TestItemsMethods` (AC-25), `TestRepr` (AC-26), `TestNoneLabelFiltering` (AC-27).
- Used `Span` instances as child/span values throughout (sourceless spans are hashable/comparable, convenient for test values).
- Added `test_extend_iterable_not_just_list` (generator input) covering the AC-25/requirements constraint that extend accepts any iterable.
- 44 tests pass; full suite 497 passed, 0 failures.

## Increment 3 — Cache UnknownSpan via GILOnceCell; remove four resolved TODOs (commit 08be093)

- `src/lib.rs`: Added `pub(crate) static UNKNOWN_SPAN: GILOnceCell<PyObject>`; populated during `_native` module init by cloning the same `PyObject` added as `m.add("UnknownSpan", ...)`.
- `src/cst_poc.rs`: Replaced per-constructor `py.import("fltk._native")?.getattr("UnknownSpan")?.unbind()` with `UNKNOWN_SPAN.get(py).expect(...).clone_ref(py)` in both `Identifier::new` and `Items::new`. Added `use crate::UNKNOWN_SPAN;`. Removed the four TODO comments at file top (`rust-cst-macro`, `cst-constructor-import-context`, `cst-unknown-span-cache`, `cst-generator-vs-list`).
- `TODO.md`: Removed entries for `rust-cst-macro`, `cst-constructor-import-context`, `cst-unknown-span-cache`, `cst-generator-vs-list`.
- 501 tests pass.
