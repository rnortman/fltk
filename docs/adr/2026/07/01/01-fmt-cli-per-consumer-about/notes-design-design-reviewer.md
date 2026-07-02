# Design review notes: `fmt-cli-per-consumer-about`

Verification scope: every file/line reference and API claim in the design was checked
against the tree at `c03a801` and against the vendored clap 4.6 source
(`~/.cargo/registry/src/.../clap_builder-4.6.0`).

## Verified correct (no findings)

- `run_main` at `crates/fltk-fmt-cli/src/lib.rs:241-251` with `FmtArgs::parse()` at
  line 245; TODO comment at lines 34-37; `FmtArgs` doc comment at 28-33;
  `fltk_formatter_main!` at 282-333 with doc example at 260-267; consumer invocation at
  `crates/fltkfmt/src/main.rs:17-22`; path-only dep at `crates/fltk-fmt-cli/Cargo.toml:16`
  (so no crates.io consumers can exist — publish is impossible with a path dep). All match.
- TODO.md: `fmt-cli-per-consumer-about` entry (line 47) and `fltkfmt-integration-tests`
  entry (line 51) both exist; the two `docs/workflow/2026-06-27-rust-fltkfmt/` mentions
  are historical per the exploration. §5 is accurate.
- clap claims are real, not invented: `Command::long_about(impl IntoResettable<StyledStr>)`
  (clap_builder-4.6.0 `src/builder/command.rs:2002`) accepts a bare `None` (the only
  `Option`-shaped impl is `Option<&'static str>`, `resettable.rs:115-121`, so inference
  resolves and `None` maps to `Resettable::Reset`). Long help renders
  `get_long_about().or_else(get_about())` (`src/output/help_template.rs:315`), so the
  `.long_about(None)` reset genuinely makes `--help` fall back to the consumer's about —
  the design's "load-bearing" analysis in §2 is correct, and test 1's
  claim that the not-contains assertion fails with `.about()` alone is correct (the
  multi-paragraph doc comment becomes `long_about` under derive).
- `render_help`/`render_long_help` exist (`command.rs:1004`, `1037`; `&mut self` on a
  temporary is fine), so the test plan is implementable as written.
- Requirements coverage: request prescribes exactly "thread `about: &'static str` through
  `run_main` and the macro, build via `FmtArgs::command().about(..)`" — §§1-4 cover it,
  §5 covers the TODO-system bookkeeping required by CLAUDE.md. Required-not-optional macro
  field and the breaking-change call-out satisfy the CLAUDE.md public-API rule (deliberate,
  called-out, migration mechanical). Scope is tight; the one addition beyond the TODO's
  literal prescription (`.long_about(None)`) is justified and necessary, not creep.

## Findings

### design-1 — "workspace crates share a version today" is false; the wrong-version symptom the design says doesn't exist, exists

- **Section:** "Edge cases / failure modes", bullet "`--version` reports `fltk-fmt-cli`'s
  version": "...not worsened here; explicitly out of scope (threading `version`/`name` the
  same way is a separate decision nobody has asked for — **workspace crates share a version
  today**)." Repeated in "Open questions": "...resolved as out-of-scope above rather than
  asked, since **nothing today produces a wrong-version symptom** (workspace crates share a
  version)..."
- **What's wrong:** `fltkfmt` is deliberately *not* a root-workspace member
  (`crates/fltkfmt/Cargo.toml:1-5` — its own `[workspace]`) and its version is `0.1.0`
  (`crates/fltkfmt/Cargo.toml:9`), while `fltk-fmt-cli` — where `#[command(version)]`
  expands `CARGO_PKG_VERSION` — is `0.2.0` (`crates/fltk-fmt-cli/Cargo.toml:3`). So
  `fltkfmt --version` already reports `0.2.0` for a `0.1.0` binary today. The
  wrong-version symptom the design claims "nothing today produces" is produced by the one
  consumer that exists.
- **Why (source-backed):** version values above; root `Cargo.toml:7` is `0.2.0` for the
  actual workspace members, which is what the design generalized from.
- **Consequence:** The "Open questions: None" resolution rests on a false premise. The
  scope decision itself is still right — the requirement and TODO are about `about` only,
  and the version mismatch is pre-existing and untouched by this change — but a judge or
  implementer relying on the stated justification would wrongly conclude no version defect
  exists, and the defect then has no tracking trail at all (it is dismissed rather than
  deferred). Under this project's TODO discipline, "known pre-existing defect, consciously
  not fixed" and "no defect" are different outcomes.
- **Suggested fix:** Correct the justification: version threading stays out of scope
  because the requirement/TODO covers `about` only and the mismatch is pre-existing and
  unworsened — not because no symptom exists. State the `0.1.0`/`0.2.0` mismatch honestly
  and either accept it as known or note it as a candidate TODO for the user to decide; do
  not expand this increment's scope.

No other findings.
