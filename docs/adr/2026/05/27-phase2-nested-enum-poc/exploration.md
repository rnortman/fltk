# Phase 2 Exploration: Nested Enum PoC — Rust CST Nodes

Concise. Precise. Token-dense. No fluff. Audience: smart human/LLM implementing Phase 2.

---

## 1. Existing Rust Infrastructure (Phase 0-1 Deliverables)

**`src/lib.rs`** (19 lines): `#[pymodule] fn _native(m: &Bound<'_, PyModule>)` exports `Span`, `SourceText`, and `UnknownSpan` sentinel. Module name in Python: `fltk._native` (`pyproject.toml:29: module-name = "fltk._native"`).

**`src/span.rs`** (247 lines): Two `#[pyclass]` types:
- `SourceText` (`#[pyclass(frozen)]`, line 22): wraps `Arc<SourceInner>` where `SourceInner { text: String }`. Constructor: `#[new] fn new(text: &str)`. No Python-visible attributes.
- `Span` (`#[pyclass(frozen, eq, hash)]`, line 56): fields `start: i64`, `end: i64`, `source: Option<Arc<SourceInner>>`. Fields are NOT exposed as `#[pyo3(get)]` — intentionally unexposed per design (tests/test_rust_span.py:63-68 confirm `s.start` raises `AttributeError`). Constructor: `#[new] fn new(start: i64, end: i64)`. Classmethod `with_source(start, end, source: &SourceText) -> Self`.

**Build**: `Cargo.toml` uses `pyo3 = { version = "0.23", features = ["abi3-py310"] }`. Maturin is the build backend (`pyproject.toml:2-3`). Build command: `uv run --group dev maturin develop`.

**Backend selector** (`fltk/fegen/pyrt/span.py`, 24 lines): Tries `from fltk._native import SourceText, Span, UnknownSpan`; falls back to `terminalsrc.Span` on `Exception`. `SourceText: type | None = None` default when Rust unavailable.

**Note:** The Rust `Span` does NOT expose `.start` and `.end` as Python attributes. The pure-Python `Span` (`terminalsrc.py`) does expose them. Production code that accesses `span.start`/`span.end` (e.g., `fltk2gsm.py:24`: `terminals[span.start : span.end]`) must use the Python `Span` or a future Rust `Span` with exposed attributes. Phase 2 Rust CST nodes will use whatever `Span` is active; this API divergence is a known TODO (`backend-with-source-signature`).

---

## 2. Target Python CST Classes to Match

### 2a. `Identifier` (`fltk_cst.py:754-795`)

Simplest case — one label, one child type (`Span` only):

```python
@dataclasses.dataclass
class Identifier:
    class Label(enum.Enum):
        NAME = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, "fltk.fegen.pyrt.terminalsrc.Span"]] = dataclasses.field(default_factory=list)
```

Methods: `append(child, label=None)`, `extend(children, label=None)`, `child()`,
`append_name(child)`, `extend_name(children)`, `children_name()`, `child_name()`, `maybe_name()`.

### 2b. `Items` (`fltk_cst.py:172-309`)

Four labels, mixed child types (`Item | Trivia | Span`):

```python
@dataclasses.dataclass
class Items:
    class Label(enum.Enum):
        ITEM = enum.auto()
        NO_WS = enum.auto()
        WS_ALLOWED = enum.auto()
        WS_REQUIRED = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Item", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]]] = ...
```

Methods: `append`, `extend`, `child` (generic) + per-label 5-method set for each of `item`, `no_ws`, `ws_allowed`, `ws_required`.

### 2c. Full method signatures (per label `FOO`, Python)

```python
def append_foo(self, child: ChildType) -> None:
    self.children.append((ClassName.Label.FOO, child))

def extend_foo(self, children: Iterable[ChildType]) -> None:
    self.children.extend((ClassName.Label.FOO, child) for child in children)

def children_foo(self) -> Iterator[ChildType]:
    return (cast(ChildType, child) for label, child in self.children if label == ClassName.Label.FOO)
    # Note: cast omitted if only one child type (e.g., Identifier)

def child_foo(self) -> ChildType:
    children = list(self.children_foo())
    if (n := len(children)) != 1:
        raise ValueError(f"Expected one foo child but have {n}")
    return children[0]

def maybe_foo(self) -> Optional[ChildType]:
    children = list(self.children_foo())
    if (n := len(children)) > 1:
        raise ValueError(f"Expected at most one foo child but have {n}")
    return children[0] if children else None
```

