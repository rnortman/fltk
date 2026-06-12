# Implementation Log: cst-named-mutators

Style: concise, precise, complete, unambiguous.

## Increment 6 — Rust identity tests §4.3 (commit c3a24a2)

- `tests/test_cst_mutators_identity.py` (new, 185 lines, 7 tests): uses `phase4_roundtrip_cst` (built with `test-introspection` by default; skipped when not available).
  - `TestRemoveAtIdentity` (4 tests): handle before remove_at stays valid; `remove_at` return `is` prior handle; removed child re-inserted via `insert` is is-stable; via `append` is is-stable.
  - `TestReplaceAtIdentity` (2 tests): evicted child handle unaffected; new child read back via accessor is same handle.
  - `TestClearRegistryEviction` (1 test): `clear()` + del handle + `gc.collect()` → registry entry absent (pins: clear holds no strong ref; registry self-evicts).
- 1591 total Python tests pass; `make check` clean.

## Increment 5 — Rust native tests §4.4 (commit fadd469)

- `tests/rust_cst_fixture/src/native_tests.rs`: 16 new tests covering `insert_child`, `remove_child`, `replace_child`, `clear_children`.
  - `insert_child`: head/middle/tail, label preserved, None label, `#[should_panic]` for index > len.
  - `remove_child`: index 1 returns correct entry with label, head removal, `#[should_panic]` on empty.
  - `replace_child`: old entry returned, length preserved, label=None clears label, `#[should_panic]` on empty.
  - `clear_children`: populated → empty, empty no-op, cleared child still accessible via retained Shared.
- 64 total native tests pass; `make check` clean.

## Increment 4 — Cross-backend parity tests §4.2 + insert-clamping bug fixes (commit 90cb790)

- `tests/test_cst_mutators_parity.py` (new): 93 tests parametrized over py/emb backends.
  - `TestInsert` (9 tests): head/middle/tail, negative, large-positive/negative clamping, labeled/unlabeled, empty node, bool index.
  - `TestRemoveAt` (8 tests): positive, negative, return-matches-children, empty/OOB IndexError, large beyond-i64 IndexError.
  - `TestReplaceAt` (7 tests): length preservation, child update, label=None clears old label, negative index, OOB IndexError, large index, returns None.
  - `TestClear` (3 tests): populated, empty no-op, returns None.
  - `TestErrorBehavior` (8 tests): bad label type (insert/replace_at), bad child type (insert/replace_at), non-index type (all three), wrong-backend label.
  - `TestMessageParity` (6 tests): exact string equality of IndexError/TypeError messages between py and emb backends.
  - `TestMixedOperationsParity` (3 tests): interleaved sequence produces identical tree structure; clear + reappend parity.
  - `TestSpanHandInPerBackend` (4 tests): py accepts both span types; emb accepts native only, rejects terminalsrc.Span.
  - `TestItemsMultiLabel` (3 tests): multi-label insert, remove_at returns correct label, replace_at changes label.
