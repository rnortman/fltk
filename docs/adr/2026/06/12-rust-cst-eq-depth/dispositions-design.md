# Dispositions: design review round 1 — rust-cst-eq-depth

Findings from `notes-design-design-reviewer.md`. All three fact-checked against source at b02cb8f; all valid; all fixed in `design.md`.

design-1:
- Disposition: Fixed
- Action: Rewrote test 6 in §5 (`test_eq_variant_mismatch_unequal`) to use same-label/different-variant children via the union-label `val` rule (`ValChild::Num` vs `ValChild::Name` under `item`), with the type-unchecked `push_child` construction as an alternative. Verified the reviewer's claim: the driver's `la != lb ||` short-circuit (§2.2d) makes the original lhs-vs-atom construction unreachable for the wildcard arm.
- Severity assessment: The test would have passed for the wrong reason, shipping the variant-mismatch wildcard arm untested; a generator bug there could make mismatched trees compare equal.

design-2:
- Disposition: Fixed
- Action: Added a paragraph to §2.2c: span-only union members emit the parameter as `_worklist` (only Span arm, never pushes), following the generator's existing conditional-underscore convention (`_py`/`_span_type`). Verified: `Num`/`Name`/`Trivia` are span-only child-union members and all fixture crates run clippy with `-D warnings` (Makefile lines 53-54, 67-71).
- Severity assessment: Without this, every regenerated in-tree grammar fails `make check` (unused-variable under `-D warnings`); a late compile break instead of a designed-for case.

design-3:
- Disposition: Fixed
- Action: Header now states implementation base b02cb8f with function names authoritative over line numbers; corrected the three shifted citations (`_eq_method` → 1859-1880, `_emit_drain_arm` → 1907-1924, `_drop_block` → 1926-1964). Verified `git diff --stat 5d94733..b02cb8f` shows the 8-line deletion in `gsm2tree_rs.py`.
- Severity assessment: Minor — wrong-function landings for late-file citations, recoverable by symbol name; no design logic affected.
