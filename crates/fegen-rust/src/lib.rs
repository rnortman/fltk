// Standalone fegen Rust CST + parser extension for Phase 4 testing.
// Provides a Rust-backed CST and parser for the fegen grammar (fegen.fltkg),
// importable as `fegen_rust_cst`.
//
// The parser module is generated from fegen.fltkg and builds against the cst module.
// CST node classes and NodeKind are in the `cst` submodule; Parser and ApplyResult
// are in the `parser` submodule.  Span/SourceText are not registered here; use
// fltk._native.Span / fltk._native.SourceText.
#[cfg(feature = "python")]
use fltk_cst_core::register_submodule;
#[cfg(feature = "python")]
use pyo3::prelude::*;

mod cst;
pub mod parser;
pub mod unparser;
#[cfg(test)]
mod native_parser_tests;

#[cfg(feature = "python")]
#[pymodule]
fn fegen_rust_cst(m: &Bound<'_, PyModule>) -> PyResult<()> {
    register_submodule(m, "cst", cst::register_classes)?;
    register_submodule(m, "parser", parser::register_classes)?;
    register_submodule(m, "unparser", unparser::register_classes)?;
    Ok(())
}
