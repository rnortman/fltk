# Adversarial Validation: TODO(rust-generated-ident-collisions)

Concise. Precise. Token-dense. No fluff.

---

## Naming formulas for all Rust-side identifier families per rule

All are derived from `rule_name` via `naming.snake_to_upper_camel(rule_name)` → `CN` (the class name).

| Family | Rust identifier | Python-visible name | Emission site |
|---|---|---|---|
| Node data struct | `CN` | — | `gsm2tree_rs.py:731` `pub struct {class_name}` |
| Node handle pyclass | `PyCN` (`f"Py{class_name}"`) | `CN` (via `name = "CN"`) | `gsm2tree_rs.py:709,887` |
| Child value enum | `CNChild` (`f"{class_name}Child"`) | — | `gsm2tree_rs.py:537-543` `child_enum_name` |
| Label enum (Rust) | `CNLabel` (`f"{class_name}Label"`) | `CN_Label` | `gsm2tree_rs.py:454,458` `_label_enum_rust_name`/`_label_enum_python_name` |
| NodeKind variant | `CN` (variant of `NodeKind`) | `CN.upper()` e.g. `FOO` | `gsm2tree_rs.py:333-335` `_node_kind_variant_name` |
| DropWorklistItem variant | `CN` (variant of `DropWorklistItem`) | — | `gsm2tree_rs.py:1954-1956` |

All six families trace back to the same `class_name_for_rule_node` call at `gsm2tree.py:46-47`:
```python
def class_name_for_rule_node(self, rule_name: str) -> str:
    return naming.snake_to_upper_camel(rule_name)
```

`snake_to_upper_camel` formula (`naming.py:22`): `"".join(part.capitalize() for part in name.lower().split("_"))`.

---

## Complete pairwise collision classes

### Class 1: Rule `foo_child` collides with rule `foo`'s `CNChild` enum

- Rule `foo` → `CN = "Foo"` → child enum named `FooChild` (Rust type, module-level).
- Rule `foo_child` → `CN = "FooChild"` → data struct also named `FooChild`.
- `FooChild` (child enum for `Foo`) and `FooChild` (data struct for `foo_child`) are both emitted as `pub enum FooChild` and `pub struct FooChild` in the same module → Rust `E0428` (duplicate definition).

**Confirmed real.** `child_enum_name` at `gsm2tree_rs.py:537-543`:
```python
@staticmethod
def child_enum_name(class_name: str) -> str:
    return f"{class_name}Child"
```

### Class 2: Rule `foo_label` collides with rule `foo`'s label enum

- Rule `foo` → `CN = "Foo"` → Rust label enum `FooLabel`, Python-visible `Foo_Label`.
- Rule `foo_label` → `CN = "FooLabel"` → data struct `FooLabel`, handle `PyFooLabel`.
- `FooLabel` (label enum for `Foo`) and `FooLabel` (data struct for `foo_label`) are both module-level `pub` items → `E0428`.

**Confirmed real.** `_label_enum_rust_name` at `gsm2tree_rs.py:454`:
```python
return f"{class_name}Label"
```

### Class 3: Rule `py_foo` collides with handle for rule `foo`

- Rule `foo` → `CN = "Foo"` → handle struct `PyFoo`.
- Rule `py_foo` → `CN = "PyFoo"` → data struct `PyFoo`.
- `PyFoo` (handle for `foo`) and `PyFoo` (data struct for `py_foo`) both emitted → `E0428`.

**Confirmed real.** Handle name at `gsm2tree_rs.py:709`:
```python
py_handle = f"Py{class_name}"
```

### Class 4: Rule `node_kind` collides with the module-level `NodeKind` enum

- Rule `node_kind` → `CN = "NodeKind"` → data struct `NodeKind`.
- `NodeKind` enum is also emitted at module level.
- **Already detected at generation time** by `_RESERVED_CLASS_NAMES` at `gsm2tree_rs.py:36-41`.

### Class 5: Rule `drop_worklist_item` collides with `DropWorklistItem`

- Rule `drop_worklist_item` → `CN = "DropWorklistItem"` → data struct `DropWorklistItem`.
- `DropWorklistItem` enum is emitted at `gsm2tree_rs.py:1954`.
- **Not in `_RESERVED_CLASS_NAMES`** — undetected.

`_RESERVED_CLASS_NAMES` only covers `NodeKind`, `Span`, `Shared`, `CstError` (`gsm2tree_rs.py:36-41`). `DropWorklistItem` is absent.

### Class 6: Rule `foo_child` NodeKind variant collides with rule `foo`'s child enum

This is a name collision at the *variant* level, not the type level. Both `NodeKind::FooChild` and `FoosChild` enum are distinct items — no Rust compile error from this pairing alone, only from the struct/enum sharing the same top-level name as in Class 1.

---

## Rust compile errors that would result

