# Quality review — batch 4 (66657a3)

## quality-1

**File:** `fltk/unparse/gsm2unparser_rs.py`, `_gen_child_prelude` / `_gen_validate_span_child`

`_gen_child_prelude` binds `child_tuple` only when `need_tuple=True`, yet its own label-check
block unconditionally references `child_tuple.0`.  The invariant — "pass `need_tuple=True`
whenever `item.label` is truthy" — is a hidden caller contract, not enforced by the method.

`_gen_validate_span_child` demonstrates the fragility: it computes
`need_tuple = bool(item.label) or num_variants > 1`, carrying the `bool(item.label)` term
solely to prevent the broken path inside `_gen_child_prelude`.  The two halves of the invariant
now live in separate methods.

**Consequence:** Every new caller of `_gen_child_prelude` (quantified-loop expansion, regex term
handling, nested-alternative terms — all deferred to later increments) must independently
reproduce this guard.  A caller that omits it generates silently broken Rust: `child_tuple`
referenced before binding, caught only at Rust compilation time rather than at Python generation
time.  The pattern will propagate as the generator is extended.

**Fix:** Inside `_gen_child_prelude`, replace the binding guard

```python
if need_tuple:
    lines.append("        let child_tuple = &children[pos];")
```

with

```python
if need_tuple or item.label:
    lines.append("        let child_tuple = &children[pos];")
```

The method then self-enforces the invariant, and `_gen_validate_span_child` can drop the
`bool(item.label)` term, simplifying its `need_tuple` calculation to just `num_variants > 1`.
