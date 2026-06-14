# FLTK Rust Build & Packaging: Factual Survey

Survey date: 2026-06-13. All citations are file:line in `/home/rnortman/src/fltk/`.

---

## Code Surface

### Cargo workspace

`Cargo.toml:1-3` declares a workspace with members:
```
members = [".", "crates/fltk-cst-core", "crates/fltk-cst-spike", "crates/fltk-parser-core"]
```

The three test crates (`tests/rust_cst_fegen/`, `tests/rust_cst_fixture/`, `tests/rust_parser_fixture/`) each declare `[workspace]` themselves and are intentionally excluded from the root workspace. They have their own `Cargo.lock` files.

### Crates

| Crate name (package) | lib name | crate-type | location |
|---|---|---|---|
| `fltk-native` | `fltk_native` | `cdylib` | `Cargo.toml` (repo root `src/`) |
| `fltk-cst-core` | `fltk_cst_core` | `rlib` | `crates/fltk-cst-core/` |
| `fltk-parser-core` | `fltk_parser_core` | `rlib` | `crates/fltk-parser-core/` |
| `fltk-cst-spike` | `fltk_cst_spike` | `rlib` | `crates/fltk-cst-spike/` |
| `rust-parser-fixture` | `rust_parser_fixture` | `rlib`, `cdylib` | `tests/rust_parser_fixture/` |
| `phase4-roundtrip-cst` | `phase4_roundtrip_cst` | `cdylib` | `tests/rust_cst_fixture/` |
| `fegen-rust-cst` | `fegen_rust_cst` | `cdylib`, `rlib` | `tests/rust_cst_fegen/` |

Sources: `Cargo.toml:1-16`, `crates/fltk-cst-core/Cargo.toml:1-24`, `crates/fltk-parser-core/Cargo.toml:1-28`, `crates/fltk-cst-spike/Cargo.toml:1-24`, `tests/rust_parser_fixture/Cargo.toml:1-21`, `tests/rust_cst_fixture/Cargo.toml:1-23`, `tests/rust_cst_fegen/Cargo.toml:1-24`.

### PyO3 / maturin configuration

- **maturin** is the build backend: `pyproject.toml:1-3` (`requires = ["maturin>=1.7,<2"]`, `build-backend = "maturin"`).
- **Python extension module name**: `fltk._native`. Set at `pyproject.toml:29` (`module-name = "fltk._native"`).
- The compiled artifact is `fltk/_native.abi3.so` (ABI3, Python 3.10+).
- PyO3 version: `0.29`, feature `abi3-py310`: `Cargo.toml:24`, `crates/fltk-cst-core/Cargo.toml:16`.
- The root cdylib entry point: `src/lib.rs:20-38`, function `fn _native(m: ...)` decorated `#[pymodule]`.

### `fltk-cst-core` feature gates

`crates/fltk-cst-core/Cargo.toml:20-23`:
```toml
[features]
default = ["python"]
python = ["dep:pyo3"]
test-introspection = ["python"]
```

- `python` feature: enables pyo3 linkage, `#[pyclass]/#[pymethods]`, cross-cdylib helpers.
- `fltk-parser-core` has **no `python` feature** (`crates/fltk-parser-core/Cargo.toml:12`): "pyo3-freedom is structural absence, not a disabled feature."
- Consumer cdylibs depending on `fltk-cst-core` use `default-features = false` and re-enable `python` via a forwarding feature: pattern shown in `tests/rust_parser_fixture/Cargo.toml:14-16`.

### Root `fltk-native` feature gates

`Cargo.toml:17-21`:
```toml
[features]
default = ["extension-module"]
extension-module = ["python", "pyo3/extension-module"]
python = ["fltk-cst-core/python"]
test-introspection = ["python", "fltk-cst-core/test-introspection"]
```

### Cross-cdylib Span/SourceText ABI protocol

Consumer cdylibs (generated parsers) do not use the same `Span` type-object as `fltk._native`. `fltk-cst-core` handles this via:
- `crates/fltk-cst-core/src/cross_cdylib.rs`: `extract_source_text()`, `extract_span()`, `get_span_type()`, `span_to_pyobject()`.
- ABI gate: `FLTK_CST_CORE_ABI = concat!("fltk-cst-core/", env!("CARGO_PKG_VERSION"))` baked into the rlib (`cross_cdylib.rs:19`). Both cdylibs must link the **same** `fltk-cst-core` rlib (same Cargo version) for cross-cdylib Span passing to work.
- Two class attributes checked at runtime: `_fltk_cst_core_abi` (version string) and `_fltk_cst_core_abi_layout` (struct layout size). Validated by `check_abi_pair<T>` at `cross_cdylib.rs:158-233`.
- Consumer-generated code calls `span_to_pyobject` (from `fltk-cst-core`) to convert native `Span` → Python object pointing at `fltk._native.Span`, not the consumer-local type.
- `get_span_type()` imports `fltk._native` at runtime: `cross_cdylib.rs:349-366` (`py.import("fltk._native").and_then(|m| m.getattr("Span"))`).