The `cast()` in `children_foo` is a Python runtime no-op but signals type. In Rust the return type is `PyObject` regardless; the cast pattern doesn't need replication but the filtering logic does.

### 2d. `__eq__` behavior (dataclass default)

Python dataclass auto-generates `__eq__` doing field-by-field comparison: `span` and `children`. `children` is a list of tuples; list equality recursively compares elements. CST `__eq__` is used in tests (`test_gsm2parser.py:74`): `assert item_parser(parser, 0) == EXPECT` where `EXPECT = ApplyResult(42, Span(0, 42))`. `ApplyResult` contains a `result` CST node; the comparison reaches into `.children`.

**No `__hash__`**: Python dataclasses with `eq=True` and no `frozen=True` set `__hash__ = None` (unhashable). No code hashes CST nodes. The Rust CST `__hash__` should be absent or raise `TypeError`, matching this contract.

### 2e. `__repr__` behavior (dataclass default)

`repr(Grammar(...))` → `"Grammar(span=Span(start=-1, end=-1), children=[])"`. Used in logging only. No test asserts the exact repr format for CST nodes (unlike Span). Format should be informative but exact match not required.

---

## 3. Label Enum Access Patterns — All Call Sites

Labels are accessed in three production files:

### `fltk2gsm.py` (all `Label.` uses, lines 36-60, 104-119)

```python
# Membership test with tuple (in operator):
items.children[0][0] in (cst.Items.Label.NO_WS, cst.Items.Label.WS_ALLOWED, cst.Items.Label.WS_REQUIRED)

# Equality comparison:
sep_label == cst.Items.Label.WS_REQUIRED
sep_label == cst.Items.Label.WS_ALLOWED
sep_label == cst.Items.Label.NO_WS       # in assert
item_label == cst.Items.Label.ITEM       # in assert

label == cst.Disposition.Label.INCLUDE
label == cst.Disposition.Label.SUPPRESS
label == cst.Disposition.Label.INLINE

label == cst.Quantifier.Label.ONE_OR_MORE
label == cst.Quantifier.Label.OPTIONAL
label == cst.Quantifier.Label.ZERO_OR_MORE
```

The `in (tuple,)` pattern requires `__eq__` AND `__hash__` on the label enum (Python `in` for tuples uses `__eq__`, not `__hash__`; but `__hash__` is needed for use as dict keys). Both must be implemented.

### `fltk_parser.py`

No direct `Label.` attribute accesses found in grep output. The parser uses typed methods (`append_rule`, `append_name`, etc.) which internally reference the label constants. The label constants are only accessed inside the CST class itself.

### `gsm2unparser.py` (generated unparser code)

The generated unparser emits label access as string interpolation at code-generation time (`gsm2unparser.py:303-308`): `f"{class_name}.Label.{expected_label.upper()}"`. This becomes `Grammar.Label.RULE`, `Items.Label.ITEM`, etc. in the generated source. The generated code does equality comparisons of `child_tuple[0]` against these labels.

### `fltk_cst.py` itself (inside methods)

Every `append_{label}` method hardcodes the label: `self.children.append((ClassName.Label.FOO, child))`. Every `children_{label}` method uses: `if label == ClassName.Label.FOO`. So the label enum must be accessible as `ClassName.Label.FOO` from within the Rust class methods as well — via the standalone enum type that gets attached as the `Label` class attribute.

---

## 4. `children` List — Exact Access Patterns in Production Code

The `children` field is `list[tuple[Label | None, ChildUnion]]`. Critical operations:

**Parser constructs** (`fltk_parser.py`):
- `result.children.extend(item0.result.children)` — 11 sites (lines 114, 224, 280, 300, 312, 317, 416, 517, 608, 1065, 1149). Returns list from one node, extends another's list.
- `result.append_name(child=item0.result)` — typed append (calls `self.children.append((Label.NAME, child))`).

