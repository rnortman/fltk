# Dispositions — deep review (fltk-parser-core, commit 1521372)

Style: concise, precise, complete, unambiguous. No padding.

---

## errhandling-1

- Disposition: Fixed
- Action: `crates/fltk-parser-core/src/memo.rs` — replaced the single `assert!(has_cache_entry)` fallthrough with an explicit two-branch dispatch: `!has_cache_entry && !is_head_or_involved` → panic with the "Untested corner case" message; `!has_cache_entry && is_head_or_involved` → panic with a distinct "growth-cycle rule is head/involved but has no cache entry" message.
- Severity assessment: Diagnostic quality only — both paths previously crashed correctly, but the wrong message fired for the `is_head_or_involved && !has_cache_entry` subcase, making post-mortem analysis harder.

---

## errhandling-2

- Disposition: Fixed
- Action: `crates/fltk-parser-core/src/memo.rs:grow_seed` — added a comment before `call_result.unwrap()` explaining the invariant: we only reach that line when `has_result && new_pos > entry.final_pos` (the break condition above fires otherwise), so `call_result` is always `Some` here.
- Severity assessment: No runtime risk currently; comment prevents a future refactor from silently making the `unwrap` reachable on `None`.

---

## errhandling-3

- Disposition: Fixed (via quality-3/reuse-1/efficiency-4)
- Action: The `line_ends` initializer now uses `chars().enumerate()` which yields codepoint indices directly, eliminating the `char_indices` → binary-search path entirely. The missing `debug_assert` is no longer needed because there is no longer a byte→codepoint conversion in this path.
- Severity assessment: The original concern (silent wrong line/col if the sentinel character changed to multibyte) is resolved structurally.

---

## correctness-1

- Disposition: Fixed
- Action: `crates/fltk-parser-core/tests/memo_toy.rs` — `rule_expr` now commits after `expr` succeeds: if `"+" num` continuation fails, returns `None` rather than falling through to Alternative 2, matching Python's semantics. The grammar comment is accurate. `indirect_a` was also given commit semantics (same pattern) as part of test-1.
- Severity assessment: Previously `test_direct` passed only because the fallback's `new_pos` was always ≤ seed's `final_pos`, masking the divergence. The growth loop could have been edited to mishandle the failed-final-iteration case without the suite catching it.

---

## security-1

- Disposition: TODO(consume-regex-anchor)
- Action: Added doc comment on `consume_regex` explaining the O(n²) DoS risk from unanchored `find_at`, and a `TODO(consume-regex-anchor)` pointing to the `regex_automata` fix. Added entry in `TODO.md`. Location: `crates/fltk-parser-core/src/terminalsrc.rs` (`consume_regex`).
- Severity assessment: Real algorithmic-complexity DoS for services parsing untrusted input; deferred because fixing it requires switching to `regex_automata::meta::Regex` (different API surface, not a one-line change).

---

## security-2

- Disposition: TODO(apply-depth-limit)
- Action: Added doc comment on `apply` explaining the stack-overflow/abort risk and its regression vs. Python's recoverable `RecursionError`. Added `TODO(apply-depth-limit)` pointing to the depth-counter fix in `PackratState`. Added entry in `TODO.md`. Location: `crates/fltk-parser-core/src/memo.rs` (`apply`).
- Severity assessment: Hard process abort (not a recoverable error) on deeply-nested input; a strict failure-mode regression vs. the Python backend it replaces.

---

## security-3

- Disposition: TODO(error-msg-escape)
- Action: Added doc comment on `format_error_message` documenting the terminal escape injection / log-forging exposure from unescaped `line_text`, and the constraint that fixing it unilaterally would break the Phase 3 parity comparator. Added `TODO(error-msg-escape)` noting the joint Python+Rust fix path. Added entry in `TODO.md`. Location: `crates/fltk-parser-core/src/errors.rs` (`format_error_message`).
- Severity assessment: Inherited from Python backend (not newly introduced); severity is correspondingly low. Must be fixed jointly with Python to preserve comparator validity.

---

## test-1

