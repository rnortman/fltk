use pyo3::prelude::*;
use pyo3::sync::GILOnceCell;

mod cst_generated;
mod cst_fegen;
mod span;

use span::{Span, SourceText};

// UNKNOWN_SPAN is set at module init (below) and exposed as `fltk._native.UnknownSpan`.
// Generated node code no longer reads crate::UNKNOWN_SPAN directly; each generated
// extension caches the sentinel via its own GILOnceCell (UNKNOWN_SPAN_CACHE) by importing
// `fltk._native.UnknownSpan` at runtime.  The static is retained here so that any
// external code that might hold a reference to the crate-internal value still works;
// it is not dead in the sense of the module being broken, but no generated code reads it.
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

    // CST node types (PoC grammar: Identifier, Items, Trivia)
    cst_generated::register_classes(m)?;

    // Fegen grammar classes in a submodule to avoid name collisions
    // (both grammars produce Identifier, Items, Trivia)
    let fegen_sub = PyModule::new(m.py(), "fegen_cst")?;
    cst_fegen::register_classes(&fegen_sub)?;
    m.add_submodule(&fegen_sub)?;

    // PyO3's add_submodule does NOT register in sys.modules, so
    // `from fltk._native.fegen_cst import X` would fail with
    // ModuleNotFoundError. Fix by inserting manually:
    let sys = m.py().import("sys")?;
    sys.getattr("modules")?
        .set_item("fltk._native.fegen_cst", &fegen_sub)
        .map_err(|e| {
            pyo3::exceptions::PyRuntimeError::new_err(format!(
                "Failed to register fltk._native.fegen_cst in sys.modules: {e}"
            ))
        })?;

    Ok(())
}
