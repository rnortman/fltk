use pyo3::prelude::*;

#[pyclass]
struct Ping;

#[pymethods]
impl Ping {
    #[new]
    fn new() -> Self {
        Ping
    }

    fn pong(&self) -> &str {
        "pong"
    }
}

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Ping>()?;
    Ok(())
}
