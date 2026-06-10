# Exploration: child-span-params-dedup TODO

Style: concise, no padding, no prescriptions. Facts and source-code ground truth only.

---

## Structures compared

### `_CHILD_SPAN_PARAMS` — `tests/test_phase4_fegen_rust_backend.py:118-126`

```python
_CHILD_SPAN_PARAMS = pytest.mark.parametrize(
    "node_class,append_method,child_method",
    [
        (fegen_rust_cst.Identifier, "append_name",  "child_name"),
        (fegen_rust_cst.Literal,    "append_value", "child_value"),
        (fegen_rust_cst.RawString,  "append_value", "child_value"),
    ],
    ids=["Identifier.child_name", "Literal.child_value", "RawString.child_value"],
)
```

Fields: `(node_class, append_method, child_method)` — 3 rows, 3 columns.

Module: `fegen_rust_cst` (the standalone Rust extension, importable only when built).

### `CLASS_LABEL_INFO` rows with `child_factory=_span` — `tests/test_fegen_rust_cst.py:55-57`

```python
(Identifier,   "NAME",          "name",         _span),   # line 55
(RawString,    "VALUE",         "value",        _span),   # line 56
(Literal,      "VALUE",         "value",        _span),   # line 57
```

Fields: `(class, label_for_Label_access, label_for_roundtrip, child_factory)` — 4 columns.

The `_span` rows are three of 14 rows in `CLASS_LABEL_INFO`. Module: `fltk._native.fegen_cst` (the embedded Rust CST, distinct from the standalone `fegen_rust_cst`).

---

## Are the structures actually duplicating each other?

### Shared content

Both encode the same three (class, label) pairs:

| Class        | label (method suffix) |
|--------------|-----------------------|
| `Identifier` | `name`                |
| `Literal`    | `value`               |
| `RawString`  | `value`               |

From this, both structures derive `append_{label}` and `child_{label}` method names.

### Differences

| Dimension               | `_CHILD_SPAN_PARAMS`                            | `CLASS_LABEL_INFO` (_span rows)                 |
|-------------------------|-------------------------------------------------|-------------------------------------------------|
| Module imported         | `fegen_rust_cst` (standalone extension)         | `fltk._native.fegen_cst` (embedded module)      |
| Class objects           | `fegen_rust_cst.Identifier` etc.               | `fltk._native.fegen_cst.Identifier` etc.        |
| Columns                 | 3: `(node_class, append_method, child_method)` | 4: `(class, Label-name, suffix, child_factory)` |
| Third param             | `child_method` = `"child_{label}"`             | `label_for_roundtrip` = raw label suffix        |
| Extra field             | none                                           | `label_for_Label_access` (uppercase variant)    |
| Extra field             | none                                           | `child_factory` callable (`_span`)              |
| `ids=` parameter        | explicit (`"Identifier.child_name"` etc.)      | derived from `ALL_CLASS_IDS`                    |
| Scope of parametrize    | 3 rows (terminal-child-only subset)             | all 14 rows (full class catalogue)              |

The two structures are **not isomorphic**: `_CHILD_SPAN_PARAMS` stores the fully-qualified method name (`"child_name"`), while `CLASS_LABEL_INFO` stores the raw suffix (`"name"`) and the caller computes `f"child_{suffix}"` at call site. Merging requires either expanding or collapsing one representation.

The class objects also come from **different modules**: `fegen_rust_cst` vs `fltk._native.fegen_cst`. These are distinct Python objects (confirmed by `test_module_is_standalone` at `tests/test_phase4_fegen_rust_backend.py:203-208`). A shared fixture would need to parameterize over both modules or pick one.

---

## Where each structure is consumed

### `_CHILD_SPAN_PARAMS` consumers — `tests/test_phase4_fegen_rust_backend.py`

Three test methods, all in `TestChildSpanAccessorContract` (lines 129-171):

- `test_sourceless_span_start_end` (line 138): calls `append_method` with a sourceless `Span(3,9)`, then `child_method`; checks `isinstance(result, Span)`, `.start`, `.end`, `.text() is None`, `.has_source() is False`.
- `test_source_bearing_span_text` (line 151): calls `append_method` with a source-bearing `Span.with_source(3,9,src)`, then `child_method`; checks `.text() == "lo wor"`.
- `test_append_rejects_terminalsrc_span` (line 165): calls `append_method` with a `tsrc.Span`; expects `TypeError("unsupported child type")`. Only uses `node_class` and `append_method`; `child_method` is unused (suppressed via `# noqa: ARG002`).

