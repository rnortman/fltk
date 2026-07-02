# Design: `fmt-cli-per-consumer-about` — per-consumer `--help` about text

Requirements: `docs/adr/2026/07/01/01-fmt-cli-per-consumer-about/request.md`
Exploration: `docs/adr/2026/07/01/01-fmt-cli-per-consumer-about/exploration.md`

## Root cause / context

`fltk-fmt-cli` is shared scaffolding: every FLTK formatter binary (in-tree `fltkfmt` today,
out-of-tree grammar formatters by design) gets its CLI from the same `FmtArgs` struct.
clap's `#[derive(Parser)]` bakes the `--help` description into that struct at the library's
compile time, and `run_main` calls `FmtArgs::parse()` directly
(`crates/fltk-fmt-cli/src/lib.rs:245`), so every consumer binary shows the same generic
text — currently the `FmtArgs` doc comment, "Command-line surface shared by every FLTK
formatter binary..." (`lib.rs:28-33`), which describes the scaffolding, not the binary the
user is holding.

The fix was prescribed when the TODO was filed (`TODO.md`, `fmt-cli-per-consumer-about`;
comment at `lib.rs:34-37`): once `run_main`/`fltk_formatter_main!` exist, thread a
per-consumer `about: &'static str` through both and build the command via
`FmtArgs::command().about(..)`. That precondition landed in commit `1e9e402`
(`run_main` at `lib.rs:241-251`, `fltk_formatter_main!` at `lib.rs:282-333`), so the
deferred work is now actionable. The requirements doc commits to doing it.

## Proposed approach

All changes are in `crates/fltk-fmt-cli/src/lib.rs` and `crates/fltkfmt/src/main.rs`,
plus TODO bookkeeping.

### 1. `run_main` gains a required `about` parameter

```rust
pub fn run_main<F>(about: &'static str, format_fn: F) -> ExitCode
where
    F: Fn(&str, Option<&str>, RendererConfig) -> Result<String, String>,
```

`about` is the one-line description shown by `-h`/`--help` (e.g. "Format FLTK grammar
(.fltkg) files."). It replaces the `FmtArgs::parse()` call with an explicitly built
command:

```rust
let matches = command_with_about(about).get_matches();
let args = FmtArgs::from_arg_matches(&matches).unwrap_or_else(|e| e.exit());
```

`get_matches()` keeps the exact `FmtArgs::parse()` UX: it prints help/version and exits 0
on `-h`/`--help`/`--version`, prints a usage error and exits 2 on bad flags.
`from_arg_matches` cannot realistically fail after a successful `get_matches` on a command
built from `FmtArgs` itself; `e.exit()` covers it identically to `parse()`.

### 2. New private, testable helper `command_with_about`

```rust
fn command_with_about(about: &'static str) -> clap::Command {
    <FmtArgs as clap::CommandFactory>::command()
        .about(about)
        .long_about(None)
}
```

The `.long_about(None)` reset is load-bearing. clap's derive maps the first paragraph of
the `FmtArgs` doc comment to `about` and the full multi-paragraph comment to `long_about`;
`--help` prefers `long_about` while `-h` prefers `about`. Overriding only `.about(..)`
would leave `--help` (the form users actually read) still showing the generic scaffolding
prose — the bug half-fixed. Resetting `long_about` makes both `-h` and `--help` show the
consumer's text.

Kept private (not `pub`): consumers go through `run_main`; the helper exists so unit tests
can assert on rendered help without spawning a process or letting clap exit.

The `FmtArgs` derive itself is untouched — same flags, same defaults, same
`#[command(version)]`. The doc comment stays for rustdoc; only the runtime help text is
overridden. The `TODO(fmt-cli-per-consumer-about)` comment block (`lib.rs:34-37`) is
replaced by a short note stating that per-consumer about text is threaded via `run_main`.

### 3. `fltk_formatter_main!` gains a required `about:` field

New arm shape (field first — it names what the binary is):

```rust
fltk_fmt_cli::fltk_formatter_main! {
    about:    "Format FLTK grammar (.fltkg) files.",
    parser:   fegen_rust_cst::parser::Parser,
    unparser: fegen_rust_cst::unparser::Unparser,
    parse:    apply__parse_grammar,
    unparse:  unparse_grammar,
}
```

Matcher: `about: $about:expr,` prepended to the existing arm; expansion passes `$about` as
`run_main`'s first argument. The trailing `$(,)?` stays. No type annotation is needed in
the macro — `run_main`'s `&'static str` parameter enforces the type at the call site with
a normal type error. The macro's doc-comment example (`lib.rs:260-267`) is updated to
show the new field.

**Required, not optional.** An optional field with a fallback would silently reintroduce
the sealed-in generic wording — the exact failure mode this TODO exists to prevent. The
whole point is that a formatter binary must say what language it formats; migration cost
is one line per consumer.

### 4. Update the one consumer

`crates/fltkfmt/src/main.rs:17-22` gains
`about: "Format FLTK grammar (.fltkg) files.",`. This is deliberately the wording that was
once flagged as harmful — it was wrong baked into the *shared crate*, and is exactly right
supplied by the *fegen consumer*.

### 5. TODO bookkeeping

- Delete the `fmt-cli-per-consumer-about` entry from `TODO.md` and the comment at
  `crates/fltk-fmt-cli/src/lib.rs:34-37` (both live occurrences; the two
  `docs/workflow/2026-06-27-rust-fltkfmt/` mentions are historical records and stay).
- Append one sentence to the existing `fltkfmt-integration-tests` entry in `TODO.md`: the
  end-to-end suite should also assert `fltkfmt --help` output contains the fegen about
  string (the macro→`run_main` threading can only be observed end-to-end through a real
  consumer, same as the other cases that TODO defers).
- Add a new TODO `fmt-cli-per-consumer-version`: entry in `TODO.md` plus a
  `TODO(fmt-cli-per-consumer-version)` comment at the `#[command(version)]` attribute on
  `FmtArgs` in `crates/fltk-fmt-cli/src/lib.rs`. Content: every consumer binary reports
  the scaffolding crate's `CARGO_PKG_VERSION` (`fltkfmt`, versioned `0.1.0`, prints
  `0.2.0` today); fix by threading `version` (and possibly `name`) through
  `run_main`/`fltk_formatter_main!` the same way this increment threads `about`. Done =
  `fltkfmt --version` prints `fltkfmt`'s own version. This records the known pre-existing
  defect (see "Edge cases") without expanding this increment's scope.

