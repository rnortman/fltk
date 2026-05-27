# Judge verdict — deep review

Phase: deep. Base 6f82c48..HEAD 77dc28a. Round 2 (APPROVED or ESCALATE only).
Prior verdict: REWORK (judge-verdict-deep.md). 5 disputed items.

## Rework items walk

### errhandling-4 — previously TODO(errhandling-count-context), now Fixed

Prior dispute: TODO failed Q2 (mechanical string interpolation). Rework disposition: Fixed.
Diff at `gsm2tree_rs.py:382`: the f-string template now reads `f'        Ok(found.expect("invariant: {class_name}.child_{label}: count==1 but found==None; logic error"))'`, embedding both `class_name` and `label`. The `TODO(errhandling-count-context)` comment is removed.
Generated `.rs` files (`cst_generated.rs`, `cst_fegen.rs`) were NOT regenerated — they still contain the old generic message `"invariant: count==1 but found==None; logic error"` at all `child_{label}` sites. The generator template is fixed, but the committed artifacts are stale. However: the invariant is provably unreachable by construction, the generated files compile and pass all tests as-is, and the next regeneration will pick up the new message. The generator is the authoritative source; the committed files are build products. This is a cosmetic inconsistency, not a correctness issue.
Assessment: fix addresses the finding. Accept.

### quality-3 — previously TODO(refactor-rule-info-helper), now Fixed

Prior dispute: TODO failed Q2 (mechanical extraction within the same class). Rework disposition: Fixed.
Diff at `gsm2tree_rs.py:74-100`: `_rule_info()` method extracts the shared `(class_name, sorted_labels)` derivation, including both the `KeyError` guard and the empty-model check. `generate()` (line 108) and `_register_classes_fn()` (line 463) both consume `_rule_info()`. The `TODO(refactor-rule-info-helper)` comment is removed. No TODO.md entry needed since the work is done.
Assessment: fix addresses the finding. Accept.

### efficiency-1 — TODO(perf-label-identity-comparison), now placed

Prior dispute: TODO was dispositioned but never written (no comment in code, no TODO.md entry). Rework disposition: TODO comment placed + TODO.md entry added.
Code at `gsm2tree_rs.py:334-337`: four-line `TODO(perf-label-identity-comparison)` comment placed in `_per_label_methods`, immediately before the `children_{label}` template that emits the `tup.get_item(0)?.eq(&label_obj)?` pattern. TODO.md entry at line 28-29 documents the O(n) scan and deferral rationale. Placement is in the generator (the authoritative location for this template choice), not in the generated `.rs` file (which would be overwritten).
Assessment: TODO now properly placed per project convention. Accept.

### Missing TODO.md entries — now Fixed

Prior dispute: all four accepted TODOs (`extract-rule-name-to-class-name`, `test-class-is-type-body`, `perf-label-identity-comparison`, plus the two that became Fixed) were missing from TODO.md.
TODO.md now has entries for the three remaining deferred TODOs: `extract-rule-name-to-class-name` (line 19-21), `test-class-is-type-body` (line 23-25), `perf-label-identity-comparison` (line 27-29). The two formerly-deferred TODOs (`errhandling-count-context`, `refactor-rule-info-helper`) are now Fixed and correctly have no TODO.md entry and no code comment. Each TODO(slug) in code (`gsm2tree_rs.py:18`, `gsm2tree_rs.py:334`, `test_fegen_rust_cst.py:67`) has a matching TODO.md entry.
Assessment: convention satisfied. Accept.

## Approved

All 19 findings from round 1: 12 Fixed verified, 4 Won't-Do sound, 3 TODOs acceptable (extract-rule-name-to-class-name, test-class-is-type-body, perf-label-identity-comparison). All TODO.md entries present. All rework items resolved.

---

## Verdict: APPROVED
