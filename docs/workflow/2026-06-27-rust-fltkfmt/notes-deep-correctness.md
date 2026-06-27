# Deep correctness review — rust-fltkfmt increments 1-3

Commit reviewed: HEAD `1b48755` (base `61fc5e8`, range `61fc5e8..1b48755`).

## Tasked investigation: the two failing tests in `tests/test_rust_unparser_generator.py`

**Finding: these failures are a regression introduced by increment 1, NOT intentional red
TDD tests for later work.**

The two failures are:
- `test_count_newlines_in_trivia_multi_variant_emits_catchall` (test file line 1968)
- `test_has_preservable_trivia_matches_configured_node_types` (test file line 2035)

Evidence trail:
- The test file `tests/test_rust_unparser_generator.py` was last modified in `6f975eb`
  (the parent of the base `spec-freeze` commit). It is **byte-unchanged** across the entire
  review range (`git diff 61fc5e8..1b48755 -- tests/test_rust_unparser_generator.py` is
  empty). Both tests already existed at base (`git show 61fc5e8:…` finds both).
- At base, `fltk/unparse/gsm2unparser_rs.py` emitted the trivia helpers with a single-arm
  `match … { Variant => …, _ => {} }`. Both tests assert on that shape: they require
  `"cst::TriviaChild::Span(span) => {"`, `"cst::TriviaChild::Comment(_) => return true,"`,
  and `"_ => {}"` substrings. They passed at the spec-freeze commit (which passed
  `make check`).
- Increment 1 (`e5bb7ec`) changed `gsm2unparser_rs.py`
  (`_gen_has_preservable_trivia_method` ~line 1446 and
  `_gen_count_newlines_in_trivia_method` ~line 1488) to emit the multi-variant case as
  `if let <pattern> = &child.1 { … }` instead of `match { … _ => {} }`, to silence clippy's
  `single_match` lint on the fegen grammar (whose `TriviaChild` has `LineComment`/
  `BlockComment` variants). The committed generated file
  `crates/fegen-rust/src/unparser.rs:27,37` confirms the new `if let` output is what ships.
- Running the suite confirms exactly these two failures (150 passed, 2 failed), each failing
  on the now-absent `=> {` / `=> return true,` / `_ => {}` substrings because the generator
  now emits `if let … = &child.1 { … }`.

So: the generator's *behavioral* output change is correct. The `if let` form is functionally
equivalent to `match { Pat => …, _ => {} }` (and to the or-pattern
`if let A | B = … { return true; }`, stable since Rust 1.65); the emitted Rust compiles and
is clippy-clean. The defect is purely that the two unit tests, which pin the *old textual
output*, were not updated to match the new output in the same increment. They were instead
carried red across commits with `--no-verify`.

This is a test-suite regression that silences the generator's own contract tests, not a
runtime correctness bug, and not deliberate red tests staged for a later increment. Nothing
in the design or later increments calls for these two tests to remain failing; the design's
drift/parity tests are separate and additive.

### correctness-1
- File: `tests/test_rust_unparser_generator.py:1979, 1981` and `:2050, 2052`
  (driven by `fltk/unparse/gsm2unparser_rs.py` changes at ~1446 and ~1488).
- What's wrong: increment 1 changed the multi-variant trivia helpers from a
  `match { Variant => …, _ => {} }` form to an `if let Variant = &child.1 { … }` form, but
  did not update the two tests that assert on the old `match`/`_ => {}` text. The tests now
  fail.
- Why: `test_count_newlines_in_trivia_multi_variant_emits_catchall` asserts
  `"cst::TriviaChild::Span(span) => {"` and `"_ => {}"`; the generator now emits
  `if let cst::TriviaChild::Span(span) = &child.1 {`.
  `test_has_preservable_trivia_matches_configured_node_types` asserts
  `"cst::TriviaChild::Comment(_) => return true,"` and `"_ => {}"`; the generator now emits
  `if let cst::TriviaChild::Comment(_) = &child.1 { return true; }`.
- Consequence: `pytest tests/test_rust_unparser_generator.py` fails (2 of 152). Because the
  commits were landed with `--no-verify`, the red suite no longer guards the generator's
  multi-variant trivia output: a future *real* breakage of these helpers (e.g. a dropped
  exhaustiveness guard, an incorrect or-pattern) would be indistinguishable from the existing
  expected-red state. The generated Rust itself is correct (equivalent control flow, compiles,
  clippy-clean), so there is no downstream behavioral defect — the harm is the lost test signal.
- Suggested fix: update both tests to assert the new `if let … = &child.1 { … }` form (drop
  the `_ => {}` and `=> {`/`=> return true,` expectations; for `_has_preservable_trivia`
  expect `if let cst::TriviaChild::Comment(_) = &child.1 {` and `return true;`). This is a
  test-text update only; no generator change is needed. Rename the
  `_emits_catchall` test to reflect the new intent (e.g. `_emits_if_let`).

## Other correctness checks across increments 1-3

- `crates/fltk-fmt-cli/src/lib.rs` `fully_consumed` (lines 54-59): correct. Guards `pos < 0`
  before `as usize` (avoids wraparound); `chars().skip(pos).all(is_whitespace)` returns
  `true` for `pos >= char_count` (empty iterator) and is genuinely char-indexed. No
  off-by-one: a parse stopping exactly at char count is accepted; one non-whitespace char in
  the suffix rejects.
- `FmtArgs` clap struct: declarative, no logic. Flag-conflict validation and `run_main`
  belong to a later increment (per design §2.2) and are correctly absent here, not missing.
- Committed `crates/fegen-rust/src/unparser.rs` matches the new generator output (no
  generator/output drift); the or-pattern `if let A(_) | B(_) = &child.1` at line 27 is valid
  stable Rust.

No other correctness findings.
