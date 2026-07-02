use pyo3::prelude::*;
use pyo3::sync::PyOnceLock;

mod span;

use span::{LineColPos, SourceText, Span};

// UNKNOWN_SPAN is set at module init (below) and exposed as `_native.UnknownSpan`.
pub(crate) static UNKNOWN_SPAN: PyOnceLock<Py<PyAny>> = PyOnceLock::new();

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Canonical Span/SourceText/LineColPos/UnknownSpan live at the top level.
    m.add_class::<Span>()?;
    m.add_class::<SourceText>()?;
    m.add_class::<LineColPos>()?;
    let unknown_span_obj = Py::new(m.py(), Span::unknown())
        .map_err(|e| {
            pyo3::exceptions::PyRuntimeError::new_err(format!(
                "_native module init: failed to create UnknownSpan sentinel: {e}"
            ))
        })?
        .into_any();
    m.add("UnknownSpan", unknown_span_obj.clone_ref(m.py()))?;
    UNKNOWN_SPAN
        .set(m.py(), unknown_span_obj)
        .expect("UNKNOWN_SPAN already set; module initialized twice");
    Ok(())
}
