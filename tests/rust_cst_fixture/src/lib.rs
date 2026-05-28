// Standalone non-FLTK user-extension fixture for Phase 4 testing.
// Demonstrates the user build pattern: a cdylib crate whose #[pymodule]
// init calls the generated register_classes.  Independent of fltk's crate
// at link time; depends on fltk._native only at runtime.
use pyo3::prelude::*;

mod cst;

#[pymodule]
fn phase4_roundtrip_cst(m: &Bound<'_, PyModule>) -> PyResult<()> {
    cst::register_classes(m)?;
    Ok(())
}
