# Requirements Review Findings

Concise. Precise. No padding. Audience: smart human/LLM.

---

## requirements-1

**Section:** "In Scope" — "Design decision on struct layout…", "Better API design…", "Handling of synthetic/sourceless spans…"

**What's wrong:** The "better API" (source-bearing spans, `span.text()`, `with_source()`) is not part of Phase 1 per the phase plan. The phase plan says Phase 1 is: implement `Span`, `UnknownSpan`, re-export, tests pass. The user's request says the Rust struct should be *designed with TerminalSource in mind* — that is a struct layout decision, not a user-facing API delivery. The requirements doc escalates "anticipate the design" into "expose `text()` and `with_source()` now," which is scope creep beyond both the phase plan and the request.

**Why:** Request says "design of the Rust equivalent of TerminalSource… needs careful consideration" and "we should expose both a compatible Python API and a *better* Python API." But the request doesn't say Phase 1 must ship the better API — it says Phase 1 must not paint itself into a corner. The phase plan explicitly scopes Phase 1 to Span replacement only.

**Consequence:** If "better API" is in-scope, Phase 1 becomes significantly larger and makes premature API commitments before `TerminalSource` is implemented in Rust. Also forces resolution of OQ1-OQ3 before coding can begin, blocking progress.

**Suggested fix:** Move "better API" to a design-only deliverable: Phase 1 produces a *written design decision* on how source refs will work (struct layout choice, API shape). Implementation of `text()`/`with_source()` defers to the phase that implements `TerminalSource` in Rust. The struct can include the `Option<Arc<str>>` field now (cheap, internal) without exposing Python API surface.

---

## requirements-2

**Section:** "Protocols / Protocol Schemas — Rust Struct Layout (constrained by requirements)"

**What's wrong:** This is design, not requirements. Specifying `#[pyclass(frozen)]`, `PartialEq`, `Eq`, `Hash`, `Option<Arc<str>>`, null pointer optimization — these are implementation details. A requirements doc should state observable behavior (which is already covered in "System Behavior" and "Acceptance Criteria").

**Why:** The document's own preamble says nothing about being a combined requirements+design doc. These details constrain the designer without observable-behavior justification.

**Consequence:** Designer cannot choose alternative internal representations (e.g., `i32` fields if analysis shows sufficient, or a different reference-counting strategy) without "violating requirements."

**Suggested fix:** Remove the "Rust Struct Layout" subsection. Keep the constraints that are observable: immutability from Python, equality semantics ignoring source reference, `Send + Sync` (observable as thread safety).

---

## requirements-3

**Section:** "Constraints — Memory"

**What's wrong:** "overhead for sourceless spans should be at most one pointer-width (8 bytes)" and "`Option<Arc<str>>` satisfies this" — over-specification. This prescribes implementation. The actual requirement is "memory overhead should be minimal for the common case (sourceless spans)." The designer should determine what "minimal" means and choose the mechanism.

**Consequence:** Same as requirements-2 — locks out alternative designs.

**Suggested fix:** State "sourceless spans should not pay significant per-instance memory overhead for the source-reference capability" and leave the mechanism to design.

---

## requirements-4

**Section:** "Re-export Pattern"

**What's wrong:** Specifies the exact Python code (`from fltk._native import Span, UnknownSpan`) to put in `terminalsrc.py`. This is implementation, not requirement. The requirement is: "all existing import paths continue to resolve to the Rust-backed types."

**Consequence:** Minor — unlikely to cause real harm, but sets a bad precedent for later phases where re-export details may matter more.

---

## requirements-5

**Section:** "Open Questions — OQ3: Deferred implementation vs. full implementation of better API in Phase 1"

**What's wrong:** The "Propose" answer says "Expose `text()` and `with_source()` now." This contradicts the phase plan's explicit scope. If the requirements doc is going to recommend this, it should be explicit that it's *expanding* Phase 1 scope, and the user should confirm. As written, it reads like a natural consequence rather than a scope expansion.

**Consequence:** Implementer builds and ships API surface that may be premature, creating backward-compatibility obligations before the full design (TerminalSource in Rust) is known.

**Suggested fix:** Reframe: "This would expand Phase 1 scope beyond the phase plan. Recommend user confirmation before proceeding."

---

## requirements-6

**Section:** "System Behavior — UnknownSpan" — "`UnknownSpan is UnknownSpan` is `True` (singleton)"

**What's wrong:** The `is` identity guarantee is stronger than what the exploration supports. Exploration says "No evidence of `is` checks on `UnknownSpan` in the codebase." Making this a hard requirement means the implementation must use PyO3's module-attribute caching pattern. While the exploration's OQ4 proposes singleton as "zero-cost," elevating it to a hard acceptance criterion means any implementation that returns a fresh `Span(-1,-1)` from the module attribute fails. This is fine as a nice-to-have but overspecified as a requirement given zero evidence of need.

**Consequence:** Low — singleton is easy to implement. But if it causes issues (e.g., pickling, subinterpreters), it's now a "bug" rather than a design choice.

**Suggested fix:** Downgrade to "should" or note it's aspirational. Or keep it but acknowledge it's a forward-looking guarantee, not backward-compatibility.

---

## requirements-7

**Section:** Overall / "In Scope" list item: "Full test suite passes with no changes to any file other than `terminalsrc.py` and Rust source."

**What's wrong:** This is probably too restrictive. If the better API (`text()`, `with_source()`) is in scope (per the doc's own scoping), new tests would need to be written — likely in a new test file or added to an existing one. The constraint "no changes to any file other than `terminalsrc.py` and Rust source" contradicts delivering testable new API surface.

**Consequence:** Either the better API ships untested, or the constraint is silently violated.

**Suggested fix:** Clarify: "No changes to existing test files required for backward compatibility. New test files may be added for new API surface."
