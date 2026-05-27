# Phase 2 Design: Nested Enum PoC -- Rust CST Nodes

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

---

## Root Cause / Context

Phase 2 exists to validate two unproven PyO3 patterns before committing to the code generator (Phase 3). Per the phase plan, these are:

1. **`#[classattr]` nested-enum workaround**: PyO3 does not support nested `#[pyclass]` definitions. Production code accesses labels as `NodeClass.Label.FOO` (exploration sec. 3: `fltk2gsm.py:36-60`, `gsm2unparser.py:303-308`). The workaround -- standalone enum types attached via `#[classattr]` -- is documented but not validated in this codebase.

2. **`Py<PyList>` mutation semantics**: The parser mutates `children` via the returned list reference: `result.children.extend(item0.result.children)` (11 sites in `fltk_parser.py`, exploration sec. 4). If `#[pyo3(get)]` on `Py<PyList>` returns a copy instead of the backing list, these mutations silently drop data.

This phase hand-writes two representative CST node classes (`Identifier` and `Items`) in Rust to empirically resolve these questions. These nodes are standalone -- not wired into any production code path (requirements: "Out of Scope").

---

## Proposed Approach

### New Files

| File | Purpose |
|---|---|
| `src/cst_poc.rs` | `Identifier`, `Identifier_Label`, `Items`, `Items_Label` structs + `#[pymethods]` |
| `tests/test_rust_cst_poc.py` | All 27 acceptance criteria from requirements |

### Modified Files

| File | Change |
|---|---|
| `src/lib.rs` | `mod cst_poc;` declaration, register four new types + module |

No changes to `src/span.rs`, `fltk_cst.py`, `fltk_parser.py`, or any other existing source.

---

### Label Enums

Two standalone `#[pyclass]` enums, one per node type:

```rust
#[pyclass(eq, hash, frozen)]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Identifier_Label {
    #[pyo3(name = "NAME")]
    Name,
}

#[pyclass(eq, hash, frozen)]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Items_Label {
    #[pyo3(name = "ITEM")]
    Item,
    #[pyo3(name = "NO_WS")]
    NoWs,
    #[pyo3(name = "WS_ALLOWED")]
    WsAllowed,
    #[pyo3(name = "WS_REQUIRED")]
    WsRequired,
}
```

**No `eq_int`**: `eq_int` would make `Identifier_Label.NAME == 0` return `True`, diverging from Python `enum.Enum` (where `Label.NAME == 0` is `False`). No production code compares labels to integers.

**Cross-type comparison**: PyO3's generated `__richcmp__` for `#[pyclass(eq)]` enums attempts `downcast::<Self>(other)`. When comparing across different `#[pyclass]` types (e.g., `Identifier_Label` vs `Items_Label`, or label vs `None`), the downcast fails and the method returns `NotImplemented`. Python's `PyObject_RichCompare` then falls back to identity comparison, yielding `False`. This gives correct inter-class discrimination (AC-4) and correct `None`-label filtering (AC-27). Verified by reading `pyo3-macros-backend` source: `pyclass_richcmp_simple_enum` in `pyclass.rs:1893-1971`.

Rust enum variants use CamelCase; `#[pyo3(name = "NAME")]` maps to the Python-visible `ALL_CAPS` name.

**`__repr__`**: Each enum gets a `__repr__` returning a string like `"Identifier.Label.NAME"`. This matches the debugging expectation (requirement: "must include class name and variant name").

```rust
#[pymethods]
impl Identifier_Label {
    fn __repr__(&self) -> &'static str {
        match self {
            Identifier_Label::Name => "Identifier.Label.NAME",
        }
    }
}
```

---

### Node Structs

```rust
#[pyclass]
pub struct Identifier {
    #[pyo3(get, set)]
    span: PyObject,
    #[pyo3(get)]
    children: Py<PyList>,
}
```

**`span` as `PyObject`**: The node accepts any Python object as a span. The Phase 2 PoC is standalone; the parser uses Python `Span` (from `terminalsrc`), not Rust `Span` (which lacks `.start`/`.end` attributes). Storing as `PyObject` avoids coupling to either Span type.

**`children` as `Py<PyList>`**: The `#[pyo3(get)]` on `Py<PyList>` returns a reference to the same Python list object (refcount increment, not copy). This is the central hypothesis being validated. No `#[pyo3(set)]` on `children` -- the list object itself is never replaced; only its contents are mutated.

