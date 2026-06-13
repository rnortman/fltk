# Judge verdict — design review

Phase: design. Doc: `docs/designs/pyo3-upgrade/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 2 findings.

Style note (applies to this doc): concise, precise, complete, unambiguous; audience is a smart
LLM/human implementer.

## Findings walk

### design-1 — Fixed
Claim: §2.G warning accounting wrong — design said "NodeKind + 18 label enums for fegen.fltkg";
actual is 2 NodeKinds + 17 label enums across two generated grammars; consequence is a
misleading step-5 verification target (phantom-residual hunting, or missed surviving
PoC-grammar warnings).
Severity: should-fix (groundedness error in an implementer-facing verification target; no
behavioral consequence in the fix itself).
Evidence: design.md §2.G now reads "2 NodeKinds + 17 label enums across the two compiled
grammars — `src/cst_fegen.rs` (1 NodeKind + 14 label enums) and `src/cst_generated.rs`
(PoC grammar, 1 NodeKind + 3 label enums). Step-5 verification target: warnings clear in BOTH
files, not just `cst_fegen.rs`." Independently verified ground truth: grep counts 14
`name = "*_Label"` pyclass attrs in `src/cst_fegen.rs`, 3 in `src/cst_generated.rs`; 1 NodeKind
each → 19 total. Reviewer's breakdown correct; fix matches it and adds the both-files
verification note the consequence called for.
Assessment: fix addresses claim and consequence. Accept.

### design-2 — Fixed
Claim: omission — plan never updates `docs/rust-cst-extension-guide.md`, whose Cargo.toml
template pins `fltk-cst-core = "0.1"` and `pyo3 = "0.23"`; consequence is downstream consumers
following the published guide post-upgrade build exactly the mixed-version extension the §1
0.2.0 ABI marker exists to reject, with no documented remediation — a break in
CLAUDE.md-protected public surface.
Severity: blocker-adjacent should-fix for a design doc (avoidable downstream break in protected
surface; cheap to plan for).
Evidence: design.md §3 step 8 now includes: update `docs/rust-cst-extension-guide.md` template
`fltk-cst-core = { version = "0.1", ... }` (line 59) → `"0.2"` and
`pyo3 = { version = "0.23", ... }` (line 63) → `"0.29"`, plus a note that existing consumer
extension crates must be rebuilt against fltk-cst-core 0.2 + pyo3 0.29 (§1 ABI marker rejects
old builds with `TypeError`). Independently verified ground truth: guide currently pins both
stale versions at the cited lines (`fltk-cst-core = { version = "0.1", ... }`,
`pyo3 = { version = "0.23", features = ["abi3-py310"] }`).
Assessment: fix addresses claim, consequence, and the reviewer's suggested remediation in full.
Accept.

## Disputed items

None.

## Approved

2 findings: 2 Fixed verified.

---

## Verdict: APPROVED

Both dispositions acceptable; both fixes present in the design doc and verified against ground
truth. Round 1.
