# Exploration: lib.rs codegen for Rust backend

## 1. Rust parser generation backend

### Generator entry points

`fltk/fegen/gsm2tree_rs.py` — `RustCstGenerator` class.
- `__init__(grammar: gsm.Grammar)` — takes a raw (pre-trivia) grammar; applies trivia processing internally via `gsm.add_trivia_rule_to_grammar` + `gsm.classify_trivia_rules` (gsm2tree_rs.py:163-170).
- `generate() -> str` — emits a complete, compilable `cst.rs` string (gsm2tree_rs.py:429-455).
- `generate_pyi(protocol_module: str) -> str` — emits a `.pyi` stub for pyright conformance (gsm2tree_rs.py:296-396).

`fltk/fegen/gsm2parser_rs.py` — `RustParserGenerator` class.
- `__init__(grammar, cst_mod_path="super::cst", source_name=None)` — constructs on a raw grammar; creates its own internal `RustCstGenerator` (gsm2parser_rs.py:74-134).
- `generate() -> str` — emits a complete, compilable `parser.rs` string (gsm2parser_rs.py:197-239).

### CLI entry points

`fltk/fegen/genparser.py` exposes two CLI sub-commands via `typer`:

- `gen-rust-cst <grammar_file> <output_file> [--protocol-module ...] [--pyi-output ...]` (genparser.py:265-362) — invokes `RustCstGenerator` and writes `cst.rs`; optionally writes `.pyi`.
- `gen-rust-parser <grammar_file> <output_file> [--cst-mod-path ...]` (genparser.py:368-397) — invokes `RustParserGenerator` and writes `parser.rs`. Default `--cst-mod-path` is `"super::cst"`.

### What each generator emits

`RustCstGenerator.generate()` emits into a single `cst.rs`:
- A preamble of `use` declarations (gsm2tree_rs.py:461-517), notably `use fltk_cst_core::{CstError, Span, Shared}` and a carefully enumerated set from `pyo3::prelude` (no glob due to class-name collision analysis).
- One `NodeKind` enum (gsm2tree_rs.py:570-633).
- Per rule: optional label enum, child enum, data struct + handle pyclass (gsm2tree_rs.py:429-455).
- A `register_classes` function (gsm2tree_rs.py:2321-2351):
  ```rust
  #[cfg(feature = "python")]
  pub fn register_classes(module: &Bound<'_, pyo3::types::PyModule>) -> pyo3::PyResult<()> {
      module.add_class::<NodeKind>()?;
      // per rule: label enum and/or handle pyclass
      Ok(())
  }
  ```

`RustParserGenerator.generate()` emits into a single `parser.rs`:
- A `#![allow(non_snake_case)]` header, imports, and the parser struct + constructors.
- Per-rule memoized `apply__*` and `parse_*` functions.
- A `mod python_bindings` block with `PyParser` / `PyApplyResult` pyclasses + a `register_classes` re-export (gsm2parser_rs.py:838-970):
  ```rust
  #[cfg(feature = "python")]
  pub use python_bindings::register_classes;
  ```

Neither generator emits `lib.rs`. Neither `RustCstGenerator` nor `RustParserGenerator` takes a module name as a parameter.

---

## 2. fltk._native hand-written lib.rs

File: `src/lib.rs` (38 lines).

```rust
use fltk_cst_core::register_submodule;
use pyo3::prelude::*;
use pyo3::sync::PyOnceLock;

mod cst_fegen;
mod cst_generated;
mod span;

use span::{SourceText, Span};

pub(crate) static UNKNOWN_SPAN: PyOnceLock<Py<PyAny>> = PyOnceLock::new();

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Span>()?;
    m.add_class::<SourceText>()?;
    let unknown_span_obj = Py::new(m.py(), Span::unknown())?.into_any();
    m.add("UnknownSpan", unknown_span_obj.clone_ref(m.py()))?;
    UNKNOWN_SPAN
        .set(m.py(), unknown_span_obj)
        .expect("UNKNOWN_SPAN already set; module initialized twice");
    register_submodule(m, "poc_cst", cst_generated::register_classes)?;
    register_submodule(m, "fegen_cst", cst_fegen::register_classes)?;
    Ok(())
}
```

