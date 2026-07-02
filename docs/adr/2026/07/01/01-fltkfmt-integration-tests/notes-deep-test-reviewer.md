# Deep test-reviewer notes — `fltkfmt` integration tests

Base `9233540d0` → HEAD `2728a78246`. Reviewed `crates/fltkfmt/tests/cli.rs` (new, 300
lines), the golden fixture, `TODO.md`, and `crates/fltkfmt/src/main.rs`. Ran
`cargo test -q --manifest-path crates/fltkfmt/Cargo.toml`: all 4 new tests pass against the
real binary. Cross-checked the `CORPUS` list in `cli.rs` against `tests/test_fltkfmt_parity.py`'s
`_CORPUS` — identical 8 entries, same order. Confirmed the committed golden fixture is
byte-identical to `fltk/fegen/fegen.fltkg` as the design claims.

All four tests specified by the design are present, each asserts real byte-level or
exit-code/stderr-content behavior (no vacuous "didn't throw" assertions), and each is tied
to a documented, verified contract (idempotency modulo the one pinned carve-out, golden
bytes, trailing-newline collapse behavior, exit-2 + filename + line/col skeleton). The
non-idempotency carve-out is handled well: it pins today's exact behavior with `assert_ne!`
so a future formatter fix trips the test and forces removal of the carve-out, rather than
silently masking a regression.

## test-1

- File: `crates/fltkfmt/tests/cli.rs` (new file; TODO.md, `crates/fltkfmt/src/main.rs`)
- Summary: The prior `TODO(fltkfmt-integration-tests)` entry being deleted by this diff
  explicitly asked for an end-to-end assertion that `fltkfmt --help` contains the
  per-consumer `about` string ("since the macro→`run_main` `about` threading can only be
  observed end-to-end through a real consumer"), but the new test suite — whose whole
  premise is "this is the only place [macro behavior] runs against a real
  Parser/Unparser"/real binary — has no test that invokes `fltkfmt --help` or `-h` at all.
  `command_with_about` is unit-tested in `crates/fltk-fmt-cli/src/lib.rs`
  (`long_help_shows_consumer_about`, `short_help_shows_consumer_about`), but only by calling
  the function directly, not through `run_main`'s `get_matches()` → real `clap::Command`
  parse → real process stdout path, which is exactly the gap the deleted TODO called out.
  The design (`docs/adr/2026/07/01/01-fltkfmt-integration-tests/design.md`) silently drops
  this ask: it lists "No changes to `crates/fltkfmt/src/main.rs`... no changes to
  `fltk-fmt-cli`" as an explicit non-change but never mentions the `--help` requirement or
  says why it's out of scope.
- Failure scenario: A future change to `run_main`'s `get_matches()`/`command_with_about`
  wiring (e.g. the `TODO(fmt-cli-per-consumer-version)` work already planned in `TODO.md`,
  which touches this exact code path) could break the real end-to-end `--help`/`-h` output
  for every consumer binary — printing the wrong description or the generic scaffolding
  text — while `long_help_shows_consumer_about`/`short_help_shows_consumer_about` keep
  passing (they call `command_with_about` directly, bypassing `run_main`/`get_matches()`
  entirely) and no test in `crates/fltkfmt/tests/cli.rs` would notice, since none of the
  four new tests run `fltkfmt --help` or `-h`.
- Fix: Add a fifth assertion (either a new `#[test]` or appended to an existing one) that
  runs `fltkfmt --help` (and/or `-h`) via the same `run()` helper already in `cli.rs` and
  asserts stdout contains `"Format FLTK grammar (.fltkg) files."`, closing the exact gap
  the deleted TODO text called out. If the reviewer/author judge this out of scope for this
  increment, the design should say so explicitly rather than the requirement disappearing
  when the TODO section is deleted.

No other findings. Coverage of the four specified tests is solid; no vacuous assertions,
no over-mocking (deliberately drives a real subprocess), no brittle implementation-detail
assertions (byte-content and exit-code/stderr-substring checks track the actual documented
contract), and cleanup/parallelism (unique temp file names, read-only corpus access) is
handled correctly.
