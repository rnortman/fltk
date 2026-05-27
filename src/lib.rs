use pyo3::prelude::*;
use pyo3::sync::GILOnceCell;

mod cst_poc;
mod span;

use cst_poc::{Identifier, Identifier_Label, Items, Items_Label};
use span::{Span, SourceText};

pub(crate) static UNKNOWN_SPAN: GILOnceCell<PyObject> = GILOnceCell::new();

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Span>()?;
    m.add_class::<SourceText>()?;
    let unknown_span_obj = Py::new(
        m.py(),
        Span {
            start: -1,
            end: -1,
            source: None,
        },
    )?
    .into_any();
    m.add("UnknownSpan", unknown_span_obj.clone_ref(m.py()))?;
    UNKNOWN_SPAN
        .set(m.py(), unknown_span_obj)
        .expect("UNKNOWN_SPAN already set; module initialized twice");

    // CST node types
    m.add_class::<Identifier_Label>()?;
    m.add_class::<Identifier>()?;
    m.add_class::<Items_Label>()?;
    m.add_class::<Items>()?;

    Ok(())
}
