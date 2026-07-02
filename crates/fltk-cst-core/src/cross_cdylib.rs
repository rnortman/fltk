use crate::{escape::escape_control_chars, SourceText, Span};
use pyo3::exceptions::PyTypeError;
use pyo3::impl_::pyclass::PyClassImpl;
use pyo3::prelude::*;
use pyo3::sync::PyOnceLock;
use pyo3::types::PyType;
use pyo3::PyTypeInfo;

/// ABI marker baked into the rlib: every cdylib linking the same fltk-cst-core rlib
/// (with the same Cargo.toml version) exposes this exact string as
/// `SourceText._fltk_cst_core_abi` and `Span._fltk_cst_core_abi` via `#[classattr]`s.
/// Used by `extract_source_text` and `get_span_type` (below) to gate `cast_unchecked`
/// without relying on type-object identity (unavailable in the canonical→consumer
/// direction; see design §2.1–2.2).
///
/// The string alone does NOT cover pyo3-resolution skew. The companion
/// `_fltk_cst_core_abi_layout` classattr (`size_of::<<T as PyClassImpl>::Layout>()`) detects
/// layout differences that the version string cannot — both are checked together
/// by `check_abi_pair`.
pub const FLTK_CST_CORE_ABI: &str = concat!("fltk-cst-core/", env!("CARGO_PKG_VERSION"));

/// Cached reference to a validated foreign `SourceText` type object.
///
/// On the cross-cdylib slow path of `extract_source_text`, every call from a consumer cdylib
/// routes through `Span::_with_source_unchecked` → `extract_source_text`.  This is the
/// **normal path** for source-bearing span reads from generated consumer code — not a rare
/// edge case.  Without caching, each call re-validates the ABI pair via two `getattr` calls.
///
/// This cell holds the first validated foreign `SourceText` type pointer.  On subsequent calls
/// the type-object pointer is compared directly (O(1), no Python calls) before falling back to
/// the full ABI validation on type mismatch (handles the case where multiple foreign cdylibs
/// each register their own `SourceText` class).
///
/// `None` cell = not yet populated (first call) or canonical cdylib (fast-path hits `cast`
/// above and never reaches this cell).
static FLTK_FOREIGN_SOURCE_TEXT_TYPE: PyOnceLock<Py<PyType>> = PyOnceLock::new();

