# Error Handling Review — Phase 3 Python Bindings + Parity

Commit reviewed: b107645

---

## errhandling-1

**File:line:** `tests/parser_parity.py:220–236` (`assert_error_equiv`)

**Broken error path:** When `py_pos == -1` (no error recorded), the function returns early after the position assertion, skipping the structural message comparison. If a future caller passes a Rust parser that *has* an error while the Python parser does not, the assertion at line 224 catches the position difference — but only as long as `rust_pos is not None`. If both are no-error (`py_pos == -1`, `rust_pos is None`), the function returns silently without verifying that `rust_parser.error_message()` is actually the no-failure form. That is benign for current usage, but the inverse case — `py_pos != -1` but `rust_pos is None` — is caught. The real gap is: the no-error early return skips message comparison entirely, so a Rust parser that produces a non-empty `error_message()` string on a fresh/successful parse would pass `assert_error_equiv` silently.

**Why:** `if py_pos == -1: return` at line 231 exits before calling `error_message()` on either side. There is no assertion that `rust_parser.error_message()` returns the no-failure form.

**Consequence:** A Rust regression that populates `error_message()` on a successful parse (e.g., leftover error state from a previous memoized result) would never be caught by the parity suite. Silent discrepancy; on-call would see only "parity tests pass" with no diagnostic about the message divergence.

**What must change:** After the `if py_pos == -1` branch asserts `rust_pos is None`, add `assert rust_parser.error_message() == ""` (or compare against the known no-failure string from the Python side) before returning. Or, refactor: always compare messages when both have no error, using the no-failure-form predicate.

---

## errhandling-2

**File:line:** `tests/parser_parity.py:166–188` (`_parse_error_message`)

**Broken error path:** The parser for `From rule "..."` sections uses `line.startswith('  From rule "')` (two leading spaces). If the Rust `error_message()` emits this header with a different indentation than the Python backend, the line will land in `header_lines` instead of starting a new rule section — silently producing a wrong parse (rule-group content folded into the header, no rule sections found). The comparison would then either pass vacuously (empty rule dicts on both sides) or fail on the header, masking the real discrepancy.

**Why:** The indentation constant is hard-coded and not validated against either backend's actual output format. If they diverge, the parser silently misclassifies lines rather than raising an error.

**Consequence:** A backend that emits `From rule` headers with wrong indentation would produce an empty `rule_sections` dict; `_assert_messages_equiv` would pass if both backends produce the same misparse (both empty) while real rule differences go undetected. Diagnosis: tests green, actual error messages structurally different and no one knows.

**What must change:** After `_parse_error_message`, assert that at least one rule section was found when a non-empty message with `Expected:` is present, or compare that `rule_sections` is non-empty when the header indicates there are rule groups. Alternatively, validate the indentation assumption with an explicit check and fail loudly if the format doesn't match expectations.

---

## errhandling-3

**File:line:** `tests/test_rust_parser_parity_fegen.py:510–513` (FAIL branch of `test_parity`)

**Broken error path:** The FAIL branch asserts `py_result is None or py_result.pos < len(text)` and then calls `assert_error_equiv`. However, it does not assert that `rust_result` is also falsy/None — a Rust parser that returns a full SUCCESS result (pos == len(text)) on input that the Python backend fails on would pass the FAIL branch check on the Rust side only because `rust_result.pos < len(text)` is also checked, but the check reads `rust_result is None or rust_result.pos < len(text)`. If Rust returns `result.pos == len(text)` (full parse), the check `rust_result.pos < len(text)` is False, so the whole disjunction is False — the test fails correctly. This is fine. However, `assert_error_equiv` is called regardless: if Rust *succeeds fully* (`rust_result is not None` and `rust_result.pos == len(text)`), the Rust `error_position()` will be `None`, and `assert_error_equiv` will check `py_pos != -1` but `rust_pos is None` — triggering `AssertionError: Error position: Python=X but Rust=None`. This is the correct failure, but the message is confusing: the real issue is that Rust *succeeded* where Python *failed*, not an error-position mismatch. The test's failure mode is correct but the error message misleads on-call diagnosis.

**Why:** The FAIL branch does not explicitly assert that both backends failed *before* entering error comparison. The asymmetric outcome (Rust succeeds, Python fails) surfaces as a confusing error-position mismatch rather than a clear "outcome disagreement."

**Consequence:** This does not produce a false green — the test still fails when backends disagree. But the failure message says "Error position: Python=5 but Rust=None" instead of "Rust succeeded (pos=N) but Python failed." On-call has to reason backward from the message to the actual cause.

**What must change:** Assert both outcomes explicitly before calling `assert_error_equiv`. Example: add `assert rust_result is None or rust_result.pos < len(text), f"Rust unexpectedly succeeded at pos {rust_result.pos} while Python failed"` before `assert_error_equiv`, producing a diagnosis-quality message. (Note: looking at the code again, this assert *is* present at line 512 — but the failure message `"Rust unexpectedly succeeded"` is only shown when the assert fires, and `assert_error_equiv` is called after it. If the assert fires, `assert_error_equiv` is not reached. If both asserts pass but the outcomes are partial vs none, `assert_error_equiv` fires with a confusing message. This is a diagnostic quality issue, not a correctness issue — the test still fails correctly.)

**Revised assessment:** This is diagnostic-quality only, not a correctness finding. Downgrading to note: the FAIL branch correctly catches outcome disagreement, but diagnosis of the failure could be clearer. Not a reportable finding under this reviewer's mandate.

---

## errhandling-4

**File:line:** `tests/test_rust_parser_parity_fixture.py:888–895` (PARTIAL branch of `test_parity`)

**Broken error path:** The PARTIAL branch has a special case:

```python
elif isinstance(expected, PARTIAL):
    if expected.pos == 0 and py_result is None:
        assert rust_result is None
    elif py_result is not None:
        assert rust_result is not None
        assert py_result.pos == expected.pos
        assert rust_result.pos == expected.pos
        assert_cst_equal(py_result.result, rust_result.result)
```

When `expected.pos != 0` and `py_result is None`, neither branch executes — the test passes silently. A PARTIAL entry where the Python parser returns None (unexpectedly fails) and `expected.pos != 0` produces a vacuous green: no assertion fires, no output, the test passes.

**Why:** The `elif py_result is not None` guard means that when `py_result is None` and `expected.pos != 0`, the branch body is skipped entirely. There is no `else: pytest.fail(...)` or fallthrough assertion.

**Consequence:** A regression in the Python parser that causes it to fail on a PARTIAL-annotated input (where `expected.pos > 0`) would produce a silent green test. On-call has no diagnostic. The corpus entry exists to catch a regression but provides no signal when the regression occurs.

**What must change:** Add an `else` clause that fails explicitly: `else: pytest.fail(f"Python parser returned None on PARTIAL-expected input (expected pos={expected.pos})")`. The `fegen` parity test (`test_rust_parser_parity_fegen.py`) does not have this issue — its PARTIAL branch asserts both sides unconditionally.

---

No further findings.