- Disposition: Won't-Do (bogus finding; prior "Fixed" disposition was wrong — reverted)
- Action: Reverted the previously-applied changes to `crates/fltk-parser-core/tests/memo_toy.rs`. The reviewer's claim that Python's grammar is `a := b "+" num | <nothing>` is false: test_memo.py:88 states `a := b "+" num`; `indirect_a` (test_memo.py:114) returns `None` when `b` fails; `test_fail` (test_memo.py:253) asserts `apply_result is None`. The `<nothing>` alternative and the `Some(<nothing>)` assertions added in the prior round have been removed. Additional fixes applied per the judge's rework prescription:
  - Removed `<nothing>` fallback from `indirect_a`; `b returns None → return None` (no alternative). File: memo_toy.rs.
  - Fixed file-header grammar comment: `a := b "+" num` (not `a := b "+" num | <nothing>`). Closes the open tail of correctness-1.
  - Fixed `indirect_a` doc comment: removed self-contradictory text, dangling `test_fail_indirect_none` reference, and nonsense "Num(97)" fragment.
  - Restored `test_fail` to assert `result.is_none()` — ports test_memo.py:253; re-covers the failed-recursion-seed path (design §2.5 step 5).
  - Restored `test_failure_caching` to assert `None` + unchanged invocation count on re-query — re-covers `Failure` cache-hit dispatch (design §4.1: "Failure caching: failed rule re-queried at same pos does not re-execute").
- Severity assessment: The bogus finding (if accepted) would have introduced a parity break with Python's semantics and removed coverage of two distinct algorithm paths required by the design test plan. The prior "Fixed" disposition was the error; the correct disposition is Won't-Do citing test_memo.py:88, :114, :253.

---

## test-2

- Disposition: Fixed
- Action: `crates/fltk-parser-core/src/errors.rs` — `format_error_message_basic` now uses `assert_eq!(msg, expected, ...)` with the exact expected string, replacing partial `starts_with`/`contains` checks.
- Severity assessment: Weak assertions previously allowed a line-boundary bug in `pos_to_line_col` or `format_error_message` to go undetected.

---

## test-3

- Disposition: Fixed
- Action: `crates/fltk-parser-core/src/errors.rs` — added `py_repr_both_quotes_in_string` test: `py_repr_str("it's a \"mix\"")` → `r#"'it\'s a "mix"'"#`.
- Severity assessment: The both-quotes branch was untested; a typo (escaping the wrong character) would not have been caught.

---

## test-4

- Disposition: Fixed
- Action: `crates/fltk-parser-core/src/errors.rs` — added `py_repr_control_characters` test covering `\t`, `\r`, `\x01`, `\x7f`.
- Severity assessment: Control-character escape arms were untested; swap bugs (e.g., `\r` → `"\\n"`) would not have been caught.

---

## test-5

- Disposition: Fixed
- Action: `crates/fltk-parser-core/src/terminalsrc.rs` — added `consume_regex_no_match_at_end`: `TerminalSource::new("x")`, `\w+`, `consume_regex(1, &re)` → `None`. Distinguishes "bounds rejection" from "regex no-match at valid end position".
- Severity assessment: An off-by-one in the bounds check (`>=` vs `>`) would not have been caught for `pos == len`.

---

## test-6

- Disposition: Fixed
- Action: `crates/fltk-parser-core/src/terminalsrc.rs` — `pos_to_line_col_trailing_newline` now also checks `pos=3` (the `\n` at index 3 in `"abc\n"`) → `line=0, col=3`, and `pos=4` (== len, decremented) → same result. Exercises the "sentinel not added" path for positions on and past the terminal newline.
- Severity assessment: The "sentinel not added" path (`ends_with('\n')`) was not confirmed to produce correct line/col for positions near the terminal newline.

---

## test-7

- Disposition: Fixed
- Action: `crates/fltk-parser-core/tests/memo_toy.rs` — added `assert!(count_after_first > 0, "rule body must execute at least once on first call")` immediately after the first-call snapshot in `test_memoization_hit`.
- Severity assessment: Without this, `assert_eq!(0, 0)` would pass vacuously if a bug caused the first call to complete via an unexpected cache path with zero invocations.

---

## test-8

- Disposition: Fixed
- Action: `crates/fltk-parser-core/src/errors.rs` — added `format_error_message_multiline` test with `TerminalSource::new("abc\nxyz")`, failure at pos 4 (`line=1, col=0`), exact `assert_eq` against the expected string. Exercises `line + 1` / `col + 1` arithmetic for `line > 0`.
- Severity assessment: A bug in `pos_to_line_col` returning the wrong line for positions on line 2+ would not have been caught by the existing error-message golden tests.

