# Exploration: rust-cst-child-node-identity TODO verification

Concise. Precise. Token-dense — no fluff, full information. Audience: smart LLM/human.

## Claim verification: cited test lines

The TODO claims tests at `tests/test_phase4_rust_fixture.py:242,276,291,350,371` "formerly used `is` for child identity were relaxed to `==`".

Verified. All five cited locations contain `# TODO(rust-cst-child-node-identity): cache if identity is needed.` and use `==` rather than `is`:

- **line 241–243**: `test_ac6_list_protocol_index` — `assert tup[1] == child`
- **line 275–277**: `test_ac6_list_protocol_negative_index` — `assert last[1] == b`
- **line 290–292**: `test_ac7_tuple_items` — `assert value == ident`
- **line 349–351**: `test_ac11_iterator_methods` — `assert node.child_key() == ident`
- **line 370–372**: `test_ac12_generic_child` — `assert tup[1] == ident`

Additionally, `tests/test_rust_cst_poc.py:46–54` explicitly documents the identity-non-guarantee in a test named `test_children_rebuilt_each_call`, asserting only `a == b` (not `a is b`) for two successive `.children` calls on the same empty node.

## Claim verification: ownership model and clone-on-access

The TODO correctly describes the mechanism. Verified against generated code (`src/cst_generated.rs`) and the generator (`fltk/fegen/gsm2tree_rs.py`):

**Struct layout** (`cst_generated.rs:224–226`, mirrored by generator `gsm2tree_rs.py:604`):
```rust
pub struct Identifier {
    span: Span,
    children: Vec<(Option<Identifier_Label>, IdentifierChild)>,
}
```

**Child enum** (`cst_generated.rs:563–564`, generator `gsm2tree_rs.py:494–495`):
```rust
Identifier(Box<Identifier>),
Trivia(Box<Trivia>),
```

Node-typed children are owned by value inside `Box<T>` in the `Vec`. There is no `Py<T>` stored anywhere on the struct.

**Python boundary conversion** (`cst_generated.rs:593`, generator `gsm2tree_rs.py:547`):
```rust
Self::Identifier(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
```

Every call to `to_pyobject` on a node-typed child calls `(**n).clone()` and then `Py::new(...)`, allocating a fresh `PyCell<T>` wrapper. `Py::new` is the pyo3 constructor that boxes the Rust value in a new Python heap object. Two successive calls to any accessor that returns a node child (`children`, `child`, `child_<label>`, `children_<label>`, `maybe_<label>`) produce two distinct Python objects at different memory addresses — Python `is` will be `False` even though `==` is `True` (structural equality via `__eq__` delegates to native `PartialEq`).

This applies to all node-typed children. Span children (`Span` variant) are also reconstructed via `span_type.call1(...)` each time but Span is `#[pyclass(frozen, eq, hash)]`, so the identity question is less practically relevant for spans.

**`children` getter** (`gsm2tree_rs.py:755–774`): rebuilds a fresh `PyList` from the entire `Vec` on every call. The list itself is also a new object each time. `tests/test_rust_cst_poc.py:46–54` directly verifies this: two successive `node.children` calls produce distinct list objects.

## Feasibility of the proposed fix (per-node boundary cache)

The TODO proposes "a per-node boundary cache (e.g. `Py` cache indexed by position)".

**What this would require:**

A cache `Vec<Option<PyObject>>` (or `HashMap<usize, PyObject>`) stored on each node struct, populated lazily when `to_pyobject` is first called for position `i`. Since PyO3 node structs are not `#[pyclass(frozen)]`, mutation is already possible — `&mut self` methods exist (`append`, `extend`, `set_span`, etc.).

**Blockers the TODO did not mention:**

1. **Cache invalidation on mutation.** `append`, `extend`, `extend_children`, `append_<label>`, `extend_<label>` all mutate `self.children` (the native `Vec`). Any cache indexed by position is invalidated when children are inserted. Position-indexed caches become incorrect if a child is prepended or inserted in the middle (not currently supported, but appending shifts nothing). Even append-only, a cache must be grown to match each new `Vec` entry. The current API has no delete/replace operations, but the protocol allows `extend_children` which bulk-appends from another node, making positional invalidation non-trivial to avoid.

2. **GIL and `Py<T>` lifecycle.** Storing `Py<PyObject>` (an owned reference to a Python object) inside a `#[pyclass]` struct requires careful handling. PyO3 allows this but the `Py<T>` drops its refcount when the Rust struct is dropped — which requires the GIL. PyO3's `Drop` impl for `Py<T>` queues the decrement when not holding the GIL, but this is standard PyO3 usage and not a fundamental blocker.

