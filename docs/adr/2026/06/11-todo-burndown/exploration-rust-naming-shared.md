# Adversarial validation: TODO(rust-naming-shared)

Concise. Precise. Token-dense. No preamble. No padding.

---

## Claim under review

> The `XChild` and `XLabel` naming conventions for generated Rust enums are encoded
> independently in `gsm2parser_rs.py` (`_child_enum_name`, `_class_name`) and
> `gsm2tree_rs.py` (`_label_enum_rust_name`, inline `f"{class_name}Child"` in
> `_child_enum_block`). A rename in one place without the other produces parser code
> that references non-existent CST enum names (caught only at `cargo` compile time).
> Extract naming helpers to `RustCstGenerator` so both generators read from a single
> source.

---

## Duplication sites — verified

### `XChild` naming

**gsm2parser_rs.py: `_child_enum_name`** (line 192–197)
```python
def _child_enum_name(self, rule_name: str) -> str:
    # TODO(rust-naming-shared): ...
    return self._class_name(rule_name) + "Child"
```
- Called at lines 550, 965.
- `_class_name` (line 188–190) delegates to `self._cst._py_gen.class_name_for_rule_node`.

**gsm2tree_rs.py: `_child_enum_block`** (line 497)
```python
enum_name = f"{class_name}Child"
```
- Repeated at line 621 (inside `_node_block`) as another bare `f"{class_name}Child"`.
- Also at line 1058 inside `_label_type_info`:
  `enum_name = f"{self._py_gen.class_name_for_rule_node(rule_name)}Child"`

So there are **three** independent inline constructions in `gsm2tree_rs.py` (lines 497, 621, 1058),
plus one method in `gsm2parser_rs.py` (line 197). Total duplication sites: **4**.

The TODO cites only `_child_enum_block` — it misses lines 621 and 1058.

### `XLabel` naming

**gsm2tree_rs.py: `_label_enum_rust_name`** (lines 400–406) — static method
```python
@staticmethod
def _label_enum_rust_name(class_name: str) -> str:
    return f"{class_name}Label"
```
Called at lines 427, 622, 865, 939, 1525. This is a method, not inlined.

`gsm2parser_rs.py` does **not** construct label enum names directly — it delegates to
`self._cst._label_type_info` (line 201) which is `RustCstGenerator._label_type_info`
(gsm2tree_rs.py line 1038). That method constructs `enum_name` at line 1058 via inline
`f"...Child"` (not via `_label_enum_rust_name`). For label enum names specifically,
`gsm2parser_rs.py` never independently constructs them; it only uses `_child_enum_name`
for child (not label) enums.

---

## Dependency direction

`gsm2parser_rs.py` already imports `RustCstGenerator` from `gsm2tree_rs.py`:

```python
# gsm2parser_rs.py line 23
from fltk.fegen.gsm2tree_rs import RustCstGenerator
```

`gsm2parser_rs.py` line 82 holds a `self._cst: RustCstGenerator` instance.
`gsm2tree_rs.py` does **not** import from `gsm2parser_rs.py`.

Dep direction: `gsm2parser_rs → gsm2tree_rs`. No cycle; `RustCstGenerator` is already
the correct home for shared naming methods. Adding a helper there requires no new coupling
or new imports in either direction.

---

## Is "caught only at cargo compile time" accurate?

There is no generation-time cross-check between the two generators for name consistency.
`gsm2parser_rs.py` constructs `_child_enum_name` independently (line 197), and the
`RustCstGenerator` constructs `f"{class_name}Child"` independently (lines 497, 621, 1058).
Neither generator calls the other's naming method, and no assertion verifies they agree.

A generation-time check **is possible**: since `gsm2parser_rs.py` holds `self._cst`,
it could call a `RustCstGenerator.child_enum_name(rule_name)` method and the two would
converge by construction. Currently no such check exists. The claim "caught only at
`cargo` compile time" is **accurate** for the status quo.

There is also a `TODO(parser-bindings-name-collision)` at gsm2parser_rs.py line 816
noting a different (but adjacent) generation-time check gap; unrelated.

---

## Is `RustCstGenerator` the right home?

Yes, for three reasons supported by the code:

1. `RustCstGenerator` already owns `_label_enum_rust_name` (gsm2tree_rs.py line 400).
2. `gsm2parser_rs.py` already holds `self._cst: RustCstGenerator` and already delegates
   `_class_name` through it (line 190) and `_label_type_info` through it (line 201).
3. `gsm2tree_rs.py` has no import of `gsm2parser_rs.py`; adding helpers to
   `RustCstGenerator` is dep-direction-safe.

---

## TODO(rust-str-lit-shared) — relationship assessment

`_rust_str_lit` is defined only in `gsm2parser_rs.py` (lines 33–46).
`gsm2tree_rs.py` does not import or call it; it embeds Rust string literals (rule names,
label names, class names) directly in f-strings without escaping.

Both TODOs identify that `gsm2tree_rs.py` is missing a helper that lives only in
`gsm2parser_rs.py`. Both would be resolved by creating a shared utility module (e.g.
`fltk/fegen/rust_codegen_util.py` or `fltk/fegen/naming_rs.py`) and importing from
both generators. They are **naturally co-located fixes** — the same new module would hold
`rust_str_lit` (for `rust-str-lit-shared`) and `child_enum_name`/`label_enum_name` helpers
(for `rust-naming-shared`). Alternatively, both helpers could move to `RustCstGenerator`
(already the dep target), but `_rust_str_lit` is a pure function with no grammar state,
so a module-level utility is also idiomatic.

There is **no blocker** to fixing either TODO. No circular dep, no missing infrastructure.

---

## Summary of factual corrections to the claim

1. **Three inline `XChild` constructions in `gsm2tree_rs.py`**, not one: lines 497,
   621, 1058. The claim cites only `_child_enum_block` (line 488/497).
2. `_class_name` in `gsm2parser_rs.py` (line 188) is **not** an independent naming
   convention — it delegates directly to `self._cst._py_gen.class_name_for_rule_node`,
   the same function used in `gsm2tree_rs.py`. Only the `+Child` suffix in
   `_child_enum_name` (line 197) is independent.
3. The claim does not note that `gsm2parser_rs.py` **already imports
   `RustCstGenerator`** (line 23) and already delegates to it for related naming,
   making the extraction straightforward with no new coupling.
4. "Caught only at `cargo` compile time" — **accurate** as stated.
5. `rust-str-lit-shared` and `rust-naming-shared` are **naturally co-located** fixes;
   both address helpers missing from `gsm2tree_rs.py` that exist in `gsm2parser_rs.py`.
