# Phase 3 Design: Rust CST Code Generator (`gsm2tree_rs.py`)

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

---

## Root Cause / Context

The Phase 2 commit (`6f82c48`) hand-wrote 694 lines of Rust (`src/cst_poc.rs`) implementing `Identifier` and `Items` CST nodes. This validated the PyO3 patterns (nested-enum workaround, `Py<PyList>` mutation semantics) but is not scalable: the `fegen.fltkg` grammar alone has 14 rules, and the method count grows linearly with labels (5 methods per label plus 7 fixed methods per node). The Python generator `gsm2tree.py` (303 lines) already solves this for Python dataclasses. Phase 3 builds a parallel Rust emitter.

Per the user's instruction: "we replace the hand-written phase 2 code with equivalent generated code; the phase2 commit serves as a *model* for code generation. At the end of phase 3, the hand-written code should be removed because the generated code passes all the same tests."

The generator must produce Rust source that, when compiled, passes all 27 acceptance criteria in `tests/test_rust_cst_poc.py` without modification to that test file (requirements AC-1).

---

## Proposed Approach

### New Files

| File | Purpose |
|---|---|
| `fltk/fegen/gsm2tree_rs.py` | `RustCstGenerator` class: takes `gsm.Grammar`, emits `.rs` source text |
| `src/cst_generated.rs` | Generated Rust output for the PoC grammar (committed, replaces `src/cst_poc.rs`) |
| `src/cst_fegen.rs` | Generated Rust output for the `fegen.fltkg` grammar (committed) |
| `tests/test_gsm2tree_rs.py` | Generator unit tests: PoC grammar, `fegen.fltkg`, minimal single-rule grammar |
| `tests/test_fegen_rust_cst.py` | Smoke tests for the 14 `fegen.fltkg` classes compiled into `fltk._native.fegen_cst` |

### Modified Files

| File | Change |
|---|---|
| `src/lib.rs` | Replace `mod cst_poc; use cst_poc::{...};` and direct `add_class` calls with `mod cst_generated;` and `cst_generated::register_classes(m)?;`. Add `mod cst_fegen;` registered into a `fegen_cst` submodule to avoid name collisions. |
| `src/cst_poc.rs` | Deleted |

No changes to `tests/test_rust_cst_poc.py`, `gsm2tree.py`, `plumbing.py`, `genparser.py`, or any other existing file.

---

### `RustCstGenerator` — Public API

```python
# fltk/fegen/gsm2tree_rs.py

class RustCstGenerator:
    def __init__(self, grammar: gsm.Grammar):
        ...

    def generate(self) -> str:
        """Return a complete, compilable .rs file as a string."""
        ...
```

**Input**: A raw `gsm.Grammar` (not yet trivia-processed). The constructor applies `add_trivia_rule_to_grammar` and `classify_trivia_rules` internally (requirements: "System behavior > Input").

**Output**: A string containing a complete `.rs` file with all `use` declarations, type definitions, `#[pymethods]` blocks, and a `register_classes` function.

### Model Reuse Strategy

The constructor instantiates `CstGenerator` to obtain `rule_models`:

```python
def __init__(self, grammar: gsm.Grammar):
    context = create_default_context()
    grammar_with_trivia = gsm.classify_trivia_rules(
        gsm.add_trivia_rule_to_grammar(grammar, context)
    )
    self._py_gen = CstGenerator(
        grammar=grammar_with_trivia,
        py_module=pyreg.Builtins,
        context=context,
    )
    self.grammar = grammar_with_trivia
```

This reuses the entire analysis pipeline: `model_for_rule`, `model_for_items`, `model_for_item`, trivia insertion (`gsm2tree.py:296-303`), whitespace separator detection (`gsm2tree.py:49-67`). The Rust generator only replaces the *emit* pipeline (`gen_py_module` / `py_class_for_model`), not the *analysis* pipeline.

`py_module=pyreg.Builtins` is passed because the Rust generator does not use Python annotations; `pyreg.Builtins` avoids unnecessary module-path prefix logic. `capture_trivia` on the context defaults to `False` (omitted). This differs from the exploration's `capture_trivia=True` but is irrelevant: `add_trivia_rule_to_grammar` ignores `context` (`gsm.py:380`), `classify_trivia_rules` takes only `grammar`, and `CstGenerator.__init__` never reads `context.capture_trivia`. Trivia inclusion is determined entirely by `add_trivia_rule_to_grammar` and `classify_trivia_rules`, both applied to the grammar before `CstGenerator`.

### Generated `.rs` File Structure

The `generate()` method emits sections in this order:

