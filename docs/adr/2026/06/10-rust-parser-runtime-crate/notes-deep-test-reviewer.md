Style: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Commit reviewed: 1521372 (top of range d23d1df..1521372)

---

test-1
File: crates/fltk-parser-core/tests/memo_toy.rs, entire file
What: The Python `test_memo.py` `test_indirect` case exercises a grammar where `a := b "+" num | <nothing>` — the `| <nothing>` alternative (empty production) is essential to the indirect recursion test. The Rust `indirect_a` port (lines 120–133) omits the `| <nothing>` alternative, so the rule only tries `b "+"  num` and falls through to `None`. This is a structural deviation from the Python grammar: Python's `indirect_a` returns `None` only after trying `b "+" num`; the Rust version also matches. The tests pass, but only because the test inputs happen not to exercise the `<nothing>` alternative — the semantic equivalence between Python and Rust grammars is not verified.
Consequence: If the memo algorithm contains a latent bug that only manifests when an indirect-recursive rule has a base alternative other than a numeric fallback, the tests will not catch it. The parity claim in the design ("ports of all five test_memo.py cases") is accurate only at the test-input level, not at the grammar level.
Fix: Add the `<nothing>` (empty) alternative to `indirect_a` to exactly match the Python grammar, then add a test input that exercises it (e.g., `"3"` — `a` should fall through to `b`, `b` tries `a` (poison/None), then falls to `num`, returns `Num(3)` at pos 1; `a` then tries `b "+"` but `"+"` is absent, hits `<nothing>`, returns `None` — whole parse is `None` since `a` has no success path for plain `num`). Alternatively document explicitly why the Rust grammar omission is intentional and does not affect the algorithm under test.

