# Request: pin-ci-actions

Style: concise, precise, no padding, no preamble. Audience: smart LLM/human.

**Type of work:** security hardening (CI config); small.

**Background.** `.github/workflows/ci.yml` references three GitHub Actions by *mutable* refs:
- `actions/checkout@v4` (line 13)
- `astral-sh/setup-uv@v6` (line 17)
- `dtolnay/rust-toolchain@stable` (line 24) — `stable` is a branch, moves every Rust release.

Mutable refs resolve at run time, so a compromised/force-moved upstream ref can execute arbitrary code in CI and tamper with build artifacts. `TODO(pin-ci-actions)` comments already sit at lines 12, 15, 22. There is no `.github/dependabot.yml` today.

**Fix shape (chosen).** SHA-pin all three to immutable 40-char commit SHAs with the human-readable ref preserved as a trailing comment (`uses: actions/checkout@<sha>  # v4`). Add `.github/dependabot.yml` with the `github-actions` ecosystem (weekly) so Dependabot proposes pinned-SHA bumps going forward. Remove the three `TODO(pin-ci-actions)` comments and the `TODO.md` entry as part of the change.

**Load-bearing constraints.**
- Resolving each ref→SHA requires network (`git ls-remote https://github.com/<owner>/<repo> <ref>`). The implementer must fetch the *current* SHA for each ref at implementation time; do not invent SHAs.
- Pin to the SHA the mutable ref currently points at (no version bumps as part of this change).
- CI must still pass after pinning (same effective action versions).

**Non-goals.** No CI logic/job changes. No action version upgrades. No other workflow files (only `ci.yml` exists).

**Verification.** `ci.yml` parses and the pinned workflow runs green; each `uses:` is a 40-hex SHA with a ref comment; `.github/dependabot.yml` is valid (`github-actions` ecosystem, directory `/`). No remaining `TODO(pin-ci-actions)` anywhere; `TODO.md` entry removed.

**Exploration:** `exploration.md` in this dir (full validation, incl. line-number corrections — comments at 12/15/22, `uses:` at 13/17/24).
