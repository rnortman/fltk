Style: concise, precise, complete, unambiguous. No padding, no preamble.

Commit reviewed: 709c01d

## test-1

File: `tests/test_registry_gc_eviction.py:256`

`test_register_after_eviction_installs_fresh` ends without `del obj_b`. Unlike every other direct-wrapper test that ends with a `del obj`, this one leaves `obj_b` registered at a synthetic address with no cleanup. At 256 lines the omission has no effect on correctness because the test is the last line in the file, but it is inconsistent with the `del` discipline the module docstring mandates ("Drop every local referencing a handle (`del`) before asserting eviction"). The missing cleanup sets a bad precedent for future tests added to this class.

Consequence: if a future test appended after this one reuses the same `_synthetic_addr` counter value (impossible with `itertools.count`, but possible if the counter were reset), the live entry would cause a false `register_if_absent` returning False. More importantly it violates the documented discipline without visible reason, making the convention seem optional.

Fix: add `del obj_b` as the last line of the test.

## test-2

File: `tests/test_registry_gc_eviction.py:171`

`test_stress_create_drop_cycles` records addresses with `addr_of(child)` after `parent.append_key(child)`. The `parent.children[0][1]` access (line 171) calls `to_pyobject` via the `children` getter, which itself goes through `get_or_insert_with`. At this point `child` is already the canonical handle (registered by `py_new`), so `get_or_insert_with` returns it on a hit and `child_via_children is child_via_accessor is child` — the assertion at line 173 exercises identity between two wrap-out paths but not between either wrap-out and the original Python variable. The test would still pass even if `py_new` did _not_ call `force_register` (address not yet in registry) as long as both wrap-out calls hit the same entry on the first read. This is by design per the stress intent, but it means the test does not verify the `py_new → force_register` path — that is `test_py_new_registers_immediately`'s job. No coverage gap: coverage is split correctly. Recording note only.

No fix needed — observation for record only, not a gap.

## test-3

File: `tests/test_registry_gc_eviction.py:99-112`

`TestSnapshotPlumbing` has two tests that are nearly identical: both construct `Identifier()`, take a snapshot, and assert presence. `test_snapshot_maps_int_addr_to_handle` also asserts the key is `int`; `test_py_new_registers_immediately` also stores the address. The two tests cover slightly different aspects (key type vs address identity), but they duplicate the construction and snapshot overhead. Not a bug; not redundant enough to call a finding. Recording note only.

No fix needed.

## test-4

File: `tests/test_registry_gc_eviction.py:128-156`

`test_arc_alive_handle_dead_fresh_handle_no_resurrection` asserts `parent.child_key() is fresh` at line 155. At this point `fresh` holds the canonical handle just minted, and `parent.child_key()` calls `child_key` → `to_pyobject` → `get_or_insert_with`. Because `fresh` is still live, the second call hits the registry and returns the same `PyObject`, so `is` is True. This correctly pins that the fresh handle is stable across two wrap-out calls. However, the test does _not_ assert that `addr_of(fresh) == addr_of(parent.child_key())` — it only asserts `is`-identity. That is fine: `is`-identity is strictly stronger (same object ⟹ same address). No gap.

No fix needed.

## test-5

File: `tests/test_registry_gc_eviction.py:165-183`

`test_stress_create_drop_cycles`: `addr_of(child)` is called at line 176 after `del`-ing would be unsafe. Specifically, `child` is still live on line 176 (the `del` is on line 177), so `addr_of` works. But the `addr_of` helper calls `_registry_snapshot().items()` inline; the snapshot returned by `_registry_snapshot()` is a temporary that lives until the generator is exhausted (which happens inside `next(...)` inside `addr_of`), so it is dead before the call to `gc.collect()` on line 178. No discipline violation.

No fix needed — observation for record only.

## test-6

File: `tests/test_registry_gc_eviction.py:202-210`

`test_lookup_miss_register_hit` calls `del obj` at the end, but the `assert _registry_lookup(addr) is obj` at line 209 has already executed, leaving `obj` registered at `addr` in the WeakValueDictionary until `del obj` triggers eviction. The `del obj` fires CPython refcount drop immediately (no cycle), evicting the entry. The test does not assert that the entry is evicted after the `del` — that behavior is covered by `test_weak_eviction_direct`. Consistent with the limited scope of this particular test. No gap.

No fix needed.

## Summary

One genuine finding (test-1): missing `del obj_b` at end of `test_register_after_eviction_installs_fresh`. All other observations are confirmations that no gap exists. The plumbing changes (feature gate, `registry_introspection.rs`, `lib.rs` wiring) are minimal and correct. The test-authoring disciplines documented in the module docstring are followed throughout — delta assertions, explicit `del` before GC, snapshot lifetime control — with the single exception of test-1.
