# Test Review Notes — Phase 3 Python Bindings

Commit range: b668897..b107645

---

## test-1

**File:** `fltk/fegen/test_gsm2parser_rs.py:959` — `test_python_bindings_apply_methods_per_rule`

**What's wrong:** The test asserts `"fn apply__parse_items(" in src` — a substring search over the whole file. The native parser already has `pub fn apply__parse_items(` in the struct impl block, which existed before Phase 3. The assertion fires on either occurrence, so a generator that omits the per-rule methods from the *bindings block* entirely would still pass, provided the native pub fn exists.

**Consequence:** A regression where `_gen_python_bindings` emits no per-rule pymethods goes undetected. The full parity tests would catch this, but only once the extension is built — the generator unit tests (which run without a Rust compiler) would not.

**Fix:** Extract the `mod python_bindings {` block before asserting, and search within it only. The `test_python_bindings_register_classes_two_classes` test already does this correctly with `src.split("mod python_bindings {", 1)[1].split("\n}", 1)[0]` — apply the same scoping to the apply-method assertions.

---

## test-2

**File:** `fltk/fegen/test_gsm2parser_rs.py` — generator tests: no test for correct `Py<ClassName>` in each apply method body

**What's wrong:** No generator unit test verifies that each per-rule pymethod canonicalizes via the *correct* `cst::Py<ClassName>::to_py_canonical`. The test confirms the methods exist (with the scoping gap above) but not that `apply__parse_items` uses `cst::PyItems::to_py_canonical` vs, say, `cst::PyItem::to_py_canonical`. A copy-paste bug in the generator loop writing the wrong class name would produce a wrong type handle at runtime, and no unit test would catch it.

**Consequence:** A generator bug mapping rule → wrong CST class is invisible in pure-Python testing. It would surface at runtime (a `TypeError` or wrong-type handle) but only after building the extension — no fast pre-build red.

