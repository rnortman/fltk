# CST Node Interface — Facts for Rust/PyO3 Replacement

Concise. Precise. No preamble. Audience: engineer designing a Rust-backed CST via PyO3.

---

## 1. Generated Node Class Pattern

Every grammar rule produces one `@dataclasses.dataclass` class. There is **no shared base class** — all classes are independent dataclasses with identical structure by convention.

### Canonical structure (example: `fltk_cst.py:52-126`, `Rule`)

```python
@dataclasses.dataclass
class Rule:
    class Label(enum.Enum):          # nested enum, one member per labeled child kind
        ALTERNATIVES = enum.auto()
        NAME = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Alternatives", "Identifier", "Trivia"]]] \
        = dataclasses.field(default_factory=list)

    # --- generic mutation ---
    def append(self, child, label=None): ...
    def extend(self, children, label=None): ...
    def child(self) -> tuple[Label | None, ChildType]: ...   # asserts exactly 1 child

    # --- per-label typed accessors (one group per label) ---
    def append_alternatives(self, child: "Alternatives") -> None: ...
    def extend_alternatives(self, children: Iterable["Alternatives"]) -> None: ...
    def children_alternatives(self) -> Iterator["Alternatives"]: ...   # generator
    def child_alternatives(self) -> "Alternatives": ...               # asserts exactly 1
    def maybe_alternatives(self) -> Optional["Alternatives"]: ...     # asserts 0 or 1
```

`gsm2tree.py:109-243` is the generator that emits this pattern. Every label produces five methods: `append_<label>`, `extend_<label>`, `children_<label>`, `child_<label>`, `maybe_<label>`.

### Fields present on every node

| Field | Type | Default |
|---|---|---|
| `span` | `terminalsrc.Span` | `terminalsrc.UnknownSpan` (`Span(-1,-1)`) |
| `children` | `list[tuple[Label \| None, ChildUnion]]` | `[]` via `dataclasses.field(default_factory=list)` |

Source: `gsm2tree.py:124-132`.

---

## 2. No Base Class

CST nodes do **not** inherit from any shared base. They are plain dataclasses. There is no `CstNode`, `AstNode`, or similar. The only shared ancestry is `object`.

Confirmed by every class in `fltk_cst.py` and `bootstrap_cst.py`: all are `@dataclasses.dataclass` with no `(BaseClass)` in the class definition.

---

## 3. The Span Type

`fltk/fegen/pyrt/terminalsrc.py:7-15`:

```python
@dataclass(frozen=True, eq=True, slots=True)
class Span:
    start: int   # byte/char index, inclusive
    end: int     # byte/char index, exclusive: range [start, end)

UnknownSpan: Final = Span(-1, -1)
```

Key facts:
- `frozen=True` — immutable after construction, safe to use as dict key.
- `eq=True` — value equality by `(start, end)`.
- `slots=True` — no `__dict__`, fixed attribute layout.
- `UnknownSpan = Span(-1, -1)` is the sentinel default on every node.
- Text extraction: callers do `terminals[span.start : span.end]` (`bootstrap2gsm.py:24`, `fltk2gsm.py:24`).
- Span is also a **child type** — leaf terminals (literals, regexes, whitespace separators) are stored as `Span` objects directly in `children`, not wrapped in a node class.

---

## 4. Children List — Structure and Access

`children` is `list[tuple[Label | None, ChildUnion]]`. The tuple is always `(label, value)`.

- **Index 0** of the tuple: `Label` enum member or `None` (unlabeled, e.g. trivia whitespace `Span`s).
- **Index 1** of the tuple: the actual child object (another node class instance, or a `Span`).

### Enumerated label types per node

Generated in `gsm2tree.py:112-115` from `model.labels.keys()`, sorted alphabetically:
```python
label_enum = pygen.klass(name="Label", bases=["enum.Enum"])
for label in sorted(model.labels.keys()):
    label_enum.body.append(pygen.stmt(f"{label.upper()} = enum.auto()"))
```

Labels are always `ALL_CAPS` enum members; the label names come from the grammar's `label:term` syntax, lowercased in the grammar, uppercased in the enum.

### Child union type

