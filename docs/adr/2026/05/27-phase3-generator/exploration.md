# Phase 3 Exploration: Rust CST Code Generator (`gsm2tree_rs.py`)

Concise. Precise. Token-dense. No fluff. Audience: smart human/LLM implementing Phase 3.

---

## 1. Phase 3 Objective (per Phase Plan)

Replace the hand-written Phase 2 Rust code (`src/cst_poc.rs`, `Identifier`, `Items`) with equivalent **generated** Rust code. The generator — `gsm2tree_rs.py` — takes a `gsm.Grammar` and emits a `.rs` file. At phase end:
- Hand-written `src/cst_poc.rs` is deleted
- Generated Rust code passes all tests in `tests/test_rust_cst_poc.py`
- Generator is tested on at least one non-FLTK grammar

The Phase 2 commit (`6f82c48`) is the model: what it hand-wrote, the generator must produce programmatically.

---

## 2. Python CST Generator: `gsm2tree.py`

**File:** `fltk/fegen/gsm2tree.py` — 303 lines.

### Key classes

**`ModelType = str | typemodel.TypeKey`** (line 19): A `str` is a rule name. `TypeKey` is the IIR key for `Span` (`self.Span = iir.Type.make(cname="Span")`, line 41).

**`ItemsModel`** (lines 22–30): Two fields:
- `labels: MutableMapping[str, set[ModelType]]` — label name (lowercase) → set of possible child types
- `types: set[ModelType]` — union of all child types across all alternatives

**`CstGenerator.__init__`** (line 34): Takes `grammar: gsm.Grammar`, `py_module: pyreg.Module`, `context: CompilerContext`. Eagerly builds `self.rule_models: dict[str, ItemsModel]` by calling `model_for_rule` for every rule (line 43–44).

### Analysis pipeline (model-building)

`model_for_rule` (line 285) → calls `model_for_alternatives` → `model_for_items` → `model_for_item`.

**Trivia insertion** (lines 296–303): After building the model for a rule, if it has whitespace separators:
- If the rule is itself a trivia rule (`rule.is_trivia_rule`): add `Span` to types
- Otherwise: add `"_trivia"` (the string) to types → causes the class-name-mapped `Trivia` to appear in the `children` union

`rule_has_whitespace_separators` (line 49): returns `True` if any `Items` in the rule uses `WS_REQUIRED` or `WS_ALLOWED` separator (initial or between items), checked recursively into sub-expressions.

**Label name**: stored lowercase in `ItemsModel.labels` keys (e.g., `"name"`, `"item"`, `"no_ws"`). Uppercased at emit time: `label.upper()` (line 115).

**Class name** (`class_name_for_rule_node`, line 46–47):
```python
"".join(part.capitalize() for part in rule_name.lower().split("_"))
```
Examples: `"identifier"` → `"Identifier"`, `"raw_string"` → `"RawString"`, `"_trivia"` → `"Trivia"`.

### Emit pipeline

`gen_py_module` (line 95): emits `ast.Module`; calls `py_class_for_model` for each rule.

`py_class_for_model` (line 109): emits one `@dataclass` class with:
1. Nested `Label(enum.Enum)` — one `LABEL = enum.auto()` per sorted label (line 112–116)
2. `span: ... = UnknownSpan` (line 126)
3. `children: list[tuple[Optional[Label], <union>]]` (line 127–131)
4. `append`, `extend`, `child` (generic methods, lines 138–168)
5. For each label (sorted): `append_{label}`, `extend_{label}`, `children_{label}`, `child_{label}`, `maybe_{label}` (lines 170–242)

**`typing.cast` in `children_{label}`** (lines 194–196): only emitted when `len(model.types) > 1`. Single-type nodes (e.g., `Identifier`) skip the cast.

**`py_module` argument**: `plumbing.py:101` passes `pyreg.Builtins`; `genparser.py:167` passes a module named after the output file. Used in `py_annotation_for_model_types` (line 85–93) to qualify forward-reference strings in generated annotations. Does **not** affect the Rust generator — Rust has no annotations.

---

## 3. Hand-Written Phase 2 Rust Code: The Template

### Files

- `src/cst_poc.rs` — 694 lines: `Identifier_Label`, `Items_Label`, `Identifier`, `Items` with full `#[pymethods]`
- `src/lib.rs` — 37 lines: module setup, `UNKNOWN_SPAN` global, registration of the four types
- `src/span.rs` — 247 lines: `Span`, `SourceText` (not changed in Phase 3)

