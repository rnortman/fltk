# Efficiency review — cross-backend label equality

Commit reviewed: c57f888 (base 854e1ad).
Scope: generators `gsm2tree.py` / `gsm2tree_rs.py`, regenerated CST outputs, `fltk2gsm.py`.

The design explicitly targets the same-backend hot path with own-type fast paths (§2.2/§2.3), and those are correctly emitted: the `children_X` filter `label == Class.Label.X` (per child) hits `other is self` / `type(other) is type(self)` and never builds a string on the same-backend path. Findings below concern the cross-backend path and repeated string rebuilds.

## efficiency-1 — `_fltk_canonical_name` rebuilds the f-string on every read (Python, both families)

`fltk/fegen/fltk_cst.py` (generated; source `gsm2tree.py:_node_kind_enum` / label-enum emit). The marker is a plain `@property`:

```python
@property
def _fltk_canonical_name(self) -> str:
    return f"NodeKind.{self.name}"
```

Enum members are immutable singletons — the canonical string is invariant per member — yet it is reformatted on every access. It is read on:
- Python `__hash__` (`return hash(self._fltk_canonical_name)`) — every hash of a label/kind member rebuilds the string, then hashes it.
- Python `__eq__` cross-type branch (`self._fltk_canonical_name == cn`).
- Every Rust-side cross-backend `__eq__`, which does a Python attribute access `getattr(other, "_fltk_canonical_name")` — that property fires and rebuilds the string.

**Consequence:** per-comparison / per-hash string allocation on the cross-backend path. Bites where labels/kinds are used as dict keys or set members (AC5 is an explicit use case) and in any out-of-tree consumer that compares Rust-parsed labels against Python module constants in a loop — exactly the `fltk2gsm.visit_items` shape (per-separator, per-item, per-rule at parse time). `__hash__` is the worst: it rebuilds the string even for pure same-backend dict/set usage, where the old `enum.Enum.__hash__` was a bare identity hash. This is a real regression for same-backend hashing.

**Fix:** compute the canonical name once per member and store it. Options that stay generator-emitted:
- Emit a per-member cached value rather than a property — e.g. a class-level dict `{member: "Name.Label.X"}` built once and read by index, or assign `member._fltk_canonical_name` as a plain attribute after class creation. The design (§2.1) already permits "a per-member value" instead of a property.
- Or memoize via `functools.cached_property` is unavailable on enum members; simplest is a post-class loop assigning a frozen string attribute, or precompute in `__hash__`/`__eq__` against a class-level mapping.

This removes the string rebuild from `__hash__` entirely (restoring cheap same-backend hashing) and from the cross-backend eq path.

## efficiency-2 — Rust `__hash__` / cross-eq allocate a fresh `PyString` per call

`fltk/fegen/gsm2tree_rs.py` `_node_kind_block` / `_label_enum_block`:

```rust
fn __hash__(&self, py) -> PyResult<isize> {
    pyo3::types::PyAnyMethods::hash(pyo3::types::PyString::new(py, self.__repr__()).as_any())
}
```

`PyString::new` allocates a new CPython `str` object on every hash call (and the cross-backend `__eq__` likewise round-trips through Python attribute access on `other`). `self.__repr__()` is already a `&'static str`, but the design (§3.1) requires routing through CPython's salted `hash(str)` for cross-backend hash agreement, so the `PyString` allocation is load-bearing for correctness on `__hash__` — not removable without breaking AC4.

**Consequence:** per-hash CPython string allocation on the Rust side. Same-backend Rust dict/set usage now allocates a `PyString` per hash where the old `#[pyclass(hash)]` derive hashed the discriminant directly. Cost shows up when Rust-backend labels/kinds are used as set/dict keys at any volume.

**Fix:** the salted-hash requirement constrains `__hash__`, so the allocation cannot be fully removed there; but it can be amortized — cache the hash isize per variant (e.g. a `GILOnceCell<isize>` per enum, or a `match` over a process-lifetime `GILOnceCell` map) so the `PyString` is built at most once per variant per process. The eq fast path already avoids this for same-type compares; confirm the cross-eq `getattr` path is only taken for genuinely-foreign operands (it is, given the own-type `extract` fast path precedes it).

## efficiency-3 — `kind` dataclass field joins generated `__eq__`/`__hash__` redundantly

`fltk/fegen/fltk_cst.py` (generated): every node gets `kind: typing.Literal[NodeKind.X] = NodeKind.X` as a dataclass field. As §2.4 notes, this field joins the dataclass-generated `__eq__`, where it is "always equal within a node type."

**Consequence:** node `==` now does one extra comparison per node that is invariant by construction (a node of type `Item` always has `kind == NodeKind.Item`, and `__eq__` only runs between same-type nodes since the dataclass eq short-circuits on type mismatch). With efficiency-1 unaddressed, that extra comparison is itself a cross-backend-capable enum `==` — but between two same-typed nodes both `kind` values are the *same* Python singleton, so `other is self` fires (cheap). Net cost is small but non-zero and pure overhead on every structural node comparison (used in the `test_*_rust_equals_python` parity tests and any consumer deep-equality).

**Fix:** if dataclass eq/repr cost matters, mark the field `dataclasses.field(compare=False, repr=False)` — it is a constant discriminant, never disambiguating. Low priority; flag only.

## Non-findings (verified clean)

- Same-backend filter path (`children_X`): own-type fast path correctly precedes the canonical-string path in both Python and Rust `__eq__`. No string build on the same-backend filter. Matches design intent.
- `fltk2gsm.py` `self.cst` removal introduces no redundant existence checks or repeated reads; `_cst_const` constants are module-level (resolved once).
- No new unbounded structures or leaks; enums and NodeKind are fixed-size per grammar.
