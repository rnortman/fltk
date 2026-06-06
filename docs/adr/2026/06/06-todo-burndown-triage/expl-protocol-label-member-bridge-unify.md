# TODO Burndown Triage: protocol-label-member-bridge-unify

Concise. Precise. No padding.

## Claim Verification

**Claim**: `_emit_protocol_label_member_class` uses raw `ast.parse()` for `__eq__`/`__hash__` instead of calling `_emit_cross_backend_eq_hash`.

**Verdict: TRUE.**

`fltk/fegen/gsm2tree.py:451-468` — `_emit_protocol_label_member_class` calls `ast.parse("""class _ProtocolLabelMember: ...""")` and returns the parsed body. The class literal includes `__init__`, `__eq__`, `__hash__`, `__repr__` — entirely via string parsing.

`fltk/fegen/gsm2tree.py:100-132` — `_emit_cross_backend_eq_hash` is a `@staticmethod` that accepts `enum_klass: ast.ClassDef` and appends `__eq__` and `__hash__` using `pygen` calls (not `ast.parse`). It is pygen-based throughout.

## Structural Differences Between the Two Implementations

Both implement the same three-case `__eq__` contract:
1. `other is self` → `True`
2. Same-type fast path
3. `getattr(other, '_fltk_canonical_name', None)` cross-type comparison

**The same-type fast path diverges:**

- `_emit_cross_backend_eq_hash` (line 121): `type(other) is type(self): return self.name == other.name`
  — Uses `.name` (the enum member name attribute). The TODO claim calls this the "enum uses `.name`" path.

- `_emit_protocol_label_member_class` (line 459): `type(other) is type(self): return self._fltk_canonical_name == other._fltk_canonical_name`
  — Uses `._fltk_canonical_name`. This makes sense because `_ProtocolLabelMember` is NOT an enum and has no `.name`.

**`__hash__`**: Both use `hash(self._fltk_canonical_name)` — identical.

**`_ProtocolLabelMember`-only extras**: `__init__` (sets `_fltk_canonical_name` from constructor arg) and `__repr__` are present in the `ast.parse` block and have no counterpart in `_emit_cross_backend_eq_hash`, which targets enum classes where `_fltk_canonical_name` is set post-class via `_emit_canonical_name_assignments`.

## Feasibility of Unification

`_emit_cross_backend_eq_hash` signature: `(enum_klass: ast.ClassDef) -> None` — takes an existing ClassDef and appends to it. It cannot emit `_ProtocolLabelMember` as-is because:

1. It appends to an existing ClassDef; `_emit_protocol_label_member_class` returns a fully constructed list of statements (ClassDef included).
2. The same-type fast path must differ: enum uses `.name`; `_ProtocolLabelMember` uses `._fltk_canonical_name`. Sharing requires a parameter (e.g., `same_type_attr: str = "name"`).
3. `_ProtocolLabelMember` needs `__init__` and `__repr__` that `_emit_cross_backend_eq_hash` does not emit — a second parameter or separate helper for those.

A parameterized version would need at minimum `same_type_attr` and likely `emit_init: bool`. This is strictly more complex than the current two-function arrangement.

## What Would Actual Drift Look Like?

The cross-type path (case 3) is identical and is the load-bearing contract. A change to the cross-type protocol (e.g., renaming `_fltk_canonical_name`) would need updating in both places — that is the concrete drift risk.

The same-type fast path (case 2) is necessarily different and is not a drift risk; the divergence is correct by construction.

## Open Factual Questions

None. The code is unambiguous.

## Summary

The TODO claim is factually accurate. The two implementations have identical cross-type logic and intentionally different same-type logic. Unification into a shared pygen helper is feasible but requires parameterization (`same_type_attr`, `emit_init`) that adds complexity without eliminating lines — the shared helper would be longer than either current function. The concrete drift risk is limited to the cross-type `_fltk_canonical_name` attribute name, which appears in both functions at lines 123 and 461.
