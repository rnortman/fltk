# TODOs

## `example-placeholder`

This is a placeholder entry. Leave it here so the file is never empty. It is not a real TODO. You would reference it in code with `// TODO(example-placeholder)` comments. This is the basic TODO system design: An entry here with a slug used to join to code comments. Add real TODOs below this one in this format.

## `pyo3-upgrade`

Upgrade pyo3 from 0.23 to a current release (>=0.29.0) to clear RustSec advisories RUSTSEC-2025-0020 (buffer overflow in `PyString::from_object`) and RUSTSEC-2026-0177 (missing `Sync` bound on `PyCFunction::new_closure`). This is a real API migration, not a version bump: pyo3 0.23->0.29 breaks ~29+ sites in `fltk-cst-core` alone, concentrated in fragile cross-cdylib internals (`pyo3::impl_::pycell::PyClassObject`, `GILOnceCell`, `downcast_*`) plus the `IntoPyObject` trait migration, and will cascade into `fltk-native`, the Rust code generators (`fltk/fegen/gsm2tree_rs.py`, `gsm2parser_rs.py`), and generated fixtures. Public-API-sensitive (generated CST is downstream public API) so do it incrementally version-by-version following pyo3 migration guides, TDD, verifying cross-backend equivalence. Until then the two advisories are ignored in `deny.toml` (`[advisories] ignore`). Bump pyo3 across all six manifests (root, `crates/fltk-cst-core`, `crates/fltk-cst-spike`, `tests/rust_cst_fegen`, `tests/rust_cst_fixture`, `tests/rust_parser_fixture`), then remove the `ignore` entries in `deny.toml`. Location: `deny.toml`, the six `Cargo.toml` manifests, `crates/fltk-cst-core/src/{span,registry,cross_cdylib}.rs`.

## `bazel-rules-rust`

Add `rules_rust` to `MODULE.bazel` so that the PyO3 native extension (`fltk._native`) is buildable via Bazel. Currently, Bazel builds do not include the Rust extension. Deferred from Phase 0 because Bazel Rust support is orthogonal to the Python/maturin build path. Location: `MODULE.bazel`.

## `extend-children-owned`

`extend_children(&Self)` clones every child Arc even though the donor node is immediately dropped after the call (inline-to-parent sub-expression and `+`/`*` loop paths). A consuming variant `extend_children_owned(other: Self)` using `Vec::append` would avoid the atomic inc+dec pairs per child on the parse hot path. Blocked on `gsm2tree_rs.py` adding the method to the generated CST node API. Location: `fltk/fegen/gsm2parser_rs.py` (`_gen_item_multiple`, `_gen_append_code`), `fltk/fegen/gsm2tree_rs.py` (generated `impl <Node>` blocks). Re-open only with profiling evidence.


