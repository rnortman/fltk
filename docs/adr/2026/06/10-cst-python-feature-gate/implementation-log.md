## Increment 5 — Documentation: rust-cst-extension-guide.md update (commit e2b2b32)

- `docs/rust-cst-extension-guide.md:30-31`: Replaced stale "depends on PyO3 only" claim with accurate statement: generated file depends on `fltk-cst-core` and PyO3; both must be declared as Cargo deps.
- `rust-cst-extension-guide.md:52-59`: Corrected Cargo.toml template — `[features]` block with `default = ["extension-module"]`, `extension-module = ["python", "pyo3/extension-module"]`, `python = ["fltk-cst-core/python"]`; added `fltk-cst-core` dependency with `default-features = false, features = ["python"]`.
- `rust-cst-extension-guide.md:132-148`: Added "Migrating an existing consumer crate" section covering both migration steps (add `fltk-cst-core` dep, add feature block) and their error consequences if omitted.
- `make check`: all steps pass.

## Increment 4 — Spike crate fltk-cst-spike (commit 5a53535)

- `Cargo.toml` workspace members: added `crates/fltk-cst-spike`.
- `crates/fltk-cst-spike/Cargo.toml`: new rlib, `default = []` (python off), `python = ["dep:pyo3", "fltk-cst-core/python"]` feature, `fltk-cst-core` dep `default-features = false`.
- `crates/fltk-cst-spike/src/lib.rs`: `#![cfg_attr(not(feature = "python"), forbid(unsafe_code))]`; `pub mod cst`; `#[cfg(test)] mod spike_tests`.
- `crates/fltk-cst-spike/src/cst.rs`: generated from `fltk/fegen/test_data/poc_grammar.fltkg` (identical to `src/cst_generated.rs` — same source grammar). No `--pyi-output`.
- `crates/fltk-cst-spike/src/spike_tests.rs`: 19 tests covering node construction, labeled child append, traversal to leaf spans, span text reads (in-bounds, sourceless, unknown), `has_source`/`len`/`is_empty`, `merge` (same-source, different-sources err, sourceless+sourced), `intersect` (overlapping, disjoint→unknown sentinel, different-sources err), structural equality (equal trees, unequal trees, label mismatch). All pass under `cargo test -p fltk-cst-spike` (python off).
- `Makefile`: added `cargo-test-no-python`, `cargo-clippy-no-python`, `check-no-pyo3` targets; added all three to `check` step list; added spike `cst.rs` regen step to `gencode`.
- `docs/adr/2026/06/10-cst-python-feature-gate/gaps.md`: written — 6 findings (no Debug on generated types, String allocation per text read, no codepoint↔byte helper, no builder, no span arithmetic helpers, SpanError lacks context).
- `cargo test -p fltk-cst-spike`: 19 passed. `cargo clippy -p fltk-cst-spike -- -D warnings`: clean. `cargo clippy -p fltk-cst-spike --features python -- -D warnings`: clean. `check-no-pyo3`: pyo3 absent from python-off graphs confirmed. `make check`: all steps pass.
- Deviation: generated types lack `Debug`, so spike tests use `assert!(a == b)` / `matches!()` instead of `assert_eq!`; this is itself gap finding #1 in gaps.md.

## Increment 3 — Generator changes: cfg-gated output (commit TBD)

