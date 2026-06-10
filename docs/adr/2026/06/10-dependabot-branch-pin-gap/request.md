# Request: dependabot-branch-pin-gap

Style: concise, precise, no padding, no preamble. Self-contained — downstream agents do not see the triage conversation.

**Type**: small scoped CI config fix. No design question.

## Background

`.github/workflows/ci.yml:24-30` pins `dtolnay/rust-toolchain` to SHA `29eef336d9b2848a0b548edc03f92a220660cdb8` with comment `# stable` — a branch ref, not a semver tag. Dependabot (`.github/dependabot.yml`, `github-actions` ecosystem, weekly) keys off the ref comment and only proposes SHA bumps for semver-tagged refs; branch-comment pins are silently skipped. The pin rots silently. Documented in `docs/adr/2026/06/06-pin-ci-actions/design.md:62`.

Validation (see `exploration.md` in this dir) confirmed upstream has tag `refs/tags/v1` at `e97e2d8cc328f1b50210efc529dca0028893a2d9`. `v1` tracks a different branch than `stable`; the one known behavioral difference (on `v1`, the `toolchain` input is required, no default) is already guarded — `ci.yml:33` passes `with: toolchain: stable` explicitly.

## Direction (decided at triage — do not second-guess)

Re-pin to the `v1` tag SHA so Dependabot tracks the pin:

- `uses: dtolnay/rust-toolchain@e97e2d8cc328f1b50210efc529dca0028893a2d9  # v1`
- Keep `with: toolchain: stable` exactly as-is.
- Remove the `TODO(dependabot-branch-pin-gap)` comment block at `ci.yml:24-28`; replace with a one-line comment noting the pin is the `v1` tag and Dependabot refreshes it.
- Remove the `dependabot-branch-pin-gap` entry from `TODO.md`.

## Constraints / non-goals

- Do not change any other action pin.
- Do not modify `.github/dependabot.yml`.
- No-VCS interactions beyond a normal commit; never push.

## Verification

- `grep -rn 'dependabot-branch-pin-gap'` across the repo returns nothing.
- YAML stays valid (e.g. `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml'))"` or equivalent).
- Re-verify the `v1` SHA live before committing: `git ls-remote https://github.com/dtolnay/rust-toolchain refs/tags/v1` must return `e97e2d8cc328f1b50210efc529dca0028893a2d9`; if it differs, use the live value and note it in the commit.
- CI itself is the real test; it runs when the user eventually pushes. Nothing to run locally beyond lint of the workflow file if a linter is available.
