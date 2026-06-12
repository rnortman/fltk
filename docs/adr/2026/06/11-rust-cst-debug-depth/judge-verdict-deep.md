# Judge verdict — deep review

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Phase: deep. Base 8c10cea..HEAD 7267eb4 (reviewers saw 2f9b05e; fixes landed in 7267eb4). Round 1.
Notes: 7 reviewer files; 3 report no findings (error-handling, correctness, security); 14 dispositioned findings.

## Added TODOs walk

### quality-2 — TODO(rust-cst-eq-depth) at crates/fltk-cst-core/src/shared.rs:93 and fltk/fegen/gsm2tree_rs.py (_node_block), entry in TODO.md
Q1 (worth doing): yes — `PartialEq` on generated nodes recurses through `Shared<T>` children unbounded; `assert_eq!` on a deep parser-produced tree aborts the process. Same DoS class as the Debug/Drop paths this increment fixed; reviewer states the consequence concretely.
Q2 (design/owner input required): yes — iterative equality is not a mechanical transplant of the Drop pattern: it needs paired traversal of two trees with cross-tree read-lock ordering, and a semantic choice the reviewer himself flags ("worklist or depth-capped shallow form, depending on semantics wanted"). Design doc scoped it out as pre-existing and "not user-authorized here"; the reviewer's requested remedy was the TODO entry, not the fix.
Not created/worsened by this iteration: PartialEq emission is untouched by the diff; the "cannot silently defer" rule does not apply. Verified: TODO.md entry with slug + fix sketch present; `TODO(rust-cst-eq-depth)` comments at both code sites (shared.rs:93 above the `PartialEq` impl, gsm2tree_rs.py above the emitted impl).
Assessment: TODO acceptable; disposition (Fixed — the finding asked for the TODO) sound.

## Other findings walk

### error-handling-1, correctness-1, security-1 — Won't-Do (no findings)
All three reviewers reported "No findings" with audit traces (lock discipline, steal soundness, generator/output drift byte-checked). "Won't-Do" is bookkeeping for empty reports; nothing to adjudicate. Accept.

### test-1 — Fixed
Claim: stale `assert "#[derive(Clone, Debug)]" in poc_source` passes only via child enums; no generator-level Debug/Drop assertions; consequence is a silent generator regression caught only at the slower Rust compile gate.
Diff at tests/test_gsm2tree_rs.py: new `TestNodeDebugDrop` class with five tests — derive(Clone)-only on `Identifier` struct (positive + negative exact-form assertions), `impl fmt::Debug for Identifier`/`Items`, `f.debug_struct("Identifier")`, `"<{} child(ren)>"`, `enum DropWorklistItem {` presence, `impl Drop for Items` present / `impl Drop for Identifier` absent. Covers every concrete assertion in the reviewer's fix list. 146 tests pass at HEAD.
Assessment: fix addresses the consequence. Accept.

### test-2 — Fixed
Claim: no flat-grammar absence check for `DropWorklistItem`; consequence is dead_code under -D warnings on regression.
Diff: `TestMinimalGrammar.test_flat_grammar_no_drop_worklist` asserts both `"DropWorklistItem" not in` and `"impl Drop" not in` minimal output — exactly the prescribed fix. Passes.
Assessment: Accept.

### test-3 — Fixed
Claim: `test_node_struct_pyclass_gated` mislabels a child-enum fact as a node-struct fact.
Diff: docstring rewritten; assertion replaced with exact-form positive `#[derive(Clone)]\npub struct Identifier {`, negative `#[derive(Clone, Debug)]\npub struct Identifier {`, plus manual-Debug positives — matches the reviewer's prescribed exact forms.
Assessment: Accept.

