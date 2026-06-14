# Deep efficiency review — rust-native-lib-shape

Commit reviewed: fltk 7a7ca4d (base 7200d9c); clockwork ea34388 (base 6ede250).

No findings.

Reviewed surface and why nothing applies:

- **`fltk/fegen/gsm2lib_rs.py` / `genparser.py gen-rust-lib`** — the only genuinely new
  logic. It is build-time codegen invoked once per `make gencode`, emitting a few dozen
  lines of lib.rs via straightforward list-append string building. Not a hot path; no
  redundant work, loops, or I/O of concern. Single `output_file.write_text(src)` — operates
  directly, no pre-existence TOCTOU check.

- **`crates/fegen-rust/src/parser.rs`** — verified byte-identical to the pre-existing
  `tests/rust_cst_fegen/src/parser.rs` (diff -q clean). Pure relocation, no new runtime
  logic to review.

- **`crates/fegen-rust/src/cst.rs`, `tests/rust_poc_cst/src/cst.rs`** — git R100 renames of
  `src/cst_fegen.rs` / `src/cst_generated.rs`. Pure relocation.

- **`crates/fegen-rust/src/lib.rs`, `tests/rust_poc_cst/src/lib.rs`,
  `crates/fltk-cst-core/src/py_module.rs`** — `#[pymodule]` registration wiring; runs once
  at module import. No per-request/per-render cost added. The py_module.rs change is a
  TODO comment only.

- **Test files, Makefile, BUILD.bazel, Cargo.toml/lock, .pyi stubs, ADR docs** — not
  runtime; no efficiency surface.

The refactor is deletion + relocation + build-time flag plumbing. Nothing lands on a
startup, per-request, or per-render hot path; no new unbounded structures, no new
sequential-could-be-parallel I/O, no redundant recomputation.
