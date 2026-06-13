use fltk_cst_core::register_submodule;
use pyo3::prelude::*;
use pyo3::sync::PyOnceLock;

mod cst_fegen;
mod cst_generated;
mod span;

use span::{SourceText, Span};

// UNKNOWN_SPAN is set at module init (below) and exposed as `fltk._native.UnknownSpan`.
// Generated node code no longer reads crate::UNKNOWN_SPAN directly; each generated
// extension caches the sentinel via its own PyOnceLock (UNKNOWN_SPAN_CACHE) by importing
// `fltk._native.UnknownSpan` at runtime.  The static is retained here so that any
// external code that might hold a reference to the crate-internal value still works;
// it is not dead in the sense of the module being broken, but no generated code reads it.
pub(crate) static UNKNOWN_SPAN: PyOnceLock<Py<PyAny>> = PyOnceLock::new();

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Canonical Span/SourceText/UnknownSpan live at the top level.
    m.add_class::<Span>()?;
    m.add_class::<SourceText>()?;
    let unknown_span_obj = Py::new(m.py(), Span::unknown())?.into_any();
    m.add("UnknownSpan", unknown_span_obj.clone_ref(m.py()))?;
    UNKNOWN_SPAN
        .set(m.py(), unknown_span_obj)
        .expect("UNKNOWN_SPAN already set; module initialized twice");

    // PoC grammar classes in a submodule (avoids clobbering canonical Span/SourceText
    // if a PoC rule name collides, and keeps top-level clean).
    register_submodule(m, "poc_cst", cst_generated::register_classes)?;

    // Fegen grammar classes in a submodule (both grammars produce Identifier, Items, Trivia).
    register_submodule(m, "fegen_cst", cst_fegen::register_classes)?;

    Ok(())
}
