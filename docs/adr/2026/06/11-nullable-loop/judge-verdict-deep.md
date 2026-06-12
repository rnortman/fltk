# Judge verdict — deep review

Concise. Precise. Complete. Unambiguous. No padding.

Phase: deep. Base 61f9384..HEAD 880b964 (notes were written against intermediate 6ac52d5; all dispositions verified against final HEAD; this verdict supersedes the prior one judged at 37c1035). Round 1.
Notes: 7 reviewer files (reuse: no findings); 13 findings. Dispositions: `dispositions-deep.md`.

## Added TODOs walk

None. No finding dispositioned TODO; diff adds no `TODO(slug)` comments (it removes `TODO(nullable-loop)` — verified gone from TODO.md, generator, and generated output via `test_todo_nullable_loop_comment_removed`). The prior `TODO(validator-subexpr)` from the intermediate commit was promoted to Fixed in the rework (af1c7d6) and removed from TODO.md and code (grep clean).

## Other findings walk

### errhandling-1 — Fixed
Claim: `validate_no_repeated_nil_items` never recurses into `Sequence[Items]` terms; nested `+`/`*` over nullable terms passes validation; consequence is no design-time error, guard-only protection.
Inspection at HEAD: `_collect_repeated_nil_errors` (`fltk/fegen/gsm.py:356-375`) checks every item via `is_multiple()` + `term_can_be_nil`, then recurses into `Sequence` terms regardless of outer quantifier — arbitrary nesting depth covered. `validate_no_repeated_nil_items` (`gsm.py:378-398`) now drives the recursive walk. The `isinstance(item.term, Sequence)` dispatch matches the established pattern at `term_can_be_nil` (`gsm.py:186`) and `_mark_trivia_reachable_in_items` (`gsm.py:338`); term is never a bare `str`, so the str-is-Sequence trap does not apply. New tests `test_repeated_nil_validation_rejects_nested_subexpr` (`fltk/fegen/test_nil_validation.py:79`) and `test_repeated_nil_validation_rejects_deeply_nested_subexpr` (`:121`) pin one- and two-level nesting; both pass.
Assessment: fix addresses the consequence exactly as the reviewer prescribed. Accept.

### correctness-1 — Fixed
Same root finding and same fix as errhandling-1. Design §3.1's "rejected at grammar-validation time" claim now holds for sub-expression-nested repetitions; the validator docstring (`gsm.py:381-382`) documents the recursive behavior. Accept.

### correctness-2 — Fixed (via documentation)
Claim: `Item.can_be_nil` is now grammar-dependent but `Rule._can_be_nil`/`Items._can_be_nil` memos are not keyed on the grammar → stale results when one object is queried under two grammars with differing identifier sets. Reviewer's suggested fixes included "document the single-grammar-per-object invariant on Rule/Items".
Inspection: docstrings added at `gsm.py:27-35` (Rule) and `gsm.py:82-87` (Items) state the invariant precisely. Responder's rejection of grammar-id keying is sound: memos live in frozen slotted dataclasses; the standard pipeline queries each object under one final grammar.
Minor imprecision, noted not disputed: the Rule docstring's supporting sentence ("classify_trivia_rules uses dataclasses.replace ... which resets the cache, satisfying this invariant") overstates the mechanism — only trivia-reachable Rules are replaced (`gsm.py:302-307`) and `Items` objects are shared unreplaced. The standard pipeline is actually safe because pre/post-classification grammars carry identical identifier sets, so the invariant as stated ("differing identifier sets") is never violated. The invariant statement itself — the load-bearing part — is accurate. Nit-level; does not change the disposition outcome.
Assessment: matches a remedy the reviewer explicitly offered; hazard is documented for out-of-tree consumers. Accept.

### security-1 — Fixed
Claim: `==` guard does not terminate on position regression (`one_result.pos < pos`); consequence is the DoS resurfacing if a future consume path breaks monotonicity — defense-in-depth should not depend on the invariant it defends against.
Diff at HEAD: Rust emits `if one_result.pos <= pos { break; }` (`fltk/fegen/gsm2parser_rs.py:708`); Python emits `iir.LogicalNegation(iir.GreaterThan(...))` → `not one_result.pos > pos` (`fltk/fegen/gsm2parser.py:564-576`), semantically `<=`. All regenerated artifacts carry the new guard (verified by grep: `fltk_parser.py` ×4, `rust_cst_fegen/src/parser.rs` ×4, `rust_parser_fixture/src/parser.rs` ×2, plus bootstrap/trivia/toy/unparsefmt parsers in the diffstat), each ahead of `pos = one_result.pos`. Tests updated to assert the new strings and ordering.
Assessment: exactly the suggested fix, both backends, regen complete. Accept.

