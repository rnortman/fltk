# Judge verdict — deep review

Phase: deep. Base `47e4e7b`..HEAD `ad06d59` (reviewed HEAD `493f20d`, fixes in `ad06d59`). Round 1.
Notes: 7 reviewer files. Six reviewers (error-handling, correctness, security, test, reuse,
efficiency) reported no findings; all 3 findings are from the quality reviewer.

## Added TODOs walk

No finding was dispositioned as TODO, but the diff adds one TODO comment, so it gets the rubric.

### TODO(fmt-cli-per-consumer-version) at crates/fltk-fmt-cli/src/lib.rs:39-46 + TODO.md
Q1 (worth doing): yes — observable defect: `#[command(version)]` expands `CARGO_PKG_VERSION` in
the scaffolding crate, so `fltkfmt` (0.1.0) prints `0.2.0`. Real user-facing wrong output.
Q2 (design/owner input required): yes — the fix (per the amended TODO itself and quality-1's
resolution) must introduce a `FormatterInfo` identity struct, i.e. reshape the public `run_main`
entry point consumed by out-of-tree formatter authors; "and possibly `name`" is an open API
question. That is a design-cycle decision, not a mechanical thread-through.
Not created/worsened this iteration: the version defect is pre-existing (design "Edge cases"
documents it as observable at base); this diff does not touch the version path.
Assessment: TODO acceptable. Both TODO.md entry and `TODO(slug)` comment present and in sync.

Note: the diff also appends one sentence to the pre-existing `fltkfmt-integration-tests` TODO
(e2e `--help` assertion). Not a new slug; the deferral is structural — the macro→`run_main`
threading is only observable through a real consumer binary, which is exactly what that tracked
increment builds. The test reviewer examined and accepted this deferral. Acceptable.

## Other findings walk

### quality-1 — run_main positional `&'static str` sprawl — Won't-Do-primary / Fixed-fallback
Claim: adding `about` now with `version` scheduled "the same way" produces two adjacent
indistinguishable positional strings; a consumer swapping them compiles clean and ships a binary
whose `--help` prints a version number. Consequence: wasted breaking-change window,
parameter-sprawl trajectory.
Disposition: Fixed — via the finding's own explicit fallback ("If the team prefers to defer, at
minimum amend the `fmt-cli-per-consumer-version` TODO to say the fix should introduce the struct
rather than a second positional string").
Evidence: the frozen design (§1) deliberately specifies `run_main(about: &'static str, format_fn)`
with `about` required-positional, and §5 defers `version` to its own increment; adopting the
reviewer's primary proposal (`FormatterInfo` now) in respond mode would rewrite the approved
design, not respond to review. The fallback is applied verbatim: the diff at `lib.rs:42-46` adds
"Do NOT add a second bare `&'static str` positional ... Introduce an identity struct (e.g.
`FormatterInfo::new(about).version(..)`)", and the matching TODO.md entry carries the same
instruction plus the non-breaking-addition rationale. There is exactly one string param today, so
no current defect exists; the footgun is defused at the commit point where it would arise.
Assessment: severity should-fix (future API trajectory, no present bug). Disposition sound —
the responder took the reviewer's own sanctioned fallback and grounded the primary-fix refusal in
the frozen design. Accept.

### quality-2 — hard-coded negative help assertions rot silently — Fixed
Claim: `!help.contains("Command-line surface shared by every FLTK formatter binary")` becomes
vacuously true if the `FmtArgs` doc comment is reworded; the load-bearing guard on
`.long_about(None)` stops testing anything with no CI signal.
Evidence: diff at `lib.rs:611-647`. `long_help_shows_consumer_about` now (a) pins the reset
semantics directly (`command().long_about(None).get_long_about().is_none()`), and (b) derives the
forbidden string from the derive itself (`command().get_long_about().to_string()`) before
asserting its absence in `command_with_about(..).render_long_help()`. `short_help_...` derives
`get_about()` the same way. This is the reviewer's proposed fix, both variants combined. If the
reset were removed from `command_with_about`, the rendered long help would contain the derived
long_about and the negative assertion fails — regression is caught regardless of doc-comment
wording. Positive assertions retained. Ran `cargo test -p fltk-fmt-cli` at `ad06d59`: 41 passed,
0 failed.
Assessment: fix addresses the rot mode at the named lines. Accept.

### quality-3 — `about` param doc merges into preceding rustdoc paragraph — Fixed
Claim: missing blank `///` line glues the `about` description onto the "All grammar-independent
behavior..." sentence in the crate's primary public entry point docs.
Evidence: diff at `lib.rs:265` inserts the blank `///` line before "`about` is the one-line
description...". Renders as its own paragraph.
Assessment: nit, fixed exactly as proposed. Accept.

## Disputed items

None.

## Approved

3 findings: 3 Fixed verified (quality-1 via the reviewer's explicit fallback). 1 added TODO
acceptable under the rubric.

---

## Verdict: APPROVED

All dispositions acceptable. Fix commit `ad06d59` verified by diff inspection and full
`fltk-fmt-cli` test run (41/41).