### `lib.rs` — `UNKNOWN_SPAN` global

```rust
pub(crate) static UNKNOWN_SPAN: GILOnceCell<PyObject> = GILOnceCell::new();
```
(line 10). Set during module init. Accessed in `cst_poc.rs` as `crate::UNKNOWN_SPAN`.

### Label enum pattern (from `cst_poc.rs`)

```rust
#[allow(non_camel_case_types)]
#[pyclass(eq, hash, frozen, name = "Identifier_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Identifier_Label {
    #[pyo3(name = "NAME")]
    Name,
}
```
(lines 12–18). Key attributes: `#[allow(non_camel_case_types)]`, `#[pyclass(eq, hash, frozen)]`, `#[derive(Clone, PartialEq, Eq, Hash)]`. Python name via `name = "Identifier_Label"`.

Variant naming: Rust uses CamelCase (`Name`), `#[pyo3(name = "NAME")]` maps to Python ALL_CAPS. Multi-word labels: `NO_WS` → `NoWs`, `WS_ALLOWED` → `WsAllowed`, `WS_REQUIRED` → `WsRequired`.

`__repr__` on label returns static string `"ClassName.Label.VARIANT"` (lines 22–27 for `Identifier_Label`, 48–57 for `Items_Label`).

### Node struct pattern

```rust
#[pyclass]
pub struct Identifier {
    #[pyo3(get, set)]
    span: PyObject,
    #[pyo3(get)]
    children: Py<PyList>,
}
```
(lines 63–69). `span` has `get, set`; `children` has `get` only (never replaced, only mutated).

### Constructor

```rust
#[new]
#[pyo3(signature = (*, span = None))]
fn new(py: Python<'_>, span: Option<PyObject>) -> PyResult<Self> {
    let span_obj = match span {
        Some(s) => s,
        None => UNKNOWN_SPAN.get(py)
            .expect("UNKNOWN_SPAN not initialized; fltk._native module not loaded")
            .clone_ref(py),
    };
    Ok(Identifier { span: span_obj, children: PyList::empty(py).unbind() })
}
```
(lines 73–87). Keyword-only `span` via `*` in signature. Defaults to `crate::UNKNOWN_SPAN`.

### `#[classattr] Label`

```rust
#[classattr]
#[allow(non_snake_case)]
fn Label(py: Python<'_>) -> PyResult<PyObject> {
    Ok(Identifier_Label::type_object(py).into_any().unbind())
}
```
(lines 89–93). Returns the type object for `Identifier_Label`. Python sees `Identifier.Label` as the class, giving `Identifier.Label.NAME` access.

### Generic methods (identical for both nodes)

- `append(child, label=None)` (lines 95–101): `#[pyo3(signature = (child, label = None))]`. Creates `PyTuple::new(py, [label_val, child])`, appends to `self.children.bind(py)`.
- `extend(children, label=None)` (lines 103–118): Iterates via `children.try_iter()`, appends one tuple per item.
- `child(self)` (lines 120–129): Checks `list.len() == 1`, returns `list.get_item(0)` as raw tuple.

All methods use `&self` (not `&mut self`). All pass `py: Python<'_>` for GIL access.

### Per-label method pattern (5 methods per label)

Template shown for label `name` / `Identifier_Label::Name`:

**`append_name`** (lines 131–136):
```rust
fn append_name(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
    let label = Identifier_Label::Name.into_pyobject(py)?.into_any();
    let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
    self.children.bind(py).append(tup)?;
    Ok(())
}
```

**`extend_name`** (lines 138–147): Iterates input, creates tuple per item with `label.bind(py).clone()` for the cloned label.

**`children_name`** (lines 149–163): Returns `Py<PyList>`. Iterates `self.children`, downcasts each to `PyTuple`, compares `tup.get_item(0)?` to `label_obj` via `.eq()`, appends `tup.get_item(1)?` to result list.

**`child_name`** (lines 165–190): Inlines filter; counts matches; errors if `count != 1`; error message: `"Expected one name child but have {count}"`. Early break when `count > 1` (optimization).

**`maybe_name`** (lines 192–217): Same filter; errors if `count > 1`; error message: `"Expected at most one name child but have at least 2"`. Returns `Option<PyObject>`.

### `__eq__`, `__hash__`, `__repr__`

