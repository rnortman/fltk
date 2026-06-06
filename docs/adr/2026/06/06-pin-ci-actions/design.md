# Design: pin-ci-actions

Concise. Precise. No padding. Audience: smart LLM/human. (Note carried per authoring protocol.)

## Root cause / context

`.github/workflows/ci.yml` references three GitHub Actions by mutable refs:

- `actions/checkout@v4` (`ci.yml:13`) — semver tag.
- `astral-sh/setup-uv@v6` (`ci.yml:17`) — semver tag.
- `dtolnay/rust-toolchain@stable` (`ci.yml:24`) — branch/channel, moves every Rust release.

GitHub Actions resolves `uses:` refs at run time. A tag can be force-moved and a branch moves by design, so a compromised or repointed upstream ref executes attacker-controlled code in CI. This CI job builds native Rust artifacts and runs `make check` (`ci.yml:26-30`); a malicious action could tamper with build artifacts. The risk is generic to any unpinned action, not an architectural defect (exploration "Deeper-problem check"). `dtolnay/rust-toolchain@stable` is highest-risk: a branch, not even a tag.

`TODO(pin-ci-actions)` comments already mark the three sites (`ci.yml:12,15,22`) and a matching `TODO.md` entry exists (`TODO.md:15`). No `.github/dependabot.yml` exists; without it Dependabot will not propose action bumps, so pins would silently rot.

## Proposed approach

Two files touched. No CI logic/job changes, no version upgrades.

### 1. `.github/workflows/ci.yml`

For each of the three `uses:` lines, replace the mutable ref with the immutable 40-hex commit SHA the ref **currently** points at, preserving the human-readable ref as a trailing comment:

```yaml
- uses: actions/checkout@<sha>  # v4
  uses: astral-sh/setup-uv@<sha>  # v6
  uses: dtolnay/rust-toolchain@<sha>  # stable
```

SHA resolution at implementation time (network required — do not invent SHAs):

- `actions/checkout` `v4` → `git ls-remote https://github.com/actions/checkout refs/tags/v4`
- `astral-sh/setup-uv` `v6` → `git ls-remote https://github.com/astral-sh/setup-uv refs/tags/v6`
- `dtolnay/rust-toolchain` `stable` → `git ls-remote https://github.com/dtolnay/rust-toolchain refs/heads/stable`

Annotated tags: if `ls-remote` returns a `^{}` peeled line for the tag, pin to the **commit** SHA (the peeled `^{}` value), not the tag-object SHA — the action runner checks out the commit; the peeled value is the right pin. (`v4`/`v6` are likely annotated tags; `stable` is a branch with a single commit SHA.)

Delete the three `TODO(pin-ci-actions)` comment lines (`ci.yml:12,15,22`). The `- name:` and `with:` lines stay.

### 2. `.github/dependabot.yml` (new)

```yaml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

`directory: "/"` is correct for the `github-actions` ecosystem — Dependabot discovers all workflow files under `.github/workflows/`. Dependabot honors SHA pins and proposes SHA bumps with the ref comment updated, preserving the pinning convention.

### 3. `TODO.md`

Remove the `## `pin-ci-actions`` section (`TODO.md:15-17`) including its blank-line separator.

## Edge cases / failure modes

- **Annotated vs lightweight tag.** Pinning the tag-object SHA instead of the commit SHA would not match what the runner checks out. Mitigation: prefer the `^{}` peeled commit SHA when present (see above).
- **Comment-format drift.** Dependabot and common scanners (e.g. `pinact`, `ratchet`) expect `@<sha>  # <ref>`. Use exactly that form so future automated bumps update the comment instead of duplicating it.
- **`stable` semantics change.** Pinning `dtolnay/rust-toolchain@stable` freezes the Rust toolchain version at the SHA's snapshot. This is intentional (immutability) and is the point Dependabot weekly bumps address. No behavior change at pin time — same effective version.
- **Wrong/stale SHA.** A typo'd or non-existent SHA fails the CI run loudly (action not found / checkout fails), not silently. Caught by the verification CI run below.
- **Dependabot YAML invalid.** GitHub surfaces an error on the repo's Dependabot config page and opens no PRs; the config does not affect CI runs. Validate by schema before commit.

## Test plan

No unit tests (CI config only). Verification gates after the change:

1. `ci.yml` parses as YAML and the workflow runs green on the PR — confirms all three pinned SHAs resolve to working actions at the same effective versions.
2. Each of the three `uses:` lines matches `@[0-9a-f]{40}  # <ref>` (40-hex SHA + ref comment).
3. `.github/dependabot.yml` is valid YAML with `package-ecosystem: "github-actions"`, `directory: "/"`, weekly schedule. GitHub Dependabot config page reports no error.
4. No `TODO(pin-ci-actions)` remains anywhere (`grep -rn 'pin-ci-actions'` returns nothing); `TODO.md` entry removed.

## Open questions

None. Request and exploration are consistent; the only line-number note (TODO comments at 12/15/22, not 21) is already reconciled in the request.
