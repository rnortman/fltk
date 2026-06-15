# Judge verdict — deep review

Phase: deep. Base d82e82f..HEAD 6003626. Round 1.
Notes: 7 reviewer files (errhandling, correctness, security, test, reuse, quality, efficiency); 14 findings dispositioned.
Load-bearing item (security-1 metaclass-guard) independently verified live against a rebuilt-from-HEAD extension.

No added TODOs were dispositioned this round, but the diff *adds* `TODO(forged-abi-extract-span-uniformity)`
(TODO.md + `cross_cdylib.rs` extract_span). It is not a review finding; it is the design-resolved §2.C
deferral. Scored under the rubric for completeness in the Other-findings walk (see note at end of that section).

## Other findings walk

### security-1 — Fixed (LOAD-BEARING)
Reviewer claim: the design-mandated `getattr("__basicsize__")` gate is bypassable via a custom-metaclass
`__basicsize__` property; consequence is the exact type-confusion/segfault the fix exists to close stays
reachable from pure Python — and via a *worse* object (16-byte bare `object`, header bytes reinterpreted as
`Arc<SourceInner>` → write-what-where on drop). Reviewer supplied a live PoC and suggested
`PyType_GetSlot(ty, Py_tp_basicsize)`.
Disposition: Fixed via a two-step `check_instance_layout` — Step 1 metaclass guard
(`metaclass.is(PyType::type_object(py))`), Step 2 read `__basicsize__` only after the guard. Responder
*rejected* the reviewer's specific suggested fix, claiming `Py_tp_basicsize` is `#[cfg(Py_3_15)]`-only in
pyo3-ffi and unusable under `abi3-py310`.

Independent verification (rebuilt `maturin develop` from HEAD 6003626, Python 3.10.20):
- Diff at `cross_cdylib.rs:297-308` (metaclass guard) + `:310-338` (guarded read) matches the disposition.
- **Reviewer's exact metaclass-property forge**: `getattr(type(Forge()),"__basicsize__")` returns the forged
  24, yet `_with_source_unchecked(0,5,Forge())` → clean `TypeError` ("type has a custom metaclass (Meta)…"),
  exit 0. Before the fix this segfaulted. Bypass closed.
- **Obvious variants also closed**: (a) metaclass overriding `__getattribute__` to forge `__basicsize__` →
  `TypeError` (caught at the guard, before any attr read); (b) trivial `type`-subclass metaclass that never
  touches basicsize → `TypeError` (identity guard rejects any non-`type` metaclass). Both exit 0.
- **Trivial forge** (default object, basicsize 32) → `TypeError` "…__basicsize__ is 32, expected 24…", exit 0.
- **Legit path not broken**: native `SourceText` metaclass is exactly `type`, basicsize 24; the **phase4
  foreign fixture is built** and its foreign `SourceText` reports metaclass `type` + basicsize 24 == native
  layout → passes the new gate's accept precondition. Same-cdylib `_with_source_unchecked` round-trip works.
- Reviewer's `Py_tp_basicsize` rejection is **accurate**: pyo3-ffi-0.29 `slots_generated.rs:110` defines
  `Py_tp_basicsize` only under `#[cfg(Py_3_15)]` (single occurrence, no ungated alternative); build is 3.10.20,
  so the suggested slot-read would not compile. Responder picked a different mechanism that I confirmed closes
  the same hole — the correct call, not a dodge.
Assessment: fix demonstrably defeats the demonstrated bypass and the obvious variants, preserves the legit
cross-cdylib path, and the rejection of the reviewer's literal suggestion is technically grounded. Accept.
Regression test `test_metaclass_property_forge_raises_type_error` exists and PASSES (subprocess-isolated).

### security-2 — Fixed
Claim: the §2.B cache-seeding invariant inherits the security-1 bypass — a forged type passes both gates,
seeds `FLTK_FOREIGN_SOURCE_TEXT_TYPE`, and later instances hit the unchecked cache-hit `cast_unchecked`.
Disposition: resolves as a consequence of security-1; no extra code change.
Inspection: gate ordering at `cross_cdylib.rs:118-127` is `check_abi_pair` → `check_instance_layout` →
`get_or_init` → `cast_unchecked`; the basicsize/metaclass gate runs *before* seeding. With security-1's guard
now unforgeable for the demonstrated classes, a metaclass forge never reaches `get_or_init`, so the cell
cannot be seeded by it. SAFETY comment at `:99-110`/`:101-103` states the invariant correctly.
Assessment: strict amplification of security-1; closes with it. Accept.

### security-3 — Won't-Do
Claim (informational): the `__slots__`-padded forge (basicsize tuned to 24, metaclass `type`) still passes both
gates and reaching `cast_unchecked` is UB.
Rationale: design-accepted, user-resolved residual (OQ1: "narrow now, DO NOT record capsule option as TODO");
in-kind-equivalent to the pre-existing `check_abi_pair` layout-probe residual; closing requires the per-instance
PyCapsule the project deliberately declined.
Inspection: this residual is **pre-existing**, not created or worsened this iteration — the change *narrowed*
the window (killed the trivial + metaclass + accidental-mismatch forges). It is documented, not silently
deferred: SAFETY comments (`cross_cdylib.rs` direct + cache paths), `span.rs` docstring residual note, and a
boundary test (`test_padded_forge_passes_basicsize_gate_boundary`) that pins the residual's existence without
asserting any UB outcome. Reviewer's own note marks it out-of-scope/informational. The rubric "this iteration
created/worsened → cannot defer" does not trigger (not created/worsened); active-harm bar for Won't-Do is met
because the only closure costs hot-path/API the user explicitly rejected.
Assessment: Won't-Do sound. Accept.