**Consumer reads** (`fltk2gsm.py`):
- `items.children[0][0]` — index + inner-tuple index (line 36)
- `items.children[start_idx:]` — slice (line 51)
- `children[::2]`, `children[1::2]` — stride-2 slice (line 52). Result is a Python list that is then iterated with `zip`.
- `len(children)` — length (line 62)
- `label, value = child` — tuple unpacking from iteration
- `sep_label, _ = items.children[0]` — tuple unpacking from index

**Consequence for `Py<PyList>`**: `node.children` must return the SAME Python list object on each access (not a copy), because `result.children.extend(...)` mutates the returned list and expects the mutation to persist. Under PyO3 `#[pyo3(get)]` on a `Py<PyList>` field, the returned object is the actual Python list (refcount increment, not copy). Empirical validation of this is one of the two PoC goals.

**Tuple shape**: Each element is `(label_or_none, child)` — a 2-tuple. `label` is either a Label enum instance or `None` (for unlabeled children appended via generic `append(child, label=None)`). In Rust, tuples stored in the list are created as Python tuples via `PyTuple::new(py, [label_or_none, child])`.

---

## 5. PyO3 Nested Enum Workaround — Design

PyO3 does not support nested `#[pyclass]` definitions. The workaround: define the Label enum as a standalone top-level Rust struct/enum, then attach it as a class attribute using `#[classattr]`.

### Standalone enum registration

```rust
#[pyclass(eq, hash, frozen)]
#[derive(Clone, PartialEq, Eq, Hash)]
enum Identifier_Label {
    NAME,
}

#[pymethods]
impl Identifier_Label {
    fn __repr__(&self) -> &'static str {
        match self {
            Identifier_Label::NAME => "Identifier.Label.NAME",
        }
    }
}
```

### Attachment as class attribute

```rust
#[pymethods]
impl Identifier {
    #[classattr]
    fn Label(py: Python<'_>) -> PyResult<Py<PyType>> {
        // Return the Python type object for Identifier_Label
        Ok(Identifier_Label::type_object(py).into())
    }
}
```

Wait — `#[classattr]` returns a value that becomes the class attribute. If it returns `Py<PyType>`, then `Identifier.Label` would be the type object `Identifier_Label`. Then `Identifier.Label.NAME` accesses the `NAME` attribute on the class, which PyO3 exposes as a class attribute for `#[pyclass]` enums (`pyo3::types::PyType::getattr`). This gives `Identifier.Label.NAME` as an instance of `Identifier_Label`.

**What must work:**
- `Identifier.Label.NAME == Identifier.Label.NAME` → requires `__eq__` on `Identifier_Label`
- `label in (Identifier.Label.NAME,)` → requires `__eq__` on `Identifier_Label` (tuple `in` uses `==`)
- `Items.Label.ITEM != Items.Label.NO_WS` → inter-variant discrimination
- `Identifier.Label.NAME != Items.Label.NAME` → inter-class discrimination (same variant name, different class)

**Inter-class discrimination**: With standalone enums `Identifier_Label` and `Items_Label` as separate PyO3 types, `Identifier_Label::NAME != Items_Label::NAME` because they are different Python type instances. The `__eq__` in PyO3 for `#[pyclass(eq)]` enums compares both the type identity and the variant. This must be verified.

### Alternative if `#[classattr]` returning `Py<PyType>` is awkward

The `#[classattr]` attribute can return any `IntoPy<PyObject>`. An alternative: return a Python class that has `NAME = Identifier_Label::NAME` as an attribute. Or, register `Identifier_Label` in the module and let `#[classattr]` return the type. The key question: does `Identifier.Label.NAME` work when `Identifier.Label` is a class (type object) and `NAME` is a class-level attribute of that class?

In PyO3 `#[pyclass]` enums, enum variants are exposed as class attributes of the enum class. So `Identifier_Label.NAME` should be an instance of `Identifier_Label`. If `Identifier.Label` is the class `Identifier_Label` (a `PyType`), then `Identifier.Label.NAME` delegates to `Identifier_Label.NAME` which works.

---

## 6. `Py<PyList>` Children Strategy — Design Details

### Rust struct shape