---

### Construction (`#[new]`)

```rust
#[new]
#[pyo3(signature = (*, span=None))]
fn new(py: Python<'_>, span: Option<PyObject>) -> PyResult<Self> {
    let span_obj = match span {
        Some(s) => s,
        None => {
            let native = py.import("fltk._native")?;
            native.getattr("UnknownSpan")?.unbind()
        }
    };
    Ok(Identifier {
        span: span_obj,
        children: PyList::empty(py).unbind(),
    })
}
```

**Keyword-only `span`**: The `*` in the signature makes `span` keyword-only, matching the parser's construction pattern: `Identifier(span=Span(start=pos, end=-1))`. The `Identifier()` no-arg form defaults to `UnknownSpan` via runtime import from `fltk._native` (requirement AC-22).

**`UnknownSpan` default via import**: Rather than hardcoding `Span { start: -1, end: -1, source: None }`, we import `UnknownSpan` from the module. This ensures the default span satisfies `node.span == UnknownSpan` (AC-22 requires equality, not identity; this approach also provides identity as a bonus). Since construction is not on any hot path in Phase 2, the import cost is irrelevant.

---

### `#[classattr]` Label Attachment

```rust
#[pymethods]
impl Identifier {
    #[classattr]
    fn Label(py: Python<'_>) -> PyResult<Py<PyType>> {
        Ok(Identifier_Label::type_object(py).unbind())
    }
}
```

`Identifier.Label` resolves to the type object `Identifier_Label`. `Identifier.Label.NAME` then resolves to `Identifier_Label.NAME`, which PyO3 exposes as a class attribute on the enum type. This gives the `NodeClass.Label.FOO` access pattern.

**`type_object` API**: `T::type_object(py)` returns `Bound<'_, PyType>`. `.unbind()` gives `Py<PyType>`, which implements `IntoPyObject`. `#[classattr]` accepts `py: Python<'_>` as an optional special parameter (verified in `pyo3-macros-backend` `pymethod.rs:530`, `impl_py_class_attribute`). The return value goes through `IntoPyObject` -> `PyObject`, so `Py<PyType>` works directly.

---

### Generic Methods

**`append`**:
```rust
#[pyo3(signature = (child, label=None))]
fn append(&self, py: Python<'_>, child: PyObject, label: Option<PyObject>) -> PyResult<()> {
    let label_val = label.unwrap_or_else(|| py.None());
    let tup = PyTuple::new(py, [label_val, child])?;
    self.children.bind(py).append(tup)?;
    Ok(())
}
```

Both `child` and `label` are positional-or-keyword (requirement: "both parameters are positional-or-keyword").

**`extend`**:
```rust
#[pyo3(signature = (children, label=None))]
fn extend(&self, py: Python<'_>, children: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {
    let label_val = label.unwrap_or_else(|| py.None());
    let iter = children.try_iter()?;
    for child_result in iter {
        let child = child_result?;
        let tup = PyTuple::new(py, [label_val.clone_ref(py).into_bound(py), child])?;
        self.children.bind(py).append(tup)?;
    }
    Ok(())
}
```

Accepts any Python iterable (requirement: "accept any Python iterable, not only lists").

**`child`**:
```rust
fn child(&self, py: Python<'_>) -> PyResult<PyObject> {
    let list = self.children.bind(py);
    let n = list.len();
    if n != 1 {
        return Err(PyValueError::new_err(format!("Expected one child but have {n}")));
    }
    Ok(list.get_item(0)?.unbind())
}
```

Returns the `(label, child)` tuple as a `PyObject` -- the raw Python tuple, not destructured.

---

### Per-Label Methods (Pattern)

For `Identifier` with label `name` / constant `Identifier_Label::Name`:

**`append_name`**:
```rust
fn append_name(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
    let label = Identifier_Label::Name.into_pyobject(py)?.into_any();
    let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
    self.children.bind(py).append(tup)?;
    Ok(())
}
```

**`children_name`**: Returns a Python list of matching children (not a generator). Collects into a `Vec<PyObject>`, returns as `Py<PyList>`.

```rust
fn children_name(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
    let label_obj = Identifier_Label::Name.into_pyobject(py)?;
    let result = PyList::empty(py);
    for item in self.children.bind(py).iter() {
        let tup = item.downcast::<PyTuple>()?;
        if tup.get_item(0)?.eq(&label_obj)? {
            result.append(tup.get_item(1)?)?;
        }
    }
    Ok(result.unbind())
}
```

