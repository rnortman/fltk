# TODO(cst-protocol-generator-refactor) Triage

Source: `fltk/fegen/gsm2tree.py`

## Do all four cited functions exist?

Yes, all four exist at the cited locations:

- `py_annotation_for_model_types` — `gsm2tree.py:85–93`
- `protocol_annotation_for_model_types` — `gsm2tree.py:402–432`
- `py_class_for_model` — `gsm2tree.py:192–349`
- `_protocol_class_for_model` — `gsm2tree.py:518–615`

The TODO comment at `gsm2tree.py:399–401` repeats the slug and makes the same claim verbatim.

---

## Annotation pair: `py_annotation_for_model_types` vs `protocol_annotation_for_model_types`

### `py_annotation_for_model_types` (lines 85–93) — 9 lines

```python
def py_annotation_for_model_types(self, *, model_types: Iterable[ModelType], in_module: bool = False) -> str:
    iir_types = [self.iir_type_for_model_type(model_type) for model_type in model_types]
    assert len(iir_types) > 0
    py_types = sorted(pycompiler.iir_type_to_py_annotation(typ, self.context) for typ in iir_types)
    if in_module:
        py_types = sorted(f'"{typ.removeprefix(".".join(self.py_module.import_path) + ".")}"' for typ in py_types)
    if len(py_types) > 1:
        return f"typing.Union[{', '.join(py_types)}]"
    return py_types[0]
```

Approach: convert all model_types through `iir_type_for_model_type` → `iir_type_to_py_annotation`, sort, optionally quote and strip module prefix, then wrap in Union.

### `protocol_annotation_for_model_types` (lines 402–432) — 31 lines

Approach: iterate model_types, dispatch on `isinstance(model_type, str)` (rule refs vs library types), produce quoted forward refs for rule refs and unquoted `iir_type_to_py_annotation` paths for library types, deduplicate, sort, wrap in Union. Also raises on empty parts with a descriptive error (vs. bare `assert` in py version).

**Structural divergence — not just "annotation resolver" differences:**

1. **Type dispatch is fundamentally different.** `py_annotation_for_model_types` routes every model_type through `self.iir_type_for_model_type` (which handles both str rule refs and TypeKeys uniformly), then calls `iir_type_to_py_annotation`. `protocol_annotation_for_model_types` branches explicitly on `isinstance(model_type, str)` to quote rule refs as `'"RuleName"'` (forward references within the protocol module) while treating library TypeKeys differently. This branching cannot be hidden behind a simple "annotation resolver" callback without passing module-context or an enum flag into the callback.

2. **The `in_module` bool in `py_annotation_for_model_types`** is a second mode switch that strips and re-quotes the module prefix from already-computed annotations; the protocol version never needs this because it controls quoting from the start.

3. **Error handling differs**: protocol version raises `ValueError` with context; py version uses `assert`.

4. **Deduplication**: protocol version calls `sorted(set(parts))`; py version does not deduplicate (relies on model having no duplicates).

**LOC saved if unified:** The two functions are 9 and 31 lines. A shared skeleton would need to accept at minimum: a per-type resolver callback, a flag/strategy for quoting behavior, an error-handling mode. Given the dispatch asymmetry, the skeleton would be ~12–15 lines of plumbing with two resolver implementations of ~5–8 lines each. Net saving: ~10 lines at best, negative clarity.

---

## Class-generation pair: `py_class_for_model` vs `_protocol_class_for_model`

### `py_class_for_model` (lines 192–349) — 158 lines

Emits a `@dataclass` with:
- Nested `Label` enum with `_emit_cross_backend_eq_hash` applied
- Three fields: `kind: Literal[NodeKind.X]`, `span`, `children: list[tuple[Optional[Label], T]]` with dataclass default
- `append(child, label)` — body calls `self.children.append((label, child))`
- `extend(children, label)` — body calls `self.children.extend(...)`
- `child()` — validates exactly one child, returns it
- Per-label quintet: `append_<l>`, `extend_<l>`, `children_<l>`, `child_<l>`, `maybe_<l>`
  - `children_<l>` uses `typing.cast` when `len(model.types) > 1`
  - `child_<l>` and `maybe_<l>` have multi-line bodies with validation and return statements

Returns `[ClassDef, *canonical_name_assignment_stmts]`.

### `_protocol_class_for_model` (lines 518–615) — 98 lines

Emits a `typing.Protocol` class with:
- Nested `Label` class (plain `pygen.klass`, no base) with `ClassVar[object]` annotations only (no enum, no `_emit_cross_backend_eq_hash`)
- Conditional `kind` field: emits `Literal[NodeKind.X]` with runtime default only if `rule_name and self.py_module.import_path`, else `kind: object`
- `span` field (no default)
- `children` field: `list[tuple[Optional[Label], T]]` if labels present, else `list[tuple[None, T]]` (asymmetry absent in py version)
- `append(child, label)` — body is `...`
- `extend(children, label)` — `label` annotation is `Optional[Label]` or `None` depending on labels presence
- `child()` — body is `...`; return type is `tuple[Optional[Label], T]` or `tuple[None, T]`
- Per-label quintet: `append_<l>`, `extend_<l>`, `children_<l>`, `child_<l>`, `maybe_<l>` — all bodies are `...`

