# TODO Burndown Triage: `pin-ci-actions`

Concise. Precise. Token-dense. No fluff.

## Claim Verification

### File and line accuracy

`.github/workflows/ci.yml` exists. Single workflow file; no other workflow files present.

TODO claim: "lines 12, 15, 21". Actual layout:

| Line | Content |
|------|---------|
| 12 | `# TODO(pin-ci-actions): Pin to immutable commit SHA.` |
| 13 | `- uses: actions/checkout@v4` |
| 15 | `# TODO(pin-ci-actions): Pin to immutable commit SHA.` |
| 17 | `uses: astral-sh/setup-uv@v6` |
| 22 | `# TODO(pin-ci-actions): Pin all action refs to immutable commit SHAs.` |
| 24 | `uses: dtolnay/rust-toolchain@stable` |

The TODO comments already exist in the file at lines 12, 15, 22 (not 21). The three mutable refs are on lines 13, 17, 24. The cited lines point to the comment lines, not the `uses:` lines — a minor discrepancy but the intent is unambiguous. The `TODO(pin-ci-actions)` slug is live in all three comments.

### Current state of mutable refs

All three cited refs are confirmed mutable:

- `actions/checkout@v4` (`.github/workflows/ci.yml:13`) — semver tag, mutable
- `astral-sh/setup-uv@v6` (`.github/workflows/ci.yml:17`) — semver tag, mutable
- `dtolnay/rust-toolchain@stable` (`.github/workflows/ci.yml:24`) — named branch/channel, mutable

No SHA-pinned form (`@<40-hex-char-sha>`) is used anywhere in the file. The TODO description accurately describes the current state.

### Threat model accuracy

The threat is real: GitHub Actions `uses:` with a tag or branch ref resolves the ref at run time. A repo owner (or attacker who compromises a repo) can force-push the tag to point at a different commit. `dtolnay/rust-toolchain@stable` is the highest-risk ref here because `stable` is a branch name, not even a semver tag — it moves on every Rust release. `@v4` and `@v6` are tags; those could in principle be force-pushed but are more stable in practice.

### Proposed fix shape: feasibility

SHA-pinning is straightforward: replace each `@ref` with `@<commit-sha>  # ref-as-comment`. Requires looking up the current commit SHA for each tag:

- `actions/checkout` at `v4`: look up `refs/tags/v4` on `github.com/actions/checkout`
- `astral-sh/setup-uv` at `v6`: look up `refs/tags/v6` on `github.com/astral-sh/setup-uv`
- `dtolnay/rust-toolchain` at `stable`: look up `refs/heads/stable` on `github.com/dtolnay/rust-toolchain`

SHAs were not resolved in this triage (requires network access to GitHub); actual SHA values must be retrieved before editing.

### Dependabot for SHA-pinned action updates: feasibility and blocker

**Blocker**: `.github/dependabot.yml` does not exist. Dependabot for GitHub Actions requires a `dependabot.yml` config with `package-ecosystem: "github-actions"`. Without this file, Dependabot will not open PRs to update action SHAs. The TODO states "Use Dependabot to manage SHA-pinned action updates" but the prerequisite config file is absent.

A minimal `dependabot.yml` to satisfy the intent:

```yaml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

### Deeper-problem check

Is SHA-pinning papering over a deeper problem? No. The three actions used are standard, widely-used actions from well-known publishers. The supply-chain risk is generic (applies to any unpinned action), not a sign of an architectural issue with this project's CI. The workflow is simple (checkout → install uv → install Rust → build → check) and the action selection is appropriate. SHA-pinning + Dependabot is the canonical mitigation for this class of risk.

## Summary of findings

| Claim | Verdict |
|-------|---------|
| File `.github/workflows/ci.yml` exists with these three mutable refs | CONFIRMED |
| Line numbers cited (12, 15, 21) | MINOR DISCREPANCY: comments at 12, 15, 22; `uses:` lines at 13, 17, 24 |
| All three refs are mutable | CONFIRMED |
| Fix shape (SHA-pinning) is feasible | CONFIRMED |
| Dependabot currently configured | FALSE — `.github/dependabot.yml` absent, must be created |
| Supply-chain threat model is accurate | CONFIRMED |
| Deeper architectural problem | NONE FOUND |

## What the fix requires

1. Resolve current commit SHAs for `actions/checkout@v4`, `astral-sh/setup-uv@v6`, and `dtolnay/rust-toolchain@stable` via network (e.g. `git ls-remote https://github.com/<owner>/<repo> <ref>`).
2. Replace mutable refs in `.github/workflows/ci.yml` lines 13, 17, 24.
3. Create `.github/dependabot.yml` with `github-actions` ecosystem config.
4. Remove the three `TODO(pin-ci-actions)` comments from the workflow file and the entry from `TODO.md`.
