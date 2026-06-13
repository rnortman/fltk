# cargo-deny CI Installation Investigation

## Problem Statement
CI `make check` fails with "cargo deny --manifest-path Cargo.toml check: error: no such command: `deny`" on the GitHub Actions runner, despite the gate being committed and functional locally.

## Relevant Makefile Targets

**File: `/home/rnortman/src/fltk/Makefile:123-127`**

The `cargo-deny` target is defined and invoked as part of `make check`:

```makefile
cargo-deny:
	cargo deny --manifest-path Cargo.toml check --config deny.toml
	cargo deny --manifest-path tests/rust_cst_fegen/Cargo.toml check --config deny.toml
	cargo deny --manifest-path tests/rust_cst_fixture/Cargo.toml check --config deny.toml
	cargo deny --manifest-path tests/rust_parser_fixture/Cargo.toml check --config deny.toml
```

It is wired into the `check` target at **line 12**:

```makefile
check:
	@steps="lint format-check typecheck test cargo-check cargo-clippy cargo-test cargo-test-python-features cargo-test-no-python cargo-clippy-no-python check-no-pyo3 cargo-deny"; \
```

The exact command failing in CI is at **line 124**: `cargo deny --manifest-path Cargo.toml check --config deny.toml`

## How CI Invokes `make check`

**File: `/home/rnortman/src/fltk/.github/workflows/ci.yml`**

The CI workflow structure:
- **Line 14-16**: Checks out the repository
- **Line 18-22**: Installs `uv` (Python package manager) and Python 3.10
- **Line 25-28**: Installs the Rust toolchain using `dtolnay/rust-toolchain@e97e2d8cc328f1b50210efc529dca0028893a2d9` pinned action with `toolchain: stable`
- **Line 30-31**: Runs `make check` (the canonical entry point)

**Key gap**: There is NO step to install `cargo-deny` or any other Rust tools beyond the stable toolchain.

## How Other Rust Tools Get Installed

**Comparison of tool installation:**

1. **rustup/cargo** (lines 25-28): Installed automatically by `dtolnay/rust-toolchain` action, which manages the Rust stable toolchain. `cargo` is part of the standard toolchain.

2. **maturin** (Makefile lines 135, 140, 147, 152): Used via `uv run --group dev maturin develop`. Maturin is listed in `pyproject.toml` as:
   - **Build requirement**: `requires = ["maturin>=1.7,<2"]`
   - **Dev group**: `dev = ["maturin>=1.7,<2"]`
   - Thus `uv` provides it when invoked with `--group dev`

3. **cargo-deny**: Unlike maturin (managed by uv), cargo-deny is a Rust binary tool. Currently:
   - NOT declared as a dependency in `Cargo.toml` or `pyproject.toml`
   - NOT installed by the `dtolnay/rust-toolchain` action (only installs `rustup`, `cargo`, `rustc`, and `clippy`)
   - Works locally because it's pre-installed in the developer's `~/.cargo/bin/`
   - **Not available on the GitHub Actions runner**

## deny.toml Presence and Contents

**File: `/home/rnortman/src/fltk/deny.toml`** (40 lines)

Shared policy file used across all four workspaces (root + 3 test fixtures via `--config deny.toml` flag in Makefile).

Key sections:
- **[advisories]**: RustSec advisory database (v2); fails on unfixed vulnerabilities or yanked crates
- **[licenses]**: Allows MIT, Apache-2.0, Apache-2.0 WITH LLVM-exception, Unicode-3.0
- **[licenses.private]**: Exempts first-party unpublished crates (`publish = false`)
- **[bans]**: Warns on multiple versions; allows wildcards
- **[sources]**: Requires registry/git sources to be from allow-listed GitHub crates.io-index

No advisories are currently exempted or ignored in this file.

## Root Cause

Commit `2919733` ("cargo-deny: add supply-chain gate to make check") added the gate without ensuring the tool is installed in CI. The `dtolnay/rust-toolchain` action installs only the stable toolchain components (rustup, cargo, rustc, clippy), not external cargo subcommands like `cargo-deny`.

## Options for Fixing

### Option 1: Install via `cargo install` in CI
**File modification**: `.github/workflows/ci.yml:30` (before "Run checks" step)

Add a step:
```yaml
- name: Install cargo-deny
  run: cargo install cargo-deny --locked
```

**Tradeoffs**:
- **Pros**: Simple, uses standard Rust tooling; `--locked` pins exact version for reproducibility
- **Cons**: Adds ~30-60s per CI run (compilation time on the runner); version drift if not maintained; cargo-deny updates independently from Rust toolchain

### Option 2: Install via third-party `binstall` action
Alternative: Use a pre-compiled binary action (e.g., `cargo-binstall/action`)

**Tradeoffs**:
- **Pros**: Faster than `cargo install` (precompiled binary); better for frequently-updated tools
- **Cons**: Adds action dependency; binary availability not guaranteed for all platforms

### Option 3: Pin version and cache compiled binary
Extend Option 1 with GitHub Actions caching:

```yaml
- uses: Swatinem/rust-cache@23bce251a8cd2ffc3c1075fab17578c3545ca2b2  # v3
  with:
    cache-targets: cargo-deny
```

**Tradeoffs**:
- **Pros**: First run ~60s, subsequent runs ~5-10s due to cache hit
- **Cons**: Adds caching overhead; cache must be invalidated if cargo-deny version constraint changes

### Option 4: Make the gate conditional/skippable
Modify Makefile to allow opting out:

```makefile
cargo-deny:
	@if command -v cargo-deny >/dev/null 2>&1; then \
		cargo deny --manifest-path Cargo.toml check --config deny.toml; \
	else \
		echo "cargo-deny not installed; skipping (set CI_REQUIRE_DENY=1 to fail)"; \
	fi
```

**Tradeoffs**:
- **Pros**: No CI changes needed; preserves local dev behavior; graceful degradation
- **Cons**: Gate is ineffective in CI unless an env var is explicitly set; defeats supply-chain protection goal; developers might not notice missing checks

### Option 5: Declare cargo-deny as a workspace tool dependency (Nightly Rust feature)
Use `[workspace.metadata.tools]` or `cargo.toml` `[tool]` section when stabilized:

**Tradeoffs**:
- **Pros**: Centralizes tool management; future-proof with stable Cargo
- **Cons**: Requires Nightly; not yet stable; unclear release timeline

### Option 6: Use a container image with pre-installed tools
Modify CI to run in a custom container with cargo-deny pre-baked.

**Tradeoffs**:
- **Pros**: Solves all tool installation atomically
- **Cons**: Maintenance burden; slower cold starts; inflexible if tools change

## Local Development Assumptions

**Current state**:
- `make check` locally requires `cargo-deny` to be pre-installed (e.g., via `cargo install cargo-deny`)
- **No documentation** in `CLAUDE.md` or project README mentions this requirement
- **No setup guide** in `docs/` or inline Makefile comments explains how to install it

**Implications**:
- New developers cloning the repo will encounter a failure when running `make check` with no guidance
- The Makefile comments at **lines 119-122** explain the intent but not the installation requirement

## Recommendations for Investigation Closure

This investigation **does not prescribe a choice** but notes:
- **Option 1** (cargo install in CI) is the most straightforward and aligns with how local developers would install it
- **Option 3** (with caching) balances simplicity with CI performance
- **Option 4** (conditional/skippable) should only be chosen if supply-chain checks are not required to pass CI
- **Local development guide** should be added to `CLAUDE.md` documenting the setup requirement regardless of CI choice
