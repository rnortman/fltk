# Dispositions: docs/rust-formatter-guide.md review

Round 1. Doc under review: `docs/rust-formatter-guide.md`. Fact-checked against
`crates/fltk-fmt-cli/src/lib.rs`, `crates/fltkfmt/` (Cargo.toml + src/main.rs),
`crates/fegen-rust/` (Cargo.toml, src/lib.rs), `docs/rust-cst-extension-guide.md`, and
`fltk/fegen/genparser.py` (`gen-rust-lib` output verified by running it).

## code-1

- Disposition: Fixed
- Action: Rewrote Step 1 (`docs/rust-formatter-guide.md`, Step 1 / sections 1a–1c) to stop
  deferring the CST-crate skeleton to `docs/rust-cst-extension-guide.md` and instead reproduce
  a complete, correct, formatter-specific skeleton mirroring `crates/fegen-rust`: a full
  `Cargo.toml` with `crate-type = ["cdylib", "rlib"]`, the pyo3-optional feature split, and
  dependencies on `fltk-cst-core` + `fltk-parser-core` + `fltk-unparser-core`; and a full
  `src/lib.rs` with `pub mod parser;` / `pub mod unparser;` and `#[cfg(feature = "python")]`
  gating. Added the explicit note that `parser.rs`/`unparser.rs` `use fltk_parser_core` /
  `fltk_unparser_core` (hence both deps). Removed the inaccurate "lib.rs module wiring via
  gen-rust-lib" attribution; replaced it with a verified caveat that `gen-rust-lib` emits
  private `mod parser;`/`mod unparser;` plus an unconditional `#[pymodule]` and so is NOT
  directly usable — the macro needs `pub mod` and feature-gated pyo3. The cross-reference to
  `docs/rust-cst-extension-guide.md` now points only to background it actually contains.
- Severity assessment: High. A downstream consumer following the linked guide verbatim produced
  a crate that does not compile (unresolved `fltk_parser_core`/`fltk_unparser_core`, missing
  `rlib`, private modules so `my_grammar_cst::parser::Parser` does not resolve). Verified the
  finding is correct and in fact understated: running `gen-rust-lib --unparser` confirmed it
  emits private `mod` (not `pub mod`) and unconditional pyo3 wiring, so it could not have been
  the turnkey generator the original cross-reference implied.

## code-2

- Disposition: Fixed
- Action: Two edits. (1) Step 2 `Cargo.toml` template now includes a `[workspace]` line with a
  rationale comment (mirrors `crates/fltkfmt/Cargo.toml`: the CST dep's default features pull in
  pyo3, so the crate is kept standalone), making artifact location well-defined. (2) The minimal
  end-to-end example now states artifacts land under `crates/my-grammar-fmt/target/` and uses a
  manifest-relative `BIN=crates/my-grammar-fmt/target/release/my-grammar-fmt` for every run
  command (replacing the repo-root `./target/release/...`), with a parenthetical covering the
  member-of-a-parent-workspace alternative.
- Severity assessment: Medium. Copy-pasted run/CI commands for the standalone-workspace layout
  the guide says it mirrors would fail with "no such file", since the binary is under the crate's
  own `target/`, not the repo root.

## code-3

- Disposition: Fixed
- Action: Added a sentence after the parameter table in Step 3 (`docs/rust-formatter-guide.md`)
  stating the four keys must appear in the order `parser`, `unparser`, `parse`, `unparse`, and
  that they are positional (single fixed-order macro arm) despite the keyword labels, so
  reordering produces a macro-match error.
- Severity assessment: Minor. A consumer who reorders the keys (assuming they are named) gets a
  confusing macro-match error rather than a clear signal. Verified against the macro arm at
  `crates/fltk-fmt-cli/src/lib.rs:284-289`.
