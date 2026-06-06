# Label-free CST node follow-up: grounding facts

Concise. Precise. Token-dense. Source-anchored throughout.

---

## 1. `py_class_for_model` — zero-label case

**`Label` inner class** (`gsm2tree.py:202-212`):

```python
label_enum = pygen.klass(name="Label", bases=["enum.Enum"])
labels = sorted(model.labels.keys())
for label in labels:
    label_enum.body.append(pygen.stmt(f"{label.upper()} = enum.auto()"))
self._emit_cross_backend_eq_hash(label_enum)
klass.body.append(label_enum)
```

When `model.labels` is empty, `labels = []`, so no `enum.auto()` members are appended. `_emit_cross_backend_eq_hash` still appends `_fltk_canonical_name: str`, `__eq__`, and `__hash__` to the class body (`gsm2tree.py:100-132`). The result is an `enum.Enum` subclass with **zero value-members** but those three extra body items. It is an empty enum in the sense that `list(Label)` is `[]`, but it is not a bare `pass` body.

**`children` field annotation** (`gsm2tree.py:232`):

```python
pygen.stmt(
    f"children: list[tuple[typing.Optional[Label], {child_annotation}]]"
    " = dataclasses.field(default_factory=list)"
)
```

`child_annotation` is computed from `model.types` (`gsm2tree.py:219`). So the emitted annotation is always `list[tuple[typing.Optional[Label], <child_type>]]` regardless of whether `model.labels` is empty.

**Runtime label slot value**: The generic `append` method (`gsm2tree.py:241-247`) defaults `label` to `None` and stores `(label, child)`. No label-specific `append_<label>` helpers exist when `labels` is empty, so all children are appended via the generic path with `label=None`. Every tuple in `children` has `None` in position 0 at runtime.

---

## 2. `_protocol_class_for_model` — zero-label case

**Nested `Label` class**: NOT emitted. The guard at `gsm2tree.py:527-538` is:

```python
if labels:
    label_class = pygen.klass(name="Label")
    for label in labels:
        label_class.body.append(pygen.stmt(f"{label.upper()}: typing.ClassVar[object]"))
    klass.body.append(label_class)
```

When `labels = []`, this block is skipped entirely. No `Label` class appears in the Protocol.

**`children` annotation** (`gsm2tree.py:553-561`):

```python
if labels:
    klass.body.append(pygen.stmt(f"children: list[tuple[typing.Optional[Label], {child_annotation}]]"))
else:
    # TODO(cst-protocol-label-free): label-free nodes use tuple[None, T] rather than
    # tuple[Label | None, T], creating an asymmetry with label-bearing nodes.
    klass.body.append(pygen.stmt(f"children: list[tuple[None, {child_annotation}]]"))
```

Zero-label Protocol emits `children: list[tuple[None, T]]` — **not** `Optional[Label]` but a hard-coded `None` type. This is the asymmetry flagged by the existing TODO.

Similarly, `append`, `extend`, and `child` method signatures use `label: None = None` (via `label_annotation = "None"` at `gsm2tree.py:563`) rather than `label: typing.Optional[Label] = None`.

---

## 3. Can a zero-label node actually exist?

### Auto-labeling in `fltk2gsm.py` (`visit_item`, lines 94-103)

```python
label = self.visit_identifier(cst_label).value if (cst_label := item.maybe_label()) else None
if label is None and isinstance(term, gsm.Identifier):
    label = term.value

disposition = self.visit_disposition(cst_disposition) if (cst_disposition := item.maybe_disposition()) else None
if disposition is None:
    if label or isinstance(term, Sequence):
        disposition = gsm.Disposition.INCLUDE
    else:
        disposition = gsm.Disposition.SUPPRESS
```

Auto-labeling rules:
- A bare rule-reference (gsm.Identifier term, no explicit label) → `label = term.value` (the rule name). Since `label` is now truthy, default disposition becomes `INCLUDE`.
- A bare Literal/Regex term, no explicit label, no explicit disposition → `label = None`, `disposition = SUPPRESS`.
- An explicit `$` disposition on a Literal/Regex → `disposition = INCLUDE`, `label = None` (unless an explicit label is given).

### What `model_for_items` does with labels (`gsm2tree.py:364-382`)

```python
for item in items.items:
    if item.disposition == gsm.Disposition.SUPPRESS:
        continue
    if item.disposition == gsm.Disposition.INLINE:
        ...inline...
    else:
        item_model = self.model_for_item(item, inline_stack)
        model.incorporate(item_model)
        if item.label:
            model.labels[item.label] |= item_model.types
```

A non-suppressed item with `item.label = None` contributes to `model.types` but NOT to `model.labels`. This is the key path to a zero-label node.

### Minimal concrete example

