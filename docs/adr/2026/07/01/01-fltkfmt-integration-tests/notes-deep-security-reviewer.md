# Security review — fltkfmt integration tests

Commit reviewed: 2728a78246ccadcb6c34b1430188603ef82bcf28 (base 9233540d088029885498a4d19a9fc70f12a11c71)
Scope: `crates/fltkfmt/tests/cli.rs` (new), `crates/fltkfmt/tests/golden/fegen.fltkg.golden` (new), `crates/fltkfmt/src/main.rs` (comment deletion), `TODO.md`, one docs file.

Overall: this is a pure test addition. No new runtime/product surface, no untrusted input reaching product code (all test inputs are fixed byte literals or repo-committed files), no network, no secrets, no new dependencies, no auth surface. The subprocess invocations use a Cargo-injected compile-time binary path (`env!("CARGO_BIN_EXE_fltkfmt")`) and fixed argv arrays — no shell, no injection vector. The golden fixture is inert data. The regeneration command in the failure message is human-directed documentation, not executed code.

One finding, test-infrastructure-only and low stakes:

## security-1 — Predictable temp-file names in world-writable temp dir, written with a symlink-following API

- **File:line**: `crates/fltkfmt/tests/cli.rs:60-73` (`temp_file` helper; used by `parse_errors_report_filename_and_position`, cli.rs:281-283).
- **Issue**: Temp files are created as `std::env::temp_dir()` + `fltkfmt-cli-{tag}-{pid}-{counter}.fltkg` and written with `std::fs::write`. On Linux, `temp_dir()` is typically the shared, world-writable `/tmp`; `std::fs::write` opens with `O_CREAT|O_TRUNC` (no `O_EXCL` / `O_NOFOLLOW`), so it follows a pre-existing symlink at that path. Pid + counter is enumerable, not random (CWE-377 insecure temp file, enabling CWE-59 link following).
- **Trust boundary / data flow**: the "untrusted input" is the shared `/tmp` namespace on a multi-user machine — another local user can pre-create entries at the predictable paths before/while the test suite runs. The path is then consumed by `std::fs::write` in the test process and passed to the `fltkfmt` subprocess.
- **Consequence**: on a shared dev/CI host, a local attacker who pre-plants a symlink at a predicted name (`/tmp/fltkfmt-cli-bad-start-<pid>-0.fltkg`, pids are enumerable and the counter starts at 0) gets any file writable by the test-running user truncated and overwritten with the fixed test bytes — data destruction / file clobbering of the developer's or CI user's files. Content is attacker-independent, so this is clobbering, not code injection. Preconditions: multi-user host with shared `/tmp` and an attacker racing or pre-seeding names; on single-user dev boxes and per-job CI containers the risk is nil. A pre-planted regular file or directory can also flakily fail or skew the test itself.
- **Suggested fix**: write test temp files under `env!("CARGO_TARGET_TMPDIR")` (Cargo provides it specifically for integration tests; it lives under the project's `target/`, not the shared system temp dir), falling back to the current naming inside it. Alternatively keep `temp_dir()` but open with `OpenOptions::new().write(true).create_new(true)` so a pre-existing file/symlink fails loudly instead of being followed. Note the same pattern exists in `fltk-fmt-cli`'s test helper that this design cites as precedent; fixing both keeps the idiom consistent.

No other findings.