---

## reuse-1

- Disposition: Fixed (same as quality-3 / efficiency-4)
- Action: `crates/fltk-parser-core/src/terminalsrc.rs:line_ends` initializer — replaced `char_indices()` + per-newline `partition_point` binary search with `chars().enumerate()` which yields `(codepoint_index, char)` directly. Eliminates both the redundant `text` scan and the O(log n) binary search per newline.
- Severity assessment: Redundant dual-scan with O(L·log N) complexity replaced by O(N); additionally the removed `cp_to_byte` borrow inside the closure means the two representations can now diverge independently without silent incorrect output.

---

## quality-1

- Disposition: Fixed
- Action: `crates/fltk-parser-core/src/errors.rs:format_error_message` fallback path — changed `format!("Syntax error at unknown position\n{expected_block}")` to `format!("Syntax error at unknown position\nExpected:\n{expected_block}")` so the fallback output includes the "Expected:\n" header, matching the normal path.
- Severity assessment: The fallback path (unreachable by construction) silently omitted the "Expected:\n" header, producing a format divergent from the normal path. If the invariant broke, the difference would go unnoticed.

---

## quality-2

- Disposition: Fixed (same as efficiency-1)
- Action: `crates/fltk-parser-core/src/memo.rs` — removed `_existing_ri: Option<RecursionInfo>` from `setup_recursion` signature and removed the redundant extraction block at the call site. `setup_recursion` already re-reads the entry via `get_mut`; the extracted value was never used.
- Severity assessment: Dead parameter caused a HashMap lookup + two HashSet clones on every poison hit, and required every future call site to supply a dead argument.

---

## quality-3

- Disposition: Fixed (same as reuse-1 / efficiency-4)
- Action: See reuse-1.
- Severity assessment: See reuse-1.

---

## quality-4

- Disposition: Fixed
- Action: `crates/fltk-parser-core/src/errors.rs` — added `use std::collections::HashMap;` at the top, replacing the fully-qualified `std::collections::HashMap` path in `build_expected_block`.
- Severity assessment: Minor style inconsistency; no functional consequence.

---

## efficiency-1

- Disposition: Fixed (same as quality-2)
- Action: See quality-2.
- Severity assessment: One redundant HashMap lookup plus two HashSet clones on every left-recursion detection event (every poison hit during seed growth). Pure waste proportional to left-recursion frequency.

---

## efficiency-2

- Disposition: Fixed (partial — step 4 re-fetch eliminated)
- Action: `crates/fltk-parser-core/src/memo.rs:apply` step 4 — clones the return value before the `get_mut` write, eliminating the subsequent `get` re-fetch (lookup 4 in the reviewer's count). The broader multi-lookup restructure noted for steps 1 and 2/3 was not done; those paths are lower-frequency and the structural change is larger.
- Severity assessment: Eliminated one redundant HashMap lookup + clone in the no-recursion (dominant) path. The remaining extra lookups (2-3 per non-recursive invocation) are deferred; the hottest path improvement is shipped.

---

## efficiency-3

- Disposition: Fixed
- Action: `crates/fltk-parser-core/src/memo.rs:grow_seed` — changed `recursion.clone()` to `recursion` (move). `recursion` is passed by value and not used after the `insert`.
- Severity assessment: Two HashSet allocations per growth-cycle start, strictly zero-benefit.

---

## efficiency-4

- Disposition: Fixed (same as reuse-1 / quality-3)
- Action: See reuse-1.
- Severity assessment: O(L·log N) → O(N) for first error-message format.

---

## efficiency-5

- Disposition: Fixed
- Action: `crates/fltk-parser-core/src/terminalsrc.rs:from_source_text` — added `cp_to_byte.shrink_to_fit()` after the build loop. For multibyte input, the initial `with_capacity(text.len() + 1)` over-reserves by up to ~4× (bytes ≫ codepoints for CJK).
- Severity assessment: Retained-memory overhead proportional to input size for non-ASCII sources, alive for the whole parse. Single realloc on construction eliminates the slack.
