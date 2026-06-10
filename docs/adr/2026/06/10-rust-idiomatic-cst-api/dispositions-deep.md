Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

# Dispositions — Phase 0 deep review (round 2)

Reviewed commit: 807d56a. Round-1 fixes at: 655b99b. Round-2 fixes at: 798c9d1.

---

## errhandling-1

- Disposition: Fixed
- Action: `get_span_type` line ~258 (post-fix): `span_type.getattr("_fltk_cst_core_abi")` now uses `.map_err(|_| PyTypeError::new_err(format!("Span ABI mismatch: fltk._native.Span has no _fltk_cst_core_abi marker (pre-sentinel build); this module expects {FLTK_CST_CORE_ABI:?}")))` instead of bare `?`. `crates/fltk-cst-core/src/cross_cdylib.rs`.
- Severity assessment: Missing-attr case was the most realistic skew scenario (pre-Phase-0 build paired with post-Phase-0 build). Raw `AttributeError` with no ABI context made diagnosis impossible. Now produces a diagnostic `TypeError` consistent with all other mismatch branches and the design contract.

---

## errhandling-2

- Disposition: Fixed
- Action: `get_span_type` layout getattr now uses `.map_err(|_| PyTypeError::new_err(format!("Span ABI mismatch: fltk._native.Span has no _fltk_cst_core_abi_layout (partial-upgrade build); this module expects layout {expected_layout}")))`. `crates/fltk-cst-core/src/cross_cdylib.rs`.
- Severity assessment: Partial-upgrade scenario (string attr present, layout attr absent) previously surfaced as an opaque `AttributeError`. Now produces a consistent `TypeError` naming the expected layout.

---

## errhandling-3

- Disposition: Fixed
- Action: `extract_source_text` layout getattr (previously line 71) now uses `.map_err(|_| PyTypeError::new_err(format!("expected fltk._native.SourceText: _fltk_cst_core_abi_layout missing (old build without layout probe); this module expects layout {expected_layout}")))`. `crates/fltk-cst-core/src/cross_cdylib.rs`.
- Severity assessment: The internal inconsistency (missing string marker → generic TypeError; matching string + missing layout attr → raw AttributeError) was confusing and could cause callers checking for TypeError to miss the error. Now consistent throughout.

---

## correctness-1

- Disposition: TODO(crosscdylib-abi-size-probe)
- Action: SAFETY comments in `extract_source_text` and `extract_span` softened from "proving … identical" to "consistent with … narrows — not closes — the layout-skew window". Rustdoc on both `_fltk_cst_core_abi_layout` classattrs similarly updated. `TODO(crosscdylib-abi-size-probe)` added at the correct location in `cross_cdylib.rs` and in `TODO.md` with full rationale. Code path (size probe) is unchanged — the suggested "fold pyo3 version into ABI string" fix is the TODO content. `crates/fltk-cst-core/src/cross_cdylib.rs`, `span.rs`, `TODO.md`.
- Severity assessment: Size-preserving layout skew is low-probability (requires pyo3 field reorder without size change at the same fltk-cst-core version), but the SAFETY comments previously asserted soundness the probe cannot deliver. Softening the claim and adding the TODO removes the false-confidence hazard for future readers without requiring an unverified build-script change in respond mode.

---

## correctness-2

- Disposition: Fixed
- Action: All three missing-attr paths produce diagnostic TypeErrors (subsumes errhandling-1/2/3). Tests added for Span missing-marker and missing-layout cases via subprocess in `TestSpanPathAbiGate`: `test_missing_abi_marker_raises_type_error` (no `_fltk_cst_core_abi` — the most-realistic pre-Phase-0 skew) and `test_missing_layout_attr_raises_type_error` (no `_fltk_cst_core_abi_layout` — partial-upgrade). Both subprocess tests exercise the `get_span_type` gate in a consumer cdylib rebuilt from current code. Prior claim "Tests added for each case" was wrong for the Span path; corrected here. `tests/test_rust_span.py`.
- Severity assessment: The Span-path missing-marker branch (`cross_cdylib.rs:308-315`) was the finding's "most realistic skew" case (pre-Phase-0 Span has no `_fltk_cst_core_abi`). A regression to raw `?` or `if let Ok` there now produces a test failure.

---

## security-1