```rust
#[pyclass]
struct Identifier {
    span: PyObject,             // holds a Span (Python or Rust); set via setter
    children: Py<PyList>,       // live Python list; never replaced, only mutated
}
```

### Construction

```rust
#[new]
fn new(py: Python<'_>, span: Option<PyObject>) -> PyResult<Self> {
    let span_obj = match span {
        Some(s) => s,
        None => {
            // import UnknownSpan from fltk._native or terminalsrc
            // or accept it as required arg
        }
    };
    Ok(Identifier {
        span: span_obj,
        children: PyList::empty_bound(py).unbind(),
    })
}
```

**Construction pattern in fltk_parser.py**: `fltk.fegen.fltk_cst.Grammar(span=Span(start=pos, end=-1))` — keyword arg `span`, no `children` arg. The `#[new]` must accept `span` as a keyword argument with default `UnknownSpan`.

### Span field setter

Parser pattern: `result.span = Span(start=result.span.start, end=pos)` — replaces the span object on the node (assignment, not mutation). Requires a setter (`#[pyo3(set)]` or explicit setter method). The `span` field should be exposed as `#[pyo3(get, set)]` accepting any `PyObject`.

**Note**: `result.span.start` — reading `.start` from the span after `result.span` access. With the Rust `Span` (Phase 1), `.start` is NOT exposed as a Python attribute. The parser uses `result.span.start` to reconstruct the span: `Span(start=result.span.start, end=pos)`. This means either (a) fltk_parser.py uses the Python Span (via terminalsrc), not the Rust Span, or (b) a future phase exposes `.start`/`.end` on the Rust Span. The current Phase 1 Rust Span does NOT expose `.start`/`.end` — this is a known design decision (tests/test_rust_span.py:63-68 test that attribute access raises `AttributeError`). The Phase 2 Rust CST nodes will accept whatever Span object is passed — either Python or Rust Span — stored as `PyObject`. The parser that constructs these nodes (`fltk_parser.py`) currently uses `terminalsrc.Span` (via `import fltk.fegen.fltk_cst` which imports `terminalsrc`), not the Rust Span.

### `append` method

```rust
fn append(&mut self, py: Python<'_>, child: PyObject, label: Option<PyObject>) -> PyResult<()> {
    let tup = PyTuple::new_bound(py, [label.map_or_else(|| py.None(), |l| l), child]);
    self.children.bind(py).append(tup)?;
    Ok(())
}
```

### `children_name` return type — Iterator vs Generator

Python `children_foo()` returns a **generator** (lazy iterator). Callers do:
- `for x in node.children_name()` — iteration
- `list(node.children_name())` — materialization (in `child_name`, `maybe_name`)

A PyO3 method can return a Python iterator by implementing `__iter__` + `__next__` on a separate `#[pyclass]` struct, or by collecting into a Python list and returning a list iterator. The simplest approach: collect into a `Vec<PyObject>` and return as a Python list (not a generator). This changes the type from `Iterator` to `list` but both support `for x in ...` and `list(...)`. No production code checks `isinstance(result, types.GeneratorType)`.

Alternatively, return a PyO3 iterator class that holds the full `children` list + a cursor. This preserves lazy semantics but adds complexity.

**Simplest correct approach**: `children_name` collects matching children into a `Vec<PyObject>` and returns as a Python list. `child_name` and `maybe_name` reuse `children_name` or inline the filter logic.

---

## 7. `__eq__` Implementation Constraint

`test_gsm2parser.py:72-74`:
```python
EXPECT = memo.ApplyResult(42, terminalsrc.Span(0, 42))
parser.consume_literal = mock.Mock(return_value=EXPECT)
assert item_parser(parser, 0) == EXPECT
```

`ApplyResult` is a dataclass with `pos` and `result` fields. In this test, `result` is a `Span` (not a CST node), so CST `__eq__` is not directly tested here. But deeper tests (e.g., nodes containing Span children) do rely on recursive equality through the `children` list.

For Phase 2 PoC, `__eq__` must compare `span` and `children`:
- `span` equality: delegate to Python `==` on the span PyObject.
- `children` equality: delegate to Python `==` on the `Py<PyList>` (Python list equality is recursive).

