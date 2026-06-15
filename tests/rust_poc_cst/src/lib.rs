// Standalone PoC CST extension for testing.
// Provides the toy three-rule grammar (Identifier, Items, Trivia) as a
// top-level `poc_cst` module with a `cst` submodule — the uniform shape
// that every generated grammar extension uses.
//
// Python imports: from poc_cst.cst import Identifier, Items, Trivia
// Span/SourceText are not registered here; use fltk._native.Span / SourceText.
#![cfg_attr(not(feature = "python"), forbid(unsafe_code))]
#[cfg(feature = "python")]
use fltk_cst_core::register_submodule;
#[cfg(feature = "python")]
use pyo3::prelude::*;

pub mod cst;

#[cfg(test)]
mod spike_tests;

#[cfg(feature = "python")]
#[pymodule]
fn poc_cst(m: &Bound<'_, PyModule>) -> PyResult<()> {
    register_submodule(m, "cst", cst::register_classes)?;
    Ok(())
}
