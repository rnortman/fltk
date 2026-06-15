# Dispositions — fix-forged-abi-segfault respond round 1

Commit reviewed: 79460b6 (base d82e82f). Fixes committed at 6003626.

---

## security-1

- Disposition: Fixed
- Action: `check_instance_layout` now uses a two-step approach. Step 1: verify that
  `type(ty)` is exactly the built-in `type` (via `metaclass.is(PyType::type_object(py))`).
  A custom metaclass can define a `__basicsize__` property; the metaclass guard rejects it
  before `__basicsize__` is ever read. Step 2: after confirming the metaclass is exactly
  `type` (immutable, cannot carry a shadowing descriptor), reads `__basicsize__` via
  `ty.getattr("__basicsize__")?.extract::<usize>()` — now provably non-interceptable.
  This replaces the design's mandated `getattr`-only path, which the reviewer correctly
  showed was forgeable via a metaclass property.
  Note: the reviewer's suggested fix (`PyType_GetSlot(ty, Py_tp_basicsize)`) is not viable
  under the project's `abi3-py310` target: the `Py_tp_basicsize` slot constant is only
  defined in pyo3-ffi under `#[cfg(Py_3_15)]` (confirmed in source). The metaclass-guard
  approach achieves the same unforgeability without requiring Python 3.15.
  Files: `crates/fltk-cst-core/src/cross_cdylib.rs:274-351` (`check_instance_layout`),
  `:297-308` (metaclass guard), `:310-338` (basicsize read after guard).
  Added regression test: `tests/test_rust_span.py` `test_metaclass_property_forge_raises_type_error`.
- Severity assessment: The metaclass-property forge reached `cast_unchecked` on a bare
  16-byte `object`, reinterpreting CPython header fields as `Arc<SourceInner>` — a
  write-what-where primitive on a crafted address, more severe than the original
  padded-slots residual. This directly defeated the stated security goal of the fix.

## security-2

- Disposition: Fixed
- Action: Resolves automatically once security-1 is fixed. The metaclass guard prevents
  any metaclass-property forge from passing `check_instance_layout`, so the forged type
  never reaches `get_or_init` and cannot seed `FLTK_FOREIGN_SOURCE_TEXT_TYPE`. The
  cache invariant ("cell can only hold a basicsize-validated type") now holds.
  No code change beyond the security-1 fix; the SAFETY comment at
  `cross_cdylib.rs:101-103` accurately describes the invariant.
- Severity assessment: A seeded forged type would have given the type-confusion read
  zero-cost replay for all subsequent instances of that class for the process lifetime.
  Fixed as a consequence of security-1.

## security-3

- Disposition: Won't-Do
- Action: no change
- Severity assessment: The padded-`__slots__` residual is the design's explicitly accepted
  and documented limitation (§2.A, §2.B, design residual sections throughout). The user
  resolved Open Question 1 as "narrow now, do not record capsule option as a TODO." The
  residual is documented in SAFETY comments in cross_cdylib.rs and in the span.rs docstring.
  Closing it fully requires a per-instance unforgeable token (PyCapsule), which the design
  declined on cost/benefit grounds.