In Rust:
```rust
fn __eq__(&self, py: Python<'_>, other: &Self) -> PyResult<bool> {
    let span_eq = self.span.bind(py).eq(other.span.bind(py))?;
    if !span_eq { return Ok(false); }
    self.children.bind(py).eq(other.children.bind(py))
}
```

---

## 8. Test Patterns in Existing Test Suite

### Relevant test files

**`tests/test_rust_span.py`**: Validates Rust `Span` — positional/keyword construction, equality, hash, frozen attributes, `with_source`, `text()`, `merge`, `intersect`. Pattern: `pytest.importorskip("fltk._native")`, then import `Span, UnknownSpan, SourceText` directly. Use of `pytest.mark.skipif(not _rust_available, ...)` for conditional skips.

**`tests/test_native.py`**: Minimal smoke test — `from fltk._native import Span, UnknownSpan, SourceText; assert native.Span is not None`.

**`tests/test_span_protocol.py`**: Protocol conformance tests; pattern for testing both Python and Rust backends.

**`fltk/fegen/test_gsm2parser.py:70-74`**: `exec`-pattern for generated CST + parser, then `ApplyResult` equality assertion.

### Phase 2 test location suggestion

New file: `tests/test_rust_cst_poc.py`. Pattern:
```python
_native_module = pytest.importorskip("fltk._native", reason="Rust extension not available")
from fltk._native import Identifier, Identifier_Label, Items, Items_Label, Span
```

Note: whether the label types are importable as `Identifier_Label` depends on whether they are registered in the `_native` module. They must be registered to be usable as Python types.

### Minimum required assertions for Phase 2 done-when criteria

Per `phase-plan.md` Phase 2 scope:
1. `Identifier.Label.NAME == Identifier.Label.NAME` — identity/equality
2. `label in (Identifier.Label.NAME,)` — containment
3. `Items.Label.ITEM != Items.Label.NO_WS` — intra-class discrimination
4. `Identifier.Label.NAME != Items.Label.NAME` — inter-class discrimination (not explicitly stated in plan but required for correctness)
5. `node.children` returns a mutable Python list
6. `node.children[0]` returns a tuple `(label, child)`
7. `node.append_name(span)` works
8. `node.child_name()` returns the child
9. `isinstance(node, Identifier)` works
10. `node.span = Span(1, 2)` works (setter)
11. `result.children.extend(other.children)` mutates backing list (key mutation-visibility check)

---

## 9. Module Registration — `lib.rs` Changes Needed

