# Exploration: parser-bindings-name-collision TODO validation

Style: concise, no fluff, anchor every claim to code.

---

## Claim under review

> `_gen_python_bindings` registers `PyApplyResult` and `PyParser` as `"ApplyResult"` and `"Parser"` in the same module that registers one class per grammar rule. A grammar containing a rule named `parser` or `apply_result` generates a CST class with the same name (`Parser`/`ApplyResult`), and pyo3's `add_class` assignment silently shadows the first registration — the CST node class becomes unreachable as a module attribute. No generator-side check rejects or warns about the collision. Fix: in the generator (CST or parser side), raise an error at generation time when a rule's class name collides with the fixed names `Parser`, `ApplyResult`, `Span`, or `SourceText`. Location: `fltk/fegen/gsm2parser_rs.py` (`_gen_python_bindings`), `fltk/fegen/gsm2tree_rs.py` (class name validation).

**Verdict: Substantially correct. Two details need sharpening (see below).**

---

## What _gen_python_bindings actually registers

`gsm2parser_rs.py:813-923`, method `_gen_python_bindings`, emits a single `register_classes` fn
(lines 914-918 in the closing template literal):

```rust
pub fn register_classes(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<PyApplyResult>()?;
    module.add_class::<PyParser>()?;
    Ok(())
}
```

- `PyApplyResult` carries `#[pyclass(frozen, name = "ApplyResult")]` — gsm2parser_rs.py:831.
- `PyParser` carries `#[pyclass(name = "Parser")]` — gsm2parser_rs.py:850.

No per-rule classes are registered by this function. Per-rule CST handles are registered by
`cst::register_classes` in `gsm2tree_rs.py:1517-1531`.

---

## Registration order and the shadow direction

All call sites examined register into one pyo3 module in this order:

- `tests/rust_cst_fegen/src/lib.rs:18-21`:
  1. `m.add_class::<Span>()` — python name `"Span"` (fltk_cst_core::Span, no explicit name attr)
  2. `m.add_class::<SourceText>()` — python name `"SourceText"` (same)
  3. `cst::register_classes(m)` — NodeKind enum first, then per-rule: label enums
     (`{ClassName}_Label`) then handles (`{ClassName}`)
  4. `parser::register_classes(m)` — `"ApplyResult"` then `"Parser"`

Same pattern at `src/lib.rs:20-21` for the main `fltk._native` module.

For a rule named `parser` (class name `Parser`):
- Step 3 adds the CST handle `PyParser` as `"Parser"`.
- Step 4 adds the parser's `PyParser` as `"Parser"`.
- **The parser's `PyParser` is last; it wins. The CST node for the `parser` rule becomes
  unreachable as a module attribute.**

For a rule named `apply_result` (class name `ApplyResult`): same logic, same outcome.

For a rule named `span` (class name `Span`):
- Step 1 adds `fltk_cst_core::Span` as `"Span"`.
- Step 3 adds the CST handle `PySpan` as `"Span"`, overwriting fltk_cst_core::Span.
- Parser does NOT re-register `"Span"`. The original `Span` becomes unreachable.

For a rule named `source_text` (class name `SourceText`): same as `span` — step 3 overwrites step 2.

---

## Does pyo3 `add_class` silently shadow, or fail to compile?

**pyo3 0.23.5** (`Cargo.lock`). `add_class` calls `add`, which calls `module.setattr`
(`pyo3-0.23.5/src/types/module.rs:507`). `setattr` is `PyObject_SetAttr` — unconditional
overwrite; returns `Ok(())` on success. No duplicate-name check exists. `__all__` gets the
name appended again (harmless for attribute access).

**Rust compilation does not fail.** Two Rust types with the same `#[pyclass(name = "...")]`
are valid Rust — they live in different Rust modules (`mod cst` vs the parser's
`mod python_bindings`). `T::NAME` is a `const &str` per type; the identity at Python runtime
comes from which type was registered last via `setattr`.

---

## Is the fixed-name list in the TODO complete?

The TODO comment at `gsm2parser_rs.py:816-820` lists `'Parser'`, `'ApplyResult'`, `'Span'`,
`'SourceText'`. This list is **incomplete**:

- **`NodeKind`** is a fixed Python class name emitted by `gsm2tree_rs.py:355`
  (`#[pyclass(frozen, name = "NodeKind")]`). It is registered FIRST inside
  `cst::register_classes` (line 1522). If any grammar rule is named `node_kind`
  (class name `NodeKind`), the CST handle for that rule (also python name `"NodeKind"`,
  registered per-rule later in the same `cst::register_classes` loop — lines 1527-1528)
  would overwrite the `NodeKind` enum, making `NodeKind` unreachable by name. This is a
  purely CST-internal collision, not a parser-vs-CST collision.

