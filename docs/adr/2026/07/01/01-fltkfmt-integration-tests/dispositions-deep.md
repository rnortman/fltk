# Dispositions — deep review round 1 (fltkfmt integration tests)

Base 9233540d → prior HEAD 2728a782. Reviewer note files: error-handling,
correctness, security, test, reuse, quality, efficiency.

No-findings reviewers: error-handling, correctness, reuse, efficiency (each verified
the change and reported nothing actionable; correctness' sub-threshold nit about a temp
file surviving a *failing* run is subsumed by the security-1 fix, which moves temp files
under `target/`).

## test-1 (== quality-1) — deleted TODO's `--help`/`about` assertion silently dropped

- Disposition: Fixed
- Action: Added `help_shows_consumer_about` (Test 5) in `crates/fltkfmt/tests/cli.rs:333-347`,
  runs `fltkfmt --help` and `-h` via the `run` helper and asserts stdout contains the
  consumer `about` literal `"Format FLTK grammar (.fltkg) files."` (pinned as the `ABOUT`
  const, cli.rs:29-32). Verified against `crates/fltkfmt/src/main.rs:14`; test passes.
- Severity assessment: A future refactor of the `fltk_formatter_main!` → `run_main` →
  `clap` wiring (e.g. planned `fmt-cli-per-consumer-version` work) could regress every
  consumer binary's `--help` text with nothing end-to-end catching it, since the
  `fltk-fmt-cli` unit tests bypass `get_matches()`. This exact assertion was an accepted
  deliverable of the closed TODO.

## security-1 — predictable temp-file names in world-writable temp dir

- Disposition: Fixed
- Action: `temp_file` (cli.rs:82-96) now writes under `env!("CARGO_TARGET_TMPDIR")`
  (Cargo's per-crate integration-test temp dir inside `target/`) instead of
  `std::env::temp_dir()`, removing the shared-`/tmp` symlink/pre-seed vector. Tests pass.
- Severity assessment: Low. Only exploitable on a multi-user host with a shared writable
  `/tmp` and an attacker racing/pre-seeding enumerable pid+counter names; nil on
  single-user dev boxes and per-job CI containers. Fix is cheap and idiomatic for Cargo
  integration tests. (The cited `fltk-fmt-cli` precedent helper is out of this change's
  scope and left untouched.)

## quality-2 — corpus cross-reference was one-directional

- Disposition: Fixed
- Action: Added a back-reference to the `_CORPUS` comment in
  `tests/test_fltkfmt_parity.py` pointing at `crates/fltkfmt/tests/cli.rs` (`CORPUS`),
  completing the two-way cross-reference the design's drift mitigation called for.
- Severity assessment: Low but real — the pytest list is the canonical place to add a
  grammar; without the back-reference the Rust idempotency sweep would silently stop
  covering new grammars (coverage degradation, never a false pass).

## quality-3 — repeated exit-0 assertion boilerplate

- Disposition: Fixed
- Action: Added `run_ok(args, stdin, ctx) -> Vec<u8>` (cli.rs:64-78) wrapping `run` with
  the shared exit-0 assertion + lossy-stderr diagnostic; refactored the pass-1/2/3, golden,
  and trailing-newline success-path invocations to use it. The raw `run` stays for the
  parse-error test (asserts exit 2). Net reduction in duplicated spawn/assert blocks; the
  new `--help` test reuses it. rustfmt + clippy clean; all 5 tests pass.
- Severity assessment: Maintainability only — divergent failure diagnostics across
  copy-pasted blocks; no behavioral impact.
