Commit reviewed: 1eb2580 (3d03b61 + 1eb2580)

## Presence

All four changed emitter shapes have corresponding Python-level test coverage in `TestFilterUnderGuardRegression`:
- `children_<label>`: `test_children_label_filters_correctly`
- `child_<label>`: `test_child_label_raises_with_exact_count`, `test_child_label_returns_unique_match`
- `maybe_<label>`: `test_maybe_label_raises_when_multiple`, `test_maybe_label_returns_unique_match`
- `child()`: `test_generic_child_raises_with_exact_count`
- Arc/node clone path: `test_accessor_identity_registry_pin`

Existing tests (`TestItemsMethods`, `TestGenericMethods`, `TestArcSharingNodeSpan`, `test_fegen_rust_cst.py::TestExtendAndMaybe`) cover the happy paths, empty-node error paths, and general maybe/child semantics for both Span and node children.

## Findings

**test-1**
File: `tests/test_rust_cst_poc.py` — `TestFilterUnderGuardRegression`
What: No test exercises `child_<label>()` or `maybe_<label>()` on a non-empty node where zero children have the requested label. The existing `TestItemsMethods.test_item_label` covers count==0 only on an empty node (zero total children). The new regression class focuses on multi-match and single-match-among-non-matching, but skips the zero-match-among-non-matching path.
Consequence: The code path `(count=0, first=None) → count != 1 → raise "have 0"` (for `child_<label>`) and `(count=0, first=None) → first is None → Ok(None)` (for `maybe_<label>`) are never exercised in the filter-under-guard scenario this diff specifically introduces. A bug that accidentally included non-matching children in the count would not be caught.
Fix: Add two tests to `TestFilterUnderGuardRegression`: (1) node with only `no_ws` children, `child_item()` raises `"Expected one item child but have 0"`; (2) node with only `no_ws` children, `maybe_item()` returns `None`.

**test-2**
File: `tests/test_rust_cst_poc.py` — `TestFilterUnderGuardRegression.test_accessor_identity_registry_pin`
What: The registry-pin test has only one child (an `Identifier`) in the node with no non-matching siblings. It verifies the Arc/WeakValueDict path in isolation, but does not verify that the identity guarantee holds when the node-typed child is surrounded by non-matching entries (the mixed-Vec scenario this diff specifically optimizes).
Consequence: A bug where the filter incorrectly passed a different matching child's Arc to `to_pyobject` on second call (e.g., off-by-one in the guard loop) would not disturb this test, since there is only one item child.
Fix: Extend the identity test (or add a sibling) to place the `Identifier` child between two `no_ws` Span children before asserting `r1 is r2`. Small change; same fixture structure as `test_child_label_returns_unique_match`.

**test-3**
File: `tests/test_rust_cst_poc.py:321-322` — `TestItemsMethods.test_item_label`
What: Pre-existing, not introduced by this diff, but adjacent: `pytest.raises(ValueError)` without `match=` for the `child_item()` zero-children error. The new regression tests introduced by this diff consistently use `match=` to pin the exact message. The pre-existing test does not.
Consequence: A message regression (wrong count, wrong label name) in the `child_<label>` zero case would not be caught by this test. Low consequence given the new regression tests pin count==5; the zero case is separately covered only weakly.
Fix: Add `match="Expected one item child but have 0"` to the existing `pytest.raises(ValueError)` at line 321. (Same pattern applied to lines 325, 342, 346, 363, 367, 384, 388 for consistency, though those are lower priority.)
