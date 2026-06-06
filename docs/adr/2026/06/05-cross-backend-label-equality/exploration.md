# Cross-Backend Label Equality — Exploration

**Date:** 2026-06-05  
**Goal:** Make generated CST `Label` enums compare (and hash) equal across backends when they denote the same grammar label, keyed on a stable canonical name, so that e.g. a Rust-backend node's label `== fltk_cst.Items.Label.NO_WS` (Python import) is `True`.

---

## 1. Python Label Generation

### Generator: `gsm2tree.py`

`CstGenerator.py_class_for_model` (`gsm2tree.py:109`) emits a nested `Label(enum.Enum)` class for every rule that has at least one labeled item:

```python
# gsm2tree.py:112-115
label_enum = pygen.klass(name="Label", bases=["enum.Enum"])
labels = sorted(model.labels.keys())
for label in labels:
    label_enum.body.append(pygen.stmt(f"{label.upper()} = enum.auto()"))
```

Values are `enum.auto()` — **ordinal integers assigned in sorted alphabetical order**. There is no stable canonical string baked in; the integer value reflects sort position within this particular enum class, not the label name.

### Generated output: `fltk_cst.py`

Example at `fltk_cst.py:174-179`:
```python
class Items:
    class Label(enum.Enum):
        ITEM = enum.auto()      # → 1
        NO_WS = enum.auto()     # → 2
        WS_ALLOWED = enum.auto()# → 3
        WS_REQUIRED = enum.auto()# → 4
```

### `__eq__` / `__hash__` source for Python labels

Python's `enum.Enum` provides identity-based `__eq__` (enum members are singletons; two references to the same member are `is`-equal and therefore `==`-equal). `__hash__` is derived from the member's value. There is no `__eq__` override in the generated code or in `enum.Enum` that would make cross-class comparisons work.

**Runtime proof:**
```
py_cst.Items.Label.NO_WS == rust_cst.Items.Label.NO_WS  → False
str(py_cst.Items.Label.NO_WS)  → "Label.NO_WS"          # no class prefix
repr(py_cst.Items.Label.NO_WS) → "<Label.NO_WS: 2>"
```

### `children_X` filter pattern (generated)

`gsm2tree.py:198-204` emits:
```python
f"return ({child_expr} for label, child in self.children"
f" if label == {class_name}.Label.{label.upper()})"
```
These comparisons use the Python `==` operator. When children were appended via `append_X`, the stored label object is exactly `ClassName.Label.X` from the module where the node was created. The `==` comparison is against the same singleton, so it works. Cross-backend equality would break these filters.

---

## 2. Rust Label Generation

### Generator: `gsm2tree_rs.py`

`RustCstGenerator._label_enum_block` (`gsm2tree_rs.py:135-177`) emits per rule:

```python
# gsm2tree_rs.py:151-160
lines.append("#[allow(non_camel_case_types)]")
lines.append(f'#[pyclass(eq, hash, frozen, name = "{enum_name}")]')
lines.append("#[derive(Clone, PartialEq, Eq, Hash)]")
lines.append(f"pub enum {enum_name} {{")
for label in labels:
    rust_variant = _rust_variant_name(label)
    python_name = _python_label_name(label)
    lines.append(f'    #[pyo3(name = "{python_name}")]')
    lines.append(f"    {rust_variant},")
lines.append("}")
```

- Rust enum name: `{ClassName}_Label` (e.g., `Items_Label`), but exposed to Python as that same string via `name = "Items_Label"`.
- Python-visible variant name: `ALL_CAPS` (e.g., `NO_WS`) via `#[pyo3(name = "NO_WS")]`.
- `#[pyclass(eq, hash, frozen)]` derives PyO3's `__eq__` and `__hash__` from Rust's `PartialEq` + `Hash` derive — **value-based comparison within the same Rust enum type**. Cross-type equality (Rust enum vs Python `enum.Enum`) is not possible under this scheme.

### The `__repr__` canonical-name string (already present)

`gsm2tree_rs.py:164-173` emits a `__repr__` block:
```python
lines.append("    fn __repr__(&self) -> &'static str {")
lines.append("        match self {")
for label in labels:
    rust_variant = _rust_variant_name(label)
    python_name = _python_label_name(label)
    lines.append(f'            {enum_name}::{rust_variant} => "{class_name}.Label.{python_name}",')
```

