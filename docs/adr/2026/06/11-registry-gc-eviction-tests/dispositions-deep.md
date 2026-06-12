# Dispositions — registry-gc-eviction-tests deep review

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Commit reviewed: 709c01d. Fixes applied at: 04c41c6.

---

## errhandling-1

- Disposition: Fixed
- Action: `tests/test_registry_gc_eviction.py:61-75` — `addr_of` now uses `next(..., None)` sentinel; raises `AssertionError(msg)` (msg assigned to variable to satisfy EM102) with `repr(node)` context on miss.
- Severity assessment: The bare `StopIteration` would have masked registration bugs (e.g. `force_register`/`py_new` failure) behind an unhelpful traceback pointing at the helper rather than the invariant violated.

---

## errhandling-2

- Disposition: Won't-Do
- Action: no change
- Severity assessment: Pre-existing code not introduced by this diff; `expect` on an invariant violation is the correct panic path. No new issue.
- Rationale: The finding itself states "Not a finding against this diff"; the `.expect` is intentionally correct for an invariant violation. Changing it would be out of scope.

---

## errhandling-3

- Disposition: Fixed
- Action: `tests/test_registry_gc_eviction.py:174-176` — structural assertion `len(parent.children) == 1 and len(parent.children[0]) == 2` added before the double-index access in `test_stress_create_drop_cycles`.
- Severity assessment: Without the guard, a structural bug in `append_key` or the `children` accessor would produce `IndexError` in the stress test rather than a targeted assertion failure, obscuring the root cause.

---

## correctness-1

- Disposition: Fixed
- Action: `crates/fltk-cst-core/src/registry.rs:134-148` — `snapshot` now calls `registry.call_method0("items")?` and passes the result to `dict_class.call1(...)` instead of passing `registry` directly. Doc comment updated to explain the TOCTOU hazard.
- Severity assessment: Latent: `dict(WeakValueDictionary)` does `keys()` then `__getitem__` per key; `__getitem__` raises `KeyError` if the weakref dies mid-copy (possible if an allocation triggers cyclic GC). Not currently triggerable (fixture nodes are non-cycle-tracked; test `_Obj` instances are acyclic), but would cause flaky `KeyError` misattributed to the registry if a future test registers cycle-participating objects. `WeakValueDictionary.items()` skips dead entries atomically per entry, eliminating the race.

---

## test-1

- Disposition: Won't-Do
- Action: no change
- Severity assessment: Nil — `del obj_b` is present at line 256 (the last line of the test). The finding is factually incorrect; the reviewed code already has the cleanup.
- Rationale: Verified by direct inspection of `tests/test_registry_gc_eviction.py:256`. The convention is followed.

---

## test-2 through test-6

- Disposition: Won't-Do (observation-only findings; reviewer stated "no fix needed" for each)
- Action: no change
- Severity assessment: Informational record entries only; no correctness or quality gap identified by the reviewer.

---

## efficiency-1

- Disposition: Won't-Do
- Action: no change
- Severity assessment: The per-iteration `gc.collect()` is a design-mandated choice (design §3: "gc.collect() (each iteration)"). The efficiency reviewer acknowledged this and framed it as "a design-level choice to revisit, not an implementer deviation." No implementation fix is appropriate; the design chose it deliberately.

---

## efficiency-2

- Disposition: Won't-Do
- Action: no change
- Severity assessment: Reviewer stated "Fix: none required now" — a scale-ceiling note only. Current registry occupancy is small (delta-bounded, evicted per iteration). Adding preemptive plumbing is not justified.
