Concise. Precise. Complete. Unambiguous. No padding.

Commit reviewed: 6ac52d5

---

test-1
File: tests/test_nullable_loop_guard.py — TestPythonGuardPlacement
What: `test_plus_loop_has_guard` asserts `"if one_result.pos == pos:"` is present in `ast.unparse` output but never asserts `break` appears after it. `ast.unparse` squashes multi-line ifs onto one line only for simple bodies, but the test would pass if something other than `break` followed the condition — e.g., a `pass` or a misplaced statement. The condition check is necessary but not sufficient.
Consequence: A future refactor that changes what executes inside the guard (say, a `continue` or a wrong statement) would not be caught — the test verifies presence of the condition expression, not the termination behavior.
Fix: Add `assert "if one_result.pos == pos:\n    break" in src` (or after `ast.unparse` normalization, check that `"if one_result.pos == pos:break"` or the equivalent one-liner appears), mirroring the stricter string check the Rust test already does for `"if one_result.pos == pos { break; }"`.

---

test-2
File: tests/test_nullable_loop_guard.py — TestPythonGuardPlacement.test_star_loop_has_guard
What: The `*` guard test only checks `"if one_result.pos == pos:" in src`. It makes no ordering assertion (no `guard_pos < pos_update_pos` check). Contrast with `test_plus_loop_has_guard`, which does check ordering. Placement before `pos = one_result.pos` is load-bearing per the design.
Consequence: A regression that emits the guard after the pos update for `*` loops would not be caught.
Fix: Add the same ordering assertion present in `test_plus_loop_has_guard`.

---

test-3
File: tests/test_nullable_loop_guard.py — no test for `validate_trivia_rule_not_nil` tightening
What: The design (§2.1, §3 behavior change 2) explicitly calls out that `validate_trivia_rule_not_nil` now rejects trivia rules with a REQUIRED quantifier + nullable term (e.g., `_trivia := r"\s*"` with REQUIRED, not `?`). The existing `test_trivia_rule_not_nil_validation` in `test_nil_validation.py` uses `NOT_REQUIRED` (optional) quantifier — that path was already caught pre-fix. The newly-caught path (REQUIRED + nullable regex) is untested.
Consequence: A regression that re-introduces the quantifier-only check would restore the old false-negative for REQUIRED-quantifier trivia rules, undetected.
Fix: Add a test in `test_nil_validation.py` or `test_nullable_loop_guard.py`: construct `_trivia` with `quantifier=gsm.REQUIRED` and `term=gsm.Regex(r"\s*")`, assert `validate_trivia_rule_not_nil` raises `ValueError`.

---

test-4
File: tests/test_nullable_loop_guard.py — TestItemNilDetectionUpdated.test_one_or_more_empty_literal_is_nil (lines 572–599)
What: The docstring contradicts the assertion. It says "Note: one_or_more_item.can_be_nil() → False under the fix because ONE_OR_MORE requires at least one iteration AND each iteration produces progress" and then says "STILL correct — the item-level nil is False", then at the end asserts `True`. The code comment explains the `True` result, but only after a multi-paragraph argument for `False`. The test name says "is_nil" and the assertion says `True`, but the docstring text says `False` in the "Note" section — a reader cannot tell on first read which is the correct post-fix value.
Consequence: Not a correctness issue — the assertion is the ground truth, not the docstring — but the confusion increases the chance a future author "fixes" the docstring to match the wrong branch, or "fixes" the assertion to match the docstring. Not a regression risk but a documentation trap.
Fix: Rewrite the docstring to state clearly upfront: "ONE_OR_MORE + nullable term → `can_be_nil` is `True` because `is_optional() OR term_can_be_nil` = `False OR True` = `True`. The empty-literal iteration means the item itself consumes zero bytes — it is nil." Remove the multi-paragraph argument for `False` that predates the conclusion.

---

No other findings. Coverage of the three main code paths (validator, Python guard, Rust guard) is solid. The subprocess hang-demonstration tests (§5.1), generator-rejection tests (§5.3), and Rust source-text assertion (§5.4) are substantive. The cross-backend parity test asserts concrete `pos` values, not just non-None. Memoization, edge case (Literal, Identifier), and non-nullable control cases are all covered.
