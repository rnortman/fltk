# Phase 2: Nested Enum PoC — Requirements

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

---

## Goals

Validate two unproven PyO3 patterns — the `#[classattr]` nested-enum workaround and `Py<PyList>` mutation semantics — by hand-writing two Rust CST node classes (`Identifier` and `Items`) and exercising them from Python. This is a standalone proof-of-concept; these nodes are not wired into the production CST pipeline.

---

## In Scope

- Two Rust `#[pyclass]` structs: `Identifier` (one label, one child type) and `Items` (four labels, heterogeneous child types).
- Two Rust `#[pyclass(eq, hash, frozen)]` enums: `Identifier_Label` and `Items_Label`.
- `#[classattr] fn Label()` on each node struct returning the corresponding label enum type, so `Identifier.Label.NAME` and `Items.Label.ITEM` etc. work from Python.
- `children` field stored as `Py<PyList>`, exposed via `#[pyo3(get)]`.
- `span` field stored as `PyObject`, exposed via `#[pyo3(get, set)]`.
- Full method surface per label: `append_<label>`, `extend_<label>`, `children_<label>`, `child_<label>`, `maybe_<label>`.
- Generic methods: `append`, `extend`, `child`.
- `__eq__` (comparing `span` and `children`), `__repr__`, and `__hash__` set to raise `TypeError` (unhashable, matching Python dataclass with `eq=True` and no `frozen=True`).
- Registration of all four types in the `fltk._native` module.
- A focused Python test file exercising all acceptance criteria below.

## Out of Scope

- Wiring these nodes into `fltk_cst.py`, `fltk_parser.py`, or any production code path.
- Code generation (`gsm2tree_rs.py`) — that is Phase 3.
- Any changes to existing Python CST classes.
- Modifying the Rust `Span` to expose `.start`/`.end` attributes (known TODO, separate concern).
- Type stubs (`.pyi`) for the Rust classes.
- Performance benchmarking.

---

## System Behavior

### Construction

- `Identifier(span=some_span)` creates an instance with the given span and an empty `children` list.
- `Identifier()` creates an instance with `UnknownSpan` (from `fltk._native`) as the default span and an empty `children` list.
- Same patterns for `Items`.

### Span field

- `node.span` returns the current span object.
- `node.span = new_span` replaces the span object. The span field accepts any Python object (stored as `PyObject`).

### Children field

- `node.children` returns the **same Python list object** on every access (not a copy). This is the critical `Py<PyList>` semantic: mutations via the returned reference persist on the node.
- Each element in the list is a 2-tuple `(label_or_none, child)`.

### Label enum attachment

- `Identifier.Label` is the type object `Identifier_Label`.
- `Identifier.Label.NAME` is an instance of `Identifier_Label`.
- `Items.Label` is the type object `Items_Label`.
- `Items.Label.ITEM`, `Items.Label.NO_WS`, `Items.Label.WS_ALLOWED`, `Items.Label.WS_REQUIRED` are instances of `Items_Label`.

### Label enum semantics

- Same-variant equality: `Identifier.Label.NAME == Identifier.Label.NAME` is `True`.
- Intra-class discrimination: `Items.Label.ITEM != Items.Label.NO_WS` is `True`.
- Inter-class discrimination: `Identifier.Label.NAME != Items.Label.ITEM` is `True`. (Different Python types; `__eq__` between unrelated types returns `NotImplemented` or `False`.)
- Cross-type `__eq__` (e.g., `Identifier.Label.NAME == Items.Label.ITEM`) may return `False` or `NotImplemented`; both are acceptable as long as `!=` returns `True`.
- Hash: label enum instances are hashable (required for dict keys and `in` membership on sets/dicts; tuple `in` uses `__eq__` only but the broader contract requires hashability since Python `enum.Enum` members are hashable).
- `repr(Identifier.Label.NAME)` produces an informative string (exact format not constrained, but must include the class name and variant name for debuggability).

### Generic methods

- `node.append(child, label=None)` appends `(label, child)` as a Python 2-tuple to `node.children`.
- `node.extend(children, label=None)` appends `(label, child)` for each `child` in the iterable.
- `node.child()` returns the single element of `node.children` — a `(label, child)` 2-tuple — if `len(node.children) == 1`, otherwise raises `ValueError` with message matching `"Expected one child but have {n}"`.
- `append(child, label=None)` and `extend(children, label=None)` — both parameters are positional-or-keyword (not keyword-only).

