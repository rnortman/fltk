# Security review — rust-bazel-packaging (final)

Commits reviewed:
- fltk: base `fafa6d7c12f9bd053f9f32f4cfb1a29e8136fe0e` .. HEAD `9657025`
- Clockwork: base `ece332ad111805e3b2a355244835b87f073ee65e` .. HEAD `6717614`

Scope: Bazel + rules_rust packaging integration, generated-Rust pyo3 name-collision
robustness fix, and Clockwork-side roundtrip test wiring.

## Trust model

The changed surface is entirely **build-time / developer-controlled**: `.fltkg`
grammar files, Bazel `BUILD`/`MODULE` files, macro parameters, and the generated
Rust the toolkit emits for downstream consumers. None of it is a service endpoint,
and no path in the diff ingests network/end-user/untrusted runtime input. The
collision-handling work hardens the generator against *legitimate* consumer grammar
rule names (`list`, `module`, `bound`, …) colliding with pyo3 imports — a
correctness/robustness property, not an attacker-controlled injection.

Secrets scan over both diffs: clean (only hit is `TokenType`, benign).

## security-1 (informational, low) — genrule shell interpolation of macro params in rust.bzl

- File: `rust.bzl` (the `fltk_pyo3_cdylib` macro, `name + "_assemble_crate"` genrule `cmd`).
- Issue: `recursion_limit` is `.format()`-interpolated into a shell single-quoted
  `printf '#![recursion_limit = "{recursion_limit}"]\n'`, and `lib_rs` / `rs_srcs`
  labels are interpolated into `$(location ...)`/`$(locations ...)`. A non-integer
  `recursion_limit` containing `'`/`$()`/`;` would break out of the single-quoted
  string and run arbitrary shell at build time.
- Data flow: value originates in a consumer's `BUILD.bazel` macro call → Starlark
  string format → genrule `cmd` → shell. The producer of that value is the same
  person authoring the BUILD file.
- Consequence: build-time arbitrary command execution **only** for someone who can
  already author the BUILD file invoking the macro — i.e. they already control the
  Bazel `cmd`/`genrule`/`rust_*` surface and can run arbitrary build actions
  directly. No privilege boundary is crossed; this is not an exploitable injection,
  just a robustness sharp edge (a typo'd `recursion_limit` fails confusingly rather
  than with a clean error). The default `512` is an int and safe.
- Suggested fix (optional hardening, not a vuln fix): coerce/validate
  `recursion_limit` to an int in the macro (`int(recursion_limit)`) before
  interpolation, so a malformed value fails loudly at analysis time. No action
  required from a security standpoint.

## Items explicitly cleared

- Clockwork `local_path_override` + `TODO(fltk-pin-finalize)`: known/intentional
  temporary verification scaffolding (per task framing). Not flagged. Worth noting
  only that it points the build at a local checkout — finalization (push + git pin)
  is already tracked.
- `rules_rust 0.70.0` + download-prebuilt rustc 1.87.0 + crate_universe pyo3/regex
  graph: new build-time supply-chain dependencies, but standard hermetic Bazel
  toolchain mechanism with a checked-in `Cargo.lock`; no new credential or fetch
  surface beyond what `rules_rust` normally does.
- `py_library(imports = ["."])` on `:native_py` and the macro wrapper: standard
  rules_python import-root wiring for the `.so`; does not widen exposure beyond the
  intended module path.
- The pyo3 prelude de-glob + reserved/qualified collision machinery: a robustness
  improvement; closes silent-miscompile (rustc E0255) cases, not a security issue.
- Generated Rust emission: grammar-derived identifiers are constrained by
  `snake_to_upper_camel` + the reserved/claims checks; no untrusted string is
  interpolated into a context where it changes Rust syntax/semantics beyond the
  already-handled struct-name space.

## Verdict

No exploitable security findings. One informational hardening note (security-1).
The change is build-tooling and codegen within a single developer trust domain.
