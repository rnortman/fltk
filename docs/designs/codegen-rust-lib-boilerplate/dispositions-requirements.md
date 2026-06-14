# Dispositions: requirements review — codegen-rust-lib-boilerplate

Round 1. Source-checked against the verbatim request (quoted in the reviewer notes) and
exploration.md. All five findings fact-checked as valid.

## requirements-1 — "fix its shape" license under-weighted; equivalence over-constrains
- Disposition: Fixed
- Action: System behavior → Standard consumer generator. Reworded the equivalence acceptance
  criterion to behavioral/import-surface equivalence and explicitly stated source byte-equivalence
  is not required. Added a "Note on shape" sanctioning normalization of the emitted `lib.rs`, citing
  the request's "we can fix its shape." Mirrored the softening in Constraints → Cross-backend
  equivalence and in the fltk._native special-case requirement (now "behaviorally equivalent at the
  Python-import surface", shape may be normalized).
- Severity assessment: A designer would otherwise reverse-engineer and replicate the exact existing
  files, foreclosing a cleaner uniform template the request explicitly invited and risking a more
  complex "exact replica" generator than wanted.

## requirements-2 — fltk._native singleton cost/benefit unsurfaced
- Disposition: Fixed
- Action: fltk._native special case section gained a "Cost/benefit caveat" flagging it as the
  lowest-confidence part of scope (singleton, no replicated-consumer payoff), kept in scope because
  the request named it. The `native-special-mechanism` open question now also asks the requester to
  confirm whether codegenning fltk._native is worth the specialized machinery, with options (a)
  generate it / (b) leave it hand-written.
- Severity assessment: Without this, a designer may build a bespoke generator path used by exactly
  one file with no recorded trade-off; surfacing it at the requirements gate lets the user cut scope
  before design effort is spent. Folded into the existing open question (already surfaces at the
  next gate), so no new TODO slug needed.

## requirements-3 — System behavior pins exact emitted Rust tokens (over-specification into design)
- Disposition: Fixed
- Action: Replaced the literal-source bullets (exact `use` lines, `mod` decls, `#[pymodule]`
  signature, `register_submodule(...)` body) in both the standard-consumer and fltk._native sections
  with observable constraints (module fn named exactly the module name; `cst`/`parser` submodules
  exposed and populated; Span types not re-registered; recursion_limit handled per Constraints). The
  sample Rust is retained but explicitly labelled "Illustrative (non-normative) shape" with a note
  that the designer may deviate as long as observable constraints hold.
- Severity assessment: Token-level pins would box the designer into exact strings even where a
  cleaner shape exists (conflicts with requirements-1) and would drift out of sync with real output
  trivia (import ordering, glob vs. enumerated imports per exploration §1).

## requirements-4 — recursion_limit left as unresolved fork inside Constraints
- Disposition: Fixed
- Action: Constraints → recursion_limit now resolved: the macro continues to own and inject
  `#![recursion_limit]` at assembly time and the generated `lib.rs` omits it — consistent with the
  Bazel surface (lines 119-123) that assumes macro-assembly continues. The direct-emit alternative
  is retained only as a named trigger for revisiting the resolution if the design changes the
  assembly path.
- Severity assessment: Left unresolved, the attribute could end up duplicated (compile error) or
  absent; resolving it removes an internally-inconsistent fork before it propagates into the Bazel
  rule design.

## requirements-5 — "byte-equivalent" acceptance unachievable and self-undercutting
- Disposition: Fixed
- Action: Subsumed by the requirements-1 edit: "byte-equivalent or behaviorally-equivalent" dropped;
  the single criterion is now behavioral/import-surface equivalence, with an explicit statement that
  source byte-equivalence is neither required nor expected (generator output is normalized by
  `make fix`).
- Severity assessment: Conflated source vs. compiled-module equivalence and the weaker "OR" clause
  made the stronger one meaningless; a literal-minded implementer could chase an impossible target or
  silently ignore the criterion, eroding trust in the acceptance list.
