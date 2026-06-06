# Judge verdict — design review

Phase: design. Doc: `./design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 6 findings, all dispositioned **Fixed**.
No TODOs walk (design phase). All findings walked below.

Code facts underpinning the reviewer's claims independently verified: `Cst2Gsm.__init__(..., cst: ModuleType = _default_cst)` (`fltk2gsm.py:10`); bare `visit_*` params; `self.cst.<Node>.Label.*` equality dispatch (`fltk2gsm.py:44-50,63-68,114-130`); `isinstance(item, self.cst.Item)` (`fltk2gsm.py:61,72`); `py_annotation_for_model_types` emits concrete `class_name_for_rule_node` names with no node-vs-Span discriminator (`gsm2tree.py:46-93`); `genparser.generate` shared_cst write-site (`genparser.py:170-186`).

## Other findings walk

### design-1 — Fixed
Claim: design's "reuse `py_annotation_for_model_types`" framing glosses a required node-name→`<Node>Node` rename; naive reuse emits undefined `Rule`/`Items` names → `reportUndefinedVariable`, fails B5. Consequence stated and real.
Verification: `py_annotation_for_model_types` (`gsm2tree.py:85-93`) builds names via `iir_type_to_py_annotation` over types registered with the concrete `class_name_for_rule_node` name (`gsm2tree.py:74-77`); `Span` passed through. No string-level node-vs-Span discriminator — reviewer's mechanism reading is correct.
Edit present: design.md:29 now states explicitly the rename is "not a free reuse," applies `<Node>Node` to rule-node types only, passes `terminalsrc.Span`/`terminalsrc.*` through un-suffixed (literal/regex children stay `Span`, cf. `gsm2tree.py:253`), keyed on rule-name-str vs registered-library-type, and names the `reportUndefinedVariable`→B5 failure mode.
Assessment: edit addresses the consequence at the named site. Accept.

### design-2 — Fixed
Claim: `Label` enum representation in the Protocol is unspecified; B4's "wrong access flagged" leans on it; `==` across nominal enums is never flagged so safety is attribute-presence only, not value-correctness — design overclaims. Consequence real.
Edit present: design.md:34-40 adds a "Label representation" subsection: nested `class Label:` with `NO_WS: ClassVar[Label]` members; states honestly B4 buys attribute-presence only (missing member flagged; wrong-but-existing `==` not flagged); Test plan 2a (design.md:97) asserts the non-flagging as a known boundary so the test does not overpromise.
Assessment: the design no longer hand-waves the load-bearing surface and no longer overclaims B4. The empirical pyright claims (nominal nested-class matching) cannot be re-run in a design phase, but they are internally consistent and the disposition's conclusion *narrows* the achievable guarantee rather than inflating it — the conservative direction. Accept.

### design-3 — Fixed
Claim: module-satisfies-`CstModule` is the load-bearing mechanism, not a peripheral edge case; "resolved during implementation" hand-wave plus interchangeable "module matches OR cast" framing lets a boundary cast silently mask a real structural mismatch and void B4 (the Python-mandatory backend). Consequence real and precise.
Edit present: design.md:61-70 "DI boundary" rewritten — removes the hand-wave; states the nested-`Label` mismatch makes the cast unavoidable; restricts the cast's justification to the known benign nominal-nested-enum limitation; gates it behind Test plan item 2b (boundary-assignability probe) and guards against masking via 2a (member-access fixture without the cast). Two casts total (default binding + Rust injection `plumbing.py:171`), none in `visit_*`; `Resolved`/`di-boundary-escape` (design.md:114) updated to match.
Assessment: the reviewer's exact hazard (cast hides a genuine gap) is named and neutralized by the cast-free 2a member-access probe. The cast is now confined to the genuine `ModuleType`-narrowing + the documented nominal limitation, matching `di-boundary-escape`'s "single documented boundary cast if unavoidable" default (requirements line 112). Accept.

### design-4 — Fixed (reframed; reviewer's prediction refuted)
Claim: `isinstance(item, self.cst.Item)` with `self.cst.Item: type[ItemNode]` (ItemNode a non-runtime_checkable Protocol) is a hard pyright error → forces `type: ignore` (B5) or `type[Any]` degradation (B1), a dead-end on the `Item` path.
Disposition: reframed — the predicted defect does not occur; `isinstance` on a *value* of type `type[ItemNode]` is accepted and narrows; the `runtime_checkable` restriction applies only to a literal Protocol-*name* second arg, which the design never writes (`fltk2gsm.py:61,72` use `self.cst.Item`, confirmed).
Assessment: this is a legitimate "responder right that finding is bogus" case, not a rubber-stamp. The reviewer over-predicted; the responder's distinction (runtime value of `type[Protocol]` vs literal Protocol name) is sound and consistent with the code, which never passes a `cstp.*` name to `isinstance`. The design records the verified behavior (design.md:52,75) so it is not re-litigated. The responder did not dodge — it engaged the substance and corrected it in the conservative-for-the-design but adversarially-honest direction. Accept.

### design-5 — Fixed
Claim: Test plan items 2/3/4 assume a pyright-invoking pytest harness that does not exist (pyright is a `make check` gate, not a pytest assertion); the negative case (B4 "wrong access flagged") needs new infra budgeted as a one-liner. Consequence real — verified no pyright-as-pytest harness in repo description; tests are pytest.
Edit present: design.md:86-91 adds a "Pyright test harness" subsection: `run_pyright(file_path)` shelling `uv run pyright --outputjson`, parsing `generalDiagnostics`, scoping to a fixture file/package, `pytest.skip` when pyright absent (CI runs it via `make check`), exposing zero-diagnostic and expected-diagnostic-at-rule/line assertions; labeled the B4/B5 verification backbone.
Assessment: infra now specified before the feature tests depend on it. Addresses the consequence. Accept.

### design-6 — Fixed
Claim (reviewer-rated low, clarity gap not defect): `from __future__ import annotations` defers annotations only; an implementer could conflate `self.cst.Item` (runtime, fine) with a `cstp.*` reference and introduce a runtime `NameError` (requirements line 97). Consequence minor, correctly self-rated low.
Edit present: design.md:51 states the invariant explicitly — `cstp.*` only in annotation position; all runtime CST access stays on `self.cst`; never write `cstp.ItemNode` in runtime position.
Assessment: one-sentence invariant forecloses the conflation. Proportionate to a low-severity clarity gap. Accept.

## Approved

6 findings: 6 Fixed verified (5 substantive design edits present and addressing the stated consequence; 1 — design-4 — a sound reframe refuting an over-predicted reviewer dead-end).

No disputed items. Empirical pyright-1.1.402 claims in the dispositions (module-vs-Protocol structural matching, nominal nested-class matching, `isinstance` on `type[Protocol]`) are not re-runnable in a design phase; they are internally consistent, drive edits in the conservative (guarantee-narrowing, not -inflating) direction, and are independently gated by Test plan items 2a/2b/3 as preconditions before implementation commits to the cast. Feasibility is verified at implementation time by those gates — appropriate for a design-phase disposition.

Scope: disciplined. Rust `.pyi` deferred via `TODO(rust-cst-pyi)` (B3a permits; shared Protocol carries B1/B6 meanwhile). No `scope-N` finding with non-trivial deferred aggregate work — the deferral is a requirements-sanctioned increment, not a retroactive narrowing. No ESCALATE trigger.

---

## Verdict: APPROVED

All six dispositions acceptable. Each names a present, consequence-addressing design edit; design-4 is a sound refutation of an over-predicted finding. Empirical claims are gated by named preconditions before implementation.