**`__eq__`** (lines 219–230):
```rust
fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
    if !other.is_instance_of::<Identifier>() {
        return Ok(py.NotImplemented());
    }
    let other_node: PyRef<Identifier> = other.extract()?;
    ...
}
```
Returns `py.NotImplemented()` for non-same-type. Delegates `span` and `children` comparison to Python `==`.

**`__hash__`** (lines 232–234): Raises `PyTypeError("unhashable type: 'Identifier'")`.

**`__repr__`** (lines 236–242): `"Identifier(span={span_repr}, children={children_repr})"`.

### `Items` node

Identical structure to `Identifier`, plus 20 per-label methods (5 × 4 labels: `item`, `no_ws`, `ws_allowed`, `ws_required`). Each label maps to a `Items_Label` variant: `Item`, `NoWs`, `WsAllowed`, `WsRequired`.

Error message strings use the label name as it appears in method names (e.g., `"Expected one item child"`, `"Expected one no_ws child"`).

### Module registration (current `lib.rs`)

```rust
m.add_class::<Identifier_Label>()?;
m.add_class::<Identifier>()?;
m.add_class::<Items_Label>()?;
m.add_class::<Items>()?;
```
(lines 31–34). Order: label enum before node struct.

**Phase 3 change:** Current code registers all classes directly in `_native`. Per the phase plan, Phase 3 introduces a `register_classes(module: &Bound<PyModule>)` function per grammar, so the generated code can be wired into any module. The hand-written Phase 2 code in `lib.rs` must be replaced by calling the generated `register_classes`.

---

## 4. Tests That Must Continue to Pass

### Primary: `tests/test_rust_cst_poc.py` (443 lines)

All 27 acceptance criteria organized in 10 test classes. Key behavioral assertions:
- `Identifier.Label.NAME == Identifier.Label.NAME` (AC-1)
- `node.children is node.children` — same list object (AC-6)
- `a.children.extend(b.children)` mutates `a`'s backing list (AC-8)
- `node.child_name()` returns the value, not a `(label, child)` tuple (AC-10)
- `children_name()` excludes `None`-labeled children (AC-27)
- `hash(node)` raises `TypeError` (AC-24)
- `node.span == UnknownSpan` for default-constructed node (AC-22)
- Label `repr` contains class name and variant: `"Identifier"` and `"NAME"` in `repr(Identifier.Label.NAME)` (AC-26)

Import pattern: `from fltk._native import Identifier, Items, Span, UnknownSpan`. For generated code to pass these tests, the generated classes must be registered in `fltk._native` under these exact names.

### Current registration in `lib.rs`

Phase 2 hand-wires `Identifier`, `Items` into `_native`. Phase 3 must ensure the generated classes are registered under the same names. Two options:
1. Generate a `register_classes` function and call it from `lib.rs` (phase plan approach)
2. Keep the current direct registration for the PoC nodes as a transitional step

The phase plan says: "remove the hand-written phase 2 code." So the generated `register_classes` for the PoC grammar must be called from `lib.rs`, and the old hand-written registrations removed.

### Other tests that transitively exercise CST

All plumbing/integration tests use `generate_parser` which calls `gsm2tree.CstGenerator` (the Python generator). Phase 3 does not modify `plumbing.py`, so these tests are unaffected. The Python generator remains live; `gsm2tree_rs.py` is additive.

---

## 5. GSM Structures Consumed by the Generator

### `gsm.Grammar` (`gsm.py:20–22`)
```python
@dataclasses.dataclass(frozen=True, slots=True)
class Grammar:
    rules: Sequence[Rule]
    identifiers: Mapping[str, Rule]
```

### `gsm.Rule` (`gsm.py:25–31`)
```python
class Rule:
    name: str                           # e.g., "identifier", "_trivia", "raw_string"
    alternatives: Sequence[Items]
    is_trivia_rule: bool = False        # set by classify_trivia_rules()
```

### `gsm.Item` (`gsm.py:101–106`)
```python
class Item:
    label: str | None         # lowercase, e.g., "name", "item", "no_ws"
    disposition: Disposition  # SUPPRESS | INCLUDE | INLINE
    term: Term                # Identifier | Literal | Regex | Sequence[Items]
    quantifier: Quantifier
```

### `gsm.Disposition` (`gsm.py:176–179`)
```python
class Disposition(Enum):
    SUPPRESS = "suppress"
    INCLUDE = "include"
    INLINE = "inline"
```

