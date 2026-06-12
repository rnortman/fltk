# Dispositions: design review round 1 — error-msg-bidi-escape

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Notes reviewed: `notes-design-design-reviewer.md` (this dir). One finding.

design-1:
- Disposition: Fixed
- Action: "9 codepoints" → "12 codepoints" in §Proposed approach → Set rationale (`design.md`, Set rationale paragraph). Fact-checked independently: PropList.txt `Bidi_Control` = 061C (1) + 200E..200F (2) + 202A..202E (5) + 2066..2069 (4) = 12; the design's enumeration was already correct and complete, only the cardinality was wrong.
- Severity assessment: The spec is designated normative and restated into code doc comments; a wrong count would propagate into the cross-pin documentation and fail any auditor's cross-check against UCD, undermining the stated auditability rationale. No behavioral impact (the enumerated set, table, and tests were already correct).