**Returning list vs. generator**: Requirements explicitly permit this: "Returns a Python list (not a generator/iterator). This is a deliberate simplification." All production call sites iterate or call `list()` on the result.

**`child_name`** and **`maybe_name`**: Inline the filter logic rather than calling `children_name`, avoiding an unnecessary list allocation.

```rust
fn child_name(&self, py: Python<'_>) -> PyResult<PyObject> {
    let label_obj = Identifier_Label::Name.into_pyobject(py)?;
    let mut found: Option<PyObject> = None;
    let mut count = 0usize;
    for item in self.children.bind(py).iter() {
        let tup = item.downcast::<PyTuple>()?;
        if tup.get_item(0)?.eq(&label_obj)? {
            count += 1;
            if count == 1 {
                found = Some(tup.get_item(1)?.unbind());
            }
        }
    }
    if count != 1 {
        return Err(PyValueError::new_err(format!("Expected one name child but have {count}")));
    }
    Ok(found.unwrap())
}

fn maybe_name(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
    let label_obj = Identifier_Label::Name.into_pyobject(py)?;
    let mut found: Option<PyObject> = None;
    let mut count = 0usize;
    for item in self.children.bind(py).iter() {
        let tup = item.downcast::<PyTuple>()?;
        if tup.get_item(0)?.eq(&label_obj)? {
            count += 1;
            if count == 1 {
                found = Some(tup.get_item(1)?.unbind());
            }
        }
    }
    if count > 1 {
        return Err(PyValueError::new_err(format!("Expected at most one name child but have {count}")));
    }
    Ok(found)
}
```

**`extend_name`**: Same pattern as generic `extend` but hardcodes the label.

---

### `Items` Node

Same structure as `Identifier` but with four labels. The `#[pymethods]` block contains 20 per-label methods (5 per label x 4 labels) plus the 3 generic methods plus `#[new]`, `#[classattr] Label`, `__eq__`, `__repr__`, `__hash__`.

Labels: `ITEM`, `NO_WS`, `WS_ALLOWED`, `WS_REQUIRED`. Method names: `append_item`, `children_item`, `child_item`, `maybe_item`, `extend_item`, `append_no_ws`, ..., `maybe_ws_required`.

The implementation is mechanically identical to `Identifier`'s methods, substituting the label constant and method/error-message name.

---

### `__eq__`

```rust
fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
    // Return NotImplemented for non-same-type comparisons
    if !other.is_instance_of::<Identifier>() {
        return Ok(py.NotImplemented().into_any().unbind());
    }
    let other_node: PyRef<Identifier> = other.extract()?;
    let span_eq = self.span.bind(py).eq(other_node.span.bind(py))?;
    if !span_eq {
        return Ok(false.into_pyobject(py)?.unbind().into_any());
    }
    let children_eq = self.children.bind(py).eq(other_node.children.bind(py))?;
    Ok(children_eq.into_pyobject(py)?.unbind().into_any())
}
```

Returns `NotImplemented` for non-same-type comparison (requirement: "Comparison with non-node types returns NotImplemented"). Delegates to Python `==` for both `span` and `children`, giving recursive tuple/list comparison for free.

---

### `__hash__`

```rust
fn __hash__(&self) -> PyResult<isize> {
    Err(PyTypeError::new_err("unhashable type: 'Identifier'"))
}
```

Requirement: "hash(node) raises TypeError" (AC-24). Python dataclasses with `eq=True` and no `frozen=True` set `__hash__ = None`, making instances unhashable.

Note: PyO3 does not support setting `__hash__` to `None` directly. Implementing `__hash__` to raise `TypeError` achieves the same runtime behavior.

---

### `__repr__`

```rust
fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
    let span_repr = self.span.bind(py).repr()?.to_string();
    let children_repr = self.children.bind(py).repr()?.to_string();
    Ok(format!("Identifier(span={span_repr}, children={children_repr})"))
}
```

Matches the Python dataclass `__repr__` format. No test asserts exact format, but the class name must be present (requirement AC-26).

---

### `&self` vs `&mut self`

All methods use `&self`, not `&mut self`. The `children` field is `Py<PyList>` -- a Python-managed list. Mutations go through `Py::bind(py)` to get a `Bound<'_, PyList>`, then call Python list methods (`.append()`, etc.). The Rust struct fields are never mutated by these methods; only the Python list object's contents change. The `span` field uses `#[pyo3(set)]` which PyO3 handles via its own setter mechanism, not `&mut self`.

