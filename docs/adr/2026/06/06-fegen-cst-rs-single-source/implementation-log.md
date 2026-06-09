## Increment 1 — replace `tests/rust_cst_fegen/src/cst.rs` with `include!` one-liner + remove duplicate `gencode` step + clean up TODO bookkeeping (commit 5deda26)

- `tests/rust_cst_fegen/src/cst.rs`: replaced 6858-line duplicate with `include!("../../../src/cst_fegen.rs");` (one line).
- `Makefile:108-109`: removed both the `TODO(fegen-cst-rs-single-source)` comment line and the duplicate `$(MAKE) gen-rust-cst ... RS_OUT=tests/rust_cst_fegen/src/cst.rs` step from `gencode`.
- `TODO.md`: removed `## fegen-cst-rs-single-source` entry (was lines 15-17 at HEAD ce8b8f2).
- Build verified: `cd tests/rust_cst_fegen && uv run --group dev maturin develop` succeeded (Rust `include!` compiles correctly).
- 123 consumer tests pass (0 skipped): `test_phase4_fegen_rust_backend.py`, `test_clean_protocol_consumer_api.py`, `test_cross_backend_label_equality.py`.
- `make gencode` verified: `cst.rs` is still the one-liner after regeneration (gencode no longer touches it).
- `make check` passes: all steps (lint, format-check, typecheck, test, cargo-check, cargo-clippy, cargo-test).
- Remaining slug references are in historical ADR docs only — not in live code or build files.
