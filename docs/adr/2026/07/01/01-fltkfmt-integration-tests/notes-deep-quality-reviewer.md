# Deep quality review — fltkfmt integration tests

Reviewed: `9233540..2728a78` (HEAD 2728a78246ccadcb6c34b1430188603ef82bcf28)

## quality-1: Closed TODO's `--help`/`about` assertion silently dropped

- **Where:** `TODO.md` (deleted `## fltkfmt-integration-tests` section) vs `crates/fltkfmt/tests/cli.rs` (no `--help` test).
- **Issue:** The deleted TODO entry explicitly specified a fifth assertion: "The suite
  should also assert `fltkfmt --help` output contains the fegen `about` string ('Format
  FLTK grammar (.fltkg) files.'), since the macro→`run_main` `about` threading can only be
  observed end-to-end through a real consumer." The design doc never mentions this item and
  the implementation doesn't include it — the TODO was closed with one of its specified
  deliverables silently dropped, with no decision trail. The `fltk-fmt-cli` unit tests
  (`long_help_shows_consumer_about` etc.) cover `command_with_about` with a stub string,
  but the `fltk_formatter_main!` → `run_main` threading of *fltkfmt's own* `about` literal
  is exactly the part only a real consumer binary can observe.
- **Consequence:** Two-fold. (1) TODO-system integrity: TODO.md entries are the record of
  accepted deferrals; closing one while quietly shedding part of its scope trains future
  readers not to trust closures — the whole point of slug-keyed TODOs is that "done" is
  checkable. (2) Coverage: a future macro refactor (e.g. the planned
  `fmt-cli-version-reporting` fix, which will rework this exact threading into a
  `FormatterInfo` struct) can regress every consumer's `--help` text and nothing end-to-end
  will catch it.
- **Fix:** Add a small fifth test to `cli.rs` (`help_shows_consumer_about`): run
  `fltkfmt --help`, assert exit 0 and stdout contains
  `"Format FLTK grammar (.fltkg) files."`. ~10 lines, no new machinery — the `run` helper
  already does everything needed.

## quality-2: Corpus cross-reference is one-directional

- **Where:** `crates/fltkfmt/tests/cli.rs:76-78` (`CORPUS` comment) vs
  `tests/test_fltkfmt_parity.py:39-41` (`_CORPUS` comment — untouched by this change).
- **Issue:** The design (§2.2, mitigation in §3) called for "a comment on each list
  cross-references the other." Only the Rust side got one ("if you add a grammar there,
  add it here too"); the pytest `_CORPUS` comment still says nothing about the Rust twin.
- **Consequence:** The pytest list is the canonical one ("every real `.fltkg` in the
  tree") and the natural place someone adds a new grammar. Without a back-reference, the
  Rust idempotency corpus silently stops covering new grammars — the exact drift mode the
  design's own mitigation was supposed to prevent, defeated by implementing only half of it.
- **Fix:** One line appended to the `_CORPUS` comment in `tests/test_fltkfmt_parity.py`,
  e.g. "Mirrored by hand in `crates/fltkfmt/tests/cli.rs` (`CORPUS`); additions here must
  be added there too."

## quality-3: Repeated exit-0 assertion boilerplate in `cli.rs`

- **Where:** `crates/fltkfmt/tests/cli.rs` — six near-identical blocks:
  pass-1/pass-2/pass-3 in `format_format_is_format`, the golden test, and the four
  `run(...)` + `assert_eq!(code, 0, "... exited {code}: {stderr}")` blocks in
  `trailing_newline_handling_is_stable`.
- **Issue:** Copy-paste with slight variation: every success-path invocation repeats the
  same spawn/assert/lossy-stderr pattern, differing only in the context string. ~70 of the
  file's 300 lines are this boilerplate.
- **Consequence:** Each new test (e.g. the quality-1 `--help` test, or future corpus/config
  additions) copies the block again; a later improvement to failure diagnostics (say,
  including stdout too) must be applied in six-plus places or the tests drift in how they
  report failures.
- **Fix:** Add `fn run_ok(args: &[&str], stdin: Option<&[u8]>, ctx: &str) -> Vec<u8>` that
  wraps `run`, asserts exit 0 with the shared message shape, and returns stdout. The raw
  `run` stays for the parse-error test, which asserts exit 2.
