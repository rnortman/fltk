# Slop pre-pass — base 61fc5e8..ff7d198

## slop-1

**File:** `crates/fltk-fmt-cli/src/lib.rs`, `char_index_not_byte_index` test, final assertion (~line 2754 of diff)

**Quote:**
```rust
// Stopping after the leading "é " (2 chars) leaves "foo ü", which is not
// all whitespace, so it is a partial parse. Passing the byte length (9) as a
// char index would skip past the end and spuriously report "consumed", so the
// distinction matters.
assert!(!fully_consumed(src, 2));
assert!(fully_consumed(src, byte_len));
```

**What's wrong:** The comment calls `fully_consumed(src, byte_len=9)` returning `true` a "spurious" result, then asserts the spurious result with a plain `assert!`. The assertion passes vacuously: `chars().skip(9)` on a 7-char string yields an empty iterator, so `all(is_whitespace)` is true for the wrong reason. The test asserts that a misuse of the API gives a specific wrong (vacuously true) answer — which is unusual and easy to misread as validating correct behavior.

**Consequence:** A reader skimming the test sees two `assert!` lines after a comment warning about spurious results and has to stop and trace through the vacuous-empty-iterator behavior to understand that the second assertion is documenting a footgun, not verifying correctness. The test name promises to demonstrate why char indices matter, but both `char_len=7` and `byte_len=9` return true from the function (for different reasons), so the distinction is not actually demonstrated for this scenario.

**Suggested fix:** Replace the final assertion with a case where byte position and char position diverge for a *partial* parse — e.g., a string where a parser stopping at byte offset 2 (= after the leading 2-byte "é") would be treated as char offset 2 (= after "é "), giving a different consumed/not-consumed verdict — and assert the correct outcome. Alternatively, if keeping the vacuous-true case, change the assertion to `assert!(fully_consumed(src, byte_len), "byte_len as char index vacuously skips past the end — this is a footgun, not correct usage")` to make intent explicit, or split into a clearly labeled "footgun demonstration" section.