**Fix:** Add one test using `_make_two_rule_grammar()` that extracts the bindings block and asserts `"cst::PyItems::to_py_canonical" in bindings_block` and `"cst::PyItem::to_py_canonical" in bindings_block` (both should be present; each with its own rule's class). This directly pins the generator's `self._class_name(rule.name)` interpolation.

---

## test-3

**File:** `tests/test_rust_parser_parity_fixture.py:126` — `PARTIAL` branch

**What's wrong:** The `PARTIAL` branch has two nested conditions:
```python
if expected.pos == 0 and py_result is None:
    assert rust_result is None
elif py_result is not None:
    ...
```
When `expected.pos != 0` and `py_result is None`, neither branch runs — the test silently passes with no assertions. The only PARTIAL corpus entry is `("expr", "1+2+3 ", PARTIAL(5))`, which has `expected.pos == 5`, so if the Python parser returns `None` on that input, the test exits without any check on the Rust result. This can mask a divergence where Python fails but Rust succeeds (or both fail when both should partially succeed).

**Consequence:** If a parser regression causes `py_result is None` for a PARTIAL entry with non-zero expected position, the test neither flags the Python failure nor checks Rust — the case silently turns into a vacuous pass. The `fegen` parity test does not have this gap (its PARTIAL branch asserts both non-None unconditionally).

**Fix:** Collapse to the same shape as `test_rust_parser_parity_fegen.py:109-114`:
```python
elif isinstance(expected, PARTIAL):
    assert py_result is not None, "Python parser failed unexpectedly"
    assert rust_result is not None, "Rust parser failed unexpectedly"
    assert py_result.pos == expected.pos
    assert rust_result.pos == expected.pos
    assert_cst_equal(py_result.result, rust_result.result)
```
Remove the `expected.pos == 0` special case — it was apparently introduced to handle a case where `PARTIAL(0)` means "both return None," but that is what `FAIL` is for; `PARTIAL(0)` is conceptually incoherent (a parse succeeding at position 0 returns the empty-match, not None).

---

## test-4

**File:** `tests/test_rust_parser_bindings.py:369–392` — `test_error_message_on_fresh_parser` / `test_error_message_after_failed_parse`

**What's wrong:** `test_error_message_on_fresh_parser` asserts only `isinstance(msg, str)`. The design (§2.6) says both should return "the no-failure form" before any parse. The content of that form is not asserted. `test_error_message_after_failed_parse` asserts `"Syntax error" in msg or "Expected" in msg` — an `or` between two tokens neither of which has to appear alone; a message that contained only "Expected:" without "Syntax error" would satisfy it vacuously.

**Consequence:** A Rust implementation that returns an empty string or wrong message form before a parse, or that emits a malformed message after a parse, passes these tests. The parity tests do structural comparison, but only when both backends agree on outcome — they don't exercise the no-failure message form cross-backend.

**Fix:** `test_error_message_on_fresh_parser`: assert `msg == ""` or assert the documented no-failure sentinel (whichever the runtime returns) rather than `isinstance(msg, str)`. `test_error_message_after_failed_parse`: use `assert "Syntax error" in msg` and `assert "Expected:" in msg` as separate assertions, both required.

---

## test-5

**File:** `tests/test_rust_parser_parity_fegen.py:544` — `test_assert_cst_equal_fails_for_different_inputs`

**What's wrong:** The negative test for `assert_cst_equal` uses two trees from different-length inputs. The comparator will fail at kind mismatch (a `Rule` node vs another `Rule` node with different spans) — but because the input texts are completely different (`'x := "a" ;'` vs `'longname := "longer_literal" ;'`), it likely fails at the root span. The test is named "different inputs" but intends to cover "trees differ." It does not specifically exercise the tree-comparison path being different from a trivial span check; it might fail purely on root span before any child recursion occurs. This is not vacuous (the test does fail correctly) but it overlaps with `test_assert_cst_equal_fails_span_mismatch` at a coarser level, and does not add any new path coverage beyond that test.

**Consequence:** Low — the comparator self-tests collectively do cover kind, span, label, child-count, deep-child, and species. This is redundancy rather than a gap.

**Note:** Not a blocking issue; the self-test suite as a whole is sound. No fix required unless the author wants to tighten the name to reflect what it actually tests.

---

## test-6

**File:** `tests/test_rust_parser_parity_fegen.py:469–470` — multibyte error corpus entry lacks explicit `PARTIAL` success path for multibyte positions

**What's wrong:** The corpus has `("grammar", 'x := "café" ** ;', FAIL)` to test multibyte caret/line rendering. The design (§2.5) specifies "multibyte content preceding a syntax error (line/col + caret line parity over multibyte text)." The `FAIL` branch calls `assert_error_equiv`, which compares header lines byte-for-byte — this does cover the line/col and caret line. However, there is no SUCCESS corpus entry that specifically pins that a parse *succeeding* past a multibyte character reports the correct final position (`result.pos`). The existing `("raw_string", '"café"', SUCCESS)` entry checks success with multibyte content, but `result.pos` is asserted equal to `len(text)` — `len` in Python counts Unicode characters, and the Rust side returns codepoint positions. If the Rust side were to return byte positions instead of codepoint positions for a multibyte input, the parity check on SUCCESS pos would catch it — so this IS covered by the existing `("raw_string", '"café"', SUCCESS)` entry. No gap.

**Consequence:** None — already covered. Removing this item.

---

## Summary

Four actionable findings:

- **test-1**: `test_python_bindings_apply_methods_per_rule` searches the whole file, not just the bindings block — can miss generator omitting methods from the gated module.
- **test-2**: No generator unit test pins that each apply method uses the correct `Py<ClassName>` — copy-paste bug in the generator loop is invisible in pure-Python testing.
- **test-3**: PARTIAL branch in `test_rust_parser_parity_fixture.py` silently passes (no assertions) when `py_result is None` and `expected.pos != 0`.
- **test-4**: Error-message binding tests assert content too weakly — no-failure form content unchecked, after-failure `or` allows one of the two required patterns to be absent.
