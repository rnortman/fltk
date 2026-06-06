# Judge verdict — deep review

Phase: deep. Base 854e1ad..HEAD 9d6f9a0 (reviewers read c57f888; fixes at 9d6f9a0). Round 1.
Notes: 7 reviewer files. Findings: 7 test, 2 reuse, 4 quality, 3 efficiency. error-handling/correctness/security: no findings.

Style note (any agent editing this doc): concise, precise, unambiguous. No padding.

## Added TODOs walk

Five findings dispositioned TODO across three slugs. Each scored on the two-question rubric, plus the iteration-worsened clause.

### reuse-1, reuse-2 — TODO(emit-cross-backend-eq-hash-helper) at gsm2tree.py:101,162 / gsm2tree_rs.py:152,224
Comments present at all four claimed sites; slug in TODO.md. Verified.
Q1 (worth doing): yes — `_fltk_canonical_name`/`__eq__`/`__hash__` emit is duplicated 2× per generator (4 sites). Design §2.3 explicitly cross-references §2.2 ("Rust logic and Python logic must stay in sync"); internal duplication doubles that divergence surface. Real maintenance hazard.
Q2 (design/owner input required): **no.** Mechanical extraction of a private helper parameterized by the canonical-name string expression / type name. The reviewers supply the exact target signatures (`_emit_cross_backend_eq_hash(enum_klass, canonical_name_expr)`, `_emit_rust_cross_backend_eq_hash(lines, type_name)`). No design cycle, no product-owner call. Doable now.
Iteration clause: this duplication was **created this iteration** (the eq/hash emit is new code in this change). Per rubric, a problem this iteration created cannot be silently deferred when it fails Q2.
Assessment: fails Q2 + iteration-created → do-now, not TODO. Disposition wrong.

### efficiency-1, efficiency-2 — TODO(canonical-name-cache) at gsm2tree.py:103,164 / gsm2tree_rs.py:154,226
Comments present; slug in TODO.md. Verified `fltk_cst.py:38-39`: `__hash__` returns `hash(self._fltk_canonical_name)` where the property rebuilds the f-string every call.
Q1 (worth doing): yes — and notably this **worsened the same-backend path this iteration**: `__hash__` has no fast path (unlike `__eq__`, which has `other is self`/type fast path), so every same-backend dict/set hash now rebuilds a string where the prior `enum.Enum.__hash__` was a bare identity hash. The design committed to keeping the same-backend path allocation-free (requirements.md:126); `__hash__` violates that SHOULD.
Q2 (design/owner input required): **no.** Python fix is a per-member cached value — design §2.1 *already sanctions* "a per-member value" instead of a property. Rust fix is `GILOnceCell<isize>` per variant, a standard amortization. Neither needs a design cycle or owner input.
Iteration clause: same-backend hashing was **worsened this iteration**; it fails Q2 → per rubric cannot be silently deferred. The responder's "accept now, fix when profiling confirms a bottleneck" is the standard premature-optimization deferral, which is legitimate for *new* cross-backend cost but not for an iteration-introduced regression on a path the design promised to keep cheap.
Assessment: fails Q2 + iteration-worsened (same-backend `__hash__`) → do-now (at least the Python `__hash__` regression). Disposition wrong.

### efficiency-3 — TODO(kind-field-dataclass-eq) at gsm2tree.py:202
Comment present; slug in TODO.md.
Q1 (worth doing): marginal — reviewer self-labels "Low priority; flag only." The `kind` field is invariant within a node type and the two operands are the same singleton (`other is self` fires), so cost is one identity check per node-eq. Not zero, not iteration-worsening anything measurable.
Q2 (design/owner input required): no — one-line `dataclasses.field(compare=False, repr=False)`.
Assessment: borderline. It's do-now-trivial rather than design-gated, but the cost is negligible and not iteration-worsened, so a TODO here is not harmful. Acceptable as TODO; flag only — not a REWORK driver.

## Other findings walk

### test-1 — Fixed
Claim: `TestNodeKindCrossBackend.test_no_raise_on_unrelated` tested only `kind == other`, omitting symmetric `other == kind` and `!=`; consequence: reflected-`__eq__`/`__ne__` bug on NodeKind uncaught (design §3.2 critical path).
Diff at `test_cross_backend_label_equality.py:228+`: loop now over `[None,1,"NodeKind.ITEMS",object(), _label(b_key,"Items","NO_WS")]`, asserts `kind==other`/`other==kind` both `False` and `kind!=other`/`other!=kind` both `True`. Cross-backend cross-family operand added.
Assessment: addresses the consequence at the named test. Accept.

### test-2 — Fixed
Claim: AC7 label test never exercised cross-backend cross-class (`a.Items.NO_WS == b.Disposition.INCLUDE`); malformed Rust canonical name on a non-Items class undetected in unequal direction.
Diff at `:130+`: appends `_label(b_key,"Disposition","INCLUDE")` (note `b_key`). Accept.

### test-3 — Fixed
Claim: AC4 hash test covered only `Items.Label`; per-enum-type hash bug on another label class undetected.
Diff at `:99+`: adds `Disposition.Label` INCLUDE/SUPPRESS to the cross-backend hash check. Accept.

