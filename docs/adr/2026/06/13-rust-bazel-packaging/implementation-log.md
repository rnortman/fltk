# Implementation Log: Clockwork consumes FLTK + Rust under Bazel

## Increment 1 — FLTK MODULE.bazel: add rules_rust + crate BUILD.bazel files for fltk-cst-core and fltk-parser-core (commit 9483931)

- MODULE.bazel:5-6: replaced `# TODO(bazel-rules-rust)` with `bazel_dep(name = "rules_rust", version = "0.70.0")`.
- MODULE.bazel:22-35: added `crate` extension (`@rules_rust//crate_universe:extensions.bzl`) with `crate.from_cargo(name = "fltk_crates", ...)` seeded from root `Cargo.toml` + `Cargo.lock` plus crate manifests for fltk-cst-core and fltk-parser-core; `use_repo(crate, "fltk_crates")`.
- crates/fltk-cst-core/BUILD.bazel (new): `rust_library` target `fltk-cst-core` with `crate_features = ["python"]`, dep `@fltk_crates//:pyo3`, public visibility.
- crates/fltk-parser-core/BUILD.bazel (new): `rust_library` target `fltk-parser-core` with deps `//crates/fltk-cst-core` and `@fltk_crates//:regex-automata`, public visibility.
- TODO.md: annotated `bazel-rules-rust` entry with ADR reference (not yet closing it — work in progress).
- All 1654 existing Python tests pass (uv run pytest). Rust build unaffected (maturin develop still works).

## Increment 2 — FLTK BUILD.bazel: fltk._native rust_shared_library + native_py py_library (commit 334cc8a)

- BUILD.bazel:3: added `load("@rules_rust//rust:defs.bzl", "rust_shared_library")`.
- BUILD.bazel:31-44: added `rust_shared_library(name = "native", ...)` — builds `src/**/*.rs` with `crate_name = "fltk_native"`, `crate_features = ["extension-module"]`, deps on `//crates/fltk-cst-core` and `@fltk_crates//:pyo3`, public visibility.
- BUILD.bazel:46-54: added `genrule(name = "native_so", ...)` — copies `libfltk_native.so` → `fltk/_native.abi3.so` (abi3 basename required for CPython stable-ABI import; rules_rust emits `lib<crate_name>.so`, not the abi3 name).
- BUILD.bazel:56-64: added `py_library(name = "native_py", data = [":native_so"], imports = ["."], ...)` — makes `fltk/_native.abi3.so` available on the Python path for any target that deps on `:native_py`, public visibility.
- All 1654 Python tests pass (uv run pytest). No Rust-level build validation possible without a live Bazel invocation.

## Increment 3 — FLTK rust.bzl: generate_rust_parser rule + fltk_pyo3_cdylib macro (commit b3bdc8e)

