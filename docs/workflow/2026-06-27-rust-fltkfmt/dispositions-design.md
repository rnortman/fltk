# Dispositions: design review — `fltkfmt` standalone Rust formatter

Design: `docs/workflow/2026-06-27-rust-fltkfmt/design.md`
Notes: `docs/workflow/2026-06-27-rust-fltkfmt/notes-design-design-reviewer.md`
Round: 1

All three findings were fact-checked against source and confirmed accurate. All Fixed.

---

design-1:
- Disposition: Fixed
- Action: Rewrote §3 "Parse failure", §2.2 `run_main` bullet, consistent with §4. The
  design no longer claims `Parser::new(src, filename, true)` makes the filename appear in
  the error message. It now states explicitly that `format_error_message`
  (`crates/fltk-parser-core/src/errors.rs:123-158`) never reads `SourceText.filename`, and
  that `run_main` — which owns the input path — prepends the path to the error string when
  writing to stderr. The §4 "Parse-error path" test assertion (message mentions filename +
  line/col) is now satisfied, because the test exercises the binary/`run_main`, where the
  prefix is applied.
- Severity assessment: As written, the §4 test would have failed against the proposed
  pipeline — `error_message()` emits no filename — and an implementer following §3 would
  have wired filename surfacing to a non-existent mechanism, shipping CLI errors that omit
  the file path when formatting multiple files.

design-2:
- Disposition: Fixed
- Action: Rewrote the §2.3 Makefile bullet. Verified `check-common`'s step list
  (`Makefile:40`) does not include `test-native-parser`/`test-rust-parser-fixture` (those
  targets exist at `Makefile:234-239` but no check target invokes them), and that
  standalone crates are gated via explicit `--manifest-path` lines inside existing
  `check-common` steps. The design now instructs adding
  `--manifest-path crates/fltkfmt/Cargo.toml` to `cargo-test-no-python` (`135-140`),
  `cargo-clippy-no-python` (`142-147`), `check-no-pyo3` (`153-170`), and `cargo-deny`
  (`176-181`), cites the MANDATORY anti-drift rule (`Makefile:27-32`), drops the redundant
  `test-fltk-fmt-cli` target (root workspace already covers `fltk-fmt-cli`), demotes
  `build-fltkfmt` to a non-check convenience target, and notes that clap's tree is
  MIT/Apache-2.0/Unicode-3.0 — all within `deny.toml`'s allow-list (`deny.toml:13-18`),
  with `multiple-versions = "warn"` — with a directive to run `make cargo-deny` to confirm.
- Severity assessment: Following the original §2.3 literally would have produced a binary
  that compiles locally but is invisible to `make check`/CI — its tests, `-D warnings`
  clippy, pyo3-absence proof, and supply-chain gate would all silently skip it, defeating
  the "first consumer proves the scaffolding stays green" goal.

design-3:
- Disposition: Fixed
- Action: Rewrote the §2.1 `lib.rs` bullet to keep `mod cst;` **private** (only
  `pub mod unparser;` is added). Empirically confirmed the change is unnecessary: `cargo
  clippy --manifest-path crates/fegen-rust/Cargo.toml --no-default-features -- -D warnings`
  passes today (exit 0) with `mod cst;` private while `pub mod parser;` exposes
  `apply__parse_grammar -> …Shared<cst::Grammar>`, and there is no `private_interfaces`
  allow anywhere in the tree. The generated `unparser.rs` reaches the CST via
  `use super::cst;` (the fixture does the same, `tests/rust_parser_fixture/src/unparser.rs:9`),
  and the binary's macro names no `cst::` path (type inference only). This removes the
  §2.1↔§2.3 contradiction ("must name CST types" vs "the macro names neither").
- Severity assessment: Low blast radius — making `cst` public is harmless — but the stated
  rationale was unsupported by the design's own approach; left uncorrected it would have
  widened `fegen-rust-cst`'s public Rust surface (per CLAUDE.md, generated output is public
  API) for no reason and on a false premise.
