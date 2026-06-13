# Efficiency review — cargo-deny CI split

Commit reviewed: edb782c (base 604dab1). Diff: Makefile, .github/workflows/ci.yml, ADR docs.

No findings.

Rationale: the diff splits one `check` target into `check-common` / `check` / `check-ci`. Total
work is unchanged or reduced — `check` (local) does the same steps as before (check-common +
cargo-deny); `check-ci` does strictly less (drops the 4 cargo-deny invocations that previously
always failed in CI). No new redundant computation, no new per-run work, no new blocking step on a
hot path. Each lane's added `mktemp`/`rm` overhead is negligible against cargo/uv step costs.

Pre-existing (NOT introduced by this diff, out of scope): check-common runs all steps serially via
a `for` loop of `$(MAKE) $step`. The cargo-heavy independent steps (cargo-check, cargo-clippy,
cargo-test, per-feature/per-manifest invocations) could run concurrently, but that serialization
predates this change and is unrelated to the cargo-deny split.
