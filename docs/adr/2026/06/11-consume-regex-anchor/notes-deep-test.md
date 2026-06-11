Style: concise, precise, complete, unambiguous. No padding, no preamble.

Commit reviewed: 097ea96

## test-1

File: `crates/fltk-parser-core/src/terminalsrc.rs`, `consume_regex_context_before_pos`

`consume_regex_context_before_pos` tests `\B` (non-word-boundary) at position 1 in `"hello"`. `\B` holds at position 1 because positions 0 and 1 are both word characters (`h`, `e`). The test verifies the match succeeds. There is no complementary test verifying that an **anchored start fails** when `\b`/`\B` context would cause rejection. For instance: `\bello` at `pos=1` in `"hello"` — `\b` must not hold between `h` and `e` (both `\w`), so it should return `None`. A slice-at-`byte_pos` implementation would also fail this (because `\b` at position 0 of the slice `"ello"` *does* match, i.e. the slice-based bug goes the wrong direction for this sub-case). More precisely: a slice-based implementation starting at `byte_pos=1` sees `"ello"` starting at a string boundary, so `\b` at position 0 of that slice resolves as "start-of-string / word" — it would incorrectly match `\bello`. An `Input::span`-with-full-haystack implementation correctly sees the `h` before position 1 and rejects. That rejection case — `\b` refusing a match because the context before `byte_pos` is a word char — is the strongest proof that the full-haystack path is operative, and it is not tested.

Consequence: a regression back to a sliced-haystack implementation would still pass `consume_regex_context_before_pos` (the `\B`-match case) while breaking the semantically distinct `\b`-rejection case. The regression guard for the wrong-context direction is absent.

Fix: add a test `consume_regex_word_boundary_reject_mid_word_via_context` (name suggestion): text `"hello"`, pattern `\bello`, `pos=1` → `None`. Comment: "`\b` at pos=1 requires seeing non-word before pos; the `h` at pos=0 is a word char, so `\b` fails. Sliced haystack would place `\b` at start-of-string and incorrectly match."

## test-2

File: `fltk/fegen/test_gsm2parser_rs.py`, `test_regex_table_emitted`

The new assertion `assert "use fltk_parser_core::regex_automata::meta::Regex;" in src` pins the import path in the header-emission path (`_gen_header`). The design also changes `_gen_regex_compile_test` to emit `fltk_parser_core::regex_automata::meta::Regex::new(pat)` in the `all_regex_patterns_compile` test body. No test asserts the compile-test body uses the new path. The existing generator tests do not assert the body of the generated `all_regex_patterns_compile` function.

Consequence: if `_gen_regex_compile_test` were accidentally left emitting the old `fltk_parser_core::regex::Regex::new(pat)` path, no Python-side test would catch it. The fixture `cargo test` would catch it (compile error), but that is not a Python-layer regression guard and is not a fast-feedback signal.

Fix: add an assertion in `test_regex_table_emitted` (or a new focused test) that `"fltk_parser_core::regex_automata::meta::Regex::new" in src` (or the exact string `fltk_parser_core::regex_automata::meta::Regex::new(pat)`) appears in the generated source, covering the compile-test emission site.

## Summary

All existing tests are substantive — assertions are meaningful and test names describe behavior. The two gaps above are missing complementary cases (wrong-direction context rejection) and a missing pin on the compile-test emission site, both with concrete regression consequences.