### Per-label methods (`Identifier`: label `name`)

- `node.append_name(child)` appends `(Identifier.Label.NAME, child)` to `node.children`.
- `node.extend_name(children)` appends `(Identifier.Label.NAME, child)` for each child.
- `node.children_name()` returns an iterable (list is acceptable) of children where the label is `Identifier.Label.NAME`, yielding only the child values (not the tuples).
- `node.child_name()` returns the single matching child, or raises `ValueError("Expected one name child but have {n}")`.
- `node.maybe_name()` returns the single matching child or `None`, or raises `ValueError("Expected at most one name child but have {n}")` if more than one.

### Per-label methods (`Items`: labels `item`, `no_ws`, `ws_allowed`, `ws_required`)

Same five-method pattern for each label, with the label name substituted into the method name and error message. Label constants used are `Items.Label.ITEM`, `Items.Label.NO_WS`, `Items.Label.WS_ALLOWED`, `Items.Label.WS_REQUIRED` respectively. The `extend` and `extend_<label>` methods accept any Python iterable, not only lists.

### Equality

- `node1 == node2` compares `span` (via Python `==`) and `children` (via Python list `==`, which recursively compares tuple elements). Returns `True` only if both match.
- `node1 != node2` is the negation.
- Comparison with non-node types returns `NotImplemented` (standard Python convention).

### Hashability

- `hash(node)` raises `TypeError`. CST nodes are mutable (children list is mutable) and must not be hashable, matching the Python dataclass contract (`eq=True` without `frozen=True` sets `__hash__ = None`).

### Repr

- `repr(node)` returns a string containing the class name, span, and children. Exact format is not constrained but must be informative for debugging. No test should assert exact repr format.

### isinstance

- `isinstance(node, Identifier)` returns `True` for `Identifier` instances, `False` for `Items` instances, and vice versa. Standard PyO3 `#[pyclass]` behavior.

---

## User-Visible Surface

### Module registration

All four types are added to `fltk._native`:
- `fltk._native.Identifier`
- `fltk._native.Identifier_Label`
- `fltk._native.Items`
- `fltk._native.Items_Label`

The label types must be module-level registrations (via `m.add_class::<T>()`) so they exist as Python type objects that `#[classattr]` can reference.

### Test file

New test file `tests/test_rust_cst_poc.py`. Uses `pytest.importorskip("fltk._native")` to skip gracefully when the Rust extension is not built.

### No CLI changes, no config changes, no environment variables.

---

## Acceptance Criteria

All of the following must pass in the test suite. Each criterion is independently testable.

