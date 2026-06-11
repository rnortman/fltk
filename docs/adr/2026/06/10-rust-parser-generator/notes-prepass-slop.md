## slop-1

**File:** `fltk/fegen/gsm2parser_rs.py:346–352`
**Quote:** `# The pattern: header checks self._regex_patterns AFTER bodies are generated. / # Actually: generate() calls _gen_rule() for all rules FIRST...`
**Problem:** Multi-line comment block in `_gen_constants` narrates the author's reasoning process about ordering constraints — "Actually:", "So by the time..." — rather than stating an invariant or non-obvious contract. This is the canonical LLM-talking-to-itself pattern.
**Consequence:** Reads as a thought-log left in by mistake; embarrassing in a code review.
**Fix:** Replace with a single-line invariant: `# regex table is complete here; generate() populates it before calling _gen_constants()`

---

## slop-2

**File:** `fltk/fegen/gsm2parser_rs.py:433`
**Quote:** `# Note: we do NOT close the impl block here; consume helpers and fn bodies are appended within it.`
**Problem:** Comment describes the structural quirk of the generator's output-assembly contract — that `impl Parser {` opened in `_gen_parser_struct` is not closed there. This is a genuine non-obvious coupling, but the comment is written as a narrative note to the reader rather than a doc on the method contract.
**Consequence:** Not severe, but the comment is the sort of thing that should be a method-level docstring on `_gen_parser_struct` stating the postcondition ("opens but does not close the impl block"), not a trailing inline note.
**Fix:** Move to docstring of `_gen_parser_struct`; remove inline note.

---

## slop-3

**File:** `fltk/fegen/test_gsm2parser_rs.py:1131–1155`
**Quote:**
```python
if stripped.startswith("pub fn ") and not stripped.startswith("pub fn apply__"):
    fn_name = stripped.split("(")[0].replace("pub fn ", "")
    assert fn_name in {
        "new",
        "from_source_text",
        "terminals",
        "capture_trivia",
        "rule_names",
        "error_message",
        "error_position",
    }, f"Unexpected pub fn: {fn_name}"
```
**Problem:** The allowlist of public function names is hardcoded in a test. Adding any new public method to `Parser` will silently break this test unless the author also updates the allowlist — and the condition `startswith("pub fn ") and not startswith("pub fn apply__")` is evaluated on stripped lines that may include method-signature continuations (e.g., multi-line `pub fn` declarations). The double-negative condition on the same prefix is also confusing.
**Consequence:** Brittle test that is likely to produce a spurious failure or a maintenance burden; the logic is fragile enough that a reviewer should question whether the test actually catches the intended invariant.
**Fix:** Test the invariant more directly: assert that the only non-`apply__` `pub fn` names in the source are those listed; or just grep for `\bpub fn\b` lines and subtract the known-good set.

---

## slop-4

**File:** `fltk/fegen/test_gsm2parser_rs.py:1283–1287`
**Quote:**
```python
# trivia rule uses regex so REGEX_PATTERNS will still be present
# (the _trivia rule is always added internally)
# So we can only check that consume_regex IS used (for the trivia rule)
assert "REGEX_PATTERNS" in src
```
**Problem:** The test is named `test_no_regex_table_when_no_regexes` but asserts the opposite of what the name says — it asserts that `REGEX_PATTERNS` IS present. The comment explains why (trivia always adds a regex), but the test name is contradicted by its assertion.
**Consequence:** Anyone reading the test suite will be confused; the test name promises one thing and the body does another. This looks like an unfinished edit.
**Fix:** Rename to `test_regex_table_present_for_trivia_even_without_user_regexes` and optionally add an assertion that the only pattern present is the trivia whitespace pattern.

---

## slop-5

**File:** `fltk/fegen/test_gsm2parser_rs.py:1324–1349`
**Quote:**
```python
def test_inline_disposition_raises_at_some_point() -> None:
    """INLINE disposition must raise an error (either at construction or generate time).

    The underlying CstGenerator does not support INLINE on non-Identifier terms,
    so an AssertionError/NotImplementedError is expected somewhere in the pipeline.
    """
    ...
    with pytest.raises((NotImplementedError, AssertionError)):
```
**Problem:** "either at construction or generate time" and `(NotImplementedError, AssertionError)` are both vague. The docstring explicitly acknowledges the test doesn't know when or what type of error fires. This is acceptable if the behavior is genuinely unspecified, but the test name says "raises at some point" — which reads as a placeholder.
**Consequence:** Signals the test was written without full understanding of the pipeline's behavior; a reviewer will ask whether this was ever verified to catch a real failure.
**Fix:** Pin down which exception fires and when, or add a comment explaining why the exact type is legitimately undetermined (e.g., "depends on CstGenerator internals we don't control").

---

## slop-6

**File:** `tests/rust_cst_fegen/src/native_parser_tests.rs:1754–1762`
**Quote:**
```rust
if result.is_none() {
    // error_position should be >= 0 if any terminal was attempted
    let _msg = parser.error_message();
    // just verify no panic
}
```
**Problem:** The test body for `test_error_position_on_failure` silently passes whether parse succeeds or fails, and in the failure branch only checks that `error_message()` doesn't panic. The comment "just verify no panic" is a tell that this test has no real assertion. The test name promises it checks error position on failure, but it doesn't assert anything about error position.
**Consequence:** Dead test — gives false confidence while catching nothing meaningful. The failure branch has no assertion at all.
**Fix:** Assert `result.is_none()` (the input `"grammar := !!!invalid;"` should reliably fail), then assert `parser.error_position().is_some()`.