All three undetected classes (1, 2, 3) produce `E0428` ("the name `X` is defined multiple times"). This is an opaque error from `cargo`'s perspective: the message names the duplicate identifier but does not connect it back to the grammar rule pair that caused it.

Class 5 (`DropWorklistItem`) produces `E0428` only when the grammar is large enough that the `DropWorklistItem` enum is emitted (i.e., there exists at least one rule with a node-typed child at `gsm2tree_rs.py:1944`).

---

## `_RESERVED_CLASS_NAMES` check — exact location and error

`gsm2tree_rs.py:36-41` defines the dict:
```python
_RESERVED_CLASS_NAMES: dict[str, str] = {
    "NodeKind": "the generated NodeKind enum",
    "Span": "fltk_cst_core::Span (imported by generated cst.rs and parser.rs)",
    "Shared": "fltk_cst_core::Shared (imported by generated cst.rs and parser.rs)",
    "CstError": "fltk_cst_core::CstError (imported by generated cst.rs)",
}
```

Check performed at `gsm2tree_rs.py:80-83` inside `RustCstGenerator.__init__`:
```python
if class_name in _RESERVED_CLASS_NAMES:
    collision_target = _RESERVED_CLASS_NAMES[class_name]
    msg = f"Rule {rule.name!r} derives class name {class_name!r}, which collides with {collision_target}"
    raise ValueError(msg)
```

Raises `ValueError` with a descriptive message. The check is per-rule, iterating `self.grammar.rules` at `gsm2tree_rs.py:75`.

---

## Python backend — same collision class?

The Python backend (`gsm2tree.py`) generates:
- A `dataclass` named `CN` for each rule (`py_class_for_model` at `gsm2tree.py:229,237`).
- A nested `Label` class (not a module-level type) at `gsm2tree.py:241`.
- No child enum — children are `list[tuple[Optional[Label], child_type]]` with no generated union type.
- No handle wrapper struct — the dataclass IS the Python object.
- No `DropWorklistItem`.

Because Python generates no module-level `CNChild`, `CNLabel`, `PyCN`, or `DropWorklistItem` types, **Classes 1, 2, 3, 5 do not exist in the Python backend**. Class 4 (`NodeKind`) would produce a Python-level name shadowing (a new `NodeKind` dataclass would clobber the enum), but there is no runtime check in `gsm2tree.py` — the issue simply shadows the module-level `NodeKind` enum silently.

The Rust backend's `_RESERVED_CLASS_NAMES` check exists precisely because Rust emits more module-level names per rule, creating more collision surface that Python doesn't have.

---

## Detection feasibility at generation time

All information required is available in `RustCstGenerator.__init__` after the grammar is processed:

- `self.grammar.rules` gives the full list of rule names.
- `self._py_gen.class_name_for_rule_node(rule.name)` gives `CN` for any rule.
- The formulas for all generated names are pure functions of `CN`:
  - Child enum: `f"{CN}Child"`
  - Label enum (Rust): `f"{CN}Label"`
  - Handle: `f"Py{CN}"`
  - `DropWorklistItem`: literal string `"DropWorklistItem"`

A detection loop would collect all generated top-level Rust identifiers across all rules, check for duplicates, and raise `ValueError` before any code is emitted. This is a straightforward cross-rule set-intersection check — no grammar structure beyond rule names is needed.

The `_RESERVED_CLASS_NAMES` check at `gsm2tree_rs.py:80` is the natural extension point: the same loop already iterates all rules; the cross-rule check would require a second pass (or accumulation into a set) because a collision only becomes visible when two rules are compared.

---

## TODO text accuracy

The TODO claim (`gsm2tree_rs.py:33-35`) is accurate:
- "pairwise Rust-identifier collisions … are not checked at generation time" — **confirmed true**.
- "`foo_child` yields class `FooChild`, which collides with the generated `FooChild` enum for a rule `foo`'s child enum" — **confirmed exact**: `child_enum_name` returns `f"{class_name}Child"` and `foo_child` → `class_name = "FooChild"`.
- "`foo_label`/`Py`-prefix analogues exist" — **confirmed**: two additional collision classes (2 and 3 above).
- "cross-rule analysis rather than a fixed reserved set" — **confirmed**: the cross-rule structure means the required check iterates all (rule_A, rule_B) pairs, unlike the O(N) fixed-set check.
- "produce uncompilable Rust output with an opaque `cargo` error" — **confirmed**: Rust `E0428` names the duplicate item but not the grammar source.
- Location "(`RustCstGenerator.__init__`, after `_RESERVED_CLASS_NAMES` check)" — **confirmed exact** (`gsm2tree_rs.py:79-100`).

One gap in the TODO: it omits the `DropWorklistItem` collision class (Class 5 above), which is structurally identical but with a fixed string rather than a per-rule formula.
