# TODOs

## `example-placeholder`

This is a placeholder entry. Leave it here so the file is never empty. It is not a real TODO. You would reference it in code with `// TODO(example-placeholder)` comments. This is the basic TODO system design: An entry here with a slug used to join to code comments. Add real TODOs below this one in this format.

## `bazel-rules-rust`

Add `rules_rust` to `MODULE.bazel` so that the PyO3 native extension (`fltk._native`) is buildable via Bazel. Currently, Bazel builds do not include the Rust extension. Deferred from Phase 0 because Bazel Rust support is orthogonal to the Python/maturin build path. Location: `MODULE.bazel`.

## `rust-cst-child-node-identity`

Native child ownership (`Box<ChildNode>` in the native Vec) means a child returned twice through a Python getter/accessor wraps a fresh `Py<ConcreteNode>` per call; the same child read twice is not the same Python object (identity differs). Tests in `tests/test_phase4_rust_fixture.py` that formerly used `is` for child identity were relaxed to `==` (value equality). If a consumer requires stable Python child-object identity, add a per-node boundary cache (e.g. `Py` cache indexed by position) at the generated accessor layer. Deferred: no in-tree consumer currently requires identity stability. Location: `fltk/fegen/gsm2tree_rs.py` (accessor methods in `_per_label_methods`); see also `tests/test_phase4_rust_fixture.py:242,276,291,350,371`.

## `crosscdylib-abi-sentinel`

`extract_span` in `crates/fltk-cst-core/src/cross_cdylib.rs` uses `downcast_unchecked` after an `isinstance` check that can pass under version skew (consumer pins revision A, installed `fltk._native` wheel built from revision B with different `Span` layout) — turning a packaging error into in-process memory corruption rather than a clean error. Fix: unify the ABI sentinel mechanism across both the `Span` path (`get_span_type`, `extract_span`) and the `SourceText` path (`extract_source_text`, `FLTK_CST_CORE_ABI` classattr on `SourceText`). The `FLTK_CST_CORE_ABI` constant and `SourceText._fltk_cst_core_abi` classattr (introduced alongside `extract_source_text`) are the seed mechanism for the `SourceText` path, but the current derivation (`CARGO_PKG_VERSION` alone) does NOT cover pyo3-resolution skew — two builds of the same `fltk-cst-core` version with different pyo3 resolutions produce identical markers over different `PyClassObject<SourceText>` layouts (→ UB, not TypeError). The strengthened derivation must fold in the pyo3 version and/or a layout hash, and should be applied to both paths. Location: `crates/fltk-cst-core/src/cross_cdylib.rs` (`get_span_type`, `extract_span`, `extract_source_text`, `FLTK_CST_CORE_ABI`).

## `pyright-batch-tests`

The PoC self-check test (`test_poc_pyi_self_check_zero_errors`) and the PoC per-class conformance test (`test_poc_per_class_no_cast_zero_errors`) still run separate `uv run pyright` subprocesses. Additionally, the stub B4 tests in `tests/test_fltk_native_stub.py` call pyright via `test_cst_protocol.py` call sites. Full cross-file harness consolidation (shared session-scoped tmpdir across both test modules) is the remaining work. Location: `tests/test_gsm2tree_rs.py` (`TestGeneratePyiSelfCheck.test_poc_pyi_self_check_zero_errors`, `TestGeneratePyiConformance.test_poc_per_class_no_cast_zero_errors`).


