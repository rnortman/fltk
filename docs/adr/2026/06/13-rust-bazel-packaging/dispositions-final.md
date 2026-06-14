# Dispositions — final review round

## correctness-1
- Disposition: Fixed
- Action: Removed `use pyo3::PyTypeInfo;` from the generated cst.rs preamble (gsm2tree_rs.py:497–501). Changed the single call site (`_label_classattr`) to use fully-qualified UFCS: `<{enum_name} as pyo3::PyTypeInfo>::type_object(py)` (gsm2tree_rs.py:~1290). Regenerated all fixture files (`tests/rust_cst_fixture/src/cst.rs`, `tests/rust_cst_fegen/src/cst.rs`, `tests/rust_parser_fixture/src/cst.rs`, `src/cst_generated.rs`, `src/cst_fegen.rs`). Updated `TestPreamble.test_required_use_declarations` to assert the import is absent. Added `test_type_info_rule_accepted` confirming `type_info` is now a legal rule name.
- Severity assessment: A grammar rule named `type_info` would have generated `pub struct PyTypeInfo` colliding with the `use pyo3::PyTypeInfo;` trait import in the preamble, producing a rustc E0255 compile error in the consumer's generated cst.rs. This is a silent mis-compile for an out-of-tree consumer — exactly the class of bug the reserved-name backstop was designed to prevent.

## errhandling-1
- Disposition: Fixed
- Action: Added a parallel `_bad_reserved_seeded` list comprehension (gsm2tree_rs.py:~133–142) that checks `_RESERVED_CLASS_NAMES_SEEDED` for entries ending with "Child" or "Label", raising `RuntimeError` at module load if any are found.
- Severity assessment: Without this guard, a future maintainer who accidentally added a `Child`- or `Label`-suffixed entry to `_RESERVED_CLASS_NAMES_SEEDED` would get no diagnostic at module load; the seeded entry would silently block grammars with no clear error pointing at the seeded dict as the source.

## errhandling-2
- Disposition: Fixed
- Action: Added `test -f $$OUTDIR/cst.rs || { echo "ERROR: ..."; exit 1; }` and `test -f $$OUTDIR/parser.rs || { echo "ERROR: ..."; exit 1; }` assertions after the copy loop in the `_assemble_crate` genrule shell command (rust.bzl:~229–232).
- Severity assessment: Without these assertions, a regression in `generate_rust_parser` that causes it to emit fewer or differently-named files produces a cryptic Bazel "declared output not created" error with no diagnostic naming which file was missing.

## errhandling-3
- Disposition: Fixed
- Action: Changed both ABI3 rename genrules from `cmd = "cp $< $@"` to `cmd = "cp $(location :<target>) $@"` — in `rust.bzl` `fltk_pyo3_cdylib` (step 3) and in `BUILD.bazel` (`native_so` genrule). This avoids positional-first-file assumptions if `rules_rust` ever emits additional files alongside the `.so`.
- Severity assessment: If `rules_rust` emits additional files and the `.so` is not the first, `$<` would copy the wrong file, producing a build success followed by a runtime `ImportError` with no diagnostic pointing at the rename step.

## errhandling-4
- Disposition: TODO(native-submodule-error-context)
- Action: Added a `TODO(native-submodule-error-context)` comment at the `register_submodule` call sites in `clockwork/dsl/clockwork_native_lib.rs` (Clockwork repo). This is consumer-authored boilerplate rather than generated code; the annotation would require either a helper change in `fltk-cst-core::register_submodule` or per-call `.map_err` in the consumer — neither is part of this design's scope.
- Severity assessment: If `cst::register_classes` fails at `import clockwork_native` time, the resulting `ImportError` does not name which submodule failed. Low severity; the fix is a quality-of-life diagnostic improvement and deferred appropriately.

## test-1
- Disposition: Fixed
- Action: Added `test_seeded_reserved_cn_rejected_directly` parametrized test covering all five seeded names (`py_any_methods`, `py_list_methods`, `py_module_methods`, `py_string_methods`, `py_type_methods`) — exercises the per-rule check path where CN is directly in `_RESERVED_CLASS_NAMES_SEEDED`. Added `test_seeded_reserved_handle_rejected_cross_rule` for rule `any_methods` (handle=`PyAnyMethods`) — exercises the cross-rule claims seeding path. Both in `TestReservedClassNameRejection` (tests/test_gsm2tree_rs.py:~1660–1706).
- Severity assessment: Without these tests, regressions in either rejection path (e.g., removal of the seeded init loop or the direct check) would silently allow grammars with rules like `any_methods` to emit code that fails to compile under Rust due to trait name re-definition.

