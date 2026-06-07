# Dispositions: requirements review — Rust CST native span

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Round 1. Findings fact-checked against request.md + exploration.md + notes-requirements-user.md.

requirements-1:
- Disposition: Fixed
- Action: Added a "Scope note" callout under Goals stating the ADR slug
  (`rust-cst-native-span`) is historical and scope is all node-state fields, not span. Body was
  already correct; this closes the residual re-narrowing risk the reviewer flagged.
- Severity assessment: Low. Body already scoped correctly; the slug/title legacy could still
  mislead a skimming designer into the exact span-narrowing the user explicitly raged against, so
  a one-line guard is cheap insurance.

requirements-2:
- Disposition: Fixed
- Action: Added a "Scope-magnitude note" callout under Goals: children migration is the
  dominant, public-Rust-traversal-API-reshaping portion (per exploration "potentially the largest
  change"); firmly in scope per user requirement; requester may stage (span/scalar first, children
  second) or do atomically, as an ordering choice that does not narrow scope.
- Severity assessment: Medium. The literal request named span; children dwarfs it and reshapes
  the public traversal API. Without surfacing magnitude, the requester discovers a much larger,
  API-shaping project mid-build. User correction confirms children is wanted, so kept in scope —
  only the size and staging option are surfaced.

requirements-3:
- Disposition: Fixed
- Action: Flipped the proposed default of Open question `native-span-start-end` from (B) to (A)
  (expose `.start`/`.end` on `fltk._native.Span`), with rationale citing CLAUDE.md's "near-drop-in
  replacement … must not be forced to edit … call sites wholesale" invariant; (B) retained as the
  redirect option. Remains an open question (requester decision), but the proposed default no
  longer contradicts a stated project invariant.
- Severity assessment: Medium-high. `node.span.start`/`.end` is a call site; defaulting to (B)
  proposes the consumer-breaking path against the project's own drop-in invariant, which the doc
  itself lists as a constraint. Wrong default to recommend; the decision still belongs to the
  requester.

requirements-4:
- Disposition: Fixed
- Action: Added a Behavioral-equivalence line explicitly declaring node/span `repr()` is **not**
  a tracked cross-backend equivalence surface; consumers must not depend on repr equality and the
  generator need not reproduce the Python repr form.
- Severity assessment: Low-medium. Undecided repr status risks either unacknowledged cross-backend
  repr divergence in downstream snapshots/logs, or a designer over-investing in repr parity nobody
  needs. Explicitly excluding it resolves the ambiguity at near-zero cost.

requirements-5:
- Disposition: Fixed
- Action: Reworded the Native-node-state acceptance from "a grep / type audit … finds no
  Python-object-typed state field" to "an audit of every … CST node struct confirms no
  Python-object-typed state field," removing the verification-mechanism phrasing.
- Severity assessment: Negligible. Reviewer self-rated borderline/harmless; the underlying
  observable property is unchanged. Reword keeps it a property-to-hold, not a prescribed test.

requirements-6:
- Disposition: Fixed
- Action: In the In-scope protocol-annotation bullet, pinned that the widening must be
  **additive** (strict superset of the current annotation) so Python-backend-only consumers'
  type-checks pass with no annotation edits; added an acceptance criterion to that effect and a
  CLAUDE.md citation.
- Severity assessment: Medium. A replacement (non-superset) protocol widening could break
  Python-backend-only consumers' type-checking — contradicting the out-of-scope promise that
  Python-backend consumers see no change. Constraining to additive widening closes the gap.

requirements-7:
- Disposition: Won't-Do
- Action: None. Not a finding — the reviewer's own confirmation that the core scope correction
  (no-Python-object-reference; children listed; "not an enumerated list") is correctly addressed
  per the user correction. Nothing to apply.
- Severity assessment: None. Confirmation only.
- Rationale (Won't-Do): No actionable defect; the reviewer explicitly states "No finding."
  Applying anything would be churn with no source-backed problem to solve.
