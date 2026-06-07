# Judge verdict — requirements review

Phase: requirements. Doc: `docs/adr/2026/06/06-rust-cst-native-span/requirements.md`. Round 1.
Notes: 1 reviewer file (`notes-requirements-requirements-reviewer.md`); 7 findings (6 actionable + 1 non-finding).

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

## Other findings walk

### requirements-1 — Fixed
Claim: title corrected but slug `rust-cst-native-span` is span-only legacy; a designer skimming the slug may re-narrow to span — the exact failure the user raged against. Consequence stated (re-narrowing). Reviewer rated minor; suggested an optional one-line guard in Goals.
Verify: doc lines 14-15 add a "Scope note" callout: "the ADR slug (`rust-cst-native-span`) is historical. The scope is **all** node-state fields, not span." Addresses the consequence at the named section (Goals).
Assessment: fix matches the suggested guard. Accept.

### requirements-2 — Fixed
Claim: children migration committed as firm scope (native enum, traversal API, accessor re-sourcing) while exploration warns it is "potentially the largest change"; magnitude not surfaced to requester. Consequence: requester discovers an API-reshaping project mid-build without a size checkpoint. Reviewer explicitly said do NOT drop from scope (user wants it) — only surface size + offer staging.
Verify: doc lines 18-23 add a "Scope-magnitude note": children is "dominant, API-shaping," "potentially the largest change," firmly in scope, requester may stage (span/scalar first, children second) or do atomically — "staging is an implementation-ordering choice and does not narrow scope."
Assessment: surfaces magnitude and offers staging without narrowing scope — exactly the requested fix. Accept.

### requirements-3 — Fixed
Claim: Open question `native-span-start-end` defaulted to (B), which keeps `.start`/`.end` off native Span and breaks out-of-tree call sites on Rust-backend adoption — contradicting CLAUDE.md "near-drop-in replacement … must not be forced to edit … call sites wholesale," which the doc itself lists as a constraint. Consequence: consumer-breaking default recommended against a stated project invariant.
Verify: doc line 189 now reads "Proposed default: (A)" with rationale citing the drop-in invariant ("`node.span.start`/`.end` is a call site, not just an import"); line 194 retains (B) as the explicit redirect. Decision remains the requester's.
Assessment: default flipped to the invariant-consistent option; redirect preserved. Source-backed (CLAUDE.md drop-in). Accept.

### requirements-4 — Fixed
Claim: repr listed among generator-emitted methods but no acceptance pins its output; if repr interpolates the span object's repr, node `repr()` changes observably while the behavioral-equivalence list omits repr. Consequence: undecided — either silent cross-backend repr divergence in snapshots/logs, or over-investment pinning repr nobody needs.
Verify: doc lines 144-146 add a Behavioral-equivalence line: repr "is **not** a tracked equivalence surface … Consumers must not depend on cross-backend repr equality; the generator need not reproduce the Python repr form."
Assessment: ambiguity resolved by explicit exclusion at near-zero cost. Accept.

### requirements-5 — Fixed
Claim: acceptance "grep / type audit … finds no Python-object-typed state field" edges toward prescribing the verification mechanism. Reviewer self-rated borderline/harmless; suggested rewording to "an audit … confirms …".
Verify: doc lines 76-77 read "an audit of every generated and hand-written CST node struct confirms no Python-object-typed state field." No "grep" phrasing remains; the permitted-`#[pymethods]` carve-out is retained.
Assessment: reworded to property-to-hold per the suggestion. Accept (low-stakes; fix is correct regardless).

### requirements-6 — Fixed
Claim: protocol annotation widened to "backend-agnostic types/unions" could break Python-backend-only consumers' type-checks (CLAUDE.md: changing the annotation surface to force downstream edits is breaking), contradicting the out-of-scope promise that Python-backend consumers "see no change." Interaction unresolved.
Verify: doc lines 52-56 pin the widening as "**additive** — a strict superset of the current annotation — so that existing Python-backend-only consumers' type-checks continue to pass with no required annotation edits," with a CLAUDE.md citation and an acceptance criterion (lines 55-56): a Python-backend-only consumer type-checking against the current `terminalsrc.Span` annotation still type-checks without edits after the widening.
Assessment: closes the gap by constraining to additive widening + explicit acceptance. Accept.

### requirements-7 — Won't-Do
Claim: explicitly "No finding" — reviewer's confirmation that the core scope correction (no-Python-object-reference; `children` listed; "not an enumerated list") is correctly addressed per the user correction.
Rationale: no actionable defect; applying anything would be churn with no source-backed problem.
Assessment: reviewer stated no finding; nothing to act on. Won't-Do correct.

## Disputed items

None.

## Approved

7 findings: 6 Fixed verified against doc text, 1 Won't-Do sound (explicit non-finding).

---

## Verdict: APPROVED

All dispositions acceptable. Every Fixed claim verified present in `requirements.md` at the named section and addresses the reviewer's stated consequence; the single Won't-Do declines an explicit non-finding. No re-narrowing, no consumer-breaking default, no unbounded annotation churn left open.
