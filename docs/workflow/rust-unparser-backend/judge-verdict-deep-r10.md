# Judge verdict — deep review batch 10

Phase: deep. Base 0285834..HEAD 4f81d53. Round 1.
Notes: 7 reviewer files (errhandling, correctness, security, test, reuse, quality, efficiency); 11 findings + security clean.
Reviewers reviewed `fa22e18`; responder's fixes landed in `4f81d53` (single commit `test(rust-unparser): address deep review batch 10 findings`). Verified against `fa22e18..HEAD` diff and current file state.

## Added TODOs walk

None. No disposition is TODO; diff (§4 test code) adds no `TODO(slug)` comments. Walk omitted.

## Other findings walk

### errhandling-1 — Fixed
Claim: `render_native!` (native_tests.rs:1021-1023) unparse-failure arm uses `.expect("native unparse must succeed")`, losing src/method context that the parse-failure arm one line up already captures; consequence is a guess-which-of-N-calls step when the expect fires.
Diff at native_tests.rs: `.expect(...)` replaced with `.unwrap_or_else(|| panic!("native unparse failed for {src:?} (method {}): returned None", stringify!($unparse)))` — verbatim the finding's requested fix, matching the parse-failure arm's diagnostics.
Assessment: nit/diagnostic; fix addresses the consequence at the named line. Accept.

### errhandling-2 — Fixed (deduped with test-2)
Claim: `assert_unparse_parity` lets mutual-None pass — `(py_str is None) == (rust_str is None)` is `True == True`, string check skipped, test green; consequence is a regression silencing both backends on a known-good corpus goes undetected.
Diff at unparser_parity.py:89-92: `assert py_str is not None, ...` added immediately after computing `py_str`, before the agreement check, with `rule/text/width/indent` in the message. Requiring non-None on the reference is correct here — the correctness review independently confirmed the corpus is intended fully-unparseable ("no vacuous all-None corpus path").
Assessment: should-fix (real test-blindness); fix matches both reviewers' requested change and closes the gap. Accept.

### correctness-1 — Fixed
Claim: native test parses `capture_trivia=false` while the cited "parity-validated reference" corpus parses `capture_trivia=true`; the byte-equal justification holds only by coincidence of input/config (`"x = y"` under `ws_required: nbsp`), not by construction. Consequence: no current false pass (native test is Rust-only and self-asserting), only the comment's justification is not airtight.
Diff at native_tests.rs: `Parser::new(src, None, false)` → `Parser::new(src, None, true)` with a comment tying the literals to the parity corpus. This is the more robust of the two reviewer-offered options (align the flag rather than soften the comment). Disposition states all native expected strings unchanged; verification line reports `native_unparse*` 10 passed.
Assessment: nit (justification tightening); fix makes the cross-reference hold by construction. Accept.

### test-1 — Fixed
Claim: `lval`/`rval` (indirect mutual left recursion) absent from corpus; distinct generated shape from self-referencing `expr` (two methods, two match arms) with zero cross-backend unparser coverage. Consequence: an alt-ordering/label-check regression there passes silently.
Diff at test_rust_unparser_parity_fixture.py:109-114: added `("lval","hello")`, `("lval","42!")`, `("rval","123")`, `("rval","hello?")` — exactly the finding's suggested entries. Disposition reports all 168 cells pass (parseable + unparseable on both backends).
Assessment: should-fix (coverage gap on structurally distinct codegen); fix adds base + indirect cases. Accept.

### test-2 — Fixed
Same assertion as errhandling-2 (both reviewers flagged the mutual-None gap). See errhandling-2. Accept.

### test-3 — Fixed
Claim: all native `#[test]`s import `crate::unparser` (fltkfmt); `unparser_default.rs` is reached only behind `#[cfg(feature = "python")]`, so its no-Python native linkage is unproven (design §4 wants the proof). Consequence: a compile/link failure in `unparser_default.rs` in the no-`python` config goes undetected by the native suite.
Diff at native_tests.rs: added `native_unparse_default_config_links`, a GIL-free `#[test]` driving `crate::unparser_default::Unparser().unparse_num` on `"123"` through `fltk-unparser-core`, asserting `"123"`. Matches the finding's requested representative test.
Assessment: should-fix (missing link/compile coverage for the second baked module); fix proves it. Accept.