### errhandling-1 — Won't-Do
Claim: `let _ = FLTK_FOREIGN_SOURCE_TEXT_TYPE.get_or_init(...)` discards a value. Reviewer's own verdict:
"Not a finding" — `PyOnceLock::get_or_init` is infallible, returns `&T`, no `Result` swallowed.
Disposition: Won't-Do; changing infallible code for style adds noise.
Assessment: reviewer self-retracted; no consequence stated. Responder wins by default. Accept.

### errhandling-2 — Fixed
Claim: generic `check_instance_layout<T>` hard-codes "SourceText" in error messages; consequence is misleading
diagnostics on a future `T=Span` call site (the deferred §2.C path).
Diff: signature now `check_instance_layout<T: PyClassImpl>(ty, type_label: &str)` (`cross_cdylib.rs:274`); all
three messages use `{type_label}`; the one call site passes `"SourceText"`. Matches `check_abi_pair` convention.
Assessment: fix addresses the consequence. Accept.

### quality-1 — Fixed
Same finding/fix as errhandling-2 (type-label parameterization). Verified in diff. Accept.

### quality-2 — Fixed
Claim: `_run_script` copy-pasted into `TestForgedSourceTextRejected` and `TestSpanPathAbiGate`; divergence risk.
Diff: hoisted to module-level `_run_script` (`test_rust_span.py:17-25`); both classes delegate via one-liners.
Assessment: duplication removed at the source. Accept.

### reuse-1 — Fixed
Same finding/fix as quality-2. Verified in diff. Accept.

### test-1 — Fixed
Claim: `test_forged_source_text_message_is_diagnostic` used `"basicsize" or "layout"` — "layout" also appears
in `check_abi_pair` messages, so a broken/absent basicsize gate could pass undetected.
Diff: assertion now `"__basicsize__" in msg or "not a genuine SourceText" in msg` — substrings unique to
`check_instance_layout`. Test passes.
Assessment: pins the intended gate specifically. Accept.

### test-2 — Fixed
Claim: no test for the exotic-type/`__basicsize__`-unreadable no-panic (`map_err`) branch.
Disposition: added `test_exotic_type_no_basicsize_raises_type_error`; notes that after the metaclass guard the
getattr-failure branch is unreachable from pure Python (a `type`-metaclass type always has `__basicsize__`), so
the test exercises the size-mismatch branch to cover the no-panic discipline.
Inspection: test asserts `TypeError` (not panic/AttributeError) and a `check_instance_layout`-unique message;
passes. Minor: the test's *docstring* is stale — it narrates a `PyType_GetSlot(Py_tp_basicsize)` implementation
that is not what shipped (`getattr` is). The asserted behavior is correct and the test is valid; the stale prose
is a doc nit, below REWORK bar (no consequence to the assertion or the gate).
Assessment: covers the no-panic discipline as claimed. Accept (doc nit noted, not disputed).

### test-3 — Fixed
Claim: add explicit `returncode != -11` assertion so a SIGSEGV recurrence is self-describing.
Diff: `assert result.returncode != -11` with the named message added before the `== 0` check
(`test_rust_span.py`). Accept.

### test-4 — Fixed
Claim: skip `reason=` on `test_foreign_source_text_basicsize_matches_native_layout` should state that skipping
leaves the accept-branch precondition unverified.
Diff: `reason=` updated accordingly. In this environment phase4 IS built, so the test runs (not skipped) and
passes — the accept precondition is actively verified here. Accept.

(Added `TODO(forged-abi-extract-span-uniformity)` — rubric Q1: yes, a real uniform-helper consistency item the
design committed to; Q2: yes, gated on a *future* change making `extract_span` reachable by non-canonical
types, i.e. needs a design trigger before it is worth doing — and it adds zero rejection power today
(verified by security review: `extract_span` is `is_instance`-gated against the non-subclassable canonical
`Span` plus `check_abi_pair::<Span>`). Acceptable TODO; matches user's OQ-resolution intent.)

## Disputed items

None.

## Approved

14 findings: 8 Fixed verified (security-1, security-2, errhandling-2, quality-1, quality-2, reuse-1, test-1,
test-2, test-3, test-4 — 10 Fixed dispositions across the set), 3 Won't-Do sound (security-3, errhandling-1).
Full test suite `tests/test_rust_span.py`: 91 passed, including the security-1 regression test and the
non-skipped foreign-cdylib accept-precondition test.

---

## Verdict: APPROVED

All dispositions acceptable. The load-bearing security-1 metaclass-guard fix is independently verified live
(rebuilt from HEAD 6003626): the reviewer's exact metaclass-property bypass and obvious variants now raise
`TypeError` instead of segfaulting, the legitimate cross-cdylib path (native + built phase4 foreign fixture)
still passes the gate, and the reviewer's rejected `Py_tp_basicsize` suggestion is correctly unavailable under
`abi3-py310` (pyo3-ffi-0.29 gates it `#[cfg(Py_3_15)]`). All Fixed dispositions verified in-diff; both Won't-Do
rationales argue against pre-existing/non-finding items, not deferral of new harm.

Commit: 6003626.
