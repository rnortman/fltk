# Error-handling review: registry GC/eviction tests

Commit reviewed: 709c01d

Style: concise, precise, complete, unambiguous. No padding, no preamble.

---

## errhandling-1

**File:line:** `tests/test_registry_gc_eviction.py:67`

**Broken path:** `addr_of` raises `StopIteration` when `node` is not present in the registry snapshot.

**Why:** The `next(... for ... in ...)` call with no default raises `StopIteration` if the comprehension finds no match. This propagates uncaught through every call site: `test_handle_dropped_entry_evicted:121`, `test_arc_alive_handle_dead_fresh_handle_no_resurrection:137,150`, `test_stress_create_drop_cycles:176`. pytest converts `StopIteration` to a generic `FAILED` with a traceback pointing at `addr_of` rather than at the assertion that would clarify which test invariant was violated.

**Consequence:** If a `py_new`-path registration bug means the node is not in the registry, the error manifests as `StopIteration` from `addr_of` — an unhelpful error that masks whether the failure is "node was never registered" (a bug in `force_register`/`py_new`) vs. "snapshot missed it for another reason." On-call cannot distinguish a plumbing failure from a test-authoring defect without inspecting the call stack.

**Fix:** Add a default sentinel and raise `AssertionError` with context, e.g.:
```python
addr = next((k for k, v in _registry_snapshot().items() if v is node), None)
if addr is None:
    raise AssertionError(f"node {node!r} not found in registry snapshot")
return addr
```

---

## errhandling-2

**File:line:** `crates/fltk-cst-core/src/registry.rs:122-124`

**Broken path:** The `expect` on the re-lookup inside `get_or_insert_with`'s race branch is the right call for an invariant violation, but the comment and the surrounding code make a claim ("entry must be live — unwrap is correct") that is only conditionally true and deserves a tighter note.

**Why:** The comment says "Race (single-threaded Python: unreachable in practice)" and then proceeds to `.expect(...)`. This is preexisting code, not introduced in this diff — the diff only removes the `TODO` comment above it and changes the `snapshot` cfg gate. No change to the panic path itself. No new issue introduced by this diff on this path.

**Status:** Not a finding against this diff — the `expect` was already present and is intentionally correct for an invariant violation. Noted for completeness only; the diff did not touch this logic.

---

## errhandling-3

**File:line:** `tests/test_registry_gc_eviction.py:171`

**Broken path:** `parent.children[0][1]` in `test_stress_create_drop_cycles` — the index access `[0]` raises `IndexError` if the append did not produce any children, and `[1]` raises `IndexError` if the tuple has fewer than two elements. Neither case is asserted before access.

**Why:** Both failures would raise `IndexError` rather than an assertion failure, and the error message would not clarify whether `append_key` failed silently, the accessor returned the wrong shape, or the fixture schema changed. The test discipline document in the module docstring is about handle identity, not about structural preconditions, so this gap is not covered by any stated convention.

**Consequence:** A structural bug in `append_key` or the `children` accessor would produce `IndexError` in the stress test, defeating the stated purpose of the test (asserting `is`-identity via the two access paths). The failure message would not distinguish a registry bug from a structural accessor bug.

**Fix:** Add an assertion before the double-index access:
```python
assert len(parent.children) == 1 and len(parent.children[0]) == 2, (
    "unexpected children shape after append_key"
)
```
Or use the dedicated accessor exclusively (`parent.child_key()`) for the children-via-children path and add a shape assertion only once at the top of the loop.

---

No other error-handling findings. The `?` propagation in `registry_introspection.rs` correctly surfaces `PyResult` errors to Python as exceptions. The `let _ =` pattern does not appear. Broad catch and silent-fallback patterns are absent. The `register_if_absent` / `force_register` wrappers correctly propagate all `PyResult` errors without swallowing.
