# Quality review — fmt-cli-per-consumer-about

Reviewed: `47e4e7b..493f20d` (single commit `493f20d`, "fmt-cli: thread per-consumer --help about text through run_main").

Overall: clean, well-scoped increment. The `long_about(None)` reset is correctly handled and
tested, the pre-existing `--version` defect is properly TODO-tracked instead of worked around,
and TODO bookkeeping (both `TODO.md` and code-comment sides) is in sync. Three findings, none
blocking.

## quality-1: `run_main` grows positional `&'static str` params with a second one already scheduled

- **Where:** `crates/fltk-fmt-cli/src/lib.rs:264` (`pub fn run_main<F>(about: &'static str, format_fn: F)`), together with the new `TODO(fmt-cli-per-consumer-version)` at `lib.rs:39-42`.
- **Issue:** This change deliberately breaks `run_main`'s signature to add `about` — and the
  TODO filed in the same commit prescribes threading `version` (and possibly `name`) "the same
  way", i.e. a *second* scheduled breaking change to the same entry point, after which the
  signature is `run_main(about, version, format_fn)`: two adjacent positional `&'static str`
  arguments that the type system cannot tell apart. A consumer that swaps them compiles clean
  and ships a binary whose `--help` prints a version number as its description.
- **Consequence:** The design correctly argues the breaking window is *now* (path-only dep, no
  crates.io consumers, API days old). Spending that window on one string param and then
  re-breaking for the next param wastes it — each future per-consumer knob (`version`, `name`,
  maybe `long_about`) either breaks every consumer again or accretes another indistinguishable
  positional string. This is the parameter-sprawl trajectory at its cheapest moment to stop.
- **Fix:** While the window is open, take a small identity struct instead of a bare string:
  `run_main(info: FormatterInfo, format_fn)` with `FormatterInfo::new(about)` (keeps `about`
  required, per the design's "required, not optional" reasoning) and builder-style setters for
  fields added later — so `fmt-cli-per-consumer-version` becomes a non-breaking
  `.version(env!("CARGO_PKG_VERSION"))` addition, and the macro grows an optional `version:`
  field without a matcher explosion. If the team prefers to defer, at minimum amend the
  `fmt-cli-per-consumer-version` TODO to say the fix should introduce the struct rather than a
  second positional string, so the next increment doesn't cargo-cult "the same way" literally.

## quality-2: negative help-text assertions are keyed to an exact doc-comment string — silent test rot

- **Where:** `crates/fltk-fmt-cli/src/lib.rs:615` and `lib.rs:625`
  (`assert!(!help.contains("Command-line surface shared by every FLTK formatter binary"))` in
  `long_help_shows_consumer_about` / `short_help_shows_consumer_about`).
- **Issue:** The guard against scaffolding prose leaking into consumer help is a hard-coded
  copy of the `FmtArgs` doc comment's first sentence. If anyone rewords that doc comment
  (`lib.rs:28`), the negative assertions become vacuously true: the tests keep passing while no
  longer guarding the `long_about(None)` reset at all. The positive assertions alone would not
  catch a regression where clap renders *both* the consumer about and the (reworded) leaked
  long_about.
- **Consequence:** The one test the design calls load-bearing ("fails if only `.about()` is set
  without the reset") quietly stops testing anything the first time the doc comment is edited —
  a rot mode invisible to CI and to the editor of the doc comment.
- **Fix:** Derive the forbidden string from the derive itself instead of duplicating it, e.g.
  `let default = <FmtArgs as clap::CommandFactory>::command();` then assert
  `!help.contains(&default.get_about().unwrap().to_string())` (and
  `get_long_about()` for the long-help test). Rewording the doc comment then updates the
  assertion automatically. Alternatively, assert `command_with_about(..).get_long_about()` is
  `None` directly — that pins the reset itself rather than one rendering of it.

## quality-3: new `about` param doc merges into the preceding rustdoc paragraph

- **Where:** `crates/fltk-fmt-cli/src/lib.rs:259-261` — the run_main doc comment goes straight
  from "…exit codes — lives here." to "`about` is the one-line description…" with no blank
  `///` line between them.
- **Issue:** Without a paragraph break, rustdoc renders the `about` parameter description glued
  onto the end of the "All grammar-independent behavior…" sentence as one run-on paragraph.
  (The parallel addition on the `FmtArgs` doc comment at `lib.rs:34-37` got the blank `///`
  separator right; this one didn't.)
- **Consequence:** `run_main` is the crate's primary public entry point for out-of-tree
  formatter authors; its rendered docs are the API surface they read. A mangled paragraph here
  is the kind of small erosion that propagates as later params (see quality-1) get doc'd by
  appending to the same blob.
- **Fix:** Insert a `///` blank line before the "`about` is the one-line description…" line
  (or move the parameter description up next to the `format_fn` paragraph, which is where the
  other parameter is documented).

No findings on: redundant state, copy-paste, leaky abstractions, stringly-typing beyond the
inherent string param, observability (CLI stderr/exit-code reporting unchanged and adequate),
workarounds (the `--version` defect is tracked, not papered over), or comment hygiene in the
changed hunks (no design-doc references or changelog comments were introduced; the "preserves
`FmtArgs::parse()`'s UX" comment documents a live behavioral equivalence, not history).
