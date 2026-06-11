Style: concise, precise, complete, unambiguous. No padding, no preamble.

Reviewed HEAD: 097ea96. Fixes committed at: 09ff919.

## test-1

- Disposition: Fixed
- Action: Added `consume_regex_word_boundary_reject_mid_word_via_context` test at `crates/fltk-parser-core/src/terminalsrc.rs:389-398`. Pattern `\bello` at pos=1 in "hello" returns None because `h` before pos is a word char; comment explains sliced-haystack regression.
- Severity assessment: Without this test, a regression to sliced-haystack could pass the existing `\B`-success case (sliced haystack also fails `\Bello` at a string boundary) while incorrectly matching `\bello` (sliced haystack places `\b` at start-of-string and matches). The anchored-semantics regression guard was incomplete.

## test-2

- Disposition: Fixed
- Action: Added assertion `assert "fltk_parser_core::regex_automata::meta::Regex::new(" in src` to `test_regex_table_emitted` in `fltk/fegen/test_gsm2parser_rs.py:300`. Pins the `_gen_regex_compile_test` emission site.
- Severity assessment: Without this pin, the compile-test body could silently retain the old `fltk_parser_core::regex::Regex::new(pat)` path; the Python-layer test suite would not catch it, only `cargo test` on fixtures would.

## quality-1

- Disposition: Fixed
- Action: Changed panic string in `_gen_regex_compile_test` (`fltk/fegen/gsm2parser_rs.py:989`) from `"not supported by the regex crate"` to `"not supported by regex_automata::meta::Regex"`. Regenerated both fixture parsers (`tests/rust_cst_fegen/src/parser.rs:1343`, `tests/rust_parser_fixture/src/parser.rs:1226`).
- Severity assessment: Every downstream-generated parser inherits the panic message from the generator. A stale crate name misleads users trying to diagnose unsupported regex patterns.

## quality-2

- Disposition: Fixed
- Action: Updated module docstring in `fltk/fegen/gsm2parser_rs.py:6-14`. Replaced both occurrences of "the Rust `regex` crate" with accurate wording: "regex-syntax (shared by the `regex` and `regex-automata` crates)" and "`regex_automata::meta::Regex` rejects them at compile time."
- Severity assessment: The docstring is the first developer-facing explanation of the regex constraint. Wrong crate name sends readers to the wrong documentation and contradicts the sentence two lines below it.

## efficiency-1

- Disposition: TODO(regex-automata-features)
- Action: Added `TODO(regex-automata-features)` comment at `crates/fltk-parser-core/Cargo.toml:16-22` and entry in `TODO.md`. The default-features choice was deliberate (DFA build is a search-time win for small patterns, tightly size-capped); the cost side (compile time, binary size for downstream consumers) was not formally weighed.
- Severity assessment: Real but not a correctness or correctness-adjacent issue. Compile time and binary size affect developer experience for downstream consumers. The DFA-build path is bounded by `nfa_size_limit` and `hybrid_cache_capacity`, so runtime memory impact is constrained. Deferring is appropriate until a downstream consumer raises it as a concern.
