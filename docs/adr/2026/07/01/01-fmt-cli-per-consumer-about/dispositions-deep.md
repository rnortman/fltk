# Dispositions — deep review, round 1

Commit with fixes: `ad06d59db220ee4d17c986d6b507c0175bd5dcab` (base `47e4e7b`, prior HEAD `493f20d`).

Six of seven reviewers reported **no findings** (error-handling, correctness, security, test,
reuse, efficiency). All findings below are from the quality reviewer; the reviewer itself marked
them "none blocking."

---

quality-1:
- Disposition: Fixed
- Action: The finding's primary proposal — restructure `run_main(about, format_fn)` into
  `run_main(info: FormatterInfo, format_fn)` now — contradicts the frozen design, which
  deliberately chose a required positional `&'static str about` (design §1) and defers `version`
  as a separate `fmt-cli-per-consumer-version` TODO (§5). Restructuring the public entry-point API
  in respond mode would be redesigning, not responding, and would overreach a `done`-scoped
  increment. I applied the finding's explicit fallback ("at minimum amend the ... TODO"): both the
  `TODO(fmt-cli-per-consumer-version)` code comment (`crates/fltk-fmt-cli/src/lib.rs:39-46`) and
  the matching `TODO.md` entry now instruct the next increment NOT to add a second bare positional
  string and to introduce an identity struct instead. This defuses the future footgun at the point
  where it would actually be committed.
- Severity assessment: No current defect — there is exactly one string param today. The risk is a
  future swap of two adjacent indistinguishable positional strings; the amended TODO prevents that
  next increment from cargo-culting "the same way" into a footgun.

quality-2:
- Disposition: Fixed
- Action: Replaced the hard-coded negative assertions (`!help.contains("Command-line surface
  ...")`) in `long_help_shows_consumer_about` and `short_help_shows_consumer_about`
  (`crates/fltk-fmt-cli/src/lib.rs:606-640`). The forbidden strings are now derived from the
  `FmtArgs` derive itself (`command().get_long_about()` / `get_about()`), so rewording the doc
  comment updates them automatically; the long-help test also directly pins the reset with
  `command().long_about(None).get_long_about().is_none()`. Positive render assertions retained.
  All 41 tests pass.
- Severity assessment: Silent test rot — the load-bearing guard on the `long_about(None)` reset
  would become vacuously true the first time the `FmtArgs` doc comment was reworded, with no CI or
  editor signal. Now rot-proof.

quality-3:
- Disposition: Fixed
- Action: Inserted a blank `///` line before the `about`-parameter paragraph in the `run_main`
  rustdoc (`crates/fltk-fmt-cli/src/lib.rs:260-262`) so it renders as its own paragraph rather than
  glued onto the preceding sentence.
- Severity assessment: Cosmetic rustdoc rendering on the crate's primary public entry point; no
  behavioral impact.
