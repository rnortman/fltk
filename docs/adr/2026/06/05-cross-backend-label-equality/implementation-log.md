# Cross-Backend Label Equality — Implementation Log

## Increment 1 — Python `Label` `__eq__`/`__hash__`/`_fltk_canonical_name` in `gsm2tree.py` (commit TBD)

Draft scope: Emit cross-backend eq/hash on Python `Label` enums in `gsm2tree.py` (§2.2): `_fltk_canonical_name` property, `__eq__` with same-type fast path + canonical-name cross-type path + `NotImplemented` for foreign operands, `__hash__` via canonical string. Regenerate `fltk_cst.py`. No Rust changes, no `NodeKind`, no `fltk2gsm.py` changes this increment.
