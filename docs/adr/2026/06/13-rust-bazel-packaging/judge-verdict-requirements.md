# Judge verdict — requirements review

Phase: requirements. Doc: `/home/rnortman/src/fltk/.claude/work/clockwork-rust-packaging/requirements.md`. Round 1.
Notes: 1 reviewer file (requirements-reviewer); 7 findings, all dispositioned Fixed.

(Doc phase — no Added TODOs walk. The `TODO(...)` markers in the requirements doc are open-question slugs the user must ratify, not deferred-work code TODOs; they are evaluated as doc content under the relevant findings, not under the code-TODO rubric.)

## Other findings walk

### requirements-1 — Fixed
Claim: design/impl detail (invented Starlark rule/macro names `generate_rust_parser`, `fltk_pyo3_cdylib`; emitted file names `cst.rs`/`parser.rs`/`lib.rs`) leaks into normative "In scope" / "User-visible surface" / criterion 2. Consequence: designer reads invented names as mandated, or deviation gets flagged as scope drift — over-constrains the implementation.
Disposition: Fixed — restated behavior in normative text; moved example names to a non-normative appendix marked designer's choice.
Verify against doc: "In scope" (lines 22-28) states behavior ("a Bazel-visible way to run FLTK's Rust codegen ... and to build the resulting sources into an importable PyO3 cdylib") and explicitly defers shape: "The concrete shape (number of rules, macro names, intermediate file names) is the designer's choice — see 'Implementation notes (non-normative)'." User-visible surface (lines 113-116) repeats the designer's-choice deferral. New "Implementation notes (non-normative)" appendix (lines 271-289) holds the `generate_rust_parser`/`fltk_pyo3_cdylib`/`cst.rs`/`parser.rs`/`lib.rs` sketch, labeled "illustrative only." `gen-rust-cst`/`gen-rust-parser` retained as existing CLI subcommands (line 122, lines 278-281), which the finding itself sanctioned.
Assessment: fix addresses the consequence — the invented names no longer sit in normative scope. Accept.

### requirements-2 — Fixed
Claim: criterion 3 over-specifies the failure mechanism (white-box): tied done-gate to absence of a `warnings.warn` from `fltk/fegen/pyrt/span.py` and a verbatim `RuntimeError` string. Consequence: a correct implementation that reworks the fallback signaling spuriously fails, or the test becomes a brittle internal-string grep.
Disposition: Fixed — restated as observable outcome; demoted internal signals to diagnostic hints.
Verify against doc: criterion 3 (lines 76-85) now asserts "the canonical `fltk._native.Span` is resolved through the native (Rust) path ... a positive assertion confirms the span object returned through the generated accessors is the native `fltk._native`-backed type and carries correct offsets." The `warnings.warn` site and `RuntimeError` string are parenthetical: "(Diagnostic hints, not pass/fail gates: ...)".
Assessment: observable behavior is now the gate; internal signals demoted. Accept.

### requirements-3 — Fixed
Claim: criterion 5 (cross-backend equivalence) was simultaneously a "done" gate and an unresolved open question, with an undefined bar. Consequence: implementer reads the strong end and balloons into a differential-test harness, or reads the weak end and it duplicates criterion 4.
Disposition: Fixed — removed the standalone equivalence criterion; folded the minimal bar into criterion 4; TODO(equivalence-surface) states minimal is the default and only a stronger bar changes scope.
Verify against doc: no standalone equivalence criterion remains; criterion 4 (lines 87-96) bakes in the minimal bar ("the Rust parser agrees with Clockwork's existing Python parser on the same input for: parse success/failure and the top-level `module` rule structure"). Criterion 5 is now the unrelated "Pure-Python path intact" (lines 98-100). TODO(equivalence-surface) (lines 259-269): "the minimal bar is the default ... only the latter changes scope."
Assessment: the done-gate no longer depends on an unresolved decision. Accept.

