# Judge verdict — requirements review

Phase: requirements. Doc: `docs/designs/codegen-rust-lib-boilerplate/requirements.md`. Round 1.
Notes: 1 reviewer file (requirements-reviewer); 5 findings, all dispositioned Fixed.

## Other findings walk

### requirements-1 — Fixed
Claim: doc pins generated output to equivalence with today's hand-written files ("byte-equivalent or behaviorally-equivalent", "behaviorally equivalent to the current hand-written one", "unchanged versus the current hand-written lib.rs"), under-weighting the request's explicit "we can fix its shape" license. Consequence: designer reverse-engineers and replicates the exact existing files, foreclosing a cleaner uniform template and risking an over-complex "exact replica" generator.
Doc inspection:
- Lines 62-65 "Note on shape": "the request explicitly sanctions reshaping the boilerplate ('it's boilerplate, and we can fix its shape')... the internal shape of the emitted `lib.rs` may be regularized/normalized."
- Lines 90-91 (acceptance): "Source-level byte-equivalence with the hand-written file is NOT required (and is not expected, since generator output is normalized by `make fix`)."
- Lines 105-106 (fltk._native): "behaviorally equivalent at the Python-import surface... the exact emitted source is a design choice and may be normalized."
- Lines 172-174 (Constraints → Cross-backend equivalence): "This constrains observable behavior, not the internal source shape."
Assessment: the shape-license is now stated in all three places the reviewer named, citing the request verbatim. Fix addresses the consequence. Accept.

### requirements-2 — Fixed
Claim: fltk._native is a singleton with non-reusable responsibilities; doc puts it in scope without surfacing that a generator whose only user is one in-tree file may cost more than the boilerplate it removes. Consequence: designer builds a bespoke path used by exactly one file with no recorded trade; requirements gate is where that "is this worth it" question belongs.
Doc inspection:
- Lines 114-120 "Cost/benefit caveat": "the replicated-consumer payoff... does not apply to it... this is the lowest-confidence part of the scope. See Open questions → `native-special-mechanism`, which now also asks the requester to confirm this sub-goal is worth the specialized machinery."
- Lines 197-201 (open question `native-special-mechanism`): "is codegenning `fltk._native` worth the specialized machinery at all?... Options: (a) generate it... (b) leave `fltk._native` hand-written."
Assessment: tension surfaced, kept in scope per the request's letter, and routed to the requester with explicit (a)/(b) options at the open-questions gate. Folding into the existing open question rather than minting a new slug is correct — it already surfaces at the next gate. Accept.

### requirements-3 — Fixed
Claim: System-behavior bullets enumerate literal Rust to emit (exact `use` lines, `mod cst;`/`mod parser;`, the `#[pymodule]` signature, the `register_submodule(...)` body) — that is design content at the wrong altitude. Consequence: designer boxed into exact strings even where a cleaner shape exists (conflicts with requirements-1), doc drifts out of sync on trivia (import ordering, glob vs. enumerated).
Doc inspection:
- Lines 53-61: bullets are now observable constraints — module fn "named exactly the supplied module name"; "exposes a `cst` submodule and a `parser` submodule, each populated by the registration entry point"; "does NOT re-register `Span`/`SourceText`/`UnknownSpan`"; recursion_limit "compatible with... resolved in Constraints."
- Lines 67-84: the sample Rust is retained under "Illustrative (non-normative) shape" with "The designer may deviate from this exact text as long as the observable constraints hold."
- Lines 105-112 (fltk._native): parallel treatment — observable/behavioral bullets, "the exact emitted source is a design choice."
Assessment: token-level pins replaced with observable constraints in both sections; sample relegated to explicitly non-normative. Addresses the consequence and stays consistent with requirements-1. Accept.

### requirements-4 — Fixed
Claim: recursion_limit is the one genuinely cross-cutting hazard but left as an unresolved either/or inside Constraints, while the Bazel surface assumes macro-assembly continues — internally inconsistent about which world we are in. Consequence: ambiguity about who owns recursion_limit propagates into the Bazel-rule design; attribute could end up duplicated (compile error) or absent.
Doc inspection:
- Lines 176-183 (Constraints → "`#![recursion_limit]` ownership (resolved)"): "the macro continues to own and inject this attribute at assembly time, and the generated `lib.rs` therefore OMITS it... The attribute must appear exactly once (macro-injected)." The direct-emit alternative is kept only as "the trigger for revisiting this resolution" if the design changes the assembly path.
Assessment: fork resolved with a stated default consistent with the Bazel surface (lines 151-156), not left open. "Exactly once" closes the duplication/absence consequence. Accept.

### requirements-5 — Fixed
Claim: "byte-equivalent ... module" conflates source vs. compiled-module equivalence, and "byte-equivalent OR behaviorally-equivalent" makes the stronger clause meaningless; byte-equivalence of generated source is a near-certain fail given `make fix`. Consequence: literal-minded implementer chases an impossible target, or the criterion gets silently ignored, eroding the acceptance list.
Doc inspection: line 90-91 — the "byte-equivalent or behaviorally-equivalent" phrasing is gone; the single criterion is now behavioral/import-surface equivalence, with "Source-level byte-equivalence... is NOT required (and is not expected...)." Subsumed by the requirements-1 edit as the disposition states.
Assessment: the self-undercutting "OR" is removed; one well-defined criterion remains. Accept.

## Approved

5 findings: all 5 Fixed verified against the current requirements.md.

---

## Verdict: APPROVED

All five reviewer findings have real consequences (designer mis-scope, foreclosed cleaner template, design-altitude over-specification, internally-inconsistent recursion_limit fork, meaningless acceptance clause), and all five Fixed dispositions are substantiated by the current doc text at the cited locations. No Won't-Do to test, no TODOs to score.