- Rationale (Won't-Do): Implementing this would reverse the user's explicit resolution of
  OQ1 ("DO NOT record the capsule option as a TODO"). The padded-forge residual is the
  documented, accepted, in-kind-equivalent to the existing `check_abi_pair` residual.
  No new hazard is introduced by leaving it; doing it would add hot-path cost and API
  surface the codebase deliberately declined.

## errhandling-1

- Disposition: Won't-Do
- Action: no change
- Severity assessment: `let _ = FLTK_FOREIGN_SOURCE_TEXT_TYPE.get_or_init(...)` is not
  swallowing a `Result`. `PyOnceLock::get_or_init` is infallible — its init closure
  cannot fail and it returns `&T`, not `Result<T, E>`. The `let _` suppresses only the
  unused-variable warning on the returned `&Py<PyType>` reference. There is no error path
  to propagate.
- Rationale (Won't-Do): Changing infallible code purely to satisfy a style concern would
  add noise. The reviewer noted this themselves ("Not a finding").

## errhandling-2

- Disposition: Fixed
- Action: Same fix as quality-1 — `check_instance_layout` now accepts `type_label: &str`
  and substitutes it into all three error messages. Call site passes `"SourceText"`.
  `crates/fltk-cst-core/src/cross_cdylib.rs:274` (signature), `:324`, `:332`, `:343` (messages).
- Severity assessment: No current misdiagnosis (only one call site exists). Future callers
  with `T = Span` would have emitted "SourceText instance layout check failed" — misleading
  diagnostics on the wrong type. Now the label is a parameter, matching `check_abi_pair`'s
  convention.

## quality-1

- Disposition: Fixed
- Action: Same as errhandling-2. `check_instance_layout<T: PyClassImpl>` signature changed
  to `check_instance_layout<T: PyClassImpl>(ty: &Bound<'_, PyType>, type_label: &str)`.
  All three format strings use `{type_label}` instead of literal `"SourceText"`.
  `crates/fltk-cst-core/src/cross_cdylib.rs:274`.
- Severity assessment: Would have caused misleading "SourceText instance layout check failed"
  messages if the helper were ever called for `Span` (the deferred §2.C path). An
  observability gap growing into a real misdiagnosis on the first future call site.

## quality-2

- Disposition: Fixed
- Action: Hoisted `_run_script` to module level in `tests/test_rust_span.py:17-25`.
  Both `TestSpanPathAbiGate._run_script` (`:499-501`) and
  `TestForgedSourceTextRejected._run_script` (`:879-881`) are one-liners delegating to it.
- Severity assessment: Two identical copies of the subprocess harness; divergence on
  future changes (timeout, env args) would produce silent differences in test behaviour
  across the two classes.

## reuse-1

- Disposition: Fixed
- Action: Same as quality-2.
- Severity assessment: Duplicate subprocess harness; any future change to invocation
  style (e.g. adding `--check` env isolation, increasing timeout) must be applied to both.

## test-1

- Disposition: Fixed
- Action: Changed `"basicsize" in msg.lower() or "layout" in msg.lower()` to
  `"__basicsize__" in msg or "not a genuine SourceText" in msg`.
  `tests/test_rust_span.py:935` (`test_forged_source_text_message_is_diagnostic`).
  These substrings appear only in `check_instance_layout` messages, not in `check_abi_pair`.
- Severity assessment: The weak disjunction passed even if `check_instance_layout` was
  absent or bypassed and `check_abi_pair` fired instead (the word "layout" appears in
  ABI-layout mismatch messages). A broken or absent basicsize gate could have gone
  undetected by this assertion.

## test-2

- Disposition: Fixed
- Action: Added `test_exotic_type_no_basicsize_raises_type_error` to
  `TestForgedSourceTextRejected` (`tests/test_rust_span.py`). Tests that the trivial
  forge (metaclass=`type`, basicsize 32≠24) raises `TypeError` (not panic/AttributeError),
  verifying the `map_err` discipline of `check_instance_layout`. Note: after the
  metaclass-guard change, the `getattr` failure branch (`__basicsize__` not readable) is
  not reachable from pure Python for any type whose metaclass IS `type` — `type.__basicsize__`
  is always defined. The test exercises the size-mismatch branch instead, which adequately
  covers the no-panic discipline.
- Severity assessment: A regression replacing `map_err` with `unwrap()` would panic/abort
  rather than raise TypeError. The test catches that regression.

## test-3

- Disposition: Fixed
- Action: Added `assert result.returncode != -11` with message
  "SIGSEGV recurrence: subprocess exited with signal 11 — forged-ABI segfault regression"
  before the `assert result.returncode == 0` in `test_forged_source_text_raises_type_error`.
  `tests/test_rust_span.py:911-914`.
- Severity assessment: Low severity. A SIGSEGV recurrence would still fail CI (returncode
  -11 ≠ 0), but the error message would be generic ("possible segfault regression") rather
  than explicit. The explicit -11 assertion makes the failure mode self-describing.

## test-4

- Disposition: Fixed
- Action: Updated `reason=` string on the `pytest.importorskip` in
  `test_foreign_source_text_basicsize_matches_native_layout` to include:
  "skipping this test means the basicsize gate's accept-branch precondition
  (foreign __basicsize__ == native layout) is unverified in this lane".
  `tests/test_rust_span.py:987-992`.
- Severity assessment: Low severity. A CI lane that always skips this test has an
  unverified precondition; the updated reason makes that gap explicit in skip output
  rather than reporting only "fixture not available."
