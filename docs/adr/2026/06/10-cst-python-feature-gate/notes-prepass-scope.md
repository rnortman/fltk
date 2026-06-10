No findings.

All design-scoped items are present in the diff:

- §2.1: fltk-cst-core Cargo.toml `python` feature (default-on, `dep:pyo3`), `lib.rs` gates on `cross_cdylib` and its re-exports, `#[cfg_attr]` on `SourceText`/`Span`, pymethods blocks gated, `SPAN_KIND_SPAN_CACHE` gated, `source_as_py` gated.
- §2.2: `SpanError` (`#[non_exhaustive]`, `Display`, `std::error::Error`), native `text`/`has_source`/`len`/`is_empty`/`merge`/`intersect`/`coerce_source` in plain `impl Span`; pymethods renamed to `py_text`/`py_merge` etc. with `#[pyo3(name = "...")]`; `text_or_raise` and `kind` remain pymethods-only; `SpanError` re-exported from `lib.rs`.
- §2.3: Generator `_preamble()` unconditional Span import + five cfg-gated pyo3/helper imports; `_node_kind_block()`/`_label_enum_block()` use dual-cfg blocks (deviation called out below); `_child_enum_block()` conversion impl gated; `_node_block()` `cfg_attr` on struct pyclass, pymethods gated; `_register_classes_fn()` gated. Generator signature unchanged.
- §2.4: Root `Cargo.toml` three-feature shape (`default`, `extension-module`, `python`); `rust_cst_fixture/Cargo.toml` and `rust_cst_fegen/Cargo.toml` same shape.
- §2.5: `crates/fltk-cst-spike` workspace member; Cargo.toml matches design; `lib.rs` with `forbid(unsafe_code)` conditional on python-off; `src/cst.rs` generated from `poc_grammar.fltkg`; `spike_tests.rs` with all required exercises (construction, push, traversal, span text, merge, intersect, structural equality).
- §2.6: Makefile `cargo-test-no-python`, `cargo-clippy-no-python`, `check-no-pyo3` targets; all added to `check` step list; `check-no-pyo3` positive-control hardening present; spike `cst.rs` regen step added to `gencode`.
- §2.7: `docs/rust-cst-extension-guide.md` stale claim corrected, template updated with `fltk-cst-core` dep and feature block, migration section added.
- §2.8: `gaps.md` exists with 6 findings.
- §4 test plan: generator tests updated (`TestCfgFeatureGate` + all existing exact-string assertions updated); fltk-cst-core native unit tests added (20 tests); `test_genparser.py` preamble assertion updated.

Deviation — explicitly called out in implementation report §Increment 3: Design §2.3 specified `#[cfg_attr(feature = "python", pyo3(name = "..."))]` on enum variants. pyo3 0.23 validates helper attributes before proc-macro expansion, so that form fails. Implementation uses dual-cfg blocks (one `#[cfg(feature = "python")]` block with direct pyo3 attrs, one `#[cfg(not(feature = "python"))]` plain block). Functionally equivalent per requirements. Called out in both implementation report and `TestCfgFeatureGate` docstring.
