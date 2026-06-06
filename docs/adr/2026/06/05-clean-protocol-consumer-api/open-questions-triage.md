# Open Questions Triage

Concise. Precise. No design. Anchored to code.

---

## A. `protocol-label-type-change` — Protocol `Label` becomes a real enum vs stays type-erased

**Classification: EXPLORATION-ANSWERABLE. Option A is the required path; designer validates feasibility; no user decision needed.**

The question as posed frames A vs B as a fork needing user input, but the existing constraints already resolve it:

**A is required by the gating criterion.** The gating criterion prohibits CST-forced suppressions in consumer code. Option B (protocol Label becomes `enum.Enum`) changes the structural type of `Label` members in the generated public API, which is a breaking change for out-of-tree consumers who annotate against protocol types — exactly what CLAUDE.md forbids without explicit called-out justification. The requirements doc itself says "if not [additive], the break is explicitly accepted under `protocol-label-type-change`" — meaning B requires user sign-off, not that it is a neutral alternative. B is therefore not a designer default.

**A is technically feasible without changing the annotated type.** The concern in the requirements is whether a value-carrying `ClassVar[object]` member can (1) round-trip through the canonical-name bridge and (2) keep `test_boundary_probe_documents_label_mismatch` passing. Both are resolvable by code inspection:

1. The canonical-name bridge at `gsm2tree.py:122` uses `getattr(other, '_fltk_canonical_name', None)` — duck-typed, cares only about the attribute, not the object's type. Any object with `_fltk_canonical_name` set to the right string will compare equal. A plain object (non-enum) assigned as `ClassVar[object]` with that attribute satisfies the bridge.

2. `test_boundary_probe_documents_label_mismatch` (`test_cst_protocol.py:359-376`) asserts that assigning `fltk_cst` (concrete) directly to a `cstp.CstModule`-typed variable *produces pyright errors* — because `Label(enum.Enum)` does not structurally match the protocol's plain `class Label`. Option A keeps the protocol Label a plain class; the structural mismatch between concrete `enum.Enum` and plain class is preserved. The test continues to pass under A as long as the protocol Label remains a non-enum class.

**Resolved answer:** Option A is the required target. Designer must confirm: (a) a plain-object value with `_fltk_canonical_name` satisfies the bridge and can be assigned to a `ClassVar[object]` annotation without pyright error in the generated module, and (b) `test_boundary_probe_documents_label_mismatch` still passes. If either check fails, designer escalates to user with specific evidence; they must not silently flip to B.

---

## B. `nodekind-runtime-dep` — NodeKind runtime-dependency for pure-protocol import

**Classification: EXPLORATION-ANSWERABLE. Option A is the only answer consistent with the stated constraint; this is not a user decision.**

The requirements state (Constraints): "importing the protocol module must not eagerly import a concrete backend." Option B (runtime import from a concrete backend) directly violates this. The question asks to "confirm acceptable" for A — there is nothing to confirm with the user; A is mandated by the constraint already in the requirements.

**Additional factual support from code:**

- `fltk2gsm.py` (exploration §5, line 212) does not reference `NodeKind` directly — only per-node `Label` members are used at lines 51, 53, 62, 65, 67, 70, 74, 117, 119, 121, 128, 130, 132. `NodeKind` is not needed in `fltk2gsm.py` to satisfy the gating criterion.
- The `Literal[NodeKind.X]` annotation in protocol classes is a type-check-only annotation (lazy string under `from __future__ import annotations`, `gsm2tree.py:438`). Providing runtime NodeKind values to consumers who need them does not require changing this annotation.
- The protocol module can define its own lightweight `NodeKind`-equivalent (Option A) that is never the concrete module's `NodeKind` class, fully satisfying the constraint.

**Resolved answer:** Option A. The protocol module owns its own runtime enum-like values. No concrete-backend import at module load time. Designer decides implementation shape (plain objects with `_fltk_canonical_name`, a dedicated lightweight enum, etc.).

---

## C. `identity-semantics` — Cross-module enum identity (`is` / `match`/`case`) not guaranteed

**Classification: USER DECISION — but a narrow, low-stakes one with a strong default.**

**Why it needs the user:** This is a public-API contract question, not an implementation question. The question is whether the supported comparison contract for protocol-module enum members is `==`/`!=` only, or whether FLTK also commits to `is`-identity or `match`/`case` compatibility across the three enum sets (protocol, Python-concrete, Rust-concrete).

**What the code establishes as fact:**

- `fltk2gsm.py` uses `==` exclusively: lines 51, 53, 62, 65, 67, 70, 74, 117, 119, 121, 128, 130, 132. No `is` comparisons against Label or NodeKind members anywhere in-tree.
- The canonical-name bridge (`gsm2tree.py:100-132`) is designed for `==`/`!=`; it explicitly does not unify identity.
- Python `match`/`case` on enum members uses identity (`is`) internally when matching enum values, not `__eq__`. A protocol-module enum member of a different class will not match a concrete-module enum member via `match`/`case` even if `==` returns `True`.
- Guaranteeing `is` or `match`/`case` compatibility across three separate enum sets would require either (a) sharing the same class objects across modules, or (b) a non-enum sentinel approach — both of which constrain the design significantly.

**Options and costs:**

- **`==`/`!=` only (current requirements text):** Designer has maximum freedom; protocol-module enum members can be any object type. Downstream consumers using `is` or `match`/`case` on protocol members get undefined behavior (silently wrong comparisons). No in-tree consumer does this today.
- **Also guarantee `is` or `match`/`case`:** Severely constrains the protocol Label design; likely requires the protocol and concrete modules to share the same enum class, which undermines the protocol/concrete separation and the structural-mismatch test.

**Why user input is genuinely needed:** The "not guaranteed" posture is the current requirements text, but it is a standing invitation for a downstream consumer to be surprised — especially since Python `match`/`case` on enum members is idiomatic and consumers accustomed to standard enum behavior may use it without realizing it is unsupported. Whether FLTK commits to that broader contract is a product/values decision about what FLTK promises to out-of-tree consumers. Facts don't resolve it; the user decides what the API contract says.

**Strong default to present to user:** `==`/`!=` only, with explicit documentation that `is` and `match`/`case` across protocol vs concrete enum sets are not guaranteed. User should confirm or upgrade the requirement.
