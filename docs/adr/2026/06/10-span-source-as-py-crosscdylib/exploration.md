# Exploration: span-source-as-py-crosscdylib

Concise. Precise. Token-dense. No fluff. Audience: smart LLM/human implementing the fix.

---

## Claim 1: "generated accessors call `source_full_text_str()` + `get_source_text_type(py)?.call1(full_text)`"

**VERIFIED. ACCURATE.**

The double-copy pattern is present verbatim in every span-returning site in every generated file.
Confirmed execution path (from `cst_fegen.rs` span getter, lines 316–332, which is identical in
`cst_generated.rs` and `tests/rust_cst_fixture/src/cst.rs`):

```rust
fn span(&self, py: Python<'_>) -> PyResult<PyObject> {
    let span_cls = get_span_type(py)?;
    if let Some(full_text) = self.span.source_full_text_str() {   // copy #1
        let st_type = get_source_text_type(py)?;
        let py_src = st_type.call1((full_text.as_str(),))?;       // copy #2
        span_cls.call_method1("with_source", (self.span.start(), self.span.end(), py_src))
            .map(|b| b.unbind())
    } else { ... }
}
```

The `to_pyobject` Span-arm on every child-enum (e.g. `AlternativesChild::to_pyobject`,
`cst_fegen.rs:1442–1452`) uses the identical pattern.

**Copy #1** — `source_full_text_str()` (`crates/fltk-cst-core/src/span.rs:168–170`):
```rust
pub fn source_full_text_str(&self) -> Option<String> {
    self.source.as_ref().map(|arc| arc.text.clone())   // heap-allocates a new String from the Arc's String
}
```
This copies the entire source string (the entire parsed input, not the span slice) from the
`Arc<SourceInner>` into a new heap `String`. Cost: O(source length).

**Copy #2** — `get_source_text_type(py)?.call1((full_text.as_str(),))` calls through Python into
`SourceText::new` (`span.rs:54–56`), which calls `SourceText::from_str` (`span.rs:39–45`):
```rust
pub fn from_str(text: &str) -> Self {
    SourceText { inner: Arc::new(SourceInner { text: text.to_owned() }) }
}
```
`text.to_owned()` copies the entire source string again into a brand-new `Arc<SourceInner>`. Cost:
O(source length).

**Total per accessor call: two full-source string copies, O(source length) each.** The O(source
length) per node read claim in the TODO is accurate.

### Occurrence count

| File | `source_full_text_str` call sites |
|---|---|
| `src/cst_fegen.rs` | 23 |
| `src/cst_generated.rs` | 6 |
| `tests/rust_cst_fixture/src/cst.rs` | 10 |
| `tests/rust_cst_fegen/src/cst.rs` | 0 (uses `include!("../../../src/cst_fegen.rs")`) |

Generator location: `fltk/fegen/gsm2tree_rs.py`. The span getter is emitted by `_span_getter_setter`
(lines 703–731); the `to_pyobject` Span-arm is emitted by `_child_enum_block` (lines 529–545).
Both emit `source_full_text_str()` + `get_source_text_type(py)?.call1(full_text.as_str())`.

The preamble that emits `get_source_text_type` / `FLTK_NATIVE_SOURCE_TEXT_TYPE` is in
`gsm2tree_rs.py:_preamble` (lines 308–328); the same block is emitted byte-for-byte into every
generated file (`TODO(preamble-helpers-into-cst-core)` tracks the duplication separately).

---

## Claim 2: "`source_as_py` clones only the Arc (O(1)) and is the correct API"

**VERIFIED. ACCURATE.**

`crates/fltk-cst-core/src/span.rs:151–161`:
```rust
pub fn source_as_py(&self, py: Python<'_>) -> PyResult<Option<Py<SourceText>>> {
    match &self.source {
        Some(arc) => Ok(Some(Py::new(py, SourceText { inner: arc.clone() })?)),
        None => Ok(None),
    }
}
```
`arc.clone()` increments the `Arc` reference count only — no heap allocation, no string copy. O(1).
The resulting `Py<SourceText>` wraps a `SourceText` whose `inner` is the *same* `Arc<SourceInner>`
as the span's, preserving `Arc` deduplication across all spans from the same parse.

