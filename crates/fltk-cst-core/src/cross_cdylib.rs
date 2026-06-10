use crate::Span;
use pyo3::exceptions::PyTypeError;
use pyo3::prelude::*;
use pyo3::sync::GILOnceCell;
use pyo3::types::PyType;

/// Cached reference to the `fltk._native.Span` Python type object.
/// Used by the span setter to validate cross-cdylib span arguments
/// (pyo3 `extract::<Span>()` only matches the locally-registered class;
/// runtime isinstance against the canonical class is required for cross-module compatibility).
pub(crate) static FLTK_NATIVE_SPAN_TYPE: GILOnceCell<Py<PyType>> = GILOnceCell::new();

/// Extract a native `Span` from a Python object, accepting any span registered
/// either in this cdylib or in `fltk._native` (cross-cdylib compatibility).
pub fn extract_span(py: Python<'_>, obj: &Bound<'_, PyAny>) -> PyResult<Span> {
    // Fast path: locally-registered Span type (succeeds when caller uses the same cdylib's Span).
    if let Ok(span_ref) = obj.extract::<Span>() {
        return Ok(span_ref);
    }
    // Slow path: check against fltk._native.Span (cross-cdylib: fltk._native Span
    // registered there, not here).  isinstance succeeds; downcast_unchecked is safe
    // because both cdylibs link the same fltk-cst-core rlib Span type.
    let native_span_type = get_span_type(py)?;
    if obj.is_instance(&native_span_type)? {
        // SAFETY: obj is a pyo3 PyCell<Span> instance (confirmed by isinstance above).
        // Both this cdylib and fltk._native MUST link the same fltk-cst-core rlib, so the
        // Span type layout is identical. The downcast_unchecked reinterprets the Python
        // object's underlying Span value, which is safe given identical type layout.
        // INVARIANT VIOLATION: if two different fltk-cst-core rlib versions are linked
        // (e.g. version skew between the installed fltk._native wheel and a consumer's
        // pinned revision), is_instance may still pass while the Span layout differs,
        // causing memory corruption (out-of-bounds Arc pointer deref, type confusion)
        // — not merely a wrong result. The deployment constraint is a single shared rlib.
        // TODO(crosscdylib-abi-sentinel): add a runtime ABI version/layout sentinel checked
        // once in get_span_type's GILOnceCell init so version skew fails with a clear error
        // rather than proceeding to UB.
        let span = unsafe { obj.downcast_unchecked::<Span>() };
        return Ok(span.borrow().clone());
    }
    let type_name = obj
        .get_type()
        .name()
        .map(|n| n.to_string())
        .unwrap_or_else(|_| "<unknown type>".to_string());
    Err(PyTypeError::new_err(format!(
        "expected fltk._native.Span, got {type_name}"
    )))
}

/// Return the `fltk._native.Span` Python type object, loading it once on first call.
pub fn get_span_type(py: Python<'_>) -> PyResult<Bound<'_, PyType>> {
    FLTK_NATIVE_SPAN_TYPE
        .get_or_try_init(py, || {
            py.import("fltk._native")
                .and_then(|m| m.getattr("Span"))
                .and_then(|s| s.downcast_into::<PyType>().map_err(|e| e.into()))
                .map(|t: Bound<'_, PyType>| t.unbind())
                .map_err(|e| {
                    pyo3::exceptions::PyRuntimeError::new_err(format!(
                        "cross-cdylib Span type lookup failed (fltk._native.Span): {e}"
                    ))
                })
        })
        .map(|t| t.bind(py).clone())
}

/// Cached reference to the `fltk._native.SourceText` Python type object.
/// Used when constructing source-bearing spans for cross-cdylib compatibility:
/// the locally-registered SourceText cannot be passed to `fltk._native.Span.with_source`,
/// so we construct a canonical `fltk._native.SourceText` from the full text string.
pub(crate) static FLTK_NATIVE_SOURCE_TEXT_TYPE: GILOnceCell<Py<PyType>> = GILOnceCell::new();

/// Return the `fltk._native.SourceText` Python type object, loading it once on first call.
pub fn get_source_text_type(py: Python<'_>) -> PyResult<Bound<'_, PyType>> {
    FLTK_NATIVE_SOURCE_TEXT_TYPE
        .get_or_try_init(py, || {
            py.import("fltk._native")
                .and_then(|m| m.getattr("SourceText"))
                .and_then(|s| s.downcast_into::<PyType>().map_err(|e| e.into()))
                .map(|t: Bound<'_, PyType>| t.unbind())
                .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!(
                    "span source preservation requires fltk._native (SourceText): {e}"
                )))
        })
        .map(|t| t.bind(py).clone())
}