1. **Preamble** (fixed):
   ```rust
   use pyo3::exceptions::{PyTypeError, PyValueError};
   use pyo3::prelude::*;
   use pyo3::types::{PyList, PyTuple};
   use pyo3::PyTypeInfo;

   use crate::UNKNOWN_SPAN;
   ```

2. **Per-rule blocks**, in grammar rule order (matching `self.grammar.rules` iteration order). For each rule with class name `C` and label enum name `C_Label`:
   - Label enum definition
   - Label enum `#[pymethods]` block (`__repr__`)
   - Node struct definition
   - Node struct `#[pymethods]` block (constructor, `Label` classattr, generic methods, per-label methods, `__eq__`, `__hash__`, `__repr__`)

3. **`register_classes` function**:
   ```rust
   pub fn register_classes(module: &Bound<'_, PyModule>) -> PyResult<()> {
       module.add_class::<C_Label>()?;
       module.add_class::<C>()?;
       // ... for each rule, label enum then node struct ...
       Ok(())
   }
   ```

### Name Transformation Functions

These match the Python generator exactly (requirements: "Name transformations"):

Class name uses `self._py_gen.class_name_for_rule_node(rule_name)` directly, ensuring exact consistency with the Python generator. The two new helpers:

```python
def _rust_variant_name(label: str) -> str:
    """Label -> CamelCase Rust enum variant. 'no_ws' -> 'NoWs'."""
    return "".join(part.capitalize() for part in label.split("_"))

def _python_label_name(label: str) -> str:
    """Label -> ALL_CAPS Python-visible name. 'no_ws' -> 'NO_WS'."""
    return label.upper()
```

### Per-Rule Code Generation — Detailed Template

Labels are sorted alphabetically within each rule (matching `gsm2tree.py:113` `sorted(model.labels.keys())`), ensuring deterministic output (requirements: "Constraints > Deterministic output").

#### Label Enum

For class name `Items` with sorted labels `["item", "no_ws", "ws_allowed", "ws_required"]`:

```rust
#[allow(non_camel_case_types)]
#[pyclass(eq, hash, frozen, name = "Items_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Items_Label {
    #[pyo3(name = "ITEM")]
    Item,
    #[pyo3(name = "NO_WS")]
    NoWs,
    #[pyo3(name = "WS_ALLOWED")]
    WsAllowed,
    #[pyo3(name = "WS_REQUIRED")]
    WsRequired,
}
```

Key attributes match Phase 2 exactly: `#[allow(non_camel_case_types)]` on the enum, `#[pyclass(eq, hash, frozen, name = "{ClassName}_Label")]`, `#[derive(Clone, PartialEq, Eq, Hash)]`.

#### Label `__repr__`

```rust
#[pymethods]
impl Items_Label {
    fn __repr__(&self) -> &'static str {
        match self {
            Items_Label::Item => "Items.Label.ITEM",
            Items_Label::NoWs => "Items.Label.NO_WS",
            // ...
        }
    }
}
```

Each arm returns `"{ClassName}.Label.{PYTHON_NAME}"` as a static string.

#### Node Struct

```rust
#[pyclass]
pub struct Items {
    #[pyo3(get, set)]
    span: PyObject,
    #[pyo3(get)]
    children: Py<PyList>,
}
```

Identical for every node. `span` has `get, set`; `children` has `get` only.

#### Node `#[pymethods]` Block

Contains, in order:

1. **`#[new]`** — keyword-only `span` defaulting to `crate::UNKNOWN_SPAN`:
   ```rust
   #[new]
   #[pyo3(signature = (*, span = None))]
   fn new(py: Python<'_>, span: Option<PyObject>) -> PyResult<Self> {
       let span_obj = match span {
           Some(s) => s,
           None => UNKNOWN_SPAN
               .get(py)
               .expect("UNKNOWN_SPAN not initialized; fltk._native module not loaded")
               .clone_ref(py),
       };
       Ok(Items {
           span: span_obj,
           children: PyList::empty(py).unbind(),
       })
   }
   ```

2. **`#[classattr] Label`**:
   ```rust
   #[classattr]
   #[allow(non_snake_case)]
   fn Label(py: Python<'_>) -> PyResult<PyObject> {
       Ok(Items_Label::type_object(py).into_any().unbind())
   }
   ```

3. **Generic `append`**, **`extend`**, **`child`** — identical to Phase 2 (`cst_poc.rs:95-129`), with the struct name substituted in the constructor.

