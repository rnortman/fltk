# Dispositions: pin-ci-actions deep review — rework round 2

Concise. Precise. No padding. Audience: smart LLM/human. (Note carried per authoring protocol.)

## security-1 — Dependabot will not bump `dtolnay/rust-toolchain` SHA

- Disposition: TODO(dependabot-branch-pin-gap)
- Action (rework):
  - Added `# TODO(dependabot-branch-pin-gap): ...` YAML comment at the `dtolnay/rust-toolchain` step in `.github/workflows/ci.yml:24-28`, documenting the Dependabot blind spot and providing the manual-refresh procedure (`git ls-remote` / `pinact`).
  - Added `## \`dependabot-branch-pin-gap\`` entry to `TODO.md` (after `pyright-batch-tests`), with slug, deferral context, and location reference.
  - Corrected `design.md` edge-case claim (line 62): previously stated "this is the point Dependabot weekly bumps address" without qualification. Now explicitly notes that Dependabot covers `actions/checkout` and `astral-sh/setup-uv` (semver-tagged) but not `dtolnay/rust-toolchain` (branch-pinned), with cross-reference to `TODO(dependabot-branch-pin-gap)`.
- Severity assessment: The pin silently rots without automated refresh proposals. This is a maintenance gap, not an active vulnerability at HEAD; the other two actions receive Dependabot coverage. The TODO anchor ensures operators will find the manual-refresh procedure at the relevant code location, and the TODO.md entry provides the deferral rationale and join key per project convention.