### `gsm.Separator` (`gsm.py:54–56`)
```python
class Separator(Enum):
    NO_WS = "NO_WS"
    WS_REQUIRED = "WS_REQUIRED"
    WS_ALLOWED = "WS_ALLOWED"
```

The generator must check `items.initial_sep` and `items.sep_after[i]` for `WS_REQUIRED` or `WS_ALLOWED` to determine trivia inclusion — exactly as `rule_has_whitespace_separators` does (lines 49–67 of `gsm2tree.py`).

---

## 6. Grammar Files and Test Grammars

### `fltk/fegen/fegen.fltkg` — The authoritative grammar (22 lines)

14 rules: `grammar`, `rule`, `alternatives`, `items`, `item`, `term`, `disposition`, `quantifier`, `identifier`, `raw_string`, `literal`, `_trivia`, `line_comment`, `block_comment`.

This is the grammar that `fltk_cst.py` was generated from.

### `fltk/fegen/fltk.fltkg` — Broken extended grammar

Per phase-plan.md line 2: "This grammar is actually broken and was never completed." Not usable.

### `fltk/fegen/fltk_cst.py` — 14 CST classes (1127 lines)

The committed CST for `fegen.fltkg`. Generated from `fegen.fltkg` (not `fltk.fltkg`). The 14 classes:

| Class | Labels | child types |
|---|---|---|
| `Grammar` | `RULE` | `Rule`, `Trivia` |
| `Rule` | `ALTERNATIVES`, `NAME` | `Alternatives`, `Identifier`, `Trivia` |
| `Alternatives` | `ITEMS` | `Items`, `Trivia` |
| `Items` | `ITEM`, `NO_WS`, `WS_ALLOWED`, `WS_REQUIRED` | `Item`, `Trivia`, `Span` |
| `Item` | `DISPOSITION`, `LABEL`, `QUANTIFIER`, `TERM` | `Disposition`, `Identifier`, `Quantifier`, `Term`, `Trivia` |
| `Term` | `ALTERNATIVES`, `IDENTIFIER`, `LITERAL`, `REGEX` | `Alternatives`, `Identifier`, `Literal`, `RawString`, `Trivia` |
| `Disposition` | `INCLUDE`, `INLINE`, `SUPPRESS` | `Span` only |
| `Quantifier` | `ONE_OR_MORE`, `OPTIONAL`, `ZERO_OR_MORE` | `Span` only |
| `Identifier` | `NAME` | `Span` only |
| `RawString` | `VALUE` | `Span` only |
| `Literal` | `VALUE` | `Span` only |
| `Trivia` | `BLOCK_COMMENT`, `LINE_COMMENT` | `BlockComment`, `LineComment`, `Span` |
| `LineComment` | `CONTENT`, `PREFIX` | `Span` only |
| `BlockComment` | `CONTENT`, `END`, `START` | `Span` only |

(Verified from `fltk_cst.py` line ranges in the overall exploration.)

### Test grammars (inline, in test files)

`test_regression_empty_nary.py`: `numbers := digit+` — single rule, one regex item. Simple case for testing the generator on a trivial grammar.

Most regression tests (`test_regression_*.py`, `test_gsm2parser.py`) build `gsm.Grammar` inline and call `gsm2tree.CstGenerator` + `gsm2parser.ParserGenerator` directly (no `.fltkg` files). These provide a battery of representative grammars to test against.

---

## 7. `plumbing.py` — Current Integration (Phase 3 Context)

**`generate_parser`** (lines 86–147):
1. `gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(grammar, context))` — always adds trivia rule
2. `CstGenerator(grammar=..., py_module=pyreg.Builtins, context=context)` — line 101
3. `cstgen.gen_py_module()` → `exec()` → `types.ModuleType` → `sys.modules` — lines 102–112
4. Parser gen and exec — lines 114–135
5. Returns `ParserResult(parser_class, cst_module, cst_module_name, ...)` — line 141

**Key fact:** `py_module=pyreg.Builtins` is passed to `CstGenerator`. `pyreg.Builtins` means no module path prefix in generated forward-reference annotations. For `gsm2tree_rs.py`, `py_module` only matters if the Rust generator reuses `py_annotation_for_model_types`; for code generation that emits plain Rust, the annotation logic is irrelevant.

**Phase 3 does not modify `plumbing.py`**. The generator is standalone. Integration comes in Phase 4.

---

## 8. `genparser.py` — CLI Generator

**`generate` command** (lines 104–216): Generates `{base_name}_cst.py`, `{base_name}_parser.py`, `{base_name}_trivia_parser.py`.

