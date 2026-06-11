// Standalone fegen Rust CST + parser extension for Phase 4 testing.
// Provides a Rust-backed CST and parser for the fegen grammar (fegen.fltkg),
// importable as `fegen_rust_cst`.
//
// The parser module is generated from fegen.fltkg and builds against the cst module.
#[cfg(feature = "python")]
use fltk_cst_core::{SourceText, Span};
#[cfg(feature = "python")]
use pyo3::prelude::*;

mod cst;
pub mod parser;
mod native_parser_tests;

#[cfg(feature = "python")]
#[pymodule]
fn fegen_rust_cst(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Span>()?;
    m.add_class::<SourceText>()?;
    cst::register_classes(m)?;
    parser::register_classes(m)?;
    Ok(())
}