Grammar rule:

```
foo := $"x" , $"y";
```

- Both items: Literal, explicit `$` disposition → `INCLUDE`, `label = None`.
- Both contribute to `model.types = {Span.key}` (each `$`-literal → `ItemsModel(types={Span.key})`).
- Neither contributes to `model.labels` because `item.label` is `None` for both.
- Result: `model.types = {Span.key}`, `model.labels = {}`.

This is a fully legitimate, non-empty node (two children, both `Span`s, no labels).

Guard at `gsm2tree.py:213-218` only raises if `model.types` is empty — it does NOT require `model.labels` to be non-empty:

```python
if not model.types:
    msg = (
        f"Model class `{class_name}` "
        "would have no members; ensure there is at least one term included in the model."
    )
    raise RuntimeError(msg)
```

**So: `foo := $"x" , $"y"` yields a real node class `Foo` with:**

Concrete (`py_class_for_model`):
```python
@dataclasses.dataclass
class Foo:
    class Label(enum.Enum):
        _fltk_canonical_name: str
        def __eq__(self, other): ...
        def __hash__(self): ...
    kind: typing.Literal[NodeKind.FOO] = NodeKind.FOO
    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[typing.Optional[Label], fltk.fegen.pyrt.terminalsrc.Span]] = dataclasses.field(default_factory=list)
    def append(self, child: fltk.fegen.pyrt.terminalsrc.Span, label: typing.Optional[Label] = None) -> None: ...
    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.terminalsrc.Span], label: typing.Optional[Label] = None) -> None: ...
    def child(self) -> tuple[typing.Optional[Label], fltk.fegen.pyrt.terminalsrc.Span]: ...
```

Protocol (`_protocol_class_for_model`):
```python
class Foo(typing.Protocol):
    # NO Label class
    kind: typing.Literal[NodeKind.FOO] = NodeKind.FOO
    span: fltk.fegen.pyrt.terminalsrc.Span
    children: list[tuple[None, fltk.fegen.pyrt.terminalsrc.Span]]
    def append(self, child: fltk.fegen.pyrt.terminalsrc.Span, label: None = None) -> None: ...
    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.terminalsrc.Span], label: None = None) -> None: ...
    def child(self) -> tuple[None, fltk.fegen.pyrt.terminalsrc.Span]: ...
```

### Other real-world paths to zero-label nodes

- A rule whose only non-suppressed items are all bare Literals/Regexes with explicit `$` and no labels.
- A rule mixing `$literal` with `!inlined_rule` where the inlined rule itself contributes no labels.
- A rule referencing another rule via `$other_rule` (explicit `$` overrides the auto-label): `item.label` remains `None` (the `$` sets disposition but does not set label; auto-label only fires when `isinstance(term, gsm.Identifier)` AND `label is None` AND no explicit label — but explicit `$` doesn't clear the auto-label step). Actually: the auto-label at `fltk2gsm.py:95-96` fires BEFORE disposition is set, so `label = term.value` if no explicit label — meaning `$rule_ref` still gets `label = rule_name` unless explicitly suppressed or given an explicit label. So bare `$rule_ref` is NOT a path to zero labels; it auto-labels.

The reliable zero-label path is **only Literal/Regex items with `$` disposition (no labels)**, because Identifiers always auto-label.

---

## 4. Empty-enum typing: `typing.Optional[Label]` when `Label` is empty

`typing.Optional[Label]` = `Label | None`. At the type-theory level these are two distinct nominal types: `Label` (empty enum, zero members) and `None`. Pyright does NOT reduce `EmptyEnum | None` to `None`. It treats `Label` as a valid (if uninhabited) type and keeps the union as two-part.

Practical consequence: pyright will accept `label: typing.Optional[Label] = None` as a valid annotation. `None` is a valid value because `None` satisfies the `None` arm. No `Label` value can exist at runtime, but pyright does not perform exhaustiveness reduction of empty enum types to `Never` (it lacks that inference for user-defined enums). So `Optional[Label]` is statically inhabited only by `None`, but the type is written as `Label | None`, not just `None`. Pyright sees a two-type union and will not flag `None` as the only assignable value.

**Asymmetry with Protocol**: The Protocol emits `label: None` (a hard literal `None` type), while the concrete class emits `label: typing.Optional[Label]` (a two-part union that is effectively `None`-only). These are structurally different annotations. The Protocol is stricter: it rules out any hypothetical `Label` value statically. The concrete class allows both — though only `None` is achievable at runtime. This mismatch means a value typed as the Protocol's `Foo` is NOT a structural subtype of the concrete `Foo` on the `append`/`extend` signature (contravariant parameter position), and vice versa. This is an existing known issue (the TODO at `gsm2tree.py:556-561`).
