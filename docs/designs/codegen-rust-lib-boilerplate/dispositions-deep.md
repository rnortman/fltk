# Dispositions — codegen-rust-lib-boilerplate deep review

Round 1. fltk HEAD after fixes: 8fd4059. clockwork: no changes (ea34388).

---

## errhandling-1

- Disposition: Fixed
- Action: Removed `_RUST_IDENT_RE` from `genparser.py:400` and the pre-validation block in `gen_rust_lib`. The `ValueError` raised by `RustLibGenerator(spec)` via `spec.validate()` is now the single validation path, caught at the existing `except ValueError` in both CLI commands (`genparser.py:439-443`, `genparser.py:468-472`). One definition of `_RUST_IDENT_RE` now lives only in `gsm2lib_rs.py:16`.
- Severity assessment: Two independent copies of the same regex could silently diverge if the identifier rule changes, producing inconsistent CLI vs. library validation. Eliminated by removing the CLI copy.

---

## errhandling-2

- Disposition: Fixed
- Action: In both `gen_rust_lib` and `gen_rust_native_lib`, changed `src = gsm2lib_rs.RustLibGenerator(spec).generate()` to `gen = gsm2lib_rs.RustLibGenerator(spec); src = gen.generate()`, with both statements inside the `try` block (`genparser.py:438-443`, `genparser.py:467-472`). Constructor-side `ValueError` from `spec.validate()` is now caught alongside generator-side errors.
- Severity assessment: Not currently reachable via any CLI path, but would produce an unformatted traceback rather than a clean error message if a future caller constructs a bad spec. Now both construction and generation are guarded.

---

## errhandling-3

- Disposition: Fixed
- Action: Added validation in `LibSpec.validate()` (`gsm2lib_rs.py:84-87`): if `submodules` is empty and neither `register_span_types` nor `unknown_span_static` is set, raises `ValueError("LibSpec.submodules must not be empty when no span types or UNKNOWN_SPAN are registered")`. Added test `test_empty_submodules_raises_value_error` in `test_gsm2lib_rs.py`.
- Severity assessment: Without this, `LibSpec(module_name="x", submodules=())` silently generates a `#[pymodule]` that registers nothing, producing a useless but compilable crate with no diagnostic at generation time.

---

## errhandling-4

- Disposition: TODO(bazel-lib-rs-location)
- Action: TODO comment added: `# TODO(bazel-lib-rs-location): $(location :name_gen_lib) expands correctly while the genrule has exactly one out; if outs ever grows, use $(location gen_lib_rs_out) directly` at `rust.bzl:218`. Changing `lib_rs` from the target label `":" + name + "_gen_lib"` to the plain file path `gen_lib_rs_out` in the Bazel `srcs` list would break the dependency chain — Bazel would not know to build the `_gen_lib` genrule first. The quoting fix (security-1) is applied; this latent concern is deferred.
- Severity assessment: Not a current failure mode; the `_gen_lib` genrule has exactly one `outs` entry. If it ever grew additional outputs, `$(location :target)` would fail with an ambiguous expansion error. Low priority.

---

## errhandling-5

