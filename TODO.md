# TODOs

## `example-placeholder`

This is a placeholder entry. Leave it here so the file is never empty. It is not a real TODO. You would reference it in code with `// TODO(example-placeholder)` comments. This is the basic TODO system design: An entry here with a slug used to join to code comments. Add real TODOs below this one in this format.

## `bazel-rules-rust`

Add `rules_rust` to `MODULE.bazel` so that the PyO3 native extension (`fltk._native`) is buildable via Bazel. Currently, Bazel builds do not include the Rust extension. Deferred from Phase 0 because Bazel Rust support is orthogonal to the Python/maturin build path. Location: `MODULE.bazel`.

## `rust-cst-child-node-identity`

Native child ownership (`Box<ChildNode>` in the native Vec) means a child returned twice through a Python getter/accessor wraps a fresh `Py<ConcreteNode>` per call; the same child read twice is not the same Python object (identity differs). Tests in `tests/test_phase4_rust_fixture.py` that formerly used `is` for child identity were relaxed to `==` (value equality). If a consumer requires stable Python child-object identity, add a per-node boundary cache (e.g. `Py` cache indexed by position) at the generated accessor layer. Deferred: no in-tree consumer currently requires identity stability. Location: `fltk/fegen/gsm2tree_rs.py` (accessor methods in `_per_label_methods`); see also `tests/test_phase4_rust_fixture.py:242,276,291,350,371`.

## `crosscdylib-abi-check-helper`

`get_span_type` and `extract_source_text` both perform the same two-step ABI pair check (string marker then layout int), with only the type label and expected-layout constant varying. Extract a generic helper (e.g. `fn check_abi_pair<T: PyClass>(ty: &Bound<'_, PyType>, type_label: &str) -> PyResult<()>`) to eliminate the duplication and ensure uniform error messages. Currently the error-message wording diverges slightly between the two paths. Location: `crates/fltk-cst-core/src/cross_cdylib.rs` (`extract_source_text` lines 57–100, `get_span_type` lines ~255–300).

## `abi-gate-test-consolidation`

`TestSpanPathAbiGate` spawns three separate subprocesses (one per scenario: ABI-string mismatch, layout mismatch, control). Since `GILOnceCell` does not cache errors, all three could share one subprocess (failures first, success last), reducing startup cost. Deferred: current structure is readable and the savings are modest. Location: `tests/test_rust_span.py` (`TestSpanPathAbiGate`).

## `crosscdylib-abi-size-probe`

The `_fltk_cst_core_abi_layout` classattr probe compares `size_of::<PyClassObject<T>>()` across cdylibs. Equal size is consistent with — but does not prove — identical field layout: a pyo3 build that reorders internal fields while preserving total size passes the probe, after which `downcast_unchecked` reinterprets memory at wrong offsets. To close this residual, fold the resolved pyo3 version into `FLTK_CST_CORE_ABI` (via a build script reading the Cargo lock or `DEP_*` env var) so the string itself separates pyo3 resolutions. The size probe remains as defense-in-depth. Location: `crates/fltk-cst-core/src/cross_cdylib.rs` (`FLTK_CST_CORE_ABI` constant and SAFETY comments in `extract_source_text` / `extract_span`).

## `rust-cst-children-list-view`

The Rust-backend `node.children` getter returns a fresh snapshot list per call (a `PyList` rebuilt from `Vec` on each access); in-place mutation of the returned list is a silent no-op on the tree. The Python backend returns the node's actual internal list, so in-place list mutation edits the tree. Closing this divergence would require a live sequence-proxy pyclass. Deferred as additive; the Python-backend behavior is documented in the Phase 3 docs. Location: `fltk/fegen/gsm2tree_rs.py` (`_children_getter`, lines 682–700).