**Consequence for out-of-tree consumers**: generated Rust code always imports `fltk._native` at Python runtime to resolve the canonical `Span` type. `fltk._native` must be importable.

### Canonical-wrapper registry

`crates/fltk-cst-core/src/registry.rs`: process-wide `weakref.WeakValueDictionary` keyed by `Arc` address (usize). Ensures at most one live Python handle per `Shared<T>` allocation (is-identity stability). All operations require the GIL.

---

## Schemas / Contracts

### Generated file set from a `.fltkg` grammar

**Python backend** (`genparser.py:generate` command, lines 120-252):
- `{base_name}_cst.py` — CST node classes
- `{base_name}_cst_protocol.py` — Protocol class definitions for type checking
- `{base_name}_parser.py` — no-trivia parser (omitted with `--trivia-only`)
- `{base_name}_trivia_parser.py` — trivia-preserving parser (omitted with `--no-trivia-only`)

**Rust backend** (`genparser.py:gen_rust_cst` and `gen_rust_parser` commands, lines 265-397):
- `cst.rs` — complete `.rs` file with `NodeKind` enum, per-rule node structs, child enums, label enums, PyO3 handle classes, `register_classes` fn. Generated by `RustCstGenerator.generate()` in `gsm2tree_rs.py:344-370`.
- `parser.rs` — complete `.rs` file with `Parser` struct, packrat cache fields, regex `OnceLock` cells, and per-rule `apply__parse_*` functions. Generated by `RustParserGenerator.generate()` in `gsm2parser_rs.py`.
- Optionally `cst.pyi` — stub for pyright when `--protocol-module` is provided.

### Generated `cst.rs` structure

Preamble (`gsm2tree_rs.py:376-395`) unconditionally emits:
```rust
use fltk_cst_core::CstError;
use fltk_cst_core::Span;
use fltk_cst_core::Shared;
use std::fmt;
#[cfg(feature = "python")] use fltk_cst_core::{extract_span, get_span_type, span_to_pyobject};
#[cfg(feature = "python")] use fltk_cst_core::registry;
#[cfg(feature = "python")] use pyo3::prelude::*;
// ... more cfg(feature = "python") use statements
```

Per rule, for a rule whose CamelCase name is `ClassName`:
- `NodeKind` enum (one variant per rule): `gsm2tree_rs.py:446-509`
- Optional `ClassNameLabel` enum (when rule has labels): `gsm2tree_rs.py:535-604`; Python-visible name is `ClassName_Label` via `#[pyclass(name = "ClassName_Label")]`
- `ClassNameChild` enum (child value enum, always): `gsm2tree_rs.py:644-814`
- `ClassName` data struct + plain `impl` (native Rust API): `gsm2tree_rs.py:820-1034`
- `PyClassName` handle pyclass (python-gated `#[cfg(feature = "python")]`): `gsm2tree_rs.py:1037-1105`
- `register_classes` fn at end: `gsm2tree_rs.py:_register_classes_fn`

Python-visible class name for the handle is unchanged from the data struct name: `#[pyclass(frozen, weakref, name = "ClassName")]` (`gsm2tree_rs.py:1042`).

### Generated `parser.rs` structure

`tests/rust_parser_fixture/src/parser.rs:1-60` (committed generated example):
- Imports `fltk_parser_core::regex_automata::meta::Regex` — regex_automata re-exported by `fltk-parser-core` (`crates/fltk-parser-core/src/lib.rs:23`).
- Imports `fltk_cst_core::{Shared, SourceText, Span}`.
- Imports `fltk_parser_core::{apply, ApplyResult, Cache, ErrorTracker, PackratState, TerminalSource}`.
- `use super::cst;` (configurable via `--cst-mod-path`, default `super::cst`).
- `RULE_NAMES: [&str; N]` const array of all rule name strings.
- `REGEX_PATTERNS: [&str; M]` + `REGEX_CELLS: [OnceLock<Regex>; M]`.
- `pub struct Parser` with one `Cache<Shared<cst::RuleName>>` field per rule.

