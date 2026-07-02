# Dispositions: design review round 1 — `fmt-cli-per-consumer-about`

Notes: `docs/adr/2026/07/01/01-fmt-cli-per-consumer-about/notes-design-design-reviewer.md`
Design: `docs/adr/2026/07/01/01-fmt-cli-per-consumer-about/design.md`

design-1:
- Disposition: Fixed
- Action: Finding fact-checked and confirmed against source: `crates/fltkfmt/Cargo.toml`
  declares its own `[workspace]` (lines 1-5) and `version = "0.1.0"` (line 9), while
  `crates/fltk-fmt-cli/Cargo.toml:3` is `version = "0.2.0"` and the root workspace
  (`Cargo.toml:7`) is `0.2.0` — so `fltkfmt --version` really does print `0.2.0` for a
  `0.1.0` binary today, and the design's "workspace crates share a version" premise was
  false (generalized from the root workspace members, missing that `fltkfmt` is
  deliberately excluded). Three design edits applied:
  1. "Edge cases / failure modes", `--version` bullet — rewritten to state the
     `0.1.0`/`0.2.0` mismatch honestly with Cargo.toml citations; out-of-scope
     justification corrected to the true grounds (requirement/TODO prescribe `about`
     only; defect is pre-existing and unworsened) instead of the false "no symptom
     exists" claim.
  2. §5 "TODO bookkeeping" — added a new tracked TODO `fmt-cli-per-consumer-version`
     (TODO.md entry + `TODO(fmt-cli-per-consumer-version)` comment at the
     `#[command(version)]` attribute on `FmtArgs`), so the known defect is deferred with
     a tracking trail per the project's TODO discipline rather than dismissed. Concrete
     done-condition recorded: `fltkfmt --version` prints `fltkfmt`'s own version. No
     scope expansion — the version fix itself stays out of this increment, exactly as
     the finding recommends.
  3. "Open questions" — resolution rewritten to rest on the corrected premise and to
     reference the new TODO.
- Severity assessment: The scope decision was already correct, so no implementation code
  would have differed; but the false premise meant a real, user-visible defect
  (`--version` misreporting) was being dismissed as nonexistent instead of consciously
  deferred, leaving it with no tracking trail — a violation of the project's TODO
  discipline and a trap for anyone later relying on the design's stated justification.

No other findings in the notes; the reviewer's "Verified correct" section required no
action.