4. **Per-label methods** (5 per label, in sorted label order): `append_{label}`, `extend_{label}`, `children_{label}`, `child_{label}`, `maybe_{label}`. Each follows the Phase 2 template exactly, substituting:
   - Label enum type (`Items_Label`)
   - Variant (`Items_Label::Item`)
   - Method name suffix (`item`, `no_ws`, etc.)
   - Error message strings (`"Expected one item child but have {count}"`)
   - Downcast error context (`"Items.children_item: children[{idx}] is not a tuple: {e}"`)

5. **`__eq__`**: Type check uses `is_instance_of::<Items>()`, extract uses `PyRef<Items>`. Returns `py.NotImplemented()` for non-same-type.

6. **`__hash__`**: Raises `PyTypeError::new_err("unhashable type: 'Items'")`.

7. **`__repr__`**: Format string `"Items(span={span_repr}, children={children_repr})"`.

### `child_{label}` and `maybe_{label}` — Error Message Details

Per requirements AC-11 and Phase 2 code:

- `child_{label}`: `"Expected one {label} child but have {count}"` — dynamic count. Early-breaks when `count > 1` (the `break` after the second match in Phase 2, `cst_poc.rs:180`). The reported count is thus 2 when the true count may be higher. This matches the Phase 2 behavior and the test assertion `"Expected one name child but have 0"` (AC-12).
- `maybe_{label}`: `"Expected at most one {label} child but have at least 2"` — fixed string. Also early-breaks.

The `{label}` in error messages uses the lowercase method-suffix form (e.g., `"name"`, `"no_ws"`, `"ws_allowed"`).

### `children_{label}`, `child_{label}`, `maybe_{label}` — Downcast Error

All three include a `.map_err` on the `downcast::<PyTuple>()` call that includes context: `"{ClassName}.{method_name}: children[{idx}] is not a tuple: {e}"`. This matches the Phase 2 pattern (`cst_poc.rs:153-156`).

### Empty Label Enum Handling

Requirements OQ-empty-label-enum: Zero-label rules are possible (a rule where all items are unlabeled INCLUDE). Rust enums cannot have zero variants.

**Decision**: Omit the label enum and `#[classattr] Label` entirely for such rules. The node struct is still emitted with all generic methods. The `register_classes` function omits the label enum registration. This diverges from the Python generator (which emits an empty `Label(enum.Enum)`) but is the only sound option in Rust; options (b) sentinel variant and (c) error both have worse tradeoffs. The Python generator succeeds because Python allows empty enums; Rust does not.

When a rule has no labels, the `register_classes` function emits only `module.add_class::<NodeStruct>()?;` for that rule (no label enum line).

### PoC Grammar Definition

The PoC grammar is hand-constructed using `gsm.*` objects (not parsed from a `.fltkg` file). It has two rules:

**`identifier` rule**: One `Items` containing one item: `label="name"`, `disposition=INCLUDE`, `term=Regex(r"[_a-z][_a-z0-9]*")`, `quantifier=REQUIRED`. Separator: `NO_WS`. Model analysis (`model_for_item` → Regex → `{Span.key}`, then `item.label="name"` → `labels["name"] |= {Span.key}`) produces `ItemsModel(labels={"name": {Span.key}}, types={Span.key})`. No whitespace separators → no trivia added. Result: `Identifier` with label `NAME`.

**`items` rule**: Must produce labels `ITEM`, `NO_WS`, `WS_ALLOWED`, `WS_REQUIRED`. Constructed as one `Items` with:
- Three labeled literal items: `label="no_ws", term=Literal(".")`, `label="ws_allowed", term=Literal(",")`, `label="ws_required", term=Literal(":")` — each `INCLUDE`. These yield `labels["no_ws"] |= {Span.key}` etc.
- One labeled identifier item: `label="item", term=Identifier("identifier"), disposition=INCLUDE` — yields `labels["item"] |= {"identifier"}`.
- Separators: at least one `WS_ALLOWED` or `WS_REQUIRED` in `sep_after` — triggers `rule_has_whitespace_separators`, adding `"_trivia"` to types (since `items` is not a trivia rule).

The `add_trivia_rule_to_grammar` call auto-adds a `_trivia` rule (since neither hand-constructed rule is named `_trivia`). After `classify_trivia_rules`, the generator produces three classes: `Identifier`, `Items`, `Trivia`. The PoC tests (`test_rust_cst_poc.py`) only import `Identifier` and `Items` — the extra `Trivia` class compiles but is not tested by that file.

**Key invariant**: The generated `Identifier` must have exactly label `NAME`. The generated `Items` must have exactly labels `ITEM`, `NO_WS`, `WS_ALLOWED`, `WS_REQUIRED`. A test in `test_gsm2tree_rs.py` verifies this by inspecting the generated source text before compilation.

### `fegen.fltkg` Grammar — Compilation Test

