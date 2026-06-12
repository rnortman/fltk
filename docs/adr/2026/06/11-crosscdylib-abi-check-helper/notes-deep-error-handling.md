Style: concise, precise, complete, unambiguous. No padding, no preamble.

Commit reviewed: 912b285

## errhandling-1

**File:line**: `crates/fltk-cst-core/src/cross_cdylib.rs:162–170` (`check_abi_pair`, step 1)

**Broken error path**: `ty.getattr(...)` can fail for reasons other than AttributeError — e.g. a Python `__getattr__` that raises `ValueError`, `RuntimeError`, or any exception. The `map_err(|_|` discards the original error entirely and replaces it with the "has no _fltk_cst_core_abi marker" message regardless of what actually went wrong.

**Why**: The original error is swallowed unconditionally. On-call sees "has no _fltk_cst_core_abi marker (pre-sentinel build)" and concludes a missing attribute, when the actual cause was, say, a failing `__getattr__` or an import error triggered during attribute lookup.

**Consequence**: Misdiagnosis of any `getattr` failure that isn't AttributeError. Under a broken `__getattr__` hook the caller is told the type lacks the sentinel marker, which is false; the original exception is unrecoverable from the propagated TypeError. Not a safety hazard (the error is still raised; the unsafe downcast is still blocked), but the diagnostic is wrong.

**What must change**: If `getattr` raises an exception that is not `PyErr` wrapping `AttributeError`, preserve it — either re-raise the original, or wrap it: `"... has no _fltk_cst_core_abi marker ... (getattr raised: {e})"`. The same pattern applies to the `_fltk_cst_core_abi_layout` getattr at step 5 (line 189–196). Both `map_err(|_|` closures should capture the error and include it in the message or re-raise it when it is not an AttributeError. Minimal fix: change `map_err(|_|` to `map_err(|e|` and append `"; getattr raised: {e}"` to the message body. Correct fix: check `e.is_instance_of::<pyo3::exceptions::PyAttributeError>(py)` and re-raise non-AttributeError errors unmodified.

---

## errhandling-2

**File:line**: `crates/fltk-cst-core/src/cross_cdylib.rs:172–177` (`check_abi_pair`, step 2) and `198–203` (step 6)

**Broken error path**: `marker.extract::<&str>()` and `layout_attr.extract::<usize>()` both use `map_err(|_|` — the original extract error is dropped.

**Why**: Same as errhandling-1. The actual extraction error (e.g. a Python exception thrown during `__str__` or `__index__` conversion) is lost. Unlike step 1, these are even less likely to be masked by a non-obvious cause, but the pattern is still a silent swallow.

**Consequence**: Lower diagnostic risk than errhandling-1 (extraction errors on a bare attr value are almost always type mismatches), but any unusual extraction failure — e.g. a descriptor that raises on extraction — becomes "is int/str, not X" which may be wrong. No safety impact.

**What must change**: Same minimal fix: `map_err(|e|` and include `e` in the message. The type-reporting fallback (`py_attr_type_name`) already fires before the error message, so appending the raw pyo3 error provides the extra context without structural change.

---

## errhandling-3

**File:line**: `crates/fltk-cst-core/src/cross_cdylib.rs:97` (`extract_source_text`)

**Broken error path**: `let _ = FLTK_FOREIGN_SOURCE_TEXT_TYPE.get_or_init(py, || obj_type.clone().unbind());`

**Why**: `GILOnceCell::get_or_init` returns a reference; `let _ =` discards it. This is intentional per the comment ("no-op if already populated"). However `get_or_init` (infallible) is correct here — there is no error to propagate. This is not an error-handling gap; it is a deliberate `let _ =` on a non-Result value. No finding beyond noting it is correct.

*Retracted — not a finding. `get_or_init` is infallible; `let _` on a non-Result is fine.*

---

## errhandling-4

**File:line**: `crates/fltk-cst-core/src/cross_cdylib.rs:326–330` (`get_span_type`, import failure branch)

**Broken error path**: The `py.import("fltk._native") ... .map_err(|e| PyRuntimeError::new_err(...))` chain wraps the original `e` via `format!("... {e}")`. This is correct — the original error is included in the message. No finding.

---

## errhandling-5

**File:line**: `crates/fltk-cst-core/src/cross_cdylib.rs:350–361` (`get_source_text_type`)

**Broken error path**: This function performs `py.import` + `getattr("SourceText")` + `downcast_into::<PyType>()` and wraps the entire chain error in a single `PyRuntimeError`. No ABI check is performed. If `get_source_text_type` is ever used as a validation step (rather than merely as a type-object lookup), the lack of `check_abi_pair` would silently yield an unvalidated type object. However, the function docstring says it is a compatibility shim and new code uses `span_to_pyobject`. The design explicitly excludes it from the ABI gate.

**Consequence**: A caller of `get_source_text_type` that uses the returned type for `downcast_unchecked` without calling `check_abi_pair` itself bypasses the ABI gate entirely. The function does not document this gap in its safety contract.

**What must change**: Add a doc comment warning: "The returned type object is NOT ABI-validated. Callers must not use it for `downcast_unchecked` without calling `check_abi_pair` separately, or must restrict use to `isinstance` checks only." This is a documentation gap in the safety contract, not a code error, but it is an error-observability gap because a future caller has no indication they are receiving an unvalidated type.

---

## errhandling-6

**File:line**: `crates/fltk-cst-core/src/cross_cdylib.rs:252–257` (`span_to_pyobject`, slow path)

**Broken error path**: `WITH_SOURCE_UNCHECKED_METHOD.get_or_try_init` calls `get_span_type(py)?` a second time and then `.getattr(intern!(py, "_with_source_unchecked"))`. If the `getattr` fails (attribute doesn't exist on the canonical Span type), the error propagates as-is via `?` with no additional context added — caller gets a raw pyo3 AttributeError naming `_with_source_unchecked`.

**Consequence**: On-call sees a bare AttributeError with no indication of which module or function was being looked up. The call stack leads into pyo3 internals; the original `span_to_pyobject` call site is the only context and that may not name the attribute.

**What must change**: Wrap the getattr error: `.map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("fltk._native.Span._with_source_unchecked lookup failed: {e}")))`. This is a minor observability gap, not a safety issue.

---

## Summary

The primary finding is **errhandling-1** (and the same pattern at step 5 in the same function): `map_err(|_|` on `getattr` swallows non-AttributeError exceptions and produces a diagnostically incorrect "no marker" message. All other findings are documentation/minor observability gaps. No unsafe code paths are unsound — all seven validation steps are present and in order; errors are raised (not swallowed) on all failure branches; the unsafe downcast is reached only after `Ok(())`.
