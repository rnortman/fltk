# Design: GC/eviction/ABA tests for the CST handle registry

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Requirements: `request.md` (this dir). Exploration: `exploration.md` (this dir). Test-only change plus clearly-test-only plumbing.

## 1. Root cause / context

The registry (`crates/fltk-cst-core/src/registry.rs`) guarantees at most one live Python handle per `Shared<T>` Arc address. Its ABA-safety claim (`registry.rs:18-22`) — weak values auto-evict on handle GC, so address reuse cannot resurrect a stale handle — has zero test coverage. Existing identity tests (`tests/test_phase4_rust_fixture.py:383-505`, AC-contract tests at 233-367) only exercise hit paths where GC never runs between accesses (exploration §4, §6). Three specific gaps:

1. Eviction: no test drops all handle references, forces GC, and verifies the weak entry is gone and a subsequent read mints a fresh, correct handle.
2. `force_register` overwrite semantics (`registry.rs:92-97`): invoked from generated `py_new`; never tested as "overwrites an existing entry".
3. `register_if_absent` false branch (`registry.rs:66-74`): returns `false` when a live entry exists; never tested.

`snapshot()` (`registry.rs:137-142`) was built for these tests but is `#[cfg(test)]`-gated, so it is compiled only during `cargo test -p fltk-cst-core` — which does not even link on machines lacking the unversioned `libpython3.10.so` symlink (exploration §2) — and never compiled into any extension Python tests can import. It is currently dead code.

Per the binding reframe in `request.md`: tests are Python-side, against the existing fixture extension `phase4_roundtrip_cst` (`tests/rust_cst_fixture/`). No Rust `#[test]` functions, no cargo test infrastructure changes.

## 2. Proposed approach

### 2.1 Expose `snapshot()` to the fixture build (fltk-cst-core)

`crates/fltk-cst-core/src/registry.rs`:
- Change the gate on `snapshot` (and the `PyDict` import at line 29-30) from `#[cfg(test)]` to `#[cfg(any(test, feature = "test-introspection"))]`.
- Update `snapshot`'s doc comment: "Only compiled under `cfg(test)` or the `test-introspection` feature; never enabled in production builds."

`crates/fltk-cst-core/Cargo.toml`:
- Add feature `test-introspection = ["python"]` with a comment stating it is test-only plumbing (enables registry introspection for test fixture crates; never enable in production extensions).

This is not a production behavior change: the feature is off by default, off in `fltk-native`, and off for pure-Rust consumers. The feature name itself marks it test-only (request constraint: plumbing must be clearly test-only).

### 2.2 Python-callable registry wrappers (fixture crate)

The wrappers must live in the fixture crate, not `fltk._native`: each cdylib statically links its own `fltk-cst-core`, so each has its own `CANONICAL_REGISTRY` static. The fixture's generated code (`tests/rust_cst_fixture/src/cst.rs`) uses the fixture's copy; only wrappers compiled into the same cdylib observe that registry instance.

`tests/rust_cst_fixture/Cargo.toml`:
- Extend the `python` feature: `python = ["fltk-cst-core/python", "fltk-cst-core/test-introspection"]`. (The fixture is itself a test artifact; unconditional introspection is appropriate.)

New file `tests/rust_cst_fixture/src/registry_introspection.rs` (hand-written, like `lib.rs`; not generated), registered from the `#[pymodule]` init in `lib.rs`:

- `#[pyfunction] fn _registry_snapshot(py) -> PyResult<Bound<PyDict>>` — delegates to `fltk_cst_core::registry::snapshot`. Returns a plain `dict` {int Arc-address → handle (strong ref)}.
- `#[pyfunction] fn _registry_lookup(py, addr: usize) -> PyResult<Option<PyObject>>` — delegates to `registry::lookup`.
- `#[pyfunction] fn _registry_register_if_absent(py, addr: usize, obj: &Bound<PyAny>) -> PyResult<bool>` — delegates to `registry::register_if_absent`.
- `#[pyfunction] fn _registry_force_register(py, addr: usize, obj: &Bound<PyAny>) -> PyResult<()>` — delegates to `registry::force_register`.

Underscore-prefixed names mark them private/test-only. Doc comments on the register wrappers must state: callers use small synthetic integer addresses (counter from 1, far below any heap Arc address; weak eviction cleans them up regardless), so the `force_register` caller contract (`registry.rs:87-91` — unrelated addr/handle pairings corrupt typed accessors) is not violated: no generated accessor ever looks up a synthetic address.

### 2.3 New test file

