# Judge verdict — deep review (round 2)

Phase: deep. Base b02cb8f..HEAD f741649. Round 2 (APPROVED or ESCALATE only).
Notes: 7 reviewer files (error-handling, security, reuse: no findings); 9 findings, two duplicate pairs (correctness-1 = quality-2, correctness-3 = efficiency-1) → 7 distinct.
Round-1 verdict was REWORK on the correctness-3/efficiency-1 TODO disposition (failed rubric Q2 — mechanical fix). Dispositions doc still records the TODO; commit f741649 resolved it. Per orchestrator instruction, judged by code at HEAD.
Style: concise, precise, complete, unambiguous; no padding. Audience: LLM/human.

## Added TODOs walk

### correctness-3 / efficiency-1 — formerly TODO(gsm2tree-nondeterministic-emission) at gsm2tree.py:407
Round-1 disputed item. Disposition text lags; code at HEAD shows the do-now fix applied (f741649).
Q1 (worth doing): yes — hash-randomized `model.types` iteration shuffled `isinstance` unions and `_MUTATOR_ALLOWED_CHILD_TYPES` tuples on every regen (~80 churn lines in this diff), making `make check` cleanliness seed-dependent and invalidating content-hash build caches.
Q2 (design/owner input required): no — and it was done now: `gsm2tree.py:422` iterates `for c in sorted(allowed_classes)` with a comment explaining the set-hash-order cause and citing the `py_annotation_for_model_types` precedent. Regenerated Python outputs pin canonical alphabetical order (verified in `fltk/fegen/bootstrap_cst.py`: `Alternatives | Identifier | Trivia`; `(Item, Trivia, fltk.fegen.pyrt.terminalsrc.Span)`).
TODO fully removed: `git grep gsm2tree-nondeterministic-emission` finds nothing outside docs/adr; `TODO.md` has no entry.
Assessment: round-1 dispute resolved by promotion to do-now Fixed. Accept. No TODOs remain at HEAD for this change (the `rust-cst-eq-depth` TODO itself was also removed from `TODO.md` and both code sites, per design §2.5).

## Other findings walk

### correctness-1 / quality-2 — Fixed (duplicate pair)
Claim: generated comment in `EqWorklistItem::compare` ("Guards … dropped before any push") asserted a lock-window invariant that does not hold; a maintainer trusting it could add lock-acquiring work and introduce same-thread RwLock re-entry deadlock.
Code: `gsm2tree_rs.py` `_eq_block` now emits "Guards are held across the child iteration; pushes to the worklist are Arc::clone + Vec::push (no lock acquisition)" — the wording quality-2 prescribed, matching design §2.2b and the actual guard lifetime in `_emit_eq_arm` (guards live across the child `for` loop; pushes take no locks). Present in generator + all 7 regenerated .rs outputs (grep: 8 files, 1 hit each); "dropped before any push" absent from the tree.
Assessment: comment now states the true invariant at every site. Accept.

### correctness-2 — Fixed
Claim: `test_multi_child_eq_worklist` unequal half placed the mismatch at the deepest lhs-spine leaf (same shape EQ-2 covers), not in an rhs branch as its comment claimed; `false` from a non-final worklist item was untested.
Code: `tests/rust_parser_fixture/src/native_tests.rs:231-273` — builder reparameterized to `rhs_diff_level: Option<usize>`; the diff span goes on the rhs Atom's `Num` at level 50; lhs spine all `Span::unknown()`. The level-50 rhs pair returns `false` from `compare` while lhs pairs remain pending — non-final worklist item, as claimed. Doc comment matches. Passes.
Assessment: exercises exactly the named gap. Accept.

### test-1 — Fixed
Claim: `la != lb` label-mismatch early-exit untested; an inversion would make differently-labeled children compare equal undetected.
Code: `test_eq_label_mismatch_unequal` (EQ-7, `native_tests.rs:317-328`) — same Shared `Atom` pushed under `ExprLabel::Atom` vs `ExprLabel::Rhs`; same span, same count, ptr_eq-equal child value, labels differ only — the assert can fail only via the label check. Passes.
Assessment: surgically pins the path; matches the reviewer's suggested construction. Accept.

### test-2 — Fixed
Claim: child-count length check untested; a wrong operator would zip-compare to min(len) and could return true for trailing-children differences.
Code: `test_eq_child_count_mismatch_unequal` (EQ-8, `native_tests.rs:330-344`) — zero-child vs one-child `Expr`, both `Span::unknown()`; only the length check can produce `false`. Passes.
Assessment: matches the suggested construction. Accept.

### test-3 — Fixed
Claim: no Python test exercised `__eq__` for distinct-allocation trees; the pymethod → `Shared<T>::eq` → iterative `T::eq` delegation chain was unpinned (existing test only hit the ptr_eq self-compare).
Code: `test_node_eq_distinct_allocation_deep_tree` (`tests/test_phase4_rust_fixture.py:463-476`) — parses `"a = 1; b = 2; c = 3;"` twice through independent Rust parsers, asserts `r1.cst == r2.cst` via Python `==`. Passes.
Assessment: pins the delegation chain per the reviewer's fix shape. Accept.

### quality-1 — Fixed
Claim: `into_drop_item` and `eq_shallow_enqueue` emitted in separate `impl {enum_name}` blocks under identical guards; split-block pattern propagates.
Code: generator emits both inside one `impl` (diff at `gsm2tree_rs.py:603-645`). Verified in regenerated `tests/rust_parser_fixture/src/cst.rs:7420-7448`: single block holds both; the only other `impl ExprChild` (:7451) is the `#[cfg(feature = "python")]` block the finding itself exempts as legitimately separate.
Assessment: merged as specified. Accept.

## Verification at HEAD

- `cargo test --manifest-path tests/rust_parser_fixture/Cargo.toml --release` (eq-filtered): 10 passed, 0 failed — EQ-1..EQ-8 all green.
- `uv run pytest tests/test_phase4_rust_fixture.py -k eq`: 5 passed, including the new deep-tree test.
- Worktree clean at f741649 (only untracked ADR doc dirs) — sort fix and regenerated outputs committed; regen cleanliness no longer seed-dependent.

## Disputed items

None. The round-1 disputed item (correctness-3/efficiency-1) was resolved as the verdict required: fix applied, TODO comment and `TODO.md` entry removed, outputs regenerated.

## Approved

9 findings (7 distinct): 7 Fixed verified (correctness-1/quality-2 pair, correctness-2, test-1, test-2, test-3, quality-1, and the former correctness-3/efficiency-1 TODO promoted to Fixed at f741649).

---

## Verdict: APPROVED

All dispositions acceptable at HEAD f741649. The single round-1 defect was cured by doing the work rather than deferring it; no TODOs remain in this change. Commit: f741649.