`children` is annotated as `list[tuple[Label | None, Union[NodeA, NodeB, ..., Span]]]`. The union includes every possible child type across all alternatives and all labels. For leaf-only rules (e.g. `Identifier`, `Literal`, `Disposition`), the union is just `Span`.

### Direct children access

Callers directly index `node.children` as a list:
- `bootstrap2gsm.py:36`: `items.children[0][0]` — gets label of first child.
- `bootstrap2gsm.py:45`: `children = items.children[start_idx:]` — slice from index.
- `bootstrap2gsm.py:46`: `zip(children[::2], children[1::2], strict=False)` — stride-2 iteration.
- `test_trivia_capture.py:107`: `for child in root_node.children:` — plain iteration.
- `fltk2gsm.py:36-51`: same patterns as bootstrap2gsm.

Callers also call `len(node.children)` via `gsm2unparser.py:604-618` which generates `len(node.children)`.

---

## 5. Typed Accessor Methods

For each label `FOO`, four read methods are generated (`gsm2tree.py:189-242`):

### `children_foo() -> Iterator[T]`
Generator expression filtering `children` by label. Does **not** materialize a list.
```python
return (typing.cast(T, child) for label, child in self.children if label == NodeClass.Label.FOO)
```
If `len(model.types) == 1` (only one possible child type), `typing.cast` is omitted.

### `child_foo() -> T`
Asserts exactly one matching child, raises `ValueError` otherwise:
```python
children = list(self.children_foo())
if (n := len(children)) != 1:
    raise ValueError(f"Expected one foo child but have {n}")
return children[0]
```

### `maybe_foo() -> Optional[T]`
Asserts at most one matching child, raises `ValueError` if more than one, returns `None` if zero:
```python
children = list(self.children_foo())
if (n := len(children)) > 1:
    raise ValueError(f"Expected at most one foo child but have {n}")
return children[0] if children else None
```

### `append_foo(child: T) -> None` / `extend_foo(children: Iterable[T]) -> None`
Mutation methods used during parsing; not typically called by consumers.

### Generic `child() -> tuple[Label | None, ChildUnion]`
Returns `self.children[0]` asserting `len == 1`. Used heavily in visitor code to destructure a single-child node:
```python
label, _ = disposition.child()
if label == cst.Disposition.Label.INCLUDE: ...
```
(`bootstrap2gsm.py:95-103`)

---

## 6. Optional vs. Repeated Children

There is **no structural difference** between optional and repeated children at the storage level — both use the same `children` list. The distinction is purely in accessor semantics and how the parser populates it:

- **Optional child** (grammar `?`): at most one child with that label. Consumer calls `maybe_foo()` which returns `Optional[T]`.
- **Repeated child** (grammar `+` or `*`): zero or more children with that label. Consumer calls `children_foo()` which returns `Iterator[T]`.
- **Required single child** (grammar implicit `REQUIRED`): exactly one child with that label. Consumer calls `child_foo()`.

All patterns seen in production code (`fltk2gsm.py:65,73,77`):
```python
label = self.visit_identifier(cst_label).value if (cst_label := item.maybe_label()) else None
disposition = self.visit_disposition(cst_disposition) if (cst_disposition := item.maybe_disposition()) else None
quantifier = self.visit_quantifier(cst_quantifier) if (cst_quantifier := item.maybe_quantifier()) else gsm.REQUIRED
```
And repeated: `grammar.children_rule()` iterated with a list comprehension (`bootstrap2gsm.py:13`, `fltk2gsm.py:13`).

---

## 7. Python-Specific Features Used

### `@dataclasses.dataclass`
- Default `eq=True` — gives value equality based on `(span, children)` comparison. Dataclass `__eq__` compares all fields recursively. **Critical**: tests use `==` on `Span` objects (`test_gsm2parser.py:74`: `assert item_parser(parser, 0) == EXPECT`).
- Default `repr=True` — auto-generated `__repr__`. Used in logging (`test_trivia_capture.py:103`: `LOG.info("Root node children: %s", root_node.children)`).
- No `frozen=True` on node classes — they are mutable (parser appends children incrementally).
- No `__slots__` on node classes (only `Span` uses slots).

