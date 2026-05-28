// Standalone fegen Rust CST extension for Phase 4 testing.
// Provides a Rust-backed CST for the fegen grammar (fegen.fltkg), importable
// as `fegen_rust_cst`.  Used by parse_grammar(rust_fegen_cst_module="fegen_rust_cst")
// to run the real Cst2Gsm against Rust-backed fegen nodes (AC8).
//
// Follows the same pattern as tests/rust_cst_fixture: a cdylib crate whose
// #[pymodule] init calls the generated register_classes.  Independent of
// fltk._native at link time; depends on it only at runtime for UnknownSpan.
use pyo3::prelude::*;

mod cst;

#[pymodule]
fn fegen_rust_cst(m: &Bound<'_, PyModule>) -> PyResult<()> {
    cst::register_classes(m)?;
    Ok(())
}
