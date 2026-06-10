# Deep correctness review — pin-ci-actions

Concise. Precise. No padding. Audience: smart LLM/human. (Note carried per authoring protocol.)

Reviewed: `74a4ac2..c2c34bd` (a062e1c + c2c34bd). Single pass.

## Verified clean

- All three pinned SHAs independently re-resolved against upstream at review time and match exactly:
  - `actions/checkout@34e1148…` = `refs/tags/v4` (lightweight tag, single SHA — correct).
  - `astral-sh/setup-uv@d0cc045…` = peeled `refs/tags/v6^{}` commit (annotated tag handled per design; tag-object SHA `d0d8abe…` correctly NOT used).
  - `dtolnay/rust-toolchain@29eef33…` = `refs/heads/stable` HEAD.
- Comment format is exactly `@<40-hex>  # <ref>` (two spaces) on all three lines — matches design §"Comment-format drift".
- `ci.yml` at HEAD parses; no other `uses:` lines exist; `ci.yml` is the only workflow file, so `dependabot.yml` `directory: "/"` covers everything.
- `dependabot.yml` matches the design verbatim and the v2 schema.
- All three `TODO(pin-ci-actions)` comments deleted; `TODO.md` section removed; `git grep pin-ci-actions` outside `docs/` returns nothing (remaining docs hits are historical, as the implementation log states).
- Confirmed the pinned `dtolnay/rust-toolchain` SHA's `action.yml` hardcodes `toolchain: default: stable`, so behavior at pin time is unchanged (same effective toolchain selection as `@stable`).

## Findings

### correctness-1

- **File:line:** `.github/workflows/ci.yml:20-21` (`dtolnay/rust-toolchain` step) and design §"`stable` semantics change" / §2.
- **What's wrong:** The step relies on an implicit default that exists only on the `stable` branch's `action.yml` (`toolchain: default: stable`). On `master`/`v1`, `toolchain` is `required: true` with no default and the action's parse step exits 1 when it is empty (verified in upstream `action.yml` at both refs). No `with: toolchain:` is specified in `ci.yml`.
- **Why:** This repo's versioning is per-toolchain branches, not semver tags; the only tag is `v1` (tracks master). Dependabot resolves SHA-pin updates from the ref comment, and `# stable` is not a release/semver ref, so the design's stated mitigation — "the point Dependabot weekly bumps address" (design.md:62) — is unlikely to function for this pin: Dependabot either proposes no bumps (pin silently rots; Rust toolchain frozen forever, contradicting the design's claim) or, if it ever maps the action to `v1`, bumps to a master SHA where the missing `toolchain` input makes the step fail.
- **Consequence:** Either (a) the CI Rust toolchain never advances despite the design asserting weekly Dependabot bumps handle it — invariant "pins are refreshed by Dependabot" violated silently; or (b) a future Dependabot bump to a `v1`/master SHA breaks the step with "'toolchain' is a required input". No wrong behavior at HEAD; the bug is that the change does not deliver the maintenance property the design claims for this one action.
- **Suggested fix:** Add `with: toolchain: stable` to the step so behavior is independent of which branch the pinned SHA came from (safe under any future bump), and either accept manual refresh of this pin or note in the ADR that Dependabot will not bump branch-comment pins.

No other findings. Off-by-one/operator/variable/control-flow/data-flow surface is trivial here; the substantive correctness risk was SHA↔ref mismatch and annotated-tag peeling, both verified correct.