/// Extract a native `SourceText` (O(1): clones the inner `Arc`) from a Python object,
/// accepting a `SourceText` registered by this cdylib or by any other cdylib that links
/// the same fltk-cst-core rlib (gated by the `_fltk_cst_core_abi`,
/// `_fltk_cst_core_abi_layout`, and `__basicsize__` checks).
///
/// Called only from `Span::_with_source_unchecked` (span.rs), which is itself an
/// underscore-private method called only by generated code passing `source_as_py` results.
///
/// # Safety contract
/// On a cache miss the gate is:
///
/// 1. `check_abi_pair` (ABI string + layout attribute pair) — version-skew diagnostic.
/// 2. `check_instance_layout` (`__basicsize__` of the object's actual type) — rejects
///    pure-Python forged-marker objects that copy the two class attributes but whose
///    CPython allocation is not a genuine `PyStaticClassObject<SourceText>`.
///
/// Only on BOTH passing is the type cached (`get_or_init`) and `cast_unchecked` reached.
///
/// **Ordering is load-bearing** (see `check_abi_pair`→basicsize→`get_or_init` invariant):
///   `check_abi_pair` runs first so its pinned diagnostic messages continue to fire for
///   ABI-string/layout-attr mismatch inputs; the basicsize gate then narrows the forgery
///   window further.  If the basicsize gate ran first, existing tests that pin `check_abi_pair`
///   error messages would receive the basicsize message instead, silently weakening coverage.
///   The cache cell (`FLTK_FOREIGN_SOURCE_TEXT_TYPE`) can therefore only ever hold a type
///   that has passed both gates.
///
/// **Cache hit**: type-object pointer identity to a cell that, by the above invariant, can
///   only hold a basicsize-validated type — no re-check needed.
///
/// **Residual (documented, not closed)**: `check_instance_layout` rejects custom-metaclass
///   forgeries (step 1) and reads `tp_basicsize` via the immutable `type.__basicsize__`
///   descriptor (step 2, safe only after step 1).  A `__slots__`-padded forge whose
///   `tp_basicsize` exactly matches the expected value and whose metaclass is the built-in
///   `type` passes both steps; `cast_unchecked` on such an object is still UB.  This residual
///   (size necessary but not sufficient) is identical in kind to the one already documented in
///   the `check_abi_pair` SAFETY comment and accepted by the project.
///
/// Soundness when the gate passes: both cdylibs link the same fltk-cst-core rlib (same pyo3
/// version, same struct layout), so `PyClassObject<SourceText>` layout is identical and
/// `cast_unchecked` merely reinterprets the same in-memory representation.
/// `SourceText` is `#[pyclass(frozen)]` and `Sync` (`Arc<SourceInner{String}>`), so
/// `Bound::get()` returns `&SourceText` without a borrow-flag check. Arc refcount mutation
/// and deallocation across cdylibs is safe because Rust's default global allocator is the
/// shared process-wide system allocator. `SourceText` is not Python-subclassable (no
/// `subclass` on `#[pyclass(frozen)]`), so no inherited-marker-with-extended-layout case.
pub fn extract_source_text(obj: &Bound<'_, PyAny>) -> PyResult<SourceText> {
    // Fast path: locally-registered SourceText (succeeds when caller is the same cdylib).
    if let Ok(st) = obj.cast::<SourceText>() {
        return Ok(SourceText {
            inner: st.get().inner.clone(),
        });
    }
    // Slow path: foreign-cdylib SourceText.  This IS the normal path when generated consumer
    // code reads a source-bearing span: `span_to_pyobject` calls `source_as_py` (which
    // produces a consumer-registered `SourceText`) and passes it to `_with_source_unchecked`,
    // which calls this function.  The consumer-registered type fails the `downcast` above
    // (different cdylib type-object) and arrives here on every cross-cdylib source-bearing span
    // read.  The `FLTK_FOREIGN_SOURCE_TEXT_TYPE` cell caches the validated type after the first
    // call so subsequent calls are a single type-object pointer comparison.
    //
    let py = obj.py();
    let obj_type = obj.get_type();

    // Cache hit: if this is the same foreign type we already validated, skip full ABI check.
    // SAFETY: By the cache-seeding invariant below, this cell can only hold a type that has
    // passed both `check_abi_pair` and `check_instance_layout`; pointer identity to that
    // cell entry is genuine provenance.
    if let Some(cached_type) = FLTK_FOREIGN_SOURCE_TEXT_TYPE.get(py) {
        if cached_type.bind(py).is(&obj_type) {
            let st = unsafe { obj.cast_unchecked::<SourceText>() };
            return Ok(SourceText {
                inner: st.get().inner.clone(),
            });
        }
    }

    // Cache miss: run both gates before seeding the cache.
    //
    // Gate 1 — ABI pair (version-skew diagnostic).  Runs first so its pinned error messages
    // fire for ABI-string/layout-attr mismatches; the basicsize gate below adds rejection power
    // on top without replacing these messages.
    check_abi_pair::<SourceText>(&obj_type, "SourceText", || py_type_obj_name(&obj_type))?;
    // Gate 2 — `tp_basicsize` genuineness check.  Rejects pure-Python forged-marker objects:
    // a class body can copy the two ABI attributes but cannot present a matching `tp_basicsize`
    // without `__slots__` padding that changes the real CPython instance allocation.
    // First verifies the type has no custom metaclass (which could shadow `__basicsize__`
    // via a property), then reads `__basicsize__` from the now-provably-safe built-in descriptor.
    check_instance_layout::<SourceText>(&obj_type, "SourceText")?;
    // Both gates passed; cache this foreign type object for O(1) pointer-compare on
    // future calls.  `get_or_init` is a no-op if already populated (another thread
    // raced here first — harmless, both observed the same validated type).
    // Invariant: the cell can only ever hold a type that has passed both gates above.
    let _ = FLTK_FOREIGN_SOURCE_TEXT_TYPE.get_or_init(py, || obj_type.clone().unbind());
    // SAFETY: `obj_type` has passed `check_abi_pair` (ABI string + layout attribute match)
    // and `check_instance_layout` (`tp_basicsize` matches `size_of::<<SourceText as
    // PyClassImpl>::Layout>()`).  Together these are consistent with both cdylibs linking
    // the same fltk-cst-core rlib at the same pyo3 version; `cast_unchecked` merely
    // reinterprets the same in-memory representation.
    // Residual: a `__slots__`-padded forge can match `tp_basicsize` while having a mismatched
    // field layout — `cast_unchecked` on such an object is still UB.  This residual is
    // identical in kind to the one documented in `check_abi_pair` and accepted by the project.
    let st = unsafe { obj.cast_unchecked::<SourceText>() };
    Ok(SourceText {
        inner: st.get().inner.clone(),
    })
}