- Bug found and fixed: Python backend `insert()` passed the `operator.index()` result directly to `list.insert()`, which overflows `ssize_t` for values like `10**25`. Fixed in `gsm2tree.py:513-521` by explicit clamp to `[0, n]` before delegating.
- Bug found and fixed: Rust backend `_generic_insert` used `__neg__` + `extract::<i64>()` to detect sign of beyond-i64 values; the negated large value also overflows i64, yielding wrong clamp direction. Fixed in `gsm2tree_rs.py:1268` by using `raw_idx.lt(0i64)?` (PyO3 `Bound::lt` handles arbitrary-magnitude ints).
- Regenerated: all Python CST modules (fltk_cst.py, bootstrap_cst.py, toy_cst.py, unparsefmt_cst.py and protocols), all Rust CST files (cst_fegen.rs, cst_generated.rs, tests/*/cst.rs, fltk-cst-spike/cst.rs), .pyi stub.
- 1584 Python tests pass; make check clean.

## Increment 3 — Generator emission tests (§4.1) (commit a886265)

- `tests/test_gsm2tree_py.py`: added `TestMutatorsEmittedPyConcreteClass` (18 tests — presence + signature shape of insert/remove_at/replace_at/clear on labeled and zero-label concrete classes), `TestMutatorsEmittedPyProtocol` (7 tests — protocol stubs present + ordering between child and per-label quintet), `TestMutatorNoLabelCollision` (2 tests — reserved-name regression: per-label prefixes never produce a fixed mutator name).
- `tests/test_gsm2tree_rs.py`: added `TestMutatorsEmittedRsPymethods` (14 tests — pymethod presence, index/signature shapes, __index__ normalization, clamp logic, IndexError message format), `TestNativeMutatorsEmittedRs` (10 tests — insert_child/remove_child/replace_child/clear_children presence and signature), `TestMutatorsEmittedPyi` (9 tests — .pyi stubs present with correct shapes and ordering), `TestRegistrySnapshotEmittedRs` (3 tests — _registry_snapshot pyfunction emitted and cfg-gated), `TestMutatorNoCollisionRs` (2 tests — per-label prefix collision reasoning).
- All 65 new tests pass; full suite 1491 passed.

## Increment 2 — Rust backend generator: emit pymethods insert/remove_at/replace_at/clear (commit f729520)

- `fltk/fegen/gsm2tree_rs.py`: added `PyIndexError` to preamble `use` import; added `_generic_insert`, `_generic_remove_at`, `_generic_replace_at`, `_generic_clear` pymethod emitters; wired them into `_node_block` after `_generic_child`; added `_native_mutators` emitter for `insert_child`/`remove_child`/`replace_child`/`clear_children` on the plain `impl` block; added four `.pyi` stubs in `generate_pyi` between `child` and per-label quintet; added `_registry_snapshot` pyfunction (gated `all(python, test-introspection)`) to `_register_classes_fn`; updated `_children_getter` docstring to replace `TODO(rust-cst-children-list-view)` with ADR pointer.
- `Cargo.toml`, `crates/fltk-cst-spike/Cargo.toml`, `tests/rust_cst_fixture/Cargo.toml`, `tests/rust_cst_fegen/Cargo.toml`, `tests/rust_parser_fixture/Cargo.toml`: added `test-introspection = ["python", "fltk-cst-core/test-introspection"]` feature to suppress `unexpected_cfg` warnings from generated `#[cfg(feature = "test-introspection")]` attributes.
- `TODO.md`: deleted `rust-cst-children-list-view` entry (§2.6).
- Regenerated: all Rust CST files (`src/cst_fegen.rs`, `src/cst_generated.rs`, `tests/*/src/cst.rs`, `crates/fltk-cst-spike/src/cst.rs`), Python protocol files (bootstrap_cst.py, fltk_cst.py, toy_cst.py, unparsefmt_cst.py), `.pyi` stub (`fltk/_native/fegen_cst.pyi`). `make check` clean.
- `tests/test_gsm2tree_rs.py`: updated `test_required_use_declarations` to expect `PyIndexError` in preamble import.
- Design §2.3 index-normalization via `__index__`: implemented by calling `index.call_method0("__index__")` on the raw PyAny parameter, then extracting as `i64`; overflow/sign detection uses a `__neg__` probe for beyond-i64 values.
- Design §2.3 `_registry_snapshot` binding: uses `registry::snapshot(py)` directly; returns `Bound<'_, PyDict>` (matching `snapshot`'s signature) wrapped in `PyResult`. The `#[cfg(feature = "test-introspection")]` attribute inside `register_classes` guards the `add_function` call.
- 1426 Python tests pass; 48 native Rust tests pass; `make check` passes.

## Increment 1 — Python backend generator: emit insert/remove_at/replace_at/clear (commit f491049)

- `fltk/fegen/gsm2tree.py`: added `operator` and `sys` to generated module imports; emitted `_get_native_span_type()` module-level helper (lazy native Span lookup, preserves pure-Python importability, §2.2); added `_emit_py_mutators` method on `CstGenerator`.
- `_emit_py_mutators`: emits per-class `_check_child_type_for_mutators` and `_check_label_type_for_mutators` helpers, then `insert`, `remove_at`, `replace_at`, `clear` methods (§2.4). Validation strict on new API, unchanged for existing `append`/`extend`.
- Index normalization via `operator.index(index)` for `__index__` semantics on all three indexed methods. `remove_at`/`replace_at` perform explicit bounds-check with parity message `"{ClassName}.{method}: index {index} out of range ({n} children)"`. `insert` delegates to `list.insert` for clamping.
- Child type validation: single type → `isinstance(child, T)`; multi-type node-only → `isinstance(child, A | B)` (UP038); span-bearing → runtime tuple with lazily resolved native Span.
- Label type validation: labeled node → `isinstance(label, ClassName.Label)`; label-free → non-None label raises TypeError. Error messages use `type(self).__name__` to avoid long generated f-string lines exceeding 120 chars.
- `_protocol_class_for_model`: added `insert`, `remove_at`, `replace_at`, `clear` stubs with same annotations as concrete class, placed between `child` and the per-label quintet (§2.4).
- Regenerated: `fltk/fegen/fltk_cst.py`, `fltk_cst_protocol.py`, `bootstrap_cst.py`, `bootstrap_cst_protocol.py`, `fltk/unparse/toy_cst.py`, `toy_cst_protocol.py`, `unparsefmt_cst.py`, `unparsefmt_cst_protocol.py`. All pass `make fix` / `ruff check` clean.
- 1280 tests pass (all non-Rust-generator tests). 2 Rust conformance tests (`TestGeneratePyiConformance::test_fegen_whole_module_no_cast_zero_errors`, `test_fegen_per_class_no_cast_zero_errors`) fail because Rust `.pyi` stubs don't yet declare the four methods — will be fixed in the Rust backend increment.
- Deviation: `_check_label_type_for_mutators` uses `type(self).__name__` instead of a literal class name to avoid E501 line-length violations in generated code for long class names like `PositionSpecStatement`. Message content is identical at runtime.
- Deviation: Rust CST generated files (`src/cst_fegen.rs`, `src/cst_generated.rs`, `tests/*/src/cst.rs`, `crates/fltk-cst-spike/src/cst.rs`) not yet regenerated — Rust `.pyi` generator not yet updated (next increment).
