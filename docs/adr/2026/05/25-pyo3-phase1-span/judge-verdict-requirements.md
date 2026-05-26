# Judge verdict — requirements review

Phase: requirements. Doc: `docs/adr/2026/05/25-pyo3-phase1-span/requirements.md`. Round 1.
Notes: 1 reviewer file; 7 findings.

## TODO walk

### requirements-1 — TODO(better-api-scope)
Reviewer claim: "better API" (`text()`, `with_source()`) is scope creep beyond phase plan; consequence is Phase 1 grows and makes premature API commitments.
Q1 (worth doing): yes — phase plan explicitly limits Phase 1 to Span replacement; gating the better API on user confirmation is necessary.
Q2 (design/owner input required): yes — whether to expand Phase 1 scope is a product-owner call, not an implementer or reviewer decision.
Action taken: moved better API to conditional on OQ5; OQ5 proposes deferral pending user confirmation. The requirements doc now correctly gates this.
Assessment: TODO acceptable. The OQ5 anchor `{#better-api-scope}` in the doc tracks the decision point. No TODO.md entry needed for a doc-phase open question that is self-tracking.

### requirements-5 — TODO(better-api-scope)
Same finding as requirements-1 (OQ3's "Propose" wording implied scope expansion without flagging it). Responder reworded OQ3 to defer, added OQ5 to explicitly gate scope.
Assessment: same as requirements-1. Acceptable.

## Other findings walk

### requirements-2 — Fixed
Claim: "Rust Struct Layout" subsection is design, not requirements; consequence is designer cannot choose alternative representations.
Requirements doc Protocols section (lines 147-158) contains only "PyO3 Module Registration" and "Re-export Pattern" — no struct layout subsection. Observable constraints (immutability, equality semantics, thread safety) retained in Constraints section (lines 164-171).
Assessment: fix removes the over-specification while preserving observable constraints. Accept.

### requirements-3 — Fixed
Claim: memory constraint prescribes mechanism (`Option<Arc<str>>`, 8 bytes); consequence is locking out alternative designs.
Requirements doc line 167: "sourceless spans should not pay significant per-instance memory overhead for the source-reference capability." No byte count, no mechanism.
Assessment: fix replaces mechanism with outcome. Accept.

### requirements-4 — Won't-Do
Claim: specifying exact Python re-export code is implementation detail; consequence is "minor — unlikely to cause real harm."
Rationale: re-export line is the only mechanism preserving import paths (a hard acceptance criterion), is user-visible source, and is the standard PyO3 pattern; removing it underspecifies.
Assessment: reviewer concedes "minor" and "unlikely to cause real harm." Responder's argument that the re-export is an observable integration point is correct — `terminalsrc.py`'s contents are part of the public module surface. Won't-Do sound.

### requirements-6 — Fixed
Claim: `UnknownSpan is UnknownSpan` as hard requirement is overspecified given zero evidence of `is` checks.
Requirements doc line 75: "UnknownSpan is UnknownSpan should be True (singleton preferred, but not a hard requirement)." Not in acceptance criteria (lines 86-95).
Assessment: downgrade to "should" addresses the finding. Accept.

### requirements-7 — Fixed
Claim: "no changes to any file other than terminalsrc.py and Rust source" contradicts testability of new API surface.
Requirements doc lines 20-21: constraint now reads "no modifications to existing test files or non-terminalsrc.py Python source" with "new test files may be added for new API surface."
Assessment: fix resolves the contradiction. Accept.

## Approved

7 findings: 4 Fixed verified, 1 Won't-Do sound, 2 TODOs acceptable.

---

## Verdict: APPROVED
