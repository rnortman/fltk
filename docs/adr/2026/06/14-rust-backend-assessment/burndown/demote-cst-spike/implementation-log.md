# Implementation Log — demote-cst-spike

## Increment 1 — fold spike into tests/rust_poc_cst, delete crates/fltk-cst-spike/ (commit ad7174d)

- `tests/rust_poc_cst/src/spike_tests.rs`: ported verbatim from `crates/fltk-cst-spike/src/spike_tests.rs` (git detects the rename); 43 tests, all pass under `--no-default-features` (python-off lane verified).
- `tests/rust_poc_cst/src/lib.rs`: added `#[cfg(test)] mod spike_tests;` declaration.
- `crates/fltk-cst-spike/`: deleted in full via `git rm -r` — Cargo.toml, benches/traverse.rs (per user directive, not relocated), src/cst.rs, src/lib.rs, src/spike_tests.rs.
- `Cargo.toml` ([workspace] members): removed `"crates/fltk-cst-spike"`.
- `Cargo.lock`: updated by `cargo check`.
- `Makefile`: removed `cargo test -q -p fltk-cst-spike` from `cargo-test-no-python`; removed two `cargo clippy -q -p fltk-cst-spike` lines from `cargo-clippy-no-python`; removed the `cp tests/rust_poc_cst/src/cst.rs crates/fltk-cst-spike/src/cst.rs` line from `gencode`; removed the fltk-cst-spike positive-control block from `check-no-pyo3` (the remaining checks exercise the same invariant via fltk-cst-core and rust_poc_cst).
- `MODULE.bazel`: removed `TODO(bazel-cst-spike-hub)` comment; updated membership note to reflect spike is gone.
- `deny.toml`: removed `fltk-cst-spike` from the `[licenses.private]` comment.
- `TODO.md`: removed the `bazel-cst-spike-hub` entry entirely. Resolves `TODO(bazel-cst-spike-hub)`.
- Build verification: `make cargo-test-no-python`, `make cargo-clippy-no-python`, `make check-no-pyo3`, `make cargo-test`, `make cargo-clippy` — all pass.
- `criterion` dev-dep is gone with the crate; no longer leaks into downstream Bazel hub.

