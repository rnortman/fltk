# Settled design direction (from interactive design discussion with the user)

Authoritative steer for the design. These mechanism decisions were settled with the user; design within them (work out the details, edge cases, generator wiring, tests). If any turns out infeasible against the working tree / pyright, surface it as an open question rather than silently diverging.

1. **Cross-backend equality is canonical-name-keyed**, emitted by BOTH generators (Python `gsm2tree.py` + the Rust codegen). Covers TWO enum families:
   - the per-node `Label` enums (existing), and
   - a NEW `NodeKind` enum (see #2).
   `__hash__` must move in lockstep with `__eq__` (same canonical key); equality must be symmetric and non-raising on unrelated objects / None (return False / NotImplemented, never raise). Rust side needs a hand-written `__richcmp__`/`__hash__` (the derived `#[pyclass(eq, hash)]` is same-type only). IntEnum value-equality is rejected.

2. **Type narrowing uses a per-node `kind` discriminant, NOT label-keyed tuple unions.** Rationale settled: destructuring `for label, child in node.children` severs the label↔child correlation for pyright (no correlated unpacking), so label-keyed tuple discrimination fails on the common idiom. An attribute discriminant on the node is what pyright narrows reliably and works on a bare node with no parent.
   - Introduce a new `NodeKind` enum: one member per node/rule type (distinct axis from the parent-scoped `Label` enums — `Label` = a child's role, `NodeKind` = a node's type).
   - Generate on every node a discriminant `kind: Literal[NodeKind.<Rule>]` (declared per-node in the Protocol so unions narrow). Consumers narrow via `if child.kind == NodeKind.Item:`.
   - Discriminant is the ENUM, not a string. The user explicitly prefers enums over stringly-typed tags for typo-safety and clean user code, accepting that the comparison is a cross-backend enum `==` (covered by the #1 machinery — no separate mechanism).

3. **`self.cst` must be fully removed from `fltk2gsm.py`** as the in-tree proof. Label comparisons reference the static module-level `cst` enum constants (cross-backend-equal via #1); the two `isinstance(item, self.cst.Item)` sites become `child.kind`-based narrowing (per the isinstance-vs-label investigation, they carry no information the label/kind doesn't). Both Python and Rust backends must yield identical `gsm.Grammar` (existing `test_*_rust_equals_python`).

4. This is a FRAMEWORK feature: everything (`NodeKind`, `kind` discriminant, cross-backend eq/hash) is generator-emitted for EVERY grammar and usable by any out-of-tree fltk consumer — never an fltk-internal special case. `fltk2gsm.py` is merely the first in-tree user.

Known caveats to address (from isinstance-vs-label-investigation.md): union-typed labels (one label → multiple types) still need discriminant narrowing within the union; raw `(None, child)` children (trivia vs unlabelled) — but with the trivia fix already landed and typed accessors, this should not surface.
