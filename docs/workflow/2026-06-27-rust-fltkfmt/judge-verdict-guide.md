# Judge verdict — guide review (docs/rust-formatter-guide.md)

Phase: doc (guide). Base e8eec4c..HEAD c25c459. Round 1.
Doc under review: `docs/rust-formatter-guide.md` (added in this range).
Ground truth: `crates/fltk-fmt-cli/src/lib.rs`, `crates/fegen-rust/` (Cargo.toml, src/lib.rs, src/parser.rs, src/unparser.rs), `crates/fltkfmt/` (Cargo.toml, src/main.rs), `fltk/fegen/genparser.py` + `fltk/fegen/gsm2lib_rs.py`, `docs/rust-cst-extension-guide.md`.
Notes: 1 reviewer file; 3 findings (code-1, code-2, code-3). All dispositioned Fixed. No TODO dispositions.

## Added TODOs walk

None. All three findings are dispositioned Fixed; no TODO(slug) dispositions in this phase. (The TODOs present in `lib.rs:34` and `fltkfmt/src/main.rs:13` are pre-existing in the ground-truth code, not introduced by this doc-only diff, and are outside the review scope.)

## Other findings walk

### code-1 — Fixed (severity: high)
Claim: original Step 1 deferred the CST-crate skeleton to `docs/rust-cst-extension-guide.md`, whose skeleton is `cdylib`-only (no `rlib`), declares only `fltk-cst-core` (not `fltk-parser-core`/`fltk-unparser-core`), uses private `mod cst;` (no `pub mod parser/unparser`), and misattributes `gen-rust-lib`. Consequence: a consumer following the linked guide verbatim gets a crate that does not compile (unresolved `fltk_parser_core`/`fltk_unparser_core`, missing modules) and cannot be used as an rlib dependency. Real consequence, defeats the guide's stated purpose → blocker for a how-to doc.

Action verified against ground truth:
- `crate-type = ["cdylib", "rlib"]` — doc 1b matches `crates/fegen-rust/Cargo.toml:13`.
- Deps on all three core crates — doc 1b matches `fegen-rust/Cargo.toml:23-25`.
- Feature split `default`/`extension-module`/`python` — doc 1b matches `fegen-rust/Cargo.toml:16-18`.
- `mod cst; pub mod parser; pub mod unparser;` + `#[cfg(feature = "python")]`-gated `#[pymodule]` — doc 1c matches `fegen-rust/src/lib.rs:14-27`.
- Section 1a note "parser.rs `use fltk_parser_core`, unparser.rs `use fltk_unparser_core`" — confirmed in `fegen-rust/src/parser.rs` (top `use fltk_parser_core::...`) and `src/unparser.rs` (top `use fltk_unparser_core::...`).
- gen-rust-lib caveat (private `mod`, unconditional `#[pymodule]`) — confirmed accurate against `gsm2lib_rs.py`: line 123 emits `use pyo3::prelude::*;` ungated, line 132 emits private `mod {sub};`, line 153 emits `#[pymodule]` ungated. The doc's "not directly usable" claim is correct.
- Narrowed cross-reference now points only to background the linked guide actually contains (extension-module install at `rust-cst-extension-guide.md:93-106`; pin alternatives path/git/bazel at lines 58-67). Verified present.

Assessment: fix reproduces a complete, correct, formatter-specific skeleton and every reproduced fact checks out against ground truth; the residual cross-reference is accurate. Addresses the consequence fully. Accept.

### code-2 — Fixed (severity: medium)
Claim: build used `cargo build --manifest-path crates/my-grammar-fmt/Cargo.toml` (a standalone-workspace layout, mirroring `crates/fltkfmt`'s own `[workspace]`), but run commands used the repo-root `./target/release/my-grammar-fmt`. Consequence: copy-pasted run/CI commands look in the wrong directory and fail with "no such file"; the binary is under the crate's own `target/`. Real, non-blocking → should-fix.

Action verified: (1) Step 2 `Cargo.toml` template now carries a `[workspace]` line with rationale — consistent with ground truth `crates/fltkfmt/Cargo.toml:5`, which is itself a standalone `[workspace]`, confirming the standalone-workspace premise and pinning artifact location under the crate's own `target/`. (2) The minimal example now states artifacts land under `crates/my-grammar-fmt/target/` and uses `BIN=crates/my-grammar-fmt/target/release/my-grammar-fmt` for every run command, with a parenthetical for the member-of-a-parent-workspace case. Manifest path and binary path are now mutually consistent.

Assessment: fix corrects both ends (makes the workspace explicit so the location is well-defined, and fixes the run paths to match). Accept.

### code-3 — Fixed (severity: minor)
Claim: `fltk_formatter_main!` is a single fixed-order `macro_rules!` arm (`lib.rs:284-289`), so keys are positional despite keyword labels; reordering fails to match. Original doc never stated the order is mandatory. Consequence: a consumer who reorders the keys gets a confusing macro-match error. Real but minor → nit.

Action verified: doc lines 188-190 now state the four keys must appear in order `parser`, `unparser`, `parse`, `unparse`, are positional (single fixed-order arm), and reordering produces a macro-match error. Matches the macro arm at `lib.rs:284-289`. Accept.

## Disputed items

None.

## Approved

3 findings: 3 Fixed verified (code-1 high, code-2 medium, code-3 minor). 0 Won't-Do, 0 TODO.

---

## Verdict: APPROVED

All three Fixed dispositions verified accurate against ground truth (`crates/fegen-rust/Cargo.toml` + `src/lib.rs`, `crates/fltkfmt/Cargo.toml`, `lib.rs:284-289` macro arm, `gsm2lib_rs.py` lib generator). The reproduced skeleton, the corrected build/run paths, and the macro key-order note all match the code.
