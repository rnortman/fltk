# Building a Standalone Formatter Binary for Your Grammar

This guide shows how to turn any FLTK grammar into a standalone, pure-Rust formatter CLI using
the `fltk_formatter_main!` macro from the `fltk-fmt-cli` crate. The macro generates a complete
`fn main()` — argument parsing, file/stdin I/O, in-place/check modes, exit codes, error
reporting — so a formatter binary is a single macro invocation naming your grammar's generated
parser and unparser types.

`crates/fltkfmt/` (the `.fltkg` formatter, built from `fegen.fltkg`) is the canonical worked
example; this guide mirrors it.

---

## Overview

`fltk-fmt-cli` provides the grammar-independent CLI scaffolding. The grammar-specific pieces —
the concrete `Parser` / `Unparser` types and the start-rule parse/unparse methods — are bound
at your call site by the macro. The expansion runs the pure-Rust pipeline:

```
Parser::new(src, filename, true) → parser.apply__parse_<rule>(0) → fully-consumed check
  → Unparser::new().unparse_<rule>(&cst) → resolve_spacing_specs → Renderer::render
```

No Python, PyO3, or GIL is involved at any stage.

---

## Step 1: Prerequisites — a pure-Rust parser + unparser crate for your grammar

You need a Rust crate that exposes, for your grammar, a `parser::Parser` and an
`unparser::Unparser`, and that is consumable as a plain `rlib` with pyo3 dropped — i.e. the
same crate the Rust CST extension builds, but with a `crate-type` that includes `rlib` and a
feature split that lets `default-features = false` strip pyo3 and produce a pure-Rust library.
The canonical template is `crates/fegen-rust/` (package `fegen-rust-cst`, lib `fegen_rust_cst`);
this section reproduces its essentials.

### 1a. Generate the source

```bash
# CST node classes (one struct per rule + label enums)
uv run python -m fltk.fegen.genparser gen-rust-cst      my_grammar.fltkg src/cst.rs
# Parser (start-rule methods named apply__parse_<rule>)
uv run python -m fltk.fegen.genparser gen-rust-parser   my_grammar.fltkg src/parser.rs
# Unparser (start-rule methods named unparse_<rule>); the format spec is baked in here
uv run python -m fltk.fegen.genparser gen-rust-unparser my_grammar.fltkg src/unparser.rs \
    --format-config my_grammar.fltkfmt
```

The generated `parser.rs` does `use fltk_parser_core::...` and `unparser.rs` does
`use fltk_unparser_core::...`, so the crate must depend on **both** of those plus
`fltk-cst-core` — not `fltk-cst-core` alone.

### 1b. `Cargo.toml`

The crate must build as an `rlib` (a `cdylib`-only crate cannot be used as a normal Cargo
library dependency) and must keep pyo3 behind an optional feature so the formatter can consume
it with `default-features = false`. Mirror `crates/fegen-rust/Cargo.toml`:

```toml
[package]
name = "my-grammar-cst"
version = "0.1.0"
edition = "2021"

[lib]
name = "my_grammar_cst"
# rlib so the formatter can use it as a library dependency; cdylib if you also build it as a
# Python extension module.
crate-type = ["cdylib", "rlib"]

[features]
default = ["extension-module"]
extension-module = ["python", "pyo3/extension-module"]
python = ["dep:pyo3", "fltk-cst-core/python"]

[dependencies]
pyo3 = { version = "0.29", features = ["abi3-py310"], optional = true }
# The *-core crates are not published to crates.io; pin by path (local checkout) or git rev.
fltk-cst-core      = { path = "../fltk/crates/fltk-cst-core", default-features = false }
fltk-parser-core   = { path = "../fltk/crates/fltk-parser-core" }
fltk-unparser-core = { path = "../fltk/crates/fltk-unparser-core" }
```

### 1c. `src/lib.rs`

