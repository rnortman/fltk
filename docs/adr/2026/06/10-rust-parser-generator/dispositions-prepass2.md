# Dispositions: Phase 2 Rust Parser Generator — prepass2 round

## slop-1
- Disposition: Fixed
- Action: gsm2parser_rs.py:241-242 — replaced 8-line scratch-note comment with a single clear sentence.
- Severity assessment: Cosmetic confidence issue; no functional impact.

## slop-2
- Disposition: Fixed
- Action: test_gsm2parser_rs.py `test_optional_item_no_return_none` — added assertion that the alt0 body lacks `} else {`, verifying the optional item does not emit a required-item else branch.
- Severity assessment: Without the fix, a regression that adds an unwanted else branch to optional items would not be caught by this test.

## slop-3
- Disposition: Fixed
- Action: test_gsm2parser_rs.py `test_zero_or_more_quantifier` — added assertion that the item body lacks `if pos == span_start`, verifying the `*` quantifier emits no one-or-more progress guard.
- Severity assessment: Without the fix, swapping `is_required()` logic between `+` and `*` would not be caught.

## scope-1
- Disposition: Fixed
- Action: test_genparser.py — added four `gen-rust-parser` CLI tests: happy path writes file (exit 0, content has `apply__parse_word`), missing grammar file (exit 1, no output file), generation error exits 1 with no partial file, invalid `--cst-mod-path` exits 1 with no output file.
- Severity assessment: CLI error handling and partial-output suppression were entirely unexercised; a regression in any of these would ship silently.

## scope-2
- Disposition: Fixed
- Action: test_genparser.py `test_gen_rust_parser_invalid_cst_mod_path` — covered by scope-1 fix above; the `_CST_MOD_PATH_RE` regex gate is now exercised.
- Severity assessment: A typo in the validation regex would not have been caught; now it would be.

## scope-3
- Disposition: Fixed
- Action: test_gsm2parser_rs.py `test_union_label_append_uses_child_enum` — builds a grammar with `item` label on two different node types (`Num` and `Word`), asserts generated code contains `result.append_item(cst::ValChild::` (the child-enum form).
- Severity assessment: A generator regression on the union-label append path would previously only be caught by the Rust compile step, not at the Python level.

## scope-4
- Disposition: Fixed
- Action: tests/rust_parser_fixture/src/native_tests.rs `test_capture_trivia_tree_delta` — parses `"foo = bar"` (stmt with WS_REQUIRED separators) under both `capture_trivia` modes; asserts lhs/rhs spans identical across modes and total children differ (2 vs 4).
- Severity assessment: A bug silently dropping or adding labeled children under `capture_trivia=true` would not have been caught.

## scope-5
- Disposition: Fixed
- Action: Two additions:
  (a) native_tests.rs `test_suppress_absent_from_children`: parses `(42)`, asserts `children().len() == 1` (suppressed parens absent).
  (b) Added `tagged := $"tag" . value:/[a-z]+/` rule to rust_parser_fixture.fltkg; regenerated cst.rs and parser.rs; added `test_include_span_present_unlabeled` asserting 2 total children with `children()[0].label == None` (the $-included literal).
- Severity assessment: A generator bug appending suppressed items or failing to emit unlabeled-INCLUDE appends would not have been detected at the Rust level without these assertions.
