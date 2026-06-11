# Exploration: `rust-cst-children-list-view` TODO adversarial validation

Concise. Precise. Token-dense — no fluff, full information.

---

## 1. Snapshot-vs-live divergence: is it real?

**Yes. Both claims are accurate.**

### Rust backend — snapshot

`gsm2tree_rs.py:875` defines `_children_getter`, which emits the following Rust body for
every `#[getter] fn children`:

```rust
// Snapshot the children vec (Arc clones for node children — O(n) refcount bumps).
// Lock scope: acquire read, snapshot, release before touching Python.
let snapshot: Vec<_> = {
    let guard = self.inner.read();
    guard.children.clone()
};
let result = PyList::empty(py);
for (label, child) in &snapshot { ... result.append(tup)?; }
Ok(result.unbind())
```

This code is in the generated output, verified at `src/cst_fegen.rs:491–510` (Grammar node)
and `tests/rust_cst_fixture/src/cst.rs` (fixture nodes). A fresh `PyList` is allocated and
populated on every getter call. The returned list object is unconnected to the native `Vec`;
appending to or clearing it has no effect on the node.

**Test that pins this behavior:** `tests/test_rust_cst_poc.py:47–55`
(`TestChildrenListSemantics.test_children_rebuilt_each_call`) — asserts `a == b` but does
not require `a is b`.

**TODO line-number discrepancy:** The TODO entry in `TODO.md:25` and the docstring in
`gsm2tree_rs.py:881` both cite "`_children_getter`, lines 682–700". The function is actually
at line **875** of `gsm2tree_rs.py`. The 682–700 range falls inside the data-struct native
method block (`set_span`, `children` native slice, `push_child`) emitted by
`_emit_data_struct`, not the Python-getter method. The discrepancy is in the
`exploration-identity-abi.md` and `design.md` cross-references as well. The behavior
described is correct; the line number is stale.

### Python backend — live list

`gsm2tree.py:258–260` emits:
```python
children: list[tuple[{label_annotation}, {child_annotation}]] = dataclasses.field(default_factory=list)
```
The `append` method body (`gsm2tree.py:273`):
```python
self.children.append((label, child))
```
The `extend_children` method body (`gsm2tree.py:289`):
```python
self.children.extend(other.children)
```

`children` is a plain dataclass list field. `node.children` returns the field reference
directly — no getter, no copy. In-place mutation of the returned list (`node.children.append(x)`,
`node.children.extend(...)`) modifies the node's backing list.

The generated `fltk_cst.py` (e.g. `fltk_cst.py:82–91`, `fltk_cst.py:148–157`) shows the
same pattern in compiled form.

---

## 2. Do downstream consumers plausibly mutate `node.children` in place?

### In-tree consumers — **not currently**

Every in-tree mutation goes through named methods, not through the getter:
- `fltk_parser.py`: all 11 extend sites use `result.extend_children(other=...)` (grep
  confirms `extend_children` in use, `.children.extend(` absent from generated parser output).
- `fltk2gsm.py:55`: captures `labeled_children = items.children` and then reads via indexing
  (`labeled_children[0]`, `labeled_children[start_idx:]`, stride slices) — read-only.
- `bootstrap2gsm.py:36–45`: same pattern — captures `items.children`, reads only.
- `gsm2unparser.py`: accesses `node.fld.children` through IIR field access, compiled to
  `node.children` in generated Python — indexing and `len()` only (subscript + iteration),
  no append/extend through the getter.

**Test guard in place:** `fltk/fegen/test_genparser.py:135–163`
(`test_gsm2parser_extend_children_call_site`) asserts that generated parsers emit
`extend_children`, not `.children.extend(`, and that the latter is absent. This assertion
was added precisely because the getter-mutation pattern was a known silent failure mode on
the Rust backend.

### The Phase 4 requirement doc — **historically required it**

`docs/adr/2026/05/28-pyo3-phase4-runtime-integration/requirements.md:146` and
`exploration.md:446` both list:
> 4. **Children mutate via extend**: `node.children.extend(other.children)` —
> `children` is a live Python list (not a snapshot).

This was the contract as of Phase 4 requirements writing. The test-genparser guard and the
switch to `extend_children` in `gsm2parser.py` post-date those requirements and remove the
actual dependency. No in-tree consumer of a **Rust-backend** node currently calls
`.children.extend(...)` on the returned list.

### Is the Python-backend live-list behavior **intended API or accident**?

