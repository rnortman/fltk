# Judge verdict — design review

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Phase: design. Doc: `docs/adr/2026/06/11-error-msg-escape/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 2 findings.

## Findings walk

### design-1 — Fixed
Claim: the "Expected: block ... already escapes via py_repr_str/Python repr" bullet was false for C1 on the Rust side; consequence is the design justifying an untested gap (raw C1 in Rust Expected blocks + cross-backend divergence) on a false premise, internally inconsistent with the design's own U+009B rationale.
Premise verified against source: `errors.rs:208` escapes only `< 0x20 || == 0x7f`; `errors.rs:188-190` documents "Non-ASCII chars are emitted raw" — C1 passes through raw on the Rust side, and Python `repr` does escape C1. Finding accurate.
Fix verified: design.md "Edge cases / failure modes", Expected-block bullet now reads "py_repr_str escapes C0/DEL (`errors.rs:208`) but emits C1 raw — a preexisting, documented Python/Rust divergence (`errors.rs:188-190`)", scopes it out as author-controlled token text rather than untrusted input, and flags the C1-in-tokens case as a separate follow-up (with the cross-backend-pinning caveat). This is exactly the verifiable claim the reviewer asked for.
Assessment: fix addresses the comment in full. Accept.

### design-2 — Fixed
Claim: the DEL+C1 widening exceeds the user-approved C0-only spec (request.md:25, triage item 4) and the design self-adjudicated it via "Open questions: None"; consequence is either an unchecked deviation from a user-approved spec or a stale requirements doc with parity tests pinning the wider set — a user-judgment item per CLAUDE.md's deliberate-decision rule for out-of-tree-observable output.
Premise verified: request.md pins "Identical escaping of C0 controls (except `\t`; `\n` unreachable)" and frames the output change as "a deliberate, user-approved change". Finding accurate.
Fix verified: design.md "Open questions" now carries item 1 — explicit user confirmation of the C0 → C0+DEL+C1 widening, rationale retained under Decisions, fallback stated (drop DEL/C1 escape-table and test rows; everything else unchanged). The caret-pad rule remains adjudicated as a design decision, which the reviewer did not contest (request.md itself delegates caret behavior to the design).
Assessment: matches the reviewer's suggested fix (open-question checkpoint, widening and rationale kept). Accept.

## Disputed items

None.

## Approved

2 findings: 2 Fixed verified.

---

## Verdict: APPROVED

Both dispositions verified against the edited design and source. Note for the orchestrator: design.md Open questions item 1 (escape-set widening C0 → C0+DEL+C1) requires explicit user confirmation before implementation proceeds.
