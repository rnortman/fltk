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

---

# Phase 2 deep-review dispositions

Reviewer notes: notes-deep-{error-handling,correctness,security,test,reuse,quality,efficiency}-reviewer.md.
Phase 2 diff: 7e39dfb..fb8852f. Fix commit: see HEAD.

---

## errhandling-1 (Phase 2)

- Disposition: Won't-Do
- Action: No change.
- Severity assessment: `get_span_type` propagates raw `AttributeError` when `_fltk_cst_core_abi` is absent on `fltk._native.Span`. Finding applies to Phase 0 code unchanged by Phase 2.
- Rationale (Won't-Do): `get_span_type` operates against the canonical `fltk._native.Span` — the same artifact as this cdylib. The attr is present by construction; absent-attr is only reachable if a user manually deletes the classattr post-import, which is unsupported. The design scoped the sentinel to the cross-cdylib barrier (A2); `get_span_type` is within-cdylib. These findings were already handled in Phase 0 round 2 for the paths where they are reachable; this path is not.

## errhandling-2 (Phase 2)

- Disposition: Won't-Do
- Action: No change.
- Severity assessment: `get_span_type` layout getattr propagates raw `AttributeError` on partial-upgrade.
- Rationale (Won't-Do): Same argument as errhandling-1 (Phase 2). Both attrs are added in the same commit; partial-upgrade where one is present and the other absent requires surgical deletion.

## errhandling-3 (Phase 2)

- Disposition: Won't-Do
- Action: No change.
- Severity assessment: `extract_source_text` layout getattr propagates raw `AttributeError` when string matched but layout attr absent.
- Rationale (Won't-Do): Phase 0 code unchanged by Phase 2. A legitimate finding on Phase 0 code; however, this was already fixed in Phase 0 round 2 (`errhandling-3` disposition there is Fixed). The reviewer's Phase 2 notes appear to have re-raised this without noticing the Phase 0 round-2 fix. Verified: the current code has `.map_err` on this getattr.

## errhandling-4 (Phase 2)

- Disposition: Fixed
- Action: Generator template `fltk/fegen/gsm2tree_rs.py` (hand-in sites, ~line 557): changed `let _ = registry::register_if_absent(py, addr, obj);` to `registry::register_if_absent(py, addr, obj)?;`. Regenerated all five outputs (`src/cst_generated.rs`, `src/cst_fegen.rs`, `tests/rust_cst_fixture/src/cst.rs`, `tests/rust_cst_fegen/src/cst.rs`, `crates/fltk-cst-spike/src/cst.rs`) — all ~54 hand-in sites updated.
- Severity assessment: A `MemoryError` or future error from `get_registry` would be swallowed; caller returns `Ok` while the registry entry is absent; subsequent reads of that child mint new handles, silently breaking `is`-identity with no error signal. High severity.

## correctness-1 (Phase 2)

- Disposition: Fixed
- Action: `fltk/fegen/gsm2tree_rs.py` — removed `rule_name_map` dict comprehension and `.get()` fallback from `_native_per_label_methods`; removed `class_name` parameter (now unused); added `rule_name: str` parameter; updated the single call site in `_node_block` to pass `rule_name` directly; replaced the conditional `if rule_name:` guard with an unconditional `self._label_type_info(rule_name, label)` call; removed the dead else fallback branch. Regenerated all five outputs.
- Severity assessment: The dead fallback branch (`ref_type = f"&{enum_name}", None, 2`) would silently emit wrong-shaped union accessors for span-only or single-node labels on a lookup miss. The O(rules) dict inversion per call was also eliminated.

## correctness-2 (Phase 2)

- Disposition: Fixed
- Action: `fltk/fegen/gsm2tree_rs.py:1409,1439` — added `f` prefix to both TODO comment strings inside `_per_label_methods`. Regenerated all five outputs; generated code now reads e.g. `see children_name above` instead of the literal `{label}`.
- Severity assessment: Comment-only; no behavioral effect. Misleading to readers of generated code.

## security-1 (Phase 2)

- Disposition: TODO(rust-cst-debug-depth)
- Action: Added `TODO(rust-cst-debug-depth)` to `TODO.md`; added `// TODO(rust-cst-debug-depth): derived Debug recurses without depth bound` comment at `fltk/fegen/gsm2tree_rs.py` on the `#[derive(Clone, Debug)]` emit line for node data structs (~line 638). Design §5 already documents the cycle case; the TODO extends the documented hazard to cover unbounded-depth DoS on acyclic attacker-controlled input.
- Severity assessment: `derive(Debug)` recurses through `Shared<T>` children with no depth bound. Parser input is frequently untrusted; tree depth is attacker-controlled via input nesting. Downstream services that debug-log nodes from untrusted input risk stack exhaustion → uncatchable abort. The cycle case is design-accepted (§5); unbounded-depth DoS on acyclic input is the new exposure from Phase 2.

## test-1 through test-5 (Phase 2)

- Disposition: Won't-Do (Phase 0 findings; outside Phase 2 scope)
- Action: No change. These findings target `test_rust_span.py` Phase 0 tests and were addressed in the Phase 0 round-2 respond. Verified already fixed at HEAD.
- Severity assessment: N/A for Phase 2 round.

## test-6 (Phase 2)

- Disposition: Fixed (already present at HEAD before this round)
- Action: `tests/test_gsm2tree_rs.py` — `test_handle_struct_emitted` pins `pub struct PyIdentifier {` and `inner: Shared<Identifier>,` (private field). Present at HEAD.
- Severity assessment: A generator regression emitting a wrong handle field type would pass all prior string-match tests.

## test-7 (Phase 2)

- Disposition: Fixed (already present at HEAD before this round)
- Action: `tests/test_gsm2tree_rs.py` — `test_to_py_canonical_uses_registry` added. Present at HEAD.
- Severity assessment: A generator emitting `Py::new` directly in `to_py_canonical` would break identity undetected.

## test-8 (Phase 2)

- Disposition: Fixed (already present at HEAD before this round)
- Action: `tests/test_gsm2tree_rs.py` — `test_py_new_uses_force_register` added. Present at HEAD.
- Severity assessment: Omitting `force_register` in `#[new]` would allow identity to hold only via hand-in, not construction.

## test-9 (Phase 2)

- Disposition: Fixed (already present at HEAD before this round)
- Action: `tests/test_phase4_rust_fixture.py` — `test_children_label_accessor_identity` added. Present at HEAD.
- Severity assessment: `children_<label>()` returning a freshly-minted handle instead of going through the registry would break identity on that path.

## test-10 (Phase 2)

- Disposition: TODO(registry-unit-tests)
- Action: TODO already in `TODO.md` and `TODO(registry-unit-tests)` comment at `crates/fltk-cst-core/src/registry.rs:128–130`. The comment explains the pyo3/cdylib linkage blocker. No new action.
- Severity assessment: Registry logic tested only through Python integration tests; a logic inversion in `register_if_absent` would require Python-level identity tests to detect.

## test-11 (Phase 2)

- Disposition: Fixed (already present at HEAD before this round)
- Action: `tests/test_phase4_rust_fixture.py:test_extend_children_duplicates_entries` — `assert first is ident` added. Present at HEAD.
- Severity assessment: Premature-eviction bug could produce two mutually-`is`-equal new handles not equal to the original; missing assertion would not catch it.

## test-12 (Phase 2)

- Disposition: Fixed (already present at HEAD before this round)
- Action: `tests/test_phase4_rust_fixture.py` — `test_shared_child_mutation_visible_through_two_parents` added. Present at HEAD.
- Severity assessment: Arc-clone semantics of `extract_from_pyobject` (hand-in) were unverified at the Python level.

## test-13 (Phase 2)

- Disposition: Fixed
- Action: `crates/fltk-cst-spike/src/spike_tests.rs` — added `child_item_unexpected_child_type` (pushes `ItemsChild::Span` under `ItemsLabel::Item`, asserts `UnexpectedChildType`) and `child_item_count_error_beats_type_error` (two wrong-type children → `ChildCount` wins). `tests/rust_cst_fixture/src/native_tests.rs` — added `child_lbl_unexpected_child_type_returned_by_accessor` (pushes `EntryChild::Literal` under `EntryLabel::Key`, asserts `UnexpectedChildType`) and `child_lbl_count_error_beats_type_error_with_wrong_types` (two `Literal` children → `ChildCount` wins).
- Severity assessment: The `UnexpectedChildType` arm in every generated `child_<lbl>` / `maybe_<lbl>` was dead from a test coverage perspective; a regression removing or inverting that branch would pass all tests.

## test-14 (Phase 2)

- Disposition: Fixed
- Action: `crates/fltk-cst-spike/src/spike_tests.rs` — added `children_item_skips_off_type_variant`. `tests/rust_cst_fixture/src/native_tests.rs` — added `children_key_skips_off_type_variant`. Both: push one typed child and one off-type child under the same label; assert `children_<lbl>().count() == 1` and `children().len() == 2`.
- Severity assessment: A regression changing `filter_map` to `map` (panicking) or dropping the filter entirely would pass all tests.

## test-15 (Phase 2)

- Disposition: Fixed
- Action: `crates/fltk-cst-spike/src/spike_tests.rs` — added `child_item_exactly_one_ok` and `child_item_zero_returns_child_count_error` for the node-typed `item` label.
- Severity assessment: Node-typed label path of `child_<lbl>` had no compiled test coverage in spike; generator bug for `ItemsLabel::Item` would be undetected.

## test-16 (Phase 2)

- Disposition: Fixed
- Action: `crates/fltk-cst-spike/src/spike_tests.rs` — added `maybe_item_two_returns_child_count_error`.
- Severity assessment: `"0 or 1"` string in `maybe_<lbl>` error messages was unpinned by spike tests; generator emitting `"1"` instead would pass spike.

## reuse-1 (Phase 2)

- Disposition: TODO(crosscdylib-abi-check-helper)
- Action: TODO already in `TODO.md` as `crosscdylib-abi-check-helper`. Phase 0 code unchanged by Phase 2. No new action.
- Severity assessment: Three copies of `py_type_name` inline pattern diverge on fallback-string changes. Minor.

## reuse-2 (Phase 2)

- Disposition: TODO(crosscdylib-abi-check-helper)
- Action: Same TODO as reuse-1. No new action.
- Severity assessment: Two per-type ABI-pair-check blocks with already-diverging error-message wording. Minor.

## reuse-3 (Phase 2)

- Disposition: Fixed (already present at HEAD)
- Action: `_eq_method` emits `let eq = self.inner == other_handle.inner;`, delegating to `Shared<T>::PartialEq`. Present at HEAD.
- Severity assessment: ptr_eq short-circuit correctness maintained in two places; a change to `Shared::PartialEq` would leave 37 generated `__eq__` bodies stale.

## reuse-4 (Phase 2)

- Disposition: Won't-Do
- Action: No change.
- Severity assessment: `Shared<T>` behavioral tests duplicated across two crates with no unit tests in `fltk-cst-core`.
- Rationale (Won't-Do): Moving tests into `shared.rs` requires pyo3 linkage — same blocker as `registry-unit-tests`. The two-crate duplication provides equivalent coverage from different grammar perspectives. Slight divergence (spike lacks `shared_deep_eq_distinct_allocations`) is acceptable. Deferred to `registry-unit-tests`.

## reuse-5 (Phase 2)

- Disposition: Won't-Do
- Action: No change.
- Severity assessment: `child_<lbl>` single-node and span generator branches emit structurally identical Rust code differing only in match-arm variant name.
- Rationale (Won't-Do): The two branches vary along a type-safety dimension (node vs span return type) that benefits from being explicit. The efficiency-1 fix already unified both branches to the alloc-free iterator-match pattern; remaining duplication is internal generator organization, not a correctness or behavioral risk.

## reuse-6 (Phase 2)

- Disposition: Won't-Do
- Action: No change. Same argument as reuse-5 (Phase 2).
- Severity assessment: Same structural duplication in `maybe_<lbl>` branches.

## reuse-7 (Phase 2)

- Disposition: Won't-Do
- Action: No change. Same argument as reuse-5 (Phase 2).
- Severity assessment: `children_<lbl>` iterator body duplicated across single-node and span branches.

## reuse-8 (Phase 2)

- Disposition: Fixed (superseded by efficiency-1)
- Action: The `TODO(rust-cst-accessor-clone-efficiency)` scope concern is moot: `child_<lbl>` and `maybe_<lbl>` native methods now use zero-alloc iterator match (efficiency-1 fix). No allocation to annotate.
- Severity assessment: The O(n) Vec allocation noted by reuse-8 no longer exists in native `child_<lbl>` / `maybe_<lbl>` after efficiency-1.

## quality-1 (Phase 2)

- Disposition: Fixed (same as correctness-1 Phase 2)
- Action: See correctness-1 (Phase 2). `rule_name_map` eliminated; `rule_name` passed directly.
- Severity assessment: Same as correctness-1 (Phase 2).

## quality-2 (Phase 2)

- Disposition: Fixed
- Action: Added `value_node := operand:identifier | operand:literal` to `fltk/fegen/test_data/phase4_roundtrip.fltkg` — first in-tree union-labeled rule. Regenerated `tests/rust_cst_fixture/src/cst.rs` with union accessors (`child_operand`, `maybe_operand`, `children_operand`, `append_operand`, `extend_operand`). Added 9 compiled Rust tests to `tests/rust_cst_fixture/src/native_tests.rs` covering: both Identifier and Literal variants via `child_operand`; zero/one/two-child count errors for `child_operand` and `maybe_operand`; `children_operand` yielding both variants; `append_operand` / `extend_operand` write paths. Added 7 generator-level string tests in `tests/test_gsm2tree_rs.py::TestUnionLabelNativeAccessors` verifying signatures, absence of `UnexpectedChildType` arm in union branch, `.map()` (not `filter_map`) for `children_operand`, and accept-child-enum write-side forms. Removed `TODO(union-label-native-accessor-tests)` comments from `gsm2tree_rs.py` and `TODO.md` entry.
- Severity assessment: Union-branch native accessor code was uncompiled and untested at the Rust level. A generator bug there would be undetected until a downstream grammar with a union label was processed. Now pinned by both generator-level string tests and compiled Rust tests.

## efficiency-1 (Phase 2)

- Disposition: Fixed
- Action: `fltk/fegen/gsm2tree_rs.py` `_native_per_label_methods` — replaced `let matching: Vec<_> = ...collect()` in `child_<lbl>` and `maybe_<lbl>` for single-node and span-typed label branches with the alloc-free `let mut it = ...; match (it.next(), it.next())` pattern. Recount via `filter().count()` on error path only. Regenerated all five outputs.
- Severity assessment: Every `child_<lbl>` / `maybe_<lbl>` call on the GIL-free data-struct API previously heap-allocated a `Vec` and did a full O(children) filter pass on every success. Now zero-alloc on the success path.

## efficiency-2 (Phase 2)

- Disposition: Fixed
- Action: `fltk/fegen/gsm2tree_rs.py` `_native_per_label_methods` — replaced per-item `push` loop in `extend_<lbl>` for all three label kinds (single-node, span, union) with `self.children.extend(iter.map(...))`. Regenerated all five outputs.
- Severity assessment: Per-item push incurs incremental capacity checks; `extend` pre-reserves via `size_hint`. Pure waste on the bulk-append path the future Rust parser is expected to use.

## efficiency-3 (Phase 2)

- Disposition: Fixed (same as correctness-1 Phase 2)
- Action: See correctness-1 (Phase 2). Per-call O(rules) dict rebuild eliminated.
- Severity assessment: O(rules²) generation-time work; negligible at current sizes but dead work either way.
