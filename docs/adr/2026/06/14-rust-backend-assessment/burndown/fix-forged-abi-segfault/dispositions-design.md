# Dispositions: fix-forged-abi-segfault (design review, round 1)

Reviewer notes: `notes-design-design-reviewer.md`. All six findings were fact-checked against
`crates/fltk-cst-core/src/cross_cdylib.rs`, `tests/test_rust_span.py`, the design, the exploration,
and the spec (`recommended-actions.md` / `recommended-actions-eli5.md`). All six checked out as
valid; all six are Fixed. Design edits were substantial, so the cleanup-editor pass was re-run and
three cross-section contradictions it surfaced were resolved (§3 abi3 bullet, §3 pinned-message
citation, OQ2).

---

design-1:
- Disposition: Fixed
- Action: Rewrote §4.3 ("Existing tests preserved — and the check-ordering they pin"). It now
  enumerates the full `extract_source_text` direct-call suite by file:line and pinned-message
  substring (`test_rust_span.py:308, 314, 331, 347, 363, 789, 803, 815, 827, 399`), states that
  every forged `FakeSource*` there has no `__slots__` (so basicsize 32 ≠ 24 → the new gate would
  also reject them but with a different message), and mandates that `check_abi_pair` run **before**
  the basicsize gate so the pinned messages keep firing. The ordering is also now stated in §2.B
  (ordering invariant), §2.D (implementation note), and §3 (the wrong-ABI-string edge-case bullet).
  Verified against source: the 10 cited tests exist at those lines with those classes/assertions,
  and every `FakeSource*` is a plain class body (no `__slots__`).
- Severity assessment: Without the explicit ordering, an implementer running the basicsize gate
  first flips ~6 pinned-message assertions to the basicsize message — the suite goes red at
  `make check`, or gets silently weakened, damaging the exact regression surface the fix protects.

design-2:
- Disposition: Fixed
- Action: Replaced §4.1 `test_padded_forge_still_rejected_or_documented` with
  `test_padded_forge_passes_basicsize_gate_boundary`. The revised test pins only the gate
  *boundary* (`type(forge).__basicsize__ == SourceText._fltk_cst_core_abi_layout`) and explicitly
  does **not** call `_with_source_unchecked` on the padded forge — so no UB-dependent runtime
  outcome is asserted. A test comment records that crossing the gate with this object is UB and
  out-of-contract (closure needs the per-instance token of OQ1). Updated §4.4 guarantee 3 to say
  the residual is documented as a tested *fact*, not a "pinned contract."
- Severity assessment: Asserting a UB outcome ("whatever it is") produces a test that is either
  flaky (flips on a debug/release/pyo3/allocator change with no code change) or actively lies that
  a UB input is supported — undermining the suite's credibility on the one residual being honest.

design-3:
- Disposition: Fixed
- Action: Rewrote §2.C from "in scope, low cost / removes a parallel latent hazard" to "deferred
  (no hazard to remove)." It now states the true rationale: `extract_span`'s `cast_unchecked`
  (`cross_cdylib.rs:331`) is reached only after `is_instance` against the canonical, ABI-validated
  `fltk._native.Span` (`cross_cdylib.rs:321`, `get_span_type` → `check_abi_pair::<Span>` at
  `cross_cdylib.rs:362`); `Span` is non-subclassable, so the gate adds no rejection power. Defers
  to `TODO(forged-abi-extract-span-uniformity)`. Updated §2.D (helper "could later be reused… but
  this design does not call it there") and resolved Open Question 2 accordingly.
- Severity assessment: Implementing §2.C as originally written adds a helper call to the hot
  span-read path that changes no observable behavior — speculative generality against the project's
  lean, and the design's own OQ2 already flagged it splittable. Low harm, correctly deferred.

design-4:
- Disposition: Fixed
- Action: Strengthened §2.A's access-path guidance to mandate `obj.get_type().getattr("__basicsize__")
  .extract::<usize>()` and explicitly reject `PyType_GetSlot(Py_tp_basicsize)` as a co-equal
  alternative, documenting that its `*mut c_void` return is the `Py_ssize_t` basicsize reinterpreted
  as a pointer (must be `as usize`, never dereferenced/null-checked, requires `unsafe`). Updated
  §2.D (helper reads via `getattr` "not raw `PyType_GetSlot`") and the §3 abi3-portability bullet
  (removed the "either access path is abi3-safe" co-equality that now contradicted §2.A).
- Severity assessment: If an implementer takes the `PyType_GetSlot` branch and mishandles the
  ssize-as-pointer return, the gate reads a wrong size — spuriously rejecting genuine foreign
  `SourceText` (breaks Requirements item 1) or spuriously accepting (defeats the gate). Either
  defeats the fix.

design-5:
- Disposition: Fixed
- Action: Revised §4.2. It now states the genuine-foreign end-to-end accept path is *already*
  covered by `test_with_source_unchecked_foreign_cdylib_works` (`test_rust_span.py:399`) and
  `test_source_bearing_span_reads_from_consumer_cdylib` (`test_rust_span.py:777`) — reuse, do not
  duplicate — and adds one focused new test `test_foreign_source_text_basicsize_matches_native_layout`
  that pins the gate's accept-branch precondition directly
  (`type(foreign_st).__basicsize__ == SourceText._fltk_cst_core_abi_layout`). Updated §4.4
  guarantee 2 to mention the precondition pin.
- Severity assessment: Lower severity — existing foreign-cdylib tests already cover the accept path
  end-to-end, so the requirement is not untested. But the original §4.2 duplicated coverage and
  could not distinguish "passed because basicsize matched" from "passed because the gate was
  bypassed/mis-ordered"; the focused precondition assertion closes that gap cheaply.

design-6:
- Disposition: Fixed
- Action: Expanded §2.B with an explicit "Ordering invariant (load-bearing)" paragraph: the
  basicsize gate must be evaluated before `get_or_init` (`cross_cdylib.rs:97`) and be the seeding
  precondition, so the cell can only ever hold a basicsize-validated type; the cache-hit branch
  (`cross_cdylib.rs:82-91`) is left unchanged and relies entirely on that invariant. Added a
  "Residual parity with §2.A" paragraph clarifying §2.B narrows the cache residual to the *same*
  padded-forge residual (a basicsize-24 padded forge can still seed the cell) — it does not fully
  close the cache residual. Ordering also reflected in §2.D and the SAFETY-comment update note.
- Severity assessment: If seeding ordering is implemented wrong (basicsize after `get_or_init`, or
  only inside the miss arm without gating the seed), the broader pre-fix residual returns — any
  `check_abi_pair`-passing forge can seed the cache, after which its instances hit `cast_unchecked`
  with no attribute check at all (UB). The invariant must be explicit so it cannot be subtly missed.
