Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

Commit reviewed: 5e29293

---

**errhandling-1**

File: `crates/fltk-cst-core/src/cross_cdylib.rs:44–53` (`get_span_type`)

Broken path: `py.import("fltk._native")` can fail (module not installed, import cycle, bad interpreter state). The error propagates via `?` inside `get_or_try_init`, then returned as-is from `get_span_type`. Every caller (`extract_span`, `get_span_type` call-sites in generated node methods) propagates it further with no added context.

Why: The error message from pyo3's `ModuleNotFoundError` or `ImportError` will say something like `"No module named 'fltk._native'"` — it carries no information about which cdylib initiated the load, which node method was being called, or what the caller was trying to accomplish. Compare `get_source_text_type` (same file, line 64–79): it wraps the import error with `"span source preservation requires fltk._native (SourceText): {e}"`, giving on-call engineers a diagnostic anchor. `get_span_type` (which is called far more widely — every single node `get_span`, `set_span`, `children`, `push_child` call) has no such wrapping; the raw pyo3 exception propagates up Python's traceback with no Rust-side context.

Consequence: When `fltk._native` fails to import in a generated-code consumer (wrong wheel installed, version skew, import cycle introduced), every `get_span_type` failure produces a bare `ModuleNotFoundError` or `AttributeError` with no indication it originated in a cross-cdylib span-type lookup. On-call cannot distinguish a general Python import failure from the specific cross-cdylib initialization failure without reading the pyo3 source. The asymmetry with `get_source_text_type` is not justified in any comment.

Fix: Wrap the import chain inside `get_span_type`'s `get_or_try_init` closure with `.map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("cross-cdylib Span type lookup failed (fltk._native.Span): {e}")))` — matching the pattern already applied in `get_source_text_type`.

---

**errhandling-2**

File: `crates/fltk-cst-core/src/cross_cdylib.rs:43–46` (`extract_span`, error branch)

Broken path: The slow-path type-error branch calls `obj.get_type().name()?`. The `name()` call on a `Bound<'_, PyType>` returns `PyResult<Cow<str>>` — it can itself fail (e.g. `__name__` attribute missing or not a str, which is valid in adversarial Python). If it fails, the `?` propagates a generic `AttributeError`/`TypeError` rather than the `PyTypeError` the caller expects, and the original "wrong type passed to span slot" context is entirely lost.

Why: The caller of `extract_span` (e.g. `set_span`, `extract_from_pyobject`) is expecting either a `Span` or a clear `PyTypeError` explaining what was received. If `name()` fails, the propagated error is a different exception type with no message indicating that the value was a wrong type for a span slot.

Consequence: On-call sees an `AttributeError` or similar exception with no indication it arose while validating a span argument. The diagnostic trail dead-ends at pyo3 internals. This is a narrow window (requires a truly malformed Python object) but the fix is trivial and the current code is not defensively written.

Fix: Replace `obj.get_type().name()?` with a fallback that cannot itself propagate — e.g. `obj.get_type().name().unwrap_or(std::borrow::Cow::Borrowed("<unknown type>"))` — so the `PyTypeError` is always emitted with whatever type-name information is available, without introducing a secondary failure path.

---

No other error-handling findings. The `unsafe { downcast_unchecked }` block's invariant is documented; the `GILOnceCell` per-cdylib duplication semantics are correct and documented; all `PyResult` returns propagate rather than swallow errors; no `unwrap`/`expect` on non-invariant paths; no `let _ =` on `Result`; no empty catch blocks.