- rust.bzl (new): new file at repo root with two public symbols:
  - `generate_rust_parser` rule (lines 25–116): runs two separate `ctx.actions.run` calls on `@fltk//:genparser` — `gen-rust-cst <grammar> <cst_out>` and `gen-rust-parser <grammar> <parser_out> --cst-mod-path <path>`. Emits `<name>/cst.rs` and `<name>/parser.rs` as action outputs with fixed basenames. Attr `cst_mod_path` defaults to `"super::cst"`.
  - `fltk_pyo3_cdylib` macro (lines 118–262): four-step assembly: (1) genrule copying lib.rs + generated cst.rs/parser.rs into a flat `<name>_crate_root/` gendir using `$(locations rs_srcs)` + bash `basename`; (2) `rust_shared_library` with `extension-module` feature, `crate_root` pointing at assembled lib.rs, deps on `//crates/fltk-cst-core`, `//crates/fltk-parser-core`, `@fltk_crates//:pyo3`; (3) genrule renaming `lib<name>.so` → `<name>.abi3.so`; (4) `py_library` carrying the abi3 so as `data` and `@fltk//:native_py` as `deps` (closes invariant #1: fltk._native importable in test sandboxes transitively).
- BUILD.bazel:5: added `load("//:rust.bzl", "generate_rust_parser")`.
- BUILD.bazel:98-103: added `generate_rust_parser(name = "bootstrap_rust_srcs", src = "fltk/fegen/bootstrap.fltkg")` smoke-test target (design §5.4 — FLTK CI coverage of the new Bazel surface independent of Clockwork).
- All 1654 Python tests pass. No Bazel invocation possible without a full Bazel environment.
- Deviation: design §2.3 shows macro signature with separate `cst_rs` and `parser_rs` attrs both pointing to the same target; shipped with single `rs_srcs` attr taking the `generate_rust_parser` target, since both `cst_rs`/`parser_rs` would be the same label and the macro uses `$(locations rs_srcs)` to get both files. Simpler interface with identical semantics.

## Increment 4 — Clockwork MODULE.bazel + BUILD.bazel: rules_rust toolchain, fltk pin update, rust codegen + cdylib targets, roundtrip test (commit 0bf463b in clockwork)

- clockwork/MODULE.bazel:34: updated @fltk pin from 0afecaf5 → f32b2c9e02f06ba6edb26fc1392d73c8a15ba290 (the commit carrying FLTK's new Rust Bazel surface: rules_rust dep, fltk_crates crate hub, fltk-cst-core/fltk-parser-core BUILD.bazel, native_py py_library, rust.bzl).
- clockwork/MODULE.bazel:59: added `("rules_rust", SINGLE_VERSION_OVERRIDE, "0.70.0", NO_PATCH)` into the keep-sorted dependencies list (between rules_python_gazelle_plugin and rules_shell, matching alphabetical order); the single_version_override list comprehension wires this into Bazel's module resolution automatically.
- clockwork/MODULE.bazel:143-152: added `rust` extension block — `use_extension("@rules_rust//rust:extensions.bzl", "rust")`, `rust.toolchain(edition="2021", versions=["1.87.0"])`, `use_repo(rust, "rust_toolchains")`, `register_toolchains("@rust_toolchains//:all")` — root-module toolchain registration per design §3.2 (O2 default: download-prebuilt, x86_64-linux, latest stable at implementation time = 1.87.0).
- clockwork/clockwork/dsl/BUILD.bazel:5: added `load("@fltk//:rust.bzl", "fltk_pyo3_cdylib", "generate_rust_parser")`.
- clockwork/clockwork/dsl/BUILD.bazel:7: added `py_test` to the `//tools/rules:python.bzl` load.
- clockwork/clockwork/dsl/BUILD.bazel:65-85: added `generate_rust_parser(name="clockwork_rs_srcs", src="clockwork.fltkg")`, `fltk_pyo3_cdylib(name="clockwork_native", rs_srcs=":clockwork_rs_srcs", lib_rs="clockwork_native_lib.rs", visibility=["//clockwork:__subpackages__"])`, `py_test(name="clockwork_rust_roundtrip_test", srcs=["clockwork_rust_roundtrip_test.py"], deps=[":clockwork_native"])`.
- clockwork/clockwork/dsl/clockwork_native_lib.rs (new): consumer-authored PyO3 crate root; declares `mod cst; mod parser;` and `#[pymodule] fn clockwork_native(...)` wiring `register_submodule` for both submodules.
- clockwork/clockwork/dsl/clockwork_rust_roundtrip_test.py (new): two tests — (1) asserts `fltk._native.Span` importable without triggering the pure-Python fallback warning; (2) parses `"cpu_domain main;\n"` (minimal valid `module` entity) through `clockwork_native.parser.Parser`, asserts result is non-None, full input consumed, span covers 0..len(src).
- O1 resolution: Clockwork does not declare its own crates_repository in this increment; FLTK's `fltk_crates` hub provides pyo3 transitively through the macro. When Clockwork adds its own native Rust with third-party deps, it will add its own `crate` hub (design O1 recommendation (b)).
- O2 resolution: Rust 1.87.0 (latest stable at implementation date), download-prebuilt, x86_64-linux; aarch64 not registered (no aarch64 Rust CI today, can be added when needed).

## Increment 5 — Verification via local_path_override + green build (commits aba376a + 3267fa0 in fltk, 42fedc8 in clockwork)

**TEMPORARY OVERRIDE NOTE**: Clockwork MODULE.bazel was temporarily switched from
`git_override` to `local_path_override("/home/rnortman/src/fltk")` for this verification run.
TODO(fltk-pin-finalize): revert to real git pin at reviewed FLTK HEAD before merging.
Comment in MODULE.bazel marks the override and records the real git pin for reference.

### What changed

**FLTK (fltk HEAD: 3267fa0)**:

- BUILD.bazel:34-44: added `"python"` to `crate_features` for `@fltk//:native` target.
  `register_classes` symbols are gated on `#[cfg(feature = "python")]`; Bazel does not
  forward features transitively (unlike Cargo), so `"python"` must be stated explicitly
  alongside `"extension-module"`. Without this, `E0425` link errors prevented
  the cdylib from building.
- rust.bzl:82-91: fixed implicit string concatenation in `cst_mod_path` doc string.
  Starlark forbids implicit string concatenation; `+` operator required.
  Error: `"Implicit string concatenation is forbidden"`.
- gsm2tree_rs.py:391-413: removed `use pyo3::types::{PyList, PyTuple, PyType}` from the
  generated cst.rs preamble. Grammar rules named "list"/"tuple"/"type" generate
  `pub struct PyList/Tuple/Type` handles that collide with these unqualified pyo3 names
  (E0255, E0117). Fix: all call sites updated to use fully-qualified
  `pyo3::types::PyList::...` paths. The clockwork grammar has a `list` rule.
- gsm2tree_rs.py/gsm2parser_rs.py: changed `register_classes(module: &Bound<'_, PyModule>)`
  to `register_classes(module: &Bound<'_, pyo3::types::PyModule>)`. The clockwork grammar
  has a `module` rule (its top-level rule) — generating `pub struct PyModule` collided
  with `PyModule` from `pyo3::prelude::*`. Fully-qualified path avoids collision.
- gsm2tree_rs.py: added `IndexError`, `TypeError`, `ValueError`, `Any` to
  `_RESERVED_CLASS_NAMES` (still imported unqualified). "List"/"Tuple"/"Type"/"Module"
  are no longer reserved since their collisions are now fixed by qualified paths.
- All fixture cst.rs/parser.rs files regenerated via `make gencode`.
- Tests updated to match new signatures and reserved-name table.
- All 1662 FLTK Python tests pass. Rust extension rebuilds clean with maturin.

**Clockwork (clockwork HEAD: 42fedc8)**:

- MODULE.bazel: switched `("fltk", git_url, commit, NO_PATCH)` to
  `("fltk", LOCAL_PATH_OVERRIDE, "/home/rnortman/src/fltk", NO_PATCH)` for verification.
  TODO(fltk-pin-finalize) comment records the original git pin and explains the revert needed.
- clockwork/dsl/BUILD.bazel: renamed `py_pytest_main(name = "__rust_test__", ...)` to
  `__test__` and updated the `py_test` srcs/deps/main references. Clockwork's `py_test`
  macro hardcodes the pytest main label as `:__test__`; `__rust_test__` was rejected.
- clockwork/dsl/clockwork_native_lib.rs: added `#![recursion_limit = "512"]`. The
  Clockwork DSL grammar contains deeply recursive DFL types (DflArg → DflExpr → ... →
  DflCallSuffix → DflArgList → DflArg) that caused E0275 "overflow evaluating
  Shared<DflArg>: Send" when the default recursion limit was exceeded.
- clockwork/dsl/clockwork_rust_roundtrip_test.py: fixed incorrect `Span.__module__` check.
  PyO3 0.29 classes without `module = "..."` report `__module__ = "builtins"`, not the
  importing module's name — this is correct behavior. Test now checks `__module__` is NOT
  `"fltk.fegen.pyrt.terminalsrc"` (the Python fallback) instead of requiring a specific value.

### Bazel verdict

| Target | Result |
|--------|--------|
| `//clockwork/dsl:clockwork_rust_roundtrip_test` (roundtrip py_test, 2 tests) | **GREEN** — both tests pass |
| `@@fltk+//:bootstrap_rust_srcs` (FLTK-side Rust codegen smoke) | **GREEN** — cst.rs + parser.rs generated |

## Increment 6 — pyo3 prelude de-glob + full collision coverage (commit 42076af)

Reviewed prior uncommitted edits against design-buildfix.md §2.4, completed all missing pieces,
regenerated fixtures, confirmed gate GREEN (1669 Python tests, full Rust clippy/test/cargo-deny).

### What shipped

**fltk/fegen/gsm2tree_rs.py**

- `_RESERVED_CLASS_NAMES` (lines 43–74): removed `Any` (PyAny now fully qualified at all
  emission sites) and `FromPyObject` (not imported unqualified; proc-macro handles it internally).
  Added Half-2 entries: `Bound`, `Py`, `Python`, `IntoPyObject` (bare `{CN}` struct collisions
  with explicit prelude import).
- `_RESERVED_CLASS_NAMES_SEEDED` (new dict, lines 76–107): five pyo3 method traits imported
  unqualified (`PyAnyMethods`, `PyListMethods`, `PyModuleMethods`, `PyStringMethods`,
  `PyTypeMethods`) that are in Py{CN} form; seeded into the cross-rule claims dict in `__init__`
  so handle collisions are detected.
- `_bad_reserved` invariant check (lines ~117–125): updated to allow `Py` + lowercase-third-char
  names (e.g. `Python`) that are not valid `Py{CN}` handle forms; replaced magic literal `2` with
  named constant `_PY_PREFIX_LEN`.
- `__init__` (line ~162): added check of `_RESERVED_CLASS_NAMES_SEEDED`; added seeding of seeded
  reserved names into claims dict before the cross-rule check.
- Preamble emission (`_cst_preamble`): replaced `use pyo3::prelude::*` glob with explicit import
  list; qualified all `PyAny`, `PyResult`, `PyRef` uses at emission sites to `pyo3::PyAny`,
  `pyo3::PyResult`, `pyo3::PyRef`; fixed three remaining unqualified `PyResult` uses
  (`children`, `children_<label>`, `register_classes`); split `pyfunction`/`wrap_pyfunction`
  into a separate `#[cfg(all(feature = "python", feature = "test-introspection"))]` import to
  avoid "unused import" warnings when test-introspection is off.

**fltk/fegen/gsm2parser_rs.py**

- Added asymmetry note comment documenting why the parser's `python_bindings` block retains
  `use pyo3::prelude::*` (parser emits only fixed class names, not rule-derived `PyX` structs,
  so rule-name collision analysis does not apply).

**src/cst_generated.rs, src/cst_fegen.rs** (regenerated via `make gencode`): updated preamble.

**tests/test_gsm2tree_rs.py**

- Updated preamble assertions: glob `not in` check; new explicit prelude string.
- `TestReservedClassNameRejection.test_reserved_class_name_rejected`: removed `any`/`from_py_object`
  (no longer reserved); added `bound`, `py`, `python`, `into_py_object`, `py_any_methods`,
  `py_list_methods`, `py_module_methods`, `py_string_methods`, `py_type_methods`.
- `test_rules_not_reserved_are_accepted`: added `any`, `err`, `result`, `from_py_object`.
- Updated ~15 test assertions using old unqualified `PyAny`, `PyResult`, `PyRef` forms to
  fully-qualified `pyo3::PyAny`, `pyo3::PyResult`, `pyo3::PyRef`.
- Updated `register_classes` return type assertion to `pyo3::PyResult<()>`.

**Gate**: 1669 Python tests GREEN, Rust build + clippy + cargo-deny all GREEN.

## Increment 7 — Problem 4: inject #![recursion_limit] into assembled crate root via fltk_pyo3_cdylib macro (commit 678dfa9 fltk, 6717614 clockwork)

- rust.bzl:126: added `recursion_limit = 512` parameter to `fltk_pyo3_cdylib`.
- rust.bzl:216-217: changed `_assemble_crate` genrule cmd from `cp $(location {lib_rs}) $$OUTDIR/lib.rs` to `printf '#![recursion_limit = "{recursion_limit}"]\\n' > $$OUTDIR/lib.rs && cat $(location {lib_rs}) >> $$OUTDIR/lib.rs`. Attribute is emitted as the very first line so it precedes all items and inner attributes in the consumer file (rustc inner-attribute ordering requirement).
- rust.bzl:225: added `recursion_limit = recursion_limit` to the `.format()` call.
- rust.bzl docstring: moved Consumer lib.rs template before Args block; added Note on recursion_limit; added `recursion_limit` attr description.
- clockwork/dsl/clockwork_native_lib.rs: removed `#![recursion_limit = "512"]` (now macro-owned); replaced explanatory comment with note directing consumers not to add the attribute.
- Gate: fltk full `make check` GREEN (lint, format, typecheck, all tests, cargo-deny).
