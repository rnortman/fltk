# Dispositions: Requirements Review

Concise. Precise. No padding. Audience: smart human/LLM.

---

## requirements-1
- Disposition: TODO(better-api-scope)
- Action: Added open question to requirements doc. Moved "Better API" items from "In Scope" to conditional on user confirmation. Reframed OQ3 proposal.
- Severity assessment: Scope creep risk. Phase plan explicitly limits Phase 1 to Span replacement; shipping `text()`/`with_source()` creates backward-compatibility obligations before TerminalSource design is finalized.

## requirements-2
- Disposition: Fixed
- Action: Removed "Rust Struct Layout" subsection from Protocols section. Retained observable constraints (immutability, equality ignoring source ref, thread safety) in Constraints section.
- Severity assessment: Over-specification blocks alternative designs without adding observable-behavior clarity.

## requirements-3
- Disposition: Fixed
- Action: Replaced specific byte/mechanism language in memory constraint with "sourceless spans should not pay significant per-instance memory overhead for the source-reference capability."
- Severity assessment: Minor over-specification; prescribes mechanism rather than outcome.

## requirements-4
- Disposition: Won't-Do
- Action: None.
- Rationale: The re-export pattern is the *only* mechanism that preserves existing import paths without modifying downstream files (a hard acceptance criterion). It is an observable integration point, not a hidden implementation detail — the contents of `terminalsrc.py` are user-visible source. The exploration confirms this is the standard PyO3 re-export approach. Removing it would leave the requirement underspecified for an implementer.

## requirements-5
- Disposition: TODO(better-api-scope)
- Action: Same TODO as requirements-1. OQ3's "Propose" reworded to explicitly flag scope expansion and require user confirmation.
- Severity assessment: Same as requirements-1 — premature API commitment.

## requirements-6
- Disposition: Fixed
- Action: Downgraded `UnknownSpan is UnknownSpan` from acceptance criterion to a "should" note. Acceptance criteria now only require value equality (`UnknownSpan == Span(-1, -1)`).
- Severity assessment: Low practical risk but sets an unnecessary hard constraint unsupported by evidence of need.

## requirements-7
- Disposition: Fixed
- Action: Clarified constraint to: "No modifications to existing test files or non-`terminalsrc.py` Python source required for backward compatibility. New test files may be added for new API surface."
- Severity assessment: Contradicts testability of any new API surface; would force shipping untested code or silently violating the stated constraint.
