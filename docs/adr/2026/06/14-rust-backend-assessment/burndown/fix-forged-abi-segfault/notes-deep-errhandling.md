# Error-Handling Review: fix-forged-abi-segfault

Commit reviewed: 79460b6  
Base: d82e82f

---

## errhandling-1

**File:** `crates/fltk-cst-core/src/cross_cdylib.rs:127`

**The broken error path:**
```rust
let _ = FLTK_FOREIGN_SOURCE_TEXT_TYPE.get_or_init(py, || obj_type.clone().unbind());
```
The return value of `get_or_init` is silently discarded via `let _`. `PyOnceLock::get_or_init` returns `&T` (the stored value), so there is nothing that propagates as an error here — `get_or_init` does not return a `Result`. The `let _` is not swallowing a `Result`; it is discarding the `&Py<PyType>` reference to the now-cached value, which is never needed at this call site.

**Why it is mentioned:** `let _ = ...` on a non-`Result` value is not an error-handling defect. However, it is worth noting that this is not a silent-failure risk — `PyOnceLock::get_or_init` is infallible (the init closure cannot fail; it merely moves a `Py<PyType>` already in hand). No error is swallowed.

**Verdict:** Not a finding. The `let _` suppresses only the unused-variable lint on the returned `&Py<PyType>` reference. Infallible, no error path exists here.

---

## errhandling-2

**File:** `crates/fltk-cst-core/src/cross_cdylib.rs:274–301` (`check_instance_layout`)

**The broken error path:**
The helper is generic over `T: PyClassImpl` but its error messages are hard-coded to "SourceText":
```
"SourceText instance layout check failed: __basicsize__ not readable…"
"SourceText instance layout check failed: __basicsize__ is not an integer…"
"SourceText instance layout check failed: object type __basicsize__ is {basicsize}, expected {expected}…"
```

The function signature `fn check_instance_layout<T: PyClassImpl>` is generic by design (doc comment: "The helper is generic so it could later be reused for `extract_span`"). If a future caller passes `T = Span`, the error messages will incorrectly say "SourceText" — an on-call engineer investigating a span-gate failure would see misleading diagnostics pointing at `SourceText` instead of `Span`.

**Consequence:** No current misdiagnosis (the only call site is `check_instance_layout::<SourceText>`). But the genericness of the helper invites a future `check_instance_layout::<Span>` call (§2.C defers it, not closes it), at which point the hard-coded type label produces misleading diagnostic messages. A span-gate failure on the `extract_span` path would emit "SourceText instance layout check failed" — an on-call engineer has no way to tell which type or path caused the error from the message alone.

**What must change:** Either (a) make the type label a parameter (e.g. `type_label: &str`) the same way `check_abi_pair` does, or (b) derive the type name from `std::any::type_name::<T>()` as a fallback, or (c) add a `// FIXME: if ever called for Span, update error messages` comment so the defect is not latent-silent. Since the design itself flags §2.C as a future possibility, option (a) is the clean fix; option (c) is the minimum acceptable mitigation if this is intentionally left for §2.C.

---

No other findings. The core error propagation chain (getattr → map_err → PyTypeError, both gates returning PyResult and propagated via `?`, cache-hit path documented and reasoned, `cast_unchecked` SAFETY comments updated) is sound. The `unwrap_or_else(|_| "<unknown type>")` in `py_any_type_name` and `py_type_obj_name` are appropriate fallbacks for diagnostic string construction (not on a safety-gate path). The subprocess test isolation for UB-risk scenarios is correct discipline.
