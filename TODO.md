# TODOs

## `example-placeholder`

This is a placeholder entry. Leave it here so the file is never empty. It is not a real TODO. You would reference it in code with `// TODO(example-placeholder)` comments. This is the basic TODO system design: An entry here with a slug used to join to code comments. Add real TODOs below this one in this format.

## `bazel-rules-rust`

Add `rules_rust` to `MODULE.bazel` so that the PyO3 native extension (`fltk._native`) is buildable via Bazel. Currently, Bazel builds do not include the Rust extension. Deferred from Phase 0 because Bazel Rust support is orthogonal to the Python/maturin build path. Location: `MODULE.bazel`.

Implementation in progress — see ADR at `docs/adr/2026/06/13-rust-bazel-packaging/`.

## `fltk-pyo3-cdylib-smoke`

Add an in-FLTK `fltk_pyo3_cdylib` invocation to `BUILD.bazel` using `bootstrap_rust_srcs` + a minimal hand-written `lib.rs` (analogous to `tests/rust_parser_fixture/src/lib.rs`) so FLTK CI covers the full macro — crate-source assembly, cdylib compilation, abi3 rename, py_library wrapper — independent of Clockwork. Currently only `generate_rust_parser` is exercised in FLTK CI; `fltk_pyo3_cdylib` is only tested transitively by Clockwork's build. Location: `BUILD.bazel` (after `bootstrap_rust_srcs`).

## `verify-pyo3-ext-module`

At implementation spike time, confirm that `extension-module` is active on the `@fltk_crates//:pyo3` target after `crate_universe` resolution. Run `bazel build //:native` on a clean checkout; if pyo3 links libpython the feature is not activated and a `crate.annotation(crate = "pyo3", crate_features = ["extension-module"])` is needed in `MODULE.bazel`'s `crate.from_cargo` block. Also confirm that dev-dep crates from the root workspace do not leak into the hub. Location: `MODULE.bazel` (`crate.from_cargo` block).

## `bazel-cst-spike-hub`

`fltk-cst-spike` is a workspace member in root `Cargo.toml` and is therefore included in the `@fltk_crates` hub via `from_cargo`. If `fltk-cst-spike` acquires large or conflicting deps, consider excluding it from the workspace root `Cargo.toml` members list or using a dedicated minimal manifest for the Bazel crate hub. Location: `MODULE.bazel` and root `Cargo.toml`.

## `extend-children-owned`

`extend_children(&Self)` clones every child Arc even though the donor node is immediately dropped after the call (inline-to-parent sub-expression and `+`/`*` loop paths). A consuming variant `extend_children_owned(other: Self)` using `Vec::append` would avoid the atomic inc+dec pairs per child on the parse hot path. Blocked on `gsm2tree_rs.py` adding the method to the generated CST node API. Location: `fltk/fegen/gsm2parser_rs.py` (`_gen_item_multiple`, `_gen_append_code`), `fltk/fegen/gsm2tree_rs.py` (generated `impl <Node>` blocks). Re-open only with profiling evidence.

