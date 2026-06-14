## Increment 1 — Scaffolding bump: pyo3 0.29 + advisory cleanup (commit 7b6c7a7)

- Cargo.toml (root): pyo3 "0.23" → "0.29"
- crates/fltk-cst-core/Cargo.toml: version 0.1.0 → 0.2.0; pyo3 "0.23" → "0.29"
- crates/fltk-cst-spike/Cargo.toml: pyo3 "0.23" → "0.29"
- tests/rust_cst_fegen/Cargo.toml: pyo3 "0.23" → "0.29"
- tests/rust_cst_fixture/Cargo.toml: pyo3 "0.23" → "0.29"
- tests/rust_parser_fixture/Cargo.toml: pyo3 "0.23" → "0.29"
- deny.toml: removed TODO(pyo3-upgrade) comment and two RUSTSEC advisory ignores
- Cargo.lock (root): already had pyo3 0.29.0 (was resolved against the bumped manifest)
- tests/rust_cst_fegen/Cargo.lock: pyo3 0.23.5 → 0.29.0 (cargo update)
- tests/rust_cst_fixture/Cargo.lock: pyo3 0.23.5 → 0.29.0 (cargo update)
- tests/rust_parser_fixture/Cargo.lock: pyo3 0.23.5 → 0.29.0 (cargo update)
- Checkpoint: `make cargo-deny` green; `cargo check -p fltk-cst-core` red as expected (class A/B errors cataloged)

## Increment 2 — fltk-cst-core tier-1 fixes: F, B, D, A, G (commit 8e2e71f)

- crates/fltk-cst-core/src/registry.rs: F (`GILOnceCell`→`PyOnceLock`, static type `PyOnceLock<Py<PyAny>>`); B (`PyObject`→`Py<PyAny>` in `lookup`, `get_or_insert_with`, `get_registry` turbofish); D (`downcast_into`→`cast_into` in `snapshot`)
- crates/fltk-cst-core/src/span.rs: F (`GILOnceCell`→`PyOnceLock`); removed `pyo3::impl_::pycell::PyClassObject` import; A (`PyClassObject<T>`→`<T as PyClassImpl>::Layout` in both `_fltk_cst_core_abi_layout` classattrs, doc comments updated); G (`from_py_object` added to `Span` pyclass attr); B (kind getter return type `Py<PyAny>`)
- crates/fltk-cst-core/src/cross_cdylib.rs: F (`GILOnceCell`→`PyOnceLock` in all four statics); B (`PyObject`→`Py<PyAny>` for `WITH_SOURCE_UNCHECKED_METHOD`, `span_to_pyobject` return type); D (`downcast`→`cast`, `downcast_into`→`cast_into`, `downcast_unchecked`→`cast_unchecked` at all six D-class sites; SAFETY comments updated); A (step-4 uses `<T as PyClassImpl>::Layout`, doc comments updated)
- crates/fltk-cst-core/src/lib.rs: F+B (`UNKNOWN_SPAN: PyOnceLock<Py<PyAny>>`); new `abi_probe_tests` module with `span_probe_above_floor` and `source_text_probe_above_floor` (python feature, §2.A guard)
- src/lib.rs: F+B (`UNKNOWN_SPAN: PyOnceLock<Py<PyAny>>`, import `PyOnceLock`)
- `cargo check -p fltk-cst-core --all-features` and `cargo clippy -D warnings`: green
- `cargo test -p fltk-cst-core --no-default-features`: 38 passed; python-feature tests require maturin (step 7)
- `cargo check` workspace: errors now exclusively in tier-3 generated files (cst_fegen.rs, cst_generated.rs) — §3 step-3 checkpoint satisfied

## Increment 3 — generators tier-2: B, D, G in gsm2tree_rs.py and gsm2parser_rs.py (commit 382d63b)

- fltk/fegen/gsm2tree_rs.py: B — `PyObject` → `Py<PyAny>` in all emitted fn signatures (to_pyobject, span getter, Label classattr, child/remove_at/child_<lbl>/maybe_<lbl>/__eq__ for nodes/enums, label params Option<PyObject>→Option<Py<PyAny>> in append/extend/insert/replace_at); D — `downcast` → `cast` in to_py_canonical emission; G — `from_py_object` added to NodeKind and label enum pyclass attrs; F — stale GILOnceCell docstring → PyOnceLock
- fltk/fegen/gsm2parser_rs.py: B — PyApplyResult.result field and getter `PyObject` → `Py<PyAny>`
- tests/test_gsm2tree_rs.py: all PyObject → Py<PyAny> assertion updates; pyclass attr assertions include from_py_object for NodeKind and label enums; 253 tests pass

## Increment 4 — regenerate tier-3 (make gencode + make fix) and verify cargo check (commit 18f6d47)

- make gencode + make fix: src/cst_fegen.rs, src/cst_generated.rs, crates/fltk-cst-spike/src/cst.rs, tests/*/src/{cst,parser,collision_*}.rs regenerated with B/D/G churn
- gsm2tree_rs.py: line-length fix for append fn signature (E501); 198+55 generator tests pass
- fltk/_native/fegen_cst.pyi: zero diff — public surface unchanged
- `cargo check` workspace: green; class C errors: 0 (§3 step-5 checkpoint satisfied)

## Increment 5 — cargo clippy, tests, Python integration, bookkeeping (commit f2144c3)

- tests/rust_cst_fixture/src/registry_introspection.rs:28: B fix (`PyObject`→`Py<PyAny>` in `_registry_lookup`; hand-written consumer of changed `registry::lookup` API; whack-a-mole per design §3 note)
- `make cargo-clippy` + `cargo-clippy-no-python`: green
- `make cargo-test-no-python`: 59+7 tests pass
- `make check-no-pyo3`: pyo3 absent from python-off graphs
- `uv run --group dev maturin develop`: green; `make build-test-user-ext build-fegen-rust-cst build-rust-parser-fixture`: green
- `uv run pytest --ignore=.claude`: 1654 passed (pre-existing worktree collection noise from .claude/worktrees is unrelated)
- `make cargo-deny`: advisories ok — RUSTSEC-2025-0020 and RUSTSEC-2026-0177 cleared
- TODO.md: `pyo3-upgrade` entry removed
- docs/rust-cst-extension-guide.md: version pins 0.1→0.2 / 0.23→0.29 + out-of-tree rebuild note