### test-4 — Fixed
Claim: disjointness test compared `NodeKind.ITEMS` vs `Items.NO_WS` (strings differ regardless of format); the dangerous same-word case (`NodeKind.ITEM` vs `Items.Label.ITEM`) untested.
Diff at `:230+`: adds `kind_item_cn != label_item_cn` and `kind_item != label_item` for the shared word "ITEM". Pins the precise family-disjointness guarantee. Accept.

### test-5 — Fixed
Claim: no test verified node objects don't expose `_fltk_canonical_name` (design §2.1/§3.3 marker-scope invariant), so `node == label` could silently return `True`.
Diff: new `TestMarkerScope` — `not hasattr` on Python/Rust/embedded `Items()`, plus `node != label` same-backend and cross-backend. Accept.

### test-6 — Fixed
Claim: `test_kind_getter_is_getter_attr` counted global `#[getter]` ≥3 — vacuous; passes even if `kind` loses its attribute.
Diff at `test_gsm2tree_rs.py:640+`: walks to `fn kind(&self) -> NodeKind {`, walks back over blanks, asserts `#[getter]` on the immediately preceding non-blank line; `pytest.fail` if the fn is absent. Now pins the getter to the function. Accept.

### test-7 — Fixed
Claim: `TestCst2GsmNoSelfCst.test_produces_correct_grammar` checked only rule-name equality; a `self.cst`-removal regression in disposition/quantifier mapping would pass.
Diff at `test_plumbing.py:580+`: replaced name loop with `assert grammar_default == grammar_baseline` (full structural eq). 150 tests in the three affected files pass. Accept.

### quality-1 — Fixed
Claim: `kind` field emitted `NodeKind.{class_name.upper()}` inline instead of routing through `node_kind_member_name`; divergence from Protocol/Rust path → silent `Literal` mismatch (pyright error downstream).
Diff `gsm2tree.py:198+`: `kind_member = self.node_kind_member_name(rule_name) if rule_name else class_name.upper()`; `py_class_for_model` gains `rule_name`; sole caller passes `rule`. For these grammars `class_name.upper() == node_kind_member_name`, so no regen diff (consistent — correctness reviewer verified member names match at runtime). pyright 0 errors. Accept.

### quality-2 — Fixed
Claim: `#[allow(non_camel_case_types)]` unconditionally on `NodeKind` (CamelCase variants — never fires); swallows future naming regressions.
Diff `gsm2tree_rs.py:160`: line removed. Regenerated: `src/cst_fegen.rs:15-17` NodeKind preamble no longer carries the allow (label enums retain it — correct). Accept.

### quality-3 — Fixed
Claim: `_protocol_class_for_model` `rule_name: str = ""` default created a dead `kind: object` fallback reachable from any argless future call.
Diff `gsm2tree.py:442`: default removed, parameter required. All callers pass it. Accept.

### quality-4 — Fixed
Claim: Protocol module unconditionally imported `NodeKind` from the concrete CST module → pure-Rust/pure-Protocol consumers break on import.
Diff `gsm2tree.py:439+`: emits `if typing.TYPE_CHECKING:\n    from ... import NodeKind` via `ast.parse`. Regenerated `fltk_cst_protocol.py:8-9` carries the guard. `from __future__ import annotations` present → `Literal[NodeKind.X]` are lazy strings, no runtime resolution. pyright 0 errors. Directly serves the CLAUDE.md out-of-tree-consumer mandate (pure-Rust deployment). Accept.

## Disputed items

- **reuse-1 / reuse-2 (emit-cross-backend-eq-hash-helper)**: TODO fails Q2 (mechanical helper extraction, signatures supplied by reviewers) and the duplication was created this iteration. Need: extract the shared helper now in both generators, OR escalate with a specific reason it cannot be done this cycle.
- **efficiency-1 / efficiency-2 (canonical-name-cache)**: TODO fails Q2 (per-member cached value is design-§2.1-sanctioned; Rust `GILOnceCell` is standard) and the same-backend `__hash__` path was worsened this iteration versus the prior identity hash, against the design's same-backend-allocation-free SHOULD (requirements.md:126). Need: at minimum precompute the canonical string per member so same-backend `__hash__` stops rebuilding it; the Rust amortization may stay TODO if argued, but the same-backend Python regression should be fixed. OR escalate with justification.

## Approved

12 findings: 11 Fixed verified (test-1..7, quality-1..4), 1 TODO acceptable (efficiency-3 / kind-field-dataclass-eq — marginal, negligible cost, not iteration-worsened).

---

## Verdict: REWORK

Four dispositions wrong: reuse-1, reuse-2, efficiency-1, efficiency-2. All four TODOs fail rubric Q2 (doable now without design cycle or owner input — the fix shapes are mechanical and reviewer-specified) and all four defer problems this iteration created or worsened, which the rubric forbids deferring silently. Round 1 → REWORK. The 11 Fixed dispositions and the one efficiency-3 TODO are accepted.
