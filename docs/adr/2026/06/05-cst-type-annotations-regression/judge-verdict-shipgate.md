# Judge verdict — ship gate (user-revision adjudication)

Phase: ship-gate. Base 1e67ed4..HEAD d2e7757. Round 1.
Directive (authoritative): `notes-shipgate-user.md` — drop the `Node` suffix so Protocol class names exactly match concrete CST class names; downstream keeps `cst.Rule`-form annotations unchanged (only import lines may change).
Notes: `notes-shipgate-scope.md` (no findings), `notes-shipgate-slop.md` (no findings).

Concise. Precise. Complete. Unambiguous. No padding.

## Disposition-doc accuracy (must address first)

`dispositions-shipgate.md` asserts: "Current implementation already satisfies this … No changes required. No commits made; HEAD is d2e7757." **This is false against ground truth.** `git log 1e67ed4..d2e7757` shows three commits in range (8cc63e2 public-API doc, 498753f suffix removal, d2e7757 ruff fix); `git diff --stat` shows 10 files changed incl. 323-line churn in `fltk_cst_protocol.py` and the suffix rename through `fltk2gsm.py`, `genparser.py`, `gsm2tree.py`, `plumbing.py`, and tests. The suffix removal was *performed in this range*, not pre-existing. The disposition's conclusion (directive satisfied) is nonetheless correct; its premise (nothing changed) is wrong. Adjudication proceeds against the code, not the disposition narrative.

## Directive-compliance walk

### D1 — Protocol names match concrete classes, no `Node` suffix
Evidence: `fltk_cst_protocol.py` declares `class Grammar/Rule/Alternatives/Items/Item/Term/Disposition/Quantifier/Identifier/RawString/Literal/Trivia/LineComment/BlockComment(typing.Protocol)` — bare names, one per node. `grep -E "[A-Za-z_]+Node\b"` over the protocol module returns nothing (exit 1). `CstModule` exposes `@property def <Name>(self) -> type[<Name>]` for each (covariant property form per design DI-boundary). Assessment: satisfied.

### D2 — generator emits suffix-free (regeneration stays consistent)
Evidence: `gsm2tree.py protocol_node_name` now `return self.class_name_for_rule_node(rule_name)` (suffix `+ "Node"` removed); `protocol_annotation_for_model_types` docstring/quoting updated to bare names. A future regen reproduces suffix-free output — not a hand-edit that drifts. Assessment: satisfied.

### D3 — drop-in: downstream annotations unchanged in form
Evidence: directive's example form is `cst.Rule`. `fltk2gsm.py` imports the protocol module under `TYPE_CHECKING` as `cst` (`from fltk.fegen import fltk_cst_protocol as cst`) and annotates `visit_grammar(self, grammar: cst.Grammar)`, `visit_rule(... cst.Rule)`, … — exactly the directive form. Only the import line changed; every `visit_*` primary-param annotation is `cst.<BareName>`. Assessment: drop-in goal holds.

### D4 — no dangling `*Node` Protocol references
Evidence: repo-wide `grep -E "\b(Grammar|Rule|…|BlockComment)Node\b" fltk/ --include=*.py` returns only `test_trivia_capture.py` lines — all comments / runtime `__class__.__name__` string checks about a legacy concrete-class-name substring, **not** Protocol type annotations. `DocNode` (accumulator), `FakeNode`/`TriviaNode` (test fixtures/comments) are unrelated identifiers, not the dropped suffix. `genparser.py`, `plumbing.py`, `genunparser.py`, `test_plumbing.py`, `test_cst_protocol.py` all migrated `cstp.*Node` → `cst.*` (or `cstp.*` bare). Assessment: zero dangling references.

### D5 — runtime safety of the `cst`-alias / `cst`-param shadowing
The protocol import alias is now `cst`; the `__init__` param is also `cst` (`def __init__(self, terminals, cst: cst.CstModule = _DEFAULT_CST)`). Hazard: param name shadows module alias in annotation position. Evidence it is safe: `fltk2gsm.py:1` has `from __future__ import annotations`; the alias is `TYPE_CHECKING`-only; the module-level sentinel `_DEFAULT_CST: cst.CstModule = cast("cst.CstModule", _default_cst)` uses the alias at module scope (before any param shadow) and the cast target is a string. All runtime CST access stays on `self.cst` (the injected `ModuleType`). Assessment: no runtime `NameError`, no annotation evaluation at runtime.

## Gate verification (independent of disposition claim)

- `uv run pyright fltk/fegen/fltk2gsm.py fltk/fegen/fltk_cst_protocol.py fltk/plumbing.py` → 0 errors, 0 warnings.
- `uv run pytest fltk/fegen/test_cst_protocol.py` → 9 passed, incl. `test_fltk2gsm_does_not_import_protocol_at_runtime` (runtime-unaffected guard) and `test_wrong_member_access_is_flagged` (negative B4 case). Tests were updated to bare names consistently.

## Reviewer-findings adjudication

Both reviewers (scope, slop) returned no findings. Confirmed warranted: the change is a mechanical, fully-consistent rename validated by a green pyright gate and a passing typed-fixture suite; no scope creep beyond directive (public-API doc in CLAUDE.md is directive-aligned, captures principle #1), no slop introduced. No bogus-reviewer concern (silence is correct, not a missed consequence).

## Disputed items

None. The only defect is documentary: `dispositions-shipgate.md` mis-states that no changes were made. It does not affect code correctness or directive compliance and does not warrant REWORK — flagged here for the record.

## Approved

Directive fully satisfied (D1–D5); 2 reviewer note-sets clean; pyright clean; 9 protocol tests pass. Suffix removed at source, generator, consumers, and tests; no dangling `*Node` Protocol references; drop-in annotation form preserved.

---

## Verdict: APPROVED