This avoids `RuntimeError: Already borrowed` panics that occur when `&mut self` methods are called reentrantly (e.g., if `__eq__` is triggered during a children list operation).

---

### Module Registration

```rust
// In lib.rs
mod cst_poc;

use cst_poc::{Identifier, Identifier_Label, Items, Items_Label};

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Existing registrations...
    m.add_class::<Span>()?;
    m.add_class::<SourceText>()?;
    m.add("UnknownSpan", Py::new(m.py(), Span { start: -1, end: -1, source: None })?)?;

    // Phase 2 additions
    m.add_class::<Identifier_Label>()?;
    m.add_class::<Identifier>()?;
    m.add_class::<Items_Label>()?;
    m.add_class::<Items>()?;

    Ok(())
}
```

Registration order does not matter for `#[classattr]` resolution -- `type_object(py)` returns the type object from the Python interpreter's type registry, which is populated at class definition time (before `#[pymodule]` runs). Both label types and node types are top-level module entries.

---

## Edge Cases / Failure Modes

### `#[classattr]` returning `Py<PyType>` does not compile

Unlikely given the verified `IntoPyObject` impl for `Py<T>`, but if it fails: return `PyObject` instead via `Identifier_Label::type_object(py).into_any().unbind()`. Python attribute resolution still works because `Identifier.Label.NAME` resolves `Label` to the type object, then resolves `NAME` on it. Phase-plan R1 mitigation (module-level label classes with aliases) is the nuclear fallback.

### Generic `extend` iterates input while appending to backing list

The generic `extend` iterates the *input* iterable and appends to `self.children`. This is safe: `append_*` and `extend_*` do not iterate the backing list. `children_*`, `child_*`, `maybe_*` iterate but do not modify. No method both iterates and modifies the same list.

### Stale `children` reference across mutations

A Python caller holds `ref = node.children`, then calls `node.append_name(child)`. `ref` and `node.children` are the same Python list object (refcount-shared via `Py<PyList>`). `append_name` mutates that same object via `self.children.bind(py).append(...)`. `ref` sees the mutation. This is the central hypothesis being validated (AC-6, AC-7, AC-8).

---

## Test Plan

New file: `tests/test_rust_cst_poc.py`. Uses `pytest.importorskip("fltk._native")` at module level.

Tests map 1:1 to the 27 acceptance criteria in requirements. Organized by test class:

| Test Class | Criteria Covered |
|---|---|
| `TestLabelSemantics` | AC-1 (identity/equality), AC-2 (containment), AC-3 (intra-class discrimination), AC-4 (inter-class discrimination), AC-5 (hashability) |
| `TestChildrenListSemantics` | AC-6 (same object), AC-7 (mutation visibility), AC-8 (cross-node extend) |
| `TestAppendAndAccessors` | AC-9 (tuple structure), AC-10 (append_name + child_name), AC-11 (extend_name + children_name), AC-12 (child_name raises), AC-13 (maybe_name None), AC-14 (maybe_name returns child), AC-15 (maybe_name raises) |
| `TestGenericMethods` | AC-16 (append label=None), AC-17 (append explicit label), AC-18 (extend), AC-19 (child) |
| `TestTypeIdentity` | AC-20 (isinstance) |
| `TestSpanField` | AC-21 (setter), AC-22 (default) |
| `TestEquality` | AC-23 (equality) |
| `TestHashability` | AC-24 (unhashable) |
| `TestItemsMethods` | AC-25 (all four labels) |
| `TestRepr` | AC-26 (repr) |
| `TestNoneLabelFiltering` | AC-27 (None-label exclusion) |

Each test constructs nodes directly (no parser involvement), using `Span` from `fltk._native` as the child/span object. Example:

```python
def test_label_identity_equality(self):
    assert Identifier.Label.NAME == Identifier.Label.NAME

def test_children_same_object(self):
    node = Identifier()
    a = node.children
    b = node.children
    assert a is b
```

---

## Open Questions

None. The exploration's OQ-classattr-type-return and OQ-none-label-eq are both resolved by source investigation of `pyo3-macros-backend` 0.23.5. See "Label Enums" and "`#[classattr]` Label Attachment" sections for the verified answers.
