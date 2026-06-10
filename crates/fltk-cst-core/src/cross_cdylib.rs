use crate::{SourceText, Span};
use pyo3::exceptions::PyTypeError;
use pyo3::prelude::*;
use pyo3::sync::GILOnceCell;
use pyo3::types::PyType;
use pyo3::PyTypeInfo;

/// ABI marker baked into the rlib: every cdylib linking the same fltk-cst-core rlib
/// (with the same Cargo.toml version) exposes this exact string as
/// `SourceText._fltk_cst_core_abi` via a `#[classattr]`. Used by
/// `extract_source_text` (below) to gate `downcast_unchecked` without relying on
/// type-object identity (unavailable in the canonical→consumer direction; see design §2.1–2.2).
///
/// TODO(crosscdylib-abi-sentinel): unify this marker with the sentinel planned for
/// `extract_span`/`get_span_type`. The current derivation (CARGO_PKG_VERSION alone)
/// does NOT cover pyo3-resolution skew — two builds of the same fltk-cst-core version
/// with different pyo3 versions produce identical markers over different
/// `PyClassObject<SourceText>` layouts (→ UB, not TypeError). The strengthened
/// derivation must fold in the pyo3 version and/or a layout hash. Until then,
/// locations relying on this marker: `extract_source_text` (this file),
/// `SourceText::_fltk_cst_core_abi` classattr (span.rs).
pub const FLTK_CST_CORE_ABI: &str = concat!("fltk-cst-core/", env!("CARGO_PKG_VERSION"));

/// Extract a native `SourceText` (O(1): clones the inner `Arc`) from a Python object,
/// accepting a `SourceText` registered by this cdylib or by any other cdylib that links
/// the same fltk-cst-core rlib (gated by the `_fltk_cst_core_abi` class marker).
///
/// Called only from `Span::_with_source_unchecked` (span.rs), which is itself an
/// underscore-private method called only by generated code passing `source_as_py` results.
///
/// # Safety contract
/// The gate is the `_fltk_cst_core_abi` class attribute. This marker is a string and is
/// therefore forgeable from pure Python. Passing a forged-marker object is UB. This is
/// acceptable because:
///   (a) the only caller is `Span::_with_source_unchecked`, which is private by convention;
///   (b) direct Python calls to an underscore-private method with a forged object are out
///       of contract; the SAFETY comment and method docstring document this.
/// Conversely, the marker is *stronger* than isinstance under version skew: a mismatch
/// produces a clean TypeError naming both ABI strings instead of proceeding to UB.
///
/// Soundness (mirrors `extract_span`'s SAFETY comment at `cross_cdylib.rs`):
///   Both cdylibs MUST link the same fltk-cst-core rlib (same pyo3 version, same struct
///   layout). Then `PyClassObject<SourceText>` layout is identical and `downcast_unchecked`
///   merely reinterprets the same in-memory representation. `SourceText` is `#[pyclass(frozen)]`
///   and `Sync` (`Arc<SourceInner{String}>`), so `Bound::get()` returns `&SourceText` without
///   a borrow-flag check. Arc refcount mutation and deallocation across cdylibs is safe because
///   Rust's default global allocator is the shared process-wide system allocator.
///   `SourceText` is not Python-subclassable (no `subclass` on `#[pyclass(frozen)]`), so
///   no inherited-marker-with-extended-layout case exists.
pub fn extract_source_text(obj: &Bound<'_, PyAny>) -> PyResult<SourceText> {
    // Fast path: locally-registered SourceText (succeeds when caller is the same cdylib).
    if let Ok(st) = obj.downcast::<SourceText>() {
        return Ok(SourceText {
            inner: st.get().inner.clone(),
        });
    }
    // Slow path: foreign-cdylib SourceText. Gate on the ABI marker classattr.
    let py = obj.py();
    if let Ok(marker) = obj.get_type().getattr(pyo3::intern!(py, "_fltk_cst_core_abi")) {
        if let Ok(s) = marker.extract::<&str>() {
            if s == FLTK_CST_CORE_ABI {
                // SAFETY: ob_type carries `_fltk_cst_core_abi == FLTK_CST_CORE_ABI`, proving
                // both cdylibs link the same fltk-cst-core rlib. `PyClassObject<SourceText>`
                // layout is therefore identical; the downcast reinterprets the same memory.
                // Forgery: a hand-crafted class could set `_fltk_cst_core_abi` to the right
                // value and still have a mismatched layout — UB. The caller (`_with_source_unchecked`)
                // is underscore-private and documented as out-of-contract for forged inputs.
                let st = unsafe { obj.downcast_unchecked::<SourceText>() };
                return Ok(SourceText {
                    inner: st.get().inner.clone(),
                });
            }
            return Err(PyTypeError::new_err(format!(
                "SourceText ABI mismatch: object reports {s:?}, this module expects \
                 {FLTK_CST_CORE_ABI:?} (fltk-cst-core version skew between cdylibs)"
            )));
        }
        // Marker attribute exists but is not a str — report the actual type.
        let attr_type = marker
            .get_type()
            .name()
            .map(|n| n.to_string())
            .unwrap_or_else(|_| "<unknown>".to_string());
        return Err(PyTypeError::new_err(format!(
            "expected fltk._native.SourceText: _fltk_cst_core_abi attribute \
             is {attr_type}, not str"
        )));
    }
    Err(PyTypeError::new_err(format!(
        "expected fltk._native.SourceText, got {}",
        py_type_name(obj)
    )))
}

