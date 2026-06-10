# Exploration: dependabot-branch-pin-gap TODO adversarial verification

Concise. Precise. No padding. Audience: smart LLM/human.

## What the TODO claims

- `dtolnay/rust-toolchain` is pinned to a commit SHA with a `# stable` branch comment (not a semver tag).
- Dependabot's `github-actions` ecosystem only proposes SHA bumps for semver-tagged actions; branch-referenced actions are silently skipped.
- The SHA will silently rot; periodic manual refresh required.
- Location: `.github/workflows/ci.yml` (the `dtolnay/rust-toolchain` step).

## Ground truth — ci.yml

**`.github/workflows/ci.yml:24-30`** (as committed at `c7a9e5b`):

```yaml
# TODO(dependabot-branch-pin-gap): dtolnay/rust-toolchain tracks the `stable`
# branch, not a semver tag. Dependabot does not propose SHA bumps for
# branch-pinned actions, so this pin will silently rot. Periodically
# refresh manually: git ls-remote https://github.com/dtolnay/rust-toolchain refs/heads/stable
# and update the SHA here (or use `pinact`).
- name: Install Rust toolchain
  uses: dtolnay/rust-toolchain@29eef336d9b2848a0b548edc03f92a220660cdb8  # stable
  with:
    toolchain: stable
```

The pin is `29eef336d9b2848a0b548edc03f92a220660cdb8` with trailing comment `# stable`.

## Ground truth — dtolnay/rust-toolchain upstream refs

Queried live (`git ls-remote` at time of exploration):

```
e97e2d8cc328f1b50210efc529dca0028893a2d9    refs/tags/v1
29eef336d9b2848a0b548edc03f92a220660cdb8    refs/heads/stable
```

Facts:
- The repo has exactly **one semver-adjacent tag**: `v1` at `e97e2d8cc328f1b50210efc529dca0028893a2d9`.
- `refs/heads/stable` HEAD at query time: `29eef336d9b2848a0b548edc03f92a220660cdb8` — **identical to the current pin** (pin is current as of exploration).
- The `v1` SHA (`e97e2d8c`) differs from the `stable` SHA (`29eef336`). These track different trees.

## Ground truth — Dependabot config

**`.github/dependabot.yml`** (entire file):

```yaml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

No `ignore:` clauses. No per-action overrides.

## Is the "Dependabot skips branch-comment pins" claim accurate?

Dependabot's `github-actions` ecosystem resolves which version to bump by reading the ref comment after the SHA (`# <ref>`). Its update logic keys on whether the comment ref resolves to a **release** (semver tag) in the upstream repo. A comment of `# stable` is a branch name, not a semver tag. Dependabot does not treat branch names as versioned releases and will not propose SHA bumps for them.

Evidence from the pin-ci-actions ADR: `docs/adr/2026/06/06-pin-ci-actions/design.md:62` states explicitly: "Dependabot either proposes no bumps (pin silently rots) … Dependabot weekly bumps address [the issue] for `actions/checkout` and `astral-sh/setup-uv` (semver-tagged), but **not** for `dtolnay/rust-toolchain` (branch-pinned, not semver-tagged) — Dependabot skips branch-referenced actions." This is repeated in `notes-deep-correctness.md:25-26`.

Conclusion: the TODO's Dependabot claim is **correct**.

## Could pinning to the `v1` tag restore Dependabot coverage?

`v1` (`e97e2d8cc328f1b50210efc529dca0028893a2d9`) is a semver-style tag. Dependabot would recognize `# v1` as a versioned ref and propose SHA bumps when `v1` is repointed.

**However**, `v1` tracks a different branch (`master`/default) from `stable`. The `notes-deep-correctness.md` review (`docs/adr/2026/06/06-pin-ci-actions/notes-deep-correctness.md:24-27`) documents a concrete behavioral difference: on `stable` branch, `action.yml` has `toolchain: default: stable`; on `master`/`v1`, `toolchain` is `required: true` with no default — a step with no `with: toolchain:` would fail with `'toolchain' is a required input`. The current `ci.yml:33` includes `with: toolchain: stable`, which guards against this failure regardless of which SHA is pinned.

So: pinning to `v1`/`# v1` would restore Dependabot coverage **and** the `with: toolchain: stable` already present would prevent the input-required failure on a future `v1` SHA bump.

The semantic difference between `stable` and `v1`/`master` beyond the `toolchain` default is not verified here (may include other behavior changes in `action.yml`).

## Are there blockers?

No technical blockers to either:
1. Accepting the status quo (manual refresh, as the TODO documents), or
2. Re-pinning to `v1` (`e97e2d8c…`) with comment `# v1` to restore Dependabot coverage.

The `with: toolchain: stable` already at `ci.yml:33` satisfies the correctness prerequisite for either approach.

## Summary of factual findings

| Claim | Verified? |
|---|---|
| Pin is a SHA with `# stable` branch comment, not semver tag | YES — `ci.yml:30` |
| `dtolnay/rust-toolchain` has no semver release tags (only `v1`) | PARTIALLY — `v1` exists but tracks a different branch than `stable` |
| Pin SHA matches current `refs/heads/stable` HEAD | YES — both `29eef336` at time of exploration |
| Dependabot skips branch-comment pins for SHA-pinned actions | YES — documented in `design.md:62`, `notes-deep-correctness.md:25-26` |
| `v1` tag exists and could restore Dependabot coverage | YES — `e97e2d8cc328f1b50210efc529dca0028893a2d9` |
| `with: toolchain: stable` present (guards against `v1` required-input failure) | YES — `ci.yml:33` |
| TODO comment in `ci.yml` matches TODO.md entry | YES — `ci.yml:24-27`, `TODO.md:31-33` |

## Open factual questions

- Whether `dtolnay/rust-toolchain` `v1` (`master`) and `stable` branches are kept semantically in sync by the maintainer (besides the `toolchain` default difference) — not verified against upstream `action.yml` at `v1`.
- Whether Dependabot proposes bumps specifically for `v1`-style tags when there is no higher-numbered semver tag (i.e., whether Dependabot treats `v1` as the "current major" and proposes SHA refreshes when `v1` is repointed, vs. only proposing a bump to a newer major tag if one existed). This determines whether `# v1` actually gets weekly bump proposals in practice.