`gen-rust-lib` emits a pyo3 cdylib skeleton, but its output is **not** directly usable here: it
declares the submodules as private `mod parser;` / `mod unparser;` and emits an unconditional
`#[pymodule]`, whereas the formatter macro needs `pub mod parser;` / `pub mod unparser;` (so
`my_grammar_cst::parser::Parser` resolves) and the pyo3 wiring gated behind the `python` feature
(so `default-features = false` yields a pure rlib). Hand-write `src/lib.rs` exactly as
`crates/fegen-rust/src/lib.rs` does:

```rust
#[cfg(feature = "python")]
use fltk_cst_core::register_submodule;
#[cfg(feature = "python")]
use pyo3::prelude::*;

mod cst; // private: parser/unparser reach it via `super::cst`
pub mod parser; // pub so `my_grammar_cst::parser::Parser` resolves
pub mod unparser; // pub so `my_grammar_cst::unparser::Unparser` resolves

#[cfg(feature = "python")]
#[pymodule]
fn my_grammar_cst(m: &Bound<'_, PyModule>) -> PyResult<()> {
    register_submodule(m, "cst", cst::register_classes)?;
    register_submodule(m, "parser", parser::register_classes)?;
    register_submodule(m, "unparser", unparser::register_classes)?;
    Ok(())
}
```

Your start rule determines the method names the formatter macro will reference — for
`fegen.fltkg` the start rule is `grammar`, giving `apply__parse_grammar` and `unparse_grammar`.

See `docs/rust-cst-extension-guide.md` for the broader Rust-CST background (building/installing
the crate as a Python extension module, and the pin alternatives for the `*-core` crates). The
formatter-specific deltas — `rlib` in `crate-type`, the `fltk-parser-core` / `fltk-unparser-core`
dependencies, the `pub mod parser/unparser`, and consuming with `default-features = false` — are
the parts shown above.

---

## Step 2: The consumer crate and its `Cargo.toml`

Create a binary crate. It needs exactly two dependencies: your grammar's CST crate (with
`default-features = false` to drop pyo3) and `fltk-fmt-cli`. The render types
(`RendererConfig`, `Renderer`, `resolve_spacing_specs`) reach the macro through
`fltk-fmt-cli`'s re-exports, so you do **not** name `fltk-unparser-core` yourself; the parser /
unparser runtime crates come in transitively.

```toml
# A standalone workspace (like crates/fltkfmt): the CST dependency's *default* features pull in
# pyo3, so keeping this crate out of any parent workspace avoids feature unification re-enabling
# pyo3. Consequence: build artifacts land under this crate's own target/, not a parent
# workspace root — see the run commands below. Drop this line if you instead make the crate a
# member of an existing workspace.
[workspace]

[package]
name = "my-grammar-fmt"
version = "0.1.0"
edition = "2021"

[[bin]]
name = "my-grammar-fmt"
path = "src/main.rs"

[dependencies]
# Your grammar's pure-Rust parser + unparser. default-features = false drops pyo3.
my-grammar-cst = { path = "../my-grammar-cst", default-features = false }
# Reusable CLI scaffolding: the fltk_formatter_main! macro + the render re-exports it names.
# fltk-fmt-cli is not published to crates.io; pin by path or git, as for the *-core crates
# (see docs/rust-cst-extension-guide.md).
fltk-fmt-cli = { path = "../fltk/crates/fltk-fmt-cli" }
```

---

## Step 3: Invoke the macro

The entire `src/main.rs` is one invocation:

```rust
fltk_fmt_cli::fltk_formatter_main! {
    parser:   my_grammar_cst::parser::Parser,
    unparser: my_grammar_cst::unparser::Unparser,
    parse:    apply__parse_<start_rule>,
    unparse:  unparse_<start_rule>,
}
```

Parameters:

| Parameter  | What it is | Value |
|------------|------------|-------|
| `parser`   | Path to your grammar's generated parser type (`path`). | `my_grammar_cst::parser::Parser` |
| `unparser` | Path to your grammar's generated unparser type (`path`). | `my_grammar_cst::unparser::Unparser` |
| `parse`    | The start-rule parse method name (a bare `ident`, not a path). | `apply__parse_<start_rule>` |
| `unparse`  | The start-rule unparse method name (a bare `ident`). | `unparse_<start_rule>` |

`<start_rule>` is the grammar rule you want to format whole documents against. The method names
are taken as identifiers (no `paste`/`concat_idents` needed), so substitute your rule name
directly: e.g. start rule `document` → `parse: apply__parse_document`, `unparse:
unparse_document`.

The four keys must appear in exactly the order shown — `parser`, `unparser`, `parse`, `unparse`.
Despite the keyword labels they are positional (the macro has a single fixed-order arm), so
reordering them produces a macro-match error rather than working.

The expansion is pure sugar over `fltk_fmt_cli::run_main`. If you need to customize the
pipeline (e.g. a different consumed-input policy), call `run_main` directly with your own
`Fn(&str, Option<&str>, RendererConfig) -> Result<String, String>` closure instead of using the
macro.

---

## The CLI surface you get for free

Every generated binary exposes the same flags (from `FmtArgs` / clap):

| Flag | Meaning |
|------|---------|
| `[FILES]...` | Input files to format. None (or `-`) reads from stdin. |
| `--check` | Report whether inputs are already formatted without writing; exit non-zero if not. |
| `--in-place` | Rewrite each input file in place (atomic temp+rename). Requires at least one file. |
| `-w, --width <N>` | Maximum line width. Default `80`. |
| `-i, --indent <N>` | Indentation width. Default `2`. |
| `-o, --output <PATH>` | Write output to this file instead of stdout (single input only). |
| `--help`, `--version` | Supplied automatically by clap. |

Behavior baked into the scaffolding:

- **Default**: format each input to stdout (multiple inputs concatenate in order).
- **Exit codes**: `0` success; `1` when `--check` finds an input that would change; `2` for any
  error (usage, read/write failure, parse/unparse failure). Processing continues across all
  inputs; the returned code is the worst outcome seen.
- **Rejected combinations** (exit `2` with a usage message): `--in-place` with `--output`,
  `--check`, no file, or `-`; `--check` with `--output`; `--output` with more than one input.
- **Errors** are prefixed with the input's filename (`<stdin>` for stdin); a partial parse
  (non-whitespace left unconsumed) and a depth-limit overflow are both reported as errors.

---

## Minimal end-to-end example

For a grammar whose start rule is `grammar` (this is exactly `crates/fltkfmt/src/main.rs`):

```rust
fltk_fmt_cli::fltk_formatter_main! {
    parser:   fegen_rust_cst::parser::Parser,
    unparser: fegen_rust_cst::unparser::Unparser,
    parse:    apply__parse_grammar,
    unparse:  unparse_grammar,
}
```

Build and run:

Because the consumer crate is its own workspace (Step 2), its artifacts land under
`crates/my-grammar-fmt/target/`, not a parent workspace root. Use the manifest-relative binary
path (or `cargo run --manifest-path ...`):

```bash
cargo build --release --manifest-path crates/my-grammar-fmt/Cargo.toml
BIN=crates/my-grammar-fmt/target/release/my-grammar-fmt

# Format a file to stdout
"$BIN" input.mygrammar

# Reformat in place at 100 columns, 4-space indent
"$BIN" --in-place -w 100 -i 4 src/*.mygrammar

# CI gate: fail if anything is unformatted
"$BIN" --check src/*.mygrammar

# Pipe through stdin → stdout
cat input.mygrammar | "$BIN"
```

(If you instead made the crate a member of an existing workspace, the binary is at that
workspace root's `target/release/my-grammar-fmt`.)

That is the whole recipe: generate the pure-Rust parser + unparser for your grammar, add the
two-line `Cargo.toml`, and write one `fltk_formatter_main!` invocation.