test-2
File: crates/fltk-parser-core/src/errors.rs:273–291, `format_error_message_basic`
What: The golden test for `format_error_message_basic` uses `assert!(msg.starts_with(...))` and `assert!(msg.contains(...))` — partial substring checks. The `line_span` for `"hello world"` (no newline) is `Span(0, 10)` = `"hello worl"` (the `line_ends` sentinel is `len - 1 = 10`, so `line_end = 10`, span `[0, 10)` = "hello worl" — missing the last 'd'). The test asserts `msg.contains("hello worl\n")` (line 287), which passes but does not confirm whether the output is `"hello worl"` (correct — matching Python's `terminals[0:10]`) or the full `"hello world"`. Python outputs `"hello worl"` via `terminals[0:10]`, so the test does verify the correct truncation, but only by substring containment. A future bug that emits the full 11-char line would not be caught unless `"hello world\n"` also appears, which it does not.
Consequence: Low severity but a correctness gap: if `pos_to_line_col` or `format_error_message` changes the line-end span boundary, the golden test would still pass as long as `"hello worl"` is a prefix of the new line text.
Fix: Assert the exact `line_text` line in the output, e.g., `assert_eq!(&msg[msg.find('\n').unwrap()+1..msg.find("hello").unwrap()+11], "hello worl")`, or capture the full expected string and `assert_eq!(msg, expected)`.

test-3
File: crates/fltk-parser-core/src/errors.rs (missing test)
What: `py_repr_str` has no test for a string containing both a single quote and a double quote — e.g. `"it's a \"test\""`. The design specifies (§2.4): "prefer `'` quotes, switch to `\"` iff the string contains `'` and not `\"`." The case where both are present should fall back to single quotes and escape the single quote. No test covers this.
Consequence: The both-quotes branch (`has_single && has_double → use single, escape single`) is untested; a bug there — e.g., escaping the wrong character — would not be caught.
Fix: Add `assert_eq!(py_repr_str("it's a \"mix\""), r#"'it\'s a "mix"'"#)`.

test-4
File: crates/fltk-parser-core/src/errors.rs (missing test)
What: `py_repr_str` has no test for control characters (`\n`, `\r`, `\t`, and other bytes < 0x20 / `\x7f`). The test for `\t` and `\r` escapes is absent.
Consequence: The `\r` → `\\r`, `\t` → `\\t`, and `\xHH` code paths are unexercised; a typo in the match arms (e.g., swapping `\r` and `\n` escape strings) would not be caught.
Fix: Add tests: `py_repr_str("\t")` → `"'\\t'"`, `py_repr_str("\r")` → `"'\\r'"`, `py_repr_str("\x01")` → `"'\\x01'"`, `py_repr_str("\x7f")` → `"'\\x7f'"`.

test-5
File: crates/fltk-parser-core/src/terminalsrc.rs (missing test)
What: `consume_regex` has no test for the `pos == len` with a non-zero-width-match attempt (only `consume_regex_empty_match_at_end` tests `pos == len` with `a*`). There is no test that a non-matching pattern at `pos == len` returns `None` (e.g., `\w+` at end-of-input). This is a boundary case the design calls out in §3.
Consequence: If the bounds check `pos > self.len()` were accidentally written as `pos >= self.len()` (off-by-one), the `pos == len` valid-but-no-match case would silently return `None` for wrong reasons; there is no test to distinguish the two failure modes.
Fix: Add `consume_regex_no_match_at_end`: `TerminalSource::new("x")`, regex `\w+`, `consume_regex(1, &re)` → `None` (end-of-input, no word char). This distinguishes "bounds rejection" from "regex no-match at valid end position".

test-6
File: crates/fltk-parser-core/src/terminalsrc.rs (missing test)
What: `pos_to_line_col` has no test for a multi-line input with a trailing newline, specifically checking that the sentinel `line_ends` logic (design §2.3: "add sentinel if text doesn't end with `\n`") correctly handles a text that *does* end with `\n` (sentinel NOT added) — i.e., querying `pos == len - 1` (the `\n` itself) and `pos == len` (decrement to `len - 1 == \n`). Only `pos_to_line_col_trailing_newline` tests trailing-newline, but it only queries `pos == 0` — not a position on or near the terminal newline.
Consequence: The `ends.last() != Some(&(len - 1))` guard is exercised only via "sentinel added" paths; the "sentinel not added" path (trailing-newline case) is not confirmed to produce a correct `line` / `col` for `pos == len - 1`.
Fix: In `pos_to_line_col_trailing_newline`, add checks for `pos_to_line_col(3)` (the `\n` at index 3 in `"abc\n"`) — should return `line=0, col=3` — and `pos_to_line_col(4)` (== len, decremented to 3) — same result.

test-7
File: crates/fltk-parser-core/tests/memo_toy.rs:302–313, `test_memoization_hit`
What: `test_memoization_hit` asserts only that `p.invocations[0]` does not change between the first and second `apply__rule_expr(0)` calls. It does not assert what `count_after_first` actually is. The test passes vacuously if the first call itself executes zero invocations (impossible here, but the assertion form `assert_eq!(p.invocations[0], count_after_first)` proves "no change since snapshot" not "exactly N invocations happened". This is fine for the cache-hit goal but the more valuable assertion — "rule body ran at least once during first call" — is missing.
Consequence: If a bug caused the first call to complete via an unexpected cache path (invocations[0] stays 0), the test would not catch it, because `assert_eq!(0, 0)` passes.
Fix: Add `assert!(count_after_first > 0, "rule body must execute at least once on first call")` immediately after the snapshot.

test-8
File: crates/fltk-parser-core/src/errors.rs (missing test)
What: `format_error_message` is not tested with `longest_parse_len > 0` on multi-line input (where line > 0). All golden tests use single-line inputs or the `-1` sentinel. The `line + 1` / `col + 1` arithmetic is not exercised for `line > 0`.
Consequence: A bug in `pos_to_line_col` that returns the wrong line for positions on line 2+ would not be caught by the error-message golden tests.
Fix: Add a test with `TerminalSource::new("abc\nxyz")`, `fail_literal(4, 0, "Q")` (pos 4 = 'x', line 1 col 0), and verify `"Syntax error at line 2 col 1:\nxyz\n^\nExpected:\n"` exactly.
