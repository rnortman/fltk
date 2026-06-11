# Exploration: TODO(rust-str-lit-shared) adversarial validation

Style note: concise, precise, token-dense. No fluff.

## Claim

> `_rust_str_lit` is only defined in `fltk/fegen/gsm2parser_rs.py`. `gsm2tree_rs.py` embeds Rust string literals in f-strings without going through an escaping helper, meaning any rule name or label containing characters that require escaping (backslash, double-quote, control chars) would produce malformed Rust there. Extract to a shared utility so both generators use the same escaping path.

---

## Verified facts

### 1. `_rust_str_lit` location

Defined exactly once: `fltk/fegen/gsm2parser_rs.py:33-46` (module level).

```python
def _rust_str_lit(s: str) -> str:
    """Return the Rust string literal content (no outer quotes) for string s."""
    out = []
    for ch in s:
        cp = ord(ch)
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif cp < _CTRL_MAX or cp == _DEL:
            out.append(f"\\u{{{cp:02x}}}")
        else:
            out.append(ch)
    return "".join(out)
```

Constants: `_CTRL_MAX = 0x20` (line 26), `_DEL = 0x7F` (line 27).

No occurrence in `gsm2tree_rs.py`. Confirmed by grep: no hits.

### 2. Where `gsm2tree_rs.py` embeds strings in Rust string literals

The following sites in `gsm2tree_rs.py` interpolate `label`, `class_name`, or derived names directly into Rust string-literal f-strings (no escaping helper):

- **line 380**: `f'            NodeKind::{variant} => "{canonical}",'` — `canonical` = `f"NodeKind.{class_name.upper()}"` (line 299), so `class_name` goes into a `&'static str` match arm.
- **line 444**: `f'#[pyclass(frozen, name = "{python_enum_name}")]'` — `python_enum_name` = `f"{class_name}_Label"` (line 411).
- **line 469**: `f'            {enum_name}::{rust_variant} => "{class_name}.Label.{python_name}",'` — both `class_name` and `python_name` go into a `&'static str`.
- **line 597**: `f'            "{class_name}: unsupported child type {{}}",`
- **line 739**: `f'#[pyclass(frozen, weakref, name = "{class_name}")]'`
- **line 934**: error message string containing `class_name` and `method_name` — but `method_name` is a Python-side constant string (`"append"` / `"extend"`), not a grammar identifier.
- **line 948**: `f'                        "{class_name}.{method_name}: label argument is not a {python_enum_name}; got {{}}",`
- **lines 1166, 1169, 1187, 1190, 1210, 1235, 1238, 1257, 1260, 1281**: `f'                _ => Err(CstError::UnexpectedChildType {{ label: "{label}" }}),'` and `f'                label: "{label}",'` — `label` goes into a `CstError` struct field (a Rust `&'static str`).
- **line 1428**: `f'                "Expected one {label} child but have {{count}}"'`
- **line 1431**: `f'        Ok(found.expect("invariant: {class_name}.child_{label}: count==1 but found==None; logic error"))'`
- **line 1458**: `f'                "Expected at most one {label} child but have at least 2",'`
- **line 1495**: `f"        Err(PyTypeError::new_err(\"unhashable type: '{class_name}'\"))"` — `class_name` interpolated into a Rust string literal containing single quotes (no double-quote risk, but backslash/control exposure).
- **line 1507**: `f'            "{class_name}(span={{span_repr}}, children=[<{{children_len}} child(ren)>])"'`

### 3. Is the bug reachable? — Identifier constraint

`fltk/fegen/fegen.fltkg:16`:
```
identifier := name:/[_a-z][_a-z0-9]*/  ;
```