What is fixed vs variable:
- **Fixed** imports: `register_submodule`, `pyo3::prelude::*`, `pyo3::sync::PyOnceLock`.
- **Fixed** structure: `#[pymodule] fn <name>(m: &Bound<'_, PyModule>) -> PyResult<()>`.
- **Fixed** Span/SourceText/UnknownSpan registration: this is unique to `fltk._native` because it is the *canonical* provider of those types. Consumer cdylibs do NOT register Span/SourceText (they import from `fltk._native` at runtime).
- **Fixed** `UNKNOWN_SPAN` static: also specific to `fltk._native`; not present in consumer lib.rs.
- **Variable** `mod` declarations: `cst_fegen`, `cst_generated`, `span` — specific to this crate's structure.
- **Variable** `#[pymodule] fn` name: `_native` — the importable module name.
- **Variable** `register_submodule` calls: `"poc_cst"` and `"fegen_cst"` with their specific `register_classes` pointers — the submodule names and which modules to register.

The `fltk._native` lib.rs is structurally non-standard: it registers Span/SourceText/UnknownSpan at module level, which is a one-time special responsibility. Consumer cdylibs do not do this.

---

## 3. Clockwork integration hand-written lib.rs

File: `clockwork/dsl/clockwork_native_lib.rs` (25 lines).

```rust
use fltk_cst_core::register_submodule;
use pyo3::prelude::*;

mod cst;
mod parser;

#[pymodule]
fn clockwork_native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    register_submodule(m, "cst", cst::register_classes)?;
    register_submodule(m, "parser", parser::register_classes)?;
    Ok(())
}
```

The file has a file-level comment (lines 1-8) noting that `mod cst; mod parser;` resolve because `fltk_pyo3_cdylib` assembles the file with `cst.rs` and `parser.rs` into a single gendir, and that `#![recursion_limit]` is injected by the macro (so it must not be in the consumer file).

Differences from `fltk._native`:
- No Span/SourceText/UnknownSpan registration (those come from `fltk._native`).
- No `UNKNOWN_SPAN` static.
- No `pyo3::sync::PyOnceLock` import.
- Module name is `clockwork_native` (matches the Bazel target `name` and the compiled `.so` stem).
- Two submodules: `"cst"` and `"parser"`, both from the generated files.

The Clockwork BUILD.bazel at `clockwork/dsl/BUILD.bazel:75-80`:
```
fltk_pyo3_cdylib(
    name = "clockwork_native",
    rs_srcs = ":clockwork_rs_srcs",
    lib_rs = "clockwork_native_lib.rs",
    ...
)
```

The `name` attribute becomes both the `#[pymodule]` fn name in `lib_rs` and the compiled `.so` stem (rust.bzl:173: "Must match the `#[pymodule]` fn name in lib_rs and the importable module name").

---

## 4. What inputs a lib.rs codegen needs

For a **standard consumer** (the common case, analogous to clockwork):

| Input | Source in pipeline | Notes |
|---|---|---|
| Module name (`clockwork_native`) | Bazel `name` attr / CLI arg | Becomes `#[pymodule] fn <name>` and the `.so` stem |
| CST submodule name (`"cst"`) | Fixed: always `"cst"` for standard layout | Could be parameterized |
| Parser submodule name (`"parser"`) | Fixed: always `"parser"` for standard layout | Could be parameterized |
| Whether to include parser | Optional: some grammars CST-only | Grammar may not need a parser module |

The standard template is invariant for all consumers using `fltk_pyo3_cdylib`. The only variable across consumer crates is the module name.

For **`fltk._native`** specifically, additional inputs are needed:
- Extra imports (`pyo3::sync::PyOnceLock`, `span::{SourceText, Span}`).
- `UNKNOWN_SPAN` static registration logic.
- Multiple grammar submodules (`"poc_cst"`, `"fegen_cst"`) rather than one `"cst"` + one `"parser"`.

