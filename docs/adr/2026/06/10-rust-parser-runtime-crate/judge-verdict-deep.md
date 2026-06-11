# Judge verdict — deep review

Style: concise, precise, complete, unambiguous. No padding.

Phase: deep. Base d23d1df..HEAD 08e1bad. Round 2 (round 1: REWORK on test-1; rework commit 08e1bad touches only `tests/memo_toy.rs` + dispositions doc).
Notes: 7 reviewer files; 25 findings (reuse-1 ≡ quality-3 ≡ efficiency-4; quality-2 ≡ efficiency-1).
Verified: working tree at 08e1bad, crate clean; `cargo test -q -p fltk-parser-core` → 47 + 8 pass.

## Added TODOs walk

Re-verified unchanged since round 1 (rework commit does not touch these files' relevant sections):

### security-1 — TODO(consume-regex-anchor) at terminalsrc.rs (`consume_regex`)
Q1: yes — unanchored `find_at` gives O(rules × n²) on attacker-controlled input.
Q2: yes — fix changes the regex type in the design §3.1 Phase 2 generated-code contract (`fltk_parser_core::regex::Regex`); cross-phase API decision.
Assessment: TODO acceptable. Slug in code and `TODO.md`.

### security-2 — TODO(apply-depth-limit) at memo.rs (`apply`)
Q1: yes — unbounded recursion aborts the process; regression vs Python's catchable `RecursionError`.
Q2: yes — limit value/configurability/error shape depend on Phase 3's error channel, which does not exist yet.
Assessment: TODO acceptable. Slug in code and `TODO.md`.

### security-3 — TODO(error-msg-escape) at errors.rs (`format_error_message`)
Q1: yes, eventually — escape injection inherited byte-for-byte from the Python backend.
Q2: yes — joint Python+Rust fix required to preserve the Phase 3 parity comparator; reviewer prescribed exactly this deferral.
Assessment: TODO acceptable. Slug in code and `TODO.md`.

## Other findings walk

### test-1 — Won't-Do (rework target; re-adjudicated this round)
Reviewer claim: Python's grammar is `a := b "+" num | <nothing>` and the Rust port omits the alternative.
Ground truth: claim is false. test_memo.py:87-88 states `a := b "+" num` / `b := a | num`; `indirect_a` returns `None` when `b` fails (test_memo.py:113); `test_fail` asserts `apply_result is None` (test_memo.py:253). Verified directly this round.
Rework verification against the round-1 prescription, diff 098aa70..08e1bad:
1. `<nothing>` fallback removed from `indirect_a` — `b` returns `None` → `return None` (memo_toy.rs:140-143). Done.
2. File-header grammar comment now `a := b "+" num` (memo_toy.rs:12) — also closes the open tail of correctness-1. Done.
3. `test_fail` restored to `assert!(result.is_none())` (memo_toy.rs:300-310); doc comment cites test_memo.py:253 and the failed-recursion-seed path (design §2.5 step 5). Done.
4. `test_failure_caching` restored: first call `None`, `count_after_first > 0` (preserves the test-7 fix), second call `None` with unchanged invocation count — re-covers `Failure` cache-hit dispatch per design test plan §4.1. Done.
5. Self-contradictory doc comment replaced; dangling `test_fail_indirect_none` reference and "Num(97)" fragment gone (memo_toy.rs:125-129). Done.
Disposition text correctly states Won't-Do with citations test_memo.py:88/:114/:253 and owns the prior wrong "Fixed".
Assessment: accept. All five prescription items shipped; suite passes at HEAD.

### correctness-1 — Fixed
`rule_expr` commit semantics verified round 1; the open tail (wrong header grammar comment) is closed by rework item 2 above.
Assessment: accept.

### Remaining 20 findings — verified round 1, unaffected by rework
The rework commit's only code change is `tests/memo_toy.rs`; round-1 verification of these stands at 08e1bad:
errhandling-1 (two-branch panic dispatch, memo.rs:125-136); errhandling-2 (invariant comment at `call_result.unwrap()`); errhandling-3 (structurally resolved via reuse-1); test-2 (exact `assert_eq!`, errors.rs:308-310); test-3 (both-quotes `py_repr`); test-4 (control chars); test-5 (`consume_regex` at `pos == len`); test-6 (trailing-newline `pos_to_line_col`); test-7 (non-vacuous count assertion — retained through the rework); test-8 (multiline format, corrected expected string verified against terminalsrc.py:191-197); reuse-1/quality-3/efficiency-4 (`chars().enumerate()` initializer); quality-1 (fallback `Expected:` header); quality-2/efficiency-1 (dead `_existing_ri` removed); quality-4 (`use` import); efficiency-2 (dominant-path lookup eliminated, remainder transparently declined — accepted round 1); efficiency-3 (move not clone); efficiency-5 (`shrink_to_fit`).

## Disputed items

None. The single round-1 disputed item (test-1) is resolved.

## Approved

25 of 25 findings: 20 Fixed verified (incl. dedups reuse-1/quality-3/efficiency-4 and quality-2/efficiency-1; efficiency-2 partial with sound rationale), 1 Won't-Do sound (test-1, bogus finding correctly rejected with citations), 3 TODOs acceptable (security-1/2/3), correctness-1 fully closed.

---

## Verdict: APPROVED

All dispositions acceptable at 08e1bad. Round 2.
