# TODO(kind-field-dataclass-eq) — Factual Verification

Concise. Precise. Token-dense. No fluff. Audience: smart LLM/human.

---

## Claim under review

TODO at `fltk/fegen/gsm2tree.py:223-224` (`py_class_for_model`):

> The `kind` dataclass field joins the generated `__eq__`/`__hash__` for every node, but it is invariant within a node type. Mark `kind` with `dataclasses.field(compare=False, repr=False)` if node-equality performance becomes a concern.

---

## Code surface

### Emit site

`fltk/fegen/gsm2tree.py:200,226-228` — `py_class_for_model` calls `pygen.dataclass(class_name)` then appends:

```python
pygen.stmt(f"kind: typing.Literal[NodeKind.{kind_member}] = NodeKind.{kind_member}"),
```

`fltk/pygen.py:53-65` — `pygen.dataclass` emits `@dataclasses.dataclass` with no keyword arguments (no `eq=`, `frozen=`, `unsafe_hash=`). Python's default: `eq=True`, `frozen=False`, `unsafe_hash=False`. Because `eq=True` and `frozen=False`, Python sets `__hash__ = None` — nodes are **not hashable**.

### Generated output

`fltk/fegen/fltk_cst.py:55,74-76` — representative generated class `Grammar`:

```python
@dataclasses.dataclass
class Grammar:
    ...
    kind: typing.Literal[NodeKind.GRAMMAR] = NodeKind.GRAMMAR
    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[...] = dataclasses.field(default_factory=list)
```

Runtime inspection confirms: `dataclasses.fields(Grammar())` → `kind: compare=True, repr=True, hash=None`.

---

## Invariance: is `kind` truly invariant within a node type?

**Yes.** `kind` is declared with a fixed class-level default (`= NodeKind.GRAMMAR` for `Grammar`, `= NodeKind.RULE` for `Rule`, etc.). There is no API to set it to a different value at construction time — the constructor only uses positional/keyword arguments; downstream consumers call `Grammar()` or `Grammar(span=..., children=...)`, never `Grammar(kind=...)` in practice (though technically possible via the dataclass constructor). The value is the `NodeKind` enum singleton specific to each class.

Runtime confirmation: `g1.kind is g2.kind` → `True` (same `NodeKind.GRAMMAR` singleton for two separate `Grammar()` instances).

---

## Does `kind` participate in `__eq__`?

**Yes — it participates in comparison but is not the cross-type guard.**

CPython's generated dataclass `__eq__` checks `other.__class__ is self.__class__` first; if not, returns `NotImplemented`. Verified: `Grammar().__eq__(Rule())` → `NotImplemented` (Python then falls back to identity → `False`).

Consequence: for **cross-type** comparisons (e.g. `Grammar()` vs `Rule()`), `__class__` is the discriminant, not `kind`. `kind` never gets evaluated in that path.

For **same-type** comparisons (e.g. `Grammar()` vs `Grammar()`), dataclass `__eq__` compares all fields left-to-right: `kind` first, then `span`, then `children`. Since `kind` is always `NodeKind.GRAMMAR` for every `Grammar` instance, the comparison reduces to `NodeKind.GRAMMAR == NodeKind.GRAMMAR`. That comparison hits the cross-backend `__eq__` on `NodeKind` (which checks `other is self` as a fast path via identity — `NodeKind` members are singletons), so the `kind` comparison is a singleton identity check — one `is` test — before short-circuiting to the `span` and `children` comparisons.

---

## Does `kind` participate in `__hash__`?

**No.** Generated node classes use `@dataclasses.dataclass` with no `frozen=True` or `unsafe_hash=True`. Python sets `__hash__ = None` when `eq=True` and `frozen=False`. `Grammar.__hash__` is `None`; nodes are not hashable. The `hash=None` in field metadata means Python ignores the field for hash purposes regardless.

---

## `repr`: current state and observability

**Current state (generated nodes):** `kind` has `repr=True` (default). `repr(Grammar())` produces:

```
Grammar(kind=<NodeKind.GRAMMAR: 1>, span=Span(start=-1, end=-1), children=[])
```

**Existing test assertions on node repr** (`test_rust_cst_poc.py:395-407`):

```python
assert "Identifier" in r   # class name present
assert "Items" in r        # class name present
```

No test asserts the presence or exact content of `kind` in a generated node's repr. No snapshot tests pin the full repr string.

**Span.kind contrast:** `terminalsrc.Span` at `fltk/fegen/pyrt/terminalsrc.py:39` already uses `field(default=SpanKind.SPAN, repr=False, compare=False, hash=False)`. A test explicitly enforces this: `test_clean_protocol_consumer_api.py:806-810` — `assert "kind" not in repr(Span(1, 5))`. No analogous test enforces that generated struct nodes include `kind` in their repr.

**Rust backend node repr:** The Rust fixture `__repr__` for node types (e.g. `cst.rs:297-302`) explicitly omits `kind` — it formats only `span` and `children`:

```rust
fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
    let span_repr = self.span.bind(py).repr()?.to_string();
    let children_repr = self.children.bind(py).repr()?.to_string();
    Ok(format!("Config(span={span_repr}, children={children_repr})"))
}
```

**Cross-backend repr divergence exists today:** Python backend includes `kind=<NodeKind.X: N>` in repr; Rust backend omits it. No test enforces cross-backend repr equivalence for node types.

---

## Would `compare=False, repr=False` change observable behavior?

### `compare=False`

- Same-type equality: removes the singleton identity check on `kind` at the front of the field comparison sequence. Same result — `span` and `children` still differentiate. No behavioral change for correct usage.
- Cross-type equality: already dispatched by `__class__` check before any field comparison. No change.
- No test currently constructs two nodes of the same type with different `kind` values (this is only possible by passing `kind=NodeKind.OTHER` explicitly to the dataclass constructor — not a documented or tested pattern).

### `repr=False`

- `repr(Grammar())` would change from `Grammar(kind=<NodeKind.GRAMMAR: 1>, span=..., children=[])` to `Grammar(span=..., children=[])`.
- No test pins this output for generated node types. No snapshot.
- Would make Python backend repr consistent with current Rust backend repr (which already omits `kind`).
- This is an **observable surface change** for downstream consumers who parse or display repr output. CLAUDE.md classifies the generated repr surface as public API context for out-of-tree consumers; however, there is no explicit contract document stating `kind` must appear in repr. The Rust backend already provides a precedent for omission.

---

## Summary of factual findings

| Claim | Verdict |
|---|---|
| `kind` field participates in `__eq__` | True — compare=True by default |
| `kind` participates in `__hash__` | False — nodes are not hashable (`__hash__ = None`) |
| `kind` is invariant per node type | True — fixed singleton default, same for all instances |
| `kind` is the cross-type equality guard | False — `__class__` check comes first |
| `compare=False` changes any equality result | No — `__class__` guard is the real differentiator |
| `repr=False` changes any existing test | No — no test pins `kind` in node repr |
| Python and Rust backend reprs are already divergent | Yes — Rust backend already omits `kind` from node repr |
| TODO frames this as perf-only/defer | Correct per comment at `gsm2tree.py:223-224` |

The overhead is: one singleton identity check (`NodeKind.X is NodeKind.X`) per same-type equality call, before the `span` comparison. The comparison never evaluates `span` or `children` to determine the type — that's handled by `__class__`. The TODO's perf framing is accurate; correctness impact of `compare=False` is zero for any code that constructs nodes via the normal API.
