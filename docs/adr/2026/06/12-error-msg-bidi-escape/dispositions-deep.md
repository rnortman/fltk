Style: concise, precise, complete, unambiguous. No padding, no preamble.

# Dispositions — error-msg-bidi-escape, round 1

## correctness-1
- Disposition: Fixed
- Action: Binary-replaced raw C1 bytes (UTF-8 `\xc2\x9b`, `\xc2\x80`, `\xc2\x9f`) with visible ``/``/`` escape sequences at `tests/test_pyrt_errors.py:25-27`. Same raw `\xc2\x9b` found and replaced at line 177 (the `no_raw_controls` input).
- Severity assessment: Raw C1 bytes in Python source are invisible in most editors/review UIs, making the cross-language pin unverifiable by inspection and allowing any tool that normalizes control chars to silently change test semantics.

## correctness-2
- Disposition: Fixed
- Action: The raw `\xc2\x9b` byte WAS present at `tests/test_pyrt_errors.py:177` (reviewer's claim that it was absent was incorrect — the byte was there but invisible), and was replaced with visible `` as part of the correctness-1 fix. Test now has visible U+009B in its input, matching the Rust twin at `errors.rs:396`.
- Severity assessment: An invisible raw C1 in the input makes the C1 coverage of this sweep invisible and fragile — any tool normalizing control chars would silently drop the test coverage.

## security-1
- Disposition: Fixed
- Action: Same fix as correctness-1 — raw C1 bytes replaced with visible escapes at `tests/test_pyrt_errors.py:25-27` and `:177`. Cross-language pin is now verifiable by inspection; U+009B (CSI) no longer appears as a live terminal control sequence when the source file is displayed.
- Severity assessment: Embedding raw CSI (U+009B) in source files creates terminal-escape-sequence injection when the file is displayed in a VT-compatible terminal, directly contradicting the security goal of the change being reviewed.

## security-2
- Disposition: Fixed
- Action: Wrapped `{e}` with `escape_control_chars(&e.to_string())` at `crates/fltk-cst-core/src/cross_cdylib.rs:278`, `:356`, and `:390` (the third site was not cited by the reviewer but was structurally identical and adjacent).
- Severity assessment: PyErr text reaching these paths could contain control/bidi chars from an attacker-controlled Python environment; inconsistency with the rest of the file's escaping posture was the primary concern.

## security-3
- Disposition: Won't-Do
- Action: no change
- Severity assessment: TAB passthrough in CST-bridge TypeError text is a deliberate design decision (design §Part (a)) called out explicitly. Re-adding TAB to the escape set in both backends would cause cross-pin churn. No line injection or escape-sequence risk from a literal TAB in a TypeError traceback; only TSV/column-alignment spoofing in log pipelines, which is not a threat in this context.
- Rationale: Design §Part (a) explicitly states "TAB in type/attribute names now passes through (was escaped)" as a deliberate alignment decision, and the design was approved. Reversing it requires a design change, not a respond-mode fix.

## test-1
- Disposition: Fixed
- Action: Same as correctness-2 — visible `` restored at `tests/test_pyrt_errors.py:177`; C1 branch in the sweep is no longer vacuous.
- Severity assessment: Without a C1 char in the input, a Python-only regression in C1 escaping would not be caught by this test.

## test-2
- Disposition: Fixed
- Action: Added `assert_eq!(escape_control_chars("\u{206a}"), "\u{206a}");` to `passthrough_boundary_chars` in `crates/fltk-cst-core/src/escape.rs:204` and mirrored assertion for U+206A in `test_escape_passthrough_boundary_chars` at `tests/test_pyrt_errors.py:108`.
- Severity assessment: Missing upper-boundary test leaves an off-by-one (extending the LRI range to U+206A) undetectable.

## test-3
- Disposition: Fixed
- Action: Replaced the hardcoded `is_escaped_set` predicate in `test_format_error_message_no_raw_extended_set_in_output` (`tests/test_pyrt_errors.py:196-202`) with `_needs_escape` as oracle (imported at line 8). LF excluded via `cp != 0x0A` since it appears raw as a line separator in formatted output.
- Severity assessment: A hardcoded predicate that duplicates `_needs_escape` will drift silently when the escape set is extended; the sweep would then stop verifying newly-added classes without any failure.

## reuse-1
- Disposition: Fixed
- Action: Rewrote the `is_escaped_set` inline predicate in `format_error_message_no_raw_extended_set_in_output` (`crates/fltk-parser-core/src/errors.rs:397-407`) to use `escape_control_chars` as the oracle — same technique as the Python test-3 fix. LF skipped via an explicit `continue` since it appears raw as the message's line separator. Predicate duplication eliminated; no visibility change needed.
- Severity assessment: A hardcoded predicate re-implementing 9 conditions would drift silently from `escape_control_chars` on future escape-set extensions, exactly as `escape_control_chars_for_msg` drifted.

## reuse-2
- Disposition: Fixed
- Action: Same as test-3 — Python sweep now uses `_needs_escape` as oracle, eliminating the duplicated predicate in `tests/test_pyrt_errors.py`.
- Severity assessment: Duplicate predicate would drift silently from `_needs_escape` on future escape-set extensions, exactly as the `escape_control_chars_for_msg` duplication drifted (the bug this commit fixes).

## quality-1
- Disposition: Fixed
- Action: Deleted `fn escape_control_chars_table` and `fn escape_control_chars_empty` from `crates/fltk-parser-core/src/errors.rs:312-340`. Replaced with a comment pointing to `escape.rs`. Re-export still exercised indirectly by the `format_error_message_*` tests.
- Severity assessment: Duplicate tests create a three-location update requirement on every future escape-set extension, reversing the intra-Rust deduplication goal of the implementation.

## quality-2
- Disposition: Fixed
- Action: Added `#[doc(hidden)]` to `pub mod escape` at `crates/fltk-cst-core/src/lib.rs:4` with a comment directing consumers to `fltk_parser_core::escape_control_chars` instead. The module remains `pub` so the inter-crate `pub use` in `errors.rs` compiles.
- Severity assessment: Without the hidden marker, `fltk_cst_core::escape` becomes an unintended second published API path, doubling the "preserved path" burden at the next API evolution point.
