pub mod cst;
pub mod parser;
mod native_tests;

#[cfg(feature = "python")]
use fltk_cst_core::{SourceText, Span};
#[cfg(feature = "python")]
use pyo3::prelude::*;

#[cfg(feature = "python")]
#[pymodule]
fn rust_parser_fixture(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Span>()?;
    m.add_class::<SourceText>()?;
    cst::register_classes(m)?;
    parser::register_classes(m)?;
    Ok(())
}