CST generation path (lines 167–177):
```python
cst_module = pyreg.Module(cst_module_name.split("."))
cstgen = gsm2tree.CstGenerator(grammar=grammar, py_module=cst_module, context=...)
cst_mod = cstgen.gen_py_module()
with shared_cst.open("w") as f:
    f.write(ast.unparse(cst_mod))
```

**Phase 3 parallel:** `gsm2tree_rs.py` will have a similar top-level function: takes `gsm.Grammar`, returns a `str` of Rust source (or writes to a file). A new `genparser.py` subcommand (`generate-rust-cst`) would call it. Phase 3 creates the generator; the CLI subcommand is Phase 4 scope.

---

## 9. Build System

### `Cargo.toml`
```toml
[package]
name = "fltk-native"
version = "0.1.0"
edition = "2021"
[lib]
name = "fltk_native"
crate-type = ["cdylib"]
[dependencies]
pyo3 = { version = "0.23", features = ["abi3-py310"] }
```

Single crate. `pyo3 = "0.23"` with `abi3-py310` stable ABI.

### `pyproject.toml` (relevant sections)
```toml
[build-system]
requires = ["maturin>=1.7,<2"]
build-backend = "maturin"

[tool.maturin]
python-packages = ["fltk"]
module-name = "fltk._native"
features = ["pyo3/extension-module"]
```

**Build command:** `uv run --group dev maturin develop` (debug build). For testing: `uv run pytest`.

**Implication for Phase 3:** Any new `.rs` file added to `src/` must be declared as a `mod` in `src/lib.rs`. The generated `.rs` file for the PoC grammar would be added as `mod cst_poc_generated;` (or similar) and its `register_classes` called from `_native`.

---

## 10. GSM-to-Rust Label Name Mapping

The generator must transform GSM label names (lowercase strings) to Rust enum variant names (CamelCase) and Python-visible names (ALL_CAPS):

| GSM label (lowercase) | Rust variant | Python name (via `#[pyo3(name)]`) |
|---|---|---|
| `name` | `Name` | `"NAME"` |
| `item` | `Item` | `"ITEM"` |
| `no_ws` | `NoWs` | `"NO_WS"` |
| `ws_allowed` | `WsAllowed` | `"WS_ALLOWED"` |
| `ws_required` | `WsRequired` | `"WS_REQUIRED"` |
| `one_or_more` | `OneOrMore` | `"ONE_OR_MORE"` |
| `zero_or_more` | `ZeroOrMore` | `"ZERO_OR_MORE"` |

Transformation rules:
- Python name: `label.upper()` (same as `gsm2tree.py:115`)
- Rust variant name: `"_".join(part.capitalize() for part in label.split("_"))` — same word-split-and-capitalize as `class_name_for_rule_node` but applied to label words
- Method name: the label as-is (lowercase, underscores preserved): `append_no_ws`, `child_ws_allowed`, etc.

Error message strings embed the label name: `f"Expected one {label} child but have {count}"`, `f"Expected at most one {label} child but have at least 2"`.

---

## 11. Per-Label Method Name Mapping

For each label `L` (lowercase, underscored), the 5 generated methods are:
- `append_{L}(child: PyObject) -> PyResult<()>`
- `extend_{L}(children: &Bound<'_, PyAny>) -> PyResult<()>`
- `children_{L}() -> PyResult<Py<PyList>>`
- `child_{L}() -> PyResult<PyObject>`
- `maybe_{L}() -> PyResult<Option<PyObject>>`

All use `&self`. All take `py: Python<'_>`.

---

## 12. `register_classes` Interface (Phase 3 Output)

Per phase-plan.md (lines 104–107):
> The register-classes function (not a `#[pymodule]`) is the key interface: it allows the same generated Rust code to be registered into *any* module.

Generated `.rs` file structure:
```rust
pub fn register_classes(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<GrammarLabel>()?;
    module.add_class::<Grammar>()?;
    // ... all label enums, then all node structs ...
    Ok(())
}
```

This is a `pub fn`, not a `#[pymodule]`. `lib.rs` calls it:
```rust
cst_poc_generated::register_classes(m)?;
```

**Removal of old code:** The current `lib.rs` lines 31–34 (`m.add_class::<Identifier_Label>()` etc.) must be removed and replaced by the call to `register_classes`. The `mod cst_poc;` declaration and the `use cst_poc::{...}` imports in `lib.rs` are also removed.

