# Implementation Log: fix-forged-abi-segfault

## Increment 1 — tp_basicsize gate in extract_source_text + regression tests (commit 67cc04e)

- `crates/fltk-cst-core/src/cross_cdylib.rs:1-7`: added `use pyo3::impl_::pyclass::PyClassImpl;` import.
- `crates/fltk-cst-core/src/cross_cdylib.rs:257-299` (new `check_instance_layout` helper):
  generic `fn check_instance_layout<T: PyClassImpl>(ty: &Bound<'_, PyType>) -> PyResult<()>`;
  reads `ty.getattr("__basicsize__")?.extract::<usize>()` (mandated `getattr` path, not raw
  `PyType_GetSlot`); compares against `size_of::<<T as PyClassImpl>::Layout>()`; returns a
  diagnostic `TypeError` on mismatch or read failure.
- `crates/fltk-cst-core/src/cross_cdylib.rs:63-160` (`extract_source_text` doc + body):
  expanded module-level SAFETY contract doc; slow-path cache-miss now runs `check_abi_pair`
  first (preserving pinned ABI/layout message ordering), then `check_instance_layout`, and
  only on both passing calls `get_or_init` (seeding the cache) then `cast_unchecked`.
  Cache-hit branch (pointer identity) unchanged — invariant noted: cell can only hold a
  basicsize-validated type.  SAFETY comment at `cast_unchecked` updated to reflect both gates
  and the narrowed (not closed) padded-forge residual.
- `crates/fltk-cst-core/src/span.rs:433-459` (`_with_source_unchecked` docstring):
  updated to state the method now raises `TypeError` (not silent UB) for a pure-Python
  forged-marker object; documented the two-gate flow and the padded-forge residual.
- `tests/test_rust_span.py` (new `TestForgedSourceTextRejected` class, 4 tests):
  - `test_forged_source_text_raises_type_error`: subprocess runs §1.1 Forge script; asserts
    returncode 0 and "OK" in stdout (was segfault / returncode -11 before fix).
  - `test_forged_source_text_message_is_diagnostic`: in-process; asserts TypeError message
    mentions "basicsize" or "layout" so a gate-bypass regression is caught.
  - `test_padded_forge_passes_basicsize_gate_boundary`: pins the known residual — asserts
    `type(PaddedForge()).__basicsize__ == native_layout` (gate cannot distinguish it);
    does NOT call `_with_source_unchecked` on the padded forge (that is UB, not contracted).
  - `test_foreign_source_text_basicsize_matches_native_layout`: skip-guarded on
    `phase4_roundtrip_cst`; asserts `type(foreign_st).__basicsize__ == native_layout` (pins
    the accept-branch precondition of the gate directly).
- All 89 existing `test_rust_span.py` tests continue to pass; full suite 1895 passed.