- **`{ClassName}_Label`** pattern: each rule with labels registers a label enum as
  `"{ClassName}_Label"`. A rule named e.g. `foo_label` (class `FooLabel`) registers a handle
  `"FooLabel"` — no underscore — so label-enum names (`"Foo_Label"`) are structurally safe
  from handle-name collisions as long as rule names do not contain underscores-then-label.
  This is not an issue in practice but the exclusion is implicit, not enforced.

---

## Does any existing grammar trigger the collision?

`fegen.fltkg` rules: `grammar`, `rule`, `alternatives`, `items`, `item`, `term`, `disposition`,
`quantifier`, `identifier`, `raw_string`, `literal`, `_trivia`, `line_comment`, `block_comment`.
None maps to `Parser`, `ApplyResult`, `Span`, `SourceText`, or `NodeKind` via
`naming.snake_to_upper_camel`. No collision in the shipped grammar.

---

## Does the Python backend have the same collision class?

**No.** The Python backend generates separate files: `fltk_cst.py` (CST node classes) and
`fltk_parser.py` (class `Parser`). They are separate Python modules with separate namespaces.
A rule named `parser` would produce a CST class `Parser` in `fltk_cst.py` and `class Parser`
in `fltk_parser.py` — different modules, no shadowing.

`gsm2tree.py:46-47` generates `class_name_for_rule_node` via `naming.snake_to_upper_camel`.
`gsm2parser.py:49` sets `cname="Parser"` on the parser class. Different modules: no collision.

---

## Where does validation currently live?

`gsm2tree_rs.py:56-80`, `RustCstGenerator.__init__`:
- Validates rule names against `_IDENTIFIER_RE = re.compile(r"^[_a-z][_a-z0-9]*$")` (line 18).
- Validates item labels against the same regex (lines 66-72).
- Checks item labels against `_RESERVED_LABELS = {"children": "extend_children"}` (lines 24-26,
  73-80) — raises `ValueError` if a label would generate a method name colliding with
  `extend_children`.

No check on rule-name-derived class names against fixed registered Python names.

`gsm2parser_rs.py:816-820` contains a TODO comment but no check:
```python
TODO(parser-bindings-name-collision): add a generation-time check that raises an
error when any grammar rule's CamelCase class name collides with the fixed registered
names ('Parser', 'ApplyResult', 'Span', 'SourceText') to prevent silent module-level
shadowing of generated CST node classes.
```

The `_RESERVED_LABELS` mechanism in `gsm2tree_rs.py:24-26` is the precedent pattern for
generation-time collision rejection; it raises `ValueError` at `RustCstGenerator.__init__`
(line 73-80).

---

## Summary of discrepancies vs. the claim

1. **Shadow direction is correct**: for `parser`/`apply_result` rules, the parser module's fixed
   class wins (registered last), making the CST node unreachable. Claim says "CST node class
   becomes unreachable" — accurate.

2. **"No generator-side check"**: accurate. The `_RESERVED_LABELS` dict at gsm2tree_rs.py:24
   covers label names only; no analogous check for rule-name-derived class names.

3. **Fixed-name list incomplete**: `NodeKind` is missing from the claim's list
   (`'Parser'`, `'ApplyResult'`, `'Span'`, `'SourceText'`). For a rule named `node_kind`,
   the NodeKind enum (registered first in `cst::register_classes`) is silently overwritten by
   the CST handle (registered second in the same function).

4. **"Rust-side names a rule `parser` generates"**: a rule `parser` produces Rust data struct
   `Parser` in `cst.rs` and Rust handle `PyParser` in `cst.rs`. The parser module also defines
   a Rust struct `Parser`. These are in different Rust modules (`mod cst` vs `mod python_bindings`
   in the parser file), so the Rust names are `cst::Parser` vs `Parser` — **no Rust
   compilation error**. The collision is purely at the Python module attribute level.

5. **Natural place for a check**: `RustCstGenerator.__init__` at gsm2tree_rs.py:56 (where
   identifier and label validation already occurs). The check would need to know the full
   fixed-name set including `NodeKind` (a cst-generated fixed name) plus `Parser`,
   `ApplyResult`, `Span`, `SourceText` (from lib.rs integration). Alternatively, a partial
   check covering only the parser-side fixed names could live in `RustParserGenerator.__init__`
   or `_gen_python_bindings`.