### test-4 — Fixed
Claim: deep-tree tests hold ≤1 worklist item; multi-child drain path unexercised; a dropped second push or wrong variant arm would go undetected.
Diff at tests/rust_parser_fixture/src/native_tests.rs: `test_multi_child_drop_worklist` builds a 100-level chain where each `Expr` has `lhs:Expr` + `rhs:Atom` (both sole-owned → both stolen and enqueued; worklist holds ≥2 items per level), shared leaf pinned by a clone to also exercise the no-steal branch. Matches the reviewer's prescribed shape (100-level, two node-typed children). Test passes; full fixture suite 51/51 green.
Assessment: Accept.

### test-5 / reuse-1 — Fixed (one fix, two findings)
Claim: `test_shared_strong_count` in the fixture duplicates the core-crate contract test.
Diff: fixture test re-scoped via doc comment as a downstream-crate public-reachability test, pointing to the canonical contract test in fltk-cst-core. The reviewer explicitly offered this alternative ("if the fixture-crate test is meant to confirm the method is accessible from downstream crates, add a comment to that effect").
Assessment: Accept.

### test-6 — Fixed
Claim: `IdentifierChild::Span` Debug output discarded without assertion.
Diff at crates/fltk-cst-spike/src/spike_tests.rs:368: `let _ = format!(...)` replaced with `assert!(span_child_dbg.contains("Span"), ...)` — the reviewer's minimum bar. Spike suite 43/43 green.
Assessment: Accept.

### test-7 — Fixed
Claim: implicit drop ordering in test 5 leaves the parser-cache teardown unverifiable to readers.
Diff: explicit `drop(r); drop(parser);` added with a comment stating the LIFO order and what each drop exercises — exactly the prescribed fix.
Assessment: Accept.

### reuse-2 — Fixed
Claim: `100_000usize` literal in test 5 not joined to `DEEP_TREE_DEPTH`.
Diff at native_tests.rs:115: literal replaced with `let n = DEEP_TREE_DEPTH;`, comment updated to reference the constant.
Assessment: Accept.

### quality-1 — Fixed
Same defect as test-1/test-3; same fix verified above. Accept.

### quality-3 — Fixed
Claim: drain-arm body copy-pasted per class in `_drop_block`; divergence risk on future edits.
Diff at fltk/fegen/gsm2tree_rs.py: `_emit_drain_arm` static method extracted, loop calls it; emitted lines are character-identical to the removed inline block (verified line-by-line in the diff), so generated output is unchanged for this refactor.
Assessment: Accept.

### efficiency-1 — Fixed
Claim: emitted `Drop` heap-allocates the worklist via `collect()` even when no child is stolen; fires per discarded partial node on the parser backtracking hot path.
Diff: emitted template replaced with `Vec::new()` + per-child `drain_into` loop — the reviewer's exact prescribed shape. Semantics traced: each top-level child item gets `drain_into` exactly once (steal-or-decrement), arm-end drop of the consumed `Shared` handle triggers the childless early-return path; grandchildren pushes are the only allocations. Behavior-equivalent, strictly fewer allocations. All six generated outputs regenerated (diff shows the new shape in src/cst_fegen.rs, src/cst_generated.rs, both spike/fegen mirrors, all three fixture cst files); workspace compiles, fixture (51) + spike (43) + Python (146) suites green at HEAD.
Assessment: Accept.

### efficiency-2 — Won't-Do
Claim: generator recomputes `_child_variants_for_rule` per rule (4 call sites) with O(U) list membership; consequence stated as "codegen-time only; negligible at current grammar sizes" and the reviewer's own fix is marked "Optional given current scale."
Rationale: generator-time only, tens of rules, lru_cache/set conversion adds complexity for no observable benefit; the pre-pass already computes the union once.
Assessment: nit by the reviewer's own framing; no parse-time impact; rationale matches reality. Won't-Do sound. Accept.

## Disputed items

None.

## Approved

14 findings (+3 empty reports): 11 Fixed verified, 1 Won't-Do sound (efficiency-2), 1 TODO acceptable (quality-2), 1 duplicate consolidated (test-3/quality-1 share test-1's fix).

---

## Verdict: APPROVED

All dispositions verified against the 2f9b05e..7267eb4 diff and green test runs at HEAD. Round 1.
