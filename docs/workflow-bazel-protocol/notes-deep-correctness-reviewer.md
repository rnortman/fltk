# Deep correctness review — Bazel parser-codegen unification

Commit reviewed: 224344d844feeefa7acdb8f4eaa285322a70634d (base 3c244d1)
Scope: rust.bzl, BUILD.bazel (the .bzl/BUILD logic; docs are informational).

No findings.

Traced:
- `out_subdir = extension_name or name` fallback — pure-Rust (`""` → target name)
  vs python-extension (`extension_name = name`) both resolve correctly; stub dir,
  `--extension-name`, and compiled module name now share one owner `name`.
- Output-group routing: `rust_srcs = [cst_out, parser_out]` fed to crate assembly;
  `stub_srcs` (pyi + optional cst_protocol.py) fed to py_library.data. `stub_srcs`
  is an empty depset exactly when `protocol_module` is empty; empty filegroup as
  py_library data is valid — no dangling label.
- Crate-assembly genrule copies only the `rust_srcs` filegroup by basename; the
  lib.rs-overwrite hazard is unreachable (codegen rule emits only cst.rs/parser.rs).
- Target/label namespace: `name` (py_library) vs `name_srcs`, `name_rust_srcs`,
  `name_stub_srcs`, `name_gen_lib`, `name_assemble_crate`, `name_cdylib`, `name_so`,
  and declared file `name/cst.rs` — all distinct; no collision.
- Fail-guard matrix (macro L583–600 + rule L123): every
  `python_extension`/`protocol`/`protocol_module` combination that is invalid
  reaches a `fail()`; no valid combination is blocked. Pure-Rust guards are correctly
  scoped inside `if not python_extension`.
- `**kwargs` routing: forwarded to `_generate_rust_srcs` in pure mode, to
  `_build_pyo3_cdylib`→`rust_shared_library` in python mode; not double-applied.

Non-blocking (pre-existing, documented, out of scope): full `bazel build
//:bootstrap_native` fails in the `gen-rust-parser` action on bootstrap.fltkg's
block-comment regex (outside Rust portable subset), tracked by
TODO(bazel-rust-smoke-bootstrap-regex). Not introduced by this diff.
