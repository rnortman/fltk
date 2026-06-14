# Audit: bespoke native path removal — HEAD e4c178d

Branch: codegen-rust-lib-boilerplate  
Audited: 2026-06-14  
Verdict: **ENTIRELY REMOVED**

---

## 1. Checklist items

### 1.1 `native_spec` — definition, calls, imports, tests

**Live code (`.py`, `.rs`, `.bzl`, `.bazel`, `.toml`):** zero occurrences.

The only hits across the entire repo are in:
- `fltk/fegen/test_gsm2lib_rs.py:141` — a comment: `# This replaces the deleted native_spec() and gen-rust-native-lib tests.`
- `fltk/fegen/test_genparser.py:1` — module docstring: `"""Tests for gen-rust-cst, gen-rust-parser, gen-rust-lib, and gen-rust-native-lib CLI subcommands."""`
- `fltk/fegen/test_genparser.py:449` — a comment: `# Tests the generalized flags that replace the deleted gen-rust-native-lib command.`
- Historical design/ADR docs under `docs/` — not executable, not imported.

None of these are functional references. `native_spec` is not defined or imported anywhere in live code.

**`test_gsm2lib_rs.py` import line (line 7):**
```python
from fltk.fegen.gsm2lib_rs import LibSpec, RustLibGenerator, Submodule
```
`native_spec` is absent from the import. The old test block `test_native_spec_*` is gone; replaced by `test_span_only_*` (lines 139–226).

### 1.2 `gen-rust-native-lib` / `gen_rust_native_lib` CLI command

**Live code:** zero occurrences.

`genparser.py` defines exactly one `@app.command(name="gen-rust-lib")` at line 400 (`gen_rust_lib`). No `gen-rust-native-lib` command exists. The Makefile has no `gen-rust-native-lib` invocation.

### 1.3 Native-specific branches or conditionals in `gsm2lib_rs.py` and `genparser.py`

**`gsm2lib_rs.py`** (181 lines total): no `if ... native`, no hardcoded `"fltk._native"` or `"_native"` strings, no `native_spec` function. The only conditionals are:
- `gsm2lib_rs.py:116` — `if spec.submodules:` (general: gates `register_submodule` import)
- `gsm2lib_rs.py:124` — `if spec.register_span_types:` (general flag)
- `gsm2lib_rs.py:131` — `if spec.register_span_types:` (general flag)
- `gsm2lib_rs.py:140` — `if spec.unknown_span_static:` (general flag)
- `gsm2lib_rs.py:153` — `if spec.register_span_types:` (general flag)
- `gsm2lib_rs.py:158` — `if spec.unknown_span_static:` (general flag)
- `gsm2lib_rs.py:168` — `if (spec.register_span_types or spec.unknown_span_static) and spec.submodules:` (general: separator between span-init block and submodule-registration block)

All are driven by `LibSpec` fields, not by any native-specific condition. `_native` is mentioned only in a comment at line 61 (the `module_name` docstring example) and in the inline comment at line 139 — both documentation, not control flow.

**`genparser.py` `gen_rust_lib` (lines 400–478):** the only branching is:
- `genparser.py:451` — guard that rejects `--register-span-types`/`--unknown-span-static` without `--no-cst` (general: prevents a nonsensical combination)
- `genparser.py:458` — `if no_cst:` constructs a `LibSpec` directly with `submodules=()`; else calls `LibSpec.standard(...)` (general: selects which constructor to use)

The docstring at `genparser.py:440–449` mentions `fltk._native` in an example invocation. That is documentation, not a code branch. No conditional checks for the module name `_native` or any other native-specific string.

### 1.4 How `fltk._native` `src/lib.rs` is generated now

**Makefile, `gencode` target, lines 265–267:**
```makefile
# Rust: src/lib.rs (fltk._native module wiring — span-only runtime, no grammar submodules)
uv run python -m fltk.fegen.genparser gen-rust-lib src/lib.rs \
    --module-name _native --register-span-types --unknown-span-static --no-cst --no-parser
```

