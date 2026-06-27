pub mod cst;
pub mod parser;
pub mod unparser;
pub mod unparser_default;
pub mod collision_cst;
pub mod collision_parser;
mod native_tests;

#[cfg(feature = "python")]
use fltk_cst_core::register_submodule;
#[cfg(feature = "python")]
use pyo3::prelude::*;

#[cfg(feature = "python")]
#[pymodule]
fn rust_parser_fixture(m: &Bound<'_, PyModule>) -> PyResult<()> {
    register_submodule(m, "cst", cst::register_classes)?;
    register_submodule(m, "parser", parser::register_classes)?;
    register_submodule(m, "unparser", unparser::register_classes)?;
    register_submodule(m, "unparser_default", unparser_default::register_classes)?;
    register_submodule(m, "collision_cst", collision_cst::register_classes)?;
    register_submodule(m, "collision_parser", collision_parser::register_classes)?;
    Ok(())
}