**This canonical string `"ClassName.Label.LABEL_NAME"` is exactly the stable key needed for cross-backend equality.** It is already present in `cst_generated.rs`:
- `cst_generated.rs:27`: `Items_Label::NoWs => "Items.Label.NO_WS"`
- `cst_generated.rs:244`: same pattern

**Runtime proof:**
```
repr(rust_cst.Items.Label.NO_WS) → "Items.Label.NO_WS"
rust_cst.Items.Label.NO_WS is rust_cst.Items.Label.NO_WS  → True  (singleton)
```

### Node's `Label` class-attribute

`gsm2tree_rs.py:247-255` (`_label_classattr`):
```rust
#[classattr]
#[allow(non_snake_case)]
fn Label(py: Python<'_>) -> PyResult<PyObject> {
    Ok(Items_Label::type_object(py).into_any().unbind())
}
```
`Node.Label` returns the **Rust enum type object** (not a Python module attribute). Accessing `RustNode.Label.NO_WS` returns a `Items_Label` Rust enum instance.

### Rust label filter in `children_X`

`gsm2tree_rs.py:344-360` emits:
```rust
let label_obj = Items_Label::NoWs.into_pyobject(py)?;
// ...
if tup.get_item(0)?.eq(&label_obj)? {
```

The Rust `children_X` methods call Python `__eq__` (`.eq()` on PyO3 objects invokes Python `==`). They create a local `label_obj` from their own backend's enum type for comparison. For cross-backend equality to work in these filters, the `==` comparison between a stored Python-backend label and a Rust-backend `label_obj` must return True.

---

## 3. Consumer Sites — Full Blast Radius

### Primary consumer: `fltk2gsm.py`

All 14 label comparisons via `self.cst.ClassName.Label.X` (where `self.cst` is a `CstModule` whose `Label` attributes may be from either backend):

| Line | Expression | Backend origin of LHS |
|------|-----------|----------------------|
| `fltk2gsm.py:52-56` | `labeled_children[0][0] in (self.cst.Items.Label.NO_WS, ...)` | Stored in children at parse time |
| `fltk2gsm.py:58` | `sep_label == self.cst.Items.Label.WS_REQUIRED` | From children |
| `fltk2gsm.py:60` | `sep_label == self.cst.Items.Label.WS_ALLOWED` | From children |
| `fltk2gsm.py:69` | `item_label == self.cst.Items.Label.ITEM` | From children |
| `fltk2gsm.py:71,73,76` | same separators | From children |
| `fltk2gsm.py:80` | `item_label == self.cst.Items.Label.ITEM` | From children |
| `fltk2gsm.py:122-126` | `label == self.cst.Disposition.Label.{INCLUDE,SUPPRESS,INLINE}` | From `disposition.child()` |
| `fltk2gsm.py:133-137` | `label == self.cst.Quantifier.Label.{ONE_OR_MORE,OPTIONAL,ZERO_OR_MORE}` | From `quantifier.child()` |

**Key insight:** The LHS label comes from `node.children[i][0]` (stored by the parser). The RHS label comes from `self.cst.ClassName.Label.X` (from the injected module). When the injected module is the Rust backend, both sides come from the Rust backend — so cross-backend equality is NOT required for `fltk2gsm.py` with `self.cst = fegen_rust_cst`. Cross-backend equality is only required when the *children were appended using one backend's labels* and *compared against the other backend's labels*.

### The `in (...)` membership test at `fltk2gsm.py:52-56`

```python
if labeled_children and labeled_children[0][0] in (
    self.cst.Items.Label.NO_WS,
    self.cst.Items.Label.WS_ALLOWED,
    self.cst.Items.Label.WS_REQUIRED,
):
```
This is a tuple membership test — calls `__eq__` on each element. Requires that `stored_label == self.cst.Items.Label.NO_WS` returns True when they denote the same grammar label. If stored labels are from Backend A and the `self.cst` tuple elements are from Backend B, this fails today.

### Generated `children_X` filters in Python CST (`fltk_cst.py`)

