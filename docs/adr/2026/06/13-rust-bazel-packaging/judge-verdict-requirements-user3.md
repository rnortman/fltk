# Judge verdict — requirements (user-notes pass)

Phase: requirements. Doc: `requirements.md`. Round 3 (user-notes pass — APPROVED or ESCALATE only).
Authoritative input: `notes-requirements-user.md` § "User notes round 3" (two directives).
Dispositions: `dispositions-requirements-user3.md` (2 items, both Fixed).

## Other findings walk

### user-round3-1 — Fixed
User directive (note 3.1): the fltk crates are not yet published to crates.io, but if the designer
decides crates.io is the most expedient/cleanest path, FLTK will publish. I.e. "not published" must
read as an available design option, not a blocker.
Disposition: rewrote the "Core-crate distribution" sub-point under Open questions → Design space.
Evidence (`requirements.md:223–230`): the sub-point now states the crates are "**not currently
published to crates.io**", that "Publishing them to crates.io is a fully available design option — if
the designer judges it the cleanest/most expedient path, FLTK will publish them," that source-only is
an equal alternative, and that "'not yet published' is **not** a constraint or blocker — it is one of
the design alternatives." The pre-existing Out-of-scope line (`:59–60`) frames publishing as
"may be selected as the mechanism … but is not mandated," consistent with this.
Assessment: text matches the directive precisely — available option, FLTK will publish if chosen,
explicitly not a blocker. Accept.

### user-round3-2 — Fixed
User directive (note 3.2): the acceptance bar is NOT that FLTK is correct; it is only that packaging
produces *something* — any parse result at all. Stop being pedantic about correctness/equivalence.
Disposition claims four sub-actions; verified each against the doc:
- (a) Criterion 4 rewritten to "Bindings produce a result — round-trip parse." Evidence
  (`requirements.md:92–100`): bar is "produce *some* parse result/output at all"; explicitly "**not**
  a test that FLTK parses correctly and is **not** a Rust-vs-Python equivalence test"; "Correctness of
  FLTK's parsing is out of scope here." Matches the directive.
- (b) Rust-vs-Python-agreement / Python-baseline clause removed from criterion 4. Verified: `grep`
  for `agree|baseline|differential|vs.\?python|equivalent` finds no surviving comparison clause; the
  only `python`/`equivalence`/`correct` hits in criterion 4 are negations (`:98–100`). The three
  "baseline" hits elsewhere (`:172`, `:208`, `:234`) refer to the Rust toolchain, not a parse
  baseline. Confirmed removed.
- (c) `TODO(equivalence-surface)` open-question section removed. Verified: `grep "equivalence"`
  returns only `:99` (the negation in criterion 4). No TODO and no such section remain. Confirmed.
- (d) Criterion 3 softened from a correctness/offset assertion to an integration check. Evidence
  (`requirements.md:84–90`): now "the Rust path is actually wired up, not silently replaced by the
  fallback," with the warn/RuntimeError text demoted to "Diagnostic hints, not pass/fail gates."
  Reads as an integration wiring check, not a correctness gate, per the directive.
Assessment: all four sub-actions verified in the doc; the requirements no longer mandate any
cross-backend correctness/equivalence harness. Accept.

## Disputed items

None.

## Approved

2 dispositions: both Fixed, both verified against `requirements.md`.

---

## Verdict: APPROVED

Both round-3 user directives are faithfully and completely applied. crates.io reframed as an
available design option rather than a blocker (`:223–230`); the correctness/equivalence acceptance
bar removed and replaced with a "produces *some* result" integration bar (criteria 3 and 4,
`:84–100`), and the `TODO(equivalence-surface)` section deleted. No directive partially applied; no
dispute requiring arbitration.
