# Judge verdict — design review

Phase: design. Doc: `docs/adr/2026/07/01/01-fmt-cli-per-consumer-about/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 1 finding.

## Other findings walk

### design-1 — Fixed

Claim: the design's out-of-scope justification for `--version` rested on a false premise
("workspace crates share a version today" / "nothing today produces a wrong-version
symptom"); consequence is a real user-visible defect (`fltkfmt --version` printing the
scaffolding crate's version) being dismissed as nonexistent rather than consciously
deferred — no tracking trail, contrary to the project's TODO discipline.

Fact-check of the finding's premise, verified against the tree:
`crates/fltkfmt/Cargo.toml` declares its own `[workspace]` (with an explanatory comment
about deliberate exclusion from the root workspace) and `version = "0.1.0"` (line 9);
`crates/fltk-fmt-cli/Cargo.toml:3` is `version = "0.2.0"`; root `Cargo.toml` workspace
version is `0.2.0`. So `fltkfmt --version` does report `0.2.0` for a `0.1.0` binary today.
The finding is genuine, consequence stated and real. Severity: should-fix (design-doc
factual error that misdirects future work; not a blocker for this increment's code).

Verification of the fix against the design doc:
1. "Edge cases / failure modes", `--version` bullet (design.md, "Edge cases" section) —
   now states "This is an observable defect today, not a hypothetical", cites both
   Cargo.toml versions and the deliberate workspace exclusion, and grounds the
   out-of-scope call in the true reason ("the requirement and TODO prescribe threading
   `about` only — not because no symptom exists"). Matches the finding's suggested fix.
2. §5 "TODO bookkeeping" — adds `fmt-cli-per-consumer-version`: TODO.md entry plus
   `TODO(fmt-cli-per-consumer-version)` comment at the `#[command(version)]` attribute,
   with a concrete done-condition ("`fltkfmt --version` prints `fltkfmt`'s own version").
   This satisfies the project's slug + code-comment TODO convention and converts
   "dismissed" into "deferred with a trail." The finding offered "accept as known or note
   as candidate TODO"; a tracked TODO is within that envelope and is bookkeeping, not
   scope expansion — the design explicitly keeps the version fix out of this increment.
3. "Open questions" — rewritten on the corrected premise; the judgment call is resolved
   as out-of-scope on the true grounds and references the §5 TODO. No false claim remains
   (checked: the strings "share a version" and "nothing today produces" no longer appear).

Assessment: fix fully addresses the comment and its consequence at all three named
locations; the responder independently re-verified the facts before editing. Accept.

## Disputed items

None.

## Approved

1 finding: 1 Fixed verified.

---

## Verdict: APPROVED

The sole finding's disposition is sound and the design edits are verified in place.
