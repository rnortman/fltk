# Dispositions — Phase 0 Deep Review

Commit reviewed: d650cfafd331ae531a38d8b1479b7a539a058cfd (base f1e2a98)

---

## correctness-1

- Disposition: TODO(ci-maturin-rebuild)
- Action: Added TODO comment at `.github/workflows/ci.yml:23` — the explicit `maturin develop` step is redundant because `make check`'s first `uv run` re-syncs the project via the maturin build-backend, rebuilding the extension itself. The design's claim ("ensures the native extension is built before any uv run step") is inaccurate as written; the toolchain install is what matters, not the explicit build step. No wrong behavior in CI today.
- Severity assessment: Zero functional impact in CI (toolchain is present when `make check` runs). Mental-model confusion for future contributors is the real risk; the redundant step encodes a false belief about uv/maturin build semantics.

## correctness-2

- Disposition: Won't-Do
- Action: No change. Already documented in CLAUDE.md and design.md as a deliberate trade-off.
- Severity assessment: Rust-less machines cannot run any `make check` target. Accepted and documented; the Rust extension is core infrastructure for this project.
- Rationale: Design.md "Edge Cases / Failure Modes" explicitly calls this out and calls it a "deliberate trade-off." CLAUDE.md documents `rustup` as a prerequisite. Treating this as a defect would contradict the accepted design.

## correctness-3

- Disposition: Won't-Do
- Action: No change. Stale coverage `source_pkgs`/`paths` referencing `src/fltk` predate this diff and are no-ops. Out of scope.
- Severity assessment: None — the paths resolve to nothing and coverage functions correctly.
- Rationale: Reviewer confirmed "no behavior change." Fixing stale coverage config is out of scope for Phase 0; can be addressed in a cleanup pass.

## correctness-4

- Disposition: Won't-Do
- Action: No change. Reviewer confirmed no defect.
- Severity assessment: None — PyO3 lifetime semantics for `&'static str` return are correct; `#[pymodule]` name matches the `PyInit__native` symbol required by maturin.
- Rationale: Informational verification finding; no action warranted.

## security-1

- Disposition: TODO(pin-ci-actions)
- Action: Added TODO comment at `.github/workflows/ci.yml:21` noting that `dtolnay/rust-toolchain@stable`, `actions/checkout@v4`, and `astral-sh/setup-uv@v6` should be SHA-pinned. Also added entry to `TODO.md`.
- Severity assessment: Mutable ref on a CI action with full runner access. If the action repo is compromised, an attacker gets code execution in CI and can tamper with build artifacts (the compiled `.so`). Low-to-medium practical risk for this repo today; higher risk as the project grows and the native extension ships to downstream users.

## security-2

- Disposition: TODO(tests-outside-package)
- Action: This overlaps with quality-2. Single TODO(tests-outside-package) covers both. See quality-2 disposition.
- Severity assessment: Benign for this specific file. The pattern risk — future test files with side effects or credentials shipping in the wheel — is the concern, not the current file.

## security-3

- Disposition: Won't-Do
- Action: No change. Lockfiles carry checksums; no known-vulnerable versions in the new dependency set.
- Severity assessment: Informational. New Rust crates enter the in-process trust boundary as a `cdylib`; this is inherent to PyO3 and accepted by the design. Auditing on future `cargo update` is appropriate operational hygiene, not a code fix.
- Rationale: No actionable defect. Checksummed lockfiles already provide the integrity guarantee the reviewer describes.

## quality-1

- Disposition: TODO(ci-maturin-rebuild)
- Action: Same finding as correctness-1 — covered by the same TODO at `.github/workflows/ci.yml:23`. The redundant `maturin develop` step encodes a false mental model and pays an extra compile cost on every CI run.
- Severity assessment: Wasted CI time (extra Rust compile, grows as crate grows in later phases) and false documentation of uv/maturin semantics for future contributors.

## quality-2

- Disposition: Fixed
- Action: Moved `fltk/test_native.py` to `tests/test_native.py`. Updated import (no change needed — `fltk._native` is an absolute import). Verified ruff `tests/**/*` per-file-ignore covers the new location. The file no longer ships in the `fltk` wheel (`python-packages = ["fltk"]` in pyproject.toml does not include `tests/`).
- Severity assessment: `fltk.test_native` was importable by end users of the installed package — an abstraction boundary violation. The test is benign now, but the pattern compounds with future test files.

## efficiency-1

- Disposition: TODO(ci-maturin-rebuild)
- Action: Same finding as correctness-1 and quality-1. Covered by TODO at `.github/workflows/ci.yml:23`.
- Severity assessment: Extra Rust compile on every CI push. Acceptable overhead today (fast crate); grows as Phase 1+ adds real code.

## efficiency-2

- Disposition: Won't-Do
- Action: No change. Debug builds for Phase 0 are intentional per design (line 130).
- Severity assessment: None for Phase 0. Noted for future phases when the extension does real CST work.
- Rationale: Design explicitly chooses debug profile for fast iteration during development. Reviewer marked this as not actionable in this diff.