Returns `ClassDef` only (no post-class stmts — those are handled by `_protocol_class_for_model_with_assignments`).

**Structural divergences — beyond "method bodies":**

1. **Label nested class differs in kind.** py: `pygen.dataclass` outer + `pygen.klass("Label", bases=["enum.Enum"])` inner + `_emit_cross_backend_eq_hash`. Protocol: `pygen.klass(class_name, bases=["typing.Protocol"])` outer + `pygen.klass("Label")` (no base) inner + `ClassVar[object]` annotations, no eq/hash. These are structurally incompatible — different outer base, different inner base, different body content, different post-class treatment.

2. **`children` field shape differs conditionally.** py: always `list[tuple[Optional[Label], T]]`. Protocol: `list[tuple[Optional[Label], T]]` when labels present, `list[tuple[None, T]]` when absent. A unified skeleton must carry this conditional, making it an explicit branch parameter.

3. **`append`/`extend` `label` parameter type differs.** py: always `Optional[Label]`. Protocol: `Optional[Label]` when labels, `None` when no labels.

4. **`child()` return type differs.** py: always `tuple[Optional[Label], T]`. Protocol: conditional on labels.

5. **`kind` field emission is conditional in protocol, unconditional in py.** Protocol checks `rule_name and self.py_module.import_path`; py always emits `Literal[NodeKind.X]`.

6. **`span` has a default in py** (`= fltk.fegen.pyrt.terminalsrc.UnknownSpan`), none in protocol.

7. **Post-class assignments are handled differently.** `py_class_for_model` (line 347–348) calls `_emit_label_canonical_name_assignments` which emits `Class.Label.X._fltk_canonical_name = "..."`. `_protocol_class_for_model_with_assignments` (line 501–516) emits `Class.Label.X = _ProtocolLabelMember("...")` — a completely different sentinel type.

8. **`children_<l>` cast logic in py** (`typing.cast` when `len(model.types) > 1`) is absent from the protocol version (all bodies are `...`).

**LOC saved if unified:** The py class function is 158 lines, the protocol class function is 98 lines, plus 16-line `_protocol_class_for_model_with_assignments`. A shared skeleton emitting the common structural frame (label loop, quintet pattern, field names) could avoid repeating the label loop iteration (~5×2 = 10 function-emit calls × 2 generators = ~40 lines of parallel `pygen.function(f"append_{label}", ...)` / `fn.body.append(pygen.stmt("..."))` pairs). The quintet loop in py is lines 273–345 (72 lines); in protocol it's lines 585–613 (29 lines, shorter because all bodies are `...`). A unified loop with injected body-emitters would be ~30–35 lines plus ~20 lines of strategy objects — saving perhaps 40–50 lines at the cost of indirection.

The non-quintet portions (field declarations, outer klass setup, Label sub-class) have 7 structural differences listed above. Each would require a strategy parameter or conditional. A "shared skeleton" handling all of these would have 7+ injection points.

---

## Feasibility Assessment

**The TODO's claim that "both pairs share identical structure... with only the annotation resolver, Label body, method bodies, and base class differing" understates the divergence.** The actual differences are:

Annotation pair: fundamentally different dispatch logic (uniform iir path vs. explicit str/TypeKey branch); the `in_module` strip-and-requote mode has no analog in the protocol version. A shared skeleton is possible but saves ~10 lines at the cost of a callback with non-trivial context requirements.

Class-generation pair: 7 distinct structural asymmetries beyond method bodies. A "shared skeleton with injected strategies" would require 7+ strategy parameters/callbacks. The resulting abstraction would be harder to read than the current duplication and would couple two generators that are conceptually and functionally distinct (concrete dataclass emitter vs. structural Protocol emitter).

**The estimate of "~120 lines saved" is plausible for raw LOC but ignores the 7-point structural divergence.** The realistic outcome is a unified function of ~120 lines with 7+ mode parameters/callbacks, replacing two functions of 158 + 98 lines — a net reduction of ~80–100 lines of body code but at the cost of a multi-mode helper that is harder to modify correctly (any future change must account for all modes).

**The "any new per-label accessor must be applied in both generators" concern is valid and real.** Adding a `count_<l>` accessor or changing Union syntax requires edits in two places. However, the protocol body for any per-label accessor is always a single `pygen.stmt("...")`, so the protocol-side change for any new accessor is trivial (one line per accessor). The py-side change is non-trivial (multi-line body). These bodies are not shareable — they diverge by design.

**Verdict: awkward multi-mode helper, not a clean win.** The per-label quintet loop is the only part where a shared skeleton would be clearly beneficial, and that part could be extracted as a standalone helper (e.g., `_emit_label_quintet_loop(labels, annotation_fn, body_fn)`) without unifying the whole class-generation path. That narrower refactor — extracting only the quintet loop — would save ~40 lines without the 7-way mode-parameter complexity.
