# Phase 3 Requirements: Rust CST Code Generator (`gsm2tree_rs.py`)

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

---

## User instruction (verbatim, binding through all workflow phases)

> "The basic shape of this phase is that we replace the hand-written phase 2 code with equivalent generated code; the phase2 commit serves as a *model* for code generation. At the end of phase 3, the hand-written code should be removed because the generated code passes all the same tests."

---

## Goals

Build `gsm2tree_rs.py`, a Python module that takes a `gsm.Grammar` and emits a `.rs` file containing PyO3 CST node classes. At phase end, the hand-written `src/cst_poc.rs` is deleted and replaced by generated Rust code that passes all existing tests in `tests/test_rust_cst_poc.py`.

---

## In scope

1. **`gsm2tree_rs.py`** — new Python module (parallel to `gsm2tree.py`) that generates Rust source text from a `gsm.Grammar`.
2. **Consistency with `CstGenerator` analysis** — the Rust generator must produce output consistent with `gsm2tree.py`'s model analysis (same label sets, child types, trivia insertion, class names). How the generator obtains this model data is a design choice.
3. **Generated `.rs` file** for the PoC grammar (the 2-rule grammar producing `Identifier` and `Items`) that replaces `src/cst_poc.rs`.
4. **`register_classes` function** in the generated Rust — a `pub fn register_classes(module: &Bound<'_, PyModule>) -> PyResult<()>` that registers all generated label enums and node structs into a given module.
5. **`lib.rs` update** — replace hand-written `mod cst_poc;` / direct `add_class` calls with `mod <generated_module>;` and a call to the generated `register_classes`.
6. **Deletion of `src/cst_poc.rs`** — the hand-written file is removed.
7. **All 27 acceptance criteria in `tests/test_rust_cst_poc.py` continue to pass** without modification to the test file.
8. **Generator tested on at least one additional grammar** beyond the PoC 2-rule grammar: specifically, `fegen.fltkg` (14 rules / 14 classes). Note: the phase plan references `fltk.fltkg`, but the correct grammar is `fegen.fltkg` (from which `fltk_cst.py` was generated; `fltk.fltkg` is broken). The generated Rust for this grammar must compile. A test instantiates every generated class, verifies construction, label access, and at least one per-label method per class.
9. **Generator tested on a minimal inline grammar** (e.g., the `numbers := digit+` pattern from `test_regression_empty_nary.py`) to validate single-rule, single-label, no-trivia edge cases.

## Out of scope

- Modifications to `plumbing.py`, `genparser.py`, or any runtime integration (Phase 4).
- Modifications to `fltk_cst.py` or any static consumer (`fltk_parser.py`, `fltk2gsm.py`) (Phase 5).
- CLI subcommand for Rust generation (Phase 4).
- Type stubs (`.pyi`) for generated Rust classes.
- Performance benchmarking.
- Bazel integration.

---

## System behavior

### Input

A raw `gsm.Grammar` object. The generator applies `add_trivia_rule_to_grammar` and `classify_trivia_rules` internally.

### Output

A string containing a complete, compilable `.rs` file.

### Processing

1. Instantiate `CstGenerator` with the grammar and `py_module=pyreg.Builtins` to populate `rule_models`.
2. For each rule in the grammar (in rule order), emit:
   - A `#[pyclass(eq, hash, frozen)]` label enum with `#[derive(Clone, PartialEq, Eq, Hash)]`, one variant per sorted label. Rust variant names are CamelCase (`rust_variant_name`). Python names are ALL_CAPS via `#[pyo3(name = "...")]`. The Python-visible type name is `{ClassName}_Label` via `name = "{ClassName}_Label"` on the `#[pyclass]`. `#[allow(non_camel_case_types)]` suppresses the Rust lint.
   - A `#[pymethods]` block for the label enum containing `__repr__` returning `"{ClassName}.Label.{VARIANT}"`.
   - A `#[pyclass]` node struct with `#[pyo3(get, set)] span: PyObject` and `#[pyo3(get)] children: Py<PyList>`.
   - A `#[pymethods]` block for the node struct containing: `#[new]` (keyword-only `span` defaulting to `crate::UNKNOWN_SPAN`), `#[classattr] Label` returning the label enum's type object, generic `append`/`extend`/`child`, per-label `append_{label}`/`extend_{label}`/`children_{label}`/`child_{label}`/`maybe_{label}`, `__eq__`/`__hash__`/`__repr__`.
3. Emit a `pub fn register_classes(module: &Bound<'_, PyModule>) -> PyResult<()>` that calls `module.add_class::<T>()?` for every label enum and node struct, label enums before their corresponding node structs.

### Trivia handling

The generator must replicate `gsm2tree.py`'s trivia insertion logic:
- If a rule has whitespace separators (checked via the equivalent of `rule_has_whitespace_separators`) and is itself a trivia rule, `Span` is added to its child types.
- If a rule has whitespace separators and is not a trivia rule, `"_trivia"` is added to its child types (mapped to class name `Trivia`).
- This affects which classes are generated (the `_trivia` rule becomes the `Trivia` class) but does not affect the Rust code structure — all children are `PyObject`.

### Name transformations

| Source | Transformation | Example |
|---|---|---|
| Rule name → class name | `"".join(part.capitalize() for part in rule_name.lower().split("_"))` | `"raw_string"` → `"RawString"`, `"_trivia"` → `"Trivia"` |
| Label → Python name | `label.upper()` | `"no_ws"` → `"NO_WS"` |
| Label → Rust variant | `"".join(part.capitalize() for part in label.split("_"))` | `"no_ws"` → `"NoWs"` |
| Label → method suffix | label as-is (lowercase, underscores preserved) | `"no_ws"` → `append_no_ws`, `child_no_ws` |
| Class name → label enum type | `{ClassName}_Label` | `"Items"` → `"Items_Label"` |