`fltk._native` is structurally different from a consumer cdylib; its lib.rs is more complex and may warrant a separate specialized codegen path or explicit special-casing.

The `grammar_name` / `source_name` already flows into `RustParserGenerator` as `source_name` (used only in the generated file header comment). There is no existing `module_name` parameter in either generator.

---

## 5. How generated Rust files are currently emitted

### CLI path (maturin / manual use)

`genparser.py:gen_rust_cst` (line 265): reads grammar, calls `RustCstGenerator(grammar).generate()`, writes with `output_file.write_text(src)` (line 351). `genparser.py:gen_rust_parser` (line 368): same for parser.

Neither emits `lib.rs`.

### Bazel path

`rust.bzl:_generate_rust_parser_impl` (line 25) runs two `ctx.actions.run` calls — one for `gen-rust-cst`, one for `gen-rust-parser` — producing `<name>/cst.rs` and `<name>/parser.rs` as declared file outputs (lines 39-72). `lib.rs` is not emitted by this rule.

`fltk_pyo3_cdylib` macro (rust.bzl:123) consumes those outputs via a `genrule` (lines 220-239) that:
1. Prepends `#![recursion_limit = "N"]` to a new `lib.rs` assembled in a gendir.
2. Copies the consumer's `lib_rs` file into the gendir after the recursion limit line.
3. Copies `cst.rs` and `parser.rs` by basename into the same gendir.
4. Validates that both `cst.rs` and `parser.rs` are present.

The `lib_rs` attribute in `fltk_pyo3_cdylib` currently takes a consumer-authored file. If lib.rs were generated, the `lib_rs` attribute would instead point to the output of a new `gen-rust-lib-rs` Bazel rule (or the `generate_rust_parser` rule could be extended to emit a third output).

**Natural seam for adding lib.rs generation:**

- In the CLI: add a `gen-rust-lib-rs` sub-command to `genparser.py`, or add a `--module-name` flag to `gen-rust-parser` that also writes `lib.rs` alongside `parser.rs`.
- In Bazel: extend `_generate_rust_parser_impl` (rust.bzl:25) to declare and write a third output `<name>/lib.rs`, or add a new `generate_rust_lib_rs` rule. The `fltk_pyo3_cdylib` macro would then pass this generated file as `lib_rs` instead of requiring a consumer-authored one. The macro already owns the assembly genrule; it could inline the lib.rs content via `printf` rather than copying a file.

### Makefile / maturin path

`Makefile:gencode` (line 235) calls `gen-rust-cst` and `gen-rust-parser` for each fixture/grammar. No lib.rs generation step. `build-native` (line 186) calls `maturin develop` which compiles from `src/lib.rs` (hand-written, checked in). The Makefile would need a `gen-rust-lib-rs` invocation for `src/lib.rs` if that file is to be codegenned.

---

## 6. Existing tests and fixtures for Rust backend codegen

### Unit tests (pure string output, no compilation)

- `fltk/fegen/test_gsm2parser_rs.py` — ~50 test functions for `RustParserGenerator.generate()`. All tests call `gen.generate()` and assert substring presence in the returned string. No lib.rs coverage.
- `tests/test_gsm2tree_rs.py` — unit tests for `RustCstGenerator.generate()`. Tests assert on `register_classes`, preamble, node kind, label enums. No lib.rs coverage.

### Integration tests (compiled extensions via maturin)

- `tests/rust_cst_fixture/` — standalone crate (`phase4_roundtrip_cst`). Has hand-written `src/lib.rs` (28 lines). Generated: `src/cst.rs`. Tests: `tests/test_fegen_rust_cst.py`, `tests/test_rust_cst_poc.py`, `tests/test_rust_span.py`.
- `tests/rust_cst_fegen/` — standalone crate (`fegen_rust_cst`). Has hand-written `src/lib.rs` (24 lines). Generated: `src/cst.rs`, `src/parser.rs`. Tests: `tests/test_phase4_fegen_rust_backend.py`, `tests/test_rust_parser_parity_fegen.py`.
- `tests/rust_parser_fixture/` — standalone crate (`rust_parser_fixture`). Has hand-written `src/lib.rs` (20 lines). Generated: `src/cst.rs`, `src/parser.rs`, `src/collision_cst.rs`, `src/collision_parser.rs`. Tests: `tests/test_rust_parser_bindings.py`, `tests/test_rust_parser_fixture_bindings.py`, `tests/test_rust_parser_parity_fixture.py`.

