## slop-1

**File:** `tests/test_fltkfmt_parity.py:21` (module docstring, last sentence)

**Quote:**
```
A run where every test here is skipped is a failure signal.
```

**What's wrong:** The skip path is triggered when `shutil.which("cargo") is None`. The module docstring explicitly acknowledges that all-skip is a failure condition, but no mechanism enforces it — when `cargo` is absent, all 16 parametrized tests skip silently and `pytest` exits 0. The docstring warning is unreadable by the test runner.

**Consequence:** The binary parity guarantee is the stated purpose of this entire file. If the CI environment ever lacks `cargo` (or if `cargo` is shadowed by something that fails `which`), the parity guarantee is silently bypassed and the suite still goes green. The docstring itself flags this as a failure — meaning the author knew this was wrong but left the enforcement gap in place. That's a ship-blocker in any test suite that claims correctness coverage.

**Suggested fix:** Either (a) drop the skip entirely and hard-fail when `cargo` is absent (CLAUDE.md already declares the Rust toolchain required for all contributors), or (b) add a session-scoped `autouse` fixture or `pytest_sessionfinish` hook that `pytest.fail`s if the binary was unavailable and all tests were skipped. Option (a) is simpler and consistent with the project's stated toolchain requirements.