It is **an accident of the dataclass representation**, not a designed API surface.
The Protocol declarations (`gsm2tree.py:658–661`, `fltk_cst_protocol.py`) declare
`children: list[tuple[...]]` — a typed attribute, not a property. There is no documented
guarantee that the list is the backing store. The Phase 3 and Phase 4 docs repeatedly call
it "live reference" as a descriptor of the Python-dataclass implementation, not as a
contract to preserve. The `test_genparser.py` guard is direct evidence that the codebase
has already moved away from depending on it.

---

## 3. How hard is a live sequence-proxy pyclass?

### What it would require

A live sequence-proxy would be a `#[pyclass]` that:
- Holds a `Shared<NodeData>` (a reference back to the node's `Arc<RwLock<NodeData>>`).
- Implements `__len__` → acquires a read lock, returns `guard.children.len()`.
- Implements `__getitem__` (integer + slice) → acquires a read lock, extracts the
  requested item(s), converts to Python tuple(s), releases lock.
- Implements `__setitem__` and `__delitem__` if full list mutation is needed → acquires
  write lock, modifies `guard.children` in place.
- Implements `__iter__` (or `__contains__`, etc.) for the full list protocol.
- Must be returned by value from `#[getter] fn children` — PyO3 supports this pattern.

### Complexity

- Lock discipline: every `__getitem__` call must hold the read lock only long enough to
  clone the single entry (same snapshot-then-drop rule already applied everywhere). A
  mutable slice (`__setitem__` with a slice range) must convert incoming Python tuples back
  to native `(label, child)` pairs — requires the same `extract_from_pyobject` path already
  in `_generic_append`.
- The proxy pyclass must be node-type-specific (it references the concrete
  `children: Vec<(LabelType, ChildEnum)>`) or generic over the label/child types. PyO3 does
  not support generic pyclasses; the generator would need to emit a distinct proxy class per
  node type, roughly doubling the pyclass count in the generated `.rs` file.
- Equality: `proxy1 == proxy2` semantics (by-value snapshot equality vs by-identity)
  is an additional design question.
- No existing PyO3 infrastructure in this codebase approaches this pattern. The `Shared<T>`
  registry handles object-identity stability for node handles, but not for a list-view proxy.

### Blockers

No hard blockers. The design files cite it as "deferrable, additive later" and that
assessment is accurate. The practical blocker is that no in-tree or visible out-of-tree
consumer depends on mutation-through-the-getter; the test guard enforces this invariant
going forward.

---

## 4. Is this papering over a deeper problem?

### Should mutation-through-children be supported at all?

The public mutation API is `append`, `append_{label}`, `extend`, `extend_{label}`,
`extend_children`. These are documented methods that go through the Rust `write()` lock and
type-check their arguments. The `.children` getter exists for read access — indexing, slicing,
iteration, len — and is used only for reads across all in-tree consumers.

There is no in-tree code that depends on list-level mutation through the getter. The Phase 4
requirements docs listed it as a contract, but that contract was invalidated by the parser
generator fix. Making mutation through `node.children` work on the Rust backend would add
implementation complexity (proxy class, double the generated pyclass surface) to support a
mutation path that is now explicitly guarded against and not exercised.

The deeper question — whether `node.children` should be a writable interface at all — is
answered by the Protocol declarations: `children` is typed as `list[tuple[...]]`, which
implies writability at the type level. However, the typed mutation methods (`append`,
`extend`, `extend_children`) provide type-safe alternatives that work identically across
both backends. The Protocol type annotation for `children` as a plain `list` is the real
mismatch, not the Rust behavior.

---

## 5. Summary of claim accuracy

| Claim | Verdict |
|---|---|
| Rust backend returns fresh `PyList` per call | **Accurate** — `src/cst_fegen.rs:491–510`, `gsm2tree_rs.py:875–909` |
| In-place mutation of returned list is silent no-op | **Accurate** — list is disconnected from `Vec` |
| Python backend returns the node's actual internal list | **Accurate** — dataclass field, no property, `gsm2tree.py:258–260` |
| In-place list mutation edits the tree (Python) | **Accurate** for the Python backend |
| Closing divergence requires live sequence-proxy pyclass | **Accurate** — no other mechanism in PyO3 |
| Deferred as additive | **Accurate** — no in-tree consumer depends on mutation-through-getter |
| Python-backend behavior documented in Phase 3 docs | **Partially accurate** — Phase 4 exploration/requirements docs describe it; Phase 3 design doc does not mention the snapshot/live divergence |
| Location: `_children_getter`, lines 682–700 | **Incorrect line numbers** — function is at `gsm2tree_rs.py:875`, not 682–700; 682–700 is the native-Rust `children()` slice method in the data struct |
