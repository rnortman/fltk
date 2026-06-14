# Scope Pre-pass Notes

Reviewed commits: fltk fafa6d7..353d24c, clockwork ece332ad..0bf463b

## Summary

Implementation is complete and clean against the design. All design-scope items are present.

## Design-scope item checklist

**§3.1 / §3.2 FLTK MODULE.bazel — rules_rust dep + crate hub**
Present. `bazel_dep(name = "rules_rust", version = "0.70.0")` replaces the `TODO(bazel-rules-rust)` line. `crate.from_cargo(name = "fltk_crates", ...)` seeded from root `Cargo.toml` + `Cargo.lock` plus the two crate manifests. `use_repo(crate, "fltk_crates")`. Matches design §3.2 and §3.1 exactly.

**§3.3 FLTK BUILD.bazel — fltk-cst-core + fltk-parser-core rust_library targets**
Present. `crates/fltk-cst-core/BUILD.bazel` and `crates/fltk-parser-core/BUILD.bazel` — both `rust_library`, public visibility, correct features (`python` on cst-core), correct deps (`@fltk_crates//:pyo3` for cst-core, `//crates/fltk-cst-core` + `@fltk_crates//:regex-automata` for parser-core).

**§3.3 FLTK BUILD.bazel — :native rust_shared_library + :native_so genrule + :native_py py_library**
Present. `rust_shared_library(name = "native", ...)` with `crate_features = ["extension-module"]`, `genrule(name = "native_so", ...)` copying `libfltk_native.so` → `fltk/_native.abi3.so`, `py_library(name = "native_py", data = [":native_so"], imports = ["."])`. Public visibility on all three. Matches design §3.3 and §3.4 (.so basename binding).

**§3.4 FLTK rust.bzl — generate_rust_parser rule**
Present. Two separate `ctx.actions.run` calls for `gen-rust-cst` and `gen-rust-parser`; fixed output basenames `<name>/cst.rs` and `<name>/parser.rs`; `cst_mod_path` attr (default `super::cst`) forwarded only to `gen-rust-parser`. No `--protocol-module` / `--pyi-output` passed. Matches design §3.4 exactly.

**§3.4 FLTK rust.bzl — fltk_pyo3_cdylib macro (4-step assembly)**
Present. Step 1 genrule copies lib.rs + cst.rs + parser.rs into `<name>_crate_root/`; step 2 `rust_shared_library` with `extension-module` + deps on `//crates/fltk-cst-core`, `//crates/fltk-parser-core`, `@fltk_crates//:pyo3`; step 3 genrule renames `lib<name>.so` → `<name>.abi3.so`; step 4 `py_library` with abi3 `.so` as `data` and `@fltk//:native_py` in `deps`. Matches design §3.4 (both Crate-source assembly and .so basename binding).

**§5.4 FLTK CI smoke test**
Present. `generate_rust_parser(name = "bootstrap_rust_srcs", src = "fltk/fegen/bootstrap.fltkg")` in `BUILD.bazel`. Matches design §5, item 4.

**§3.2 / §3.5 Clockwork MODULE.bazel — rules_rust dep + toolchain registration**
Present. `("rules_rust", SINGLE_VERSION_OVERRIDE, "0.70.0", NO_PATCH)` in alphabetical position in the dependencies list. `rust` extension block with `rust.toolchain(edition="2021", versions=["1.87.0"])`, `use_repo(rust, "rust_toolchains")`, `register_toolchains("@rust_toolchains//:all")`. O2 resolved as download-prebuilt x86_64 1.87.0 (logged). Matches design §3.2 exactly.

**§3.5 / §2.3 Clockwork BUILD.bazel — generate_rust_parser + fltk_pyo3_cdylib + py_test targets**
Present. `generate_rust_parser(name="clockwork_rs_srcs", src="clockwork.fltkg")`, `fltk_pyo3_cdylib(name="clockwork_native", rs_srcs=":clockwork_rs_srcs", lib_rs="clockwork_native_lib.rs", visibility=[...])`, `py_test(name="clockwork_rust_roundtrip_test", ...)`. Existing Python targets unchanged (AC #5 visually confirmed — no removals in the diff above the `# --- Rust backend ---` comment).

**§2.3 clockwork_native_lib.rs**
Present. Matches design's template exactly: `use fltk_cst_core::register_submodule`, `mod cst; mod parser;`, `#[pymodule] fn clockwork_native(...)`.

**§5 (AC #3 + #4) clockwork_rust_roundtrip_test.py**
Present. Two tests: (1) asserts `fltk._native.Span` importable without triggering the pure-Python fallback warning; (2) parses `"cpu_domain main;\n"` through `clockwork_native.parser.Parser`, asserts non-None result with full input consumed and span covering 0..len(src). Matches design §5, items 3.

**TODO.md annotation**
Present. `bazel-rules-rust` entry annotated with ADR reference. Design required the entry be updated; it is (not yet closed — logged as in-progress, consistent with implementation log note).

## Noted deviation (called out, accepted)

The design showed `fltk_pyo3_cdylib` with separate `cst_rs` and `parser_rs` attrs (both pointing at the same label). The implementation shipped a single `rs_srcs` attr instead. The implementation log calls this out explicitly with rationale: both attrs would always be the same label, so the single-attr interface is strictly simpler with identical semantics. The deviation is documented and the consequence is a cleaner consumer API; the design intent (both generated files fed to the macro) is fully realized.

## No findings.
