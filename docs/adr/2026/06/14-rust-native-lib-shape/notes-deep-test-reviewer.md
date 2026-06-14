## Test review — 14-rust-native-lib-shape

Commit reviewed: 7a7ca4d

---

**test-1**

File: `fltk/fegen/test_genparser.py` (gen-rust-lib CLI section)

Missing coverage: `--no-cst` without `--register-span-types` is an invalid invocation (produces an empty-submodule, zero-span spec that `LibSpec.validate()` rejects as "submodules must not be empty"). No test exercises this path at the CLI level to confirm the error is surfaced, exit code is 1, and no output file is written. The analogous unit-level case is covered in `test_gsm2lib_rs.py:test_empty_submodules_raises_value_error`, but the CLI handler's error-routing path for this case is untested.

Consequence: if a future change to `gen_rust_lib()` accidentally swallows the `ValueError` or writes a partial file before raising, no test catches it.

Fix: add `test_gen_rust_lib_no_cst_without_span_flags_fails` — invoke with `["gen-rust-lib", str(output_rs), "--module-name", "_native", "--no-cst"]`, assert `exit_code != 0`, assert output file not written.

---

**test-2**

File: `fltk/fegen/test_genparser.py` (gen-rust-lib CLI section)

Missing coverage: `--unknown-span-static` without `--register-span-types` (valid per CLI — both are optional boolean flags — but invalid per `LibSpec.validate()`). No CLI-level test exercises this error path.

Consequence: the error message that fires (`register_span_types` must be True) is tested in `test_gsm2lib_rs.py:test_unknown_span_static_without_register_span_types_raises_value_error`, but the CLI handler's translation of that `ValueError` to exit 1 + stderr + no-file-written is untested.

Fix: add `test_gen_rust_lib_unknown_span_without_register_span_types_fails` — invoke with `["gen-rust-lib", str(output_rs), "--module-name", "_native", "--no-cst", "--unknown-span-static"]`, assert `exit_code != 0`, assert no output file.

---

**test-3**

File: `tests/test_module_split.py`, `TestNativeRuntimeOnly`

Absence behavior is checked by name (no `poc_cst`, no `fegen_cst`, no `Identifier`, no `Items`), but the old submodule paths `"fltk._native.poc_cst"` and `"fltk._native.fegen_cst"` are not asserted absent from `sys.modules`. After the refactor these should never appear in `sys.modules`. The old tests previously asserted their *presence*; the replacement tests drop that direction entirely rather than flipping it.

Consequence: a stale or partially-rebuilt `.so` that still exports the submodules would not be caught by this test class — the absence assertions on `hasattr(fltk_native, "poc_cst")` etc. pass, but `sys.modules["fltk._native.poc_cst"]` could still be set from a prior import in the same session.

Fix: add two assertions in `TestNativeRuntimeOnly`:
```python
assert "fltk._native.poc_cst" not in sys.modules
assert "fltk._native.fegen_cst" not in sys.modules
```

---

**test-4**

File: `fltk/fegen/test_gsm2lib_rs.py`

The `register_span_types=True, unknown_span_static=False` combination (span type registration without UNKNOWN_SPAN static) is a valid `LibSpec` that `validate()` accepts — but no test exercises it. The generator has a distinct code path: it emits `mod span;` + `use span::{...};` + `m.add_class::<Span>()` + `m.add_class::<SourceText>()` without the `PyOnceLock` use declaration, the `UNKNOWN_SPAN` static, or the `m.add("UnknownSpan", ...)` call. The current tests only exercise the all-on combination via `_span_only_spec()`.

Consequence: if someone adds span registration to a standard extension (cst + parser) the code path is fully untested; a bug in the conditional-emission logic (e.g. emitting `UNKNOWN_SPAN` even when `unknown_span_static=False`) would not be caught.

Fix: add a test for `LibSpec(module_name="my_ext", submodules=(Submodule("cst","cst"),), register_span_types=True, unknown_span_static=False)` that asserts `mod span;` present, `m.add_class::<Span>()` present, `UNKNOWN_SPAN` absent, `PyOnceLock` absent, and `register_submodule` still present (it coexists with span types when submodules are non-empty).

---

**test-5**

File: `tests/test_cross_backend_label_equality.py`, `TestAC8PyRustCross`

The class was renamed from `TestAC8TwoRustCrates` and repurposed to test `py↔ext` distinctness. The renamed `test_crates_are_distinct_python_types` now asserts `type(py_cst.Items.Label.NO_WS) is not type(fegen_rust_cst.cst.Items.Label.NO_WS)` — this is now trivially true because the two types come from entirely different implementations (Python dataclass vs Rust cdylib), not the interesting case the original AC8 was designed to catch (two *Rust cdylibs* exposing the same Pyo3 class name). The test name still says "distinct Python types" but the scenario being validated has changed in a way that makes it vacuous: py and rust will *always* have distinct Python types, so the assert can never fail.

Consequence: the cross-crate-equality property (two distinct cdylibs whose Label types still compare equal via the canonical-name protocol) is now exercised only implicitly by the parametrized `TestLabelCrossBackend` class (which now has only the `("py","ext")` pair). The specific structural claim "two separate Rust crate instances produce equal-but-distinct types" is no longer tested at all after removal of the `emb` backend.

Fix: either remove `TestAC8PyRustCross.test_crates_are_distinct_python_types` (it tests a fact that cannot be false) and document that AC8 cross-crate property is gone with the `emb` backend, or rename and refocus the test to assert the useful direction: `type(fegen_rust_cst.cst.Items.Label.NO_WS) is not type(py_cst.Items.Label.NO_WS)` with a comment explaining it's a type-distinctness sanity check, not the original AC8 claim.