A second generated `.rs` file is produced from `fegen.fltkg` (14 rules → 14 classes; `_trivia` is already defined in the grammar at line 19, so `add_trivia_rule_to_grammar` is a no-op). This file is compiled as `mod cst_fegen;` in `lib.rs` with its `register_classes` called during module init.

The `fegen.fltkg` grammar is parsed using the existing `fltk_parser` + `fltk2gsm` pipeline (same as `genparser.py:26-55`). The generated Rust file is committed as `src/cst_fegen.rs`.

### `lib.rs` Changes

```rust
mod cst_generated; // replaces mod cst_poc
mod cst_fegen;     // new: fegen grammar classes
mod span;

use span::{Span, SourceText};

pub(crate) static UNKNOWN_SPAN: GILOnceCell<PyObject> = GILOnceCell::new();

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Span>()?;
    m.add_class::<SourceText>()?;
    // ... UnknownSpan setup (unchanged) ...

    // PoC grammar classes registered at top level (Identifier, Items, etc.)
    cst_generated::register_classes(m)?;

    // Fegen grammar classes in a submodule to avoid name collisions
    // (both grammars produce Identifier, Items, Trivia)
    let fegen_sub = PyModule::new(m.py(), "fegen_cst")?;
    cst_fegen::register_classes(&fegen_sub)?;
    m.add_submodule(&fegen_sub)?;

    // PyO3's add_submodule does NOT register in sys.modules, so
    // `from fltk._native.fegen_cst import X` would fail with
    // ModuleNotFoundError. Fix by inserting manually:
    let sys = m.py().import("sys")?;
    sys.getattr("modules")?
        .set_item("fltk._native.fegen_cst", &fegen_sub)?;

    Ok(())
}
```

The `use cst_poc::{...}` import and direct `add_class` calls are removed. `register_classes` handles all class registration per grammar. The fegen grammar gets a submodule (`fltk._native.fegen_cst`) because both grammars produce classes named `Identifier`, `Items`, and `Trivia`.

The `sys.modules` insertion is required because PyO3's `add_submodule` only sets an attribute on the parent module; without the manual registration, `from fltk._native.fegen_cst import X` raises `ModuleNotFoundError`.

### Build/Generate Workflow

The generated `.rs` files are committed artifacts (like `fltk_cst.py`). The generation step is a development-time command, not a build-time step. Developers regenerate by running the generator script and then `maturin develop`:

```bash
# Regenerate Rust CST files (development-time)
uv run python -m fltk.fegen.gsm2tree_rs  # or a test fixture that writes the files

# Build
uv run --group dev maturin develop

# Test
uv run pytest
```

The generator itself has no CLI surface in this phase (requirements: "No CLI surface in this phase"). The `.rs` files are generated by test fixtures or a simple script that calls `RustCstGenerator.generate()` and writes the result. The committed `.rs` files are the source of truth for compilation.

---

## Edge Cases / Failure Modes

### Rules with no labels

Handled by omitting the label enum and `#[classattr] Label`. The node struct still has `span`, `children`, generic `append`/`extend`/`child`, `__eq__`, `__hash__`, `__repr__`. No per-label methods are generated. This is reachable for rules like a hypothetical `foo := "bar"` where the literal is INCLUDE but unlabeled (though `gsm2tree.py:274-276` only creates labels for items with `item.label`, so this would have `types` but no `labels`).

### Rules with no types (empty model)

`gsm2tree.py:117-121` raises `RuntimeError` for models with no types. The Rust generator inherits this check via `CstGenerator`. If a grammar produces such a rule, the Python analysis layer raises before the Rust emitter runs. No separate handling needed.

### PoC grammar label mismatch

If the programmatic PoC grammar produces different labels than Phase 2's hand-written code, `test_rust_cst_poc.py` fails. Mitigation: a dedicated test in `tests/test_gsm2tree_rs.py` asserts the generated Rust source contains the expected label enum variants before compilation, catching label mismatches early.

### `fegen.fltkg` parsing failure

The fegen grammar test depends on the parser pipeline (`fltk_parser` + `fltk2gsm`). If the grammar file is modified or the parser has bugs, generation fails. Mitigation: the test uses `fegen.fltkg` as committed — the same file the existing Python CST was generated from.

### Name collisions in `_native` module

Both grammars produce classes named `Identifier`, `Items`, and `Trivia`. Handled by registering the fegen grammar into a `fegen_cst` submodule (see `lib.rs` Changes section). If a future grammar also collides, the same submodule pattern applies.