/// Return the Python type name of any `PyAny` object for use in error messages
/// (control chars escaped via canonical `escape_control_chars`).
/// Works for both direct objects and attribute values.
fn py_any_type_name(obj: &Bound<'_, PyAny>) -> String {
    let raw = obj
        .get_type()
        .name()
        .map(|n| n.to_string())
        .unwrap_or_else(|_| "<unknown type>".to_string());
    escape_control_chars(&raw)
}

/// Return the fully-qualified Python type name of a type object for use in error messages
/// (control chars escaped via canonical `escape_control_chars`).
/// Uses `fully_qualified_name()` with fallback `"<unknown type>"`.
/// Note: pyo3 strips `"builtins"` and `"__main__"` module prefixes, so classes defined in
/// those modules render as bare `__qualname__` (e.g. `"str"`, `"SourceText"`).
/// Classes in test modules render fully qualified (e.g. `"test_rust_span.<locals>.FakeSource"`).
fn py_type_obj_name(ty: &Bound<'_, PyType>) -> String {
    let raw = ty
        .fully_qualified_name()
        .map(|n| n.to_string())
        .unwrap_or_else(|_| "<unknown type>".to_string());
    escape_control_chars(&raw)
}

/// Validate the cross-cdylib ABI pair (`_fltk_cst_core_abi` string marker, then
/// `_fltk_cst_core_abi_layout == size_of::<<T as PyClassImpl>::Layout>()`) on `ty`.
///
/// `type_label` is the logical class name used in error prefixes ("SourceText" or "Span").
/// `subject_fn` is called lazily — only when an error is being constructed — to produce the
/// string identifying the checked type in error bodies.  Callers supply:
/// - Span path: `|| "fltk._native.Span".to_string()` (lookup-path identity, truthful even
///   when that attribute is monkeypatched, as the subprocess gate tests do).
/// - SourceText path: `|| py_type_obj_name(&obj_type)` (derived from caller-supplied type;
///   called only on the failure branch, avoiding an eager Python C-API round-trip on every
///   slow-path validation that succeeds).
///
/// `Ok(())` means `ty` is safe to treat as `T` for `cast_unchecked`, subject to the
/// documented forgery and size-preserving-skew residuals (see callers' SAFETY comments).
fn check_abi_pair<T: pyo3::PyClass>(
    ty: &Bound<'_, PyType>,
    type_label: &str,
    subject_fn: impl Fn() -> String,
) -> PyResult<()> {
    let py = ty.py();
    // Step 1: missing marker — treat as mismatch (pre-sentinel build or unrelated type).
    // Use map_err(|e| ...) rather than map_err(|_| ...) so that non-AttributeError
    // exceptions from a raising __getattr__ are captured in the diagnostic rather than
    // silently discarded.
    let marker = ty
        .getattr(pyo3::intern!(py, "_fltk_cst_core_abi"))
        .map_err(|e| {
            let subject = subject_fn();
            PyTypeError::new_err(format!(
                "{type_label} ABI mismatch: {subject} has no _fltk_cst_core_abi marker \
                 (not a {type_label} from a compatible fltk-cst-core build, or a \
                 pre-sentinel build); this module expects {FLTK_CST_CORE_ABI:?}\
                 ; getattr raised: {}",
                escape_control_chars(&e.to_string())
            ))
        })?;
    // Step 2: non-str marker.
    let s = marker.extract::<&str>().map_err(|e| {
        let subject = subject_fn();
        PyTypeError::new_err(format!(
            "{type_label} ABI mismatch: {subject}._fltk_cst_core_abi is {}, not str\
             ; extract raised: {}",
            py_any_type_name(&marker),
            escape_control_chars(&e.to_string())
        ))
    })?;
    // Step 3: string mismatch.
    if s != FLTK_CST_CORE_ABI {
        let subject = subject_fn();
        return Err(PyTypeError::new_err(format!(
            "{type_label} ABI mismatch: {subject} reports {s:?}, this module expects \
             {FLTK_CST_CORE_ABI:?} (fltk-cst-core version skew between cdylibs)"
        )));
    }
    // Step 4: compute expected layout.
    let expected_layout =
        std::mem::size_of::<<T as pyo3::impl_::pyclass::PyClassImpl>::Layout>();
    // Step 5: missing layout attr — same reasoning as step 1.
    let layout_attr = ty
        .getattr(pyo3::intern!(py, "_fltk_cst_core_abi_layout"))
        .map_err(|e| {
            let subject = subject_fn();
            PyTypeError::new_err(format!(
                "{type_label} ABI mismatch: {subject} has no _fltk_cst_core_abi_layout \
                 (partial-upgrade build); this module expects layout {expected_layout}\
                 ; getattr raised: {}",
                escape_control_chars(&e.to_string())
            ))
        })?;
    // Step 6: non-int layout attr.
    let reported_layout = layout_attr.extract::<usize>().map_err(|e| {
        let subject = subject_fn();
        PyTypeError::new_err(format!(
            "{type_label} ABI mismatch: {subject}._fltk_cst_core_abi_layout is {}, not int\
             ; extract raised: {}",
            py_any_type_name(&layout_attr),
            escape_control_chars(&e.to_string())
        ))
    })?;
    // Step 7: layout mismatch.
    if reported_layout != expected_layout {
        let subject = subject_fn();
        return Err(PyTypeError::new_err(format!(
            "{type_label} ABI layout mismatch: {subject} reports layout {reported_layout}, \
             this module expects {expected_layout} \
             (pyo3-resolution skew between cdylibs)"
        )));
    }
    Ok(())
}

