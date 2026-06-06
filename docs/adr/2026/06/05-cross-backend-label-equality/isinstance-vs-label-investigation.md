# isinstance-vs-label Investigation

**Question**: Can ALL `isinstance` call sites on a CST node be replaced with a label check?
**Context**: Removing `self.cst` from `fltk2gsm.py`; the blocking pattern is `isinstance(item, self.cst.Item)`.

---

## 1. IN-TREE INVENTORY

### fltk2gsm.py — the two blocking sites

```python
# fltk2gsm.py:69
assert item_label == self.cst.Items.Label.ITEM and isinstance(item, self.cst.Item)

# fltk2gsm.py:80
assert item_label == self.cst.Items.Label.ITEM and isinstance(item, self.cst.Item)
```

Both are in `visit_items` iterating over `items.children` (a `list[tuple[Label | None, child_union]]`).
The assertion is checking both the label AND the type simultaneously.

**Label sufficiency**: `Items.Label.ITEM` maps to exactly one type (`Item`) in the generated CST.
From `fltk_cst.py:173-210`: `Items` has labels `ITEM`, `NO_WS`, `WS_ALLOWED`, `WS_REQUIRED`.
Label `ITEM` is only ever appended via `append_item(child: "Item")` (fltk_cst.py:203-204),
so `label == Items.Label.ITEM` ↔ `isinstance(child, Item)` is a total equivalence.
The `isinstance` adds zero information beyond the label check here.

**Verdict for these sites**: The `isinstance` is pure defensive redundancy. Drop it; keep only the label check.

### bootstrap2gsm.py — identical pattern

```python
# bootstrap2gsm.py:47
assert item_label == cst.Items.Label.ITEM and isinstance(item, cst.Item)

# bootstrap2gsm.py:56
assert item_label == cst.Items.Label.ITEM and isinstance(item, cst.Item)
```

Same analysis as fltk2gsm.py. The bootstrap CST (`bootstrap_cst`) is a concrete module bound at import time — no backend indirection — so there was never a real need for `isinstance` here either.

### fltk2gsm.py / bootstrap2gsm.py — gsm.Identifier / Sequence checks

```python
# fltk2gsm.py:92, bootstrap2gsm.py:66
if label is None and isinstance(term, gsm.Identifier):

# fltk2gsm.py:97, bootstrap2gsm.py:71
if label or isinstance(term, Sequence):
```

These `isinstance` calls are on **GSM model objects** (`gsm.Identifier`, `gsm.Items` as a `Sequence`),
not on CST nodes. The GSM is a plain Python dataclass hierarchy — no label structure. These are
**not candidates for label replacement** and are completely orthogonal to the question.

### gsm2tree.py — GSM object dispatch

```python
# gsm2tree.py:64
if isinstance(item.term, list):  # Sub-expression is a list of Items

# gsm2tree.py:247, 252, 254, 263, 266, 268, 275
isinstance(item.term, gsm.Identifier), isinstance(item.term, gsm.Literal | gsm.Regex), etc.
```

All on `gsm.Item.term` (a union of `gsm.Identifier | gsm.Literal | gsm.Regex | list[gsm.Items]`).
These are GSM model dispatches, not CST node dispatches. Not relevant.

### gsm2parser.py:727

```python
assert isinstance(item_if.orelse, iir.Block)
```

On an IIR node, not a CST node. Not relevant.

### tests/test_rust_cst_poc.py:181-199

```python
assert isinstance(node, Identifier)
assert not isinstance(node, Items)
```

These are **acceptance criteria** verifying that the Rust backend supports `isinstance`.
They are tests of the isinstance contract itself, not consumers that could be changed.

---

## 2. LABEL-VS-TYPE SEMANTICS

### How the mapping is established

`gsm2tree.py:274-276` records labels for non-suppressed, non-inline items:
```python
if item.label:
    assert not isinstance(item.term, Sequence)
    model.labels[item.label] |= item_model.types
```

So `model.labels[label]` = the set of CST types that appear under that label.

For a **single-alternative rule with a single non-union identifier under a label**, the mapping
`label → concrete type` is 1:1 and total.

### Where one label can map to multiple types (union children)

`ItemsModel.labels` is `MutableMapping[str, set[ModelType]]`. The set accumulates types across
alternatives of the same label name. A grammar rule with two alternatives like:

```
foo := bar:baz | quux:baz
```

where `bar` and `quux` are different rules both labelled `baz` would produce
`model.labels["baz"] = {"bar", "quux"}`, generating
`children_baz() -> Iterator[Union[Bar, Quux]]`. In this case, the label alone cannot distinguish
`Bar` from `Quux` — `isinstance` would still be needed to differentiate within that union.

**In the current fltk grammar**: the `Items.ITEM` label has exactly one type (`Item`), so the
union case does not arise at the blocker sites in fltk2gsm.py.

### Trivia: the label=None case