**Assumption**: The `#[classattr] Label` pattern (`T::type_object(py)`) is expected to work identically for classes registered in a submodule vs top-level — `type_object` returns the interpreter's type object, which is module-agnostic. Phase 2 validated this only for top-level registration. The AC-8 smoke test (`test_label_access`) will confirm this assumption for the submodule case.

### Rust enum variant naming for edge-case labels

Labels like `_content` (leading underscore) would produce `""` as the first capitalized part. `"".join(["", "Content"])` = `"Content"`, which is correct CamelCase. Labels that are entirely underscores would produce an empty variant name — but such labels cannot exist in the GSM (label names match `/[_a-z][_a-z0-9]*/` per `fegen.fltkg:16`). No special handling needed.

### Deterministic output across Python versions

`sorted()` on `model.labels.keys()` (strings) is deterministic. `self.grammar.rules` preserves insertion order (a `Sequence`). No `set` iteration without sorting. Output is deterministic.

---

## Test Plan

### `tests/test_gsm2tree_rs.py` — Generator Unit Tests

**Placement rationale**: Existing convention: grammar/generator tests under `fltk/fegen/`, Rust-extension tests under `tests/`. These generator tests validate source text (not compiled output), but they depend on `fltk._native` for the PoC grammar fixture and sit alongside `test_rust_cst_poc.py` which validates the compiled result. Placing them in `tests/` groups all Phase 3 test files together. The fegen smoke tests (`test_fegen_rust_cst.py`) import compiled Rust classes and belong in `tests/` by the same convention.

Tests for the generator itself (source-text validation), NOT for the compiled Rust output.

| Test | What it validates | Requirements |
|---|---|---|
| `test_poc_grammar_generates_expected_labels` | Generated source contains `Identifier_Label` with `Name`/`"NAME"` and `Items_Label` with all four variants | AC-1 precondition |
| `test_poc_grammar_generates_register_classes` | Generated source contains `pub fn register_classes` with `add_class` calls for all types | AC-5 |
| `test_poc_grammar_preamble` | Generated source starts with correct `use` declarations | AC-10 |
| `test_fegen_grammar_generates_14_classes` | Generated source from `fegen.fltkg` contains all 14 class names (`Grammar`, `Rule`, ..., `BlockComment`) | AC-7 precondition |
| `test_minimal_grammar_single_rule` | Generator does not crash on a single-rule grammar (e.g., `numbers := digit+` from `fltk/fegen/test_regression_empty_nary.py`) | AC-9 |
| `test_deterministic_output` | Two calls to `generate()` on the same grammar produce identical strings | Determinism constraint |
| `test_empty_label_enum_omitted` | A rule with no labels omits the label enum and `#[classattr] Label` | OQ-empty-label-enum |

### `tests/test_rust_cst_poc.py` — Unchanged (27 acceptance criteria)

Passes without modification against the generated `cst_generated.rs`. This is the primary validation that generated code is behaviorally equivalent to hand-written Phase 2 code (all 27 Phase 2 acceptance criteria, requirements AC-6).

### `tests/test_fegen_rust_cst.py` — Fegen Grammar Smoke Tests

Validates that the compiled `fegen.fltkg` Rust classes work correctly.

| Test | What it validates | Requirements |
|---|---|---|
| `test_all_classes_importable` | All 14 classes (plus `_trivia` derivatives) are importable from `fltk._native.fegen_cst` | AC-7 |
| `test_label_access` | Each class's `ClassName.Label.VARIANT` is accessible for at least one label | AC-8 |
| `test_construction_default_span` | Each class constructs with default `UnknownSpan` | AC-8 |
| `test_append_child_roundtrip` | For each class, `append_{label}` + `child_{label}` round-trips correctly | AC-8 |
| `test_children_is_list` | `node.children` is a Python list for each class | AC-8 |

### Existing test suite

`uv run pytest` passes in its entirety (AC-12). No existing test is modified.

---

## Open Questions

**OQ-empty-label-enum vs requirements**: The requirements error-behavior section states the generator "still emits a node struct with an empty label enum (zero variants)" and "`#[classattr] Label` still attaches the empty enum type." PyO3's `#[pyclass]` macro does not support zero-variant enums (no Python instances can be created, and the generated type infrastructure has no variants to enumerate). This design omits the label enum and `#[classattr] Label` entirely for zero-label rules (see "Empty Label Enum Handling"). The requirements text should be updated to match. Note: the requirements describe the trigger as "all items suppressed," but all-suppressed rules produce no types and hit the existing `RuntimeError` at `gsm2tree.py:117-122` before reaching label-enum generation. The realistic trigger is unlabeled INCLUDE items (types but no labels).

ANSWER: Don't bother updating requirements, just ignore the impossible requirements and follow this design.