`tests/test_registry_gc_eviction.py`, with the same `pytest.importorskip("phase4_roundtrip_cst", ...)` preamble as `test_phase4_rust_fixture.py:28-31` — the importorskip only. Node classes (`Entry`, `Identifier`) and the `_registry_*` wrappers are taken as attributes of the importorskip'd module object (`register_classes` exposes the classes on the extension module — `tests/rust_cst_fixture/src/cst.rs:4844-4861`). Do NOT copy the sibling file's `fltk.plumbing` / `generate_parser` module-level plumbing (`test_phase4_rust_fixture.py:36-55`): that adds registry-occupying module state to exactly the file designed to avoid it. Separate file (not appended to `test_phase4_rust_fixture.py`) because these tests are GC-discipline-sensitive and need their own conventions (explicit `del`, delta-based occupancy assertions) that don't apply to the rest of that file.

Test-authoring disciplines (documented in the file's module docstring):
- **Delta assertions, not absolutes.** The registry is process-wide and other tests (module-level parse fixtures in `test_phase4_rust_fixture.py`) may hold live entries. Assert presence/absence of addresses the test created, never total registry size == 0.
- **Snapshot dicts hold strong refs.** Every snapshot taken before an eviction check must be explicitly `del`'d (or scoped out) before `gc.collect()`.
- **Frame locals pin handles.** Drop every local referencing a handle (`del`) before asserting eviction. Helper functions that need to report which entry corresponds to a node return the int address only, never the handle.
- **Determinism.** CPython refcounting frees handles at last decref; `gc.collect()` is called anyway per request constraint. No timing dependence.
- **`id()` reuse.** After eviction, a freshly minted handle may reuse the dead handle's `id()`; tests must not assert `id(new) != id(old)`. Non-resurrection is established by asserting the address was absent from the snapshot at the dead point, plus correctness of the fresh handle.

Address-to-node mapping helper: `addr_of(node) -> int` = `next(k for k, v in _registry_snapshot().items() if v is node)` — the generator expression's snapshot is temporary and dropped on return.

Synthetic-address allocator for direct-wrapper tests: module-level `itertools.count(1)`; each test takes fresh addresses. The suite consumes a few dozen addresses — small integers far below any mappable heap address, so they cannot collide with real Arc addresses; weak eviction cleans entries up when test objects die regardless.

## 3. Tests

Classes/tests in `tests/test_registry_gc_eviction.py`:

**TestSnapshotPlumbing**
- `test_snapshot_maps_int_addr_to_handle`: create `Identifier()`; snapshot contains an int key whose value `is` the node.
- `test_py_new_registers_immediately`: create node; assert present in snapshot *before* any accessor read — pins the `py_new → force_register` natural path (request gap 2's hit half).

**TestEvictionAndFreshHandles** (real fixture nodes)
- `test_handle_dropped_entry_evicted`: create node, record `addr_of`, `del` node and any snapshot, `gc.collect()`, assert addr absent from fresh snapshot. Covers both eviction and the absence of a registry strong-ref leak (a strong ref would keep the entry alive forever).
- `test_arc_alive_handle_dead_fresh_handle_no_resurrection`: the core ABA scenario, strengthened — same address guaranteed, not just possible. `parent = Entry(); child = Identifier(); parent.append_key(child)`; record `addr = addr_of(child)`; `del child`; `gc.collect()`; assert `addr` absent (Arc still alive inside parent — entry must still evict because only the handle is weakly held); re-read `parent.child_key()` → fresh handle minted *at the same Arc address*; assert it is a live `Identifier`, `addr` present again, and `parent.child_key() is parent.children[0][1]` (new canonical is stable across accessors).
- `test_stress_create_drop_cycles`: loop ~200 iterations: create parent+child, read child back via two accessors, assert `is`-identity within the iteration, record addresses, drop all locals, `gc.collect()` (each iteration). After the loop: fresh snapshot contains none of the recorded addresses. Exercises natural allocator address reuse across iterations; asserts invariants hold, does not assert reuse occurred (per request — reuse cannot be forced deterministically from Python).

**TestDirectRegistrySemantics** (synthetic addresses + wrappers)
- `test_lookup_miss_register_hit`: `lookup(addr) is None`; `register_if_absent(addr, A) == True`; `lookup(addr) is A`.
- `test_register_if_absent_false_when_live_entry`: register A; `register_if_absent(addr, B) == False`; `lookup(addr) is A` (B not installed). Covers request gap 3's testable half.
- `test_force_register_overwrites_live_entry`: register A; `force_register(addr, B)`; `lookup(addr) is B`. Pins overwrite semantics (request gap 2).
- `test_weak_eviction_direct`: register A; `del A`; `gc.collect()`; `lookup(addr) is None` and addr absent from snapshot.
- `test_register_after_eviction_installs_fresh`: register A at addr; drop A; `gc.collect()`; `register_if_absent(addr, B) == True` (the dead weak entry does not block re-registration — CPython `WeakValueDictionary.setdefault` treats a dead value as absent); `lookup(addr) is B`.

Registered objects in direct tests are instances of a plain Python class defined in the test module (weakref-able; ints/None are not).

**Unreachable branch — documented, not tested.** The `registered == false` arm inside `get_or_insert_with` (`registry.rs:121-125`) requires another thread to install a handle between this thread's `lookup` miss and its `register_if_absent` — impossible under single-threaded CPython with the GIL held for the whole Rust call. It is not practically forceable from Python; per request gap 3, the test file documents this in a comment adjacent to `TestDirectRegistrySemantics` (the direct `register_if_absent`-returns-false test covers the same function-level contract the arm depends on).

## 4. Edge cases / failure modes

- **Registry occupancy from other tests / module fixtures.** Handled by delta assertions (§2.3). Recorded synthetic and real addresses cannot collide with pre-existing live entries: a live Arc's address cannot be re-handed-out by the allocator, and synthetic addresses are sub-page.
- **Snapshot/local strong refs defeating eviction.** Handled by explicit `del` discipline and address-only helpers (§2.3). A test bug here manifests as a deterministic failure ("addr still present"), not flakiness.
- **pytest assertion-rewrite temporaries.** Assertions evaluated before the `del`/`gc.collect()` sequence don't pin anything afterward; no assertion in any eviction test references a handle after its `del`.
- **Cross-cdylib registry split.** Wrappers in `fltk._native` would observe the wrong registry static; design places them in the fixture crate (§2.2). A comment in `registry_introspection.rs` records this so they are not "helpfully" moved later.
- **Non-weakref-able values.** `WeakValueDictionary` raises `TypeError` for non-weakref-able values; direct tests use a plain Python class. Generated node classes are already weakref-capable (the production registry stores them today).
- **`maturin develop` staleness.** Tests run against a stale fixture build silently lacking the new functions → `AttributeError` on `_registry_snapshot`, which is a clear failure mode; the importorskip reason already directs to `make build-test-user-ext`.
- **Feature unification.** `test-introspection` is additive and enabled only by the fixture crate (its own workspace, `tests/rust_cst_fixture/Cargo.toml:3`); it cannot leak into `fltk-native` or downstream builds via feature unification.

## 5. TODO bookkeeping

- Delete the `TODO(registry-unit-tests)` comment at `registry.rs:128-130` — its framing (Rust unit tests blocked by linking) was dropped by the approved reframe, and this work resolves the underlying coverage gap.
- Delete the `registry-unit-tests` entry from `TODO.md:31-33`. No residue remains to reframe: the entry's substance (the four functions tested only indirectly) is resolved by `TestDirectRegistrySemantics` + the eviction tests.

## 6. Verification

- New tests fail under mutation reasoning: e.g., if the registry held strong refs (swap `WeakValueDictionary` for `dict`), `test_handle_dropped_entry_evicted` and `test_weak_eviction_direct` fail; if eviction returned stale entries, `test_arc_alive_handle_dead_fresh_handle_no_resurrection` fails at the absent-addr assertion; if `force_register` used `setdefault`, `test_force_register_overwrites_live_entry` fails.
- `make build-test-user-ext`, then `uv run pytest tests/test_registry_gc_eviction.py` and full `uv run pytest`; `make fix`.
- `make check` clean — with one pre-existing caveat: its `cargo-test` step (`Makefile:46-47`, workspace `cargo test -q`) fails to link `fltk-cst-core` on machines lacking the unversioned `libpython3.10.so` symlink (§1, exploration §2). That failure predates and is unrelated to this change. Either create the symlink (install the Python dev package) before running `make check`, or run the other gate steps individually — `lint`, `format-check`, `typecheck`, `test`, `cargo-check`, `cargo-clippy`, `cargo-test-no-python`, `cargo-clippy-no-python`, `check-no-pyo3` (all of which must pass; only `cargo-test` links libpython) — and report the `cargo-test` skip explicitly. Do not attribute the link failure to this change.

## 7. Open questions

None. The one judgment call — feature-gating `snapshot` rather than unconditionally compiling it — follows directly from the request constraint that plumbing be "clearly test-only"; an always-compiled `pub fn snapshot` on a crate downstream extensions link would not be.