/// Return the Python type name of `obj` for use in error messages.
fn py_type_name(obj: &Bound<'_, PyAny>) -> String {
    obj.get_type()
        .name()
        .map(|n| n.to_string())
        .unwrap_or_else(|_| "<unknown type>".to_string())
}

/// Build the canonical `fltk._native.Span` PyObject from a native `Span`.
/// O(1) in source length; preserves Arc-sharing of the source.
///
/// Fast path (this cdylib IS `fltk._native`): `Span::type_object` pointer-identity confirms
/// local registration IS canonical registration; `Py::new` constructs directly with zero
/// Python calls. Covers both source-bearing and sourceless spans.
///
/// Slow path (consumer cdylib such as out-of-tree crates): one O(1) `Py::new`
/// (`source_as_py`) + one Python method call (`_with_source_unchecked`) + one classattr
/// getattr (the ABI marker check inside `extract_source_text`). Sourceless arm unchanged.
pub fn span_to_pyobject(py: Python<'_>, span: &Span) -> PyResult<PyObject> {
    // TODO(crosscdylib-abi-sentinel): cache the "am I the canonical cdylib" bool and the
    // bound `_with_source_unchecked` classmethod in GILOnceCell to avoid re-deriving
    // process-constant facts on every span accessor call (currently: get_span_type +
    // type_object().is() + call_method1 each time on the slow path).
    let span_type = get_span_type(py)?;
    // Fast path: this cdylib IS fltk._native — type objects are pointer-identical.
    // Local registration is canonical registration; construct directly, zero Python calls.
    if Span::type_object(py).is(&span_type) {
        return Py::new(py, span.clone()).map(|p| p.into_any());
    }
    // Slow path: cross-cdylib (consumer crate). Source is shared O(1) via source_as_py;
    // _with_source_unchecked accepts the locally-registered SourceText via the ABI marker.
    match span.source_as_py(py)? {
        Some(st) => span_type
            .call_method1(
                pyo3::intern!(py, "_with_source_unchecked"),
                (span.start(), span.end(), st),
            )
            .map(|b| b.unbind()),
        None => span_type
            .call1((span.start(), span.end()))
            .map(|b| b.unbind()),
    }
}

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
    Err(PyTypeError::new_err(format!(
        "expected fltk._native.Span, got {}",
        py_type_name(obj)
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
///
/// Retained for compatibility with previously-generated consumer `cst.rs` files that still
/// call `get_source_text_type` / `source_full_text_str`. Removal would break consumer
/// builds on fltk upgrade before regeneration. Use `span_to_pyobject` for new generated code.
pub(crate) static FLTK_NATIVE_SOURCE_TEXT_TYPE: GILOnceCell<Py<PyType>> = GILOnceCell::new();

/// Return the `fltk._native.SourceText` Python type object, loading it once on first call.
///
/// Retained for compatibility with previously-generated consumer `cst.rs` files.
/// New generated code uses `span_to_pyobject` instead (O(1) source-preserving path).
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