Trivia nodes are inserted by the parser as separators between semantic children
(gsm2parser.py:584-610). They are appended with `label=iir.LiteralNull()` — `label=None` at
runtime. This means any `children` list can contain `(None, Trivia(...))` entries alongside
`(SomeLabel.X, ConcreteNode(...))` entries.

A consumer iterating `.children` raw and trying to dispatch purely by label would see `None`
for trivia entries. `label is None` does NOT uniquely identify Trivia, because (a) label-free
nodes' children can also have `None` labels for unlabelled appends (gsm2parser.py:505:
`method = f"append_{item.label}" if item.label else "append"` — unlabelled semantic children
also use `label=None`), and (b) `Span` objects from regex/literal matches in trivia-capable
nodes share the same `None` label slot as Trivia nodes (gsm2tree.py:459-461).

**Conclusion on trivia**: A consumer iterating raw `.children` and seeing `label=None` cannot
tell whether it has a `Trivia` node or an unlabelled `Span` or an unlabelled semantic child
without `isinstance`. This is the only case in the CST where `isinstance` is not replaceable
by a label check — but the generated typed accessor methods (`children_<label>()`,
`children_rule()`, etc.) completely hide this: they filter by label and use `cast`, so callers
using the typed API never need to inspect `label=None` entries at all.

---

## 3. CONJECTURE: OUT-OF-TREE USE CASES

### Case A: holding a node without its parent tuple

A consumer receives a bare `node: SomeCstType` (e.g., as a function parameter, return value,
or after calling `child_name()` which returns the child without its label). To dispatch on
type, the consumer has no label available.

**Assessment**: This is a real pattern for visitors and unparsers that accept a node and must
determine which `visit_*` method to call. However, the typical dispatch pattern for generated
CST is:
- The parent's typed accessors (`child_term()`, `children_rule()`) return the node already
  typed via cast — the static type is known.
- If dispatch is truly dynamic, the consumer can call `node.__class__.__name__` or switch on
  the set of methods available (duck typing) rather than `isinstance`.
- Or the parent's `children_<label>()` accessor already filters, so the caller already knows
  the type statically.

**Obstacle level**: real but avoidable by using typed accessors rather than iterating raw
children. `isinstance` on bare nodes held outside parent context is not replaceable by a label
check, but the design pressure is to always access nodes through typed accessors.

### Case B: term discriminant in Term node (Alternatives | Identifier | Literal | RawString)

`Term.Label` has `ALTERNATIVES`, `IDENTIFIER`, `LITERAL`, `REGEX` (fltk_cst.py:438-442).
Each label maps to exactly one type. `term.maybe_alternatives()` / `term.maybe_identifier()`
etc. already encapsulate the label check. Any `isinstance(term, ...)` on `Term`'s children
can be replaced by the `maybe_*` accessors — this is exactly what `fltk2gsm.py:visit_term`
already does (lines 109-117).

### Case C: grammar-level root nodes

A `Grammar` node is the top-level parse result. It has no parent, so no label is available.
Code that checks `isinstance(result, Grammar)` (e.g., the test at
`tests/test_phase4_rust_fixture.py:319`) is performing a root-level type assertion. No label
is accessible.

**Obstacle level**: real. But these checks are either trivially avoidable (the parse result
type is statically known) or are tests of the isinstance contract itself.

### Case D: multi-backend visitor holding a Union[BackendA.Item, BackendB.Item]

If a visitor can receive items from either backend, and the backends' `Item` types are
structurally identical but nominally distinct, then `isinstance(node, BackendA.Item)` is the
only way to distinguish them in a mixed-backend scenario.

**Assessment**: This is the *exact scenario* the planned `__eq__` work aims to dissolve by
making labels cross-backend-equal so dispatch never needs to know the backend.

---

## 4. VERDICT

**Claim**: "Every isinstance on a CST node can be replaced by a label check."

**Verdict**: Holds for all in-tree call sites that matter to the `self.cst` removal goal,
with two caveats for general use:

1. **Label union children**: When a single label name covers multiple types across alternatives
   (e.g., `Union[Bar, Quux]` under label `baz`), a label check narrows to the union but
   `isinstance` is still needed to pick within it. This does not arise at the current blocker
   sites in fltk2gsm.py.

2. **label=None ambiguity in raw children iteration**: Trivia nodes and unlabelled semantic
   children both appear as `(None, child)` in the raw `.children` list. Distinguishing them
   requires `isinstance` — but only when iterating raw children. The typed accessor API
   (`children_<label>()`) fully encapsulates this; callers using typed accessors never see
   the ambiguity.

**For the immediate goal** (removing `self.cst` from fltk2gsm.py): the two blocking
`isinstance(item, self.cst.Item)` calls at fltk2gsm.py:69 and :80 are fully redundant with
the co-located label check `item_label == self.cst.Items.Label.ITEM`. They can be deleted.
The remaining `self.cst` usages in fltk2gsm.py are all label comparisons
(`self.cst.Items.Label.*`, `self.cst.Disposition.Label.*`, etc.) which become replaceable
once cross-backend label equality (`__eq__`) is in place.