### `enum.Enum` nested class
- `Label` is a nested class inside each node class.
- Members: `FOO = enum.auto()`.
- Accessed as `NodeClass.Label.FOO` for both comparison and construction.
- `bootstrap2gsm.py:36-43`: labels compared with `in` and `==`: `items.children[0][0] in (cst.Items.Label.NO_WS, cst.Items.Label.WS)`.

### `typing.Union`, `typing.Optional`, `typing.Iterator`
- Used in annotations only; no runtime behavior. `Iterator` return from `children_foo()` is a plain generator expression, not a class instance.

### `typing.cast`
- `typing.cast(T, child)` is a no-op at runtime; used to satisfy type checkers in `children_<label>` methods when multiple child types exist.

### `dataclasses.field(default_factory=list)`
- Ensures each node instance gets its own fresh `children` list.

### No `__iter__`, no `__len__`, no `__getitem__`
- Node classes do **not** implement sequence protocols themselves. Callers iterate `node.children` directly, or call typed accessors.

---

## 8. How Tests and Consumers Interact With CST Nodes

### Visitor pattern (primary usage)
`bootstrap2gsm.py` and `fltk2gsm.py` are the canonical consumers. Pattern:
1. Receive a typed node as argument.
2. Call `child_<label>()` / `maybe_<label>()` / `children_<label>()` to extract typed children.
3. Recursively visit each child.
4. Access `Span.start` / `Span.end` to slice `terminals` string for text.

### Direct children list access (secondary usage)
When the full sequence matters (interleaved separators and items):
```python
# fltk2gsm.py:51-57
for (item_label, item), (sep_label, _) in zip(children[::2], children[1::2], strict=False):
    assert item_label == cst.Items.Label.ITEM and isinstance(item, cst.Item)
    gsm_items.append(self.visit_item(item))
    if sep_label == cst.Items.Label.WS_REQUIRED: ...
```
Callers inspect `children[i][0]` (label) and `isinstance(children[i][1], SomeClass)` for dispatch.

### Trivia test usage (`test_trivia_capture.py:107-115`)
```python
for child in root_node.children:
    label, value = child
    if "Trivia" in value.__class__.__name__:
        ...
        LOG.info("Found trivia node: %s with span: %s", value, value.span)
```
Accesses `.span` on a child node directly.

### Unparser generated code (`gsm2unparser.py:288-335`)
The unparser generator emits code that:
- Subscripts `node.children[pos]` directly: `child_tuple = node.children[pos]`.
- Gets `child_tuple[0]` (label) and `child_tuple[1]` (value).
- Checks `isinstance(child_value, SomeType)` for type dispatch.
- Calls `len(node.children)` for bounds.
- Accesses `node.children` as a field (`node_var.load().fld.children.load()`, `gsm2unparser.py:289`).

---

## 9. Span Text Extraction

Text is never stored in the CST; only byte positions are stored. All text recovery goes through:
```python
terminals[span.start : span.end]   # used in bootstrap2gsm.py:24, fltk2gsm.py:24
```
The unparser uses `fltk.unparse.pyrt.extract_span_text(span, terminals)` (`gsm2unparser.py:1459-1461`).

---

## 10. PyO3 / FFI Challenges

### Challenge: No base class, heterogeneous child union
The `children` list holds values of completely different Python types (`Span`, `Rule`, `Alternatives`, `Trivia`, etc.) — all in one `list[tuple[Label | None, Any]]`. PyO3 would need to store these as `PyObject` (boxed) and expose them as Python objects. The `typing.Union` in annotations is purely static.

### Challenge: Nested enum as inner class
`NodeClass.Label` is accessed as an attribute of the **class** (not an instance). PyO3 does not natively support nested classes. The `Label` enum must be accessible as `Rule.Label.NAME`. Options: expose as a standalone Python class and attach it as a class attribute, or replicate with a PyO3 `#[pyclass]` plus `#[classattr]`.

### Challenge: `dataclass` equality
Consumers compare nodes and spans with `==`. The `Span` dataclass has `eq=True` and `frozen=True`. A PyO3 replacement must implement `__eq__` / `__richcmp__` with value semantics.

