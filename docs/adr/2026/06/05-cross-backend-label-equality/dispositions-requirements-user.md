# Dispositions — Cross-Backend Label Equality requirements, user gate (post-human revision)

Source: `notes-requirements-user.md` (verbatim chat directives, authoritative — not subject to reviewer-style fact-check or downgrade). These notes REVISE prior dispositions requirements-5 and requirements-7.
Style note (for any agent editing this doc): concise, precise, unambiguous. No padding.

---

user-note-1 (re-frame to LIVE out-of-tree problem; correct "future-proofing" downgrade):
- Disposition: Fixed
- Action: Goals — replaced the "Premise (no in-tree consumer requires it / future-proofs)" paragraph with a "Motivation (LIVE problem, not future-proofing)" paragraph: out-of-tree consumers already compare CST labels against static `cst.X.Label.Y` constants and break the moment they adopt the Rust backend or mix backends; absence of an in-tree consumer is explicitly stated as NOT evidence the feature is unneeded. Compatibility constraint reworded to drop "purely additive / no consumer edits" framing where it implied no live need. This directly overturns prior disposition requirements-5 (which added the future-proofing premise citing exploration §146/§178/§201-202/§218); that exploration evidence speaks only to *in-tree* consumers and does not bear on out-of-tree consumers the explorer could not see.
- Severity assessment: High. The future-proofing framing mis-set priority and invited under-investment / "do we even need this" pushback on a feature that prevents live breakage of real out-of-tree apps adopting the Rust backend.

user-note-2 (self.cst removal from fltk2gsm.py is in scope; revises out-of-scope constraint):
- Disposition: Fixed
- Action:
  - In scope — added "In scope (continued) — `self.cst` removal from `fltk2gsm.py`" section: static `cst.X.Label.Y` comparisons (no `self.cst`) and reworked `isinstance(item, self.cst.Item)` dispatch so `self.cst` is gone from the file; end-state goal stated.
  - Out of scope — removed the bullet "Removing or replacing `self.cst` module injection. `isinstance(...)` type dispatch ... unchanged." (This bullet is the prior constraint being revised.)
  - Acceptance criteria — added AC10 ("`self.cst` eliminated from `fltk2gsm.py`"): no `self.cst` in the file; static `cst` label comparisons correct for both backends; existing `test_phase4_fegen_rust_backend.py` parity holds without `self.cst` injection; genuine-obstacle caveat pointing at Open question 5. Reworded AC9 to reference static `cst` constants (not `self.cst`) and dropped its old Bound that asserted the isinstance dispatch was out of scope.
  - Open questions — added Open question 5 (TODO: isinstance-dispatch-removal) capturing the technical obstacle the explorer flagged (§182-195: `isinstance` against PyO3 native classes tests native type identity, not satisfiable by label equality), with a proposed default (dispatch on the backend-independent label) and a tightly-bounded genuine-obstacle escape that may narrow AC10 only on a *demonstrated* obstacle.
  - User-visible surface — added note that `Cst2Gsm`'s `cst=` constructor argument is affected; design decides drop/ignore/retain-as-no-op.
  - Compatibility constraint — reworded to carve `fltk2gsm.py` out as intended in-scope edit, not a compatibility break.
  This overturns prior disposition requirements-7's narrowing, which had cited exploration §182-195 to declare the isinstance dispatch out of scope. The user note explicitly re-scopes it IN; the exploration's technical observation is preserved — but as an open question for design to solve, not as grounds to exclude the work.
- Severity assessment: High. Without this, the cycle would ship cross-backend label equality with no in-tree consumer actually exercising it via static constants, leaving `fltk2gsm.py` dependent on `self.cst` and the core demonstration ("static `cst` comparison works for both backends") unproven in tree.

---

Both user notes applied. The genuine-technical-obstacle clause from note 2 is honored as an explicit Open question (5), not a silent narrowing — per the note's instruction. No Won't-Do (user notes are authoritative).
