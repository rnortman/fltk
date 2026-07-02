# Efficiency review notes — fmt-cli-per-consumer-about

Commit reviewed: 493f20d281bcd06944bad3c73dee7b8010bb391a (base 47e4e7b73fbfdd05171326600d4abc835dff5926)

Scope: `crates/fltk-fmt-cli/src/lib.rs`, `crates/fltkfmt/src/main.rs`, `TODO.md`.

## No findings.

Rationale (not findings, context for why the diff is clean on efficiency grounds):

- `run_main` is a process entry point invoked exactly once. The swap from
  `FmtArgs::parse()` to `command_with_about(about).get_matches()` +
  `FmtArgs::from_arg_matches(&matches)` is the same one-time argv parse; clap builds
  the `Command` once. No added cost on any repeated path.
- `command_with_about` constructs the `Command` once per invocation (or once per test).
  No loops, no repeated file reads, no duplicated parsing.
- No new blocking work on a hot path — there is no per-request/per-render/per-item loop
  in this diff; the format pipeline (`run_inner`) is untouched.
- No new data structures, allocations in loops, listeners, or unbounded growth. `about`
  is a `&'static str` threaded by value.
- No concurrency opportunity missed: the work is inherently sequential single-shot arg
  parsing.