### Challenge: `list[tuple[...]]` as mutable Python sequence
`children` is a plain Python `list`. Code directly indexes it (`children[0][0]`), slices it (`children[start_idx:]`), strides it (`children[::2]`), and calls `len()`. PyO3 can expose a `Vec` as a Python `list` via `IntoPy`, but the tuples inside must also be real Python tuples for the indexing patterns to work.

### Challenge: Iterator protocol from `children_<label>()`
The return value of `children_foo()` is a Python generator object. Callers wrap it with `list(node.children_foo())` or iterate it directly. PyO3 can return `impl Iterator` as a Python iterator class, but the `list()` call and `for x in node.children_foo()` both rely on the Python iterator protocol (`__iter__` / `__next__`).

### Challenge: `isinstance` checks
Consumer code calls `isinstance(child, cst.Item)` and `isinstance(child_value, SomeType)` heavily. PyO3 classes work transparently with `isinstance` when registered properly, but the type must be the same Python class object, not a Rust struct cast to a different class.

### Challenge: `repr` used in logs
`LOG.info("Root node children: %s", root_node.children)` relies on `__repr__` on nodes and `list.__repr__`. PyO3 classes need `__repr__` (`#[pyproto]` / `fn __repr__`).

### Challenge: `child()` returning a tuple
The generic `child()` method returns `tuple[Label | None, ChildUnion]` — a Python 2-tuple. PyO3 can return this as a `PyTuple` constructed from `(label_or_none, child_obj)`.

### Challenge: `maybe_<label>()` returning `None`
Returns `Optional[T]` — either a Python object or Python `None`. PyO3 maps this naturally to `Option<T>` with `IntoPyObject`.

### Challenge: `dataclass` `__repr__` exposes `children` and `span`
The default dataclass `__repr__` formats all fields. For a node with a large tree, this can be recursive and enormous. Current Python code implicitly relies on this for debugging (`LOG.info`). PyO3 should implement `__repr__` carefully.

### No `__iter__` on nodes (non-challenge)
Nodes themselves are **not** iterable — only `node.children` (a plain list) and the typed accessor generators are iterated. No `__iter__` protocol needed on the node class.

---

## 11. Code Surface Summary

| File | Role | Key items |
|---|---|---|
| `fltk/fegen/pyrt/terminalsrc.py` | Runtime: `Span` definition | `Span(start,end)`, `UnknownSpan`, `TerminalSource` |
| `fltk/fegen/fltk_cst.py` | Generated CST for full grammar | 12 node classes: `Grammar`, `Rule`, `Alternatives`, `Items`, `Item`, `Term`, `Disposition`, `Quantifier`, `Identifier`, `RawString`, `Literal`, `Trivia`, `LineComment`, `BlockComment` |
| `fltk/fegen/bootstrap_cst.py` | Generated CST for bootstrap grammar | Same pattern, slightly simpler; `Items.Label` has `WS` instead of `WS_ALLOWED`/`WS_REQUIRED` |
| `fltk/fegen/gsm2tree.py` | Generator for CST classes | `CstGenerator.gen_py_module()`, `py_class_for_model()`, `model_for_rule()` |
| `fltk/fegen/bootstrap2gsm.py` | CST consumer (visitor) | Primary example of `child_`, `maybe_`, `children_`, `.children[i][j]` usage |
| `fltk/fegen/fltk2gsm.py` | CST consumer (visitor) | Same pattern as bootstrap2gsm but for full grammar CST |
| `fltk/unparse/gsm2unparser.py` | Unparser generator | Shows how generated code accesses `node.children` by index/subscript |

---

## 12. Open Factual Questions

- No evidence of `__hash__` on node classes. Dataclasses with `eq=True` and no `frozen=True` set `__hash__ = None` (unhashable). Whether any consumer tries to hash nodes is unverified.
- The `Trivia` node in `fltk_cst.py` stores both sub-node types (`BlockComment`, `LineComment`) and raw `Span`s (for whitespace). Whether the trivia whitespace `Span` children always have `label == None` is asserted in `gsm2unparser.py:974-976` but may need verification against all grammar variants.
- `bootstrap_cst.py` items rule has `Label.WS` (single); `fltk_cst.py` has `Label.WS_ALLOWED` and `Label.WS_REQUIRED` (two). These are **different** CST schemas; any replacement must know which grammar it is serving.
