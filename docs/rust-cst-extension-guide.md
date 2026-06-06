# Building a Rust CST Extension for Your Grammar

This guide explains how to compile a Rust CST backend for your grammar and use it with FLTK's
`generate_parser`. The Rust backend is optional — the Python dataclass backend (the default) works
without any of this.

---

## Overview

FLTK can generate Rust CST source from your grammar. You compile it into a standalone Python
extension module (a `cdylib`) using your own build tool, install it, and point `generate_parser`
at it by module name. FLTK never invokes `cargo`, `maturin`, or `rustc` at runtime.

**Runtime dependency:** your extension imports `fltk._native` lazily (on first node construction)
for the `UnknownSpan` sentinel. FLTK must be installed in the same environment. Rebuild your
extension if you upgrade FLTK and `Span`/`UnknownSpan` changed.

---

## Step 1: Emit Rust CST source

```bash
uv run python -m fltk.fegen.genparser gen-rust-cst my_grammar.fltkg cst.rs
```

This writes `cst.rs` — a Rust source file containing one struct per grammar rule, their label
enums, and a `register_classes` function that registers all types with a PyO3 module.

The generated file has no link-time dependency on FLTK's crate. It depends on PyO3 only.

---

## Step 2: Write the `cdylib` crate

Create a Cargo project with `crate-type = ["cdylib"]`. The only thing your crate needs is a
`#[pymodule]` init function that calls the generated `register_classes`.

**`Cargo.toml`**:

```toml
[package]
name = "my-grammar-cst"
version = "0.1.0"
edition = "2021"

[lib]
name = "my_grammar_cst"
crate-type = ["cdylib"]

[features]
extension-module = ["pyo3/extension-module"]
default = ["extension-module"]

[dependencies]
pyo3 = { version = "0.23", features = ["abi3-py310"] }
```

**`src/lib.rs`**:

```rust
use pyo3::prelude::*;

mod cst;  // the generated cst.rs

#[pymodule]
fn my_grammar_cst(m: &Bound<'_, PyModule>) -> PyResult<()> {
    cst::register_classes(m)?;
    Ok(())
}
```

Copy `cst.rs` into `src/cst.rs`. The module name (`my_grammar_cst`) must match the `[lib] name`
in `Cargo.toml` and the module name you will pass to `generate_parser`.

---

## Step 3: Build and install

Use any tool that can build a PyO3 `cdylib`:

```bash
# With maturin (recommended):
maturin develop           # editable install into the active virtualenv
maturin build --release   # build a wheel

# With pip + maturin as build backend:
pip install -e .
```

After installation, `import my_grammar_cst` must succeed in your Python environment.

---

## Step 4: Use the Rust backend

Pass the dotted module name to `generate_parser`:

```python
from pathlib import Path
from fltk.plumbing import generate_parser, parse_grammar_file

grammar = parse_grammar_file(Path("my_grammar.fltkg"))
pr = generate_parser(grammar, rust_cst_module="my_grammar_cst")

# pr.cst_module is a types.ModuleType backed by the Rust extension's classes.
# pr.parser_class is a parser that constructs Rust-backed nodes.
```

If the module cannot be imported, `generate_parser` raises `RustBackendUnavailableError`
immediately — no silent fallback to the Python backend.

---

## How it works

- `generate_parser` imports your module by name, reads all public `type` attributes off it, and
  sets them as attributes on a fresh `types.ModuleType` registered in `sys.modules` under the
  per-call name `fltk_grammar_{id(grammar)}`. This per-call module is the coupling string between
  the generated parser and any generated unparser — both backends use the same string.
- The generated parser constructs nodes from these class references. `isinstance` dispatch and
  label equality work because the same class objects are used for construction and comparison.
- Your extension calls `register_classes` in its `#[pymodule]` init, so by the time Python
  imports the module, it is already populated. FLTK reads classes off the imported module — it
  never calls `register_classes` from Python.

---

## Limitations

- **No grammar-consistency check.** If you pass a `rust_cst_module` built from a different grammar
  than the one passed to `generate_parser`, the mismatch surfaces at parse time as an
  `AttributeError` or `KeyError`, not at load time.
- **No ABI pinning.** A user extension built against one FLTK version may misbehave if
  `Span`/`UnknownSpan` changed in a newer FLTK version. Rebuild on upgrade.
- **`fltk._native` must be importable at parse time.** If FLTK is not installed, the first node
  construction (lazy sentinel fetch) raises `ImportError`.

---

## FLTK's own test artifacts

`tests/rust_cst_fixture/` and `tests/rust_cst_fegen/` follow this exact pattern and serve as
working examples. Build them with `make build-test-user-ext` and `make build-fegen-rust-cst`.
These are FLTK-internal; they are not the user build recipe.
