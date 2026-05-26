# Deep Correctness Review — Phase 0 Rust/PyO3 Infra

Commit reviewed: d650cfafd331ae531a38d8b1479b7a539a058cfd (base f1e2a98)
Scope: build-infra change (Cargo.toml, src/lib.rs, pyproject.toml, CI, .gitignore, test_native.py, TODO.md, MODULE.bazel).
Style: concise/precise/complete/unambiguous; same applies to any doc derived from this.

Verified empirically: extension builds, `fltk._native.Ping().pong() == "pong"`, smoke test passes, and the
CI sequence (`uv run --group dev maturin develop` then `uv run --group lint --group test pytest` via `make check`)
works — the maturin editable install leaves the `.so` in the source tree, so the cross-group re-sync keeps it importable.

No correctness bugs found in code logic, control flow, or data flow. Findings below are behavioral observations on the
build/CI control flow that affect *when* the build succeeds, not defects in the committed code.

---

## correctness-1
File: .github/workflows/ci.yml:22-23 (and Makefile `check`)
What: `make check` runs `uv run --group lint --group test ...` with a *different* group set than the build step
(`uv run --group dev maturin develop`). Each `uv run` with a new group set triggers a re-sync that uninstalls and
reinstalls the `fltk` editable package, re-invoking the maturin backend.
Why: Confirmed by running the sequence — the second `uv run` prints "Uninstalled 1 package / Installed 1 package".
That reinstall re-runs maturin, which requires the Rust toolchain. The explicit `maturin develop` step is therefore
not what makes the extension available to `make check`; the re-sync inside `make check` rebuilds it. The toolchain
happens to be present (installed one step earlier), so it works.
Consequence: The `Build Rust extension` CI step is effectively redundant for correctness — the build is re-driven by
the first `uv run` inside `make check`. Functionally correct in CI (toolchain present), but the dependency chain is
not what the design states ("ensures the native extension is built before any uv run step"). No wrong behavior in CI.
Suggested fix: None required for correctness. Optional: keep the explicit step only as a fail-fast/clear-error guard,
or align `make check`'s `uv run` group set with the build step to avoid the re-sync churn.

## correctness-2
File: Makefile `check` chain invoked locally without Rust
What: With `build-backend = "maturin"`, every `uv run` re-syncs the `fltk` editable install via maturin. A developer
machine without `rustc`/`cargo` cannot run *any* `make check` target (lint, typecheck, test) — not just the native test.
Why: `pyproject.toml:2-3` sets maturin as build-backend; uv invokes it on sync. No Rust → build failure → the whole
`uv run` aborts before pytest/ruff/pyright run.
Consequence: On a Rust-less machine, lint and typecheck (which have nothing to do with the extension) also fail. This
is a deliberate trade-off documented in design.md ("Rust toolchain required for all development") and CLAUDE.md, so it
is an accepted invariant, not a defect. Noted for completeness.
Suggested fix: None — intended per design. Ensure CLAUDE.md prerequisite note ships (it does).

## correctness-3 (non-issue, verified)
File: pyproject.toml:118-127 coverage `source_pkgs`/`paths` reference `src/fltk` and `src/fltk/__about__.py`.
`src/` now contains Rust (`src/lib.rs`), and `src/fltk` does not and never did exist. These stale paths predate this
diff and resolve to no-op omits; the new Rust `src/` does not collide with Python coverage. No behavior change.

## correctness-4 (non-issue, verified)
File: src/lib.rs
`Ping` unit struct, `#[new] -> Self`, `pong(&self) -> &str { "pong" }`: PyO3 copies the `'static` str into a Python
str on return; lifetimes sound. `#[pymodule] fn _native` matches `module-name = "fltk._native"` final path component
(`PyInit__native`). No defect.
