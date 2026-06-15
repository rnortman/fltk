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

The generated file depends on `fltk-cst-core` (for `Span`/`SourceText` and cross-cdylib helpers)
and on PyO3. You must declare both as Cargo dependencies (see Step 2).

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
default = ["extension-module"]
extension-module = ["python", "pyo3/extension-module"]
python = ["fltk-cst-core/python"]

[dependencies]
# fltk-cst-core is not published to crates.io. Use whichever pin method suits your setup
# (uncomment one):
#
# Path pin (local FLTK checkout):
#   fltk-cst-core = { path = "../fltk/crates/fltk-cst-core", default-features = false, features = ["python"] }
#
# Git pin (specific revision):
#   fltk-cst-core = { git = "https://github.com/rnortman/fltk", rev = "<commit-sha>", default-features = false, features = ["python"] }
#
# Bazel: see the Bazel section in this guide instead of a Cargo pin.
pyo3 = { version = "0.29", features = ["abi3-py310"] }
# NOTE: existing consumer extension crates must be rebuilt against fltk-cst-core 0.2 + pyo3 0.29.
# The ABI string marker in fltk-cst-core 0.2 deterministically rejects old builds (pyo3 0.23/fltk-cst-core 0.1)
# with a TypeError on first cross-cdylib span operation, preventing silent layout-skew UB.
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

## Migrating an existing consumer crate

If you built a consumer crate against an older version of FLTK that did not declare `fltk-cst-core`
as a dependency, you need to make two changes before or alongside upgrading:

1. **Add the `fltk-cst-core` dependency** to your `Cargo.toml` (see template in Step 2 above).
   Without it, unresolved `fltk_cst_core` imports in your committed `cst.rs` will fail to compile.

2. **Add the `python` feature block** (`default`, `extension-module`, `python` as shown above).
   Without it, `cargo build` emits `unexpected_cfgs` warnings and then fails because `register_classes`
   is conditionally compiled out (`#[cfg(feature = "python")]`) but referenced from your
   `#[pymodule]` init.

Both changes are required regardless of whether you regenerate `cst.rs`. Apply them first, then
rebuild. If you then regenerate (`make gencode` equivalent), the new cfg-gated output is compatible
with the same `Cargo.toml`.

`node.children` returns a snapshot on the Rust backend; mutate via the named mutator API.

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

`tests/rust_cst_fixture/` follows this exact pattern and serves as a working example. Build it with `make build-test-user-ext`.
`crates/fegen-rust/` (built via `make build-fegen-rust-cst`) is a more complete example: it
includes a `.pyi` stub and demonstrates the `extension-module`/`python` feature split used
to keep pyo3 out of non-Python builds.
These are FLTK-internal; they are not the user build recipe.