## test-2
- Disposition: Fixed
- Action: Added `TestRustParserRegisterClasses.test_register_classes_signature_uses_qualified_pymodule` (tests/test_gsm2tree_rs.py:~2375–2396) that instantiates `RustParserGenerator` with a minimal grammar and asserts `"pub fn register_classes(module: &Bound<'_, pyo3::types::PyModule>) -> PyResult<()> {"` is in the output.
- Severity assessment: If the qualified `pyo3::types::PyModule` path were accidentally reverted to the bare `PyModule` in `gsm2parser_rs.py`, the test suite would not catch it; the resulting `parser.rs` would fail to compile when the glob import does not bring `PyModule` into scope in contexts where it is not present.

## test-3
- Disposition: Fixed
- Action: Updated `TestPreamble.test_required_use_declarations` (tests/test_gsm2tree_rs.py:~204–213) to assert: (a) the combined-gate import `#[cfg(all(feature = "python", feature = "test-introspection"))]\nuse pyo3::prelude::{pyfunction, wrap_pyfunction};` is present; (b) `pyfunction`/`wrap_pyfunction` do NOT appear under the plain `#[cfg(feature = "python")]` gate alone.
- Severity assessment: Without these assertions, collapsing the combined gate to just the python gate (causing unused-import warnings in non-introspection builds) would go undetected by the test suite.

## reuse-1
- Disposition: Won't-Do
- Action: No change.
- Severity assessment: The two `cp $< $@` (now `cp $(location ...) $@`) sites — one in `BUILD.bazel`'s `native_so` genrule and one inside the `fltk_pyo3_cdylib` macro in `rust.bzl` — serve different targets in different BUILD contexts. Extracting a private Starlark helper would save one line of duplication but introduces `load` coupling between `BUILD.bazel` and an internal symbol in `rust.bzl`. Since `BUILD.bazel` already loads `rust.bzl` for `generate_rust_parser`, the coupling is tolerable, but the two-copy pattern is so trivial (a single `cp` command, now with an explicit location reference) that divergence risk is negligible. Won't-Do unless a third site appears.

## reuse-2
- Disposition: Fixed
- Action: Merged the two consecutive `if class_name in _RESERVED_CLASS_NAMES` / `if class_name in _RESERVED_CLASS_NAMES_SEEDED` blocks into a single `collision_target = _RESERVED_CLASS_NAMES.get(class_name) or _RESERVED_CLASS_NAMES_SEEDED.get(class_name)` with one `if collision_target: raise ValueError(...)` (gsm2tree_rs.py:~171–177).
- Severity assessment: The duplicated format string would cause inconsistent diagnostics if one branch were updated without the other. Low severity but easy to eliminate.

## quality-1
- Disposition: Fixed
- Action: Dropped the `[:40]` truncation and trailing `"..."` in the seeded-claims dict comprehension (gsm2tree_rs.py:~217), changing to `f"pyo3 method trait import: {desc}"`. The full description now appears in cross-rule collision diagnostics.
- Severity assessment: When a grammar author hits a handle collision with a seeded pyo3 method trait, the truncated description forces them to hunt through generator source to understand why the name is reserved. Low severity but a friction point for every consumer who hits this.

## quality-2
- Disposition: Fixed
- Action: Added a comment to `crates/fltk-cst-core/BUILD.bazel` explaining that `crate_features = ["python"]` is hardcoded because all current Bazel consumers are PyO3 cdylibs, and noting that a `config_setting`-based variant would be needed for any future pure-Rust Bazel consumer.
- Severity assessment: Without the comment, the discrepancy between the Cargo.toml (which documents python as optional) and the Bazel BUILD (which hardcodes it) is a silent trap for any future pure-Rust Bazel consumer who depends on `fltk-cst-core` and expects to exclude pyo3.

## quality-3
- Disposition: Fixed
- Action: Added a WARNING note to the `rs_srcs` parameter docstring in `fltk_pyo3_cdylib` (rust.bzl:~183–189) explaining that a target whose outputs include a file named `lib.rs` will silently overwrite the assembled crate root, and instructing callers to always pass a `generate_rust_parser` target.
- Severity assessment: A caller who accidentally passes the wrong label (e.g., one emitting `lib.rs`) gets a silent overwrite that may still compile but produces an unexpected binary missing the `recursion_limit` attribute, manifesting as cryptic E0275 errors. The warning prevents this misuse.

## security-1
- Disposition: Won't-Do
- Action: No change.
- Rationale: The `recursion_limit` parameter is interpolated into a shell command, but the producer of that value is the BUILD file author who already controls the entire Bazel `genrule`/`cmd` surface and can run arbitrary build actions directly. No privilege boundary is crossed. Adding `int()` coercion would provide no meaningful security improvement in this trust domain. The default value (`512`) is an integer literal and is safe. This is an informational note, not an exploitable injection.

## efficiency
- No findings. No dispositions.
