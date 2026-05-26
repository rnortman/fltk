# Phase 0 Design: Rust/PyO3 Infrastructure Bootstrap

Concise. Precise. No padding. Audience: smart human/LLM implementing this phase.

---

## Root Cause / Context

Phase 0 establishes build infrastructure for the PyO3 CST project. The repo has no Rust tooling. `pyproject.toml` uses `setuptools>=61` (lines 1-3) with `packages = ["fltk"]` (line 28). No `Cargo.toml`, no `src/` directory, no maturin. MODULE.bazel has only `rules_python` (lines 5-19). The entire subsequent phase chain (Span PoC, nested enum PoC, generator, runtime integration) depends on a working mixed Python/Rust build.

Requirements reference: `phase-plan.md` lines 19-37.

---

## Proposed Approach

### Part A: Maturin Build Migration

**Files created:**
- `/home/rnortman/src/fltk/Cargo.toml`
- `/home/rnortman/src/fltk/src/lib.rs`

**Files modified:**
- `/home/rnortman/src/fltk/pyproject.toml`
- `/home/rnortman/src/fltk/.gitignore`
- `/home/rnortman/src/fltk/TODO.md`
- `/home/rnortman/src/fltk/MODULE.bazel` (TODO comment only)

#### Cargo.toml

```toml
[package]
name = "fltk-native"
version = "0.1.0"
edition = "2021"

[lib]
name = "fltk_native"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.23" }
```

The crate name uses a hyphen (Cargo convention); the `lib.name` uses underscore (Python module naming requirement). Version `0.23` is the current stable PyO3 release line. The `extension-module` feature is intentionally omitted from Cargo.toml — it is enabled via `[tool.maturin] features = ["pyo3/extension-module"]` so that `cargo test` (if used later) can still link libpython normally.

#### src/lib.rs

Minimal `#[pymodule]` exposing `fltk._native` with a single `Ping` class. The function name must be `_native` (not `fltk_native`) because maturin's dotted `module-name` requires the `#[pymodule]` function name to match the final path component — Python looks for `PyInit__native`:

```rust
use pyo3::prelude::*;

#[pyclass]
struct Ping;

#[pymethods]
impl Ping {
    #[new]
    fn new() -> Self { Ping }

    fn pong(&self) -> &str { "pong" }
}

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Ping>()?;
    Ok(())
}
```

#### pyproject.toml changes

Replace `[build-system]`:
```toml
[build-system]
requires = ["maturin>=1.7,<2"]
build-backend = "maturin"
```

Remove `[tool.setuptools]` section (line 27-28).

Add `[tool.maturin]`:
```toml
[tool.maturin]
python-packages = ["fltk"]
module-name = "fltk._native"
features = ["pyo3/extension-module"]
```

`python-packages = ["fltk"]` explicitly tells maturin which Python package to include — avoids auto-discovery picking up `docs/`, `src/`, or stray top-level directories. `module-name = "fltk._native"` places the compiled `.so` as a submodule of `fltk`.

Add `dev` dependency group:
```toml
[dependency-groups]
dev = ["maturin>=1.7,<2"]
```

#### .gitignore additions

```
target/
*.so
*.pyd
*.dylib
```

#### CI changes (`.github/workflows/ci.yml`)

Switching build-backend to maturin means `uv run` will invoke maturin (which requires `rustc`/`cargo`) when syncing the project. CI currently installs only uv + Python. Without Rust, the editable install fails and *all* CI steps (lint, typecheck, test) break — not just `test_native.py`.

Add to CI before `make check`:
```yaml
      - name: Install Rust toolchain
        uses: dtolnay/rust-toolchain@stable

      - name: Build Rust extension
        run: uv run --group dev maturin develop
```

This ensures the native extension is built before any `uv run` step attempts to sync/build the package. The `dtolnay/rust-toolchain` action is the standard, lightweight Rust installer for CI.

#### Development workflow change

After migration, the build-and-test workflow is:
```bash
uv run --group dev maturin develop && uv run pytest
```

Debug builds (`maturin develop` without `--release`) are the default for development — fast compile, adequate for correctness testing. Document this in CLAUDE.md.

#### Bazel gap

Add a TODO comment in `MODULE.bazel`:
```python
# TODO(bazel-rules-rust): Add rules_rust for building the PyO3 extension via Bazel.
```

Add corresponding entry to `TODO.md`.

### Part B: Smoke Test for Rust Extension

**File created:**
- `/home/rnortman/src/fltk/fltk/test_native.py`

```python
import pytest

native = pytest.importorskip("fltk._native", reason="Rust extension not built — run `maturin develop`")

def test_ping():
    assert native.Ping().pong() == "pong"
```

Uses `pytest.importorskip` so the test skips with a clear message when the extension is not built, rather than failing with an opaque `ModuleNotFoundError`. Acceptance criterion from `phase-plan.md` line 36.

**Pyright compatibility**: `pytest.importorskip` returns `Any`, so pyright will not flag attribute access on the result. Verify `uv run pyright` passes with this file before merging. If pyright does flag `fltk._native` as unresolvable, add a `# type: ignore[import-not-found]` on the `importorskip` line or exclude test files from the pyright `include` list.

---

## File Summary

| File | Action | Purpose |
|------|--------|---------|
| `Cargo.toml` | Create | Rust crate config with PyO3 dep |
| `src/lib.rs` | Create | Minimal pymodule with Ping class |
| `pyproject.toml` | Modify | setuptools -> maturin, add maturin config |
| `.github/workflows/ci.yml` | Modify | Add Rust toolchain + maturin develop step |
| `.gitignore` | Modify | Add `target/`, `*.so`, `*.pyd`, `*.dylib` |
| `TODO.md` | Modify | Add `bazel-rules-rust` entry |
| `MODULE.bazel` | Modify | Add TODO comment |
| `fltk/test_native.py` | Create | Rust extension smoke test |
| `CLAUDE.md` | Modify | Document `maturin develop` workflow |

---

## Edge Cases / Failure Modes

### Rust toolchain required for all development
With maturin as build-backend, `uv run` invokes maturin to sync the project, which requires `rustc` and `cargo`. A machine without Rust cannot run *any* `uv run` command — not just `test_native.py`.

**Mitigation**: Document `rustup` as a development prerequisite in CLAUDE.md. CI installs it explicitly (see "CI changes" above). This is a deliberate trade-off: the Rust extension is not optional infrastructure — it is the project's direction.

### PyO3 version vs Python version compatibility
PyO3 0.23 supports Python 3.8+. The project targets Python 3.10+. No conflict expected. However, PyPy (listed in classifiers, line 23) has limited PyO3 support.

**Mitigation**: PyPy support for the Rust extension is not a Phase 0 goal. The extension is additive — PyPy users fall back to pure Python in later phases. No action needed now, but note that classifiers may eventually need updating.

### Existing `fltk.egg-info/` directory
The repo has `*.egg-info` in `.gitignore`, suggesting an editable setuptools install exists. After switching to maturin, stale `.egg-info` metadata could confuse Python's import system.

**Mitigation**: Delete `fltk.egg-info/` as part of the migration. Document in commit message.

---

## Test Plan

After Phase 0, the following tests exist:

1. **`fltk/test_native.py::test_ping`** — Verifies the Rust extension loads and the `Ping` class works. Acceptance criterion: `from fltk._native import Ping; assert Ping().pong() == "pong"`.

2. **All existing tests pass unchanged** — `uv run pytest` (after `maturin develop`) produces zero new failures. This is validated by running the full test suite as the final CI step.

The native smoke test skips via `pytest.importorskip` when the extension is not built.

---

## Open Questions

None.
