use pyo3::prelude::*;
use pyo3::sync::PyOnceLock;

mod span;

use span::{SourceText, Span};

// UNKNOWN_SPAN is set at module init (below) and exposed as `fltk._native.UnknownSpan`.
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
    Ok(())
}
