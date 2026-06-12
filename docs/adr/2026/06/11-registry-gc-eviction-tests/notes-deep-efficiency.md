# Efficiency review — registry-gc-eviction-tests (8ec5324..709c01d)

Style: concise, precise, complete, unambiguous. No padding. Audience: LLM/human reviewer.

Scope reviewed: `crates/fltk-cst-core/{Cargo.toml,src/registry.rs}`, `tests/rust_cst_fixture/{Cargo.toml,src/lib.rs,src/registry_introspection.rs}`, `tests/test_registry_gc_eviction.py`. Production builds unaffected: `test-introspection` is off by default and enabled only from the fixture crate's own workspace, so no feature-unification path adds the `snapshot` code or its `PyDict` import to `fltk-native` or downstream extensions. The only runtime surface this change touches is test execution.

## Findings

### efficiency-1: per-iteration full `gc.collect()` in the 200-iteration stress loop

- File: `tests/test_registry_gc_eviction.py:177` (`test_stress_create_drop_cycles`, `gc.collect()` inside the `for _ in range(200)` loop).
- Problem: each iteration runs a full (gen-2) collection. Nothing in the iteration depends on it: the identity assertions run while the objects are still alive, the handles are freed deterministically by refcounting at the `del` on the previous line (the module docstring itself states this), and the only eviction assertion is after the loop. The per-iteration collection therefore validates nothing that a single post-loop `gc.collect()` would not.
- Consequence: full-collection cost scales with the total number of live objects in the pytest process, not with this test's objects. Under `uv run pytest` (full suite, module-level parse fixtures, imported generators) each pass is on the order of milliseconds-to-tens-of-milliseconds; ×200 this single test can add seconds of wall time, and the cost grows as the suite grows. Bites on every full-suite run and in CI.
- Fix: move `gc.collect()` out of the loop — one call after the loop, before the final snapshot, preserves every assertion. If the intent is to interleave collection with allocator reuse, collect every N (e.g. 50) iterations and say so in a comment. Note: the design (§ test list) specifies "gc.collect() (each iteration)", so this is a design-level choice to revisit, not an implementer deviation.

### efficiency-2: `addr_of()` copies the entire registry per call

- File: `tests/test_registry_gc_eviction.py:64-71` (`addr_of`), called once per stress-loop iteration plus in the eviction tests.
- Problem: each call materializes a full `dict` copy of the process-wide registry (`_registry_snapshot()`) and linearly scans it to find one node. Overly broad: whole-registry copy to answer a single reverse lookup.
- Consequence: cost is O(live registry size) per call, ~200 calls in the stress test. Today the registry stays small (delta-bounded, evicted per iteration), so the cost is negligible — this is a scale-ceiling note, not a current cost: if future suites keep many live handles (e.g. module-scoped parsed trees), the stress test becomes O(iterations × registry size). Bites only if registry occupancy grows.
- Fix: none required now. If it ever matters, expose a direct `_registry_addr_of(obj)` wrapper (reverse scan in Rust without building a Python dict), or accept as-is — the snapshot is currently the only Python-visible address source, and adding plumbing preemptively is not justified.

No other findings. No unnecessary existence checks, no missed concurrency (tests are intentionally single-threaded; the GIL-interleaving branch is documented unreachable), no recurring no-op updates, no unbounded growth (`recorded_addrs` is bounded at 200; all snapshots are `del`'d).

Commit reviewed: 709c01d
