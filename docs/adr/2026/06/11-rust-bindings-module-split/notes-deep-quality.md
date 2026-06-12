## quality-1

**File:line**: `fltk/fegen/genparser.py:298-318` (gen-rust-cst docstring)

**Issue**: The `gen-rust-cst` docstring says the generated `cst.rs` "wires into the cst submodule of the compiled extension, e.g. `<module>.cst`" but does not show the `lib.rs` wiring pattern a downstream consumer must write. Design §2.3 explicitly states the canonical consumer pattern should be "documented in genparser.py help text and the fixture lib.rs comments" and provides the code snippet. The help-text change adds one sentence about submodule placement but omits the snippet entirely.

**Consequence**: Out-of-tree consumers — FLTK's primary audience — reading `genparser gen-rust-cst --help` learn that the output goes into a `cst` submodule but have no guidance on how to wire it. They must discover `register_submodule` by grepping the test fixtures or reading `fltk-cst-core` source. As more consumers adopt the Rust backend this discovery gap will repeat; the design's explicit intent was to prevent it.

**Fix**: Add a short wiring example to the `gen-rust-cst` docstring showing the canonical `lib.rs` pattern:

```rust
// In your lib.rs:
use fltk_cst_core::register_submodule;
#[pymodule]
fn my_grammar(m: &Bound<'_, PyModule>) -> PyResult<()> {
    register_submodule(m, "cst", cst::register_classes)?;
    register_submodule(m, "parser", parser::register_classes)?;
    Ok(())
}
```

Place it in the docstring after the submodule placement sentence (line 307) or in the Examples section.
