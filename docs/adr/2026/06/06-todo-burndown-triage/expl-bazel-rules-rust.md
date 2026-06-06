# TODO Burndown: `bazel-rules-rust` Adversarial Verification

Concise, token-dense. No fluff, no prescriptions.

## Claim verification

### "Location: `MODULE.bazel`"

VERIFIED. `MODULE.bazel:5` contains the TODO comment exactly:

```
# TODO(bazel-rules-rust): Add rules_rust for building the PyO3 extension via Bazel.
```

`MODULE.bazel:7` has only `bazel_dep(name = "rules_python", version = "1.5.0")` — no `rules_rust` dep. The rest of the file (lines 9–21) configures `rules_python` Python/pip toolchains only. Nothing Rust-related exists in `MODULE.bazel`.

### "Currently, Bazel builds do not include the Rust extension"

VERIFIED. `BUILD.bazel:23–26` defines the `fltk` py_library target:

```python
py_library(
    name = "fltk",
    srcs = glob(["**/*.py"]),
    ...
)
```

The glob pattern is `**/*.py` only — no `.so`, `.pyd`, `.dylib`, or any artifact from the Rust build. `BUILD.bazel` has zero references to `_native`, `fltk._native`, or any Rust build target. `WORKSPACE.bazel` is a single empty line.

### "PyO3 native extension (`fltk._native`)"

VERIFIED. The extension is named `fltk._native` per:
- `pyproject.toml:29`: `module-name = "fltk._native"`
- `src/lib.rs:21`: `#[pymodule] fn _native(...)`
- `Cargo.toml:7–8`: `name = "fltk_native"`, `crate-type = ["cdylib"]`

The extension exposes `Span`, `SourceText`, `UnknownSpan`, and CST node classes via PyO3.

## Current build state

The extension is built exclusively by maturin:
- `Makefile:build-native`: `uv run --group dev maturin develop`
- CI (`.github/workflows/ci.yml`): `make build-native build-test-user-ext build-fegen-rust-cst`

There are three separate cdylib crates: `Cargo.toml` (fltk._native), `tests/rust_cst_fegen/Cargo.toml` (fegen_rust_cst), `tests/rust_cst_fixture/Cargo.toml` (phase4_roundtrip_cst). All share the same PyO3 `0.23` / `abi3-py310` configuration. None have Bazel build files.

## Python graceful-degradation at import time

The extension is optional at Python import time:
- `fltk/fegen/pyrt/span.py:16–22`: tries `from fltk._native import SourceText, Span, UnknownSpan`, falls back to pure-Python on `Exception`, emits a `warnings.warn`.
- `fltk/fegen/pyrt/span_protocol.py:59–64`: same try/except pattern for `AnySpan` type union.

This means Bazel-built Python code that does NOT have the native extension available degrades silently to the pure-Python Span backend, not a hard import failure. Bazel consumers are currently in this state.

## Blockers not mentioned in the TODO

1. **Three separate cdylib crates, not one.** The TODO says "add `rules_rust` to `MODULE.bazel`" as if there is a single extension. There are three: `fltk._native`, `fegen_rust_cst`, and `phase4_roundtrip_cst`. The test extensions (`rust_cst_fegen/`, `rust_cst_fixture/`) are separate Cargo workspaces with their own `Cargo.toml`. A Bazel integration would need to decide which of these to expose as Bazel targets and how.

2. **No Cargo workspace.** The three crates are independent (no root `Cargo.toml` workspace). `rules_rust` can handle non-workspace crates but the topology needs to be declared explicitly.

3. **PyO3 abi3 feature flag.** `Cargo.toml:15`: `pyo3 = { version = "0.23", features = ["abi3-py310"] }`. The `extension-module` feature (`Cargo.toml:11`) must be enabled for PyO3 extensions; `rules_rust` requires this to be set correctly. `rules_rust`'s `rust_pyo3_extension` (if using `pyo3_bazel`) or `rust_shared_library` with manual feature flags each have different configuration surface.

4. **`rules_rust` and PyO3 integration complexity.** As of `rules_rust` 0.x, PyO3 support requires either `pyo3_bazel` (separate Bazel module) or manual `rust_shared_library` + feature flag injection. Neither is a trivial one-line `bazel_dep`. The Bazel `MODULE.bazel` Bzlmod registry availability of `rules_rust` and compatible `pyo3_bazel` versions must be verified.

5. **Generated Rust CST user workflow.** The `gen-rust-cst` make target emits Rust source that downstream consumers compile into their own cdylib (see `tests/rust_cst_fegen/` as the dogfood example). A Bazel integration would also need a Bazel macro analogous to `generate_parser` in `rules.bzl` that compiles the generated Rust source. This is not mentioned in the TODO.

## Is this papering over a symptom?

No deeper structural problem. The Python fallback (`span.py:16–22`) means existing Bazel consumers of the pure-Python path are not broken — they get warnings, not errors. The TODO correctly identifies the gap: Bazel cannot build the Rust CST path (Rust backends, faster Span) for its consumers. The work is genuinely additive, not a fix for a hidden breakage.

## TODO accuracy verdict

The TODO text is accurate as a one-sentence description but understates scope. The cited file (`MODULE.bazel`) and the described gap (no `rules_rust`, extension not buildable via Bazel) are verified correct. The phrase "Add `rules_rust` to `MODULE.bazel`" implies a single small change; the actual work spans multiple crates, PyO3 Bazel integration, and likely a new Bazel macro for the generated-Rust-CST user workflow.
