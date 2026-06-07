// Standalone non-FLTK user-extension fixture for Phase 4 testing.
// Demonstrates the user build pattern: a cdylib crate whose #[pymodule]
// init calls the generated register_classes.  Independent of fltk's crate
// at link time.
//
// Span and SourceText are registered so pyo3 can extract Span arguments in the
// generated span setter (fltk._native.Span is the same Rust type from fltk-cst-core).
use fltk_cst_core::{SourceText, Span};
use pyo3::prelude::*;

mod cst;
mod native_tests;

#[pymodule]
fn phase4_roundtrip_cst(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Span>()?;
    m.add_class::<SourceText>()?;
    cst::register_classes(m)?;
    Ok(())
}
