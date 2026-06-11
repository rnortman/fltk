# Judge verdict — prepass2

Phase: pre-pass round 2. Base 490bccf..HEAD b95f772 (respond commit b95f772 over reviewed 261fa5e). Round 1.
Notes: 2 reviewer files (slop, scope); 8 findings. All dispositioned Fixed; no TODOs, no Won't-Dos.

Style note: concise, precise, complete, unambiguous; no padding.

## Added TODOs walk

No TODO dispositions in this round. No new `TODO(slug)` comments in the respond diff (261fa5e..b95f772).

## Other findings walk

### slop-1 — Fixed
Claim: 8-line self-correcting scratch-note comment at `fltk/fegen/gsm2parser_rs.py:241-248`; consequence is reviewer-confidence drop from uncommitted thought-log.
Diff: comment replaced with the exact single-sentence form the reviewer proposed ("generate() calls _gen_rule() for all rules before calling _gen_constants(), so self._regex_patterns is complete here").
Assessment: matches the suggested fix verbatim. Accept.

### slop-2 — Fixed
Claim: `test_optional_item_no_return_none` docstring promises absence of `else { return None; }` but only asserts `apply__parse_opt(` exists; consequence is an unwanted else-branch regression going uncaught.
Diff: docstring corrected; assertion added that isolates the `parse_opt__alt0` body (split on fn boundaries) and asserts `"} else {" not in alt0_body`. Not vacuous: sibling test `test_ws_required_separator_has_else_return_none` asserts the same string IS present when required, so the tell is real. Test passes.
Assessment: assertion now matches the docstring's claim. Accept.

### slop-3 — Fixed
Claim: `test_zero_or_more_quantifier` asserts only wrapper existence; the `*` vs `+` distinction (no `if pos == span_start` guard) untested; consequence is an `is_required()` swap going uncaught.
Diff: assertion added isolating `parse_zom__alt0__item0` body and asserting the guard string is absent — scoped to the item body as the reviewer requested. Counterpart `test_one_or_more_quantifier` asserts the guard present for `+`. Test passes.
Assessment: the one observable `*`/`+` behavioral difference is now pinned both directions. Accept.

### scope-1 — Fixed
Claim: design §4 item 2 CLI tests for `gen-rust-parser` absent from `test_genparser.py`; consequence is untested CLI error handling and partial-output suppression.
Diff: five tests added — `test_gen_rust_parser_happy_path` (exit 0, file written, `apply__parse_word` in content), `test_gen_rust_parser_missing_grammar_file` (exit ≠0, no output), `test_gen_rust_parser_generation_error_no_partial_file` (INLINE-disposition grammar triggers generation error; exit ≠0, no partial file), `test_gen_rust_parser_invalid_cst_mod_path` (exit ≠0, no output), plus bonus `test_gen_rust_parser_custom_cst_mod_path` (propagation to `use my::cst;`). Covers all three design rows plus the reviewer's suggested (d). All pass.
Assessment: complete coverage of the design contract. Accept.

### scope-2 — Fixed
Claim: `_CST_MOD_PATH_RE` regex gate in `genparser.py` unexercised; consequence is a regex typo going uncaught.
Diff: `test_gen_rust_parser_invalid_cst_mod_path` invokes the CLI with `--cst-mod-path "123bad"`, asserts non-zero exit and no output file — exactly the reviewer's suggested fix. Passes.
Assessment: gate now exercised. Accept (shared fix with scope-1 is fine; the finding is satisfied).

### scope-3 — Fixed
Claim: design §4 item 1 union-label structural assertion missing from Python unit tests; consequence is union-label append regressions caught only at the slower Rust compile step.
Diff: `test_union_label_append_uses_child_enum` builds `val := item:num | item:word` (same label, two node types), asserts `result.append_item(cst::ValChild::` — the child-enum form the design specifies. Passes, so the generated source genuinely contains the union path.
Assessment: structural assertion at the Python level as the design requires. Accept.

### scope-4 — Fixed
Claim: design §4 item 3 capture_trivia on/off tree-delta assertion absent from Rust fixture tests; consequence is silent labeled-child drop/insert under `capture_trivia=true` going uncaught.
Diff: `test_capture_trivia_tree_delta` in `native_tests.rs` parses `"foo = bar"` (stmt, WS_REQUIRED separators) in both modes; asserts lhs/rhs spans identical across modes, `total_true > total_false`, and `total_false == 2`. Reviewer suggested WS_ALLOWED; WS_REQUIRED equally produces inter-token trivia, so the substitution is sound. Disposition says "2 vs 4" while the test asserts `>` plus `== 2`; the delta direction and labeled-children invariance — the design's actual claim — are pinned. Passes.
Assessment: design assertion satisfied. Accept.

### scope-5 — Fixed
Claim: SUPPRESS-absent and INCLUDE-span-present-unlabeled child assertions missing; fixture grammar had no `$`-included unlabeled item at all; consequence is appends of suppressed items or missing unlabeled-INCLUDE appends going undetected.
Diff: (a) `test_suppress_absent_from_children` parses `(42)`, asserts `children().len() == 1` and `child_inner()` present — suppressed parens absent. (b) New fixture rule `tagged := $"tag" . value:/[a-z]+/` added to `rust_parser_fixture.fltkg`; `cst.rs` (+556) and `parser.rs` (+44) regenerated; `test_include_span_present_unlabeled` asserts 2 children with `children()[0]` label `None`. Both halves of the reviewer's suggested fix delivered. All 37 fixture tests pass.
Assessment: both §2.3 table rows now covered. Accept.

## Verification

`uv run pytest fltk/fegen/test_gsm2parser_rs.py fltk/fegen/test_genparser.py` — 45 passed.
`cargo test` in `tests/rust_parser_fixture` — 37 passed (includes all new tests).

## Disputed items

None.

## Approved

8 findings: 8 Fixed verified.

---

## Verdict: APPROVED

All eight dispositions are Fixed and each fix verifiably addresses the finding's consequence; both test suites pass at HEAD b95f772.
