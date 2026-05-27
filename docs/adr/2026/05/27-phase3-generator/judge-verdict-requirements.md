# Judge verdict — requirements review

Phase: requirements. Doc: `docs/adr/2026/05/27-phase3-generator/requirements.md`. Round 1.
Notes: 1 reviewer file; 14 findings.

## Added TODOs walk

### requirements-8 — TODO(fegen-compilation-mechanism)
OQ-fegen-compilation-test at requirements.md:149. Whether fegen.fltkg compilation test compiles into a loadable extension or validates source text only.

Q1 (worth doing): Yes — the choice has real scope implications (adding a module to `lib.rs` + rebuild vs. source-text-only checks). Must be decided before design.

Q2 (design/owner input required): Yes — this is a build-system scoping decision with tradeoffs the user should weigh. The responder's recommendation (compile it) is sound but the user hasn't confirmed.

Assessment: TODO acceptable. The OQ is preserved in the requirements doc with a recommendation. Note: the slug `fegen-compilation-mechanism` is not registered in `TODO.md`, but in a requirements phase this is an open question annotation, not a code-level TODO — the OQ text in the doc itself serves the tracking purpose.

## Other findings walk

### requirements-1 — Fixed
Claim: "Public API" section specifies concrete class/method names (`RustCstGenerator`, `gen_rs_module`), which are design decisions. Consequence: needlessly constrains designer.
Requirements doc lines 113-115: "The module must expose a callable that accepts a `gsm.Grammar` and returns a `str` of compilable Rust source." No concrete names. Fix addresses the finding.
Assessment: Accept.

### requirements-2 — Fixed
Claim: Contradictory instructions — input section says grammar is preprocessed, public API says constructor preprocesses. Consequence: double-added trivia rules or implementer confusion.
Requirements doc line 46: "A raw `gsm.Grammar` object. The generator applies `add_trivia_rule_to_grammar` and `classify_trivia_rules` internally." Line 115-116 consistent. No contradiction remains.
Assessment: Accept.

### requirements-3 — Fixed
Claim: Exact Rust method signatures are design, not requirements. Consequence: locks designer into specific PyO3 patterns.
Requirements doc lines 129-131: replaced with "Python-visible API contract" paragraph. Internal Rust details are explicitly called design choices. AC-6 and AC-11 capture the behavioral contract.
Assessment: Accept.

### requirements-4 — Fixed
Claim: Generated Rust file structure (ordering) is design. Consequence: constrains designer when compiler doesn't care.
No "Generated Rust file structure" section exists in the doc. Removed as part of requirements-3 fix. AC-10 and AC-5 remain as observable constraints.
Assessment: Accept.

### requirements-5 — Fixed
Claim: Ambiguity on `maybe_{label}` error message — "at least 2" vs. dynamic `{count}`. Consequence: only one implementation passes tests.
Requirements doc line 101: specifies `maybe_{label}` uses fixed string "at least 2" with early break. Verified against committed code (`cst_poc.rs` lines 213, 399, 487, 575, 663 all use "at least 2") and test assertion (`test_rust_cst_poc.py` line 124 asserts "at least 2"). Ground truth confirmed.
Assessment: Accept.

### requirements-6 — Fixed
Claim: Exact `lib.rs` integration code is design. Consequence: minor — overrides designer choices.
No `lib.rs` code block section exists. Removed as part of requirements-3 fix. AC-4 and AC-5 capture the observable requirements.
Assessment: Accept.

### requirements-7 — Fixed
Claim: "Byte-identical output" is over-specification. Consequence: adds testing burden, constrains implementation choices.
Requirements doc line 139: "Output should be deterministic to support diffing committed generated files." Weakened from "byte-identical." Ordering constraints retained (labels sorted, rules in grammar order) as the concrete mechanism.
Assessment: Accept.

### requirements-9 — Fixed
Claim: OQ-empty-label-enum should be resolved before design. Consequence: designer might encounter compile failure.
Requirements doc line 123: specifies behavior ("generator still emits a node struct with an empty label enum"). Line 151: OQ retained with analysis of how zero-label rules arise and three viable options. The behavioral requirement (don't crash) is stated; the implementation choice is left to design.
Assessment: Accept. The finding asked for resolution; the response partially resolves it (must handle, not crash) while leaving the mechanism to design. This is appropriate.

### requirements-10 — Fixed
Claim: "Instantiate `CstGenerator`... Do not duplicate" is a design constraint. Consequence: locks designer into specific reuse strategy.
Requirements doc line 22: "must produce output consistent with `gsm2tree.py`'s model analysis... How the generator obtains this model data is a design choice."
Assessment: Accept.

### requirements-11 — Fixed
Claim: 120-char line length for generated Rust is over-specification. Consequence: requires line-wrapping logic for no benefit.
Requirements doc line 143: "120 characters applies to the generator's Python source (project convention). Generated Rust output has no line-length requirement."
Assessment: Accept.

### requirements-12 — Fixed
Claim: `fegen.fltkg` vs. `fltk.fltkg` discrepancy with phase plan not noted. Consequence: minor cross-reference confusion.
Requirements doc line 28: "Note: the phase plan references `fltk.fltkg`, but the correct grammar is `fegen.fltkg`..." Clarifying note added.
Assessment: Accept.

### requirements-13 — Won't-Do
Claim: Scope expansion (fegen.fltkg + minimal grammar testing) beyond user's literal instruction. Consequence: reviewer itself said "Acceptable scope expansion. No action needed."
Rationale: Phase plan explicitly requires testing on at least two grammars. The scope expansion is directly supported by the authoritative scope document.
Assessment: Accept. The reviewer acknowledged this was acceptable, and the rationale correctly cites the phase plan. Won't-Do is sound.

### requirements-14 — Fixed
Claim: OQ-generated-file-location should be resolved. Consequence: minor — obvious answer left open.
No OQ-generated-file-location in the requirements doc. Removed; implied by AC-2 and AC-4.
Assessment: Accept.

## Approved

14 findings: 12 Fixed verified, 1 Won't-Do sound, 1 TODO acceptable.

---

## Verdict: APPROVED