### Consumer cdylib wiring (lib.rs pattern)

From `tests/rust_parser_fixture/src/lib.rs:1-20` and docstring in `genparser.py:gen_rust_cst:307-317`:
```rust
use fltk_cst_core::register_submodule;
#[pymodule]
fn my_grammar(m: &Bound<'_, PyModule>) -> PyResult<()> {
    register_submodule(m, "cst", cst::register_classes)?;
    register_submodule(m, "parser", parser::register_classes)?;
    Ok(())
}
```

The Python module name used in `#[pymodule] fn <name>` must match `[lib] name` in `Cargo.toml` and the `module-name` in maturin config.

### `fltk-parser-core` public re-exports

`crates/fltk-parser-core/src/lib.rs:25-27`:
```rust
pub use regex_automata;  // structural re-export: generated code uses fltk_parser_core::regex_automata::meta::Regex
pub use errors::{escape_control_chars, format_error_message, ErrorTracker, ParseContext, TokenType};
pub use memo::{apply, ApplyResult, Cache, DEFAULT_MAX_DEPTH, MemoEntry, MemoResult, PackratState, RecursionInfo};
pub use terminalsrc::{LineColPos, TerminalSource};
```

`regex_automata` is re-exported so consumers need no direct `regex-automata` dependency.

### Python import path of the native extension