Every `children_X()` method uses `label == ClassName.Label.X`. These only see same-backend labels (the node was created by the Python parser and uses the Python module's labels), so they are unaffected.

### Generated `children_X` filters in Rust CST (`cst_generated.rs`)

`cst_generated.rs:123-137` — Rust `children_name()` does `.eq(&label_obj)?` where `label_obj` is `Identifier_Label::Name.into_pyobject(py)?`. Labels stored in Rust node children are also Rust enum instances. Same-backend comparison, unaffected.

### `bootstrap2gsm.py`

`bootstrap2gsm.py:38-56` — same pattern as `fltk2gsm.py` but against `cst.Items.Label.*` where `cst` is the bootstrap module (a Python module). No cross-backend comparison.

### Test sites

- `test_phase4_rust_fixture.py:278`: `assert label == Entry.Label.KEY` — Rust-backend label vs Rust-backend label (same-backend).
- `test_phase4_rust_fixture.py:283-293`: `test_ac8_label_equality` and `test_ac8_label_containment` — all same-backend comparisons (within `Operator.Label.*`).
- `test_phase4_rust_fixture.py:389-393`: `TestAC7BothBackends.test_label_equality_and_hash` — per-backend, not cross-backend. Tests `Operator.Label.ASSIGN == Operator.Label.ASSIGN` within each backend separately.
- `test_phase4_fegen_rust_backend.py:66-86`: `assert python_result == rust_result` — compares `gsm.Grammar` objects, not CST labels directly.

**No existing test checks cross-backend label equality.**

---

## 4. `isinstance(item, self.cst.Item)` — the isinstance constraint

`fltk2gsm.py:69`:
```python
assert item_label == self.cst.Items.Label.ITEM and isinstance(item, self.cst.Item)
```
`fltk2gsm.py:80`: same.

`self.cst.Item` is the class object from the injected module. `isinstance` with a Rust-backend class checks PyO3's native type hierarchy — it cannot be spoofed by `__eq__`. This means:

- When `self.cst = rust_module`: `isinstance(item, self.cst.Item)` checks `isinstance(item, RustItem)`. If `item` came from the Python backend, this would be `False`.
- **The label-equality problem and the isinstance problem are coupled**: if labels from backend A are stored in nodes, and `self.cst` is from backend B, both comparisons fail independently.

`__eq__`/`__hash__` on labels CANNOT fix `isinstance`. The design is constrained: cross-backend label equality is only meaningful when nodes AND their stored labels come from the SAME backend, but `self.cst` comparisons are against potentially different backend constants.

**The practical cross-backend scenario** (from `test_phase4_fegen_rust_backend.py`) is:
- Rust-backend parser produces Rust-backend nodes with Rust-backend labels in `children`.
- `Cst2Gsm` is initialized with `cst = rust_module`.
- `self.cst.Items.Label.NO_WS` is a Rust enum instance.
- The stored label in `labeled_children[0][0]` is also a Rust enum instance (same backend).
- Therefore: **currently, same-backend comparisons always work; the cross-backend equality goal is about a DIFFERENT scenario**.

The scenario requiring cross-backend equality: user code that holds a label from one backend (e.g., parsed a file with the Python backend) and then tests it against a constant from the other backend (e.g., `label == rust_cst.Items.Label.NO_WS`). This is the "drop-in goal" mentioned in the task.

---

## 5. Existing Tests Covering Label Equality / Backend Parity

| Test | File | What It Checks |
|------|------|----------------|
| `TestAC8RealCst2GsmRustBackend.test_simple_grammar_rust_equals_python` | `test_phase4_fegen_rust_backend.py:66` | gsm.Grammar equality (not label equality) |
| `TestAC5ApiContract.test_ac8_label_equality` | `test_phase4_rust_fixture.py:282` | Same-backend Rust label `==` |
| `TestAC5ApiContract.test_ac8_label_containment` | `test_phase4_rust_fixture.py:289` | Same-backend Rust `in (...)` |
| `TestAC5ApiContract.test_ac8_label_hashable` | `test_phase4_rust_fixture.py:295` | Same-backend Rust label in set/dict |
| `TestAC7BothBackends.test_label_equality_and_hash` | `test_phase4_rust_fixture.py:389` | Per-backend label equality (not cross) |

**Zero tests verify cross-backend label equality today.**

### Build targets (Makefile)

- `make build-native` — builds `fltk._native` (the main Rust extension including `fegen_cst`); uses `maturin develop` at repo root.
- `make build-test-user-ext` — builds `phase4_roundtrip_cst`; `maturin develop` in `tests/rust_cst_fixture/`.
- `make build-fegen-rust-cst` — builds `fegen_rust_cst`; `maturin develop` in `tests/rust_cst_fegen/`.

The three Rust CST modules are **separate cdylib crates** with separate `Cargo.toml`s. The fegen cst at `tests/rust_cst_fegen/src/cst.rs` is a copy of `src/cst_fegen.rs` with a TODO noting the duplication hazard (`tests/rust_cst_fegen/src/cst.rs:1`: `TODO(fegen-cst-rs-single-source)`).

---

## 6. The Equality Problem — Precise Formulation

**Current state:**
- Python `Label` = `enum.Enum` subclass; members have integer values from `auto()`; `__eq__` is identity within the enum class.
- Rust `{ClassName}_Label` = PyO3 frozen enum with `#[pyclass(eq, hash, frozen)]`; `__eq__` is value-based within the Rust type; `__hash__` is derived.
- `repr(rust_label)` already contains `"ClassName.Label.LABEL_NAME"` — a stable canonical key.
- `str(python_label)` = `"Label.LABEL_NAME"` (missing class prefix).

**Cross-backend comparison today:**
```python
py_cst.Items.Label.NO_WS == rust_cst.Items.Label.NO_WS  → False
```
Because: Python `enum.Enum.__eq__` compares by identity/class membership; the Rust label is not an instance of `py_cst.Items.Label`.

**For cross-backend equality to work, one or both sides must delegate to a canonical-name comparison.** The `__repr__` string `"Items.Label.NO_WS"` is already the stable name; it is emitted by the Rust generator at `gsm2tree_rs.py:170-172` and baked into `cst_generated.rs:27,244`.

**The Python side canonical name:** The generator emits `{class_name}.Label.{label.upper()}` in `__repr__`-like contexts only implicitly (via `enum.Enum` default repr). The generator would need to add a `canonical_name` property or override `__eq__`/`__hash__` to return a string-keyed result.

**The Rust side:** A `__richcmp__` override could be added to the `#[pymethods]` block for `{ClassName}_Label` enums. Currently `#[pyclass(eq, hash, frozen)]` handles `__eq__` and `__hash__` via Rust `PartialEq`/`Hash`. A custom `__richcmp__` would shadow or supplement this.

However: PyO3 `#[pyclass(eq, hash, frozen)]` with `#[derive(PartialEq, Eq, Hash)]` already provides value-based eq/hash within the Rust type. Adding cross-type equality via `__richcmp__` means the Rust enum's `__eq__` would need to accept Python `enum.Enum` instances and compare by canonical name string — requiring Python calls from Rust.

---

## 7. Open Factual Questions

1. **Scope of cross-backend equality requirement:** Is the goal that `rust_label == py_label` (Rust enum == Python enum), or only `py_label == rust_label` (Python enum == Rust enum, where Python drives)? The `in (...)` check at `fltk2gsm.py:52` compares `stored_label in (self.cst.Items.Label.NO_WS, ...)`. If `stored_label` is a Rust instance and the tuple contains Rust instances, it works today. The only scenario requiring cross-type equality is when a stored label from one backend is compared against a constant from the other.

2. **Does the drop-in goal actually arise in practice?** The `fltk2gsm.py` injection pattern (`self.cst = backend_module`) ensures both stored labels and comparison constants come from the same module. The cross-backend scenario arises only if user code or tests explicitly mix backends.

3. **Protocol `Label` class:** The Protocol's `Label` nested class (`fltk_cst_protocol.py:10-11`, `gsm2tree.py:354-361`) uses `typing.ClassVar[object]` — opaque; no equality contract is specified. The Protocol does not currently assert anything about cross-backend label equality.

4. **`fltk._native.fegen_cst` vs `fegen_rust_cst`:** These are two separate built modules (`src/cst_fegen.rs` compiled into `fltk._native`; `tests/rust_cst_fegen/src/cst.rs` compiled into `fegen_rust_cst`). Their label types are **different Python types** even though they represent the same grammar — `fltk._native.fegen_cst.Items.Label.NO_WS` and `fegen_rust_cst.Items.Label.NO_WS` are instances of different Rust enum types. Cross-backend equality spans this gap too.