The grammar regex for identifiers is `[_a-z][_a-z0-9]*`. This charset:
- Contains only lowercase ASCII letters, digits, and underscore.
- Excludes: backslash (`\`), double-quote (`"`), any control character (all < 0x20), DEL (0x7F), any non-ASCII character.

`gsm2tree_rs.py:18` mirrors this constraint as a Python-side guard:
```python
_IDENTIFIER_RE = re.compile(r"^[_a-z][_a-z0-9]*$")
```

`RustCstGenerator.__init__` (lines 60-80) validates every `rule.name` and every `item.label` against `_IDENTIFIER_RE` at construction time, raising `ValueError` if any fails.

**Consequence**: the characters that `_rust_str_lit` escapes — `\`, `"`, code points < 0x20 or == 0x7F — are all excluded from the identifier charset enforced by the grammar and by the `RustCstGenerator` constructor validation. A grammar that somehow bypassed the fltkg parser (e.g., a `gsm.Grammar` constructed directly in Python with an exotic rule name) would be caught by the `RustCstGenerator` constructor before any code is emitted.

The only input to `gsm2tree_rs.py` that is NOT a grammar identifier (and therefore not constrained to `[_a-z][_a-z0-9]*`) is `class_name`, which is derived from `rule_name` via `CstGenerator.class_name_for_rule_node`. That function applies `snake_to_upper_camel` from `fltk/fegen/naming.py:22`, which processes `rule_name`. Since `rule_name` is itself constrained to `[_a-z][_a-z0-9]*`, `class_name` is in `[A-Z][A-Za-z0-9]*` — no escaping-sensitive characters.

### 4. `_source_name` in `gsm2parser_rs.py`

`gsm2parser_rs.py:254` does pass `_source_name` through `_rust_str_lit`:
```python
escaped = _rust_str_lit(self._source_name)
```
`_source_name` is a free-form string (file path or description, `str | None`), so it CAN contain backslash or double-quote (e.g., Windows paths). This is the only actual use-case where escaping is needed and is being handled.

In `gsm2tree_rs.py`, the analogous sites are grammar identifiers and their CamelCase derivatives — neither can contain escapable characters given the current constraints.

### 5. Is the TODO's core claim correct?

**Partially.** The factual claim that `gsm2tree_rs.py` embeds names in Rust string literals without an escaping helper is true (lines listed in §2 above). The claim that this "would produce malformed Rust" given current identifier constraints is **not reachable**: the grammar format and the `RustCstGenerator.__init__` validator ensure no rule name or label can contain `\`, `"`, or control characters. The bug exists in theory (a handcrafted `gsm.Grammar` bypassing the grammar parser) but is blocked in practice for all legitimate grammar inputs.

### 6. `rust-naming-shared` relationship

`TODO(rust-naming-shared)` (`gsm2parser_rs.py:193`, `TODO.md:68`):

```python
def _child_enum_name(self, rule_name: str) -> str:
    # TODO(rust-naming-shared): The "Child" and enum-name conventions are also
    # encoded inline in gsm2tree_rs.py (_label_enum_rust_name, _child_enum_block).
    return self._class_name(rule_name) + "Child"
```

Both TODOs are about extracting shared Rust-codegen utilities out of these two files. The natural shared home would be `fltk/fegen/naming.py` (currently 22 lines, already imported by `gsm2tree_rs.py`) or a new `fltk/fegen/rust_naming.py`. Adding `_rust_str_lit` and naming helpers (`child_enum_name`, `label_enum_rust_name`, etc.) to the same module would resolve both TODOs in one move. `naming.py` is the only existing shared-utility leaf module in `fltk/fegen/`; it imports nothing from `fltk`.

### 7. Summary verdict on TODO validity

- **`_rust_str_lit` exclusively in `gsm2parser_rs.py`**: TRUE (`gsm2parser_rs.py:33`).
- **`gsm2tree_rs.py` embeds names without escaping helper**: TRUE (many sites, §2).
- **Bug is reachable for rule names or labels**: FALSE under current grammar + constructor validation; identifiers are `[_a-z][_a-z0-9]*`, no escapable chars possible.
- **Bug reachable via `_source_name` path**: NOT APPLICABLE — `_source_name` is only in `gsm2parser_rs.py` and is already escaped there.
- **TODO rationale survives?**: Weakly. The stated motivation (consistency / future-proofing if escaping rules change) is real but the current risk is theoretical. The TODO's primary practical value would be eliminating the code-drift risk between the two files, and enabling shared escaping if the identifier charset were ever widened. The TODO text overstates the current risk by omitting the identifier constraint.
- **Shared-module fix would also address `rust-naming-shared`**: YES. Both TODOs point at the same structural problem (helpers duplicated or split across `gsm2parser_rs.py` and `gsm2tree_rs.py`) and would naturally co-locate in the same new/extended module.