### `CLASS_LABEL_INFO` consumers — `tests/test_fegen_rust_cst.py`

Five test classes consuming all 14 rows via `_span` rows included:

- `TestConstructionDefaultSpan` (line 73): uses only `ALL_CLASSES` (class objects); label/suffix/factory not used.
- `TestChildrenIsList` (line 94): uses only `ALL_CLASSES`.
- `TestLabelAccess` (line 108): uses `(cls, label_for_Label_access)` — the uppercase variant name, not the suffix. Not present in `_CHILD_SPAN_PARAMS` at all.
- `TestAppendChildRoundtrip` (line 126): uses `(cls, suffix, child_factory)`.
- `TestExtendAndMaybe` (line 166): uses `(cls, suffix, child_factory)` and `(cls, suffix)`.

The `TestAppendChildRoundtrip.test_append_and_child_roundtrip` and `TestExtendAndMaybe` tests are the closest analog to `TestChildSpanAccessorContract` tests, but they test only value-equality roundtrip — not source preservation, `.text()`, `.has_source()`, or rejection of `tsrc.Span`. Those three behaviors are unique to `_CHILD_SPAN_PARAMS` consumers.

---

## What a shared conftest fixture would look like

The minimal shared data is `(class, label_suffix)` for the three terminal-child classes. The fixture would live in `tests/conftest.py` and export something like:

```python
# hypothetical shape
FEGEN_TERMINAL_CHILD_LABELS = [
    ("Identifier", "name"),
    ("Literal",    "value"),
    ("RawString",  "value"),
]
```

Each test file would then import this and:

- `test_phase4_fegen_rust_backend.py`: resolve class objects via `getattr(fegen_rust_cst, name)`, construct `child_method = f"child_{suffix}"`, `append_method = f"append_{suffix}"`.
- `test_fegen_rust_cst.py`: resolve class objects via module-level imports from `fltk._native.fegen_cst`; the `_span` `child_factory` and uppercase `label_for_Label_access` must be added separately or by convention (uppercase = `suffix.upper()`).

The `test_fegen_rust_cst.py` side is harder: `CLASS_LABEL_INFO` has 14 rows, three of which share the terminal-child shape. The fixture would only unify those three rows; the other 11 rows stay as-is. That means `CLASS_LABEL_INFO` would need to be assembled from two sources (shared fixture + local rows), adding complexity to a file that is currently a single clean list.

---

## Drift risk assessment

A label rename (e.g. `Identifier.name` → `Identifier.ident`) would require updating:

1. The Rust source that defines the CST methods (`fltk/src/` or `fltk-fegen-cst/src/`).
2. `CLASS_LABEL_INFO` in `test_fegen_rust_cst.py` (the suffix `"name"` at line 55, the uppercase `"NAME"` at line 55).
3. `_CHILD_SPAN_PARAMS` in `test_phase4_fegen_rust_backend.py` (the strings `"append_name"` and `"child_name"` at line 121).

Both test lists would fail loudly on the first pytest run — the accessor methods simply would not exist on the node class. The failure is immediate and unmissable; there is no silent drift scenario.

The risk is not undetected drift but **edit burden**: a label rename touches two files instead of one. With three (class, label) pairs total, the edit burden is at most 6 string values across two files.

---

## Line-count arithmetic

Current state:
- `_CHILD_SPAN_PARAMS`: 9 lines (lines 118-126).
- The three `_span` rows in `CLASS_LABEL_INFO`: 3 lines (lines 55-57).

After unification: a conftest fixture of ~6-8 lines replaces the 3-line `CLASS_LABEL_INFO` subset. The `_CHILD_SPAN_PARAMS` block shrinks to ~6 lines of fixture consumption (resolve classes + build parametrize). `CLASS_LABEL_INFO` assembly gains ~3 lines of fixture import and splice logic. Net change: roughly zero lines saved, structure complexity increases.

---

## Open factual questions

None — the structures, their consumers, and the refactor mechanics are fully determinable from the source.
