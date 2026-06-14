# Dispositions — deep review round 1 (commit 63493a8)

Style note: concise, precise, complete, unambiguous; audience is smart LLM/human.

---

errhandling-1:
- Disposition: Fixed
- Action: Updated two doc-comment occurrences in span.rs: line 380 `GILOnceCell` → `PyOnceLock`; line 565 `GILOnceCell` → `PyOnceLock`. (Also fixed span.rs:382 `downcast_unchecked` → `cast_unchecked` found alongside, per test-2/quality-1 co-location.)
- Severity assessment: No runtime impact; stale names mislead on-call readers tracing ABI failure paths through source.

errhandling-2:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: Reviewer confirmed no finding — noted for reviewer clarity only.
- Rationale (Won't-Do): Reviewer explicitly marked verdict "No finding."

errhandling-3:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: Reviewer confirmed no finding — pattern is intentional.
- Rationale (Won't-Do): Reviewer explicitly marked verdict "No finding."

errhandling-4:
- Disposition: Fixed
- Action: registry.rs:121-125 — replaced `.expect("registry invariant violated...")` with `ok_or_else(|| PyRuntimeError::new_err(...))`. Converts unreachable invariant violation from panic to catchable Python RuntimeError.
- Severity assessment: Pre-existing; not introduced by this diff. Panic under free-threaded Python (PEP 703) or pathological GC timing would give `PanicException` rather than structured `PyErr`, making callers unable to catch it normally.

correctness-1:
- Disposition: Fixed (arbitrated by user; previously TODO(abi-probe-cargo-test))
- Action: Makefile — added `cargo-test-python-features` target (line ~53) that runs
  `cargo test -q -p fltk-cst-core --features python` with
  `PYO3_PYTHON=$(uv python find --managed-python --no-project 3.10)`; added target to
  `make check` step list; removed TODO comment from `cargo-test` and removed
  `abi-probe-cargo-test` entry from TODO.md. The 4 abi_probe_tests now run in the gate.
- Severity assessment: Gate now executes the abi_probe_tests module (42 tests total, 4 in
  abi_probe_tests). Stub regression in either classattr body will fail `make check`.

correctness-2:
- Disposition: Fixed
- Action: Extracted `span_abi_layout_probe()` and `source_text_abi_layout_probe()` as `pub(crate)` free functions in span.rs; classattr bodies delegate to them; lib.rs test module imports both and adds `span_probe_matches_classattr_body` and `source_text_probe_matches_classattr_body` assertions alongside the existing floor checks. A hardcoded constant in either classattr body now fails the test.
- Severity assessment: Without this fix, replacing either classattr body with a hardcoded constant passes the existing tests, eliminating the probe's only regression guard.

correctness-3:
- Disposition: Fixed
- Action: test_gsm2tree_rs.py:321 — added `assert "span: Py<PyAny>," not in poc_source` alongside the existing `PyObject` assertion in `test_span_field_native`. test_gsm2tree_rs.py:925 — same addition in `TestNoPyObjectAudit.test_no_pyobject_span_field`.
- Severity assessment: Both negative assertions were vacuous after class-B migration (PyObject can no longer appear in generator output); a future change reintroducing a Python-typed span field would silently pass the audit test.

test-1:
- Disposition: Fixed
- Action: tests/test_rust_span.py:470-478 — replaced all three `GILOnceCell` occurrences with `PyOnceLock` in `TestSpanPathAbiGate` class docstring.
- Severity assessment: Cosmetic; stale type name in test docstring misleads readers cross-referencing test premise against implementation.

test-2:
- Disposition: Fixed
- Action: span.rs:382 `downcast_unchecked` → `cast_unchecked`; cross_cdylib.rs:33 `downcast` → `cast` (in cell-comment); cross_cdylib.rs:247 `PyObject` → `Py<PyAny>` (in span_to_pyobject doc). cross_cdylib.rs:383 "before any unchecked downcast" left unchanged — uses "downcast" as a verb (conceptual type-cast direction), not the removed pyo3 API name.
- Severity assessment: Stale API names in doc comments make cross-referencing code vs pyo3 docs harder than necessary.

test-3:
- Disposition: Fixed
- Action: fltk/fegen/test_genparser.py:75 — `GILOnceCell` → `PyOnceLock` in `test_gen_rust_cst_sentinel_decoupled` docstring.
- Severity assessment: Cosmetic; stale type name in test docstring.

test-4:
- Disposition: Fixed
- Action: tests/test_rust_span.py — added `import ctypes` at top; added `assert layout >= ctypes.sizeof(ctypes.py_object)` to both `test_span_abi_layout_is_positive_int` and `test_source_text_abi_layout_is_positive_int`. This rules out stub constants ≤ 8 (sizeof PyObject on 64-bit) at the Python test level, exercising the running binary.
- Severity assessment: Without the floor check, a probe-disabled variant returning `1` passes the Python tests; the Rust-level guard only runs when `cargo test -p fltk-cst-core --features python` is explicitly invoked (blocked by correctness-1).

quality-1:
- Disposition: Fixed
- Action: Same fix as errhandling-1 (same two sites in span.rs).
- Severity assessment: Duplicate of errhandling-1; resolved together.

quality-2:
- Disposition: Fixed
- Action: Same fix as test-1 (TestSpanPathAbiGate docstring).
- Severity assessment: Duplicate of test-1; resolved together.

quality-3:
- Disposition: Fixed
- Action: Same fix as test-3 (test_genparser.py:75).
- Severity assessment: Duplicate of test-3; resolved together.
