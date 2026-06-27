# Judge verdict — deep review (rust-fltkfmt increments 1-3)

Phase: deep. Base `61fc5e8`..HEAD `762bbce` (respond commit on top of reviewed `1b48755`). Round 1.
Notes: 7 reviewer files; 11 dispositioned items (correctness-1 / test-1 / quality-1 are the same defect).

## Added TODOs walk

### errhandling-1 — TODO(unparser-none-path-diagnostics) at `fltk/unparse/gsm2unparser_rs.py:1351`
Q1 (worth doing): yes — the missing `else` on the `_has_preservable_trivia` / `unparse__trivia` block silently discards a `None` after the helper confirmed comments exist, dropping a source comment from formatted output with zero diagnostic signal. Real observability gap on an invariant-violation path.
Q2 (design/owner input required): yes — the fix is a cross-backend behavioral-policy choice (log-and-continue vs `debug_assert!` vs halt). CLAUDE.md mandates Python/Rust behavioral parity; a Rust-only `eprintln` (literally what the reviewer proposed) would diverge the backends, so the reviewer's concrete patch is wrong as-stated and the proper fix spans both the Rust generator and the Python unparser. Genuine design work.
Furthermore (this-iteration check): the None-discard logic is **pre-existing** — `if let Some(trivia_result)` exists in the generator at base `61fc5e8` (verified via `git show 61fc5e8:fltk/unparse/gsm2unparser_rs.py`); the generator landed in `6f975eb`, an ancestor of base. This diff only changed the `match`→`if let` shape, not None handling. The new `unparser.rs` is a faithful instance of pre-existing behavior, not a regression this diff introduced. And it is not *silently* deferred regardless — tracked with a slug, a code comment, and a TODO.md entry with full rationale.
Assessment: Q1+Q2 both yes → TODO acceptable. Slug join verified (code comment + TODO.md entry).

### errhandling-2 — TODO(unparser-none-path-diagnostics) at `fltk/unparse/gsm2unparser_rs.py:1077`
Q1 (worth doing): yes — `let text = span.text()?;` propagates `None` from a sourceless/sentinel labeled span up to the public `unparse_*` entry with no record of which label failed; a Python caller cannot distinguish "unparseable" from "invariant-violated span." Same real observability gap.
Q2 (design/owner input required): yes — same cross-backend policy decision as errhandling-1, tracked under the same slug covering both sites.
Furthermore: same as errhandling-1 — `let text = span.text()?;` is present in the generator at base (verified); pre-existing pattern, unchanged by this diff.
Assessment: Q1+Q2 both yes → TODO acceptable. Second code comment for the slug present at the `_gen_regex_term_body` site.

## Other findings walk

### correctness-1 / test-1 / quality-1 — Fixed (single test update)
Claim: increment 1 changed the multi-variant trivia helpers from `match { Variant => …, _ => {} }` to `if let`, but the two tests asserting the old `match`/`_ => {}` text were not updated; suite red, multi-variant helper branches lose passing coverage, future regression indistinguishable from known-red. Consequence is real (lost test signal); generated Rust itself is correct.
Diff at `tests/test_rust_unparser_generator.py`: `test_count_newlines_in_trivia_multi_variant_emits_catchall` renamed to `..._uses_if_let`, now asserts `if let cst::TriviaChild::Span(span) = &child.1 {` present and `_ => {}` absent; `test_has_preservable_trivia_matches_configured_node_types` now asserts `if let cst::TriviaChild::Comment(_) = &child.1 {` and `return true;` present and `_ => {}` absent. No generator change (output was already correct).
Verified by running: `pytest tests/test_rust_unparser_generator.py` → 152 passed. Fix matches exactly what all three reviewers prescribed. Accept.

### test-2 — Fixed
Claim: no test exercises the `pos < 0` guard in `fully_consumed`; silent removal would wrap `pos as usize` and report any input "consumed." Real (unverified guard).
Diff at `crates/fltk-fmt-cli/src/lib.rs:132-138`: added `negative_pos_is_not_consumed` asserting `!fully_consumed("foo", -1)` and `!fully_consumed("", -1)`.
Verified by running: `cargo test` in `fltk-fmt-cli` → 12 passed including this test. Accept.

### test-3 — Fixed
Claim: behavior for `pos > char count` unspecified/untested; reviewer offered option (a) document + test, or (b) change impl to reject.
Disposition: chose (a). Doc comment extended (`lib.rs:59-64`) to specify negative⇒false and at/beyond⇒true (vacuous), with the rationale that the parser bounds `pos` by input length; added `pos_past_end_is_consumed` asserting `fully_consumed("foo", 3)` and `fully_consumed("foo", 1000)` are true.
Verified by running: test passes. Reviewer explicitly offered (a) as acceptable; responder executed it cleanly. Accept.

### quality-2 — Fixed + TODO(fmt-cli-per-consumer-about)
Claim: grammar-specific `about = "Format FLTK grammar files."` baked into the shared `FmtArgs` would mislead every out-of-tree consumer's `--help` (public-API concern, CLAUDE.md). Real.
Diff at `lib.rs:24`: `about` removed; now `#[command(version)]` (clap falls back to the generic struct doc comment). TODO comment + TODO.md entry added for the per-consumer `about` hook.
Assessment: the *harmful* part (the misleading baked string, created this iteration) is removed now — not deferred. The deferred part (threading `about` through `run_main` / `fltk_formatter_main!`) genuinely depends on increment-4 code that does not exist in this diff, so it is not "doable now"; tracked with a proper slug. Accept.

### efficiency-1 — Won't-Do
Claim: non-comment separator case scans trivia children twice (`_has_preservable_trivia` then `_count_newlines_in_trivia`). Reviewer's own consequence: "negligible bounded constant per separator," "leaving it as-is is reasonable," "not a blocker."
Rationale: pre-existing generator logic (diff changed only the clippy shape, not the two-pass structure); a Rust-only single-pass would diverge from the Python backend and break the hard cross-backend parity requirement → active harm, for no measurable benefit.
Assessment: rationale argues active harm (parity divergence) and the finding's stated consequence is negligible by the reviewer's own measurement. Textbook-acceptable Won't-Do. Accept.

### security / reuse — Won't-Do (no findings)
Both reviewer notes report "No findings." Nothing to address; forward-looking I/O items belong to the later `run_main` increment. Accept by default.

## Approved

11 dispositions: 5 Fixed verified (correctness-1/test-1/quality-1 shared, test-2, test-3, quality-2), 3 Won't-Do sound (efficiency-1, security, reuse), 2 TODOs acceptable (errhandling-1, errhandling-2 under one slug). All TODO slug join points verified (code comments + TODO.md entries). Generator suite green (152 passed); `fltk-fmt-cli` suite green (12 passed).

---

## Verdict: APPROVED

All dispositions acceptable. Both TODOs pass the two-question rubric (worth doing + genuine cross-backend design decision) and are properly tracked; the None-discard pattern is pre-existing generator logic, not a regression this diff introduced. All Fixed claims verified by running the affected suites. Both Won't-Do rationales sound. HEAD `762bbced1f5b44de2ad507db3a18a653c2ca585a`.