### test-4 — Fixed
Claim: corpus has `("opt_item","1")` (present) but not `("opt_item","")` (absent); the absent-`?` path (`if let Some` skipped, `Some(empty doc)` returned) is distinct from both present-`?` and the `*`-loop-never-entered path (`zero_items ""`). Consequence: a bug in the absent-`?` path (e.g. None instead of Some) is uncaught.
Diff at test_rust_unparser_parity_fixture.py:126: added `("opt_item","")`, renders to `""` on both backends. `""` is non-None, so the new errhandling-2 assert is satisfied.
Assessment: should-fix (distinct path uncovered); fix adds the case. Accept.

### reuse-1 — Fixed
Claim: `unparse_python` duplicates the instantiate→dispatch→`resolve_spacing_specs` pipeline already in `fltk.plumbing.unparse_cst`, plus a direct `resolve_specs` import; consequence is independent drift yielding a stale-pipeline false parity result.
Diff at unparser_parity.py:46-50: now `doc = unparse_cst(unparser_result, py_cst, text, rule)` (caught `ValueError` → None), rendered via `render_doc`; direct `resolve_specs` import dropped. Signature confirmed against plumbing.py:302 (`unparser_result, cst, terminals, rule_name`) — args line up. `unparse_cst` raises `ValueError` on both missing-method (323-325) and None-result (329-331), so the disposition's behavioral note is accurate: a missing method changes from `AttributeError` to a caught-None, but the errhandling-2/test-2 assert re-surfaces it loudly as "reference returned None — generator or test-infra bug." Programming errors still fail loudly.
Assessment: should-fix (drift risk); fix is exactly the reviewer's suggested delegation, and the error-surface regression is mitigated by the assert added in the same batch. Accept.

### quality-1 — Fixed
Claim: four module-level `None` globals + identically-structured `_*_cached()` functions (copy-pasted 4×); `functools.cache` idiom exists to eliminate the boilerplate.
Diff: four `@functools.cache`-decorated plain functions (`_grammar`, `_py_parser_result`, `_py_unparser_result`, `_py_unparser_result_default`); all four `None` sentinels and `# noqa: PLW0603` suppressions removed; declaration order preserves the dependency chain. Matches the reviewer's suggested rewrite.
Assessment: nit/maintainability; fix removes the boilerplate cleanly. Accept.

### quality-2 — Fixed
Claim: `test_unparse_parity_fltkfmt` / `_default` are structurally identical 12-line functions differing in two values; the `test_rust_parser_parity_fixture.py` analog uses one parametrized function.
Diff at test_rust_unparser_parity_fixture.py:170-189: merged into one `test_unparse_parity` parametrized over a new `_BACKEND_CONFIGS` axis (`fltkfmt`/`default`), lambda-deferred Rust class refs. Matches the cited precedent; same cell count.
Assessment: nit; fix removes the copy-paste-per-config pattern. Accept.

### efficiency-1 — Fixed
Claim: `_py_cst`/`_rust_node` re-parse per `(rule,text,config,backend)` cell though parse depends only on `(rule,text)`; ~4× redundant parses (reviewer rated magnitude negligible at current sizes).
Diff at test_rust_unparser_parity_fixture.py:82-90: `@functools.cache` on both. Caching safety verified: both backends consume the same cached CST, which is sound because formatter config affects only unparse, not parse, and the CST is read-only to the unparser; 168 cells pass, confirming no aliasing/mutation issue. Args `(text,rule)` are hashable strings.
Assessment: nit (reviewer's own low magnitude); fix is cheap and correct. Accept.

### security — no findings
Security review reported none (all-hardcoded test corpus, no trust boundary). Responder took no action. Correct.

## Approved

11 findings: all Fixed and verified (errhandling-1/2, correctness-1, test-1/2/3/4, reuse-1, quality-1/2, efficiency-1; test-2 deduped with errhandling-2). Security: no findings, no action. No Won't-Do, no TODOs, no scope-N.

---

## Verdict: APPROVED

Every disposition is "Fixed" and each fix is confirmed at its named line to address the finding's consequence. The two fixes with cross-effects (reuse-1's AttributeError→None surface change, errhandling-2's mandatory non-None reference) compose correctly within the batch. Round 1.
