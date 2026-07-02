# Exploration: `TODO(fmt-cli-per-consumer-about)`

## TODO text (verbatim, both locations match)

- `TODO.md:89-91` (entry `## \`fmt-cli-per-consumer-about\``)
- `crates/fltk-fmt-cli/src/lib.rs:34-37` (comment directly above `pub struct FmtArgs`)

Both say: "When `run_main`/`fltk_formatter_main!` land, thread a per-consumer `about: &'static str` and build the command via `FmtArgs::command().about(..)` so each binary's `--help` describes the language it actually formats — otherwise `FmtArgs::parse()` inside `run_main` seals one wording in for every consumer."

## Has `run_main` / `fltk_formatter_main!` landed?

Yes. Both exist today in `crates/fltk-fmt-cli/src/lib.rs`:

- `pub fn run_main<F>(format_fn: F) -> ExitCode` — `crates/fltk-fmt-cli/src/lib.rs:241-251`.
- `macro_rules! fltk_formatter_main!` (`#[macro_export]`) — `crates/fltk-fmt-cli/src/lib.rs:282-333`.

They were added by commit `1e9e402` ("rust-fltkfmt: standalone pure-Rust .fltkg formatter binary"), which also added the first (and so far only) consumer: `crates/fltkfmt/src/main.rs`.

## Is the about-threading done?

No — the TODO's precondition ("when `run_main`/`fltk_formatter_main!` land") is now satisfied, but the described fix has not been applied:

- `run_main`'s signature takes only `format_fn: F` (`crates/fltk-fmt-cli/src/lib.rs:241-243`) — no `about` parameter of any kind.
- `run_main`'s body calls `FmtArgs::parse()` directly (`crates/fltk-fmt-cli/src/lib.rs:245`) — exactly the "seals one wording in for every consumer" pattern the TODO warns about.
- `fltk_formatter_main!`'s macro arms accept only `parser`, `unparser`, `parse`, `unparse` (`crates/fltk-fmt-cli/src/lib.rs:284-289`) — no `about` field.
- No `.command()` / `.about(` call exists anywhere in `crates/fltk-fmt-cli/` or `crates/fltkfmt/`. `grep -rn "\.command(\|\.about(\|about:"` over both crates matches only the TODO comment's own prose (lines 36-37 of `lib.rs`), nothing executable.
- `FmtArgs` itself (`crates/fltk-fmt-cli/src/lib.rs:38-63`) still carries only `#[command(version)]`; clap falls back to the struct's doc comment (`lib.rs:28-33`, "Command-line surface shared by every FLTK formatter binary...") as the `--help` `about` text.
- The one real consumer, `crates/fltkfmt/src/main.rs:17-22`, invokes `fltk_fmt_cli::fltk_formatter_main! { parser: ..., unparser: ..., parse: ..., unparse: ... }` with no `about` field — confirming the macro genuinely has no hook yet, and this binary's `--help` shows the generic shared doc-comment text rather than anything naming `.fltkg`/fegen specifically.

## Origin of the TODO

`docs/workflow/2026-06-27-rust-fltkfmt/dispositions-deep.md:37-40` ("quality-2 — Fixed + TODO(fmt-cli-per-consumer-about)") and the matching entry in `judge-verdict-deep.md:37-40` record why it was deferred rather than fixed immediately: a prior diff had baked `about = "Format FLTK grammar files."` into `FmtArgs`, which a reviewer flagged as misleading for out-of-tree consumers (public-API concern per CLAUDE.md). The harmful hardcoded string was removed in that same diff; the disposition explicitly states the remaining threading work "genuinely depends on increment-4 code that does not exist in this diff" (i.e., `run_main`/`fltk_formatter_main!`), so it was deferred and tracked with this slug rather than done on the spot.

That precondition no longer holds: increment landed in `1e9e402`, so the deferred work is now actionable but still outstanding.

## All TODO(fmt-cli-per-consumer-about) occurrences found

1. `TODO.md:89-91` — master list entry.
2. `crates/fltk-fmt-cli/src/lib.rs:34` — code comment above `FmtArgs`.
3. `docs/workflow/2026-06-27-rust-fltkfmt/judge-verdict-deep.md:37` — historical record (section heading), not a live TODO marker.
4. `docs/workflow/2026-06-27-rust-fltkfmt/dispositions-deep.md:105` — historical record (references the TODO comment + TODO.md entry being added), not a live TODO marker.

No other `.rs`/`.py`/`.md` files in the repo reference this slug.
