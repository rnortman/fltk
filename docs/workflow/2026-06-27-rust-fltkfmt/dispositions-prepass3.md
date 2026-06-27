# Dispositions — prepass3

## slop-1

- Disposition: Fixed
- Action: `tests/test_fltkfmt_parity.py` — replaced the `if shutil.which("cargo") is None: pytest.skip(...)` in the `fltkfmt_binary` session fixture (was ~line 97) with an `assert shutil.which("cargo") is not None` hard failure, and updated the module docstring (lines 13-16) and fixture docstring to match. The parity guarantee can no longer be silently bypassed by a cargo-absent environment. Verified: `ruff check` clean and all 16 parity tests pass.
- Severity assessment: Real but narrow. The docstring asserted "all-skip is a failure signal" while nothing enforced it; a cargo-less environment would skip all 16 tests and still exit 0, silently dropping the file's stated parity guarantee. CLAUDE.md declares the Rust toolchain mandatory for all contributors, so the skip guarded a state that is never legitimate — making the hard-fail both correct and the reviewer's own preferred fix (option a). Note: the sibling `test_rust_unparser_parity_fixture.py` uses `pytest.importorskip` for a different reason (its Rust *fixture extension* may be unbuilt via a separate optional `make` step); this file's only skip reason was total cargo absence, so the divergence is justified and the sibling needs no change.
