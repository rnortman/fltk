# Deep error-handling review: fmt-cli-per-consumer-about

Commit reviewed: 493f20d281bcd06944bad3c73dee7b8010bb391a (base 47e4e7b73fbfdd05171326600d4abc835dff5926)
Scope: crates/fltk-fmt-cli/src/lib.rs, crates/fltkfmt/src/main.rs, TODO.md

## Findings

No findings.

## Notes (why the changed error paths are sound)

- `run_main` (lib.rs:273): `FmtArgs::from_arg_matches(&matches).unwrap_or_else(|e| e.exit())`
  is not a swallowed error. `clap::Error::exit()` prints the error to stderr and terminates
  with the proper exit code (returns `!`), so the failure is both reported and responded to.
  This is behaviorally identical to the prior `FmtArgs::parse()`, which uses the same pattern
  internally. `get_matches()` on the preceding line handles `-h`/`--help`/`--version` and
  usage errors by printing and exiting (0 / 2) as before. Exit-code contract unchanged.
- The `.unwrap()` at lib.rs:636 is test code on a value just constructed in-test; not a
  production input path.
- No new `?` propagation, no empty catch, no broad catch, no default-on-error fallback,
  no match/enum changes. The clap derive (`FmtArgs`) is untouched.