3. **Structural equality becomes identity equality for cached children, but Python `__eq__` is already structural.** The node's `__eq__` (`gsm2tree_rs.py:989–1001`) compares structurally via `PartialEq`, not by Python object identity. A cache would make repeated getter calls return the same Python object, but structural equality already works correctly without it. So the cache fixes `is` but cannot affect `==`.

4. **Span children cannot be cached the same way.** Span children are reconstructed via Python calls (`span_type.call1(...)` or `span_type.call_method1("with_source", ...)`). Their identity is independently unstable, but Span is `frozen, eq, hash` so `is` on spans is not load-bearing in any current in-tree code.

5. **Thread safety.** `#[pyclass]` without `Sync` or `Send` bounds is single-threaded from Python's perspective (GIL-protected), so a `Vec<Option<PyObject>>` cache doesn't require additional synchronization beyond what PyO3 already enforces.

**Whether this is papering over a symptom:** The root cause is that the ownership model — `Box<T>` in the native `Vec` — was deliberately chosen (`gsm2tree_rs.py:844–859`, `_generic_extend_children` docstring) to enable `extend_children` to efficiently bulk-copy children from one node to another by cloning the native `Vec` entries, without going through Python. The design comment at `gsm2tree_rs.py:845–848` explicitly states this was chosen because `a.children.extend(b.children)` would mutate a throwaway list. So the cloning-on-Python-access is an intentional consequence of the native-ownership design, not incidental.

A cache would reduce the symptom (fresh wrappers per call) without changing the fundamental tradeoff: native ownership enables GIL-free tree manipulation (used in `extend_children`, and the `new_native`/`push_child_native`/`span_native`/`children_native` native API), at the cost of Python identity instability per access.

## Real downstream consumer exposure

The CLAUDE.md states: "The real consumers live outside this repository and are not visible here."

**Patterns in current in-tree code where identity instability could bite:**

1. **`fltk2gsm.py:55`** — `labeled_children = items.children` stores the `children` list once, then accesses it repeatedly via `labeled_children[start_idx:]` and stride slicing (`labeled_children[::2]`, `labeled_children[1::2]`). This is safe because it stores the list (rebuilt once), then indexes into the stored list — no second `node.children` call. But it illustrates that downstream code naturally stores the result rather than calling the getter twice.

2. **`fltk2gsm.py:79`** — `assert item.kind == cst.Item.kind` — uses `==` on `kind`, not `is`. Safe.

3. **`fltk2gsm.py:113`** — `item.maybe_label()` and `item.maybe_disposition()` are called once and the result stored in a local variable. No repeated calls to the same accessor on the same node. Safe as written.

**Realistic downstream risk scenarios:**

- Code that calls the same labeled accessor twice expecting the same Python object: `child = node.child_key(); assert child is node.child_key()` — fails with Rust backend.
- Code that uses node children as dict keys or set members: nodes are explicitly `__hash__ = PyTypeError` (`gsm2tree_rs.py:1003–1008`), so this fails before identity is even tested. Not a risk.
- Code that checks `child_a is child_b` to deduplicate nodes in a tree walk — would silently fail with Rust backend even when logically the same child.
- Code that accumulates children via `results.append(node.child_key())` in a loop across grammar rules, then checks `id(x) == id(y)` or `x is y` across accumulated results — would fail.

**Python backend comparison:** The Python backend (`gsm2tree.py`) stores `children` as a plain `list` attribute on a `@dataclass`. Accessing `node.children[0][1]` twice returns the same Python object because the list contains the actual Python object reference — no copy occurs. So Python backend has stable identity; Rust backend does not.

## Summary of factual discrepancies vs. TODO text

- The cited line numbers are correct and the `==`/`is` relaxation is accurately described.
- "Native child ownership (`Box<ChildNode>` in the native Vec)" — correct.
- "a child returned twice through a Python getter/accessor wraps a fresh `Py<ConcreteNode>` per call" — confirmed, via `Py::new(py, (**n).clone())` in `to_pyobject`.
- "Location: `fltk/fegen/gsm2tree_rs.py` (accessor methods in `_per_label_methods`)" — correct. The clone-on-access pattern is in `_child_enum_block`'s `to_pyobject`, called from `_children_getter`, `_generic_child`, and `_per_label_methods` accessors.
- The proposed fix is feasible in principle but has the cache-invalidation complication on mutation (append/extend), which the TODO did not mention. The fix would also need to handle the list-level identity of `node.children` itself (currently a fresh `PyList` each call) separately from per-element identity.
