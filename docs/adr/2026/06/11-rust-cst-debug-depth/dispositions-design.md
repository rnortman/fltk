# Dispositions: design review round 1 — non-recursive Debug for generated CST node structs

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Notes: `notes-design-design-reviewer.md`. Design: `design.md`.

design-1:
- Disposition: Fixed
- Action: "Edge cases / failure modes" deep-tree-teardown bullet rewritten. Verified the reviewer's API claim against `tests/rust_parser_fixture/src/cst.rs` (line 250: "Not pub: use span() / children() / push_child()"; no `drain`/`clear`/destructive accessor anywhere in the generated surface) — "pop into a worklist" was indeed unimplementable as written. Design now specifies the retain-handles mechanism (root-first `Vec<Shared<Expr>>` built during construction; drop root binding, then drop handles front-to-back; each drop deallocates exactly one node since the next level's refcount goes 2→1) and explicitly forbids adding a destructive child API. Test plan item 1 updated to retain levels during construction.
- Severity assessment: Highest-value finding. An implementer following the old text would either stall or grow the generated public API — exactly the scope creep CLAUDE.md warns against for out-of-tree consumers.

design-2:
- Disposition: Fixed
- Action: "Test plan" item 1 depth rationale restated. Verified the arithmetic gap (100 000 × 64 B ≈ 6.1 MiB < 8 MiB — doesn't close at its own low end). Now states ~5-10 frames per tree level under the old derive chain (`Shared::fmt` → derived node `fmt` → `debug_struct` → `Vec`/tuple → `ChildEnum` → next `Shared::fmt`), several hundred bytes to >1 KiB per level, so 100 000 levels comfortably overflows; added an explicit warning not to lower the depth from a per-frame estimate.
- Severity assessment: The conclusion (100 000) was right but the justification was wrong; left as-was, a future "optimization" of the depth could make the pre-fix demonstration vacuous and invite dropping the iterative-teardown requirement.

design-3:
- Disposition: Fixed
- Action: "Test plan" item 1 reworded: "the only fixture grammar with a self-recursive node type reachable programmatically" → `Expr` is "the simplest directly self-recursive node type", with the alternatives named (`lval`/`rval` mutual recursion and `rec_via_sub` in the same grammar — verified at `fltk/fegen/test_data/rust_parser_fixture.fltkg:36-37,66`; `Shared<Alternatives>` in `tests/rust_cst_fegen/src/cst.rs:779`). Location now explicitly chosen, not forced.
- Severity assessment: No material consequence to the plan; corrects a false uniqueness claim that would mislead a future reader relocating or extending the test.

Reviewer's open-question assessment (not a numbered finding): incorporated. Design open question 1 now records reviewer concurrence on filing `TODO(rust-cst-drop-depth)` plus the suggested comment locations (the `children` field emission in `gsm2tree_rs.py`; the deep-tree test's iterative teardown). Remains a user-decision item; does not block this fix.