All three fixture crates have hand-written `lib.rs` files. None are codegenned.

### Bazel smoke test

`BUILD.bazel:111-115` — `generate_rust_parser(name="bootstrap_rust_srcs", src="fltk/fegen/bootstrap.fltkg")`. Tests only that the rule runs without error; no compiled extension or lib.rs. A `TODO(fltk-pyo3-cdylib-smoke)` at BUILD.bazel:117-122 notes the absence of an in-FLTK `fltk_pyo3_cdylib` invocation.

---

## 7. Cross-backend / public-API considerations from CLAUDE.md

The following facts from CLAUDE.md are directly relevant:

1. **Generated public symbols are downstream API.** Class names, accessor method names, `NodeKind` member names, and `Label` enum names emitted by `RustCstGenerator` are consumed by out-of-tree downstream code. `lib.rs` codegen does not affect these symbols — `lib.rs` contains only module wiring (`register_submodule`, `#[pymodule]`) with no rule-derived names.

2. **Near-drop-in replacement.** The explicit goal is that consumers switch from Python backend to Rust backend by updating import statements only, not type annotations or call sites. A codegenned `lib.rs` is additive — it reduces the number of files consumers must author, but does not change the Python-visible API surface.

3. **No generated public symbols renamed.** A `lib.rs` generator introduces no new symbols into the Python namespace and does not rename any existing ones. The `#[pymodule] fn <name>` function name is already determined by the `name` attribute (Bazel) or a new `--module-name` CLI arg; it is not derived from grammar rule names.

4. **`fltk._native` special case.** `fltk._native` registers `Span`, `SourceText`, and `UnknownSpan` — types that do not exist in the Python backend at all and are fltk-internal. This is not downstream API in the consumer sense; consumers depend on `fltk._native` for these types at runtime but do not own the lib.rs that registers them. Codegenning `fltk._native`'s `lib.rs` is a separate problem from codegenning consumer lib.rs files.

5. **Backward compatibility.** If an existing consumer already has a hand-authored `lib.rs`, switching to codegen is opt-in (change `lib_rs = "hand_authored.rs"` to `lib_rs = ":generated_lib_rs"` in Bazel). No existing downstream consumer is broken by adding the generation capability.

---

## Open factual questions

1. **`fltk._native` lib.rs scope**: The user request says "both fltk._native and the clockwork lib.rs get codegenned." The `fltk._native` lib.rs is significantly more complex (Span/SourceText/UnknownSpan registration, UNKNOWN_SPAN static, multiple non-standard submodules). Is the intent to generate it via a separate specialized template, or to make the generator flexible enough to cover it with flags?

2. **Grammar name vs module name**: `gsm.Grammar` has no `name` field (gsm.py:22-24). The `#[pymodule] fn` name must come from an external source (CLI arg or Bazel `name` attr). Does any existing pipeline component already carry a "grammar/module name" that can be reused, or must it always be a new explicit input?

3. **CST-only grammars**: `rust_cst_fixture` registers only `cst` (no `parser`). Should the lib.rs generator support CST-only mode, or is parser always present in the target use cases?

4. **Multiple grammars in one cdylib**: `rust_parser_fixture` hosts two grammars (`cst`/`parser` and `collision_cst`/`collision_parser`). The standard one-grammar lib.rs template does not cover this. Is multi-grammar support in scope?

5. **`#![recursion_limit]` injection**: The Bazel macro injects this line at assembly time (rust.bzl:226-227). If lib.rs is generated directly (not assembled by the macro), this line must be included in the generated file or the macro must still inject it. The clockwork lib.rs comment at clockwork_native_lib.rs:7-8 explicitly warns against including it in the consumer file because the macro owns it.