Phase 2 adds `Identifier`, `Identifier_Label`, `Items`, `Items_Label` (and possibly `Items`'s child type stubs) to the `_native` module. Pattern from existing `lib.rs`:

```rust
#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Span>()?;
    m.add_class::<SourceText>()?;
    m.add("UnknownSpan", Py::new(m.py(), Span { start: -1, end: -1, source: None })?)?;
    // Phase 2 additions:
    m.add_class::<Identifier_Label>()?;
    m.add_class::<Identifier>()?;
    m.add_class::<Items_Label>()?;
    m.add_class::<Items>()?;
    Ok(())
}
```

Label enum types (`Identifier_Label`, `Items_Label`) must be registered in the module as top-level classes for two reasons:
1. They need to be accessible as Python type objects so `#[classattr]` can return a reference to them.
2. Phase 3's `register_classes` function needs to register them alongside node classes.

---

## 10. `Items` Children — Heterogeneous Child Types

`Items.children` contains three child types: `Item | Trivia | Span`. For Phase 2, `Item` and `Trivia` are not yet Rust-backed. The `children` list holds Python objects of any type — this is inherent to `Py<PyList>` with `PyObject` elements. Phase 2 Rust `Items` accepts any `PyObject` as a child, which is correct.

The typed `append_item(child)` method takes `child: PyObject` (no Rust-level type enforcement). Python callers still pass the right types. This is the same as the Python version which annotates but doesn't enforce at runtime.

---

## 11. `span` Field — Python vs Rust Span Interaction

**Current state**: `fltk_cst.py` imports `fltk.fegen.pyrt.terminalsrc` and uses `terminalsrc.Span` and `terminalsrc.UnknownSpan`. The Python Span exposes `.start` and `.end`. The Rust Span does NOT expose `.start` and `.end`.

**For Phase 2 Rust CST nodes**: The `span` field is stored as `PyObject`. The parser (`fltk_parser.py`) passes `Span(start=pos, end=-1)` where `Span` is `fltk.fegen.pyrt.terminalsrc.Span` (Python Span). The parser also reads `result.span.start` — this works only with the Python Span.

**Phase 2 is standalone validation**: Phase 2 Rust CST nodes are NOT wired into `fltk_cst.py` or used by `fltk_parser.py`. The PoC test constructs nodes directly with explicit `Span(...)` objects. No parser compatibility issue arises in Phase 2.

**Default span for `#[new]`**: The Python CST `Grammar(span=Span(start=pos, end=-1))` construction pattern requires `span` as a keyword arg. For the PoC, construct the `UnknownSpan` default by importing it: `fltk._native.UnknownSpan` at Rust initialization time, or take `span` as a required arg in the PoC. The cleaner approach for Phase 2: require `span` as a keyword arg in `#[new]` (matches how the parser always passes it). A `None` default that falls back to `UnknownSpan` from `fltk._native` is also possible but requires importing within the Rust module itself.

---

## 12. `gsm2tree.py` Logic to Replicate in Phase 3

Noted here because Phase 2 PoC must be consistent with what Phase 3 will generate.

**Label name transformation** (`gsm2tree.py:113-115`): `label.upper()` — label names are stored lowercase in `ItemsModel.labels` keys, uppercased for enum values. E.g., `"name"` → `Label.NAME`.

**Class name transformation** (`gsm2tree.py:46-47`): `"".join(part.capitalize() for part in rule_name.lower().split("_"))` — `"raw_string"` → `"RawString"`.

**`children_foo` cast** (`gsm2tree.py:194-197`): The `typing.cast(T, child)` is only emitted when `len(model.types) > 1` (multiple child types). For `Identifier` (one type: `Span`), no cast. For `Items` (three types: `Item | Trivia | Span`), cast is emitted. In Rust, this distinction doesn't matter (all children are `PyObject`), but the filtering predicate is the same.

**Trivia insertion** (`gsm2tree.py:296-303`): If a rule has whitespace separators AND a trivia rule is in the grammar, `"_trivia"` (mapped to class name `Trivia`) is added to `model.types`. This is why `Items.children` union includes `Trivia` — `items` rule uses `.`/`,`/`:` separators, all of which can have adjacent trivia. Phase 2 hand-written `Items` must include `Trivia` in its child union type annotation (as a string/comment only — Rust stores `PyObject`), matching this invariant.

---

## 13. Open Factual Questions

1. **`#[classattr]` returning `Py<PyType>` syntax in PyO3 0.23**: The exact Rust signature for returning a type object from `#[classattr]` is not in the repo. PyO3 docs show `fn Label() -> Py<SomeType>` for instance attrs. For returning the class itself (type object), the return type may be `&'static PyType` or `Py<PyType>`. Needs verification against PyO3 0.23 API.

2. **Inter-class label discrimination**: `Identifier_Label::NAME == Items_Label::NAME` — do PyO3 `#[pyclass(eq)]` enums compare by type identity as well as variant? If `__eq__` only compares the discriminant integer, two different enum types with the same variant would compare equal, breaking discrimination. Needs empirical verification.

3. **`children_name()` return type — list vs iterator**: If `child_name()` and `maybe_name()` call `children_name()` internally (as Python does), and `children_name()` returns a Python list, the list is materialized once and reused. If they inline the filter logic, no extra allocation. The PoC should pick one approach and verify the behavior is identical.

4. **`Identifier_Label` and `Items_Label` name collisions in `_native` module**: Both enums have a `NAME` variant (Identifier) and `ITEM` variant (Items). These are class-level attributes on the respective Python enum types, not module-level. No collision as long as each enum type is a distinct Python class object.

5. **`None` label in children**: The generic `append(child, label=None)` can insert `None` as the label. The `children_name()` filter `if label == ClassName.Label.FOO` correctly skips `None` because `None != ClassName.Label.FOO`. In Rust, the `None` Python object is compared via `__eq__` against the label enum instance — this will return `False` correctly as long as the enum's `__eq__` doesn't panic on non-enum comparands.
