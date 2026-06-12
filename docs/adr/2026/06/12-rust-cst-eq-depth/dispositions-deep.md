# Dispositions — rust-cst-eq-depth respond round 1

Commit reviewed: 44458c5. Fixes applied at 57612a8.

---

correctness-1:
- Disposition: Fixed
- Action: Rewrote EqWorklistItem::compare comment in `fltk/fegen/gsm2tree_rs.py:2091` from "Guards are held only for the duration of one arm and dropped before any push" to "Guards are held across the child iteration; pushes to the worklist are Arc::clone + Vec::push (no lock acquisition)." Regenerated all outputs.
- Severity assessment: Misleading comment documenting a lock-window invariant that does not hold; a maintainer trusting it while adding lock-acquiring work to eq_shallow_enqueue would introduce a real same-thread RwLock re-entry deadlock.

correctness-2:
- Disposition: Fixed
- Action: Restructured `test_multi_child_eq_worklist` in `tests/rust_parser_fixture/src/native_tests.rs:228-260`. Replaced `leaf_span` parameter (which placed the mismatch at the deepest lhs spine leaf) with `rhs_diff_level: Option<usize>` (which places the mismatch in the rhs branch at a mid-level, level 50). The unequal case now exercises a `false` result from a non-final worklist item.
- Severity assessment: Unequal-case coverage gap — a regression mishandling `false` from a non-final worklist item would not have been caught by the old test; the equal-case half still exercised multi-pair worklists.

correctness-3:
- Disposition: TODO(gsm2tree-nondeterministic-emission)
- Action: Added `TODO(gsm2tree-nondeterministic-emission)` comment at `fltk/fegen/gsm2tree.py:407` and entry in `TODO.md`. Pre-existing defect surfaced by this change's regeneration; out of scope to fix in this respond round.
- Severity assessment: Every `make gencode` can produce semantically-neutral but content-distinct generated files, obscuring real diffs and invalidating content-hash build caches. No runtime behavior change.

test-1:
- Disposition: Fixed
- Action: Added `test_eq_label_mismatch_unequal` (EQ-7) in `tests/rust_parser_fixture/src/native_tests.rs:314-328`. Constructs two `Expr` nodes using `push_child` with `ExprLabel::Atom` vs `ExprLabel::Rhs` on the same `ExprChild::Atom` value and asserts `!=`.
- Severity assessment: The `la != lb` early-exit in the iterative driver was untested; an inversion would cause nodes with different child labels to compare equal, undetected.

test-2:
- Disposition: Fixed
- Action: Added `test_eq_child_count_mismatch_unequal` (EQ-8) in `tests/rust_parser_fixture/src/native_tests.rs:330-344`. Constructs one `Expr` with zero children and one with one `append_atom` child (both `Span::unknown()`) and asserts `!=`.
- Severity assessment: The child-count length check was untested; a wrong operator or off-by-one would cause nodes with different child counts to zip-compare against min(len_a, len_b) and potentially return true, undetected.

test-3:
- Disposition: Fixed
- Action: Added `test_node_eq_distinct_allocation_deep_tree` in `tests/test_phase4_rust_fixture.py:463-476`. Parses `"a = 1; b = 2; c = 3;"` twice through independent Rust parsers and asserts `r1.cst == r2.cst` via Python `==`.
- Severity assessment: The Python `__eq__` pymethod → `Shared<T>::eq` → iterative `T::eq` delegation chain was unpinned by any Python test; a breakage in the delegation would go undetected by the Python suite while only Rust tests covered the underlying logic.

quality-1:
- Disposition: Fixed
- Action: Merged the two separate `impl {enum_name} {}` blocks for `into_drop_item` and `eq_shallow_enqueue` into one in `fltk/fegen/gsm2tree_rs.py:606-650`. Both methods now emit under a single `impl {enum_name} {` open/close pair. Regenerated all outputs.
- Severity assessment: Cosmetic but propagating: every future private method added under the same condition would follow the split-block pattern, requiring readers to scan multiple non-contiguous impl blocks to understand the type's private API.

quality-2:
- Disposition: Fixed
- Action: Same fix as correctness-1 — quality-2 and correctness-1 are the same finding from two reviewers.
- Severity assessment: See correctness-1.

efficiency-1:
- Disposition: TODO(gsm2tree-nondeterministic-emission)
- Action: Same TODO as correctness-3 — efficiency-1 and correctness-3 are the same finding from two reviewers.
- Severity assessment: See correctness-3.
