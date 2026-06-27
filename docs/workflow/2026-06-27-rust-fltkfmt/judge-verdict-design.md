# Judge verdict — design review

Phase: design. Doc: `docs/workflow/2026-06-27-rust-fltkfmt/design.md`. Round 1.
Notes: 1 reviewer file (design-reviewer); 3 findings. All dispositioned Fixed.

## Other findings walk

### design-1 — Fixed
Claim: §3/§4 asserted the parse-error path surfaces the filename via `Parser::new(src, filename, true)`; the mechanism does not exist — `Parser::error_message()` routes through `format_error_message` which never reads the filename, so the §4 "message mentioning the filename" assertion would fail.
Consequence: real — test fails; CLI errors omit the file path across multiple inputs.
Source check: `crates/fltk-parser-core/src/errors.rs:123-158` — `format_error_message(tracker, terminals, rule_names)` takes no filename, emits `"Syntax error at line {} col {}:\n…\n^\nExpected:\n…"`. Confirmed: filename never read.
Fix verified: current §3 (design.md:233-240) and §2.2 `run_main` bullet (127-135) now state explicitly that `format_error_message` does NOT read `SourceText.filename`, and that `run_main` — which owns the input path — prepends `"<path>: "` to the `Err` string before stderr. §4 (294) reworded to "(synthetic) filename" surfaced by the binary/`run_main`, which is now consistent with the prepend mechanism.
Assessment: finding valid; fix relocates the responsibility to the component that actually has the path, internally consistent and correct against source. Accept.

### design-2 — Fixed
Claim: §2.3 said new crates get gated by wiring into a `check` aggregation "that already runs `test-native-parser` / `test-rust-parser-fixture`" — false; `check`→`check-ci`→`check-common`, whose step list does not include those targets. A standalone-workspace crate is invisible to root `cargo test/clippy/deny` and must be added via explicit `--manifest-path` lines.
Consequence: real — `fltkfmt` would compile locally but skip CI/`make check` entirely (tests, `-D warnings` clippy, pyo3-absence proof, supply-chain).
Source check: `Makefile:40` `check-common` steps = `lint format-check typecheck test cargo-check cargo-clippy cargo-test cargo-test-python-features cargo-test-no-python cargo-clippy-no-python check-no-pyo3` — `test-native-parser`/`test-rust-parser-fixture` absent. Standalone crates gated via `--manifest-path` in cargo-test-no-python (135-140), cargo-clippy-no-python (142-147), check-no-pyo3 (153-170), cargo-deny (176-181). Anti-drift rule at 27-32. All confirmed.
Fix verified: current §2.3 (design.md:183-204) drops the false "already runs …" claim, instructs adding `--manifest-path crates/fltkfmt/Cargo.toml` to exactly those four targets, cites the anti-drift rule, drops the redundant `test-fltk-fmt-cli` (root workspace covers `fltk-fmt-cli`), demotes `build-fltkfmt` to non-check, and flags the clap/cargo-deny license question with a directive to run `make cargo-deny`.
Assessment: finding valid; fix matches the actual gating pattern line-for-line. Accept.

### design-3 — Fixed
Claim: §2.1's rationale for `pub mod cst` ("must name CST types across the crate boundary") contradicts §2.3's "the macro names neither"; inference-only use of an unnameable downstream type compiles, so widening `cst` to `pub` rests on a false premise and needlessly expands the public Rust surface (CLAUDE.md: generated output is public API).
Consequence: real but low blast radius — surface widening on an unsupported rationale.
Source check: `crates/fegen-rust/src/lib.rs:14-15` — `mod cst;` private, `pub mod parser;`. The crate is already exercised by `cargo-clippy-no-python` (Makefile:146 runs the exact `--manifest-path crates/fegen-rust/Cargo.toml --no-default-features -- -D warnings`) inside `check-common`, so "compiles clean with `cst` private" is backed by existing green infra, not a forward promise.
Fix verified: current §2.1 (design.md:70-84) keeps `mod cst;` private, adds only `pub mod unparser;`, routes the generated unparser to the CST via `use super::cst;` (sibling-module visibility, fixture precedent at `tests/rust_parser_fixture/src/unparser.rs:9`), states the macro names no `cst::` path (inference only), and explicitly says widening to `pub` is unnecessary. Contradiction removed.
Assessment: finding valid; fix resolves the §2.1↔§2.3 contradiction in the direction that keeps the public surface minimal, consistent with CLAUDE.md. Accept.

## Disputed items

None. All three findings have real consequences, and all three Fixed rewrites address the comment and check out against source.

## Approved

3 findings: 3 Fixed verified.

---

## Verdict: APPROVED

All dispositions acceptable. Three valid findings, three correct Fixes, each source-backed (errors.rs:123-158; Makefile:40 / 135-181; lib.rs:14-15 + clippy gate at Makefile:146).