---

## Claim 3: "`source_as_py` cannot be used cross-cdylib because the locally-registered SourceText type object differs from `fltk._native.SourceText`"

**VERIFIED. ACCURATE, WITH PRECISE MECHANISM IDENTIFIED.**

The problem is at the Python boundary of `fltk._native.Span.with_source`:
```rust
// crates/fltk-cst-core/src/span.rs:204–206
fn with_source(_cls: &Bound<'_, PyType>, start: i64, end: i64, source: &SourceText) -> Self {
    Span::new_with_source(start, end, source)
}
```
The `source: &SourceText` parameter is extracted by pyo3 using pyo3's type registry. pyo3's `extract`
for a `#[pyclass]` type only succeeds when the Python object's `PyTypeObject` pointer matches the
one registered in the *current* cdylib — i.e., `fltk._native`'s registered `SourceText` type.

`source_as_py` (`span.rs:151`) creates a `Py<SourceText>` registered with the **calling** cdylib's
type system (the out-of-tree consumer crate, not `fltk._native`). When that `Py<SourceText>` is
passed to `fltk._native.Span.with_source(...)` via Python, pyo3 in `fltk._native` tries to extract
it as `&SourceText` against its own registry — the type-object pointers don't match (different
registration tables), so extraction fails with `TypeError`.

This is the exact same cross-cdylib boundary problem that `extract_span` / `downcast_unchecked`
solves for `Span`: `cst_fegen.rs:16–42` and `gsm2tree_rs.py:268–294`.

---

## Claim 4: "Fix: add an `extract_source_text` helper to the generated preamble (analogous to `extract_span`, using the shared-rlib invariant and `downcast_unchecked`)"

**FEASIBILITY: VERIFIED. MECHANISM: ACCURATE WITH IMPORTANT CLARIFICATION ON DIRECTION.**

### How `extract_span` works

`extract_span` (`cst_fegen.rs:16–42`, emitted by `gsm2tree_rs.py:_preamble:268–294`):
1. Fast path: `obj.extract::<Span>()` — succeeds when `obj`'s type-object matches locally registered `Span`.
2. Slow path: `get_span_type(py)?` fetches `fltk._native.Span` type object (cached `GILOnceCell`).
   `obj.is_instance(&native_span_type)?` — succeeds because Python `isinstance` checks by `PyTypeObject`
   pointer identity, and both cdylibs registered the *same* `Span` type from the *same* `fltk-cst-core`
   rlib (same object in memory). `unsafe { obj.downcast_unchecked::<Span>() }` then reinterprets the
   `PyCell<Span>` — valid because both cdylibs link the same rlib Span type layout.

The shared-rlib invariant (`cst_fegen.rs:27–34`): both this cdylib and `fltk._native` link the
same `fltk-cst-core` rlib, so `Span` layout is identical. `downcast_unchecked` is sound only under
this invariant; version skew causes UB.

### What `extract_source_text` would do

Direction: the fix does **not** need to call `source_as_py` and then extract the result. The
fix needs to **extract** a native `SourceText` value from a `Py<SourceText>` that was registered
in a *different* cdylib, then construct a locally-registered `Py<SourceText>` (or use the native
`SourceText` directly).

But the actual data flow for the accessor fix is simpler than the TODO implies. The span getter
does not *receive* a cross-cdylib `SourceText` — it *sends* one. The fix is:

1. Call `self.span.source_as_py(py)?` — this creates a locally-registered `Py<SourceText>` wrapping
   the same `Arc` (O(1)).
2. The problem: pass this `Py<SourceText>` to `fltk._native.Span.with_source(...)`, which will fail
   pyo3 type extraction as described above.

