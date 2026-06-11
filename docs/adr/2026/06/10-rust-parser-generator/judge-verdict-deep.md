# Judge verdict — deep review

Style note: concise, precise, complete, unambiguous. No padding.

Phase: deep. Base 490bccf..HEAD 7619a5d (round-1 fixes 5780b71; round-2 fixes dbb9607; commit reviewed b95f772). Round 2 — APPROVED or ESCALATE only.
Notes: 7 reviewer files; 27 dispositions (quality-3 dup of correctness-1; quality-4 dup of test-1). Round 1 verdict: REWORK on errhandling-1, correctness-2, test-7, test-10. This round re-verifies those four against dbb9607 and confirms the 23 round-1-accepted dispositions are unchanged.

## Added TODOs walk

Unchanged since round 1 (no TODO dispositions touched by dbb9607). Round-1 analysis re-confirmed, condensed:

### security-1 — TODO(parser-depth-limit) at gsm2parser_rs.py (_gen_header)
Q1: yes — untrusted nested input causes uncatchable process abort, strictly worse than Python's `RecursionError`.
Q2: yes — configurable depth limit is new public API on every generated `Parser` (out-of-tree consumer surface per CLAUDE.md), cross-phase with the Phase 1 runtime. Iteration-created exposure is not silent: TODO.md entry + `TODO(parser-depth-limit)` + `//!` stack-depth warning in every generated file header.
Assessment: TODO acceptable.

### security-2 — TODO(nullable-loop) at gsm2parser_rs.py (_gen_item_multiple)
Q1: yes — crafted input can pin a nullable `*`/`+` term at 100% CPU.
Q2: yes — deliberately mirrors the Python backend (design §3 recorded decision); fixing requires a lockstep cross-backend parity call. Reviewer named the TODO as the acceptable alternative. Not created this iteration.
Assessment: TODO acceptable.

### reuse-1 — TODO(rust-str-lit-shared) at gsm2parser_rs.py (module level)
Q1: yes — escaping divergence is a real latent hazard (currently unreachable: names validated against `^[_a-z][_a-z0-9]*$`).
Q2: yes — extracting a shared escaping module reverses design §2.1/§5's compose-don't-refactor decision; requires auditing every `gsm2tree_rs.py` literal-emission site.
Assessment: TODO acceptable.

### reuse-2 — TODO(rust-naming-shared) at gsm2parser_rs.py (_child_enum_name)
Q1: yes — naming drift produces parser code referencing nonexistent CST enums, caught only at consumer `cargo` build.
Q2: yes, narrowly — exactly the shared-helper refactor design §2.1/§5 declined for this phase; revisiting is a design call.
Assessment: TODO acceptable.

### efficiency-1 — TODO(extend-children-owned) at gsm2parser_rs.py (_gen_item_multiple)
Q1: yes — per-child atomic inc+dec on the parse hot path, scaling with input size.
Q2: yes — blocked on `gsm2tree_rs.py` adding a consuming variant to the generated CST node API (public out-of-tree consumer surface); needs a CST API design pass.
Assessment: TODO acceptable.

Phase signal: 5 TODOs, none narrows this phase's deliverables — each is cross-phase, cross-backend, or reverses a recorded design decision. Not a wrong-scope pile.

## Other findings walk

### Round-2 reworked items (the four round-1 REWORKs)

#### errhandling-1 — Fixed (round 2)
Round-1 gap: `__init__` validation walk was not recursive; SUPPRESS-disposed dangling identifier inside a sub-expression escaped both validators, raising raw `KeyError` at `generate()`.
Fix at gsm2parser_rs.py:108-127 (dbb9607): recursive `_validate_term` descends `list | tuple` sub-expression terms, validating every `Identifier` at every depth, disposition-irrelevant.
Verification (empirical, against HEAD): reconstructed the exact round-1 escape — unlabeled INCLUDE sub-expression containing a SUPPRESS-disposed `Identifier('nosuchrule')`. Construction now raises `ValueError("Rule 'broken' references unknown rule 'nosuchrule'")` from gsm2parser_rs.py:113 — the new walk, the correct exception type for the CLI handler. The escape is closed at every nesting depth.
Nit (noted, not blocking): `test_dangling_identifier_in_subexpression_raises` uses an INCLUDE-disposed nested identifier; traced empirically, its ValueError originates at gsm2tree.py:370 (pre-existing `model_for_item` validation, which runs during `RustCstGenerator` construction at gsm2parser_rs.py:73 — before the new walk). The test pins the system-level behavior (nested dangling identifier → ValueError) but would pass even if the recursion were deleted; a SUPPRESS-shaped nested test would pin the walk uniquely. The top-level test does pin the walk (gsm2tree skips SUPPRESS items). The bug itself is fixed and verified; residual is test-pinning precision on an already-closed path — same weight as the correctness-5 tuple-test nit accepted in round 1.
Assessment: accept.

