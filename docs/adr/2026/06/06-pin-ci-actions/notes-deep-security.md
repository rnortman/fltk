# Security review: pin-ci-actions (74a4ac2..c2c34bd)

Concise. Precise. No padding. Audience: smart LLM/human. (Note carried per authoring protocol.)

## Verification performed

Pinned SHAs independently re-resolved against upstream via `git ls-remote` at review time; all three are authentic:

- `actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5` == `refs/tags/v4` (lightweight tag).
- `astral-sh/setup-uv@d0cc045d04ccac9d8b7881df0226f9e82c39688e` == peeled `refs/tags/v6^{}` commit (annotated tag handled correctly per design; tag-object SHA `d0d8abe...` correctly NOT used).
- `dtolnay/rust-toolchain@29eef336d9b2848a0b548edc03f92a220660cdb8` == `refs/heads/stable` HEAD.

All three `uses:` lines match `@[0-9a-f]{40}  # <ref>`. Dependabot YAML is minimal and valid; no secrets in the diff; no injection surface added (no new `run:` steps, no untrusted-input interpolation into shell). The change is a strict security improvement over mutable refs.

## Findings

### security-1 — Dependabot will not bump the branch-pinned `dtolnay/rust-toolchain` SHA; pin rots silently

- File: `.github/workflows/ci.yml:21` + `.github/dependabot.yml`.
- Issue: Dependabot's `github-actions` ecosystem updates SHA pins by mapping the trailing comment to a release/semver tag and bumping toward the latest release. `dtolnay/rust-toolchain` publishes no releases and no semver tags — `stable` is a branch. With comment `# stable`, Dependabot has no version to compare and will not propose bumps for this action (it will handle `checkout` and `setup-uv` fine). The design (`design.md` "stable semantics change": "the point Dependabot weekly bumps address") and the rot mitigation rationale assume Dependabot covers all three pins; it covers two.
- Trust boundary / data flow: upstream action repo → CI runner executing action code with access to the repo checkout, `GITHUB_TOKEN`, and build artifacts. The pin freezes that code at today's snapshot.
- Consequence: if a vulnerability is later found and fixed in `dtolnay/rust-toolchain` (or in the toolchain-fetch path it implements), this repo keeps executing the vulnerable revision indefinitely with no automated signal — the exact "pins silently rot" failure the dependabot.yml was added to prevent. Also freezes the Rust toolchain version itself, so toolchain security fixes stop arriving via CI.
- Suggested fix: any of — (a) add a periodic manual/scheduled bump note for this one action (e.g. TODO or calendar'd `pinact`/`ratchet` run); (b) pin to one of dtolnay's per-version branches and document that Dependabot won't bump it; (c) accept and document the gap explicitly in the ADR so the design's claim isn't misleading. At minimum correct the design/ADR text.

### security-2 — (pre-existing, same threat model) workflow grants default `GITHUB_TOKEN` permissions and persists credentials into the checkout

- File: `.github/workflows/ci.yml:8-12` (job `check`; `actions/checkout` step touched by this diff).
- Issue: no top-level or job-level `permissions:` block, so the `GITHUB_TOKEN` gets the repo's default scope (write for `contents` etc. unless the repo/org default was tightened), and `actions/checkout` defaults to `persist-credentials: true`, writing the token into `.git/config` where every later step (`make build-*`, `make check` — which runs cargo builds, i.e. arbitrary build.rs/proc-macro code from crate dependencies) can read it.
- Trust boundary / data flow: third-party action code AND third-party crate/Python dependency code executed by the build → token on disk/in env → GitHub API with write scope.
- Consequence: a compromised action (the very threat this change mitigates — pinning narrows but does not eliminate it: the pinned snapshot could already be malicious-but-unnoticed, and post-install code like the Rust toolchain binaries is fetched at run time) or a malicious crate dependency can use the persisted token to push commits/tags or tamper with the repo, not just the current job. Pre-existing, not introduced by this diff; listed because it sits inside the diff's stated threat model ("a malicious action could tamper with build artifacts") and the checkout line was edited here.
- Suggested fix: add top-level `permissions: contents: read` and `persist-credentials: false` on the checkout step (nothing in this workflow pushes).

No other findings.
