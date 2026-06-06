# Error-handling review — clean-protocol-consumer-api

Base: 1e78b73  HEAD: bc42280

---

## errhandling-1

**File:** `fltk/fegen/fltk2gsm.py:57–58, 65, 69–70, 73`

**Path:** `assert item_label == cst.Items.Label.ITEM` / `assert item.kind == cst.Item.kind` / `assert sep_label == cst.Items.Label.NO_WS` / `assert len(gsm_items) == len(sep_after)`

**Why:** All five assertions are now bare `assert` statements (no `# noqa: S101`) with `AssertionError` as the only signal. `AssertionError` carries no context: which label was seen, what the actual value was, what the children list looked like, or which grammar rule triggered the walk. The old code used `typing.cast` (which is a no-op at runtime and also silent), but the replacement asserts are equally silent — they just crash instead of miscast. When a malformed or unexpected CST tree reaches `visit_items`, the on-call engineer sees `AssertionError` with no operands and no stack context beyond the frame.

**Consequence:** Any mismatch between the expected interleaved (ITEM, separator) structure and the actual children list produces an `AssertionError` with no diagnostic payload. Debugging requires reproducing the input, adding prints, and re-running. For a production grammar-compilation pipeline this is silent failure mode: the error message is `AssertionError` with no indication of which label was present vs. expected, which child index, or which rule was being visited.

**What must change:** Add the actual vs. expected values to each assertion message. For example:
```python
assert item_label == cst.Items.Label.ITEM, f"expected ITEM label, got {item_label!r} at child index {start_idx + 2*i}"
assert item.kind == cst.Item.kind, f"expected Item node, got kind={item.kind!r}"
assert sep_label == cst.Items.Label.NO_WS, f"expected NO_WS separator, got {sep_label!r}"
assert len(gsm_items) == len(sep_after), f"item/sep count mismatch: {len(gsm_items)} items, {len(sep_after)} seps"
```
These are invariant-violation assertions (malformed CST = programmer/generator bug), so crashing is correct; the messages just need enough context to diagnose.

---

## errhandling-2

**File:** `src/span.rs:261–271` (`Span::kind` getter)

**Path:** `get_or_try_init` → `py.import("fltk.fegen.pyrt.terminalsrc")?.getattr("SpanKind")?.getattr("SPAN")?` → `PyResult` propagated to caller.

**Why:** If the import or attribute lookup fails (e.g., `terminalsrc` module not on `sys.path` in an unusual deployment, or if the module is partially initialized during interpreter startup), the `?` operators propagate a `PyErr` upward. The caller (Python `match child.kind:`) receives a `PyException` with a message like `ModuleNotFoundError: No module named 'fltk.fegen.pyrt.terminalsrc'` or `AttributeError: module 'fltk.fegen.pyrt.terminalsrc' has no attribute 'SpanKind'`. These are propagated correctly as Python exceptions — that part is fine. However, **the `GILOnceCell` is not populated on failure**: `get_or_try_init` only stores the value if the init closure succeeds. A transient error (unlikely here, but possible during import ordering at startup) would be retried on every subsequent `.kind` access. More critically, if the failure is permanent (e.g., deployment without the Python package), every `Span.kind` access raises, and the error message contains no hint that the acyclicity invariant or the deployment is the root cause — the traceback will show an opaque Python import error from a Rust getter.

**Consequence:** A broken deployment (missing Python package for `terminalsrc`) causes every `Span.kind` call to throw, including in `match child.kind:` dispatch blocks, making the entire CST traversal surface unusable. The error message is a raw `ModuleNotFoundError` from inside a `#[getter]` with no added context. An on-call engineer seeing `AttributeError` or `ModuleNotFoundError` raised from inside `child.kind` access has no immediate signal that the issue is the Rust↔Python import bridge for `SpanKind`.

**What must change:** Add a context-wrapping error message on init failure:
```rust
.get_or_try_init(py, || -> PyResult<PyObject> {
    py.import("fltk.fegen.pyrt.terminalsrc")
        .and_then(|m| m.getattr("SpanKind"))
        .and_then(|sk| sk.getattr("SPAN"))
        .map(|obj| obj.unbind())
        .map_err(|e| {
            PyValueError::new_err(format!(
                "Span.kind: failed to load SpanKind.SPAN from fltk.fegen.pyrt.terminalsrc: {e}"
            ))
        })
})
```
This preserves the `PyResult` propagation (correct for the Python boundary) while giving on-call a root-cause string. The retry-on-transient-error behavior is acceptable here since the import is idempotent.

---

## errhandling-3

**File:** `fltk/fegen/fltk_cst_protocol.py` (generated) and `fltk/fegen/gsm2tree.py:551–569` (`_emit_protocol_label_member_class`)

**Path:** `_ProtocolLabelMember.__eq__` for the case where `other` is a non-`_ProtocolLabelMember` foreign object that does NOT have `_fltk_canonical_name`.

**Why:** When `cn = getattr(other, "_fltk_canonical_name", None)` returns `None`, the method returns `NotImplemented`. This is the correct bridge contract and matches the generated `NodeKind.__eq__` shape. However: if `other` is any object that accidentally has a `_fltk_canonical_name` attribute set to the correct string (e.g., any object carrying that attribute for unrelated reasons), `__eq__` will return `True`. This is a pre-existing design choice (duck-typed equality) and intentional per the design doc — **not a new bug from this diff**. Calling it out because the new `_ProtocolLabelMember` class is freshly introduced here: unlike `NodeKind` (an `enum.Enum` with same-type fast-path), `_ProtocolLabelMember`'s same-type fast-path checks `type(other) is type(self)`, which means two distinct `_ProtocolLabelMember` instances with the same canonical string (e.g., from two independent protocol module imports) correctly compare equal. No silent failure mode introduced here beyond the pre-existing duck-typing contract.

**Verdict:** Not a new finding; design-intentional. No change required.

---

No other findings. The `unwrap()` at `span.rs:172` is pre-existing (present in base commit, guarded by the prior `source.is_none()` return), not introduced by this diff.
