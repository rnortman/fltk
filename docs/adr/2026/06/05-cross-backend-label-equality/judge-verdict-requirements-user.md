# Judge verdict — requirements gate (user-notes revision)

Phase: requirements. Doc: `requirements.md`. Round 1 (user-notes revision).
Authoritative input: `notes-requirements-user.md` (verbatim chat directives). Job: verify faithful application; user rulings not second-guessed.

Style note (for any agent editing this doc): concise, precise, unambiguous. No padding.

## Other findings walk

### user-note-1 — Fixed (re-frame to LIVE out-of-tree problem)
Note directs: out-of-tree consumers already compare CST labels against static `cst.X.Label.Y`; they break on Rust-backend adoption / mixed backends; this is a NOW-problem; "no in-tree consumer" framing is wrong; CLAUDE.md prominence stronger.
Verify in doc:
- Goals §line 15 — "**Motivation (LIVE problem, not future-proofing):**" replaces the prior premise. States static-constant comparisons silently return `False` on Rust-backend adoption / mixed backends and "those comparisons silently start returning `False` and the consumer breaks." Absence of in-tree consumer stated as "**not** evidence the feature is unneeded." Matches note verbatim in substance.
- Compatibility constraint §line 120 — reworded; "purely additive" now scoped to genuine external consumers; no longer implies "no live need." Consistent.
Assessment: faithfully applied. (Note's CLAUDE.md-prominence ask is a separate codebase edit, not a requirements-doc obligation; out of this gate's surface — not held against the disposition.)

### user-note-2 — Fixed (`self.cst` removal in scope)
Note directs: end-of-cycle comparison against static `cst.something` enums instead of `self.cst`; `isinstance(item, self.cst.Item)` dispatch reworked so `self.cst` gone; removal is an in-scope acceptance criterion / in-tree demonstration.
Verify in doc:
- In scope §lines 25-32 — "In scope (continued) — `self.cst` removal" section present; both sub-parts (static label comparisons; isinstance dispatch rework) stated; revises prior out-of-scope requirement explicitly.
- Out of scope §lines 34-41 — prior bullet declaring `self.cst` removal / isinstance dispatch out of scope is absent. Removed as claimed.
- AC9 §line 99 — reworded to reference static `cst.ClassName.Label.X`; old Bound asserting isinstance out of scope dropped.
- AC10 §lines 100-103 — added: `self.cst` absent from file; static `cst` comparisons; `test_phase4_fegen_rust_backend.py` parity holds without injection; genuine-obstacle caveat redirecting to Open question 5.
- Open question 5 §lines 150-153 — added: TODO isinstance-dispatch-removal; exploration §182-195 obstacle preserved; proposed default (dispatch on label); tightly-bounded genuine-obstacle escape narrowing AC10 only on a *demonstrated* obstacle.
- User-visible surface §line 110 — `Cst2Gsm` `cst=` constructor arg flagged; design decides drop/ignore/retain-as-no-op.
- Compatibility constraint §line 120 — carves `fltk2gsm.py` out as intended in-scope edit.
Assessment: faithfully applied. The genuine-technical-obstacle observation (exploration §182-195) is honored as an explicit Open question, not a silent narrowing — exactly as the note instructed ("preserved... but as an open question for design to solve, not as grounds to exclude the work").

## Disputed items

None. Both authoritative notes applied without distortion. No Won't-Do used (correct — user notes authoritative). The "TODO: isinstance-dispatch-removal" label on Open question 5 is a requirements-doc open-question marker, not a code `TODO(slug)`; no code exists at this phase, so the code-TODO rubric does not apply.

## Approved

2 dispositions: both Fixed, both verified against the requirements doc.

---

## Verdict: APPROVED

Both user notes faithfully applied to `requirements.md`. Re-frame (LIVE out-of-tree problem) present in Goals + compatibility constraint; `self.cst` removal in-scope across In-scope/AC9/AC10/Open-question-5/user-visible-surface/compatibility. Genuine-obstacle clause surfaced as Open question 5, not silently narrowed.
