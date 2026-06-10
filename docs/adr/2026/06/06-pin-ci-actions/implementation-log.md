## Increment 1 — pin-ci-actions (commit a062e1c)

- `.github/workflows/ci.yml`: replaced three mutable `uses:` refs with pinned SHAs + trailing ref comments; removed three `# TODO(pin-ci-actions):` comment lines.
  - `actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5  # v4` (lightweight tag; single SHA from ls-remote)
  - `astral-sh/setup-uv@d0cc045d04ccac9d8b7881df0226f9e82c39688e  # v6` (annotated tag; peeled `^{}` commit SHA used)
  - `dtolnay/rust-toolchain@29eef336d9b2848a0b548edc03f92a220660cdb8  # stable` (branch HEAD)
- `.github/dependabot.yml`: created; `package-ecosystem: "github-actions"`, `directory: "/"`, `interval: "weekly"`.
- `TODO.md`: removed `## \`pin-ci-actions\`` section.
- Both YAML files validated clean (pyyaml `safe_load`). All three `uses:` lines match `@[0-9a-f]{40}  # <ref>`.
- `make check` passed (pre-commit hook ran full suite: lint, format-check, typecheck, test, cargo-check, cargo-clippy, cargo-test).
- Note: `grep -rn 'pin-ci-actions'` still returns hits in docs/ADR files (exploration notes, triage docs, design/request) — these are historical records referencing the slug, not live TODO comments. The live code and TODO.md are clean.
