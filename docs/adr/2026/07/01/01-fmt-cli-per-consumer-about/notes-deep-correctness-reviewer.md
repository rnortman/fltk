# Deep correctness review — fmt-cli-per-consumer-about

Reviewed: `47e4e7b..493f20d` (HEAD 493f20d, "fmt-cli: thread per-consumer --help about text through run_main").

No findings.

Verification performed:
- Read all of `crates/fltk-fmt-cli/src/lib.rs` and the diff to `crates/fltkfmt/src/main.rs` and `TODO.md`.
- `run_main`'s replacement of `FmtArgs::parse()` with `command_with_about(about).get_matches()` + `FmtArgs::from_arg_matches(..).unwrap_or_else(|e| e.exit())` is behaviorally equivalent to `parse()` (which is itself `command().get_matches()` + `from_arg_matches` + `e.exit()`), with only the about/long_about override added. Exit-code semantics (0 on help/version, 2 on usage error) are unchanged.
- The `.long_about(None)` reset compiles and behaves as designed: ran `cargo test` in `crates/fltk-fmt-cli` — all 41 tests pass, including the three new `command_with_about` tests that guard both help forms and arg-parsing invariance.
- End-to-end: built `crates/fltkfmt` and ran the binary; both `--help` and `-h` print "Format FLTK grammar (.fltkg) files." and the usage line shows `fltkfmt` (argv[0]-derived, unaffected).
- Macro arm: `about: $about:expr,` is prepended and `$about` is passed as `run_main`'s first argument, matching the new signature; the field is required (a consumer omitting it gets a macro-match compile error, per design intent).
- `FromArgMatches` is imported for the trait method; `CommandFactory` is used via fully-qualified path — both resolve.
- TODO.md changes are documentation-only (entry swap + one-sentence append); no code paths affected.

The known `--version`-reports-wrong-crate defect is pre-existing, untouched by this diff, and tracked as `fmt-cli-per-consumer-version` — not a finding against this change.
