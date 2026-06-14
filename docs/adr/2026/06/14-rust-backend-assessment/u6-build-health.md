# u6 — Live Build / Test Health (ground-truth)

Agent task: actually run the builds and tests. Measure, do not speculate. Do not fix.

- Repo HEAD at measurement: `c0182064e2f6906fb5cf836b025980beca44cab3` (clean working tree).
- Toolchain present: `rustc 1.96.0 (ac68faa20 2026-05-25)`, `cargo 1.96.0`, `uv` (system), `cargo-deny 0.19.8`, `pyright` (in venv), managed CPython 3.10 (uv). `maturin` only via the `dev` uv group (not on PATH — expected).
- Machine note: builds were measured on a fast machine with warm Cargo registry/incremental caches. Absolute timings (≈5s cold compile, 59s full `make check`) are NOT representative of a true first-ever checkout that must also download the crate registry. They are valid for "does it reproduce green," not for capacity planning.

## BOTTOM LINE

Everything builds and everything is green. The full precommit gate `make check` passes end-to-end, exit 0. This is a genuinely healthy, well-instrumented build — not a "green because nothing runs" situation. I actively probed for hidden skips, suppressed warnings, ignored tests, and feature-matrix gaps; the gate holds up.

The only soft spots are (a) Python Rust-backed tests SILENTLY skip via `pytest.importorskip` if a fixture extension is not pre-built — green-by-default-when-absent, not green-by-passing; and (b) a few harmless config-slack warnings (deny.toml unused license entries). Neither is a correctness problem. There are zero compiler warnings, zero clippy warnings under `-D warnings` across the full feature matrix, and zero `#[ignore]`d tests.

## 1. maturin develop (native extension)

`uv run --group dev maturin develop` → **SUCCESS**.
- Found CPython 3.10 in venv, pyo3 abi3 support, features from pyproject.toml.
- Compiled pyo3-ffi, pyo3, fltk-cst-core, fltk-native; `Finished dev profile in 1.75s`.
- Built `fltk-0.1.1-cp310-abi3-linux_x86_64.whl`, installed editable. `Installed fltk-0.1.1`.

## 2. pytest

`uv run pytest -q` → **1700 passed, 0 failed, 0 skipped, 0 xfail, 0 warnings, 29.0s.**
- `pytest --collect-only` = 1700 collected → all 1700 actually ran (no silent collection-time skips).
- Re-run with `-rs` (report skips): no skip section emitted → confirmed zero skips on THIS environment.

CRITICAL CAVEAT — the 0-skips result is environment-conditional, not unconditional:
- The Rust-backed tests guard their imports with `pytest.importorskip(...)`. If the fixture extension is not installed, those tests SKIP silently rather than fail. All four fixture modules happened to be pre-installed in the venv from a prior build, so they ran here:
  - `import phase4_roundtrip_cst / fegen_rust_cst / rust_parser_fixture / poc_cst` all succeed (verified directly).
- `importorskip`-gated test files (these are the cross-backend / Rust-parity surface): `test_module_split.py`, `test_phase4_rust_fixture.py`, `test_phase4_fegen_rust_backend.py`, `test_fegen_rust_cst.py`, `test_rust_cst_poc.py`, `test_rust_parser_bindings.py`, `test_rust_parser_fixture_bindings.py`, `test_rust_parser_parity_fixture.py`, `test_rust_parser_parity_fegen.py`, `test_cross_backend_label_equality.py`, `test_cst_mutators_identity.py`, `test_cst_mutators_parity.py`, `test_registry_gc_eviction.py`, `test_rust_span.py` (many `importorskip` call sites at lines 391–779).
- `pyright`-gated tests (`test_gsm2tree_rs.py:2149`, `test_clean_protocol_consumer_api.py:94`, `pyright_test_utils.py:36`) skip if pyright is missing — pyright IS present here, so they ran.
- `test_nullable_loop_guard.py:337` skips if `cargo` not on PATH — cargo present, ran.
- WHY THIS MATTERS for production-readiness: a bare `uv run pytest` on a fresh checkout (no fixtures built) would report "all passed" while having skipped the entire Rust-parity/cross-backend surface. The Makefile defends against this: `test:` depends on `build-test-fixtures` (build-native + build-test-user-ext + build-fegen-rust-cst + build-rust-parser-fixture + build-poc-cst), so `make test` / `make check` always builds the five extensions first. The protection lives in the Makefile, NOT in pytest itself. A consumer running raw pytest gets a misleadingly-green result.

## 3. Cargo (per Makefile lanes — the real CI behavior)

Plain `cargo test -q` at the workspace root runs only the `fltk-native` cdylib's tests = **0 tests**. It does NOT transitively run the library-crate tests, because the root default member is the `fltk-native` cdylib whose `default = ["extension-module"]` activates `pyo3/extension-module` (no libpython link → standalone test bins can't run). This is exactly why the Makefile drives tests via explicit `-p` / `--manifest-path` selection rather than a workspace-wide `cargo test`. Ran all Makefile lanes:

cargo-test-no-python lane (all exit 0):
- `fltk-cst-core --no-default-features`: 38 passed
- `fltk-cst-spike`: 43 passed
- `fltk-parser-core`: 56 + 13 = 69 passed (lib + integration bins)
- `tests/rust_parser_fixture` (default): 59 passed
- `crates/fegen-rust --no-default-features`: 7 passed
- `tests/rust_poc_cst --no-default-features`: 0 passed (no rust unit tests; covered via Python bindings)

