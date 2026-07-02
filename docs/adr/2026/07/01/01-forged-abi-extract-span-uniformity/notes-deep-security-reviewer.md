# Security review — forged-abi-extract-span-uniformity

Reviewed: a330940..aa9a5f2 (`git diff a330940ed619771bcb4724be3e53d4f68fd8fcfe..aa9a5f27d4d307a43bfc9115857a9e52e4a384cb`)

No findings.

Verification performed (diff is itself a security hardening; checked that the gate holds and nothing new is introduced):

- `crates/fltk-cst-core/src/span.rs:287` — `Span` is `#[pyclass(frozen, eq, hash, from_py_object)]`, no `subclass` flag. The SAFETY comment's non-subclassable claim (is_instance pass ⇒ object's type IS the dual-gated reference type) holds.
- `crates/fltk-cst-core/src/cross_cdylib.rs:489-507` — both gates (`check_abi_pair`, `check_instance_layout`) run inside the `get_or_try_init` closure on the exact bound `span_type` object that is then cached; no re-lookup between validation and seeding, so no TOCTOU. A losing racer's result is discarded, so `FLTK_NATIVE_SPAN_TYPE` can only hold a closure-validated type.
- `check_instance_layout` (cross_cdylib.rs:292-339) metaclass guard reads the real `ob_type` via `ty.get_type()` and compares by pointer identity to the builtin `type` — not spoofable from Python. This also forecloses `__instancecheck__` hooks: CPython consults `__instancecheck__` on the metaclass of the reference type, which the gate pins to builtin `type`.
- All `cast_unchecked` sites on the Span path funnel through `get_span_type` + `is_instance` (`extract_span` is the only one in fltk-cst-core; generated `crates/fegen-rust/src/cst.rs` contains none directly). No bypass path found.
- Accepted residual (`__slots__`-padded forge with matching `tp_basicsize` and metaclass `type`) is explicitly documented in the SAFETY comments and matches the pre-existing accepted `extract_source_text` residual; consistent with the stated threat model (attacker who can reassign `fltk._native.Span` already runs arbitrary Python — goal is UB/segfault elimination and clear diagnostics, not privilege separation).
- `obj.__class__` reassignment onto the validated genuine `Span` type is rejected by CPython layout-compatibility rules (differing solid base for an extension type vs plain-Python class); pre-existing behavior, unchanged by this diff.
- Tests (`tests/test_rust_span.py`): subprocess helper passes a literal script string to `[sys.executable, "-c", script]` with a timeout — no command-injection or untrusted-input surface; forge tests are subprocess-isolated so a regression cannot corrupt the test runner process.