/// Check that `ty`'s CPython `tp_basicsize` equals the compile-time layout size of `T`.
///
/// Two-step check:
///
/// **Step 1 — metaclass guard**: verify that `type(ty)` is exactly the built-in `type`.
/// A custom metaclass can define a `__basicsize__` property that returns any value, so
/// reading `ty.__basicsize__` via `getattr` is only safe when the metaclass is `type`
/// itself (which is both immutable and cannot be monkeypatched from Python).
/// pyo3-allocated types always have `type` as their metaclass.  A metaclass-property forge
/// has a custom metaclass and is caught here.
///
/// **Step 2 — basicsize gate**: read `ty.__basicsize__` via `getattr` and compare against the
/// compile-time layout size.  After step 1 confirms the metaclass is exactly `type`, the
/// `__basicsize__` attribute is resolved via the immutable built-in `type.__basicsize__`
/// data descriptor, which cannot be shadowed by any user-defined Python object.  Anything
/// whose CPython type does not carry a matching `tp_basicsize` (e.g. a class without enough
/// `__slots__` padding) is rejected here.
///
/// Any read/extract failure is surfaced as a diagnostic `TypeError` rather than an unwrap
/// panic, mirroring `check_abi_pair`'s `map_err` discipline.
///
/// `type_label` is the logical class name used in error prefixes (e.g. "SourceText"),
/// matching the convention of `check_abi_pair`.  The helper is generic so it can later be
/// reused for other types (e.g. `Span` in §2.C) without message confusion.
///
/// **Residual**: a `__slots__`-padded forge whose `tp_basicsize` exactly matches the expected
/// value and whose metaclass is `type` (default for plain Python classes) passes both steps.
/// This residual (size necessary but not sufficient for layout identity) is identical in kind
/// to the one already accepted and documented in the `check_abi_pair` SAFETY comments; it is
/// not closed by this helper.
fn check_instance_layout<T: PyClassImpl>(ty: &Bound<'_, PyType>, type_label: &str) -> PyResult<()> {
    let py = ty.py();
    let expected = std::mem::size_of::<<T as PyClassImpl>::Layout>();

    // Step 1: metaclass guard — reject types with a custom metaclass.
    // `PyType::type_object(py)` is the built-in `type`.  A type whose metaclass is anything
    // other than `type` can shadow `__basicsize__` via a metaclass property.
    let metaclass = ty.get_type();
    if !metaclass.is(PyType::type_object(py)) {
        let meta_name = metaclass
            .name()
            .map(|n| escape_control_chars(&n.to_string()))
            .unwrap_or_else(|_| "<unknown>".to_string());
        return Err(PyTypeError::new_err(format!(
            "{type_label} instance layout check failed: type has a custom metaclass \
             ({meta_name}), which may shadow __basicsize__ via a property; only a genuine \
             pyo3-allocated {type_label} from a compatible cdylib is accepted"
        )));
    }

    // Step 2: basicsize gate — metaclass is exactly `type`, so `__basicsize__` resolves
    // via the immutable built-in data descriptor and cannot be intercepted from Python.
    let basicsize = ty
        .getattr(pyo3::intern!(py, "__basicsize__"))
        .map_err(|e| {
            PyTypeError::new_err(format!(
                "{type_label} instance layout check failed: __basicsize__ not readable on type \
                 (exotic or proxy type?); getattr raised: {}",
                escape_control_chars(&e.to_string())
            ))
        })?
        .extract::<usize>()
        .map_err(|e| {
            PyTypeError::new_err(format!(
                "{type_label} instance layout check failed: __basicsize__ is not an integer; \
                 extract raised: {}",
                escape_control_chars(&e.to_string())
            ))
        })?;
    if basicsize != expected {
        return Err(PyTypeError::new_err(format!(
            "{type_label} instance layout check failed: object type __basicsize__ is {basicsize}, \
             expected {expected} (not a genuine {type_label} allocation — possible forged-marker \
             object; only a genuine pyo3-allocated {type_label} from a compatible cdylib is accepted)"
        )));
    }
    Ok(())
}