---

## 13. Design of `gsm2tree_rs.py`

### Reuse strategy

Per phase-plan.md (line 101–102):
> Reuse the analysis logic by instantiating (or subclassing) `CstGenerator` and consuming its `rule_models` dict.

`CstGenerator.__init__` populates `self.rule_models` eagerly. `gsm2tree_rs.py` can instantiate `CstGenerator` with any `py_module` (e.g., `pyreg.Builtins`) to get the `rule_models`, then use those models to emit Rust text instead of `ast.Module`.

The `gen_py_module` and `py_class_for_model` methods are Python-specific and not reused. The model-building methods (`model_for_rule`, `model_for_items`, etc.) and `class_name_for_rule_node` are the reusable parts.

### Generator structure

```python
class RustCstGenerator:
    def __init__(self, grammar: gsm.Grammar):
        # Reuse CstGenerator for model building
        context = create_default_context(capture_trivia=True)
        grammar_with_trivia = gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(grammar, context))
        self._py_gen = CstGenerator(grammar=grammar_with_trivia, py_module=pyreg.Builtins, context=context)
        self.grammar = grammar_with_trivia

    def gen_rs_module(self) -> str:
        # Emit preamble (use declarations), then per-rule code, then register_classes fn
        ...

    def _gen_label_enum(self, class_name: str, model: ItemsModel) -> str: ...
    def _gen_node_struct(self, class_name: str, model: ItemsModel) -> str: ...
    def _gen_pymethods(self, class_name: str, label_enum_name: str, labels: list[str]) -> str: ...
    def _gen_register_classes(self, class_names: list[str]) -> str: ...
```

### Rust variant name helper

```python
def rust_variant_name(label: str) -> str:
    return "".join(part.capitalize() for part in label.split("_"))
# "no_ws" -> "NoWs", "name" -> "Name", "one_or_more" -> "OneOrMore"
```

### Preamble (fixed across all generated files)

```rust
use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyList, PyTuple};
use pyo3::PyTypeInfo;

use crate::UNKNOWN_SPAN;
```

---

## 14. Open Factual Questions

1. **Trivia rule in PoC grammar**: The Phase 2 PoC hand-wrote `Identifier` and `Items` — but does the PoC correspond to a grammar with or without a trivia rule? If `gsm2tree_rs.py` generates from a grammar with the trivia rule added (`add_trivia_rule_to_grammar`), `Trivia` and related classes also need to be generated. The Phase 2 test file only imports `Identifier, Items, Span, UnknownSpan` from `_native` — not `Trivia`, `LineComment`, `BlockComment`. So the PoC grammar (to replace the hand-written code) is a minimal 2-rule grammar with no trivia rule, or generation includes trivia classes that just aren't tested by `test_rust_cst_poc.py`.

2. **Where does the generated `.rs` file live?** Options: (a) alongside `gsm2tree.py` at `fltk/fegen/gsm2tree_rs.py` outputs to `src/generated_cst.rs`; (b) output path is an argument. Phase plan doesn't specify. For Phase 3 this is a test artifact; Phase 4 decides the convention.

3. **`_trivia` class name**: `class_name_for_rule_node("_trivia")` = `"Trivia"`. The Rust label enum name would be `Trivia_Label`. With the `_` prefix stripped by capitalize-split, `"_trivia".lower().split("_")` = `["", "trivia"]`, `"".capitalize()` = `""`, so `class_name_for_rule_node("_trivia")` = `"Trivia"`. Needs verification against the actual Python: `"".join(part.capitalize() for part in "_trivia".lower().split("_"))` → `"" + "Trivia"` = `"Trivia"`. Correct.

4. **`UNKNOWN_SPAN` initialization order**: The generated `cst_{grammar}.rs` uses `crate::UNKNOWN_SPAN`. This cell is set in the `_native` module init function in `lib.rs`. As long as generated CST nodes are registered in the same module init (via `register_classes(m)`), the cell will be initialized before any node is constructed. No ordering issue.

5. **`fegen.fltkg` vs `fltk.fltkg`**: The phase plan says (phase-plan.md line 108): "Generate Rust source from the FLTK grammar (`fltk.fltkg`, after Phase 0 reconciliation — currently 14 classes in `fltk_cst.py`)". But `fltk.fltkg` is broken; `fltk_cst.py` was actually generated from `fegen.fltkg`. This discrepancy must be resolved before Phase 3 can test against the full FLTK grammar.
