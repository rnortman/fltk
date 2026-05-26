Concise. Precise. No padding. Audience: smart human/LLM.

---

## quality-1

**File**: `.github/workflows/ci.yml`, line 24

**Issue**: `uv run --group dev maturin develop` is a redundant CI step. When `make check` → `uv run --group lint --group test pytest` executes, `uv run` will sync the project, which invokes maturin as the build-backend and builds the extension. The explicit `maturin develop` step before `make check` is thus a double-build that does not prevent any failure mode.

**Consequence**: Every CI run pays an extra Rust compile (~same cost as the real build). Worse, the pattern encodes a false mental model — readers infer that `uv run` does *not* build the extension, so future contributors copy the workaround. If maturin's editable-install semantics ever diverge from `maturin develop` (e.g., path differences), the duplicate could silently shadow real failures.

**Fix**: Remove the "Build Rust extension" step from `ci.yml`. The Rust toolchain step is still needed. If there is a concrete reason `maturin develop` must precede `uv run` (e.g., maturin build-backend does not produce an importable `.so` in-place for editable installs on this uv version), document that reason and add a comment; otherwise delete the redundant step.

---

## quality-2

**File**: `fltk/test_native.py`, line 3 — placed under `fltk/` (the package source tree) rather than a `tests/` or top-level directory

**Issue**: The project's ruff per-file-ignores apply the test linting relaxations only to `tests/**/*` and `**/test_*.py`. The file matches `**/test_*.py`, so that part is fine. However, placing a test file *inside* the installable package (`fltk/`) means the test is shipped as part of the installed package — `fltk.test_native` becomes importable by users. This is an abstraction boundary violation: test infrastructure leaks into the public package namespace.

**Consequence**: Every downstream installation of `fltk` carries `test_native` as an importable module. Future test files added under `fltk/` compound this. pytest discovery from `fltk/` is also non-standard and will confuse tools that treat `fltk/` as the library root.

**Fix**: Move `test_native.py` to a top-level `tests/` directory (consistent with the `tests/**/*` ruff ignore path that already exists). If `maturin` requires the smoke test to live inside the package for some build reason, document that explicitly.

---

No other findings.
