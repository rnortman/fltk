# Dispositions: User Notes on Requirements

Concise. Precise. No padding.

---

## user-1: OQ3 and OQ5 ask "is this serious?" — answer is yes

- Disposition: Fixed
- Action: Removed OQ3 and OQ5 entirely. The "better API" (`text()`, `with_source()` or equivalent) is confirmed in scope for Phase 1. Updated In Scope and Acceptance Criteria to reflect this.
- Severity assessment: These questions blocked scope commitment on the most important user-facing deliverable.

## user-2: All other open questions are design questions

- Disposition: Fixed
- Action: Removed OQ1 (single type vs two types), OQ2 (source reference type), OQ4 (UnknownSpan identity). These are design decisions, not requirements. Requirements state what behavior is required; design decides how.
- Severity assessment: Keeping design questions in requirements conflates concerns and blocks implementation unnecessarily.

## user-3: Document over-specifies design

- Disposition: Fixed
- Action: Removed Protocols/Protocol Schemas section (PyO3 registration details, re-export implementation pattern). Removed design option discussions from User-Visible Surface (Option A vs Option B details). Removed internal struct layout mentions from In Scope. Stripped constraint language that dictates implementation approach (e.g., specific Rust types like `Arc<str>`, `Option<Py<PyAny>>`). Retained only observable behavior, acceptance criteria, and compatibility constraints.
- Severity assessment: Design in requirements creates false constraints and confuses implementers about what's negotiable vs. what's fixed.
