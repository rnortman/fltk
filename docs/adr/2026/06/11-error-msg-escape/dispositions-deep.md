Style: concise, precise, complete, unambiguous. No padding, no preamble.

# Dispositions — deep review of error-msg-escape (8da7924)

## correctness-1

- Disposition: Fixed
- Action: Corrected comment in `errors.rs:374` from `line_ends=[7], line_span=[0,7)` to `line_ends=[5], line_span=[0,5)`. String `"ab\x1bcd\n"` is 6 codepoints; `\n` is at index 5. Test assertions were already correct; only the comment documenting the derivation was wrong.
- Severity assessment: No runtime impact; incorrect comment would have led maintainers to compute wrong expected values when extending the test.

## security-1

- Disposition: TODO(error-msg-bidi-escape)
- Action: Added TODO comment to `escape_control_chars` in both `errors.rs` and `errors.py`; added `error-msg-bidi-escape` entry to `TODO.md` with threat description and rationale.
- Severity assessment: Extending to Unicode Cf/bidi/U+2028-U+2029 requires a new representation spec (two-digit `\xHH` insufficient) and cross-backend repinning — genuine scope extension beyond the user-approved C0+DEL+C1 bound (design.md A1). Log-forging via U+2028/U+2029 and bidi visual reordering are real but lower-impact than the closed ESC vector; accepted risk for this scope.

## test-1

- Disposition: Won't-Do (finding was incorrect)
- Action: No change. The Python no-raw-controls test at `test_pyrt_errors.py:89` already includes U+009B in the input as UTF-8 bytes `\xc2\x9b`. The file viewer displayed `\x9b` ambiguously; the C1 char was present. The Rust test (already confirmed to include `\u{009b}`) and Python test are symmetric.
- Severity assessment: No gap exists; the finding was a false positive caused by visual ambiguity in the byte display of the source file.
- Rationale (Won't-Do): Applying the fix would introduce a duplicate C1 char in the input string, adding noise with no correctness benefit.

## test-2

- Disposition: Fixed
- Action: Replaced partial `startswith`/`in` assertions in `test_format_error_message_col_minus_one` and `test_format_error_message_empty_input` with full golden equality assertions (`tests/test_pyrt_errors.py:100-114`). Expected strings derived from actual output and verified against codepoint arithmetic. Rework: corrected new comment from `line_span=[0,1)` to `line_span=[0,2)` (actual `Span(start=0, end=2)` verified by execution — sentinel quirk on "abc" excludes the last character, giving line_text "ab" = indices 0..2).
- Severity assessment: Low regression risk on these paths (col=-1 and empty-input produce no escaping), but the pattern of partial assertions for edge cases was inconsistent with the full-golden approach used elsewhere and would not catch regressions in the line-text line.

## test-3

- Disposition: Fixed
- Action: Added `test_format_error_message_caret_at_control_char` to both backends: Python at `tests/test_pyrt_errors.py:87-97`, Rust at `errors.rs:388-400`. Tests line `"ab\x1bcd\n"` with error at col 2 (the ESC): prefix `"ab"` has no controls → pad=2, caret lands on `\` of `\x1b` escape, asserted `lines[2] == "  ^"`.
- Severity assessment: The design explicitly listed "caret at a control char" as an edge case; the behavior was correct but unverified. A regression (e.g., off-by-one in the prefix split when the split point is itself a control) would not have been caught.

## test-4

- Disposition: Won't-Do
- Action: No change. Finding is informational (comment in Rust test does not document the unreachability of `\n` at the call site). The assertion itself is correct and the comment accurately says "C0 controls".
- Severity assessment: No correctness impact; documentation nit only.
- Rationale (Won't-Do): Adding a parenthetical to a test comment about unreachability does not prevent any regression and would make the comment longer without improving correctness.

## quality-1 / efficiency-1 (same underlying issue)

- Disposition: Fixed
- Action: Replaced `Vec<char>` collect + slice + two `String` collects with `line_text.char_indices().nth(split).map_or(line_text.len(), |(b, _)| b)` byte-offset lookup and direct `&str` slices. `errors.rs:150-157`. Eliminates three intermediate heap allocations; makes the codepoint-index invariant explicit at the call site.
- Severity assessment: Correctness-neutral (identical output); removes latent hazard where a future maintainer could mistake the split for a byte index. Allocation savings are per-error-message (cold path), so performance impact is modest but the code is strictly better.

## quality-2 / efficiency-2 (same underlying issue)

- Disposition: Fixed
- Action: Replaced `out.push_str(&format!("\\x{:02x}", cp))` with `write!(out, "\\x{:02x}", cp).unwrap()` in `escape_control_chars` (`errors.rs:93`) and the same fix in `py_repr_str` (`errors.rs:235`). Added `use std::fmt::Write as FmtWrite` import. Applied the same change to both occurrences in the file.
- Severity assessment: Eliminates one heap allocation per escaped character. On adversarial input (line of N controls), saves N temporary `String` allocations. Cold path only; correctness is unchanged.

## efficiency-3

- Disposition: Fixed (early-return form); TODO(error-msg-escape-zero-copy) (zero-alloc Cow variant)
- Action: Implemented signature-preserving early-return fast path in both backends. Rust: `needs_escape` predicate extracted inline, `s.chars().any(|c| needs_escape(c as u32))` pre-scan returns `s.to_owned()` on clean input (`errors.rs`). Python: `any(((cp := ord(ch)) <= _C0_END and cp != _TAB) or cp == _DEL or _C1_START <= cp <= _C1_END for ch in text)` pre-scan returns `text` unchanged (`errors.py:70-71`). Renamed TODO from `error-msg-escape-fast-path` to `error-msg-escape-zero-copy`, narrowed to the `Cow<'_, str>` zero-alloc variant only.
- Severity assessment: Common-case regression (Python replaced direct slice with per-char loop; Rust rebuilt string char-by-char on clean input) is now recovered. The zero-alloc `Cow` variant remains deferred as an API-surface decision.
