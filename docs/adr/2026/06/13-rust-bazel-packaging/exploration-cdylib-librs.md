# Exploration: cdylib `lib.rs` — Hand-Authored vs. Generated

Survey date: 2026-06-13. All citations are file:line unless prefixed with `tps/clockwork/`.

---

## 1. The hand-authored Clockwork cdylib `lib.rs`

File: `/home/rnortman/tps/clockwork/clockwork/dsl/clockwork_native_lib.rs` (25 lines, sole Rust file in the repo).

Full contents:

```rust
// Consumer-authored PyO3 wiring for the Clockwork DSL native module.
//
// This file is the crate root for the clockwork_native cdylib.  The `mod`
// declarations below resolve because fltk_pyo3_cdylib assembles this file,
// cst.rs, and parser.rs into a single gendir before compilation.
//
// The Clockwork DSL grammar is large and contains deeply recursive type
// references (DflArg → DflExpr → ... → DflCallSuffix → DflArgList → DflArg).
// Rust's trait solver needs an elevated recursion limit to evaluate Send + Sync
// bounds across the full recursive chain for PyO3's pyclass macro.
#![recursion_limit = "512"]

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

**What it declares / does:**

- `#![recursion_limit = "512"]` — crate-level inner attribute. Must appear before all items. Raises rustc's trait-solver recursion limit from the default 128 to 512 to handle `Send + Sync` bound evaluation over Clockwork's deeply recursive grammar (`DflArg → DflExpr → … → DflArgList → DflArg`). A grammar with shallower recursion does not need this.
- `use fltk_cst_core::register_submodule` — imports the FLTK helper that registers a generated module as a named Python submodule.
- `use pyo3::prelude::*` — brings `#[pymodule]`, `Bound`, `PyModule`, `PyResult` etc. into scope.
- `mod cst;` / `mod parser;` — bare module declarations that resolve because `fltk_pyo3_cdylib`'s `_assemble_crate` genrule copies `cst.rs` and `parser.rs` into the same generated directory as `lib.rs` before compilation (`rust.bzl:197–215`).
- `#[pymodule] fn clockwork_native(...)` — the PyO3 entry point for the `clockwork_native` extension module. The function name (`clockwork_native`) equals the `crate_name` set by the macro (`rust.bzl:224`) and the importable Python module name — this three-way match is load-bearing (`design.md` invariant #5).
- Registers `cst::register_classes` as the `cst` submodule and `parser::register_classes` as the `parser` submodule.

The `#[pymodule]` decorator and the `#[recursion_limit]` are the only grammar-specific decisions in this file; the structural boilerplate is identical to the in-tree fixture patterns (see §3 below).

---

## 2. What FLTK's Rust codegen currently generates for a grammar

### Generated outputs

`genparser.py` exposes two Rust subcommands (`genparser.py:265–397`):

- `gen-rust-cst <grammar_file> <output_file>` — generates `cst.rs`.
- `gen-rust-parser <grammar_file> <output_file> --cst-mod-path <path>` — generates `parser.rs`.

Neither subcommand has an `--output-dir` flag (unlike the Python `generate` subcommand at `genparser.py:120`). Each takes a single positional output file.

### `cst.rs` — what `RustCstGenerator.generate()` emits (`gsm2tree_rs.py:365–391`)

The generated file contains (`gsm2tree_rs.py:397–410`):
- `use fltk_cst_core::*` preamble (with `#[cfg(feature = "python")]` guards on pyo3 imports)
- `NodeKind` enum (one variant per rule)
- Per rule: `ClassNameLabel` enum (if labels present), `ClassNameChild` enum, `ClassName` data struct with native `impl`, `PyClassName` handle pyclass (gated on `#[cfg(feature = "python")]`)
- At the end: a `pub fn register_classes(module: &Bound<'_, pyo3::types::PyModule>) -> PyResult<()>` function (`gsm2tree_rs.py:2220–2250`) that registers `NodeKind` plus every rule's label enum and handle class.

**`register_classes` is generated, not hand-written.**

### `parser.rs` — what `RustParserGenerator` emits (`gsm2parser_rs.py:948–958`)

The parser module's Python bindings are inside a `#[cfg(feature = "python")] mod python_bindings { ... }` block. At the end of the closing skeleton:

```rust
    pub fn register_classes(module: &Bound<'_, pyo3::types::PyModule>) -> PyResult<()> {
        module.add_class::<PyApplyResult>()?;
        module.add_class::<PyParser>()?;
        Ok(())
    }
}
#[cfg(feature = "python")]
pub use python_bindings::register_classes;
```

`register_classes` for the parser is also **generated, not hand-written.**

### What codegen does NOT generate

Neither `gen-rust-cst` nor `gen-rust-parser` emits:
- A crate root / `lib.rs` file.
- A `#[pymodule]` entry point function.
- Any `mod cst;` / `mod parser;` declarations.
- A `#![recursion_limit]` attribute.

The `gen-rust-cst` docstring at `genparser.py:309–317` explicitly shows the consumer-authored `lib.rs` pattern as something the user must write:

```
Wire the generated cst.rs and parser.rs into your lib.rs like this:

    use fltk_cst_core::register_submodule;
    #[pymodule]
    fn my_grammar(m: &Bound<'_, PyModule>) -> PyResult<()> {
        register_submodule(m, "cst", cst::register_classes)?;
        register_submodule(m, "parser", parser::register_classes)?;
        Ok(())
    }
```

This docstring text is documentation of a hand-authoring requirement, not a code-generation output.

---

## 3. FLTK's own in-tree cdylib crate root (`src/lib.rs`) — hand-written or generated?

File: `/home/rnortman/src/fltk/src/lib.rs` (38 lines).

**Hand-written.** It is the crate root for the `fltk-native` crate (the `fltk._native` extension module built by maturin). It:
- Imports `register_submodule`, `Span`, `SourceText` from `fltk_cst_core`.
- Declares `mod cst_fegen; mod cst_generated; mod span;`.
- Defines a `pub(crate) static UNKNOWN_SPAN: PyOnceLock<Py<PyAny>>`.
- Defines `#[pymodule] fn _native(m: &Bound<'_, PyModule>) -> PyResult<()>` — the entry point for `fltk._native`.

There is **no `#![recursion_limit]` attribute** in `src/lib.rs`. FLTK's in-tree grammars (fegen grammar, PoC grammar) are shallower and do not hit the default limit of 128.

### In-tree fixture `lib.rs` files — all hand-written

| File | crate-type | `#![recursion_limit]`? | `#[pymodule]` fn name |
|---|---|---|---|
| `src/lib.rs` | cdylib | No | `_native` |
| `tests/rust_parser_fixture/src/lib.rs` | rlib + cdylib | No | `rust_parser_fixture` |
| `tests/rust_cst_fixture/src/lib.rs` | cdylib | No | `phase4_roundtrip_cst` |
| `tests/rust_cst_fegen/src/lib.rs` | cdylib + rlib | No | `fegen_rust_cst` |

All four are hand-written. None carries `#![recursion_limit]`. All register generated `register_classes` functions via `register_submodule`.

### The Bazel macro's role (`rust.bzl:123–270`)

`fltk_pyo3_cdylib` (`rust.bzl:123`) takes a mandatory `lib_rs` parameter — the consumer-authored file. The macro:

1. Runs a `_assemble_crate` genrule (`rust.bzl:201–216`) that copies `lib_rs`, `cst.rs`, and `parser.rs` verbatim into a single `<name>_crate_root/` gendir. The copy is `cp $(location {lib_rs}) $$OUTDIR/lib.rs` — **no content injection**, no prepending.
2. Compiles the assembled sources as a `rust_shared_library` (`rust.bzl:219–245`) with `crate_name = name`, `crate_root = ":" + crate_lib_rs`, `crate_features = ["extension-module", "python"] + crate_features`.
3. Renames `lib<name>.so` → `<name>.abi3.so` (`rust.bzl:250–255`).
4. Wraps in a `py_library` that carries `@fltk//:native_py` as a dep (`rust.bzl:264–270`).

**The macro copies `lib.rs` verbatim — it does not generate or inject any content into it.** The `#![recursion_limit]` must be in the consumer's source file. The macro docstring (`rust.bzl:171–182`) documents the required template but does not generate it.

---

## 4. Is the Clockwork hand-authored `lib.rs` filling a real gap or duplicating generated code?

**It fills a genuine gap.** FLTK's Rust codegen (`gen-rust-cst`, `gen-rust-parser`) produces only `cst.rs` and `parser.rs`. No FLTK mechanism — generator class, CLI subcommand, Bazel rule, or macro — currently emits a crate root / `lib.rs` / `#[pymodule]` entry point.

### What a consumer must hand-write today to get a working pyo3 cdylib

A consumer must author a `lib.rs` containing:

1. `use fltk_cst_core::register_submodule;` — pulls in the submodule wiring helper.
2. `use pyo3::prelude::*;` (or the needed subset) — brings `#[pymodule]`, `Bound`, `PyModule`, `PyResult` into scope.
3. `mod cst;` and `mod parser;` — bare module declarations (they resolve because `fltk_pyo3_cdylib` assembles the files in one directory).
4. `#[pymodule] fn <module_name>(m: &Bound<'_, PyModule>) -> PyResult<()> { ... }` — the entry point; the function name must equal the Bazel `name` attr passed to `fltk_pyo3_cdylib` and the importable Python module name.
5. Inside the entry point: `register_submodule(m, "cst", cst::register_classes)?;` and `register_submodule(m, "parser", parser::register_classes)?;`.
6. **If the grammar is deeply recursive**: `#![recursion_limit = "512"]` (or higher) as the first line of the file. Required for grammars where PyO3's `#[pyclass]` macro causes rustc's trait solver to exceed the default limit of 128 during `Send + Sync` evaluation. No FLTK mechanism detects or warns about this condition before compilation.

Items 1–5 are structural boilerplate that does not vary across consumers (modulo the module name in item 4). Item 6 is grammar-dependent and invisible until a real `cargo`/`rustc` run fails with `E0275`.

### Design note (from `design-buildfix.md` §5)

`design-buildfix.md:329–368` (Problem 4, Tier 3) documents the `#![recursion_limit]` issue and the two resolution options:

1. Have `fltk_pyo3_cdylib` inject `#![recursion_limit = "512"]` at the front of the assembled `lib.rs` (prepend before `cp`). This would move items 1–5 above plus item 6 entirely into the macro and make the consumer file optional or trivially templatable.
2. Document it as a required line in the consumer `lib.rs` template (current state).

The current state is option (2): the `#![recursion_limit]` lives in the consumer-authored file, the macro copies it verbatim, and the macro docstring (`rust.bzl:171–182`) shows the template without the recursion-limit line. The buildfix design marks option (1) as preferred and deferred (`TODO(rust-recursion-limit-macro)`).

**Items 1–5 are also not generated or injected** — they are present in the consumer file by hand. The macro could in principle synthesize the entire `lib.rs` from the `name` parameter alone (since items 1–5 are fully determined by the module name), but no such synthesis exists today. The `lib_rs` parameter is mandatory; there is no default or auto-generation path.

---

## Open Factual Questions

1. **Whether `fltk_pyo3_cdylib` should synthesize `lib.rs` entirely.** Items 1–5 are fully determined by `name` and the two generated modules. The only consumer-specific content is the `#[pymodule]` fn name (= `name`) and any extra `mod` declarations for consumer-owned native Rust. A macro that synthesizes the standard `lib.rs` and accepts an optional `extra_lib_rs` for additions would eliminate hand-authoring for the common case. This is not in any current design; it is an unresolved design question.

2. **`design-buildfix.md:344–367`** states the `_assemble_crate` genrule `cp $(location {lib_rs}) $$OUTDIR/lib.rs` is a verbatim copy. The recommendation to prepend `#![recursion_limit = "512"]` before the `cat` would require changing the `cmd` in the genrule. This has not been implemented; the `TODO(rust-recursion-limit-macro)` tracking item is prescribed but not yet filed in `TODO.md`.