/// Cached: whether this cdylib IS `fltk._native` (fast-path bypass for `span_to_pyobject`).
/// `true` = local `Span::type_object` IS the canonical type; use `Py::new` directly.
/// `false` = slow path: call `_with_source_unchecked` on the canonical type.
/// Populated once on the first `span_to_pyobject` call. Initializing this cell calls
/// `get_span_type`, which populates `FLTK_NATIVE_SPAN_TYPE` as a side effect.
static IS_CANONICAL_CDYLIB: PyOnceLock<bool> = PyOnceLock::new();

/// Cached reference to the bound `fltk._native.Span._with_source_unchecked` classmethod.
/// Used on the slow path of `span_to_pyobject` to avoid a `getattr` + `call_method1`
/// per invocation. Only populated when `IS_CANONICAL_CDYLIB == false`.
static WITH_SOURCE_UNCHECKED_METHOD: PyOnceLock<Py<PyAny>> = PyOnceLock::new();

/// Build the canonical `fltk._native.Span` Python object (`Py<PyAny>`) from a native `Span`.
/// O(1) in source length; preserves Arc-sharing of the source.
///
/// Fast path (this cdylib IS `fltk._native`): cached `IS_CANONICAL_CDYLIB == true` →
/// `Py::new` constructs directly with zero Python calls. Covers both source-bearing and
/// sourceless spans.
///
/// Slow path (consumer cdylib such as out-of-tree crates): one O(1) `Py::new`
/// (`source_as_py`) + one cached Python method call (`_with_source_unchecked`).
/// Sourceless arm uses `call1` on the canonical type (no source, no method needed).
pub fn span_to_pyobject(py: Python<'_>, span: &Span) -> PyResult<Py<PyAny>> {
    let is_canonical = IS_CANONICAL_CDYLIB.get_or_try_init(py, || {
        let span_type = get_span_type(py)?;
        Ok::<bool, PyErr>(Span::type_object(py).is(&span_type))
    })?;

    if *is_canonical {
        // Fast path: this cdylib IS fltk._native — construct directly, zero Python calls.
        return Py::new(py, span.clone()).map(|p| p.into_any());
    }

    // Slow path: cross-cdylib (consumer crate). Source is shared O(1) via source_as_py;
    // _with_source_unchecked accepts the locally-registered SourceText via the ABI marker.
    match span.source_as_py(py)? {
        Some(st) => {
            let method = WITH_SOURCE_UNCHECKED_METHOD.get_or_try_init(py, || {
                let span_type = get_span_type(py)?;
                span_type
                    .getattr(pyo3::intern!(py, "_with_source_unchecked"))
                    .map(|m| m.unbind())
                    .map_err(|e| {
                        pyo3::exceptions::PyRuntimeError::new_err(format!(
                            "fltk._native.Span._with_source_unchecked lookup failed: {}",
                            escape_control_chars(&e.to_string())
                        ))
                    })
            })?;
            method
                .call1(py, (span.start(), span.end(), st))
        }
        None => {
            // `FLTK_NATIVE_SPAN_TYPE` is guaranteed populated here (IS_CANONICAL_CDYLIB init
            // above called get_span_type as a side effect), so this is a cheap PyOnceLock
            // hit — no additional Python import or validation.
            let span_type = get_span_type(py)?;
            span_type
                .call1((span.start(), span.end()))
                .map(|b| b.unbind())
        }
    }
}

