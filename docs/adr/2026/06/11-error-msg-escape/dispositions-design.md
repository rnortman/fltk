# Dispositions: design review round 1 — error-msg-escape

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Notes: `notes-design-design-reviewer.md`. Design: `design.md` (edited in place).

design-1:
- Disposition: Fixed
- Action: Reworded the `Expected:` block bullet in "Edge cases / failure modes". Verified the finding against source: `py_repr_str` escapes only codepoints < 0x20 and 0x7f (`errors.rs:208`); C1 passes through raw, documented as a divergence at `errors.rs:188-190`; Python `repr` does escape C1. The bullet now states the verifiable claim (C0/DEL escaped, raw C1 is a preexisting documented divergence), scopes it out on the grounds that grammar tokens are author-controlled rather than untrusted input, and flags the C1-in-tokens case as a possible separate follow-up.
- Severity assessment: The original bullet was factually wrong and internally inconsistent with the design's own U+009B rationale; left as-is it would have justified an untested gap (raw C1 in Rust Expected blocks plus a cross-backend divergence) with a false premise. Actual runtime risk is bounded since tokens are grammar-author-controlled.

design-2:
- Disposition: Fixed
- Action: Replaced "Open questions: None" with an explicit user-confirmation item: escape set widened from the approved C0-only spec (request.md:25, triage item 4) to C0+DEL+C1; rationale retained under Decisions; fallback path stated (drop DEL/C1 rows, rest of design unchanged). The caret-pad rule remains adjudicated as a design decision.
- Severity assessment: Without the checkpoint, the implementation would deviate from a user-approved spec for out-of-tree-observable output and the parity tests would pin the wider set, making a later narrowing a second breaking change. Per CLAUDE.md, deviations affecting generated output must be deliberate, called-out decisions resolved by the user, not self-adjudicated.
