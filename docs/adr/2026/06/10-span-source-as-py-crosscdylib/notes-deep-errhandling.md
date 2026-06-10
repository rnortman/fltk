<!-- Concise. Precise. Complete. Unambiguous. No preamble. Audience: smart LLM/human. -->

## errhandling-1

**File:** `crates/fltk-cst-core/src/cross_cdylib.rs:59-77`

**Path:** `extract_source_text` slow path — `marker.extract::<&str>()` fails silently when `_fltk_cst_core_abi` is non-string (e.g. an integer, a bytes object, any non-str type).

```rust
if let Ok(marker) = obj.get_type().getattr(pyo3::intern!(py, "_fltk_cst_core_abi")) {
    if let Ok(s) = marker.extract::<&str>() {   // ← Err(_) drops here
        if s == FLTK_CST_CORE_ABI { ... }
        return Err(...ABI mismatch...);
    }
    // fall through to "expected fltk._native.SourceText" TypeError
}
```

When `marker.extract::<&str>()` returns `Err` (marker exists but is not a str), the inner `if let` does not match, control falls through the outer `if let Ok(marker)` body, and the function reaches the final `Err(PyTypeError::new_err(format!("expected fltk._native.SourceText, got {type_name}")))`. The caller receives a TypeError naming the Python type (e.g. `"expected fltk._native.SourceText, got MyFakeClass"`), not a message about the ABI attribute being the wrong type.

**Consequence:** On-call sees a confusing "expected SourceText, got X" error for a class that *does* have `_fltk_cst_core_abi` set, just not as a `str`. The real cause — `_fltk_cst_core_abi` has wrong type — is invisible in the error. Diagnosing this requires inspecting the Python class definition manually. The ABI-mismatch branch (the more informative path) is never taken when it would help with non-str markers.

**Fix:** After the `if let Ok(s) = marker.extract::<&str>()` fails, return a distinct `TypeError` naming both the attribute and its actual Python type:
```rust
if let Ok(marker) = obj.get_type().getattr(...) {
    if let Ok(s) = marker.extract::<&str>() {
        if s == FLTK_CST_CORE_ABI { ... }
        return Err(PyTypeError::new_err(format!(
            "SourceText ABI mismatch: ...")));
    }
    // New: attribute exists but is not a str
    let attr_type = marker.get_type().name()
        .map(|n| n.to_string())
        .unwrap_or_else(|_| "<unknown>".to_string());
    return Err(PyTypeError::new_err(format!(
        "expected fltk._native.SourceText: _fltk_cst_core_abi attribute is {attr_type}, not str"
    )));
}
```

---

## errhandling-2

**File:** `crates/fltk-cst-core/src/cross_cdylib.rs:99-119` (`span_to_pyobject`)

**Path:** `get_span_type` error is propagated with `?` from `span_to_pyobject`. Every caller that invokes `span_to_pyobject` — every span getter and every `to_pyobject` Span arm in every generated node — now propagates `get_span_type` failures through `?`. The design comment on `span_to_pyobject` says the sourceless arm is "unchanged in semantics from today's `call1`." That is correct for the error *type* (PyRuntimeError) but not for the call frequency: previously `get_span_type` was called once per accessor method (guarding both branches), now it is still called once per `span_to_pyobject` invocation, including the fast path. This is not a regression — it was the same before — and is handled. No finding here.

*(Documented to avoid re-raising during future review: `get_span_type` failure is correctly propagated as `PyRuntimeError` at all call sites. No silent swallow.)*

---

## errhandling-3

**File:** `crates/fltk-cst-core/src/cross_cdylib.rs:103-104` (`span_to_pyobject` fast path)

**Path:** Fast-path `Py::new(py, span.clone())` returns `PyResult<Py<Span>>`, mapped with `.map(|p| p.into_any())`. `Py::new` can fail if the GIL allocation fails (OOM). The `?` propagation is correct; the error is a `PyMemoryError` and surfaces to the Python caller. No silent swallow.

*(Documented to avoid re-raising: the allocation error is correctly propagated.)*

---

## errhandling-4

**File:** `crates/fltk-cst-core/src/cross_cdylib.rs:108-118` (`span_to_pyobject` slow path, source-bearing arm)

**Path:** `span.source_as_py(py)?` (`span.rs:165-175`) calls `Py::new(py, SourceText { inner: arc.clone() })`. If this `Py::new` fails (OOM), the `?` surfaces it as `PyMemoryError` — correct.

The subsequent `span_type.call_method1(intern!(py, "_with_source_unchecked"), ...)` is a Python method call into `Span::_with_source_unchecked`. That method calls `extract_source_text(source)`. The source argument is the `Py<SourceText>` from `source_as_py` — locally registered in this cdylib, so the fast path (`obj.downcast::<SourceText>()`) always succeeds. However: the `Py<SourceText>` from `source_as_py` is passed as `st` (a `Py<SourceText>`). When pyo3 converts it to the `&Bound<'_, PyAny>` parameter of `_with_source_unchecked`, it uses the locally-registered type. The `downcast::<SourceText>()` fast path in `extract_source_text` tests against the *executing cdylib's* (i.e. `fltk._native`'s) type registry. But `_with_source_unchecked` executes inside `fltk._native` (it is a classmethod on `fltk._native.Span`), while `source_as_py` creates a `SourceText` registered with the *consumer* cdylib's type. So the fast path in `extract_source_text` will NOT match (different type objects), and it falls to the slow path ABI-marker check. That slow path is correct and will succeed. No error, but the comment "fast path...succeeds when caller is the same cdylib" in `extract_source_text` is slightly misleading in this specific invocation. Not an error-handling finding — noting for accuracy.

---

No additional findings.

Commit reviewed: 588d55f
