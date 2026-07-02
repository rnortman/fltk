# Judge verdict — deep review

Phase: deep. Base 9233540d088029885498a4d19a9fc70f12a11c71..HEAD dfda2d95141cfbdee3ec2b799ca1c7bde9bd8e0e. Round 1.
Notes: 7 reviewer files (error-handling, correctness, security, test, reuse, quality, efficiency); 4 distinct findings (test-1 == quality-1), 4 no-findings reviewers.

## Added TODOs walk

### TODO(formatter-group-idempotency) at crates/fltkfmt/tests/cli.rs:141

Not a disposition of a deep-review finding — design-specified (design.md §2.2, flagged in §5) — but it is an added TODO in this diff, so scored.

Q1 (worth doing): yes — real formatter non-idempotency bug (`rust_parser_fixture.fltkg` at 40/4 re-breaks a grouped alternation between passes), present in both backends per single-pass parity; correctness reviewers independently confirmed the carve-out logic.
Q2 (design/owner input required): yes — fixing it changes formatter output in both backends, which is observable behavior for out-of-tree consumers per CLAUDE.md; a cross-backend layout change needs its own design cycle, not a drive-by inside a test addition. The bug pre-exists this iteration (discovered, not created), so the cannot-silently-defer clause does not apply — and it is not silent: the `assert_ne!` pin trips loudly on any fix, forcing carve-out + TODO removal.
Slug hygiene: `TODO.md:26` entry and code comment both present and in sync; old `fltkfmt-integration-tests` slug fully removed from code and TODO.md.
Assessment: TODO acceptable.

## Other findings walk

### test-1 / quality-1 — Fixed
Claim: the deleted `TODO(fltkfmt-integration-tests)` explicitly required an end-to-end `fltkfmt --help` assertion on the consumer `about` string; the suite dropped it silently. Consequence: a future `fltk_formatter_main!` → `run_main` → `get_matches()` refactor (e.g. the planned `fmt-cli-per-consumer-version` work) could regress every consumer's `--help` text with the `fltk-fmt-cli` unit tests still green (they call `command_with_about` directly).
Evidence: `help_shows_consumer_about` added at cli.rs:307-317 — runs both `--help` and `-h` through the real subprocess via `run_ok`, asserts stdout contains the `ABOUT` const (cli.rs:32), which matches `crates/fltkfmt/src/main.rs:14` (`about: "Format FLTK grammar (.fltkg) files."`) exactly. (Dispositions cite cli.rs:333-347; lines drifted, test is present and correct.) Test passes at HEAD.
Assessment: fix closes exactly the gap both reviewers named, at the end-to-end layer they required. Accept.

### security-1 — Fixed
Claim: `temp_file` wrote pid+counter-predictable names under `std::env::temp_dir()` with symlink-following `std::fs::write` (CWE-377/CWE-59); consequence: file clobbering on shared multi-user hosts.
Evidence: `temp_file` (cli.rs:83-95) now roots paths at `env!("CARGO_TARGET_TMPDIR")` — the reviewer's own first-choice fix, per-crate under `target/`, removing the shared-`/tmp` pre-seed/symlink vector. Doc comment records the rationale. Responder's low-severity call matches the reviewer's stated preconditions (nil on single-user boxes / per-job CI). Leaving the analogous `fltk-fmt-cli` helper untouched is defensible: reviewer offered it as a consistency note, it is pre-existing code outside this change's scope, and the finding's consequence attached to the new code.
Assessment: fix addresses the consequence via the suggested mechanism. Accept.

### quality-2 — Fixed
Claim: design's corpus-drift mitigation required cross-references on both lists; only the Rust side had one. Consequence: new grammars added to the canonical pytest list silently escape the Rust idempotency sweep.
Evidence: diff 2728a78..HEAD adds the back-reference to `tests/test_fltkfmt_parity.py` `_CORPUS` comment ("Mirrored by hand in `crates/fltkfmt/tests/cli.rs` (`CORPUS`); additions here must be added there too…"). Two-way now complete.
Assessment: exactly the one-line fix asked for. Accept.

### quality-3 — Fixed
Claim: six near-identical spawn/assert-exit-0/lossy-stderr blocks; consequence: diagnostic drift and copy-paste growth as tests are added.
Evidence: `run_ok(args, stdin, ctx) -> Vec<u8>` added at cli.rs:68-77; all success-path invocations in tests 1, 2, 3, and the new test 5 funnel through it; raw `run` retained solely for the exit-2 parse-error test, as the reviewer specified. Duplicated blocks eliminated (diff: 121 changed lines in cli.rs, net structure matches the proposed shape).
Assessment: fix implements the suggested helper and applies it everywhere applicable. Accept.

## Disputed items

None.

## Approved

4 findings: 4 Fixed verified (test-1/quality-1 counted once), 0 Won't-Do, 1 added TODO acceptable (design-specified carve-out). Suite verified green at HEAD: `cargo test -q --manifest-path crates/fltkfmt/Cargo.toml` — 5/5 pass.

---

## Verdict: APPROVED

All dispositions verified against the code at HEAD dfda2d95; the sole added TODO passes both rubric questions with slug entries in sync.
