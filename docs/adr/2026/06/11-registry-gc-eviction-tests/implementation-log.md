# Implementation Log: GC/eviction/ABA tests for the CST handle registry

## Increment 2 — Python-callable registry wrappers in fixture crate (commit 381a454)

- `tests/rust_cst_fixture/Cargo.toml`: extended `python` feature to also enable `fltk-cst-core/test-introspection`.
- `tests/rust_cst_fixture/src/registry_introspection.rs`: new hand-written module with four `#[pyfunction]` wrappers: `_registry_snapshot`, `_registry_lookup`, `_registry_register_if_absent`, `_registry_force_register`; each delegates to the corresponding `fltk_cst_core::registry` function. Doc comments note the cross-cdylib rationale and synthetic-address caller contract.
- `tests/rust_cst_fixture/src/lib.rs`: added `mod registry_introspection`; registered all four functions on the `phase4_roundtrip_cst` module via `wrap_pyfunction!`.
- Build: `make build-test-user-ext` clean (1.50s).

## Increment 3 — New test file `tests/test_registry_gc_eviction.py` (commit 709c01d)

- `tests/test_registry_gc_eviction.py`: new file; 10 tests across 3 classes.
  - `TestSnapshotPlumbing`: `test_snapshot_maps_int_addr_to_handle`, `test_py_new_registers_immediately`.
  - `TestEvictionAndFreshHandles`: `test_handle_dropped_entry_evicted`, `test_arc_alive_handle_dead_fresh_handle_no_resurrection`, `test_stress_create_drop_cycles`.
  - `TestDirectRegistrySemantics`: `test_lookup_miss_register_hit`, `test_register_if_absent_false_when_live_entry`, `test_force_register_overwrites_live_entry`, `test_weak_eviction_direct`, `test_register_after_eviction_installs_fresh`.
  - Module docstring documents the five authoring disciplines (delta assertions, snapshot strong-refs, frame-local pinning, determinism, id() reuse).
  - Inline comment at `TestDirectRegistrySemantics` documents the unreachable `registered == false` arm.
- `crates/fltk-cst-core/src/registry.rs`: deleted `TODO(registry-unit-tests)` comment (lines 128-130).
- `TODO.md`: deleted `registry-unit-tests` entry.
- All 10 new tests pass; full suite 1426 passed; `make check` clean including `cargo-test`.

## Increment 1 — `test-introspection` feature gate on `fltk-cst-core` (commit 5546cfc)

- `crates/fltk-cst-core/Cargo.toml`: added `test-introspection = ["python"]` feature with test-only comment.
- `crates/fltk-cst-core/src/registry.rs`: changed `#[cfg(test)]` gate on `PyDict` import (line 29-30) and `snapshot` fn to `#[cfg(any(test, feature = "test-introspection"))]`; updated `snapshot` doc comment to name both compilation conditions.
