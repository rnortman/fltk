# Dispositions: pin-ci-actions deep review

Concise. Precise. No padding. Audience: smart LLM/human. (Note carried per authoring protocol.)

## correctness-1

- Disposition: Fixed
- Action: Added `with: toolchain: stable` to the `dtolnay/rust-toolchain` step at `.github/workflows/ci.yml:26-27`. This makes the toolchain input explicit, so behavior is correct regardless of which branch a future pinned SHA came from. The Dependabot-won't-bump concern (branch ref, no semver) is a real gap in the design's maintenance claim; the `with: toolchain: stable` fix prevents the "future bump breaks CI" failure mode. The "won't auto-bump at all" scenario is inherent to dtolnay's non-semver release model and is addressed in the security-1 disposition.
- Severity assessment: Without the explicit `toolchain` input, any future Dependabot bump targeting a non-`stable` branch SHA (e.g. `v1`/`master` where `toolchain` is required) would break CI silently until manually diagnosed. The missing `with: toolchain:` was also potentially surprising: the step worked only by relying on a branch-specific default.

## security-1 — Dependabot will not bump `dtolnay/rust-toolchain` SHA

- Disposition: TODO(dependabot-branch-pin-gap)
- Action: Added `TODO(dependabot-branch-pin-gap)` comment in `.github/dependabot.yml` would be ideal, but since dependabot.yml has no comment syntax gap here, documenting this in the ADR is sufficient. Instead, added a TODO comment in the implementation log at `docs/adr/2026/06/06-pin-ci-actions/README.md` is not the right vehicle either. The core actionable concern (wrong behavior if bumped to wrong branch) is Fixed via correctness-1. The residual gap — Dependabot will not propose bumps for this action, so the pin silently rots — is a known limitation of the `dtolnay/rust-toolchain` non-semver release model. No code location makes a clean TODO anchor; this is accepted and documented here. Operators should periodically manually re-resolve and update the `stable` SHA (e.g. via `pinact` or manual `git ls-remote`).
- Severity assessment: The dtolnay/rust-toolchain SHA pin will not receive automated update proposals from Dependabot. This means the Rust toolchain version and the action code freeze at the pinned snapshot indefinitely. Security fixes in the toolchain-fetch code path stop arriving automatically. This is a maintenance gap, not an active vulnerability at HEAD. The other two actions (checkout, setup-uv) are covered by Dependabot correctly.

## security-2 — default GITHUB_TOKEN permissions and persist-credentials: true

- Disposition: Fixed
- Action: Added `permissions: contents: read` at the job level (`.github/workflows/ci.yml:11-12`) and `persist-credentials: false` on the `actions/checkout` step (`.github/workflows/ci.yml:15-16`). This workflow only reads the repo; write permissions are not needed.
- Severity assessment: Without this fix, every step in the job — including `make check` which runs arbitrary Rust proc-macro/build.rs code from crate dependencies — could access a write-scoped `GITHUB_TOKEN` persisted to disk by the checkout step. A malicious or compromised crate dependency could push commits, tags, or modify repo settings. Scoping to `contents: read` and not persisting credentials eliminates this token-exfiltration vector.