So the fix shape is: **do not call `fltk._native.Span.with_source` via Python at all**. Instead,
use `downcast_unchecked` to extract the locally-built `Py<SourceText>` (or `fltk._native`'s
`SourceText`) and call `fltk._native.Span.with_source` at the Rust level — or, more directly,
build the native `Span` directly and wrap it without going through `with_source` at all.

Concretely, the symmetry with `extract_span` applies to *incoming* objects (things passed *in*
from Python). The outgoing direction (building a Python `Span` to return) could bypass the
`with_source` Python call entirely by constructing the `Span` directly in Rust and then creating
a `Py<Span>` via `Py::new(py, span_value)?` — but that `Py<Span>` will again be registered with
the local cdylib's type, not `fltk._native`'s.

**The actual blocker**: generated code must return `fltk._native.Span` (not a locally-registered
`Span`) so downstream Python consumers always see the canonical type. See `cst_fegen.rs:317–319`
comment: "Return a `fltk._native.Span` so consumers always get the canonical type regardless of
which cdylib the node is defined in."

**The `extract_source_text` approach**: to call `fltk._native.Span.with_source` efficiently, the
generated code could:
1. Call `self.span.source_as_py(py)?` to get a locally-registered `Py<SourceText>` (O(1)).
2. An `extract_source_text_for_native` helper then: try local extract (succeeds for fltk._native
   generated code); if fails, use `isinstance` against `fltk._native.SourceText` type object and
   `downcast_unchecked::<SourceText>()` (same shared-rlib invariant as `extract_span`) to extract
   a `&SourceText` or clone it. Then reconstruct a `Py<SourceText>` registered with `fltk._native`
   by calling through `get_source_text_type(py)?.call0()` — but this is still a Python call.

**Simpler and correct alternative**: since both cdylibs share the same `fltk-cst-core` rlib and
thus the same `Span` type layout, the generated code can:
1. Get a native `Span` clone (already done: the native `Span` field `self.span`).
2. Wrap it as a Python `Span` registered with `fltk._native` by calling through the cached type:
   `get_span_type(py)?` gives the `fltk._native.Span` `PyType`; call `with_source` on it via
   Python with a `SourceText` argument.
3. The `SourceText` argument must be `fltk._native.SourceText` or accepted by it.

**The key insight**: `with_source` on the Python side calls `Span::new_with_source(start, end, source)`
(`span.rs:205–206`), which extracts `source: &SourceText`. If the `SourceText` object was
produced by `source_as_py` from a different cdylib, extraction fails.

**What actually works cross-cdylib without string copying:**

Add an `unsafe extract_source_text` analog to `extract_span` in the preamble. Just as `extract_span`
uses `downcast_unchecked::<Span>()` on an `fltk._native.Span` PyObject, `extract_source_text` would
use `downcast_unchecked::<SourceText>()` on an `fltk._native.SourceText` PyObject. The `SourceText`
layout is identically defined in `fltk-cst-core` (same struct, same `Arc<SourceInner>` field), so
`downcast_unchecked` is safe under the same shared-rlib invariant.

The modified accessor flow would be:
1. `let py_st = self.span.source_as_py(py)?` — locally-registered `Py<SourceText>`, O(1).
2. Pass `py_st` to `get_span_type(py)?.call_method1("with_source", (start, end, py_st))`.
3. pyo3 in `fltk._native` extracts `source: &SourceText` — this fails because `py_st` is from
   another cdylib.

So the helper is needed on the **receiving** side, which is inside `fltk._native`'s `with_source`
— but that code is not generated. The fix must be at the **call site** in generated code.

**Correct fix shape without modifying `fltk._native`**:

In generated code: call `source_as_py` (O(1) Arc clone) to get a locally-registered `Py<SourceText>`.
Then use a `create_native_span_with_source(py, &Span) -> PyResult<PyObject>` helper in the preamble
that:
1. Fetches the `fltk._native.Span` type object (cached).
2. Fetches the `fltk._native.SourceText` type object (cached).
3. Uses `downcast_unchecked::<SourceText>()` on the `Py<SourceText>` returned by `source_as_py` to
   get a `&SourceText` — valid because both cdylibs share the same `fltk-cst-core` `SourceText`
   layout.
4. Passes the `&SourceText` reference to `Span::new_with_source(start, end, source)` directly at
   the Rust level... except `new_with_source` is a Rust function on the same `fltk-cst-core` rlib,
   so this **works** — you don't need Python at all.
5. Wrap the resulting `Span` via `Py::new(py, span_value)?`... but this is again locally-registered.

**The fundamental constraint**: to return a `fltk._native.Span`, you *must* either:
(a) Call through Python via `get_span_type(py)?.call_method1("with_source", ...)`, or
(b) Use `downcast_unchecked` to cast a locally-created `Py<Span>` and claim it is the `fltk._native`
    registered type — which is NOT sound, because `Py::new(py, span_value)` registers with the
    current cdylib's type, not `fltk._native`'s. The `PyObject` pointer points to the current
    cdylib's `PyTypeObject`, not `fltk._native`'s.

Path (a) is the only sound path. The open question is whether the `SourceText` argument to
`with_source` can be provided without copying. The answer: YES, if the preamble adds
`extract_source_text` that uses `downcast_unchecked::<SourceText>()` on a locally-created
`Py<SourceText>` bound to the GIL, extracts a `&SourceText`, and passes it through `call_method1`
via a pyo3 `IntoPyObject` conversion that avoids string copying.

**But**: pyo3's `call_method1` takes `impl IntoPyObject` args. A `&SourceText` from a
`downcast_unchecked` is a Rust reference; you can't pass it directly to `call_method1` in the
`fltk._native` registry context. The `with_source` method takes `source: &SourceText` at the Rust
level but is called from Python where pyo3 extracts it from the `PyObject` argument.

The sound resolution: generate code that uses `source_as_py` (O(1)), then constructs a span
**without going through Python `with_source`** by using the fact that both cdylibs share the
`fltk-cst-core` rlib. Specifically:

```rust
// In the preamble helper (sketch):
fn build_native_span(py: Python<'_>, span: &Span) -> PyResult<PyObject> {
    let span_type = get_span_type(py)?;  // fltk._native.Span type
    match span.source_as_py(py)? {
        None => span_type.call1((span.start(), span.end())).map(|b| b.unbind()),
        Some(local_st) => {
            // local_st is Py<SourceText> registered with THIS cdylib.
            // downcast_unchecked is sound: same fltk-cst-core rlib layout.
            let bound_st = local_st.bind(py);
            let st_ref: &SourceText = unsafe { &*bound_st.downcast_unchecked::<SourceText>().as_ptr() };
            // Now call fltk._native.Span.with_source via Python, passing local_st.
            // fltk._native.Span.with_source extracts source: &SourceText from the Python arg.
            // If it uses pyo3 extraction, it will fail for the same cross-cdylib reason.
            // *** This is still stuck. ***
        }
    }
}
```

The root issue: `fltk._native.Span.with_source` is a `#[pymethods]` function that pyo3 dispatches
through type-checked extraction. There is no way to call it with a non-`fltk._native`-registered
`SourceText` without either (a) string-copying or (b) making `fltk._native.Span.with_source`
accept cross-cdylib `SourceText` objects (e.g. by adding an `extract_source_text` to `fltk._native`
itself, or changing the `with_source` signature to accept `&PyAny` + use `downcast_unchecked`).

**The blocker the TODO did not fully state**: to avoid the string copy, `fltk._native.Span.with_source`
must be changed to accept a cross-cdylib `SourceText` using `downcast_unchecked`, OR a new
Python-callable entry point (e.g. `fltk._native.Span.with_source_arc_unsafe`) is needed on the
`fltk._native` side.