## Breaking-change assessment (per CLAUDE.md)

Changing `run_main`'s signature and requiring a new macro field breaks any out-of-tree
caller of either. This is deliberate and called out, and the window is right:

- The API is days old (`1e9e402`) and unpublishable as-is: `fltk-fmt-cli` depends on
  `fltk-unparser-core` by path only (`crates/fltk-fmt-cli/Cargo.toml:16`), so no crates.io
  consumers can exist; any out-of-tree use is git/path-pinned and freshly written.
- The TODO was filed at the same review that created `run_main`, precisely so this
  threading would land before the entry-point signature ossified. Deferring further only
  grows the eventual break.
- Migration is mechanical: one added argument / one added macro field per consumer, with a
  compile error pointing at the spot. No type-annotation churn, no renames.

## Edge cases / failure modes

- **`--help` vs `-h` divergence** — handled by `.long_about(None)` (see §2). Without it,
  the two help forms would disagree about what the binary is.
- **Empty `about` string** — compiles and renders help with no description line. This is a
  consumer's deliberate literal; no runtime validation. Not worth a guard.
- **`--version` reports `fltk-fmt-cli`'s version** — `#[command(version)]` expands
  `CARGO_PKG_VERSION` where `FmtArgs` is defined, so every consumer binary reports the
  scaffolding crate's version, not its own. This is an observable defect today, not a
  hypothetical: `fltkfmt` is `0.1.0` (`crates/fltkfmt/Cargo.toml:9`; it is deliberately
  outside the root workspace, with its own `[workspace]`), while `fltk-fmt-cli` is `0.2.0`
  (`crates/fltk-fmt-cli/Cargo.toml:3`), so `fltkfmt --version` prints `0.2.0` for a
  `0.1.0` binary. Pre-existing, orthogonal to `about`, and not worsened here; out of scope
  because the requirement and TODO prescribe threading `about` only — not because no
  symptom exists. Deferred with tracking rather than dismissed: see the new
  `fmt-cli-per-consumer-version` TODO in §5.
- **Usage line binary name** — clap derives the displayed binary name from `argv[0]` at
  parse time, not from the crate name, so usage lines already show `fltkfmt` (or the
  consumer's name). Unaffected.
- **clap error exit codes** — `get_matches()` preserves `parse()`'s behavior (exit 2 on
  usage errors, 0 on help/version). `run_inner` and its exit-code contract are untouched.
- **Existing `FmtArgs::try_parse_from` tests** — unaffected; the derive is unchanged and
  those tests bypass `run_main`.

## Test plan

TDD: the new unit tests are written first and fail against the current code (the helper
and parameter don't exist yet).

New unit tests in `crates/fltk-fmt-cli/src/lib.rs` `mod tests`:

1. `long_help_shows_consumer_about` — `command_with_about("Format Foo files.")
   .render_long_help()` contains `"Format Foo files."` and does **not** contain
   `"Command-line surface shared by every FLTK formatter binary"` (guards the
   `long_about(None)` reset — this assertion fails if only `.about()` is set).
2. `short_help_shows_consumer_about` — same two assertions against `render_help()`.
3. `command_with_about_parses_args_unchanged` — parse
   `["fltkfmt", "--check", "-w", "100", "in.fltkg"]` via
   `command_with_about(..).try_get_matches_from(..)` + `FmtArgs::from_arg_matches`, assert
   the same field values the existing `fmt_args_*` tests check. Guards that the
   `Command` mutation doesn't disturb argument definitions or defaults.

Compile-level coverage: the updated `fltkfmt` invocation is built by the normal
`cargo build`/`make check` gate, proving the new macro arm expands and type-checks with a
real consumer.

End-to-end `--help` output through the actual binary is deferred to the already-tracked
`fltkfmt-integration-tests` increment (see §5) — same reasoning as the macro's other
untestable-without-a-consumer branches.

After implementation: full existing suite (`cargo test -p fltk-fmt-cli`, `make check`)
stays green.

## Open questions

None. The one judgment call surfaced during design — whether to thread `version` the same
way — is resolved as out-of-scope rather than asked: the TODO/requirements scope is
`about` only, and the pre-existing wrong-version symptom (`fltkfmt` `0.1.0` reporting
`0.2.0`) is untouched by this change and tracked as `fmt-cli-per-consumer-version` (§5)
rather than fixed here or silently dismissed.
