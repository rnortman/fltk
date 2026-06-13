No findings.

This diff touches only Makefile targets, `.github/workflows/ci.yml`, and docs. There are no new code paths, no new test modules, and no conventional test coverage to evaluate.

Structural verification: `check-ci` is a pure delegation to `check-common` (correct); `check` depends on `check-common` and then runs `cargo-deny` in its own failure-capturing shell block (correct); the pre-commit hook (`exec make check`) calls the heavy lane as the ADR requires. The anti-drift rule is editorial/review-enforced only — no automated test exists for it, which the ADR explicitly acknowledges as an accepted gap.