/// Cached reference to the `fltk._native.Span` Python type object.
/// Used by the span setter to validate cross-cdylib span arguments
/// (pyo3 `extract::<Span>()` only matches the locally-registered class;
/// runtime isinstance against the canonical class is required for cross-module compatibility).
pub(crate) static FLTK_NATIVE_SPAN_TYPE: PyOnceLock<Py<PyType>> = PyOnceLock::new();

/// Extract a native `Span` from a Python object, accepting any span registered
/// either in this cdylib or in `fltk._native` (cross-cdylib compatibility).
///
/// The two-gate check in `get_span_type` (called below) ensures that the returned reference
/// type has passed both `check_abi_pair::<Span>` (version/layout-skew diagnostic) AND
/// `check_instance_layout::<Span>` (`tp_basicsize` genuineness), failing once, on first use,
/// with a clear `TypeError` — before any `cast_unchecked`. This is the same dual-gate invariant
/// established for `extract_source_text`.
pub fn extract_span(py: Python<'_>, obj: &Bound<'_, PyAny>) -> PyResult<Span> {
    // Fast path: locally-registered Span type (succeeds when caller uses the same cdylib's Span).
    if let Ok(span_ref) = obj.extract::<Span>() {
        return Ok(span_ref);
    }
    // Slow path: check against fltk._native.Span (cross-cdylib: fltk._native Span
    // registered there, not here).  `get_span_type` has already dual-gated the canonical type
    // (or will fail with TypeError on first call under skew/forgery) — so is_instance +
    // cast_unchecked is sound given the invariant that both cdylibs link the same fltk-cst-core
    // rlib with the same pyo3 version.
    let native_span_type = get_span_type(py)?;
    if obj.is_instance(&native_span_type)? {
        // SAFETY: `get_span_type` ran BOTH gates on the returned type before caching it:
        // `check_abi_pair::<Span>` (verified `_fltk_cst_core_abi == FLTK_CST_CORE_ABI` and
        // `_fltk_cst_core_abi_layout == size_of::<<Span as PyClassImpl>::Layout>()`) and
        // `check_instance_layout::<Span>` (verified the type's `tp_basicsize` matches that same
        // layout size via the immutable `type.__basicsize__` descriptor). `Span` is not
        // Python-subclassable (`#[pyclass(frozen)]`, no `subclass`), so a passing `is_instance`
        // means the object's type IS that dual-gated reference type. These checks are consistent
        // with both cdylibs linking the same fltk-cst-core rlib at the same pyo3 version, but do
        // not prove it — size equality does not imply field-layout equality. The gates narrow —
        // not close — the skew window. Accepted risk: for frozen pyo3 types without dict/weakref,
        // PyClassImpl::Layout (PyStaticClassObject<T>) reduces to {ffi::PyObject, T} (repr(C)); a
        // size-preserving internal reorder is not constructible without changing ffi::PyObject.
        // Residual: a `__slots__`-padded plain-Python forge whose `tp_basicsize` matches and
        // whose metaclass is `type` passes both gates; instances of such a forge (and of an
        // un-padded subclass of it, which also satisfies `is_instance`) reach this
        // `cast_unchecked` and are still UB. Mounting that attack requires building the padded
        // forge anyway, so validating the reference type (rather than the object's own type)
        // adds no attacker power. Identical in kind to the residual accepted for
        // `extract_source_text`.
        let span = unsafe { obj.cast_unchecked::<Span>() };
        return Ok(span.borrow().clone());
    }
    Err(PyTypeError::new_err(format!(
        "expected fltk._native.Span, got {}",
        py_any_type_name(obj)
    )))
}

