# TODO Adversarial Validation: rust-cst-accessor-clone-efficiency

**Subject:** TODO claim that Python-facing CST accessors clone the full children `Vec` then filter outside the lock guard, and that filter-inside-guard is a mechanical fix.

**Source file:** `fltk/fegen/gsm2tree_rs.py`

---

## 1. Does the full-Vec-clone-then-filter-outside-guard pattern actually exist?

**Yes, exactly as claimed.** Three pymethod generators exhibit the pattern:

### `_generic_child` (lines 1011–1036)

```rust
let snapshot: Vec<_> = {
    let guard = self.inner.read();
    guard.children.clone()      // ← clones entire Vec under guard
};                              // ← guard drops here
let n = snapshot.len();
if n != 1 { ... }
let (label, child) = &snapshot[0];
```

The TODO comment is verbatim in the emitted template at line 1014–1016:
> `// TODO(rust-cst-accessor-clone-efficiency): clones the full children Vec`
> `// before checking len. Could check len under the read guard and only clone`
> `// the single needed entry, avoiding O(total-children) allocation on the error path.`

### `_per_label_methods` — `children_<label>` (lines 1387–1404)

```rust
let snapshot: Vec<_> = {
    let guard = self.inner.read();
    guard.children.clone()      // ← clones entire Vec
};
// guard dropped; filtering happens on snapshot
for (lbl, child) in &snapshot {
    if *lbl == Some(LabelEnum::Variant) { ... }
}
```

TODO comment at line 1388–1390.

### `_per_label_methods` — `child_<label>` (lines 1408–1434)

Same snapshot pattern; TODO at line 1411:
> `// TODO(rust-cst-accessor-clone-efficiency): see children_{label} above.`

### `_per_label_methods` — `maybe_<label>` (lines 1437–1465)

Same snapshot pattern; TODO at line 1441:
> `// TODO(rust-cst-accessor-clone-efficiency): see children_{label} above.`

---

## 2. What is cloned per element?

Each element is `(Option<LabelEnum>, ChildEnum)`. From `_child_enum_block` (lines 488–604), `ChildEnum` variants are either `Span(Span)` or `NodeClass(Shared<NodeClass>)`. `Clone` on `Shared<T>` is a shallow Arc reference-count increment (confirmed by line 503–504 doc comment: "Clone is shallow (increments the reference count, does not copy the node)"). So per-child clone cost = one atomic refcount increment (for node children) or a Span copy (a simple struct, no heap).

The claim of "O(total-children) Arc/Span/label clones per call" is factually accurate.

---

## 3. Is the fix "mechanical"?

**Partially.** The claim varies by accessor:

### `_generic_child` (the `child()` pymethod)

The TODO comment itself says "check len under the read guard and only clone the single needed entry." This is straightforward: `children.len()` is a `usize` read under the guard, and indexing `children[0].clone()` clones exactly one element. No Python work is done inside the guard because `to_pyobject` is only called after the single-entry clone. Lock-hold duration shrinks; no Python calls happen under the lock (already the constraint the existing `_span_getter_setter` at lines 837–840 cites explicitly). This sub-case is truly mechanical.

### `children_<label>`, `child_<label>`, `maybe_<label>` (the per-label pymethods)

Filtering inside the guard means: hold the read lock while calling `child.to_pyobject(py)` on matching children. `to_pyobject` calls `span_to_pyobject(py, s)` or `registry::get_or_insert_with(py, addr, ...)` (lines 543–557). Both perform Python work (Py::new, Python method calls). Holding an `RwLock` read guard while running Python is the exact pattern the existing `_span_getter_setter` code (line 839) explicitly warns against:

> `// Snapshot the span under the read lock, then drop the guard before`
> `// calling span_to_pyobject — which performs Python work (Py::new or`
> `// Python method calls) that must not happen while a node lock is held.`

So for per-label pymethods the naive "filter inside guard" fix is **not** mechanical — it would call Python work under the lock, violating the established constraint.

The safe variant for per-label methods remains: clone only the matching entries (label comparison is cheap, done under the guard), drop the guard, then call `to_pyobject` outside. This is a two-pass approach within the existing snapshot discipline. It reduces the clone count from `O(total-children)` to `O(matching-children)` but does not eliminate the snapshot-then-process structure.

---

## 4. Correctness constraints and blockers

### Lock-hold discipline (established invariant)

The project already enforces the rule: no Python work under a node RwLock. Evidence: `_span_getter_setter` (lines 836–851), `_children_getter` (lines 887–909 comment: "Lock scope: acquire read, snapshot, release before touching Python"), `_generic_extend_children` (lines 988–1009 comment: "Lock scope: hold read only long enough to clone the Arc-based children vec"). The claim that "filter inside guard" is safe for per-label methods contradicts this invariant.

### Panic while holding guard

`to_pyobject` is fallible (`PyResult`). If a PyO3 call inside the guard returns `Err`, the guard would be dropped by Rust's unwind. Rust's `std::sync::RwLock` is poisoned on panic; pyo3 uses panic for some error paths on Python exceptions. The existing snapshot discipline avoids this class of hazard entirely.

### `_generic_child` has no Python-work issue

For `child()`, the fix IS mechanical: check `len` under the guard, clone `children[0]` (one Arc bump), drop the guard, call `to_pyobject` outside. No Python work happens under the lock.

---

## 5. Native (GIL-free) per-label accessors: already fixed

The native (non-pymethod) per-label accessors generated by `_native_per_label_methods` (lines 1071–1345) do not use the snapshot pattern. They operate directly on `&self.children` with iterator chains (`children.iter().filter(...).filter_map(...)`), zero allocation, zero cloning on the common path. The pattern described by the TODO does not apply to the native API — only to the `#[pymethods]` block generated by `_per_label_methods`.

---

## 6. Is this papering over a deeper problem?

No deeper structural issue identified. The snapshot discipline is a deliberate design choice to separate PyO3 work from lock scope, consistent with the design ADR commentary throughout the file. The inefficiency is solely that the snapshot includes non-matching elements. The fix is bounded: reduce clone scope to matching elements only (for per-label methods), or to the single element (for `child()`).

---

## 7. Claim accuracy summary

| Sub-claim | Accurate? | Notes |
|---|---|---|
| Accessors clone full Vec under guard then filter outside | Yes | Confirmed at lines 1013–1019, 1388–1403, 1411–1424, 1441–1455 |
| O(total-children) Arc/Span clones per call | Yes | Each element clone = Arc bump (node) or Span copy |
| `child()` fix is mechanical | Yes | Check len + clone single entry, no Python under lock |
| Per-label fix is mechanical | Partially false | Filter-inside-guard violates established no-Python-under-lock invariant; correct fix is filter-under-guard + clone matching only + drop guard + convert outside |
| Fix is independent, not blocked by §6 benchmark | Yes | Pure template edit in `_per_label_methods` and `_generic_child` |
| Location: `_generic_child`, `_per_label_methods` | Yes | Lines 1011 and 1347 respectively |