- Python import: `fltk._native` (the `fltk` package's `_native` submodule).
- Stub package: `fltk/_native/` directory containing only `.pyi` files (no `__init__.py`). `fltk/_native/__init__.pyi:1-7` documents this.
- Python fallback: `fltk/fegen/pyrt/span.py` tries `from fltk._native import SourceText, Span, UnknownSpan`, falls back to pure-Python on any `Exception` with `warnings.warn`. (Cited in `docs/adr/2026/06/06-todo-burndown-triage/expl-bazel-rules-rust.md:51-54`.)

---

## Invariants / Constraints

### Runtime dependency: `fltk._native` must be importable by consumer cdylibs

Generated `cst.rs` imports `fltk._native` at Python startup via `get_span_type()` (`cross_cdylib.rs:349-366`). This is not optional — every span read/write through a consumer cdylib triggers the cross-cdylib ABI check on first use. Without `fltk._native`, consumer code raises `RuntimeError: "cross-cdylib Span type lookup failed (fltk._native.Span)"`.

### Same `fltk-cst-core` rlib version required across all cdylibs

`cross_cdylib.rs:19`: `FLTK_CST_CORE_ABI = concat!("fltk-cst-core/", env!("CARGO_PKG_VERSION"))`. If `fltk._native` and a consumer cdylib link different versions of `fltk-cst-core`, the ABI check raises `TypeError`. This constrains Bazel's ability to independently build `fltk._native` and consumer cdylibs unless both reference exactly the same `fltk-cst-core` rlib artifact.

### pyo3 `abi3-py310` — ABI stable, CPython 3.10+

`Cargo.toml:24`: `pyo3 = { version = "0.29", features = ["abi3-py310"] }`. The compiled `.so` is ABI3 and works on CPython 3.10 through 3.x without recompilation.

### `extension-module` Cargo feature must be enabled for PyO3 extension builds

`Cargo.toml:14`: `extension-module = ["python", "pyo3/extension-module"]`. For a cdylib that will be imported from Python, this feature must be enabled; otherwise the build links libpython statically (linker errors or ABI mismatch). Consumer fixture crates use the same pattern: `tests/rust_parser_fixture/Cargo.toml:14-16`.

### Pure-Rust build path (no Python)

All generated code emits `#[cfg(feature = "python")]` guards around pyo3 code, and `#[cfg(not(feature = "python"))]` for plain-Rust enum variants. `fltk-parser-core` never links pyo3 at all. This means generated parsers can be compiled as pure-Rust rlibs without Python, e.g., for embedding in a non-Python application.

### Cross-rule identifier collision check

`gsm2tree_rs.py:123-164`: `RustCstGenerator.__init__` runs a collision check across all derived Rust identifiers (`ClassName`, `PyClassName`, `ClassNameChild`, `ClassNameLabel`) before any emission. Raises `ValueError` with a descriptive message if two rules map to the same Rust identifier.

### Regex subset restriction

`gsm2parser_rs.py:7-14`: grammar regexes must use the subset compatible with `regex-automata` (no lookahead/lookbehind/backreferences). Every generated `parser.rs` includes `#[test] fn all_regex_patterns_compile` that exercises this at `cargo test` time.

---

## Existing Bazel Surface

### What exists

- `MODULE.bazel`: Declares `fltk` module, depends only on `rules_python 1.5.0`. Configures CPython 3.10 toolchain and a pip hub. No `rules_rust`. `MODULE.bazel:5` contains `# TODO(bazel-rules-rust): Add rules_rust for building the PyO3 extension via Bazel.`
- `WORKSPACE.bazel`: Empty (single blank line).
- `BUILD.bazel`: Defines `py_library(name = "fltk", srcs = glob(["**/*.py"]), ...)` and `py_binary(name = "genparser", ...)`. No references to `.so`, `_native`, or any Rust artifact.
- `rules.bzl`: `generate_parser` Starlark rule (`rules.bzl:40-71`) that runs the Python `genparser generate` CLI and declares `{base_name}_cst.py`, `{base_name}_parser.py`, `{base_name}_trivia_parser.py` as outputs. Handles `--trivia-only` / `--no-trivia-only` flags.

### What is absent

- No Bazel rule for `gen-rust-cst` or `gen-rust-parser` (Rust codegen commands).
- No `rules_rust` dependency, no `rust_library` or `rust_shared_library` targets.
- No Bazel macro to compile a generated `cst.rs` + `parser.rs` into a cdylib.
- The `generate_parser` Bazel rule (`rules.bzl`) generates only Python artifacts, not Rust.
- The Bazel `fltk` py_library target globs `**/*.py` only; `fltk/_native.abi3.so` is not a declared output or data dependency — Bazel consumers get the pure-Python fallback silently.

---

## Generator Entry Points

### Python CLI

`fltk/fegen/genparser.py` is the unified CLI, invoked as `python -m fltk.fegen.genparser` or `genparser` (via `py_binary` in `BUILD.bazel`). Three subcommands:

1. `generate` (line 120): Grammar → Python CST + parsers.
2. `gen-rust-cst` (line 265): Grammar → `cst.rs` (+ optional `.pyi` stub).
3. `gen-rust-parser` (line 368): Grammar → `parser.rs`.

### Generator class hierarchy

- `fltk/fegen/gsm2tree_rs.py`: `RustCstGenerator` — generates `cst.rs`. Takes raw (pre-trivia) `gsm.Grammar`; applies trivia internally.
- `fltk/fegen/gsm2parser_rs.py`: `RustParserGenerator` — generates `parser.rs`. Accepts `cst_mod_path` (Rust module path to cst, default `"super::cst"`).
- `fltk/fegen/gsm2tree.py`: `CstGenerator` — Python CST generator; also used internally by `RustCstGenerator` for naming decisions (`class_name_for_rule_node`, `rule_models`, `protocol_annotation_for_model_types`).
- `fltk/fegen/gsm2parser.py`: Python parser generator.
- `fltk/fegen/gsm.py`: Grammar Semantic Model data structures.
- `fltk/fegen/fltk2gsm.py`: Converts parsed CST → `gsm.Grammar`.

### Grammar pipeline

1. Read `.fltkg` file → `fltk_parser.Parser.apply__parse_grammar` → CST.
2. `fltk2gsm.Cst2Gsm.visit_grammar` → raw `gsm.Grammar`.
3. `gsm.add_trivia_rule_to_grammar` + `gsm.classify_trivia_rules` → grammar with `_trivia` rule.
4. Pass to `RustCstGenerator` or `RustParserGenerator`.

---

## Open Factual Questions

1. **Published crates**: `fltk-cst-core` and `fltk-parser-core` have `license = "MIT"` but no `publish = false`. `fltk-native` has `publish = false` (`Cargo.toml:9`). It is not verified whether `fltk-cst-core` or `fltk-parser-core` are published to crates.io; if not, a Bazel consumer cannot fetch them via `crates_repository` and must use `git_override` or local path.

2. **`rust_cst_fegen` workspace members**: `tests/rust_cst_fegen/Cargo.toml:1` declares `[workspace]`. It does not appear in the root workspace `members` list, so `cargo deny` must be run against it separately (and `Makefile:178` does this). A Bazel integration must account for these separate workspace topologies.

3. **Exact `.so` file name**: maturin produces `fltk/_native.abi3.so` (or `.pyd` on Windows) based on `module-name = "fltk._native"`. The exact path within the installed wheel is not verified in source code; it is implicit in maturin's naming convention.
