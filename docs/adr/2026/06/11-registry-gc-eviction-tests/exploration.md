# Registry Unit Tests — TODO Adversarial Validation

Validates TODO `registry-unit-tests` at `crates/fltk-cst-core/src/registry.rs:128-130`.

---

## 1. Does registry.rs actually lack unit tests?

**Confirmed.** `crates/fltk-cst-core/src/registry.rs` has no `#[test]` functions. The only
test-gated item is `pub fn snapshot(...)` at line 136, which is a helper for testing from
outside — not a test itself. The `#[cfg(test)]` at line 29 gates a `use pyo3::types::PyDict`
import (used only by `snapshot`), not a test module.

The module comment at line 128–130 correctly states no Rust unit tests exist.

---

## 2. Is the libpython-linking blocker real?

**Confirmed, with nuance.**

`cargo test -p fltk-cst-core` (default features = `["python"]`) fails with:

```
rust-lld: error: unable to find library -lpython3.10
```

Root cause chain:

- `crates/fltk-cst-core/Cargo.toml:15`: `pyo3 = { version = "0.23", features = ["abi3-py310"], optional = true }`
- `crates/fltk-cst-core/Cargo.toml:18-19`: `[features] default = ["python"]; python = ["dep:pyo3"]`
- `pyo3-build-config-0.23.5/src/impl_.rs:863-885`: `is_linking_libpython()` returns true when
  `CARGO_FEATURE_EXTENSION_MODULE` is absent — which it is for `fltk-cst-core` (the `extension-module`
  feature lives only on the top-level `fltk-native` cdylib in `Cargo.toml:15-16`).
- The linker searches `/usr/lib64` for `-lpython3.10` but only `libpython3.10.so.1.0` exists there;
  no unversioned `libpython3.10.so` symlink is present on this system. This is a system packaging
  gap, not a pyo3 design flaw.

`cargo test -p fltk-cst-core --no-default-features` succeeds (24 tests pass, all `Span`/`SourceText`
tests in `lib.rs`). The `registry` module is gated behind `#[cfg(feature = "python")]`
(`lib.rs:4-5`), so it is entirely absent in that build.

---

## 3. Are the four functions actually pyo3-dependent?

**All four are irreducibly pyo3-dependent.** Every function signature takes `py: Python<'_>` as
its first argument. All four delegate to `get_registry(py)` (line 37–44), which calls
`py.import("weakref")` and `weakref.WeakValueDictionary()`. There is no Python-free code path.

The entire registry is implemented as a `GILOnceCell<PyObject>` (line 34) holding a Python
`weakref.WeakValueDictionary`. No subset of its logic can be exercised without a live Python
interpreter.

---

## 4. How adequate is the existing Python-side coverage?

**Substantial, but not exhaustive.** Python tests exercise registry behavior indirectly through
the fixture crate `phase4_roundtrip_cst` (tests load the compiled extension). The identity tests
in `tests/test_phase4_rust_fixture.py`:

- `TestPhase1IdentityAndMutation::test_repeated_child_reads_return_same_handle` (line 383):
  reads `children[0]` twice, asserts `first is second` — exercises `get_or_insert_with` hit path.
- `test_child_label_accessor_returns_same_handle` (line 394): `child_key() is ident` — exercises
  `get_or_insert_with` hit path via labeled accessor.
- `test_identity_stable_across_different_accessors` (line 463): `children[0][1] is child_key()`.
- `test_new_node_append_readback_identity` (line 474): `append` then `children[0][1] is ident` —
  exercises `force_register` path (py_new → append → read-back).
- `test_children_label_accessor_identity` (line 484): `children_key()[0] is ident`.
- `test_extend_children_self_original_handle_survives` (line 495): self-extend, then original
  handle still canonical.
- `TestAC5ContractItems::test_ac6_list_protocol_index` (line 233): `tup[1] is child`.
- `test_ac6_list_protocol_negative_index` (line 264): `last[1] is b`.
- `test_ac7_tuple_items` (line 278): `value is ident`.
- `test_ac11_iterator_methods` (line 335): `child_key() is ident`, `maybe_key() is ident`.

Also `tests/test_rust_parser_bindings.py:79` exercises a parser-side "same result object"
identity guarantee (different registry, parser memo, not CST registry).

**Gaps not covered by existing Python tests:**
- `register_if_absent` returning `false` (race path): the comment at `registry.rs:121` labels this
  "unreachable in practice" under single-threaded Python. No test forces or verifies the
  `registered == false` branch.
- `force_register` called directly: it is invoked from generated `py_new` code in the fixture;
  it is covered only in the sense that object creation works. There is no test that verifies
  `force_register` specifically overwrites an existing entry.
- `lookup` returning `None` followed by `make_handle` execution (miss path): implied by any
  first-access test, but not tested as an explicit miss-then-register sequence.
- `snapshot()` is defined at `registry.rs:137-142` but is never called in any Python test.

---

## 5. Simpler option the TODO missed?

The TODO lists three options (dedicated test cdylib, ctypes/cffi, integration test crate). It
does not mention the simplest workaround for this specific system: the link failure is not a
`rlib`-with-pyo3 fundamental, it is a missing `libpython3.10.so` unversioned symlink. On systems
where `python3-devel` (or equivalent) is installed, the symlink exists and `cargo test -p
fltk-cst-core` (with `python` feature) links successfully. The TODO overstates the build
impossibility — it is a missing dev-package gap on this machine, not an architectural block.

The `pyo3` `auto-initialize` feature (available since pyo3 0.14) enables embedding: a test
binary that is not a cdylib can call `Python::with_gil` without a pre-initialized interpreter if
the `auto-initialize` feature is enabled (it calls `Py_Initialize` automatically). This is not
enabled anywhere in this workspace. Adding `pyo3 = { version = "0.23", features = ["abi3-py310",
"auto-initialize"] }` as a dev-dependency of `fltk-cst-core` would allow `#[test]` functions to
call `Python::with_gil(|py| { ... })` directly — provided the linker can find the `.so` symlink.
The TODO does not mention this option.

---

## 6. Is this papering over a deeper problem?

**Partially.** The registry correctness property (at-most-one live Python handle per Arc address)
is the core invariant. The Python `is`-identity tests in `test_phase4_rust_fixture.py` test the
observable consequence (identity stability) but do so via full round-trip through the fixture crate.
If the registry contained a subtle bug — e.g., the `register_if_absent` false-branch returning a
stale handle after eviction — the existing Python tests would catch it only if the GC ran between
accesses, which does not happen in CPython under normal deterministic test execution.

The `WeakValueDictionary` eviction behavior (ABA safety claim at `registry.rs:18-22`) is not
tested at all: no test creates a node, appends it, drops all references to force GC, then creates
a new node at the same address and verifies the old weak entry is gone. This is the one scenario
where a bug would be non-obvious and the Python-side tests provide no coverage.

The `snapshot()` function at `registry.rs:137` was presumably added to enable such tests but is
never used.