/// Return the `fltk._native.Span` Python type object, loading it once on first call.
///
/// Two-gate check on the first call (both run inside the `PyOnceLock` init):
///
/// 1. `check_abi_pair::<Span>` — `_fltk_cst_core_abi` string + `_fltk_cst_core_abi_layout`
///    attribute pair; version/layout-skew diagnostic.
/// 2. `check_instance_layout::<Span>` — `tp_basicsize` of the resolved type (via the immutable
///    `type.__basicsize__` descriptor, after a metaclass guard). Rejects a pure-Python
///    forged-marker class that copies the two ABI attributes but whose CPython allocation is
///    not a genuine `PyStaticClassObject<Span>`.
///
/// **Ordering is load-bearing** (same as the `SourceText` path): `check_abi_pair` runs first so
/// its pinned diagnostic messages continue to fire for ABI-string/layout-attr mismatch inputs
/// (the existing subprocess tests that pin `check_abi_pair` error messages); the basicsize gate
/// then narrows the forgery window further. Because both gates run before `get_or_try_init` seeds
/// the cell, `FLTK_NATIVE_SPAN_TYPE` can only ever hold a type that passed BOTH gates — mirroring
/// the documented `FLTK_FOREIGN_SOURCE_TEXT_TYPE` invariant. Every consumer of this function
/// (`extract_span`, `span_to_pyobject`, and the generated `cst.rs` call sites) therefore
/// receives an already-dual-gated reference type.
///
/// `Span` is not Python-subclassable (`#[pyclass(frozen)]`, no `subclass` flag), so an
/// `is_instance` pass against the returned type means the object's type IS that dual-gated type.
///
/// When this cdylib IS `fltk._native`, the check compares the canonical type against itself
/// (same classattrs, genuine layout); it always passes and is O(1) beyond the `PyOnceLock` hit.
///
/// The padded-forge residual (accepted, not closed) is documented at its canonical homes:
/// `check_instance_layout`'s doc comment and the SAFETY comment in `extract_span`.
pub fn get_span_type(py: Python<'_>) -> PyResult<Bound<'_, PyType>> {
    FLTK_NATIVE_SPAN_TYPE
        .get_or_try_init(py, || {
            let span_type = py
                .import("fltk._native")
                .and_then(|m| m.getattr("Span"))
                .and_then(|s| s.cast_into::<PyType>().map_err(|e| e.into()))
                .map_err(|e| {
                    pyo3::exceptions::PyRuntimeError::new_err(format!(
                        "cross-cdylib Span type lookup failed (fltk._native.Span): {}",
                        escape_control_chars(&e.to_string())
                    ))
                })?;
            check_abi_pair::<Span>(&span_type, "Span", || "fltk._native.Span".to_string())?;
            check_instance_layout::<Span>(&span_type, "Span")?;
            Ok(span_type.unbind())
        })
        .map(|t| t.bind(py).clone())
}

/// Cached reference to the `fltk._native.SourceText` Python type object.
///
/// Retained for compatibility with previously-generated consumer `cst.rs` files that still
/// call `get_source_text_type` / `source_full_text_str`. Removal would break consumer
/// builds on fltk upgrade before regeneration. Use `span_to_pyobject` for new generated code.
pub(crate) static FLTK_NATIVE_SOURCE_TEXT_TYPE: PyOnceLock<Py<PyType>> = PyOnceLock::new();

/// Return the `fltk._native.SourceText` Python type object, loading it once on first call.
///
/// Retained for compatibility with previously-generated consumer `cst.rs` files.
/// New generated code uses `span_to_pyobject` instead (O(1) source-preserving path).
///
/// # Safety contract gap
/// The returned type object is NOT ABI-validated (no `check_abi_pair` call).
/// Callers MUST NOT use it for `cast_unchecked` — restrict use to `isinstance` checks
/// only, or call `check_abi_pair` separately before any unchecked downcast.
pub fn get_source_text_type(py: Python<'_>) -> PyResult<Bound<'_, PyType>> {
    FLTK_NATIVE_SOURCE_TEXT_TYPE
        .get_or_try_init(py, || {
            py.import("fltk._native")
                .and_then(|m| m.getattr("SourceText"))
                .and_then(|s| s.cast_into::<PyType>().map_err(|e| e.into()))
                .map(|t: Bound<'_, PyType>| t.unbind())
                .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!(
                    "span source preservation requires fltk._native (SourceText): {}",
                    escape_control_chars(&e.to_string())
                )))
        })
        .map(|t| t.bind(py).clone())
}
