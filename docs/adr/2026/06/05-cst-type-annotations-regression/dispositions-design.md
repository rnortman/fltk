# Dispositions — design review round 1

Concise. Precise. Source-backed. Audience: smart LLM/human. No padding.

Reviewer notes: `./notes-design-design-reviewer.md`. Design: `./design.md`. Each finding fact-checked against code and empirically against pyright 1.1.402 (the repo's pinned version) before disposition. Several findings were *under*-stated by the reviewer; the empirical checks surfaced a harder, adjacent obstacle (nested-class nominal matching) that drives the corrected design.

## Empirical findings (pyright 1.1.402, project venv) underpinning the dispositions

- A module object **is** matched structurally against a Protocol-typed parameter (pyright reports per-attribute incompatibilities).
- A `Grammar: type[GrammarNode]` mutable attribute on the module Protocol is **invariant** → module match **rejected**. A `@property def Grammar(self) -> type[GrammarNode]` is **covariant** → module match **accepted** (for label-free nodes). New, load-bearing; not in the original design.
- A **nested class inside a Protocol is matched nominally**, not structurally: `type[Items.Label]` (concrete enum) is never assignable to a protocol's nested `Label` class, under every member typing tried (`object`, `ClassVar[Label]`, empty enum). So any label-bearing node makes the concrete module fail the structural match → a boundary cast is required. This validates design-2/design-3's concern and is stronger than the reviewer stated.
- `isinstance(item, m.Item)` where `m.Item: type[ItemNode]` (Protocol via property): **no error**, narrows `item` to `ItemNode`. Direct `isinstance(item, ItemNode)` (Protocol name literal): error. The design uses only the former. This **refutes** design-4's predicted dead-end.
- `==` across distinct nominal enum types: **never flagged**. Accessing a non-existent enum member (`.WRONG`): **flagged**. Confirms design-2's substance (attribute-presence safety only).

---

design-1:
- Disposition: Fixed
- Action: "New generated artifact" bullet (design.md, "Child/label value types…") rewritten to state explicitly that `py_annotation_for_model_types` is *not* a free reuse: protocol generation must apply a node-name→`<Node>Node` rename to rule-node types only, passing `terminalsrc.Span`/`terminalsrc.*` through un-suffixed (literal/regex children stay `Span`), keyed on rule-name-str vs registered-library-type. Notes the failure mode (`reportUndefinedVariable` → B5 fail) if under-budgeted.
- Severity assessment: Correct and material. Verified `py_annotation_for_model_types` (`gsm2tree.py:85-93`) emits concrete `class_name_for_rule_node` names with no node-vs-Span discriminator; naive reuse would emit undefined `Rule`/`Items` names in the protocol module and fail pyright.

design-2:
- Disposition: Fixed
- Action: Added a dedicated "Label representation" subsection. Empirically established nested-class nominal matching; prescribes nested `class Label:` with `NO_WS: ClassVar[Label]` members; states honestly that B4 buys **attribute-presence only** (missing member flagged; wrong-but-existing label via `==` not flagged). Test plan 2a updated to assert the wrong-existing-label non-flagging as a known boundary, so the test does not overpromise.
- Severity assessment: High. The Label surface is the most intricate part of the mechanism and was hand-waved ("typed as the concrete enum is structurally used"). Left unspecified, the implementer would discover late that a naive nested enum breaks both label access and the module match, and would overclaim B4 safety. The fix makes the achievable safety explicit and correct.

design-3:
- Disposition: Fixed
- Action: "DI boundary" section rewritten. Removed the "resolved during implementation" hand-wave and the framing that "module matches" and "use a cast" are interchangeable success paths. Now: empirically the nested-`Label` mismatch means the default-binding cast **is** required; the cast is justified only because the mismatch is the known benign nominal-nested-enum limitation (concrete enums carry the declared members); Test plan 2a independently verifies member resolution *without* the cast so the cast cannot mask a real missing member (the B4-voiding hazard the reviewer named). Two casts total (default binding + Rust injection site), both documented; none in `visit_*`. `__init__` annotation line and Resolved/`di-boundary-escape` updated to match.
- Severity assessment: High. This is the load-bearing mechanism. The empirical check confirmed the structural match genuinely fails (not merely "might"), so the cast is unavoidable; the reviewer's hazard (cast silently masking a real gap) is real and is now neutralized by the 2a member-access fixture.

design-4:
- Disposition: Fixed (reframed — the predicted defect does not occur)
- Action: "fltk2gsm.py changes" bullet and the `isinstance` edge case rewritten to state the verified result: `isinstance(item, self.cst.Item)` with `self.cst.Item: type[ItemNode]` produces **no** pyright error and narrows to `ItemNode`. The `runtime_checkable` restriction applies only to a literal Protocol-name second arg, which the design never writes. No `type: ignore`, no `type[Any]` degradation on the `Item` path.
- Severity assessment: Medium, and the reviewer's specific prediction was wrong. The reviewer assumed `type[ItemNode]` as an `isinstance` arg would be rejected; empirically pyright accepts a *value* of `type[Protocol]` (it cannot prove it is a bare Protocol). The B1×B5 tension the reviewer feared on the `Item` path does not exist. The design now records the verified behavior so no one re-litigates it or adds a needless ignore.

design-5:
- Disposition: Fixed
- Action: Added a "Pyright test harness" subsection to the Test plan: a `run_pyright(file_path)` helper shelling `uv run pyright --outputjson`, parsing `generalDiagnostics`, scoping to a fixture file/package, `pytest.skip` when pyright is absent (CI runs it via `make check`), exposing zero-diagnostic and expected-diagnostic-at-rule/line assertions. Labeled the verification backbone for B4/B5.
- Severity assessment: Medium-high. B4's two mandatory Python-backend checks and the negative case depend entirely on this harness; budgeting it as a one-liner risked a faked/weaker check. No existing pyright-as-pytest harness in the repo (confirmed: tests are pytest, pyright is a separate `make check` gate).

design-6:
- Disposition: Fixed
- Action: "fltk2gsm.py changes" bullet now states the invariant explicitly: `cstp.*` names appear only in annotation position; all runtime CST access stays on `self.cst` (the injected `ModuleType`); never write `cstp.ItemNode` in runtime position (would `NameError`); `from __future__ import annotations` defers annotation evaluation only, not runtime references.
- Severity assessment: Low (reviewer agreed — minor clarity gap, design correct as intended). The one explicit sentence forecloses an implementer conflating `self.cst.Item` (runtime, fine) with a `cstp` reference (would `NameError`), satisfying requirements line 97.

---

Cleanup-editor re-invoked after edits; resolved three contradictions the edits introduced (the stale "must satisfy `CstModule` structurally — verified by B4" line at `__init__`; the Rust "satisfies `CstModule` structurally" claim; a stale "decided in cleanup" naming note) and removed a leaked reviewer-finding ID (`design-3`) from the design prose.
