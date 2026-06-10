# Dispositions — deep review round 1: span-source-as-py-crosscdylib

Commit reviewed: 588d55f. Fixes applied at: 28355db.

---

## errhandling-1
- Disposition: Fixed
- Action: `extract_source_text` now returns a distinct `TypeError` when `_fltk_cst_core_abi` exists but is not a `str`, naming the actual attribute type. `cross_cdylib.rs:77-82`.
- Severity assessment: Non-str marker produced a misleading "expected SourceText, got X" error that hid the real cause; diagnosability issue, no runtime correctness consequence.

## errhandling-2
- Disposition: Won't-Do
- Action: no change — the reviewer documented this as a non-finding.
- Rationale: Reviewer explicitly confirmed `?` propagation of `get_span_type` errors is correct and unchanged from prior behavior. No defect exists.

## errhandling-3
- Disposition: Won't-Do
- Action: no change — the reviewer documented this as a non-finding.
- Rationale: Reviewer confirmed `Py::new` OOM is correctly propagated as `PyMemoryError`. The comment about fast-path behavior in `errhandling-4` is an observation about comment accuracy, not a code defect.

## errhandling-4
- Disposition: Won't-Do
- Action: no change.
- Severity assessment: The reviewer notes that the "fast path…succeeds when caller is the same cdylib" comment in `extract_source_text` is slightly misleading when called via `span_to_pyobject`'s slow path (the incoming `SourceText` is locally-registered in the consumer cdylib, not `fltk._native`, so the fast path in `extract_source_text` actually falls to the slow path). This is a doc-accuracy observation, not a code error; the code path is correct and the behavior is documented in the `span_to_pyobject` slow-path doc comment. Editing the comment would require explaining a subtle re-entrancy that would obscure more than it clarifies.

## correctness-1
- Disposition: Fixed
- Action: Removed the slug `span-source-as-py-crosscdylib` from the `crosscdylib-abi-sentinel` TODO.md body; replaced with "alongside `extract_source_text`" phrasing. `TODO.md:17`.
- Severity assessment: The slug's presence in TODO.md caused the design §4 completion gate (`grep` for slug in TODO.md returns nothing) to falsely fail; also caused slug-scanning tooling to treat the retired work as open.

## security-1
- Disposition: Won't-Do
- Action: no change.
- Rationale: Explicitly addressed in design §2.2 and §3 as an accepted contract delta. The forgeable-marker UB is documented at the `unsafe` site and in the method docstring. The entry point is underscore-private and intentionally callable only by generated code passing `source_as_py` results. The `basicsize` sanity-check defense-in-depth suggestion is a valid hardening but is owned by `TODO(crosscdylib-abi-sentinel)` per the design, which explicitly delegates strengthening there. Implementing it here would be a partial redesign of the gate mechanism — out of respond-mode scope.

## security-2
- Disposition: Won't-Do
- Action: no change.
- Rationale: Explicitly addressed in design §2.2, §3, and the `TODO(crosscdylib-abi-sentinel)` comment. The pyo3-resolution-skew gap in the ABI string derivation is a documented known limitation; the fix (fold pyo3 version and/or layout hash into the marker) is explicitly deferred to the sentinel follow-up. No new finding.

## test-1
- Disposition: Fixed
- Action: Added `TestAbiMarkerClassattr.test_span_to_pyobject_fast_path_arc_sharing` in `tests/test_rust_span.py:255-270`, naming the same-cdylib fast path (`Span::type_object(py).is(&span_type)` → `Py::new`) as its explicit target via a `Grammar` node merge assertion.
- Severity assessment: Without a named test, a refactor removing the fast-path branch would pass all tests (slow path also produces correct results); the O(1) guarantee and its correctness implications were silently unguarded.

## test-2
- Disposition: Fixed
- Action: Added `match="SourceText"` to `pytest.raises(TypeError)` in `test_with_source_keeps_exact_behavior` and added a clarifying comment that a CI lane where this test is always skipped is a gap. `tests/test_rust_span.py:299-310`.
- Severity assessment: Without `match`, any `TypeError` for any reason would pass the assertion, making it possible for `with_source` to accept foreign `SourceText` (breaking the stated invariant) without test failure if some other `TypeError` was still raised.

## test-3
- Disposition: Fixed
- Action: Extended `test_source_text_abi_classattr_exists` to also assert `hasattr(type(src), "_fltk_cst_core_abi")` and `type(src)._fltk_cst_core_abi == SourceText._fltk_cst_core_abi`, matching what `extract_source_text` actually does (`obj.get_type().getattr(...)`). `tests/test_rust_span.py:240-249`.
- Severity assessment: Negligible runtime risk (pyo3 `#[classattr]` always attaches to `ob_type`), but the test was documenting the contract from the wrong access path.

## test-4
- Disposition: Fixed
- Action: Added `TestAC7BothBackends.test_cross_cdylib_sourceless_span_accessor` to `tests/test_phase4_rust_fixture.py:584-595`, constructing a cross-cdylib node with a sourceless span and asserting `has_source() is False` and value equality. Pins the `None` arm of `span_to_pyobject` on the slow path.
- Severity assessment: The `test_ac1_construction_default_span` test would catch a hard crash but would not catch subtler breakage (e.g. returning a source-bearing span when none was set, or returning wrong bounds). The explicit `has_source() is False` check closes that gap.

## test-5
- Disposition: Fixed
- Action: (a) Added `match="fltk._native.SourceText"` to `test_with_source_unchecked_str_raises_type_error`. (b) Added `test_with_source_unchecked_no_marker_attr_raises_type_error` (object with no `_fltk_cst_core_abi` attr → TypeError naming the type). (c) Added `test_with_source_unchecked_non_str_marker_raises_type_error` (non-str marker → TypeError naming the attribute) — this also exercises the errhandling-1 fix. `tests/test_rust_span.py:283-311`.
- Severity assessment: Without `match`, error-message regressions (e.g. losing the type name or attribute name) would be silently undetected.

## reuse-1
- Disposition: Fixed
- Action: Extracted `fn py_type_name(obj: &Bound<'_, PyAny>) -> String` in `cross_cdylib.rs:97-102`; both `extract_source_text` and `extract_span` now call it, eliminating the duplicated four-line type-name retrieval block.
- Severity assessment: The duplication was benign but meant divergent error-message formatting if either copy was edited independently; the helper eliminates the maintenance surface.

## efficiency-1
- Disposition: TODO(crosscdylib-abi-sentinel)
- Action: Added a `TODO(crosscdylib-abi-sentinel)` comment at the top of `span_to_pyobject` (`cross_cdylib.rs:104-107`) naming the cacheable process-constant facts (canonical-cdylib bool, bound classmethod). Deferred to the sentinel follow-up per the reviewer's own recommendation and design §3 precedent.
- Severity assessment: Per-span-read constant overhead on the consumer slow path (≤2 extra Python attribute lookups + 1 transient object per node read); small magnitude vs. O(N) it replaces; does not block the change.
