Style: concise, precise, complete, unambiguous. No padding, no preamble.

Commit reviewed: f904540
Base: dd52073

## test-1

File: tests/test_cst_mutators_parity.py, TestErrorBehavior (lines 460-495)

`test_bad_child_type_insert` and `test_bad_child_type_replace_at` assert only `TypeError` with no message check. The design pins the exact message text: `"{ClassName}: unsupported child type {type}"` (§2.2). `TestMessageParity` tests bad-label message parity but has no counterpart for bad-child message parity. A backend difference in the type-name rendering (e.g. `str` vs `<class 'str'>` or differing `type(x).__name__` output) would silently diverge.

Consequence: cross-backend bad-child-type message drift is undetected. The design explicitly pins this text (§2.2) and describes it as a parity surface.

Fix: add `test_bad_child_type_message_parity` to `TestMessageParity` in the same style as `test_bad_label_insert_message_parity`: capture both backends' TypeError messages and assert equality.

---

## test-2

File: tests/test_cst_mutators_parity.py (no test exists)

The design specifies a `"no labels defined for this node"` error path for label-free nodes (§2.2, §2.4). The `_check_label_type_for_mutators` helper in generated Python code emits this path; the Rust generator also emits it (gsm2tree_rs.py line 1086). Neither `test_cst_mutators_parity.py` nor `test_gsm2tree_py.py` tests the runtime behavior when a non-`None` label is passed to a label-free node's mutators. The fegen CST happens to have no label-free node classes, so this path is never exercised at all through the parity tests.

Consequence: the `"no labels defined"` TypeError path is a dead-end for test coverage. If the generated error message drifts between Python and Rust, or if the path has a bug (wrong class name in message, wrong format string), no test catches it.

Fix: add a test in `TestErrorBehavior` (or a `TestLabelFreeNodeErrors` class) that instantiates a generated label-free node (e.g. via the PoC grammar's zero-label fixture used in generator tests), calls `insert(0, child, label="bad")` on it, and asserts:
1. `TypeError` is raised.
2. The message matches `r"Foo\.insert: no labels defined for this node; got str label"` (or equivalent for the generated class name).
Both backends should be tested.

---

## test-3

File: tests/test_cst_mutators_parity.py, TestErrorBehavior lines 475-495

The three `test_non_index_*_raises_type_error` tests accept `(TypeError, AttributeError)`. The design says the error type for a non-indexable index is `TypeError`, with "type pinned, text not" (§2.2, error table). Permitting `AttributeError` means the tests don't pin the type. If the Rust backend started emitting `ValueError` or some other exception, these tests would still pass.

Consequence: exception-type for non-indexable index is not actually pinned. The design's claim that type is pinned is undermined.

Note: the `AttributeError` allowance may be correct in practice — PyO3's `call_method0("__index__")` raises `AttributeError` when the method doesn't exist. If this is intentional and the backends are expected to diverge in exception type, the test comments say "or AttributeError on Rust" which is accurate. In that case, the design table entry "TypeError | ... type pinned" is inaccurate and should say "(TypeError or AttributeError)". Either the test or the design should be tightened to be internally consistent.

Fix (option A — tighten to match reality): update the design table to say "TypeError or AttributeError (backend-specific)". No test change needed.
Fix (option B — pin TypeError): update the Rust backend to convert AttributeError → TypeError for non-indexable index (catching the AttributeError from `__index__` lookup and re-raising TypeError), then update the tests to accept only `TypeError`.

---

## test-4

File: tests/test_cst_mutators_parity.py, TestMixedOperationsParity (lines 579-627)

`test_mixed_operations_identical_structure` uses `_children_equal` which compares spans by `start/end` values (lines 62-71). For span-bearing children this is correct. However, the fegen CST `Identifier` node's children are spans only — the mixed-operations test never exercises a node where children include sub-nodes (non-span `Identifier`-type children). Design §4.2 says parity is checked for "kind/label/span sequences." A multi-level tree (node with node-typed children) is not exercised in the mixed sequence test.

Consequence: a mutation-after-mutation regression that only manifests with node-typed children (e.g. an `Items` node whose children include `Identifier` sub-nodes) would not be caught by the mixed-operations parity test.

Fix: add one mixed-operations parity test using `Items` (which has an `Identifier`-type child via the `item` label), building both backends' trees in parallel and comparing via `children_equal` extended to recursively compare node identity or structure.

---

## test-5

File: tests/test_cst_mutators_identity.py, lines 156-185 (TestClearRegistryEviction)

`test_clear_then_drop_evicts_registry_entry` tests `clear()` eviction. There is no parallel test for `remove_at` eviction: take a handle, confirm it's in the registry, call `remove_at`, drop the handle, GC, assert the registry entry is absent. Design §4.3 lists this as a separate property ("Removed child re-inserted..." covers re-insertion but not drop-after-removal without re-insertion).

Consequence: `remove_at`'s "no retained strong handle" guarantee is not directly pinned. If `remove_at`'s Rust implementation accidentally retained a strong `Arc` reference in a local variable that outlived the guard drop, the registry would not self-evict and the bug would be invisible to the current tests (which only check `remove_at` identity and `clear` eviction, not `remove_at` eviction).

Fix: add `test_remove_at_then_drop_evicts_registry_entry` to `TestClearRegistryEviction` mirroring the existing test but calling `remove_at(0)` and discarding the return value before dropping the handle and asserting eviction.

---

## test-6

File: tests/test_cst_mutators_parity.py, TestReplaceAt (lines 320-408)

`replace_at` has no large-negative out-of-range test. `test_replace_at_large_out_of_range` tests `10**25` but not `-(10**25)`. Both directions exercise the beyond-`i64` clamp logic on both backends; the asymmetry leaves the negative-overflow code path for `replace_at` untested by parity tests. (By contrast, `remove_at` has both `test_remove_at_large_positive_out_of_range` and `test_remove_at_large_negative_out_of_range`.)

Consequence: a backend bug in the negative-overflow `replace_at` path (e.g. treating `-(10**25)` as index `0` instead of raising `IndexError`) would not be caught.

Fix: add `test_replace_at_large_negative_out_of_range` to `TestReplaceAt` matching the pattern of `test_replace_at_large_out_of_range` but with `big = -(10**25)`.