#### correctness-2 — Fixed (round 2)
Round-1 gap: union-**span** append arm (`cst::ValChild::Span` under a union label) compiled nowhere.
Fix: fixture grammar extended to `val := item:num | item:name | item:/[!@#$]+/` (rust_parser_fixture.fltkg:53). Regenerated artifacts verified: `parser.rs:774` `result.append_item(cst::ValChild::Span(item0.result))`; `cst.rs:9117-9121` `enum ValChild { Span(Span), Name(Shared<Name>), Num(Shared<Num>) }`. New `test_val_union_label_span` asserts `matches!(child, cst::ValChild::Span(_))`; existing num/name tests upgraded to assert their variants. `cargo test`: 44 passed.
Both §2.3 union rows (node, span) now compile and run in-repo.
Assessment: accept.

#### test-7 — Fixed (round 2)
Round-1 gap: no test asserted successful mutual-recursive consumption for the lval/rval pair.
Fix: `test_rval_mutual_recursion_positive` (`rval("foo?")` → `Some`, pos 4, `child_inner().is_ok()`) and `test_lval_mutual_recursion_positive` (`lval("42!")` → `Some`, pos 3, `child_inner().is_ok()`) — exactly the round-1 prescription. Base-case tests retained. All pass in `cargo test`.
Assessment: accept.

#### test-10 — Fixed (round 2)
Round-1 gap: else-return search satisfiable by item1's required-item else under a WS_ALLOWED downgrade.
Fix at test_gsm2parser_rs.py:671-690: search now bounded — `trivia_else_idx < item1_idx` and `return_idx < item1_idx` where `item1_idx = alt0_body.find("if let Some(item1)")` (asserted present). Downgrade analysis: WS_ALLOWED removes the trivia else-branch; the first `} else {` after the trivia call would then be item1's, which follows `if let Some(item1)` — the `< item1_idx` bound fails. Downgrade removing the trivia call entirely fails the `apply__parse__trivia` presence assert. The named regression is now detectable. Test passes against genuine output.
Assessment: accept.

### Round-1 accepted items (re-confirmed unchanged)

dbb9607 touches only the four reworked items plus strengthening additions to the val tests; no earlier fix was weakened. The following were verified in round 1 against 5780b71 and stand: errhandling-2 (explicit `NotImplementedError` for unhandled separator), correctness-1 (`ws_pattern = r"\s+"`, artifacts regenerated), correctness-3 (`generate()` memoized), correctness-4 (phantom `__one__` path segment removed), correctness-5 (`list | tuple` term dispatch), quality-1 (dead `_label_enum_name` deleted), quality-2 (`source_name=None` omits `from` clause), quality-3 (dup of correctness-1), quality-4 (dup of test-1), test-1 (SUPPRESS no-append body assertion), test-2 (`source_name=None` header test), test-3 (fegen capture_trivia=true integration), test-4 (comment-trivia structural test), test-5 (no `consume_literal` in regex-only grammar), test-6 (multi-alternative if-let ordering), test-8 (left-associativity span assertions), test-9 (`error_position().is_some()`), efficiency-2 (`Span::unknown()` placeholder).
Suites green at HEAD: `pytest fltk/fegen/test_gsm2parser_rs.py` 38 passed; `cargo test` (rust_parser_fixture) 44 passed.

## Approved

27 findings: 22 Fixed verified (incl. 2 duplicates), 5 TODOs acceptable. Nothing disputed.

---

## Verdict: APPROVED

All four round-1 REWORK items verified fixed (errhandling-1 empirically reproduced-then-closed; correctness-2 union-span arm compiles and runs; test-7 positive mutual-recursion pinned; test-10 search bounded). One non-blocking nit recorded under errhandling-1 (nested test pins behavior via gsm2tree's validator, not the new walk).
