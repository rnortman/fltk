# Error-handling review — pyo3-upgrade branch

Commit reviewed: 6df2369

Style note: concise, precise, complete, unambiguous; audience is a smart LLM/human.

---

## errhandling-1

**File:line:** `crates/fltk-cst-core/src/span.rs:380`, `span.rs:565`

**Broken error path:** Two doc comments refer to `GILOnceCell` after the rename to `PyOnceLock`
(`:380` — "Checked once in `get_span_type`'s `GILOnceCell` init"; `:565` — "Uses a `GILOnceCell`
cache"). Not a runtime path, but one comment is load-bearing for traceability: `:380` is the doc
for `Span._fltk_cst_core_abi` and it points on-call readers to the wrong symbol name when they
are chasing a cross-cdylib ABI failure.

**Why:** The diff updated `GILOnceCell` → `PyOnceLock` in all API-surface and static-declaration
sites but missed these two doc-comment occurrences inside `#[pymethods] impl Span`.

**Consequence:** Stale names don't cause runtime failure, but an on-call engineer debugging a
cross-cdylib TypeError who searches for `GILOnceCell` based on the doc comment will not find the
relevant initialisation site in `cross_cdylib.rs` (it's now called `PyOnceLock`). Low operational
impact because the two-step ABI check fails loudly with a `TypeError` message anyway, but the
diagnostic trail in source is misleading.

**Fix:** In `span.rs`:
- `:380`: change `"get_span_type`'s `GILOnceCell` init"` → `"get_span_type`'s `PyOnceLock`
  init"`.
- `:565`: change `"Uses a `GILOnceCell` cache"` → `"Uses a `PyOnceLock` cache"`.

---

## errhandling-2

**File:line:** `crates/fltk-cst-core/src/cross_cdylib.rs:284–286`

**Broken error path:** In `span_to_pyobject`, the slow-path `Some(st)` arm calls
`method.call1(py, (span.start(), span.end(), st))` and returns the result directly. The old code
appended `.map(|b| b.into_any())`. In pyo3 0.29, `Py<PyAny>::call1` returns
`PyResult<Py<PyAny>>` directly (not `PyResult<Bound<'_, PyAny>>`), so the `.map` is correctly
removed. This is **not a defect** — the removal is correct for 0.29.

However, for completeness: the `None` arm at `:292–294` does `span_type.call1(...).map(|b|
b.unbind())`. `span_type` is `Bound<'_, PyType>` so `call1` returns `PyResult<Bound<'_, PyAny>>`
and `.map(|b| b.unbind())` converts to `Py<PyAny>`. The asymmetry (one arm uses `Py<T>::call1`,
the other `Bound<T>::call1`) is correct but subtly different. No error is discarded; both arms
propagate failures via `?`.

**Verdict:** No finding. Noted for reviewer clarity.

---

## errhandling-3

**File:line:** `crates/fltk-cst-core/src/cross_cdylib.rs:97`

**Broken error path:** `let _ = FLTK_FOREIGN_SOURCE_TEXT_TYPE.get_or_init(py, || obj_type.clone().unbind());`

`PyOnceLock::get_or_init` is infallible (takes `impl FnOnce() -> T`, not `FnOnce() -> Result<T>`),
so the `let _ =` discards the returned `&T` reference, not a `Result`. This is correct: the cell
is populated as a side effect and the caller already holds `obj_type` for the subsequent
`cast_unchecked`. The `let _ =` comment in context ("no-op if already populated") makes intent
clear.

**Verdict:** No finding. Pattern is intentional and the type system confirms no `Result` is
discarded.

---

## errhandling-4

**File:line:** `crates/fltk-cst-core/src/registry.rs:122–124`

**Broken error path:** The race-recovery branch inside `get_or_insert_with` calls
`lookup(py, arc_addr)?.expect(...)`. The `expect` fires if `lookup` returns `Ok(None)` after
`register_if_absent` returned `false` (meaning the racing thread won and registered a handle, but
that handle was then GC'd before the retry lookup executes).

**Why:** The comment acknowledges the path as "unreachable in practice" under CPython's GIL, but
the `expect` would panic — not raise a `PyErr` — if the weak value dies between
`register_if_absent` and `lookup`. In a free-threaded Python build (PEP 703, 3.13+) or if a
custom allocator triggers GC between those two calls, this is reachable. The design assumes
single-threaded Python.

**Consequence:** A Python caller would get a Rust panic (converted by pyo3 to a
`PanicException`/`SystemExit` depending on the pyo3 version) rather than a structured `PyErr`.
On-call can diagnose the panic message, but the caller cannot catch it as a normal Python
exception. This is pre-existing behaviour, not introduced by this diff — but the diff did not
improve it either.

**Fix:** Replace `lookup(py, arc_addr)?.expect(...)` with a proper `PyErr` path:
```rust
lookup(py, arc_addr)?.ok_or_else(|| {
    pyo3::exceptions::PyRuntimeError::new_err(
        "registry invariant violated: entry evicted immediately after register_if_absent returned false"
    )
})?
```
This converts the invariant violation into a catchable Python `RuntimeError` instead of a panic.
The invariant comment may remain; the fix just determines who handles it.

---

No other findings. The mechanical `GILOnceCell` → `PyOnceLock`, `PyObject` → `Py<PyAny>`, and
`downcast*` → `cast*` renames are exhaustive across the diff. All `map_err` chains in
`check_abi_pair` preserve the original exception text via `e.to_string()` and wrap it in typed
`PyTypeError` messages — no context is lost. The `unwrap_or_else(|_| "<unknown type>")` fallbacks
in `py_any_type_name`/`py_type_obj_name` are justified (diagnostic helper, failure to read a
type name should not abort error construction). The `expect` in `src/lib.rs:28` for
`UNKNOWN_SPAN.set` is a correct crash-on-double-init invariant. The `expect` instances in
generated `cst_fegen.rs` (child accessor invariants: `count==1 but first==None`) are correct
invariant panics within already-guarded count-checked branches.
