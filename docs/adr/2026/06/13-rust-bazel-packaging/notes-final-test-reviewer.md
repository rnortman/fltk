# Test review notes — rust-bazel-packaging

Commit reviewed: fltk HEAD 9657025, Clockwork HEAD 6717614
Acceptance bar: Bazel-built Rust parser + pyo3 bindings produce SOME parse result — NOT Python/Rust equivalence or fltk correctness.

---

## test-1

**File:** `tests/test_gsm2tree_rs.py`, `TestReservedClassNameRejection`

**What's wrong — missing coverage (seeded reserved names, direct rejection path).**

`_RESERVED_CLASS_NAMES_SEEDED` has five entries (`PyAnyMethods`, `PyListMethods`, `PyModuleMethods`, `PyStringMethods`, `PyTypeMethods`). There are two rejection paths for these names, and neither is tested:

- *Direct check* (`gsm2tree_rs.py` line 175–178): a rule named `py_any_methods` derives `CN = PyAnyMethods`, which falls into `_RESERVED_CLASS_NAMES_SEEDED` and is rejected there before the cross-rule claims check. No parametrize entry exists for any of these rule names.
- *Cross-rule claims check*: a rule named `any_methods` derives `CN = AnyMethods` and `handle = PyAnyMethods`. `PyAnyMethods` is seeded into `claims` at init time (line 218), so a grammar containing `any_methods` should raise a collision error. This path has zero test coverage.

**Consequence:** if either rejection path regressed (e.g., a future developer removes the seeded init or the direct check), grammars with rules named `py_any_methods` or `any_methods` (and the other four trait names) would silently emit code that fails to compile under Rust because the trait name would be re-defined as a struct/handle. The test suite would not catch the regression.

**Fix:** add two parametrize cases to `test_reserved_class_name_rejected`: `("py_any_methods", "PyAnyMethods", "pyo3")` (direct path) and one representative cross-rule case such as a two-rule grammar containing `any_methods` raising a ValueError naming `PyAnyMethods`. Alternatively extend the existing cross-rule collision tests with a case seeded from `_RESERVED_CLASS_NAMES_SEEDED`.

---

## test-2

**File:** `tests/test_gsm2tree_rs.py` (no test file for `gsm2parser_rs.py`)

**What's wrong — missing coverage (parser.rs register_classes signature change).**

`gsm2parser_rs.py` was changed so that `parser.rs`'s `register_classes` uses `pyo3::types::PyModule` (qualified) instead of the bare `PyModule` that the glob previously provided. This change is present in the production code and is reflected in the checked-in fixture files (`tests/rust_cst_fegen/src/parser.rs`, `tests/rust_parser_fixture/src/parser.rs`), but there is no pytest that exercises `RustParserGenerator` directly and asserts the new signature string in generated source.

The closest equivalent for the CST generator is `test_register_classes_function_present` (in `TestRegisterClasses`) which checks the full `register_classes` signature in `cst.rs`. No parallel test exists for `parser.rs`.

**Consequence:** if the `pyo3::types::PyModule` path in `gsm2parser_rs.py` is accidentally reverted to the bare `PyModule` (or accidentally removed), the test suite will not detect it. The fixture files are golden outputs and would need to be manually regenerated and compared; there is no automated dynamic check.

**Fix:** add a test (parallel to `TestRegisterClasses.test_register_classes_function_present`) that instantiates `RustParserGenerator` with a minimal grammar, calls `generate()`, and asserts `"pub fn register_classes(module: &Bound<'_, pyo3::types::PyModule>) -> PyResult<()> {"` appears in the output. This could live in `test_gsm2tree_rs.py` or in a dedicated `test_gsm2parser_rs.py`.

---

## test-3

**File:** `tests/test_gsm2tree_rs.py`, `TestPreamble.test_required_use_declarations`

**What's wrong — missing coverage (combined cfg gate for pyfunction/wrap_pyfunction).**

`gsm2tree_rs.py` emits a new import line gated on `#[cfg(all(feature = "python", feature = "test-introspection"))]` that brings `pyfunction` and `wrap_pyfunction` into scope. This is a new separate import statement that did not exist before the diff. `test_required_use_declarations` checks the regular `#[cfg(feature = "python")]` preamble contents but does not assert that the combined-gate import is present (or that `pyfunction`/`wrap_pyfunction` do NOT appear inside the ordinary python gate — which would be a regression if the import were accidentally moved).

**Consequence:** if the combined cfg gate were accidentally collapsed to just `#[cfg(feature = "python")]` (pulling the macro names into the always-on-python import), the test suite would not notice, and the "unused import" warnings the comment warns about would appear in production builds without test-introspection enabled.

**Fix:** in `test_required_use_declarations`, add:
```python
assert '#[cfg(all(feature = "python", feature = "test-introspection"))]\nuse pyo3::prelude::{pyfunction, wrap_pyfunction};' in poc_source
```
and assert that `pyfunction` and `wrap_pyfunction` do NOT appear inside the ordinary `#[cfg(feature = "python")]` block without the combined gate.

---

## Not findings (within acceptance bar)

- **Clockwork `test_clockwork_native_parses_module`**: does not test `clockwork_native.cst` directly (only `clockwork_native.parser`). Against the stated acceptance bar — "produce SOME parse result" — this is sufficient. The CST accessors (`span.start`, `span.end`) are exercised via `module_node.span`. Adequate.
- **`test_fltk_native_span_is_rust_path`**: the inverted `__module__` check is not vacuous — `ImportError` from `import fltk._native` would fail the test loudly, and the `!= "fltk.fegen.pyrt.terminalsrc"` + `in ("builtins", "fltk._native")` pairing correctly distinguishes Rust from the fallback. The design-buildfix.md §7 rationale holds.
- **`rust.bzl` / `fltk_pyo3_cdylib`**: Bazel macro behavior (crate assembly, recursion_limit injection, abi3 rename) is not testable by pytest. The Clockwork `clockwork_rust_roundtrip_test` transitively exercises the full macro path and serves as the integration gate. This is structurally appropriate.
- **`bootstrap_rust_srcs` TODO**: the `TODO(fltk-pyo3-cdylib-smoke)` in `BUILD.bazel` correctly calls out the missing in-FLTK smoke test for `fltk_pyo3_cdylib`. It is a known intentional deferral, not a test quality issue.
