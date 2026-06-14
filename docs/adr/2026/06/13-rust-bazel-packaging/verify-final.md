# Final Verification — Rust/Bazel Packaging

**Verdict: GREEN**

Date: 2026-06-13

Repos / HEADs:
- fltk: `/home/rnortman/src/fltk` — HEAD `332742a`
- Clockwork: `/home/rnortman/tps/clockwork` — HEAD `ed3d9f0` (temporary `local_path_override` → local fltk working tree)

## Per-check results

### 1. fltk gate (`make check`) — PASS
- `check-common`: all steps passed (lint, format-check, typecheck, test, cargo-check,
  cargo-clippy, cargo-test, cargo-test-python-features, cargo-test-no-python,
  cargo-clippy-no-python, check-no-pyo3).
- `check`: all steps passed (check-ci + cargo-deny).

### 1b. Gencode drift (`make gencode` → `git status`) — CLEAN
- `make gencode` exit 0.
- `git status --porcelain` shows **no** modified/tracked generated source files.
- Only untracked entries are new `docs/adr/2026/06/13-rust-bazel-packaging/*.md`
  artifacts (review/design notes), not generated code. Zero gencode drift.

### 2. Clockwork roundtrip (`bazel test //clockwork/dsl:clockwork_rust_roundtrip_test`) — PASS
- Built from Clockwork workspace. Exit 0.
- `Executed 1 out of 1 test: 1 test passes.`
- (Benign "test size too big" timeout note only.)

### 3. fltk smoke (`bazel build @@fltk+//:bootstrap_rust_srcs`) — PASS
- The `@@fltk+` repo is only defined in the Clockwork workspace context, so the
  build was run from `/home/rnortman/tps/clockwork`. (Running it from the fltk
  workspace yields `Repository '@@fltk+' is not defined`, which is expected — that
  canonical repo name belongs to the Clockwork module graph, not fltk standalone.)
- `Build completed successfully`. Produced `bootstrap_rust_srcs/cst.rs` and
  `parser.rs`.
- Warnings only (pre-existing, non-fatal): `SyntaxWarning: invalid escape sequence`
  in `genparser`, and `UserWarning: fltk._native could not be loaded; falling back
  to pure-Python Span backend`. No errors.

## Summary
All three checks green. No gencode drift. No fixes applied.
