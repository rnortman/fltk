# Judge verdict — deep review

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Phase: deep. Base 74adcf8..HEAD ebdf24e (implementation 3d03b61/1eb2580, fix ebdf24e). Round 1.
Notes: 7 reviewer files; 4 distinct findings (reuse-1 and quality-1 are the same finding from two reviewers). 4 reviewers (error-handling, correctness, security, efficiency): no findings.

## Added TODOs walk

None. Full-range diff grep for added `TODO` lines: only implementation-log prose describing TODO *removal* and the `TODO.md` entry deletion. The iteration removes the `rust-cst-accessor-clone-efficiency` TODO (4 generator comments + TODO.md entry), per design §TODO removal. No new TODOs to score.

## Other findings walk

### test-1 — Fixed
Claim: no test exercises `child_<label>`/`maybe_<label>` count==0 among non-matching children — the zero-match path of the filter-under-guard scenario this diff introduces; consequence: a count-leak bug (non-matching children counted) would pass all regression tests.
Diff at `tests/test_rust_cst_poc.py:593-609` (ebdf24e): `test_child_label_raises_when_zero_among_non_matching` builds an Items node with two `no_ws` children only, asserts `child_item()` raises with exact message `"Expected one item child but have 0"`; `test_maybe_label_returns_none_when_zero_among_non_matching` same fixture, asserts `maybe_item()` returns `None`. Exactly the two tests the finding prescribed.
Assessment: fix addresses the consequence; both tests pass (63 passed). Accept.

### test-2 — Fixed
Claim: `test_accessor_identity_registry_pin` has a single child, so the Arc-identity guarantee is unverified in the mixed-Vec scenario this diff optimizes; consequence: an off-by-one in the guard loop returning the wrong child's Arc would not be caught.
Diff at `tests/test_rust_cst_poc.py:611-628` (ebdf24e): the `Identifier` item child is now surrounded by `no_ws` Span children (`append_no_ws(_span(0,1))` before, `append_no_ws(_span(2,3))` after) before the `r1 is r2` assertion; docstring updated to state the mixed-Vec intent.
Assessment: matches the finding's prescribed fix; test passes. Accept.

### test-3 — Fixed
Claim: pre-existing bare `pytest.raises(ValueError)` calls in `TestItemsMethods` don't pin messages; consequence: message regression (wrong count/label) in the zero-count `child_<label>` path passes undetected.
Diff at `tests/test_rust_cst_poc.py:321, 325, 342, 346, 363, 367, 384, 388`: all eight bare raises now carry `match=` with the exact message for each of the four label variants and both error shapes ("Expected one {label} child but have 0", "Expected at most one {label} child but have at least 2"). Covers the primary line plus the seven consistency lines the finding listed.
Assessment: complete; tests pass. Accept.

### reuse-1 / quality-1 — Fixed
Claim: the `(count, first)` lock-scope scan block (comment + scan, only `{label_enum_name}::{rust_variant}` interpolated) is emitted verbatim in both `child_<label>` and `maybe_<label>` in `_per_label_methods`; consequence: silent divergence on future edits — generated methods compile and pass even when only one site is updated.
Diff at `fltk/fegen/gsm2tree_rs.py:1375-1399` (ebdf24e): `_emit_count_first_scan_block(self, label_enum_name, rust_variant) -> list[str]` extracted; both emitters now call it (`gsm2tree_rs.py:1462-1463` and `1479-1480`); the duplicate inline blocks removed. Helper line list compared against the removed lines: byte-identical strings, so emitted Rust output is unchanged — confirmed by the absence of generated-`.rs` template drift in ebdf24e.
Assessment: single-site emission achieved exactly as both findings prescribed. Accept.

## Notes on commit hygiene

ebdf24e additionally commits `tests/rust_parser_fixture/src/collision_cst.rs` — the increment-1 template regeneration (TODO removal + four new shapes) that was missed in 3d03b61 and sat uncommitted in the working tree. Disclosed in the dispositions doc; the file's diff matches the four design templates with `collision`-grammar substitutions only. Not a disposition defect.

## Disputed items

None.

## Approved

5 findings (4 distinct): 5 Fixed verified. 0 Won't-Do, 0 TODOs.

Verified independently: `uv run pytest tests/test_rust_cst_poc.py` — 63 passed at HEAD, including the four new/extended regression tests.

---

## Verdict: APPROVED

All dispositions verified against the fix-commit diff and a passing test run. No TODOs added; the iteration's purpose was TODO retirement and the join-key cleanup (4 code comments + TODO.md entry) is complete.
