Style: concise, precise, complete, unambiguous. No padding, no preamble.

Commit reviewed: 8da7924

## Findings

### test-1

**File:** `tests/test_pyrt_errors.py` — `test_format_error_message_no_raw_controls_in_output`

**What's wrong:** The input `"\x00\x01\x1b\r\x7fabc\n"` does not include any C1 codepoint (U+0080–U+009F). The no-raw-controls assertion therefore never exercises the C1 branch of `escape_control_chars` inside `format_error_message`. The C1 case is proven for `escape_control_chars` in isolation (`test_escape_control_chars_c1`) but the integration path — C1 in a line that flows through `format_error_message` — has no no-raw-controls coverage. A bug that dropped C1 from the `format_error_message` call path (e.g., wrong dispatch order, accidental raw pass-through) would not be caught.

**Consequence:** Regression not caught: a C1 character in the failing line would pass through to the formatted message unescaped, bypassing the security invariant, with no test failing.

**Fix:** Add `` (or any U+0080–U+009F) to the input string in the no-raw-controls test, e.g. `"\x00\x01\x1b\r\x7fabc\n"`. The same gap exists in the Rust `format_error_message_no_raw_controls_in_output` test at `errors.rs:392`, which already includes `\u{009b}` — the Python test just needs to match.

Checking: the Rust test at line 392 does include `\u{009b}` in its input — that backend's no-raw-controls test is complete. Only the Python test (`test_pyrt_errors.py:89`) is missing the C1 input.

---

### test-2

**File:** `tests/test_pyrt_errors.py` — `test_format_error_message_col_minus_one` and `test_format_error_message_empty_input`

**What's wrong:** Both tests assert only `msg.startswith(...)` and `"\n^\n" in msg`. Neither asserts the full message structure (escaped line text, absence of raw controls, expected block). These are effectively smoke tests: they verify the function returns a string that starts with the right header and contains `^`, but do not verify the line-text line (line index 1 in the output). A regression that, say, emitted raw text on the line-text line would not be caught.

**Consequence:** Regression not caught for col=-1 / empty-input edge cases. The existing golden test for ASCII-clean input (`test_format_error_message_ascii_clean_unchanged`) uses full equality, but the edge-case tests are weaker. While the col=-1 and empty-input paths are lower risk (they produce an empty prefix/suffix), the pattern sets a precedent of partial assertions for edge cases.

**Fix:** Add a full string equality assertion (as done in `test_format_error_message_ascii_clean_unchanged`) or at minimum assert `lines[1] == ""` (empty line text) and `lines[2] == "^"` (no leading spaces).

---

### test-3

**File:** `tests/test_pyrt_errors.py` — `test_format_error_message_caret_alignment_with_escaped_prefix`

**What's wrong:** The test puts the error at `col=3` (the `c` character, which is printable). This verifies that the pad correctly counts 6 positions (the escaped prefix expands `\x1b` from 1 char to 4 chars). However, it does not test the case where the error column itself is a control character — i.e., the caret lands on the `\` of an escape sequence (design doc §"Edge cases": "Error column at a control char: caret lands on the `\` of its escape"). This is a distinct code path where `split_clamped` bisects at a control char.

**Consequence:** Behavior unverified for the design-specified edge case "caret at a control character." A bug that placed the caret one position off when the error column is itself a control would not be caught.

**Fix:** Add a test with error column pointing at a control character, e.g. line `"ab\x1bcd\n"`, fail at col=2 (the ESC). Escaped line = `"ab\\x1bcd"`, pad = `len("ab")` = 2 (prefix is `"ab"` with no controls → 2 chars), caret line = `"  ^"`. Symmetric test exists for neither Python nor Rust — both backends need it.

---

### test-4

**File:** `tests/test_pyrt_errors.py` — `test_escape_control_chars_c0`

**What's wrong:** The test asserts `escape_control_chars("\n") == "\\x0a"`. Per the design doc (§ Escape set), `\n` is in the escape set because "line_span excludes the terminating newline both backends" makes it unreachable at the call site. This assertion is correct, but the comment in the Rust table test (`escape_control_chars_table` at `errors.rs:330-331`) says "C0 controls (except TAB)" and lists `\n` without noting it is in-set but unreachable at the `format_error_message` call site. Minor documentation concern only — the assertion itself is accurate.

No action required for this item beyond noting it; it is informational.

---

### Summary

Material gaps: test-1 (missing C1 coverage in the integration no-raw-controls path — Python only), test-2 (partial assertions for col=-1 and empty-input edge cases), test-3 (error column at a control character is untested in both backends).
