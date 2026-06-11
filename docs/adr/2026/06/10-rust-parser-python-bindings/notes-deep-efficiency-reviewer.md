# Efficiency review — Phase 3 Python bindings + parity (b668897..b107645)

Scope reviewed: `fltk/fegen/gsm2parser_rs.py` (`_gen_python_bindings`), generated bindings in
`tests/rust_cst_fegen/src/parser.rs` and `tests/rust_parser_fixture/src/parser.rs`,
`tests/rust_parser_fixture/{Cargo.toml,src/lib.rs}`, `tests/parser_parity.py`,
`tests/test_rust_parser_bindings.py`, `tests/test_rust_parser_parity_{fegen,fixture}.py`, `Makefile`.

Verified non-issues (no finding):
- `check_pos` per `apply__` call is O(1): `TerminalSource::len()` is arithmetic on `cp_to_byte.len()` (crates/fltk-parser-core/src/terminalsrc.rs:88).
- Canonicalization is root-only and registry-deduped (`to_py_canonical`, tests/rust_cst_fegen/src/cst.rs:432) — no eager deep tree conversion per apply call.
- Fixture parity tests cache the two plumbing-generated parser classes in module globals (tests/test_rust_parser_parity_fixture.py:28-40) — the expensive codegen runs at most twice per session, not per test.
- `rule_names` fresh-list-per-access and GIL-held-during-parse are explicitly dispositioned in the design (§2.1, §3); not re-raised.
- `PyApplyResult.result` uses `clone_ref` (refcount bump), `PyParser::new(text: &str)` copies the input once into `SourceText` — both minimal.

## Findings

### efficiency-1: `cargo-check` lines redundant with same-feature `cargo-clippy` lines in `make check`

- File: `Makefile:43` (`cargo check -q --manifest-path tests/rust_parser_fixture/Cargo.toml --features python`), in combination with `Makefile:51` (`cargo clippy` same manifest, same `--features python`, `-D warnings`). Same pattern for `tests/rust_cst_fegen` (`Makefile:42` vs `Makefile:50`).
- Problem: `cargo clippy -D warnings` is a strict superset of `cargo check` — it type-checks and fails on compile errors. `make check` runs both lanes (`Makefile:10`), so each fixture crate (and its path-dep workspace members `fltk-cst-core`/`fltk-parser-core`) is type-checked twice at the identical feature set per gate run; clippy fingerprints workspace members differently, so the second pass does not reuse the first's artifacts.
- Consequence: duplicated compile work on every `make check` / CI run — roughly the python-on check time of two crates plus their local deps added to the canonical precommit gate, recurring forever and growing as the generated parsers grow. Bites on every commit, not at runtime.
- Fix: drop the per-fixture `cargo check` lines that are feature-identical to a `cargo-clippy` line (keep `cargo-check` runnable standalone for fast iteration if desired, but `make check` should not execute both for the same crate+features). Alternatively have the `check` target skip `cargo-check` when `cargo-clippy` is in the step list.
- Note: mirrors a pre-existing root-workspace pattern (`Makefile:41` vs `Makefile:49`), but this change extends it to two more crates; fixing all three is the same one-line-per-crate edit.

No other findings.
