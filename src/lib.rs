use pyo3::prelude::*;

mod span;

use span::{Span, SourceText};

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Span>()?;
    m.add_class::<SourceText>()?;
    let unknown = Span {
        start: -1,
        end: -1,
        source: None,
    };
    m.add("UnknownSpan", Py::new(m.py(), unknown)?)?;
    Ok(())
}