- `fltk/fegen/gsm2tree_rs.py:_preamble()`: `use fltk_cst_core::Span;` unconditional; five pyo3/helper imports each gated with `#[cfg(feature = "python")]`.
- `gsm2tree_rs.py:_node_kind_block()`: dual-cfg blocks — python-on enum with `#[pyclass]`+`#[pyo3(name)]` on variants, python-off plain enum without pyo3 attrs. `#[pymethods]` impl gated.
- `gsm2tree_rs.py:_label_enum_block()`: same dual-cfg pattern for label enums.
- `gsm2tree_rs.py:_child_enum_block()`: enum+PartialEq unconditional; `to_pyobject`/`extract_from_pyobject` impl block gated with `#[cfg(feature = "python")]`.
- `gsm2tree_rs.py:_node_block()`: `#[pyclass]` → `#[cfg_attr(feature = "python", pyclass)]`; `#[pymethods]` impl block gated.
- `gsm2tree_rs.py:_register_classes_fn()`: entire fn gated with `#[cfg(feature = "python")]`.
- `tests/test_gsm2tree_rs.py`: updated exact-string assertions for new preamble, dual-cfg enum blocks, gated pymethods/register_classes. Added `TestCfgFeatureGate` class with 7 structural tests.
- `fltk/fegen/test_genparser.py:64`: updated preamble startswith assertion.
- Regenerated: `src/cst_fegen.rs`, `src/cst_generated.rs`, `tests/rust_cst_fixture/src/cst.rs`. All 1049 Python tests pass; cargo clippy -D warnings clean; python-off `cargo test -p fltk-cst-core --no-default-features` (23 tests) pass.
- Deviation: design §2.3 specified `#[cfg_attr(feature = "python", pyo3(name = "..."))]` on enum variants. This fails with pyo3 0.23 — the attribute validator fires before proc-macro expansion, so `pyo3` is not yet registered as a helper attribute when the variant attributes are checked. Used dual-cfg blocks (separate python-on and python-off enum definitions within the same file) instead. Functionally equivalent: python-on consumers see `#[pyclass]`+`#[pyo3(name)]`; python-off consumers see a plain enum with the same Rust variant names. Struct `#[pyclass]` still uses `cfg_attr` (structs have no helper-attribute issue).

## Increment 2 — Feature gate on fltk-cst-core (commit 1888b78)

- `crates/fltk-cst-core/Cargo.toml`: `pyo3` made optional; `[features]` added with `default = ["python"]` and `python = ["dep:pyo3"]`; updated comment block.
- `crates/fltk-cst-core/src/lib.rs:1-5`: `cross_cdylib` mod and its five re-exports gated behind `#[cfg(feature = "python")]`.
- `crates/fltk-cst-core/src/span.rs:1-12`: All pyo3 `use` lines (cross_cdylib, pyo3::exceptions, pyo3::prelude, pyo3::sync, pyo3::types) gated behind `#[cfg(feature = "python")]`.
- `span.rs`: `SPAN_KIND_SPAN_CACHE` static gated `#[cfg(feature = "python")]`.
- `span.rs`: `SourceText` changed to `#[cfg_attr(feature = "python", pyclass(frozen))]`; its `#[pymethods]` block gated `#[cfg(feature = "python")]`.
- `span.rs`: `Span` changed to `#[cfg_attr(feature = "python", pyclass(frozen, eq, hash))]`; `source_as_py` gated `#[cfg(feature = "python")]`; the `#[pymethods]` block gated `#[cfg(feature = "python")]`.
- `Cargo.toml` (fltk-native): features restructured to `default = ["extension-module"]`, `extension-module = ["python", "pyo3/extension-module"]`, `python = ["fltk-cst-core/python"]`.
- `tests/rust_cst_fixture/Cargo.toml`, `tests/rust_cst_fegen/Cargo.toml`: same three-line feature shape added.
- Python-off: `cargo check -p fltk-cst-core --no-default-features` clean; `cargo tree -p fltk-cst-core --no-default-features` shows no pyo3; 23 native Span tests pass.
- Python-on: `cargo check` workspace clean; clippy `-D warnings` both modes clean; fixture crates build.

## Increment 1 — SpanError type + native Span methods (commit dce0053)

- `crates/fltk-cst-core/src/span.rs:1-31`: Added `SpanError` enum with `SourceMismatch` variant, `Display`, and `std::error::Error` impls. Added `use std::fmt;`.
- `span.rs:212-311`: Moved `coerce_source` (now returns `Result<_, SpanError>` instead of `PyResult`), `text`, `has_source`, `len`, `is_empty`, `merge`, `intersect` to plain `impl Span` as `pub` methods.
- `span.rs:357-448`: `#[pymethods]` block now has `py_text`, `py_has_source`, `py_len`, `py_is_empty`, `py_merge`, `py_intersect` rename wrappers delegating to native methods; Python-visible names and error messages unchanged.
- `crates/fltk-cst-core/src/lib.rs:4`: Added `SpanError` to re-exports.
- `lib.rs:56-205`: Added 20 unit tests for native API (text, has_source, len, is_empty, merge, intersect, SpanError::Display). Tests are written but will only run standalone once the `python` feature gate exists (feature gate is a later increment); they compile and pass via the workspace build which links Python.
- All 1042 Python tests pass. Clippy clean with `-D warnings`.

