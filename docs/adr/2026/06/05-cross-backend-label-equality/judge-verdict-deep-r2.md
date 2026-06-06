# Judge verdict — deep review (round 2)

Phase: deep. Base 854e1ad..HEAD 97b041c (round-1 fixes 9d6f9a0; rework 0c4093d). Round 2 — APPROVED or ESCALATE only.
Scope: the four round-1 disputed items (reuse-1, reuse-2, efficiency-1, efficiency-2). All other dispositions accepted in round 1.

Style note (any agent editing this doc): concise, precise, unambiguous. No padding.

## Disputed-item walk (round 1 → round 2)

### reuse-1 — was TODO → now Fixed
R1 ruling: fails Q2 (mechanical helper, signatures supplied) + duplication created this iteration → do-now.
Rework: diff `gsm2tree.py` extracts `@staticmethod _emit_cross_backend_eq_hash(enum_klass)`; both `_node_kind_enum` and `py_class_for_model` Label emit now call it. The duplicated `_fltk_canonical_name`/`__eq__`/`__hash__` emit blocks are deleted from both sites. `TODO(emit-cross-backend-eq-hash-helper)` comments removed from all sites (`git grep` 0 hits); TODO.md entry gone. Single divergence point. Accept.

### reuse-2 — was TODO → now Fixed
R1 ruling: same as reuse-1 on the Rust-emission side.
Rework: diff `gsm2tree_rs.py` extracts `@staticmethod _emit_rust_cross_backend_eq_hash(lines, type_name)`; both `_node_kind_block` (`"NodeKind"`) and `_label_enum_block` (`enum_name`) call it. The two copied 10-line pymethod blocks deleted. `type_name` is the only varying parameter (own-type `extract`). Comments removed; TODO.md entry gone. Accept.

### efficiency-1 — was TODO → now Fixed
R1 ruling: fails Q2 (per-member cached value design-§2.1-sanctioned) + same-backend `__hash__` worsened this iteration (per-call f-string rebuild vs prior identity hash, against requirements.md:126 SHOULD) → do-now.
Rework: `@property _fltk_canonical_name` removed from the emitted class body; replaced by a bare `_fltk_canonical_name: str` annotation (pyright) plus post-class plain-string assignments (`_emit_node_kind_canonical_name_assignments` / `_emit_label_canonical_name_assignments`). `py_class_for_model` now returns `list[ast.stmt]` (ClassDef + assignments); callers use `.extend`. Regenerated `fltk_cst.py` confirms: lines 39-52 assign `NodeKind.<M>._fltk_canonical_name = "NodeKind.<M>"` once post-class; `__hash__` at :36/:72 reads `hash(self._fltk_canonical_name)` against a plain attribute — no per-call f-string rebuild. Same-backend `__hash__` regression resolved. 47/47 cross-backend tests pass. Accept.

### efficiency-2 — was TODO(canonical-name-cache) → remains TODO(canonical-name-cache), now Rust-only scope
R1 status: the same slug bundled the Python `__hash__` regression (the REWORK driver) with the Rust `PyString`-per-call allocation. R1 ruling explicitly permitted the Rust amortization to stay TODO ("the Rust amortization may stay TODO if argued, but the same-backend Python regression should be fixed").
Rework: Python side fixed under efficiency-1. Remaining TODO is Rust-only — `__hash__` in `_emit_rust_cross_backend_eq_hash` allocates a `PyString` per call. Re-scored:
Q1 (worth doing): yes — eventual amortization for Rust-backend dict/set usage at volume.
Q2 (design/owner input required): the deferral rationale is correctness-constraint + no profiled bottleneck, not design-gating. Strictly this is do-now-able (`GILOnceCell<isize>` is a standard PyO3 pattern). However: the allocation is **load-bearing for correctness** (AC4 cross-backend hash agreement via CPython's salted `hash(str)`, design §3.1) — it is *not* an iteration-introduced regression. The pre-existing Rust path never had a cheaper hash; `#[pyclass(hash)]` was dropped because it could not satisfy cross-backend agreement at all. So the iteration-worsened clause does **not** bite: same-backend Rust hashing did not regress against a prior cheap path that satisfied the new contract — there was none. This is genuinely-new cross-backend cost, and "defer amortization until a profiled bottleneck exists" is legitimate premature-optimization deferral for new cost. TODO.md entry correctly narrowed to Rust-only; comment retained at `gsm2tree_rs.py:158`.
Assessment: TODO acceptable.

## Verdict

All four round-1 disputed items resolved correctly:
- reuse-1, reuse-2, efficiency-1: Fixed, verified against the diff and regenerated output; tests green.
- efficiency-2: re-scoped to Rust-only; the remaining deferral is new correctness-constrained cross-backend cost (not an iteration-introduced regression on a previously-cheap path), so TODO is acceptable.

efficiency-3 (kind-field-dataclass-eq) was accepted as TODO in round 1; unchanged.

## Verdict: APPROVED