Alternatively: since generated code always returns the `Arc`-shared native `Span` to Python as a
`fltk._native.Span` by going through `get_span_type(py)?.call_method1(...)`, a simpler fix is to
add a *new* Python classmethod to `fltk._native.Span`, e.g. `_with_native_source_text`, that takes
`&PyAny` and uses `downcast_unchecked::<SourceText>()` internally. Generated code calls this instead
of `with_source`. No string copy; same shared-rlib invariant as `extract_span`.

---

## Summary of Factual Findings

| Claim in TODO | Verdict | Notes |
|---|---|---|
| "copies full source string twice per accessor call" | **True** | Confirmed: `source_full_text_str` = `arc.text.clone()` (copy 1); `SourceText::new` = `text.to_owned()` (copy 2) |
| "O(source length) per node read" | **True** | Each copy is O(source string length), not O(span length) |
| "`source_as_py` clones only the Arc (O(1))" | **True** | `arc.clone()` is a refcount increment |
| "cannot be used in generated code for out-of-tree consumer crates" | **True** | pyo3 type-extraction of `SourceText` in `fltk._native.Span.with_source` fails for non-`fltk._native`-registered `SourceText` objects |
| "`extract_source_text` analogous to `extract_span`, using `downcast_unchecked`" | **Partially true** | The incoming direction (extracting a `SourceText` from Python) works this way; the outgoing direction (producing a `fltk._native.Span` that `with_source` will accept a cross-cdylib `SourceText`) requires a NEW entry point in `fltk._native` (`span.rs`) — or a change to `fltk._native.Span.with_source` — not just a generated-preamble change alone |
| Fix requires changes to `gsm2tree_rs.py` preamble and span-getter/to_pyobject | **True** | But also requires a change to `crates/fltk-cst-core/src/span.rs` (or `src/lib.rs`) to add a cross-cdylib-safe `Span` constructor callable from generated code |

## Additional Unmentioned Fact: Parse Path is Clean

`notes-deep-efficiency.md` correctly notes (and code confirms): the parse path constructs
`SourceText` once and shares it. `fltk_parser.py:16` (and `gsm2parser.py`-emitted
`_source_text_init`) build one `SourceText` object; every `Span.with_source(start, end,
source_text)` call reuses it. The double-copy regression is exclusively at the **getter/read**
boundary, not at parse/write time.

## Files and Locations

- `crates/fltk-cst-core/src/span.rs:151–161` — `source_as_py` (O(1) Arc clone)
- `crates/fltk-cst-core/src/span.rs:168–170` — `source_full_text_str` (O(source) copy)
- `crates/fltk-cst-core/src/span.rs:204–206` — `with_source` #pymethods (type-checked extraction)
- `fltk/fegen/gsm2tree_rs.py:703–731` — `_span_getter_setter` emitter (double-copy source)
- `fltk/fegen/gsm2tree_rs.py:529–545` — `_child_enum_block` to_pyobject Span arm (double-copy)
- `fltk/fegen/gsm2tree_rs.py:308–328` — `_preamble` `get_source_text_type` / `FLTK_NATIVE_SOURCE_TEXT_TYPE`
- `src/cst_fegen.rs:56–75` — emitted preamble helpers (`FLTK_NATIVE_SOURCE_TEXT_TYPE`, `get_source_text_type`)
- `src/cst_fegen.rs:316–332` — span getter (double-copy, 23 total `source_full_text_str` sites in file)
- `src/cst_fegen.rs:1442–1452` — `to_pyobject` Span arm (double-copy)
- `src/cst_generated.rs` — 6 `source_full_text_str` sites (same pattern)
- `tests/rust_cst_fixture/src/cst.rs` — 10 `source_full_text_str` sites (same pattern)
- `tests/rust_cst_fegen/src/cst.rs` — 1 line: `include!("../../../src/cst_fegen.rs")` (same sites via include)
