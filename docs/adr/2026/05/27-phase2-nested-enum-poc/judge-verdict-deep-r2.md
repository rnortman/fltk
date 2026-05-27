# Judge verdict — deep review

Phase: deep (design phase). Design: `design.md`. Base 0f9b786..HEAD 5f89161. Round 2.
Notes: 7 reviewer files; 22 findings. Prior verdict: REWORK (3 disputed).

## Rework verification

### errhandling-1 — Fixed (was TODO, disputed as do-now)

Prior dispute: `found.unwrap()` is mechanical → do-now, not TODO.
Rework disposition: Fixed.
Diff (33d6704..5f89161): all five `child_*` methods (`child_name`, `child_item`, `child_no_ws`, `child_ws_allowed`, `child_ws_required`) now use `found.expect("invariant: count==1 but found==None; logic error")`. The `TODO(cst-unwrap-diagnostic)` comment removed from top-of-file.
Assessment: fix matches the requested change exactly. Accept.

### errhandling-3 — Fixed (was TODO, disputed as do-now)

Prior dispute: `.map_err(...)` wrapping is mechanical → do-now, not TODO.
Rework disposition: Fixed.
Diff (33d6704..5f89161): all `children_*`, `child_*`, and `maybe_*` methods across both `Identifier` (3 methods) and `Items` (12 methods) now use `.enumerate()` and `.map_err(|e| PyTypeError::new_err(format!("NodeType.method_name: children[{idx}] is not a tuple: {e}")))`. The `TODO(cst-downcast-context)` comment removed from top-of-file.
Assessment: fix addresses the consequence — downcast errors now carry node type, method name, and index. Accept.

### efficiency-3 — Fixed (was TODO, disputed as do-now)

Prior dispute: `else { break; }` is a 2-line addition per method → do-now, not TODO.
Rework disposition: Fixed.
Diff (33d6704..5f89161): all 10 `child_*` and `maybe_*` methods now have `else { break; }` after the `count == 1` capture branch. `maybe_*` error messages changed from `"have {count}"` to `"have at least 2"` (string literal, no `format!`). Test at `test_rust_cst_poc.py:124` updated to match new error message. The `TODO(cst-accessor-early-exit)` comment removed from top-of-file.
Assessment: fix addresses the consequence — early exit avoids full O(n) scan on error path; error message is acceptable. Accept.

## Approved

19 dispositions: 9 Fixed verified (test-1, test-2, test-4, test-5, test-6, quality-1/efficiency-2, errhandling-1, errhandling-3, efficiency-3), 2 Won't-Do sound (test-3, efficiency-4), 7 TODOs acceptable (cst-constructor-import-context, cst-unknown-span-cache, rust-cst-macro x4, cst-generator-vs-list), 1 no-findings (correctness/security).

---

## Verdict: APPROVED
