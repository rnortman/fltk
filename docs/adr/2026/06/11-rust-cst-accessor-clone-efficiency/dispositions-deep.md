Style: concise, precise, complete, unambiguous. No padding, no preamble.

Commit reviewed: 1eb2580. Fix commit: ebdf24e.

error-handling: No findings.

correctness: No findings.

security: No findings.

test-1:
- Disposition: Fixed
- Action: Added `test_child_label_raises_when_zero_among_non_matching` and `test_maybe_label_returns_none_when_zero_among_non_matching` to `TestFilterUnderGuardRegression` in `tests/test_rust_cst_poc.py`. Each builds an Items node with only `no_ws` children and asserts `child_item()` raises with the exact message "Expected one item child but have 0" and `maybe_item()` returns None.
- Severity assessment: Without these, a bug that leaked non-matching children into the count (returning count > 0 when zero matches exist) would pass all regression tests. Low likelihood given the label-compare logic, but the gap was real in the filter-under-guard scenario this diff specifically introduces.

test-2:
- Disposition: Fixed
- Action: Extended `test_accessor_identity_registry_pin` in `tests/test_rust_cst_poc.py` to surround the Identifier item child with two `no_ws` Span children before asserting `r1 is r2`. The test now exercises the filter loop in a mixed-Vec scenario as the diff specifically optimizes.
- Severity assessment: Without non-matching siblings, an off-by-one in the filter loop that happened to return the correct child in the single-child case would not be caught by the identity pin test.

test-3:
- Disposition: Fixed
- Action: Added `match=` to all eight bare `pytest.raises(ValueError)` calls in `TestItemsMethods` (`tests/test_rust_cst_poc.py` lines 321, 325, 342, 346, 363, 367, 384, 388). Exact message strings pinned for all four label variants and both error types (count==0 for `child_<label>`, "at least 2" for `maybe_<label>`).
- Severity assessment: A message regression (wrong count, wrong label name) in any of these paths would have passed undetected. Low consequence given the new regression tests cover count==5, but the zero-count error path for child_<label> was only weakly covered.

reuse-1 / quality-1 (same finding from two reviewers):
- Disposition: Fixed
- Action: Extracted `_emit_count_first_scan_block(self, label_enum_name: str, rust_variant: str) -> list[str]` private helper at `fltk/fegen/gsm2tree_rs.py` immediately before `_per_label_methods`. Both `child_<label>` and `maybe_<label>` emitters in `_per_label_methods` now call the helper; the duplicate 16-line block is removed. Emitted Rust output is byte-for-byte identical (no regeneration needed).
- Severity assessment: Duplication was silent — both emitters compiled and tested correctly even when one diverged. Future modifications (e.g., early exit at count==2, invariant panic message rewording) required two edits; now require one.

efficiency: No findings.

Note: commit ebdf24e also includes the pre-existing uncommitted regeneration of `tests/rust_parser_fixture/src/collision_cst.rs`, which was missed in the implementation commit (3d03b61) but was already correct in the working tree; `make check` confirms it.
