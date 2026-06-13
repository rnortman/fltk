# ADR: cargo-deny CI Split — Local Precommit vs. CI Check Lanes

**Date:** 2026-06-12
**Status:** Accepted

## Context

Commit 2919733 ("cargo-deny: add supply-chain gate to make check") added `cargo deny` to the `make check` target without ensuring the tool is available on the GitHub Actions runner. The `dtolnay/rust-toolchain` action installs only the stable Rust toolchain (rustup, cargo, rustc, clippy); it does not install external cargo subcommands such as `cargo-deny`. The result: every CI run fails immediately with `error: no such command: 'deny'`.

Supporting analysis is in the sibling file `exploration.md`, which surveyed all options in detail.

### Options considered

1. **`cargo install cargo-deny --locked` in CI** — straightforward but adds ~30–60 s of compile time per run; version must be maintained independently.
2. **Third-party binstall action** — faster binary install but adds an action dependency with its own supply-chain surface.
3. **Binary caching (Swatinem/rust-cache)** — mitigates the compile-time cost of option 1 but adds caching complexity and invalidation concerns.
4. **Conditional/skippable gate** — gate silently no-ops in CI unless an env var is set; defeats the purpose of having a supply-chain gate.
5. **`[workspace.metadata.tools]` / Cargo `[tool]`** — not yet stable in Rust; blocked on toolchain.
6. **Custom container image** — high maintenance burden; inflexible.
7. **Split check into local vs. CI lanes (this ADR)** — omit cargo-deny from CI entirely; enforce it only via the local pre-commit hook.

Options 1–3 all require adding cargo-deny to CI one way or another. The team decided this cost is not worthwhile given that:
- cargo-deny checks advisories, license allow-lists, and source allow-lists against a RustSec database fetch; these checks are primarily useful as a "did something drift since I last looked" signal.
- The local pre-commit hook runs `make check` (the heavy lane) on every commit attempt, so advisory/supply-chain drift is caught before code lands.
- Installing and pinning additional tools in CI increases the CI surface area and maintenance burden.

## Decision

Split the `make check` family into three targets:

- **`check-common`** — the shared base; runs every check except `cargo-deny`. Both lanes run this.
- **`check`** — the local/precommit lane; runs `check-common` then `cargo-deny`. The git pre-commit hook runs this target.
- **`check-ci`** — the CI lane; runs `check-common` only. `cargo-deny` is deliberately absent because it is not installed on the GitHub Actions runner.

CI workflow (`ci.yml`) now calls `make check-ci`. The local pre-commit hook (`.git/hooks/pre-commit`) already calls `make check` and is unchanged.

Strong anti-drift comments in the Makefile require that any new check step be added to `check-common` so both lanes pick it up. Adding a step directly to `check` or `check-ci` (other than the sanctioned `cargo-deny` line on `check`) is explicitly forbidden by those comments.

## Consequences

- **CI does NOT independently detect new RustSec advisories, license violations, or banned/source violations.** This is an accepted trade-off. The local pre-commit hook compensates, but only when developers actually push commits from a machine with cargo-deny installed.
- New contributors who clone the repository and run `make check` without cargo-deny installed will get a clear failure at the `cargo-deny` step. They should install cargo-deny via `cargo install cargo-deny`.
- `make check-ci` is safe to run without cargo-deny installed; it omits the advisory/supply-chain gate.
- Drift between `check` and `check-ci` is mitigated structurally (shared `check-common`) and editorially (mandatory Makefile comments). No automated test enforces the anti-drift rule; it relies on code review.