cargo-test-python-features lane (exit 0):
- `fltk-cst-core --features python` (libpython linked via `PYO3_PYTHON=<uv managed 3.10>`): 42 passed (4 more than the no-python build → 4 python-gated tests).

Approx Rust test total exercised: 42 + 43 + 69 + 59 + 7 = **220 Rust tests** (counting cst-core once under the python build; +0 poc, +0 root cdylib).

clippy `-D warnings`, FULL feature matrix — every lane exit 0, **zero warnings**:
- python-on: workspace, fegen-rust, rust_poc_cst, rust_parser_fixture(--features python).
- no-python: fltk-cst-core(--no-default-features), fltk-cst-spike, fltk-cst-spike(--features python), fltk-parser-core, rust_parser_fixture, fegen-rust(--no-default-features), rust_poc_cst(--no-default-features).
- Fresh recompile of `fltk-parser-core` (touched lib.rs to defeat cache): 0 warnings — confirms the green is not a stale-cache artifact.

check-no-pyo3 (mechanical pyo3-absence proof on python-off graphs): PASS — "pyo3 absent from python-off graphs". Confirms structural pyo3 isolation of the no-Python lane.

cargo-deny (supply-chain gate, all 5 manifests): exit 0 — `advisories ok, bans ok, licenses ok, sources ok` on every manifest. Two non-fatal warnings: `license-not-encountered` at deny.toml:16 (`Apache-2.0 WITH LLVM-exception`) and :17 (`Unicode-3.0`) — allow-listed licenses that no current dependency uses (forward-looking allow-list slack, not a failure).

## 4. Warnings / suppressions / ignored / counts

- Compiler warnings: 0 (cold full-workspace `cargo build --workspace`: 0 warnings, 0 errors).
- Clippy warnings under `-D warnings`: 0 across entire matrix (any warning would have failed the lane).
- `#[ignore]`d Rust tests: **0** (grep across crates/ src/ tests/, excl target/). No quarantined tests.
- `#[allow(...)]` suppressions (excl target/): 189 occurrences across 8 files — but composition matters:
  - 120 `unused_imports` + 68 `non_snake_case` = 188, ALL inside GENERATED `cst.rs` files (rust_parser_fixture 21, rust_cst_fegen 14, fegen-rust 14, rust_cst_fixture 7, collision_cst 6, rust_poc_cst 3, fltk-cst-spike 3). These are blanket allows the code generator emits so generated CST modules with conditional `#[cfg(feature="python")]` imports and grammar-derived non-snake-case identifiers compile clean. Defensible for generated code, but it means clippy/rustc lint coverage over the GENERATED surface (the public API) is effectively disabled for those two lints — generated-code lint blind spot worth noting.
  - 1 hand-written runtime allow: `crates/fltk-cst-core/src/span.rs:64` `#[allow(clippy::should_implement_trait)]` on `Span::from_str` — justified inline ("Intentional: not FromStr; construction from &str is the natural API name").
  - Note: generated `cst.rs` files carry NO "DO NOT EDIT / @generated" header (verified head of crates/fegen-rust/src/cst.rs). Drift/hand-edit detection relies entirely on the `make gencode` + `git diff` cheat-detection flow, not an in-file banner.
- `unsafe` in runtime crates: 3 total, all in `crates/fltk-cst-core/src/cross_cdylib.rs` (lines 86, 112, 331) — all `obj.cast_unchecked::<SourceText|Span>()`, the cross-cdylib ABI downcast guarded by the sentinel mechanism. Zero `unsafe` elsewhere in fltk-cst-core/src, fltk-parser-core/src, or src/. No `build.rs` anywhere (pyo3 link configured via `PYO3_PYTHON` env, not a custom build script).

## 5. Full gate

`make check` (= check-common + cargo-deny; the local precommit gate): **exit 0, 59.0s wall** (warm caches). Output:
- `check-common: all steps passed (lint format-check typecheck test cargo-check cargo-clippy cargo-test cargo-test-python-features cargo-test-no-python cargo-clippy-no-python check-no-pyo3)`
- `check: all steps passed (check-ci + cargo-deny)`

## 6. Reproducibility / cold build

- `cargo clean` (removed 7.3GiB) then cold `cargo build --workspace`: exit 0, **0 warnings, 0 errors**, `Finished dev in 4.73s` (warm registry; pyo3 sources already fetched). Verified pyo3 was genuinely recompiled (libpyo3 / libpyo3_ffi rlibs present in target/debug/deps).
- All 5 Cargo.lock files committed (root + fegen-rust + the 3 tests/* fixture crates) → pinned, reproducible dependency resolution across the independent workspaces.
- Disk cost of full build cache is large: 6.8G root target + 3.4G fegen-rust + 3.0G rust_cst_fegen + 1.3G rust_cst_fixture + 3.6G rust_parser_fixture + 248M rust_poc_cst ≈ 18.3GiB across six independent target/ trees (six separate Cargo workspaces, each compiling its own pyo3). High disk + redundant-compile cost is a real operational tax of the "many standalone fixture crates" layout, even though it all builds.

## Nothing failed. Nothing could-not-be-run. All four task steps completed on this machine.
