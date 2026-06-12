# Deep correctness review — rust-cst-accessor-clone-efficiency

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Reviewed: 74adcf8..1eb2580 (`git diff`), design.md, generated outputs at HEAD.

No findings.

Verified:

- **Template logic.** All four emitters (`_generic_child`, `children_<label>`, `child_<label>`, `maybe_<label>`) match the design shapes exactly. `child()`: len read + at-most-one clone under guard; `let Some(...) = entry else` covers n==0 and n>1, message preserves exact `n`. `child_/maybe_`: count + first-match clone in one guard scope; `count == 1` gate clones only the first match; `count != 1` / `count > 1` checks and exact messages unchanged from base. `children_<label>`: filter+clone under guard, per-element `to_pyobject` outside, conversion order and partial-failure point unchanged.
- **Lock discipline.** Everything inside each guard block is pure Rust (`len`, label `PartialEq`, `Child::clone`, `Vec` collect). `format!`, `PyValueError::new_err`, `to_pyobject`, `into_pyobject` all execute after the block expression ends (guard dropped). Same single-guard atomicity as base: count/first/n all derive from one consistent snapshot, so the `first.expect(count==1 ⇒ Some)` invariant cannot be violated by concurrent writers.
- **Generated-file drift.** Normalized/deduped every added line across all six regenerated `.rs` files: 62 `child()` sites + 119 per-label triples, all fitting the four templates with only label-enum/variant/message substitutions. No stray changes.
- **Behavioral delta.** Only the design-dispositioned one: error paths no longer call `to_pyobject` before raising (validate-before-convert). Unobservable through documented API; raised types/messages identical.
- **Tests.** New `TestFilterUnderGuardRegression` (7 tests) exercises mixed-label filtering, exact-count messages (5, 10), unique-match success paths, and registry identity. `tests/test_rust_cst_poc.py`: 61 passed.

Commit reviewed: 1eb2580.