### security-2 — Fixed (a) + documented (b)
(a) Sub-expression recursion gap: same fix as errhandling-1; nested trigger tests pass. Closed.
(b) Context-sensitive regex under-approximation (`\ba*`, `(?=x)`): reviewer's suggested fix for (b) was documentation — "the cheap, load-bearing half". Validator docstring (`gsm.py:384-389`) now states the guard MUST remain as defense-in-depth and names the exact residual patterns. No code change for (b) is consistent with the reviewer's own framing (gap report, not vuln report; guard terminates these cases).
Assessment: both halves resolved per the reviewer's prescription. Accept.

### test-1 — Fixed
Claim: `test_plus_loop_has_guard` asserted the condition string but never `break`; a non-terminating guard body would pass.
Inspection: rewritten test (`tests/test_nullable_loop_guard.py:726-743`) asserts the `not one_result.pos > pos` condition, asserts `break` appears in the region between the condition and `pos = one_result.pos`, and asserts guard-before-update ordering. Passes.
Assessment: condition + terminating effect both verified. Accept.

### test-2 — Fixed
Claim: `test_star_loop_has_guard` (Python) had no ordering assertion; guard-after-update regression undetected.
Inspection: ordering assertion added (`tests/test_nullable_loop_guard.py:745-754`): `guard_idx < pos_update_pos`. Passes.
Assessment: accept.

### test-3 — Fixed
Claim: the newly-tightened REQUIRED+nullable-term path of `validate_trivia_rule_not_nil` was untested.
Inspection: `test_trivia_rule_not_nil_required_nullable_term` (`fltk/fegen/test_nil_validation.py:224-250`) constructs `_trivia` with `quantifier=gsm.REQUIRED`, `term=gsm.Regex(r"\s*")`, asserts ValueError — exactly the reviewer's prescribed test. Passes.
Assessment: accept.

### test-4 — Fixed
Claim: `test_one_or_more_empty_literal_is_nil` docstring argued for `False` then asserted `True` — documentation trap.
Inspection: docstring rewritten (`tests/test_nullable_loop_guard.py:568-580`): states the formula upfront (`is_optional() OR term_can_be_nil` = `False OR True` = `True`), explains why the item is nil; contradicting argument removed.
Assessment: accept.

### quality-1 — Fixed
Same finding as errhandling-1/correctness-1; the implemented `_collect_repeated_nil_errors` follows the reviewer's suggested helper shape (per-Items walk, recurse into `Sequence` terms regardless of quantifier). Accept.

### quality-2 — Fixed
Claim: `one_result_ref` named local used only in the guard, inconsistent with the inline-lookup pattern at the other three `one_result` references.
Diff: named local removed; guard condition now uses inline `loop.block.get_leaf_scope().lookup_as("one_result", iir.Var)` (`fltk/fegen/gsm2parser.py:570-576`), matching the reviewer's preferred "consistent inline" option.
Assessment: accept.

### efficiency-1 — Fixed
Claim: the throwaway cargo crate cold-compiled regex-automata every pytest session.
Inspection: `CARGO_TARGET_DIR` now points at `_repo_root / "target" / "nullable-loop-guard-test"` and the binary path follows it (`tests/test_nullable_loop_guard.py:379-399`). Empirically verified: full guard-test file (including `test_rust_backend_guard`) ran in 0.81 s on this machine — deps reused, only the generated crate recompiles.
Assessment: accept.

### efficiency-2 — Fixed
Claim: `test_cross_backend_parity` re-ran full Python generation, duplicating `test_python_backend_guard` with zero added coverage.
Inspection: replaced with a near-zero-cost cross-reference check (`tests/test_nullable_loop_guard.py:421-440`) asserting `_RUST_MAIN_RS` encodes the shared expected outcomes (pos=2 / exit-on-None / None-correct for "b"). Reviewer offered delete-or-strengthen; the replacement is closer to delete-plus-tripwire — the redundant generation (the stated consequence) is gone, and the residual assertions pin the Rust binary's expectations against silent weakening. Marginal test value, but the efficiency consequence is fully resolved and no false coverage is claimed (docstring is explicit that runtime demonstration lives in the two backend tests).
Assessment: accept.

## Cross-cutting verification

- `uv run pytest -q`: 1332 passed at HEAD (16.5 s) — rework introduced no regressions; regenerated artifacts consistent with generators.
- No stale `TODO(validator-subexpr)` or `TODO(nullable-loop)` anywhere outside ADR docs (grep clean).

## Disputed items

None.

## Approved

13 findings: 13 Fixed verified (correctness-2 fixed via the reviewer-sanctioned documentation remedy; security-2(b) via the reviewer-prescribed docstring note). 0 Won't-Do, 0 TODOs.

---

## Verdict: APPROVED

All dispositions acceptable; every Fixed claim verified against HEAD 880b964 by code inspection and passing tests.
