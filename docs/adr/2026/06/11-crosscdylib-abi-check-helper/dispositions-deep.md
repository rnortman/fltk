Style: concise, precise, complete, unambiguous. No padding, no preamble.

Commit: ad58891

---

errhandling-1:
- Disposition: Fixed
- Action: Changed `map_err(|_|` to `map_err(|e|` for both `getattr` calls (step 1 at cross_cdylib.rs:182–190, step 5 at cross_cdylib.rs:216–225) in `check_abi_pair`. Original error appended as `"; getattr raised: {e}"` in the message body. Non-AttributeError exceptions now visible in the diagnostic.
- Severity assessment: Wrong diagnosis of `__getattr__`-raising failures — on-call sees "no ABI marker" when the actual error was unrelated. Not a safety hazard (error still raised), but misleading. Fixed.

errhandling-2:
- Disposition: Fixed
- Action: Changed `map_err(|_|` to `map_err(|e|` for both `extract` calls (step 2 at cross_cdylib.rs:192–200, step 6 at cross_cdylib.rs:227–234). Original extraction error appended as `"; extract raised: {e}"` in the message. Unusual extraction failures now visible.
- Severity assessment: Low probability (extraction errors on bare attr values are almost always type mismatches already described by `py_attr_type_name`), but unusual descriptor failures would have been misdiagnosed. Fixed.

errhandling-3:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: Retracted by the reviewer — `get_or_init` is infallible, `let _` is correct. Not a finding.
- Rationale (Won't-Do): Reviewer self-retracted. `GILOnceCell::get_or_init` is infallible; there is no error to handle.

errhandling-4:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: Reviewer confirmed this is correct — `map_err(|e| ... {e})` already preserves the original error. Not a finding.
- Rationale (Won't-Do): Reviewer marked as no finding.

errhandling-5:
- Disposition: Fixed
- Action: Added "Safety contract gap" doc comment to `get_source_text_type` (cross_cdylib.rs:365–369) warning that the returned type is NOT ABI-validated and callers must not use it for `downcast_unchecked` without calling `check_abi_pair` separately.
- Severity assessment: Documentation gap in the safety contract — a future caller could obtain an unvalidated type object and misuse it for unchecked downcasts with no warning. No current caller does this. Fixed by documentation.

errhandling-6:
- Disposition: Fixed
- Action: Added `.map_err(|e| PyRuntimeError::new_err(format!("fltk._native.Span._with_source_unchecked lookup failed: {e}")))` wrapping the `getattr` call for `_with_source_unchecked` inside `WITH_SOURCE_UNCHECKED_METHOD.get_or_try_init` (cross_cdylib.rs:275–282). Error now names the method and module.
- Severity assessment: Minor observability gap — a missing `_with_source_unchecked` attribute would surface as a bare `AttributeError` with no context. Not a safety issue. Fixed.

security-1:
- Disposition: Fixed
- Action: (Round 1) Added `escape_control_chars_for_msg` and applied it in all three type-name helpers. (Round 2 rework) Escaped the four `PyErr` Display strings added by the errhandling-1/2 fixes: `"; getattr raised: {e}"` at steps 1 and 5 and `"; extract raised: {e}"` at steps 2 and 6 — each now wrapped as `escape_control_chars_for_msg(&e.to_string())` (cross_cdylib.rs:211, 219, 241, 249 at commit 466df05). A raising metaclass `__getattr__` delivers attacker-chosen text in `{e}`; an ordinary AttributeError embeds `__name__` from the class; both can carry control characters. All attacker-influenced interpolations now escaped.
- Severity assessment: Log injection / terminal escape-sequence injection via crafted `__qualname__`, `__module__`, or exception message. Requires attacker-controlled class to reach the error path. No memory-safety or gate-bypass impact. Fixed.

test-1:
- Disposition: Fixed
- Action: Strengthened `test_with_source_unchecked_non_str_marker_raises_type_error` (test_rust_span.py:328–342): changed `match="_fltk_cst_core_abi"` to `match="SourceText ABI mismatch"` and added assertions for `"_fltk_cst_core_abi"` and `"not str"` in `str(exc_info.value)`.
- Severity assessment: The non-str-marker error path on the SourceText branch could regress silently to any message containing `"_fltk_cst_core_abi"`. Strengthened assertion pins the unified template.

test-2:
- Disposition: Fixed
- Action: Added two subprocess tests to `TestSpanPathAbiGate` (test_rust_span.py:641–718): `test_non_str_abi_marker_raises_type_error` (patches `_fltk_cst_core_abi` to `42`, asserts `"Span ABI mismatch"` and `"not str"`) and `test_non_int_abi_layout_raises_type_error` (patches `_fltk_cst_core_abi_layout` to `"oops"`, asserts `"Span ABI mismatch"` and `"not int"`). Both pass after `make build-test-user-ext` rebuilds phase4.
- Severity assessment: Templates 2 and 5 on the Span path were untested via subprocess; regressions in those branches would be invisible. Fixed.

test-3:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: Reviewer self-identified as non-finding. Substring assertion `"FakeSource" in msg` is intentionally loose and sufficient per the design (§2).
- Rationale (Won't-Do): Not a finding.

reuse-1:
- Disposition: Fixed
- Action: (Round 2 rework) Merged `py_type_name` and `py_attr_type_name` into a single `py_any_type_name(obj: &Bound<'_, PyAny>) -> String` (cross_cdylib.rs at commit 466df05). Both had identical bodies (`get_type().name()`, escape, `"<unknown type>"` fallback — the sole difference was an inconsistent fallback string `"<unknown>"` vs `"<unknown type>"`). The `extract_span` call site updated from `py_type_name` → `py_any_type_name`. The four `check_abi_pair` call sites updated from `py_attr_type_name` → `py_any_type_name`. Removed the `TODO(crosscdylib-helper-consolidation)` comment and `TODO.md` entry. `py_type_obj_name` retained — different input type and name method.
- Severity assessment: Two module-private helpers with byte-identical bodies (modulo inconsistent fallback string) now unified. Low severity; code quality cleanup. Fixed.

efficiency-1:
- Disposition: Fixed
- Action: Changed `check_abi_pair` parameter from `subject: &str` to `subject_fn: impl Fn() -> String` (cross_cdylib.rs:170). Closure called only inside error arms (steps 1–7 failure branches). SourceText call site: `|| py_type_obj_name(&obj_type)` — `fully_qualified_name()` Python C-API call deferred to failure path. Span call site: `|| "fltk._native.Span".to_string()` — static str, trivially cheap even lazy.
- Severity assessment: On the cross-cdylib SourceText slow path with a single-slot cache miss (the normal consumer code path for uncached types), every validation call previously allocated a `String` and made a Python C-API round-trip even on success. With multiple distinct foreign `SourceText` types (cache permanently misses beyond the first), this cost was per-span-read. Fixed to error-path-only.