### Acceptance criteria

**AC-1: Test file unchanged.** `tests/test_rust_cst_poc.py` passes without modification.

**AC-2: Hand-written code removed.** `src/cst_poc.rs` does not exist after phase completion.

**AC-3: Generated code compiles.** `uv run --group dev maturin develop` succeeds.

**AC-4: Generated classes registered in `fltk._native`.** `from fltk._native import Identifier, Items, Span, UnknownSpan` works (same import path as the test file uses).

**AC-5: `register_classes` interface.** The generated `.rs` file exports a `pub fn register_classes(module: &Bound<'_, PyModule>) -> PyResult<()>`. `lib.rs` calls it instead of hand-written `add_class` calls.

**AC-6: All 27 Phase 2 acceptance criteria preserved.** Every behavioral assertion in `tests/test_rust_cst_poc.py` passes: label identity/equality, containment, discrimination, children-list identity, mutation visibility, cross-node extend, tuple structure, per-label accessors, isinstance, span setter/default, equality, unhashable, repr, None-label filtering.

**AC-7: `fegen.fltkg` generation compiles.** Generated Rust for the full `fegen.fltkg` grammar (14 classes) compiles without error.

**AC-8: `fegen.fltkg` smoke test.** A test instantiates every class generated from `fegen.fltkg`, verifies `ClassName.Label.VARIANT` access, `node.children` is a list, and at least one `append_{label}` / `child_{label}` round-trip per class.

**AC-9: Minimal grammar generation.** A test generates Rust from a single-rule grammar (e.g., `numbers := digit+`) and confirms the generator does not crash on trivial inputs. Whether this test compiles the output or only validates source text is a design choice.

**AC-10: Preamble correctness.** Every generated `.rs` file includes the required `use` declarations (`pyo3::prelude::*`, `pyo3::types::{PyList, PyTuple}`, `pyo3::PyTypeInfo`, `pyo3::exceptions::{PyTypeError, PyValueError}`, `crate::UNKNOWN_SPAN`).

**AC-11: Error messages match Phase 2 behavior.** `child_{label}` raises `ValueError("Expected one {label} child but have {count}")` (dynamic count). `maybe_{label}` raises `ValueError("Expected at most one {label} child but have at least 2")` (fixed string; early-breaks on count > 1). The `{label}` in the message uses the lowercase method-suffix form (e.g., `"name"`, `"no_ws"`). These match the committed Phase 2 code and the test assertions in `test_rust_cst_poc.py`.

**AC-12: Full test suite passes.** `uv run pytest` passes — no regressions in any existing test.

---

## User-visible surface

### New Python module

`fltk.fegen.gsm2tree_rs` — importable module containing the generator class.

### Public API

The module must expose a callable that accepts a `gsm.Grammar` and returns a `str` of compilable Rust source. The grammar is raw (not yet trivia-processed); the callable applies `add_trivia_rule_to_grammar` and `classify_trivia_rules` internally. Class/method naming is a design choice.

### No CLI surface in this phase

The generator is a library API only. CLI integration is Phase 4.

### Error behavior

If the grammar contains a rule with no labels (all items suppressed), the generator still emits a node struct with an empty label enum (zero variants). The `#[classattr] Label` still attaches the empty enum type. This matches `gsm2tree.py`'s behavior for such rules.

---

## Protocols / protocol schemas

### Python-visible API contract

The generated Rust classes must expose the same Python-visible API as the Phase 2 hand-written classes. The Phase 2 tests (`tests/test_rust_cst_poc.py`) define the behavioral contract. Internal Rust implementation details (method signatures, PyO3 attribute choices, file structure) are design choices.

---

## Constraints

- **Rust edition**: 2021.
- **Deterministic output**: Output should be deterministic to support diffing committed generated files. Labels are sorted alphabetically within each rule (matching `gsm2tree.py`). Rules are emitted in grammar rule order.
- **No runtime code generation**: The generator produces static Rust source. It does not invoke `cargo` or `maturin` — compilation is a separate step performed by the developer.
- **`UNKNOWN_SPAN` dependency**: Generated code references `crate::UNKNOWN_SPAN` (a `GILOnceCell<PyObject>` defined in `lib.rs`). The generator does not emit this definition; it is provided by the existing `lib.rs` infrastructure.
- **Python 3.10+**: Generator code uses Python 3.10+ syntax.
- **Line length**: 120 characters applies to the generator's Python source (project convention). Generated Rust output has no line-length requirement.

---

## Open questions

**OQ-fegen-compilation-test**: Should the `fegen.fltkg` compilation test (AC-7, AC-8) compile the generated Rust into a loadable extension, or only verify the source text is syntactically valid Rust? Compiling requires adding the generated module to `lib.rs` and rebuilding, which couples the test to the build system. Source-text validation (e.g., checking for balanced braces, required tokens) is weaker but decoupled. Recommendation: compile it. The generated module can be conditionally included in `lib.rs` behind a `#[cfg(test)]` or as a second module always compiled. The smoke test then imports classes from `fltk._native` (or a test submodule).

**OQ-empty-label-enum**: Zero-label rules are possible (`gsm2tree.py` populates labels only from items with non-None `item.label`; a rule with all unlabeled INCLUDE items has types but no labels; `gsm2tree.py` emits an empty Python `Label(enum.Enum)` which is valid). Rust enums cannot have zero variants. Options: (a) omit the label enum and `#[classattr] Label` entirely for such rules, (b) emit a label enum with a single sentinel variant that is never used, (c) treat zero-label rules as an error. The Python generator succeeds on such rules, so the Rust generator should too.