1. **Label identity/equality**: `Identifier.Label.NAME == Identifier.Label.NAME` is `True`.
2. **Label containment**: `Identifier.Label.NAME in (Identifier.Label.NAME,)` is `True`.
3. **Intra-class label discrimination**: `Items.Label.ITEM != Items.Label.NO_WS` is `True`.
4. **Inter-class label discrimination**: `Identifier.Label.NAME != Items.Label.ITEM` is `True`.
5. **Label hashability**: `hash(Identifier.Label.NAME)` does not raise. `{Identifier.Label.NAME: 1}` works.
6. **Children is a live Python list**: Holding two references: `a = node.children; b = node.children; assert a is b` — same object on repeated access.
7. **Children mutation visibility**: `node.children.append(x)` is visible on subsequent `node.children` access (and via `len(node.children)`).
8. **Cross-node children extend**: Given two nodes `a` and `b` with children, `a.children.extend(b.children)` mutates `a`'s backing list and is visible via `a.children`.
9. **Children tuple structure**: After `node.append_name(span)`, `node.children[0]` is a 2-tuple `(Identifier.Label.NAME, span)`.
10. **append_name works**: `node.append_name(span)` adds the child; `node.child_name()` returns `span`.
11. **extend_name works**: `node.extend_name([s1, s2])` adds two children; `list(node.children_name())` returns `[s1, s2]`.
12. **child_name raises on wrong count**: `child_name()` on an empty node raises `ValueError`.
13. **maybe_name returns None on empty**: `maybe_name()` on an empty node returns `None`.
14. **maybe_name returns child on one**: After one `append_name`, `maybe_name()` returns the child.
15. **maybe_name raises on multiple**: After two `append_name` calls, `maybe_name()` raises `ValueError`.
16. **Generic append with label=None**: `node.append(child)` stores `(None, child)` in children.
17. **Generic append with explicit label**: `node.append(child, label=Identifier.Label.NAME)` stores `(Identifier.Label.NAME, child)`.
18. **Generic extend**: `node.extend([c1, c2], label=Identifier.Label.NAME)` appends two labeled tuples.
19. **Generic child()**: With exactly one child, returns the `(label, child)` tuple. With zero or more than one, raises `ValueError`.
20. **isinstance**: `isinstance(Identifier(...), Identifier)` is `True`. `isinstance(Identifier(...), Items)` is `False`.
21. **Span setter**: `node.span = new_span` followed by `node.span` returns `new_span`.
22. **Span default**: `Identifier()` (no args) has `node.span` equal to `fltk._native.UnknownSpan`.
23. **Equality**: Two nodes with the same span and same children are `==`. Two nodes with different children are `!=`.
24. **Node unhashability**: `hash(node)` raises `TypeError`.
25. **Items multi-label methods**: For each of `item`, `no_ws`, `ws_allowed`, `ws_required`: `append_<label>`, `extend_<label>`, `children_<label>`, `child_<label>`, `maybe_<label>` work correctly with the corresponding `Items.Label.<LABEL>` constant.
26. **Repr**: `repr(node)` returns a non-empty string containing the class name (e.g., `"Identifier"` substring).
27. **None-label filtering**: After `node.append(child_a)` (unlabeled) followed by `node.append_name(child_b)`, `list(node.children_name())` returns `[child_b]` only — the unlabeled child is excluded.

---

## Constraints

- **Backward compatibility**: No changes to existing Rust code (`src/span.rs`) or Python code. All existing tests must continue to pass.
- **Build**: `uv run --group dev maturin develop` must succeed. `uv run pytest` must pass all tests (existing + new).
- **Label enum naming**: Rust types use `<NodeName>_Label` naming (e.g., `Identifier_Label`). This is an internal name; Python consumers access them as `<NodeName>.Label` via the `#[classattr]` attachment. The underscore name is visible only if importing directly from `fltk._native`.
- **children_<label>() return type**: Returns a Python list (not a generator/iterator). This is a deliberate simplification from the Python CST (which returns a generator). All production call sites work with both (they iterate or call `list()` on the result). No production code checks `isinstance(result, types.GeneratorType)`.
- **Error messages**: `ValueError` messages from `child()`, `child_<label>()`, and `maybe_<label>()` must follow the pattern used by the Python CST classes (e.g., `"Expected one name child but have 0"`).

---

## Open Questions

### `OQ-classattr-type-return`

The exact PyO3 0.23 return type for `#[classattr] fn Label()` that returns a type object is unverified in this codebase. The exploration proposes `fn Label(py: Python<'_>) -> PyResult<Py<PyType>>` using `Identifier_Label::type_object(py)`. If this doesn't compile under PyO3 0.23's `abi3-py310`, alternatives include returning a `PyObject` wrapping the type, or using `Bound<'_, PyType>`. This is an implementation question that will be resolved empirically during coding. If none of the `#[classattr]` approaches work, the fallback (per phase-plan.md R1 mitigation) is module-level label classes with re-export aliases, which would change the module registration surface but not the Python-facing API.

### `OQ-none-label-eq`

When `children` contains `(None, child)` tuples (from generic `append` with no label), the filter `label == NodeClass.Label.FOO` must evaluate to `False` when `label` is Python `None`. PyO3 `#[pyclass(eq)]` enums: if `__eq__` receives a `None` argument, it should return `NotImplemented` (or `False`), not panic. The exploration flags this as needing empirical verification. If PyO3's derived `__eq__` panics on non-enum comparands, a custom `__richcmp__` implementation is needed instead of the derived one.

### ~~`OQ-extend-iterable`~~ (resolved)

Resolved: The `extend` and `extend_<label>` methods accept any Python iterable, not only lists. This is consistent with the system-behavior section ("for each `child` in the iterable") and the Python CST's `typing.Iterable` annotation.
