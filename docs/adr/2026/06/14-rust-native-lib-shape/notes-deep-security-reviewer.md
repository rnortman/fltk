# Deep Security Review — rust-native-lib-shape

Commit reviewed: fltk 7a7ca4d (base 7200d9c); clockwork ea34388 (base 6ede250)

No findings.

## Scope examined

- `fltk/fegen/gsm2lib_rs.py` — new Rust lib.rs generator. Emits Rust source
  parameterized by `module_name` / submodule names. All such names pass through
  `_validate_rust_ident` (`^[A-Za-z_][A-Za-z0-9_]*$`) before interpolation, so
  no code-injection path into the generated `.rs` exists. Inputs are
  developer/build-time (Bazel target name, CLI flags), not untrusted runtime data.
- `fltk/fegen/genparser.py` — new `gen-rust-lib` CLI command. Writes generated
  source to a developer-supplied output path; no untrusted input.
- `rust.bzl` — `fltk_pyo3_cdylib` now generates lib.rs from the target `name` via
  `genparser gen-rust-lib $@ --module-name '{name}'`. `name` is a Bazel target
  name (build-time, restricted charset); the generator additionally rejects any
  non-identifier via `_validate_rust_ident`. Single-quoted in the genrule cmd.
  No injection of untrusted runtime data.
- `crates/fegen-rust/src/parser.rs` + `cst.rs` + `lib.rs`, `tests/rust_poc_cst/*`,
  `src/lib.rs`, `crates/fltk-cst-core/src/py_module.rs` — generated/boilerplate
  pyo3 module wiring and a generated recursive-descent parser. The parser handles
  arbitrary source text by design; stack exhaustion is bounded by `max_depth`
  (documented), regex patterns are compile-time constants. No secrets, no auth
  surface, no network/SSRF, no deserialization, no path traversal.
- clockwork diff: deletions only (removed `clockwork_native_lib.rs`, BUILD edit).
  No new attack surface.

No trust-boundary, injection, secrets, crypto, auth, or deserialization issues
introduced by this change.
