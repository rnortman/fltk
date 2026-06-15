# Test Review — fix-forged-abi-segfault

Commit reviewed: 79460b6

---

test-1
File: tests/test_rust_span.py:916 (`test_forged_source_text_message_is_diagnostic`)
What: The message assertion is a disjunction — `"basicsize" in msg.lower() or "layout" in msg.lower()`. The word "layout" appears in every `check_abi_pair` error message (e.g. "layout mismatch"), so this assertion passes even if `check_instance_layout` never fires and `check_abi_pair` is the gate that rejects (which it isn't for this input, but the logic does not prove that). The intent is to verify that the NEW basicsize gate fires specifically; the disjunction lets the old gate satisfy the assertion.
Consequence: If the ordering is accidentally inverted (basicsize gate runs first, rejected by `check_abi_pair` instead — impossible with this input since `check_abi_pair` passes on a forge that has both attrs set correctly, but this matters for a forge with only one attr), or if future refactoring causes `check_abi_pair` to fire instead, the test stays green while the basicsize gate is broken or absent.
Fix: Pin the message substring that only `check_instance_layout` emits. The helper's error contains `"__basicsize__"` and `"not a genuine SourceText allocation"`. Assert at least one of those is present: `assert "__basicsize__" in msg or "not a genuine SourceText" in msg`. The disjunction "basicsize or layout" is too weak for a message that is uniquely identifiable.

---

test-2
File: tests/test_rust_span.py:862 (`TestForgedSourceTextRejected` class)
What: The design (§3, "exotic-type" edge case) requires that a `__getattr__`-raising or `__basicsize__`-missing exotic type surfaces a `TypeError` from `check_instance_layout` rather than unwrapping or panicking. The implementation's `map_err` handles this. There is no test exercising that path. The existing `FakeSourceNoLayout` test (`test_source_text_abi_layout_missing_raises`, line 803) tests missing `_fltk_cst_core_abi_layout`, not missing `__basicsize__`, so it does not cover this branch.
Consequence: A regression in `check_instance_layout`'s `map_err` handling (e.g., an `unwrap()` replacing `map_err`) would panic/abort rather than raise TypeError. The panic path is not guarded by any test.
Fix: Add a test that passes an object whose type raises on `__basicsize__` access (a metaclass with `__getattr__` that raises), or — simpler — a `types.SimpleNamespace` instance (which has no `__basicsize__` on its type in the slot sense but does have it via the MRO). More directly: a class using `__class_getitem__` tricks is fragile; instead, create a fake metaclass that raises `AttributeError` on `__basicsize__` and verify that `_with_source_unchecked` raises `TypeError` with a message containing `"not readable"` or `"getattr raised"`. Subprocess isolation applies since this calls `_with_source_unchecked`.

---

test-3
File: tests/test_rust_span.py:887 (`test_forged_source_text_raises_type_error`)
What: The test asserts `result.returncode == 0` and `"OK" in result.stdout`. It does not assert that `result.stderr` is empty or that no traceback was printed. A future change that raises the right exception type but also prints an unhandled secondary error (e.g. a panic message to stderr from a different path) would pass the test while silently producing noisy output.
Consequence: Low severity, but a crash that produces returncode 0 + "OK" stdout via some early-exit trick (unlikely but possible with atexit/signal handlers) would not be caught. More practically, the absence of a `returncode == -11` assertion before the fix is not checked — the test comment says "Before the fix, subprocess exited with -11" but nothing in the test would catch if the test is somehow run pre-fix. This is acceptable (it's a regression test, not a bisect tool), but the missing stderr check is worth noting.
Consequence: Noisy test output for future regressions goes undetected by the assertion; not a correctness hole.
Fix: Add `assert result.returncode != -11, "SIGSEGV recurrence"` as a secondary assertion before the main returncode check, to make a segfault regression produce an explicit message rather than just "returncode -11 != 0". Optionally add `assert not result.stderr` or `assert "Traceback" not in result.stderr` to catch secondary noise.

---

test-4
File: tests/test_rust_span.py:976 (`test_foreign_source_text_basicsize_matches_native_layout`)
What: This test is skip-guarded on `phase4_roundtrip_cst`. The design (§4.2) designates it as the direct pin of the gate's accept-branch precondition — if a CI lane always skips it (phase4 not built), the precondition is never verified and a future change breaking cross-cdylib basicsize equality would not be caught by this test. The design acknowledges this ("A CI lane where this test is always skipped is a gap, not a pass") but the existing skip comment on line 389 is on a different test; this new test's skip message does not carry that warning.
Consequence: The accept-branch precondition pin is silently absent in CI lanes that do not build `phase4_roundtrip_cst`. This is a known structural gap (cross-cdylib fixture dependency), not a test-quality bug per se, but the skip message should reflect that skipping means the gate precondition is unverified, not just that the fixture is unavailable.
Fix: Update the `reason=` string to: `"phase4_roundtrip_cst not built; run 'make build-test-user-ext' first — skipping this test means the basicsize gate's accept-branch precondition is unverified in this lane"`. This matches the comment convention already present at line 389.

---

No findings on: subprocess isolation (correctly applied to the crash repro), the ordering of `check_abi_pair` before `check_instance_layout` (preserved; existing pinned-message tests at lines 308–383 and 789–845 remain green because `check_abi_pair` fires first for those inputs), the padded-forge boundary test (correctly does NOT call `_with_source_unchecked` and explains why), and the cache-hit path (covered transitively via the existing `TestSpanToPyobjectCaching` suite and the foreign-cdylib accept tests).
