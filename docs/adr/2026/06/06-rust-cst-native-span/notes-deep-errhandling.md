errhandling-1: fltk/fegen/fltk2gsm.py:35
Silent wrong-text extraction when Rust-backend span.text() returns None.

`_span_text` calls `span.text()` and falls back to `self.terminals[span.start:span.end]`
when `None` is returned. The docstring asserts the fallback "is needed for bootstrap
compatibility" and will be unreachable after regen. But `span.text()` on a
`fltk._native.Span` returns `None` for any span whose byte offsets do not land on
UTF-8 code-point boundaries (or exceed source length). If that case is ever reached,
the fallback silently indexes the Python str by code-point rather than by byte, producing
wrong identifier/literal/regex text with no error, no log, and no caller diagnostic.
The `gsm.Identifier`, `gsm.Literal`, and `gsm.Regex` objects are then built from
garbage text; downstream parse failures carry no indication that source-text extraction
was the root cause.

Consequence: on-call sees a downstream semantic error or incorrect grammar identity
with no observable link to the malformed span. Reachable in practice only for
non-ASCII grammar source; for ASCII-only grammars byte == code-point, so the fallback
produces correct output by coincidence.

Fix: after calling `span.text()`, if the result is `None` on what should be a
source-bearing span (i.e., `hasattr(span, "has_source") and span.has_source()`),
raise a descriptive error (e.g., `ValueError(f"span.text() returned None for
source-bearing span {span!r}; byte offsets may be non-UTF-8-aligned")`) rather than
silently falling back. Alternatively, add an assertion so the fallback is gated strictly
to Python-backend sourceless spans and panics loudly for Rust-backend spans.

---

errhandling-2: fltk/unparse/pyrt.py:39-42 (extract_span_text)
Same pattern as errhandling-1. When `span.text()` is `None` for a source-bearing
`fltk._native.Span`, the fallback `terminals[span.start:span.end]` uses Python
character indexing on byte offsets. No log, no error, silent wrong text in formatter
output. Fix is identical: guard the fallback on "sourceless Python-backend span only",
raise or log for any other None-text case.

---

errhandling-3: crates/fltk-cst-core/src/span.rs:176-179 (source_full_text_str)
All span getters (`.span()` Python getter, every `to_pyobject` `Self::Span(s)` arm in
every child enum) call `s.source_full_text_str()` and then immediately allocate a new
`String` from the full source text. When source is present, this clones O(N) bytes on
every single accessor call. This is not an error-handling finding per se, but:

The observable error-path consequence is that if `source_full_text_str()` returns
`None` (span is sourceless), the code silently falls through to a sourceless
`span_type.call1((s.start(), s.end()))` with no log that source preservation was
attempted and failed. A caller inspecting the returned span cannot distinguish "was
always sourceless" from "had source but was dropped due to unexpected None". Structured
logging (debug level is sufficient) at the "else" branch — "span child converted
without source (was sourceless)" — would make the loss observable in on-call traces.

---

errhandling-4: src/cst_fegen.rs and tests/rust_cst_fixture/src/cst.rs — all child
accessor `expect` calls.

Pattern (representative):
```
Ok(found.expect("invariant: Grammar.child_rule: count==1 but found==None; logic error"))
```

`expect` here panics (i.e., crashes the Python interpreter / raises `PanicException`
propagated to Python). This is correct for a genuine internal logic error: if
`count == 1` but `found` is `None`, something is seriously wrong with the iterator
bookkeeping and continuing is unsafe.

The distinction is clear and correct: the count-check above it (`if count != 1 { return
Err(PyValueError) }`) handles the expected bad-input case (wrong number of children)
with a proper Python exception. The `expect` below it fires only if the loop invariant
breaks — a genuine impossible state worth panicking on.

No change required. Confirmed correct.

---

errhandling-5: src/cst_fegen.rs:29-37 (extract_span slow path)

```rust
let span = unsafe { obj.downcast_unchecked::<Span>() };
return Ok(span.borrow().clone());
```

Preceded by `if obj.is_instance(&native_span_type)?`. If `is_instance` returns true
but the underlying object is not actually a `Span` (e.g., a third-party object
happened to be an instance of the Python type), `downcast_unchecked` is UB / memory
corruption. The comment asserts "Both this cdylib and fltk._native link the same
fltk-cst-core rlib, so the Span type layout is identical."

This is the correct approach for the cross-cdylib scenario: the isinstance check IS
the type proof given the shared rlib constraint. However, the safety proof depends on
a deploy invariant (single fltk-cst-core rlib), not on anything the compiler can verify.
If a future user links two different fltk-cst-core versions, this silently corrupts.

The `SAFETY` comment is present and accurate. No immediate action required, but the
comment should mention the consequence of violating the single-rlib invariant:
memory corruption (not merely a wrong result), to make the severity of that deploy
invariant clear.

---

errhandling-6: fltk/fegen/gsm2tree_rs.py:302-307 / generated Rust code (get_source_text_type)

`get_source_text_type` uses `GILOnceCell::get_or_try_init`. If `fltk._native` fails to
import (e.g., during testing with the pure-Python backend), every call to the span
getter or `to_pyobject` on a source-bearing span will retry the failed import and return
a `PyErr` (propagated correctly to Python). This is correct behavior — errors propagate
rather than silently dropping source.

However, the error message from `py.import("fltk._native")` is just the raw Python
`ImportError` or `ModuleNotFoundError` with no added context: callers see e.g.
"No module named 'fltk._native'" with no hint that it originated from a span-source
preservation attempt in a CST node accessor.

Fix: wrap the error in a context message, e.g.:
```rust
py.import("fltk._native")
    .map_err(|e| PyRuntimeError::new_err(format!(
        "span source preservation requires fltk._native (SourceText): {e}"
    )))
```
This is low-severity but aids on-call diagnosis.
