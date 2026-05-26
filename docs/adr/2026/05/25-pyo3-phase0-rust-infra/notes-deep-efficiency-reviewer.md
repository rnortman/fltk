# Efficiency Review — PyO3 Phase 0 Rust Infra

Commit reviewed: d650cfafd331ae531a38d8b1479b7a539a058cfd (base f1e2a98)

Scope: build/infra bootstrap (Cargo.toml, src/lib.rs, pyproject.toml maturin migration, CI, smoke test). No runtime hot paths, data structures, loops, or I/O patterns introduced. `Ping::pong` is a trivial constant return. Findings are confined to build-time/CI cost.

## efficiency-1: CI build step then `make check` may trigger a second Rust rebuild

`.github/workflows/ci.yml` runs `uv run --group dev maturin develop`, then `make check`. `make check` runs three separate `uv run --group lint --group test ...` invocations (lint, typecheck, test via Makefile). With maturin as build-backend, each `uv run` resolves/syncs the project; if the `--group dev` first invocation and the subsequent `--group lint --group test` invocations produce a different resolved environment, uv re-syncs and maturin re-links the extension — recompiling/relinking the cdylib up to one extra time.

Consequence: CI wall-clock cost. Rust compile + link is the dominant cost in this pipeline; a redundant rebuild adds tens of seconds to every CI run, on every push, indefinitely. Cost grows as the crate grows in later phases.

Direction: Confirm whether the `dev`-group sync and the `lint`/`test`-group syncs share one environment (cargo's incremental cache would make a re-link cheap but a cold re-sync would not). If they diverge, either build with the same group set used by `make check`, or drop the explicit `maturin develop` step and let the first `make check` sub-invocation build once (uv caches the built extension for identical subsequent syncs). Verify with a CI run timing comparison before committing to either.

## efficiency-2: No release/opt profile pinned — acceptable for Phase 0, flag for later

Cargo.toml defines no `[profile]`. `maturin develop` defaults to debug, which the design (lines 130) intentionally chooses for fast compile. Correct for Phase 0.

Consequence: none now. Noted only so it is not forgotten: once the extension does real CST work (later phases), debug builds in any perf-sensitive benchmark or local-dev measurement will mislead. Not actionable in this diff.

No other findings. The migration itself (setuptools -> maturin, smoke test, gitignore, TODO) is efficiency-neutral.