This is the same `gen-rust-lib` subcommand a downstream consumer uses (e.g. Clockwork). The three flags `--register-span-types`, `--unknown-span-static`, and `--no-cst` are general-purpose flags on the shared command — not native-specific code paths. A downstream consumer could supply the same flags to produce a span-only runtime lib. The flags exist as general capabilities, not as a bespoke interface to serve `_native` specifically.

### 1.5 Bazel: `rust.bzl`, `BUILD.bazel`, `MODULE.bazel`

No occurrences of `native_spec` or `gen-rust-native-lib` in any Bazel file.

`rust.bzl` defines a general `generate_rust_lib` Bazel rule (lines 58–98) that accepts `module_name`, `no_cst`, `register_span_types`, `unknown_span_static` as attrs and passes them as flags to `gen-rust-lib`. This is the same general mechanism; no `_native`-specific branch exists.

`BUILD.bazel` uses `fltk_pyo3_cdylib` for:
- `:native` (lines 32–64): the `fltk._native` cdylib itself — compiled from committed `src/lib.rs`, not generated via the Bazel `generate_rust_lib` rule. This is the extension crate, not a consumer crate using the macro to generate its lib.rs.
- `:bootstrap_native` (lines 121–126): smoke target for the no-`lib_rs` branch of `fltk_pyo3_cdylib` (uses `generate_rust_lib` auto-generation with default standard flags, no span flags).

Neither BUILD target uses a `gen-rust-native-lib` command or `native_spec`.

### 1.6 `TODO.md`

No entries for `native-lib`, `native_lib`, `gen-rust-native`, or `native_spec`.

The four TODOs in the live codebase relevant to this area are:
- `TODO(rust-ident-dedup)` — `gsm2lib_rs.py:16` — regex deduplication nit
- `TODO(submodule-register-fn-convention)` — `gsm2lib_rs.py:49` — convention doc
- `TODO(native-span-init-error-context)` — `gsm2lib_rs.py:159` — error message quality
- `TODO(bazel-lib-rs-no-cst)` — `rust.bzl:311` — assembly genrule does not support span-only crates via the macro

None are residue of the old bespoke path; all are independent polish items surfaced during review.

---

## 2. Classification of remaining references

| Location | Text | Class |
|---|---|---|
| `fltk/fegen/test_gsm2lib_rs.py:141` | comment noting what was deleted | comment, harmless |
| `fltk/fegen/test_genparser.py:1` | module docstring listing old commands | docstring, harmless |
| `fltk/fegen/test_genparser.py:449` | comment noting replacement | comment, harmless |
| `fltk/fegen/gsm2lib_rs.py:61` | `module_name` field docstring example `'clockwork_native'` | docstring, harmless |
| `fltk/fegen/gsm2lib_rs.py:139` | inline comment mentioning `fltk._native` as motivating use case | comment, harmless |
| `fltk/fegen/genparser.py:441` | docstring: "Used for fltk._native" | docstring, harmless |
| `fltk/fegen/genparser.py:449` | example invocation in docstring | docstring, harmless |
| `docs/**` | historical design/ADR/review docs | documentation, not executable |

No live code reference is a control-flow branch keyed on `_native`, `native_spec`, or `gen-rust-native-lib`.

---

## 3. Verdict

**ENTIRELY REMOVED.**

`native_spec()` is deleted from `gsm2lib_rs.py`. The `gen-rust-native-lib` CLI command is deleted from `genparser.py`. The Makefile gencode target now invokes the generalized `gen-rust-lib` with `--no-cst --register-span-types --unknown-span-static --module-name _native`. The Bazel `generate_rust_lib` rule exposes the same three flags as general attrs. The test suites (`test_gsm2lib_rs.py`, `test_genparser.py`) have been updated: the old `test_native_spec_*` and `test_gen_rust_native_lib_output` tests are replaced by `test_span_only_*` and `test_gen_rust_lib_span_only_output` tests that exercise the generalized flag path. All remaining mentions are comments or documentation strings referencing the old path in the past tense, or illustrative examples in docstrings; none are operational code.
