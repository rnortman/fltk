Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

---

## Findings

**test-1** — `tests/test_rust_cst_poc.py:730` (TestAppendAndAccessors.test_append_name_and_child_name)

`child_name()` returns the raw child value extracted from the tuple (index 1), not the whole `(label, child)` tuple, so `assert node.child_name() == s` passes. But `child()` (generic) returns the full `(label, child)` tuple, and test_generic_child_one asserts `tup == (Identifier.Label.NAME, s)`. This is fine — the two behaviors are intentionally different. No bug here, but the inconsistency is untested: there is no test confirming `child_name()` returns *only* the value (not the tuple). The current test passes vacuously if the implementation happened to return the tuple AND the span compared equal to the tuple (it wouldn't, but the assertion is underspecified). Fix: add `assert not isinstance(node.child_name(), tuple)` or equivalently `assert type(node.child_name()) is Span` to the round-trip test. Consequence: a future refactor changing `child_name()` to return the full tuple (matching `child()` semantics) would not be caught.

**test-2** — `tests/test_rust_cst_poc.py:913-932` (TestItemsMethods.test_item_label)

The four `test_*_label` methods each test `children_*` with a single-element list and `extend_*` with a two-element list, but no test verifies that `children_*` *filters by label* — i.e., that when a node has children with mixed labels, `children_item()` returns only `ITEM`-labeled ones and not `NO_WS`-labeled ones. The only filtering test is `TestNoneLabelFiltering` for the `Identifier.children_name` case. The `Items` node has four labels and the cross-label exclusion behavior for `Items` label methods is not tested. Consequence: a bug where `children_item()` returns all children regardless of label would pass the entire `TestItemsMethods` suite.

**test-3** — `tests/test_rust_cst_poc.py:802-812` (TestGenericMethods.test_generic_child_one)

The `child()` return-value test only checks the tuple content when there is exactly one child. There is no test verifying `child()` returns a two-element tuple structure (i.e., index 0 is the label, index 1 is the value) — the assertion `tup == (Identifier.Label.NAME, s)` does cover this via Python tuple equality, so this is adequately covered. No finding.

**test-4** — `tests/test_rust_cst_poc.py:669` (TestLabelSemantics — label-vs-None comparison)

AC-27 is covered for `children_name` filtering but the more primitive assertion — that `Identifier.Label.NAME != None` — is never directly tested. The design calls out that PyO3's `__richcmp__` returns `NotImplemented` for cross-type comparisons including `None`, and this falling back to `False` is load-bearing for the filtering logic. If the cross-type comparison returned `True` (or raised), `children_name()` would break. The existing AC-27 test exercises this path indirectly, but only through `children_name`. Consequence: if the `__richcmp__` fallback behavior changes (e.g., a PyO3 version upgrade introduces `NotImplemented` -> exception instead of `False`), AC-27 could still pass if the test data has no `None`-labeled children mixed with non-`None`-labeled ones in a way that triggers the comparison. Direct test: `assert Identifier.Label.NAME != None` (also `assert (Identifier.Label.NAME == None) is False`). Adds < 3 lines; explicitly documents the PyO3 contract being relied on.

**test-5** — `tests/test_rust_cst_poc.py:866-891` (TestEquality — cross-type comparison)

`__eq__` is designed to return `NotImplemented` for non-`Identifier` arguments (design sec. `__eq__`). This triggers Python's reflected `__eq__` on the other side, giving correct cross-type `!=`. There is no test that `Identifier() != Items()` or `Identifier() != "string"` or `Identifier() != None`. The design explicitly calls out "Comparison with non-node types returns NotImplemented" as a requirement (AC-23 area). The tests only cover same-type comparisons (equal, different children, different span). Consequence: a mistaken `is_instance_of::<Items>()` check in `Identifier.__eq__` returning `True` instead of `NotImplemented` would go undetected, causing `Identifier() == Items()` to return `True` (or raise) in production.

**test-6** — `tests/test_rust_cst_poc.py:848-863` (TestSpanField)

`span` has both `get` and `set`. The getter is tested. The setter test (AC-21) assigns and reads back, confirming the field changed. However, there is no test that constructing with an explicit `span=` keyword stores the provided value: `node = Identifier(span=s); assert node.span == s`. The current tests only check the default (AC-22) and post-construction assignment (AC-21). The keyword-only construction path is used by the parser (`Identifier(span=Span(start=pos, end=-1))`). Consequence: a bug in `#[pyo3(signature = (*, span=None))]` handling where the provided span is ignored and UnknownSpan is always used would not be detected.
