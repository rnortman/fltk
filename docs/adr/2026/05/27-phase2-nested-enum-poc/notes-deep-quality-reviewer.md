Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Commit reviewed: 5ee6eb4

---

## quality-1

**File:line**: `src/cst_poc.rs:143`, `src/cst_poc.rs:313`, `src/cst_poc.rs:385`, `src/cst_poc.rs:457`, `src/cst_poc.rs:529`

**Issue**: In every `extend_<label>` method, `label.into_pyobject(py)?` is called *inside the loop*, creating a new Python object for the same constant label on every iteration. The generic `extend` correctly hoists `label_val` before the loop (line 111). The per-label variants are inconsistent and wasteful.

```rust
// All five extend_* methods do this:
for child_result in iter {
    let child = child_result?;
    let label = Items_Label::Item.into_pyobject(py)?.into_any();  // inside loop
    ...
}
```

**Consequence**: The pattern will be mechanically reproduced by the Phase 3 code generator — the generator targets `cst_poc.rs` as its template. Every generated `extend_<label>` in production code will allocate a fresh Python enum object per child. This is a template bug, not just a PoC inefficiency. A grammar rule with 100 children processed via `extend_item` will allocate 100 identical PyO3 enum wrappers.

**Fix**: Hoist the label creation before the loop, matching the generic `extend` pattern:

```rust
fn extend_name(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
    let label = Identifier_Label::Name.into_pyobject(py)?.into_any().unbind();
    let iter = children.try_iter()?;
    for child_result in iter {
        let child = child_result?;
        let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
        self.children.bind(py).append(tup)?;
    }
    Ok(())
}
```

(Or use `clone_ref(py)` as the generic `extend` does for its `label_val`.)

---

## quality-2

**File:line**: `src/cst_poc.rs:162–181`, `src/cst_poc.rs:183–202` (and six analogous pairs in `Items`)

**Issue**: `child_<label>` and `maybe_<label>` share identical loop bodies — same label creation, same `found`/`count` accumulator, same downcast, same `eq` call — diverging only in the final error check (`!= 1` vs `> 1`). Each exists as a full copy. The `rust-cst-macro` TODO acknowledges this but only at the node-boilerplate level; the *within-node* `child`/`maybe` duplication is a separate concern: even a future macro would emit two copies of the loop per label unless the loop is factored into a shared helper.

**Consequence**: Any fix to the loop body (e.g., early exit on `count > 1` to avoid scanning the full list) must be applied to 10 method bodies across this file (2 methods × 5 labels). Phase 3 generator inherits this: every label in every node type emits two full loop copies.

**Fix**: Extract a private helper that returns `(count, Option<PyObject>)`:

```rust
fn filter_by_label(
    py: Python<'_>,
    list: &Bound<'_, PyList>,
    label: &Bound<'_, PyAny>,
) -> PyResult<(usize, Option<PyObject>)> {
    let mut found = None;
    let mut count = 0usize;
    for item in list.iter() {
        let tup = item.downcast::<PyTuple>()?;
        if tup.get_item(0)?.eq(label)? {
            count += 1;
            if count == 1 {
                found = Some(tup.get_item(1)?.unbind());
            }
        }
    }
    Ok((count, found))
}
```

`child_<label>` and `maybe_<label>` call `filter_by_label` and diverge only on the final assertion. This also applies to `children_<label>` (same loop, different accumulator). A free function (not a `#[pymethod]`) keeps it out of the Python API surface.