- Disposition: Won't-Do
- Action: No change. The finding itself states this is already acknowledged and tracked.
- Severity assessment: The TODO(native-submodule-error-context) is tracked in TODO.md and at the correct location in `fltk_cst_core`. No additional action needed.
- Rationale (Won't-Do): The finding explicitly says "already acknowledged as TODO(native-submodule-error-context) in the diff and tracked in TODO.md. No change needed; noting here for completeness."

---

## test-1

- Disposition: Fixed
- Action: Added `assert "''" in result.output` to `test_gen_rust_lib_invalid_module_name_empty` and added `assert not output_rs.exists()` + `assert "has space" in result.output` to `test_gen_rust_lib_invalid_module_name_has_space` (`test_genparser.py:401-403`, `test_genparser.py:422-424`). Verified that the new error message format (from the generator's `ValueError`: `"Invalid Rust identifier for module_name: '...'"`) includes the offending value in all cases.
- Severity assessment: Without these assertions, a regression where the CLI exits 1 silently (no message naming the offending value) would not be caught.

---

## test-2

- Disposition: Fixed
- Action: Added `test_gen_rust_lib_missing_module_name` to `test_genparser.py:437-444` that invokes `gen-rust-lib` without `--module-name` and asserts `exit_code != 0`. Verified that typer gives exit code 2 with a clear "Missing option '--module-name'" message.
- Severity assessment: Without this test, accidentally giving `--module-name` a default would not be caught. The omission case is a distinct code path from empty-string and is now covered.

---

## test-3

- Disposition: Fixed
- Action: Removed `cfg_python_gate: bool = False` field from `LibSpec` entirely (`gsm2lib_rs.py:62-63`). The field was never read in `generate()`. Removing it rather than adding a `NotImplementedError` guard avoids a public API footgun where callers set the field expecting behavior that never materializes.
- Severity assessment: A dead field on a public frozen dataclass is a silent API trap. Downstream callers setting `cfg_python_gate=True` would get standard output with no gating and no diagnostic. Removing it eliminates the trap; the field can be added with a real implementation when actually needed.

---

## test-4

- Disposition: Fixed
- Action: Added `test_native_spec_declaration_and_registration_order` to `test_gsm2lib_rs.py:192-202` that asserts `src.index("mod cst_generated;") < src.index("mod cst_fegen;")` and `src.index('"poc_cst"') < src.index('"fegen_cst"')`.
- Severity assessment: Without ordering tests, a transposition of mod declarations or registration calls would leave all presence-check tests passing while changing observable init order. Order is load-bearing if any consumer depends on registration sequence.

---

## reuse-1

- Disposition: Fixed
- Action: Same fix as errhandling-1. The `_RUST_IDENT_RE` in `genparser.py` is removed; the single authoritative copy is `gsm2lib_rs._RUST_IDENT_RE`.
- Severity assessment: Duplicate regex constants with identical patterns must be kept in sync; a divergence would produce inconsistent CLI vs. library behavior with no diagnostic.

---

## quality-1

- Disposition: Fixed
- Action: Same fix as errhandling-1/reuse-1.
- Severity assessment: Same as reuse-1.

---

## quality-2

- Disposition: Fixed
- Action: Same fix as test-3. `cfg_python_gate` removed from `LibSpec`.
- Severity assessment: Same as test-3.

---

## quality-3

- Disposition: Won't-Do
- Action: No change to the `--module-name` option declaration. The reviewer's concern about a `TypeError` when `--module-name` is omitted is incorrect — typer rejects it before entering the function body with exit code 2 and a clear "Missing option '--module-name'" message. Verified by running the CLI. The new `test_gen_rust_lib_missing_module_name` test (test-2) covers this case.
- Severity assessment: The `TypeError` scenario described does not occur in practice. Typer handles missing required options at its own parse layer. No code change needed; the test (added for test-2) provides coverage.
- Rationale (Won't-Do): The reviewer's premise ("If typer allows the call to proceed with `module_name = None`, the guard `if not module_name` passes but `_RUST_IDENT_RE.match(None)` raises `TypeError`") is invalidated by removing the pre-guard entirely. The CLI now delegates fully to the generator's `ValueError`, which is caught cleanly. And in any case, typer catches missing required options before the function body executes.

---

## security-1

- Disposition: Fixed
- Action: Changed `--module-name {module_name}` to `--module-name '{module_name}'` in the Bazel genrule `cmd` string at `rust.bzl:213`. The target name is now shell-quoted, so any shell-significant characters in it (however unlikely given Bazel's name grammar) are not expanded by the shell before the Python validator sees them.
- Severity assessment: The actual attack surface is minimal (the actor is the build author; Bazel target-name rules disallow most metacharacters), but the code read as "validated" when the validation ran after the shell boundary. The fix puts the guard on the correct side.

---

## security-2

- Disposition: Won't-Do
- Action: No change.
- Severity assessment: Validation is already in place and mandatory (`RustLibGenerator.__init__` calls `spec.validate()`). The finding explicitly states "currently safe" and "no fix required."
- Rationale (Won't-Do): The finding itself recommends no fix and notes the validation is correct as-is.

---

## security-3

- Disposition: Won't-Do
- Action: No change.
- Severity assessment: Output path traversal is acceptable for a developer codegen CLI where the caller is the build author.
- Rationale (Won't-Do): The finding itself states "no fix required" and "acceptable for a developer codegen CLI."
