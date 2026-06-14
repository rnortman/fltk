# Dispositions — rust-native-lib-shape (deep review round 1)

## errhandling-1

- Disposition: TODO(native-span-init-error-context)
- Action: Added TODO comment at `fltk/fegen/gsm2lib_rs.py` in the `unknown_span_static` body-generation block; added slug to `TODO.md`.
- Severity assessment: On import failure of `fltk._native`, the Python error message gives no indication the failure was in UnknownSpan sentinel creation vs. submodule registration. On-call cannot distinguish the two cases without source inspection.
- Rationale: The reviewer's option (b) — document rather than fix — is appropriate here; the failure is OOM-level and extremely rare. A full structured wrap (option a) can be done later without blocking this change.

---

## errhandling-2

- Disposition: Fixed
- Action: Added an early validation guard in `gen_rust_lib()` (`fltk/fegen/genparser.py:452-458`) that rejects `--register-span-types` or `--unknown-span-static` without `--no-cst` with exit 1 and an explicit error message. The previously unreachable `dataclasses.replace` branch is now simply absent (the else branch only builds `LibSpec.standard()`). Three new CLI-level tests in `test_genparser.py` cover this guard and the adjacent error paths.
- Severity assessment: Without the guard, callers who accidentally passed `--register-span-types` without `--no-cst` got a silently generated file that was neither a standard grammar lib nor a runtime-only lib. The error would surface only at Rust compile time or runtime, with no indication the generator was invoked with incompatible flags.

---

## errhandling-3

- Disposition: TODO(submodule-register-fn-convention)
- Action: Added a docstring note and TODO comment in `Submodule.validate()` (`fltk/fegen/gsm2lib_rs.py:39-50`); added slug to `TODO.md`.
- Severity assessment: A caller using a non-standard `register_fn` name gets a Rust compile error rather than a Python-level validation error. Acceptable for a code generator; validation is intentionally limited to identifier syntax.

---

## reuse-1

- Disposition: TODO(rust-ident-dedup)
- Action: Added TODO comment at `fltk/fegen/gsm2lib_rs.py:15-18` near `_RUST_IDENT_RE`; added slug to `TODO.md`.
- Severity assessment: The single-segment Rust identifier pattern is hand-written in both `gsm2lib_rs.py` and `genparser.py`'s `_CST_MOD_PATH_RE`. Low risk currently; consolidation deferred until more gen-* commands need the same validation.

---

## quality-1

- Disposition: TODO(bazel-lib-rs-no-cst)
- Action: Added TODO comment at `rust.bzl:239-244` above the `_assemble_crate` genrule; added slug to `TODO.md`.
- Severity assessment: Every current `fltk_pyo3_cdylib` caller is a grammar crate that supplies both `cst.rs` and `parser.rs`. A future runtime-only crate built via this macro would hit the `test -f` guards with a misleading error. The leaky abstraction is documented; fix deferred until a concrete caller emerges.

---

## quality-2

- Disposition: Fixed
- Action: The fix for errhandling-2 eliminated the branch that needed `dataclasses.replace` entirely (the only code path that reconstructed a `LibSpec` by field copy is now replaced by an upfront rejection of the unsupported combination). The manual field-copy code is gone; no `dataclasses` import needed.
- Severity assessment: The original manual field copy was a maintenance hazard — adding a new `LibSpec` field would silently leave this copy stale. Now there is no such copy site.

---

## quality-3

- Disposition: Fixed
- Action: Removed hardcoded `fltk.` prefix from the UNKNOWN_SPAN advisory comment template in `fltk/fegen/gsm2lib_rs.py:132`. The comment now uses `{spec.module_name}.UnknownSpan` without a package prefix.
- Severity assessment: Any non-`fltk.*` module using `unknown_span_static=True` would have gotten an incorrect module path in the generated comment, misleading readers of the generated source.

---

## quality-4

- Disposition: Fixed
- Action: Added `"rlib"` to `crate-type` in `tests/rust_poc_cst/Cargo.toml:13`. Now matches the `fegen-rust` pattern (`["cdylib", "rlib"]`).
- Severity assessment: Without `rlib`, `cargo test --no-default-features` on `poc_cst` silently produces no test binary and exits zero. Any native Rust tests added to `poc_cst` in the future would appear to pass without running. This is confirmed by `make check` pre-commit hook passing with the fix.

---

## test-1

- Disposition: Fixed
- Action: Added `test_gen_rust_lib_no_cst_without_span_flags_fails` to `fltk/fegen/test_genparser.py`. Asserts exit code != 0 and no output file created.
- Severity assessment: Without this test, a future change that accidentally swallows the `ValueError` or writes a partial file before raising would go undetected at the CLI level.

---

## test-2

- Disposition: Fixed
- Action: Added `test_gen_rust_lib_unknown_span_without_register_span_types_fails` to `fltk/fegen/test_genparser.py`. Asserts exit code != 0 and no output file. Also added `test_gen_rust_lib_span_and_submodules_fails` covering the errhandling-2 guard path.
- Severity assessment: The error message translation from `ValueError` to exit 1 + stderr + no-file-written was exercised only at the unit level, not the CLI level.

---

## test-3

- Disposition: Fixed
- Action: Added `test_old_native_poc_cst_path_absent_from_sys_modules` and `test_old_native_fegen_cst_path_absent_from_sys_modules` to `TestNativeRuntimeOnly` in `tests/test_module_split.py`.
- Severity assessment: A stale or partially-rebuilt `.so` that still exports the old submodules could set `sys.modules["fltk._native.poc_cst"]` without the `hasattr` assertions catching it. The new assertions are a backstop against this.

---

## test-4

- Disposition: Fixed
- Action: Added three tests for `register_span_types=True, unknown_span_static=False` via a `_span_types_no_unknown_span_spec()` helper in `fltk/fegen/test_gsm2lib_rs.py`: span module and class registrations present; UNKNOWN_SPAN/PyOnceLock absent; submodule registration coexists.
- Severity assessment: The conditional-emission path for span types without UNKNOWN_SPAN was entirely untested. A bug in the conditional logic (e.g., emitting UNKNOWN_SPAN when `unknown_span_static=False`) would not be caught.

---

## test-5

- Disposition: Won't-Do
- Action: No change to `TestAC8PyRustCross.test_crates_are_distinct_python_types`.
- Severity assessment: The reviewer correctly notes the assertion is vacuously true (py and rust will always have distinct Python types). However, removing the test eliminates a stated sanity check without replacing it. The test name and docstring accurately describe what it asserts; it is harmless.
- Rationale (Won't-Do): The test documents a design property (the two backends expose distinct Python types) even if that property cannot currently be false. The original AC8 cross-crate property (two Rust cdylibs producing equal-but-distinct types) is gone with the `emb` backend; this test is the successor that covers what remains. Deleting it would leave AC8 entirely unasserted. The reviewer's proposed resolution ("remove it and document AC8 is gone") is less informative than keeping the sanity check with its current docstring.
