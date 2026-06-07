Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Reviewed commit: 767315f

## quality-1

**File:** `fltk/fegen/gsm2tree_rs.py` — `_span_getter_setter`, `_children_getter`, `_generic_append`, `_generic_extend`, `_per_label_methods` (lines 501, 548, 573, 618, 664, 691, 709, 731, 753, 786)

**Issue:** The `FLTK_NATIVE_SPAN_TYPE` cache-initialization block (`get_or_try_init` + `py.import("fltk._native").and_then(…)`) is emitted **10 times verbatim** in the generated code — once per method that needs the span type (`span` getter, `children` getter, `append`, `extend`, `append_<label>`, `extend_<label>`, `children_<label>`, `child_<label>`, `maybe_<label>`). The preamble already introduces `extract_span` as a shared helper (one such helper is correct). There is no analogous shared helper to get the `span_type: &Bound<'_, PyType>` handle.

**Consequence:** Every future method that needs the span type must repeat this 5-line block; every bug in the initialization logic (wrong attribute name, error message, return type) must be fixed in all 10 copies. The generated `.rs` files grow proportionally with the number of labels: a grammar with 10 labels on one rule produces ~80 lines of redundant cache lookup just for that rule's per-label methods. This is a copy-paste propagation trap that gets worse as grammars grow.

**Fix:** Emit a file-level helper function in the preamble — analogous to `extract_span` — that encapsulates the cache lookup:

```rust
fn get_span_type(py: Python<'_>) -> PyResult<Bound<'_, PyType>> {
    FLTK_NATIVE_SPAN_TYPE.get_or_try_init(py, || {
        py.import("fltk._native")
            .and_then(|m| m.getattr("Span"))
            .and_then(|s| s.downcast_into::<PyType>().map_err(|e| e.into()))
            .map(|t: Bound<'_, PyType>| t.unbind())
    }).map(|t| t.bind(py).clone())
}
```

Then every callsite becomes a single `let span_type = get_span_type(py)?;`. Add this helper to `_preamble` in `gsm2tree_rs.py` (immediately after the `extract_span` emission), replace all 10 inline blocks in the per-method generators with the one-liner call, and regenerate.

---

## quality-2

**File:** `fltk/fegen/gsm2tree_rs.py` line 371; generated in `to_pyobject` for `Self::Span(s)`

**Issue:** When a terminal `Span` child is returned to Python via `to_pyobject`, the generated code reconstructs it **sourceless**:

```rust
Self::Span(s) => span_type.call1((s.start(), s.end())).map(|b| b.unbind()),
```

`span_type.call1((start, end))` invokes `Span::py_new(start, end)` — the sourceless constructor. The native `Span` stored in the child enum may carry a source (`source: Some(…)`), but that source is silently discarded at the Python boundary. Any Python-side consumer that calls `.text()` / `.text_or_raise()` on a child span returned through a label accessor (`child_<label>`, `children_<label>`, `maybe_<label>`, `children`) will get `None` / `ValueError` even if the underlying native span has source attached.

This is not gated on §2.5 being incomplete — it is a structural defect in the current `to_pyobject` implementation that will persist after §2.5 adds source-bearing child spans, because `to_pyobject` will still strip the source when converting back to Python.

**Consequence:** §2.5 and §2.6 plan to make child spans source-bearing for `fltk2gsm`'s `text_or_raise()` reads. Those reads go through exactly this boundary (`child_name()`, `child_value()` call the label accessor, which calls `to_pyobject`). If this is not fixed, §2.6 will not work correctly even after §2.5 attaches source to the native child spans — the source will be stripped each time the child crosses the Python boundary.

**Fix:** Expose a `with_source`-equivalent on the Python `Span` type (already exists: `Span::with_source` is a `#[classmethod]`). The generated `to_pyobject` for `Self::Span(s)` must call the `with_source` classmethod when source is present, and fall back to the sourceless constructor only for sourceless spans. In generated Rust this requires accessing `s.source`, which is `pub(crate)` in `fltk-cst-core/src/span.rs`. The fix therefore also requires making the source accessible from outside the crate — either a `pub fn source(&self) -> Option<&SourceText>` Rust accessor on `Span` in `fltk-cst-core` (returning a `SourceText` wrapper or a reference), or exposing `SourceInner` at a level that allows `to_pyobject` to reconstruct a `SourceText` for the `with_source` call. The cleanest form: add `pub fn has_source(&self) -> bool` (already exists as a `#[pymethods]` item; expose it as a plain `pub fn` in `impl Span` too) and `pub fn source_text(&self) -> Option<SourceText>` (returns `Some(SourceText { inner: arc.clone() })` when present) to `fltk-cst-core`'s `Span`. Then `to_pyobject` becomes:

```rust
Self::Span(s) => {
    if let Some(src) = s.source_text() {
        let src_py = Py::new(py, src)?.into_any();
        span_type.call_method1("with_source", (s.start(), s.end(), src_py))
            .map(|b| b.unbind())
    } else {
        span_type.call1((s.start(), s.end())).map(|b| b.unbind())
    }
}
```

This is needed before §2.6 can work.

---

## quality-3

**File:** `fltk/fegen/gsm2tree.py` lines 252–258 (`extend_children` on the Python CST class); `fltk/fegen/gsm2parser.py` lines 494–502, 712–713 (emitting `extend_children` calls)

**Issue:** `extend_children` on the Python-backend CST node (`gsm2tree.py:252`) is typed as `self, other: '{class_name}'` but its body does `self.children.extend(other.children)` — copying `(label, child)` tuples. This is correct, but the method is **not declared in the protocol** (`fltk_cst_protocol.py`). The parser generator now emits calls to `result.extend_children(item.result)` (`gsm2parser.py`) on the result node. Because `extend_children` is absent from the protocol, `fltk_cst_protocol.py`-based type-checking of generated parsers will produce a false-positive: the protocol says nothing about `extend_children`, so a type-checker using the protocol cannot verify the call is valid, and a future refactor that removes the method from the concrete class but forgets the protocol won't get a type error.

**Consequence:** The protocol is the public cross-backend contract. A method used by the generator on every node must be on the protocol. Omitting it means the protocol does not describe the full API surface that generated parsers rely on — an abstraction-boundary breach. Every future grammar regeneration emits `extend_children` calls whose correctness cannot be verified by static analysis against the protocol.

**Fix:** Add `extend_children` to the protocol's node interface in `gsm2tree.py` (the `_protocol_class` / protocol emit path, line ~543 area) so that `fltk_cst_protocol.py` re-generation includes the method. The signature is `def extend_children(self, other: 'Self') -> None`. The protocol is already parameterized per-class (it generates `{class_name}Protocol` with typed children); `extend_children` takes the same concrete type, so `other: '{class_name}'` in the protocol. Also update the Rust generator to emit `extend_children` in the `#[pymethods]` block with matching signature (currently done — this is about the Python protocol only).