- Disposition: TODO(crosscdylib-abi-size-probe)
- Action: Same as correctness-1 — SAFETY comment overclaim fixed; residual gap documented with TODO. The finding correctly identifies that the size probe is necessary-not-sufficient. The pyo3-version-fold fix is the complete solution and is the TODO content. `crates/fltk-cst-core/src/cross_cdylib.rs`, `span.rs`, `TODO.md`.
- Severity assessment: The attack surface is accidental packaging skew (not an adversarial attacker), and the trigger probability (size-preserving field reorder across pyo3 patch) is low. Fail-loud on all likely real skews is preserved. The TODO tracks the remaining gap.

---

## security-2

- Disposition: Won't-Do
- Action: No change.
- Severity assessment: Informational only. `_with_source_unchecked` forgery is UB reachable from in-process Python, but only by code already executing arbitrary Python — no privilege boundary is crossed. The `ctypes`/native FFI paths are equivalent. The design explicitly declined the PyCapsule alternative as not removing this path (`span.rs:95-97`). No exploit vector beyond what arbitrary Python already enables.
- Rationale (Won't-Do): The span.rs SAFETY comment and method docstring document the out-of-contract nature. Adding defense-in-depth against in-process Python (which already owns arbitrary native access) provides no security benefit. The design ADR explicitly accepted this tradeoff.

---

## test-1

- Disposition: Won't-Do
- Action: No change. Finding is factually incorrect.
- Severity assessment: Zero. The reviewer claimed "`FakeSource` does not set `_fltk_cst_core_abi`" — source inspection at `tests/test_rust_span.py:553` shows `_fltk_cst_core_abi = SourceText._fltk_cst_core_abi` IS present. The test correctly reaches and exercises the layout mismatch path. No test gap exists here; test-2's additional coverage is additive and valuable for other reasons.
- Rationale (Won't-Do): The finding is a hallucination. The test already had the attribute set. Verified by reading `tests/test_rust_span.py:549-557` (pre-fix).

---

## test-2

- Disposition: Fixed
- Action: Four branch-coverage tests added in round 1 (layout mismatch, missing layout, non-int layout, missing ABI string). `test_source_text_all_markers_correct_succeeds` (round 1) contained dead `FakeSourceCorrect` class and a false "full slow path" comment; renamed to `test_source_text_fast_path_succeeds` in round 2, dead class removed, comment corrected to state the canonical SourceText hits the fast path (not the slow path). Cross-cdylib slow-path success coverage lives in `test_source_bearing_span_reads_from_consumer_cdylib`. `tests/test_rust_span.py`.
- Severity assessment: The false comment would have misdirected future readers about which path is exercised. Dead code removed. All branch-coverage tests remain and pin the actual branches.

---

## test-3

- Disposition: Fixed
- Action: Added `test_source_bearing_span_reads_from_consumer_cdylib` to `TestSpanToPyobjectCaching`: creates a source-bearing span in the consumer cdylib, reads it 5 times, asserts all results equal the expected span and all `has_source()`. Skippable via `pytest.importorskip("phase4_roundtrip_cst")`. `tests/test_rust_span.py`.
- Severity assessment: `WITH_SOURCE_UNCHECKED_METHOD` caching correctness was exercised only indirectly via `phase4_roundtrip_cst` integration (which could be skipped). A stale method cache could silently corrupt source-bearing spans on repeated reads from consumer cdylibs with no test signal.

---

## test-4

- Disposition: Fixed
- Action: Added `assert native.Span is FakeSpan, "patch did not take effect"` to the ABI-string-mismatch and layout-mismatch subprocess scripts. Added `assert hasattr(native.Span, "_fltk_cst_core_abi"), "real Span missing ABI marker (unexpected)"` to the control subprocess. `tests/test_rust_span.py`.
- Severity assessment: The fragility was real — a fixture import order change could silently make the patch a no-op, producing opaque failures. The assertions make subprocess scripts self-diagnosing. The `"OK"` guard already prevented false-passes; this improves failure messages.

---

## test-5

- Disposition: Fixed
- Action: `test_layout_mismatch_raises_type_error` subprocess script now captures `real_layout = native.Span._fltk_cst_core_abi_layout` before patching and asserts `str(real_layout) in msg`. `tests/test_rust_span.py`.
- Severity assessment: A regression that drops the expected-layout value from the error message would pass the test, leaving users with a less diagnostic error. Now pinned.

---

## reuse-1

- Disposition: Fixed
- Action: Extracted `fn py_attr_type_name(attr: &Bound<'_, PyAny>) -> String` helper at `crates/fltk-cst-core/src/cross_cdylib.rs:128-133`. All three inline attr-type extraction idioms replaced with calls to this helper. `crates/fltk-cst-core/src/cross_cdylib.rs`.
- Severity assessment: Three independent copies of the same idiom would diverge on fallback-string changes. Centralized.

---

## reuse-2

- Disposition: Fixed
- Action: `TODO(crosscdylib-abi-check-helper)` code comment added at `get_span_type`'s ABI-string-check section (`cross_cdylib.rs:307-311`) to satisfy the project TODO system (slug comment + TODO.md entry both present). The TODO.md entry at line 15 already existed from round 1; the missing code comment is the round-2 fix. `crates/fltk-cst-core/src/cross_cdylib.rs`.
- Severity assessment: Malformed TODO (entry without code comment) violates CLAUDE.md conventions; corrected. The underlying duplication (`get_span_type` and `extract_source_text` both implement the two-step ABI pair check) is deferred — the refactor is a mechanical generics extraction but would restructure both functions.

---

## quality-1

- Disposition: Fixed
- Action: Added comment on the `None` arm of `span_to_pyobject`: "`FLTK_NATIVE_SPAN_TYPE` is guaranteed populated here (IS_CANONICAL_CDYLIB init above called get_span_type as a side effect), so this is a cheap GILOnceCell hit — no additional Python import or validation." `crates/fltk-cst-core/src/cross_cdylib.rs`.
- Severity assessment: The hidden coupling between `IS_CANONICAL_CDYLIB` and `FLTK_NATIVE_SPAN_TYPE` could confuse future readers and lead to incorrect optimizations. Comment eliminates the question.

---

## quality-2

- Disposition: Fixed
- Action: Replaced the false comment added in round 1 ("slow path is unreachable in normal operation — arguments are always locally-registered SourceText objects") with a correct description: the slow path IS the normal path for cross-cdylib source-bearing span reads. Consumer-cdylib `span_to_pyobject` calls `source_as_py` (producing a consumer-registered SourceText) and passes it to `_with_source_unchecked` → `extract_source_text`; the consumer-registered type fails `downcast::<SourceText>()` and arrives at the slow path every call. The rewritten comment also notes the `FLTK_FOREIGN_SOURCE_TEXT_TYPE` cache (added for efficiency-1) and the TODO(crosscdylib-abi-check-helper) deferred refactor. `crates/fltk-cst-core/src/cross_cdylib.rs:63-84`.
- Severity assessment: The false comment directly contradicted `span.rs:207-211` and the test `test_source_bearing_span_reads_from_consumer_cdylib` in the same changeset. It would misdirect any future reader investigating slow-path caching.

---

## efficiency-1

- Disposition: Fixed
- Action: Added `FLTK_FOREIGN_SOURCE_TEXT_TYPE: GILOnceCell<Py<PyType>>` static. On the first cross-cdylib source-bearing span read, the full ABI pair validation runs and the validated foreign type object is stored via `get_or_init`. On subsequent calls, `FLTK_FOREIGN_SOURCE_TEXT_TYPE.get()` returns the cached type; a pointer comparison (`is()`) against the incoming object's type bypasses both `getattr` calls. Multiple foreign cdylibs are handled correctly: pointer mismatch falls through to full ABI validation and may overwrite the cache (last-writer-wins; all validated types are ABI-compatible so the only consequence is an extra getattr round on the first call from the second cdylib). `crates/fltk-cst-core/src/cross_cdylib.rs:38-67, 140-155`.
- Severity assessment: The slow path is the normal path for every cross-cdylib source-bearing span read from generated consumer code (confirmed by `span.rs:207-211` and exercised by `test_source_bearing_span_reads_from_consumer_cdylib`). Per-call type-constant re-validation on the design-committed hot path is now eliminated after the first call.

---

## efficiency-2

- Disposition: TODO(abi-gate-test-consolidation)
- Action: Added `TODO(abi-gate-test-consolidation)` to `TestSpanPathAbiGate` docstring and to `TODO.md`. Added a note that GILOnceCell does not cache errors so consolidation is feasible. No test restructuring — three separate subprocess tests remain for readability and isolation (now five, with the two new correctness-2 tests). `tests/test_rust_span.py`, `TODO.md`.
- Severity assessment: 5 vs 1 subprocess interpreter spawns is a real but modest overhead per CI run. The prior commit (3217a14) batched 14→4 for the same reason, so the project has established appetite for this optimization. Deferred rather than skipped — the TODO documents the feasibility argument.