### requirements-4 — Fixed
Claim: TODO(grammar-regex-subset) sat as an open question while criterion 1 silently assumed grammar compatibility; a discovered incompatibility forces an unanticipated Clockwork-source change. Consequence: criteria unreachable mid-project after Bazel plumbing is built — stall pending an unapproved grammar edit.
Disposition: Fixed — added "resolve this first, before any Bazel plumbing" with the cheap-derisking rationale and hard-blocker framing; added a compatibility-assumption parenthetical to criterion 1.
Verify against doc: TODO(grammar-regex-subset) (lines 247-257): "**Resolve this first, before any Bazel plumbing:** it is the single cheapest derisking step ... flag as a hard blocker if incompatible." Criterion 1 (lines 67-68): "(Assumes the grammar is regex-automata compatible; if not, this criterion is unreachable until the grammar is adjusted — see TODO(grammar-regex-subset) ...)."
Assessment: the blocker is surfaced and sequenced first; criterion 1's hidden assumption is made explicit. Accept.

### requirements-5 — Fixed
Claim: the request's "submodule vs pip" premise is mistaken (Clockwork uses `git_override`, not a submodule); the correction was buried in the open-question body rather than surfaced as the recommendation headline. Consequence (reviewer rates low): user approves under a wrong mental model.
Disposition: Fixed — added a bolded "Premise correction (lead with this in the recommendation)" at the top of TODO(dep-mechanism).
Verify against doc: TODO(dep-mechanism) (lines 183-189) leads with "**Premise correction (lead with this in the recommendation):** ... Clockwork does not consume FLTK via a git submodule — it uses a Bazel-module `git_override` ... So the actual decision is **git_override source-dep ... vs. wheel/pip packaging**, not submodule-vs-pip. Confirm this corrected framing matches the user's intent before choosing."
Assessment: correction is now the headline of the decision the user must ratify. Accept.

### requirements-6 — Fixed
Claim: the deliverable is two-headed (POC + genuine FLTK product changes); approving it approves shipping new public FLTK Bazel surface (rule/macro names become API), which the doc did not state. Consequence (low/informational): the FLTK-side surface ships without the public-API care CLAUDE.md demands.
Disposition: Fixed — added a "Note on scope of the FLTK-side work" paragraph.
Verify against doc: lines 32-39: "the FLTK changes here are not throwaway POC scaffolding — they are genuine FLTK product/feature work ... the new Bazel surface (rule/macro names, visibility) likewise becomes public API the moment a consumer loads it. Approving this work approves shipping that new public FLTK Bazel surface, which must get the same compatibility care CLAUDE.md demands of generated symbols."
Assessment: the public-API implication is now explicit. Accept.

### requirements-7 — Fixed
Claim: criterion 7 (ABI mismatch surfaces as typed error) is not a clean done-gate, because default mechanism (A) makes a mismatch unproducible. Consequence: implementer wastes effort building a deliberate-mismatch test, or the criterion is quietly ignored.
Disposition: Fixed — removed from the numbered list; folded into the Constraints "Single fltk-cst-core rlib version" bullet as an invariant.
Verify against doc: numbered acceptance criteria now run 1-5 only (no criterion 7). The ABI guard lives in Constraints (lines 142-147): "The ABI guard must remain effective across the Bazel-built artifacts: a mismatch must surface as the existing typed error, never a silent wrong answer ... This is an invariant to preserve, not a separately-tested acceptance gate — constructing a deliberate mismatch is out of scope for the POC."
Assessment: reclassified from a testable gate to a preserved invariant, matching the reviewer's suggested fix. Accept.

## Disputed items

None. All seven findings had stated consequences justifying their (low-to-medium) severity, and every Fixed disposition is verifiable in the current doc text.

## Approved

7 findings: 7 Fixed verified.

---

## Verdict: APPROVED

All seven requirements-reviewer findings carried real consequences and all seven Fixed dispositions are verifiable in the requirements doc. Design/impl detail moved out of normative scope (req-1), criteria 3-4 restated as observable behavior with the equivalence bar pinned to minimal (req-2, req-3), the grammar-regex blocker sequenced first (req-4), the dep-mechanism premise correction surfaced as the recommendation headline (req-5), the public-API implication of the FLTK Bazel surface made explicit (req-6), and the un-gateable ABI-mismatch item reclassified as an invariant (req-7).
