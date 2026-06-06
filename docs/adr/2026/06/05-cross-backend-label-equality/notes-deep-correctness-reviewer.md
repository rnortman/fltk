# Deep correctness review — cross-backend label equality + NodeKind

Reviewed: 854e1ad..c57f888. Mandate: does the code do what it appears to do (logic/control/data flow).

Notes for any agent editing this doc: concise, precise, unambiguous.

## Verification performed (empirical, against built ext)
- Python label eq: distinct=False, same=True, vs None/int/object/str=False, `!=` correct, hash works.
- Cross-backend py↔rust (embedded `fltk._native.fegen_cst`): `==` both directions True, diff-member False, hash agreement True, set collapse to 1, dict cross-retrieval works.
- NodeKind: `rust.Item().kind == py.NodeKind.ITEM` True; cross-family `NodeKind.ITEM == Label.NO_WS` False (disjoint by construction holds); `node == label` False (marker not on nodes).
- AC7 symmetric (`None == rust.X`) False; no raises.
- tests/test_cross_backend_label_equality.py 42 passed; test_phase4_fegen_rust_backend + test_gsm2tree_rs 82 passed.
- Member-name consistency py vs rust verified: node `kind` field member name, NodeKind enum member, and canonical string all derive from `class_name_for_rule_node(rule).upper()` on both backends — identical, confirmed at runtime.

## Findings

No correctness findings.

Logic traced and confirmed sound:
- Python `__eq__` (gsm2tree.py emit): `other is self` → `type(other) is type(self)` member-name compare → canonical-name cross-type → `NotImplemented` for foreign. Returns `NotImplemented` (not False) on foreign operand, so reflected Rust `__eq__` runs and `py==rust` reaches True. Same-type fast path preserves same-backend filter semantics (the stored label *is* the member). Returning `NotImplemented` under a `-> bool` annotation is runtime-correct (typing-only concern, out of lane).
- Rust `__eq__`: own-type `extract` fast path → `getattr(other,"_fltk_canonical_name")` string compare → `NotImplemented`. Errors in getattr/extract are swallowed to `NotImplemented` (no raise; matches design AC7).
- Hash agreement: both backends route through CPython `hash(PyString)` (PyAnyMethods::hash), so per-process salted hashes match. -1 sentinel remap handled inside CPython hash. Verified equal at runtime.
- Family disjointness: `"X.Label.Y"` vs `"NodeKind.Z"` strings never coincide; node objects do not expose the marker, so `node == label` stays NotImplemented→False. All verified.
- `kind` as dataclass field with default (not ClassVar): parser builds nodes via `node_type()` with no args (gsm2parser.py:448), so default applies; construction unaffected. Field joins dataclass `__eq__` but is invariant within a node type — no node-equality regression.
- fltk2gsm.py self.cst removal: label comparisons rewired to `_cst_const` (cross-backend-equal, verified). isinstance conjunct deleted and replaced by `typing.cast` (runtime no-op). Intentional per design §2.5: the removed `isinstance(item, Item)` was a runtime assert guard that no longer fires on a malformed ITEM-labeled non-Item child; design justifies this as a 1:1 label↔type invariant. Accepted as documented scope, not a defect.
- NodeKind registered before node structs/label enums (register_classes_fn). Member-name derivation consistent across both generators.
