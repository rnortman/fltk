# Deep correctness review — registry-gc-eviction-tests

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Commit reviewed: 709c01d (base 8ec5324). Files: `crates/fltk-cst-core/{Cargo.toml,src/registry.rs}`, `tests/rust_cst_fixture/{Cargo.toml,src/lib.rs,src/registry_introspection.rs}`, `tests/test_registry_gc_eviction.py`, `TODO.md`.

## Verification performed

- Ran the suite against the built fixture: `uv run pytest tests/test_registry_gc_eviction.py -q` → 10 passed in 0.56s. (709c01d is an ancestor of working HEAD; the reviewed files are byte-identical at HEAD.)
- Traced every test's logic against the actual fixture code, not just the design's claims:
  - `Identifier()`/`Entry()` zero-arg construction valid: `py_new` signatures are `(*, span = None)` (`tests/rust_cst_fixture/src/cst.rs:1276`, `:2936`); both call `registry::force_register` on the fresh `Shared`'s `arc_ptr()` — `test_py_new_registers_immediately` pins the intended path.
  - `append_key` → `EntryChild::extract_from_pyobject` (`cst.rs:848-905`) clones the child's `inner` `Shared` (same Arc, same `arc_ptr()`), so after `del child; gc.collect()` the parent holds only the Arc, never the handle. Eviction assertion in `test_arc_alive_handle_dead_fresh_handle_no_resurrection` is sound, and `new_addr == addr` is guaranteed (cloned Arc → identical `Arc::as_ptr`), matching the design's "same address guaranteed" claim.
  - `child_key` (`cst.rs:1470-1494`) requires exactly one `Key`-labeled child; the test appends exactly one. `parent.child_key() is fresh` holds via `get_or_insert_with` registry hit.
  - `register_if_absent` uses `WeakValueDictionary.setdefault` + identity compare (`registry.rs:66-74`); CPython's `setdefault` treats a dead weakref value as absent, so `test_register_after_eviction_installs_fresh` tests real semantics, not an accident of ordering.
  - Stress-test final assertion is sound against address reuse: a recorded address can be reused only while no live Arc occupies it, and any reuse within the test is dropped before the final snapshot; pre-existing live entries (other test files' module state) pin their Arcs, so their addresses can never appear in `recorded_addrs`. Delta-assertion discipline holds.
  - Pytest assertion-rewrite temporaries do not pin handles: modern pytest clears `@py_assert` temps after each assert, and this is confirmed empirically — if the stress loop's identity-assert temps lingered, the final iteration's child would survive to the closing snapshot and the test would fail; it passes.
  - `addr_of`'s generator-expression snapshot cannot pin handles past the call: the genexpr is a temporary argument to `next()`, decref'd on return, clearing its frame (and the snapshot dict).
  - Synthetic addresses (counter from 1) cannot collide with heap Arc addresses (sub-page integers); wrapper doc comments preserve the `force_register` caller contract (`registry.rs:87-91`) by construction.
  - Feature plumbing: `test-introspection = ["python"]` (`crates/fltk-cst-core/Cargo.toml`) enabled only via the fixture's `python` feature; fixture is its own workspace, so no unification leak into `fltk-native`. `make cargo-test-no-python` builds `fltk-cst-core --no-default-features`, under which `registry` (and the new cfg) is not compiled at all — gate change is inert there.
  - TODO bookkeeping matches design §5: `TODO(registry-unit-tests)` comment and `TODO.md` entry both removed; no orphaned slug remains (grepped).

## Findings

### correctness-1

- **File:line:** `crates/fltk-cst-core/src/registry.rs:134-139` (`snapshot`)
- **What's wrong:** `dict(WeakValueDictionary)` is a check-then-act copy: CPython's `PyDict_Merge` for a non-dict mapping materializes `keys()` then calls `__getitem__` per key. `WeakValueDictionary.__getitem__` raises `KeyError` if the weak value died between the two steps.
- **Why:** The gate change makes this previously dead (`#[cfg(test)]`-only, never linked) function live in the fixture extension, so its behavior is now reachable from Python tests. The death window can open only if an allocation inside the `dict()` construction triggers cyclic GC that collects a registered handle. **Not triggerable today:** generated node handles are `#[pyclass(frozen, weakref)]` without traverse/subclass support (not GC-tracked; die only at decref, impossible mid-call with the GIL held and no threads), and the test file's `_Obj` instances are never placed in reference cycles.
- **Consequence:** Latent, not current-behavior: if a future test registers an object that participates in a reference cycle (e.g. a richer `_Obj`), `_registry_snapshot()` can intermittently raise `KeyError` mid-copy — a flaky infrastructure failure misattributed to the registry under test. No production impact (feature is test-only and off by default).
- **Suggested fix:** Copy via `registry.items()` instead of the mapping protocol — `WeakValueDictionary.items()` dereferences each weakref itself and skips dead entries atomically per entry: `dict_class.call1((registry.call_method0("items")?,))`.

No other findings: loop bounds, identity/`is` semantics, eviction ordering, del discipline, wrapper signatures (`usize`/`bool`/`Option<PyObject>` conversions), and module registration in `lib.rs` all check out.
