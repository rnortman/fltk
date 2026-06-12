// Standalone non-FLTK user-extension fixture for Phase 4 testing.
// Demonstrates the user build pattern: a cdylib crate whose #[pymodule]
// init calls the generated register_classes.  Independent of fltk's crate
// at link time.
//
// Span and SourceText are registered at top level so tests can construct
// foreign-cdylib Span/SourceText instances from Python (required for the
// cross-cdylib span test suite: tests/test_rust_span.py TestSpanPathAbiGate
// and TestSpanToPyobjectCaching).  They are NOT needed for span extraction;
// extraction uses pyo3 type identity checks that work without registration.
use fltk_cst_core::{register_submodule, SourceText, Span};
use pyo3::prelude::*;

mod cst;
mod native_tests;

#[pymodule]
fn phase4_roundtrip_cst(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Span>()?;
    m.add_class::<SourceText>()?;
    register_submodule(m, "cst", cst::register_classes)?;
    Ok(())
}
