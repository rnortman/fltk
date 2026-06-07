// Standalone fegen Rust CST extension for Phase 4 testing.
// Provides a Rust-backed CST for the fegen grammar (fegen.fltkg), importable
// as `fegen_rust_cst`.  Used by parse_grammar(rust_fegen_cst_module="fegen_rust_cst")
// to run the real Cst2Gsm against Rust-backed fegen nodes (AC8).
//
// Follows the same pattern as tests/rust_cst_fixture: a cdylib crate whose
// #[pymodule] init calls the generated register_classes.  Independent of
// fltk._native at link time.
//
// Span and SourceText are registered so pyo3 can extract Span arguments in the
// generated span setter (fltk._native.Span is the same Rust type from fltk-cst-core).
use fltk_cst_core::{SourceText, Span};
use pyo3::prelude::*;

mod cst;

#[pymodule]
fn fegen_rust_cst(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Span>()?;
    m.add_class::<SourceText>()?;
    cst::register_classes(m)?;
    Ok(())
}
