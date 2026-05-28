# Judge verdict — requirements review

Phase: requirements. Doc: `docs/adr/2026/05/28-pyo3-phase4-runtime-integration/requirements.md`. Round 1.
Notes: 1 reviewer file; 6 findings. All dispositioned Fixed.

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

(Requirements phase — no TODO walk.)

## Other findings walk

### requirements-1 — Fixed
Claim: ACs 3/5/6 + AC6 require a real, loadable Rust CST artifact, but artifact production ("resolving `UNKNOWN_SPAN` linkage") is Out of Scope (line 29) and the build mechanism is itself an open question. Consequence: circular dependency — Phase 4 cannot be declared done without resolving the question it scoped out, leaving the end-to-end ACs untestable.
Consequence assessment: real coherence defect; the doc both defers the build mechanism and gates acceptance on its output. Reviewer's consequence justifies action.
Edit verified: AC section (lines 123-133) now opens with a two-tier preamble. Tier 1 (ACs 1, 2, 4, Python half of 7) runtime-contract, build-mechanism-independent; Tier 2 (ACs 3, 5, 6, Rust half of 7) "gated on Open question `artifact-build-mechanism` being resolved first ... a prerequisite, not a parallel concern." Each AC tagged with its tier; AC7 split (line 133).
Assessment: fix names the dependency explicitly and removes the circularity by sequencing Tier 2 behind the build-mechanism decision — exactly the reviewer's suggested resolution. Accept.

### requirements-2 — Fixed
Claim: step 2 asserts `register_classes` populates a Python-created `types.ModuleType` as settled fact, but exploration Q5 flags PyO3 acceptance of an unregistered Python module as `Bound<PyModule>` as unverified. Consequence: if the mechanism is rejected at runtime the whole step-2 integration approach changes, discovered late.
Consequence assessment: legitimate — requirement asserting an unverified mechanism as fact is the failure the reviewer names. Justifies action.
Edit verified: line 54 now states the binding contract as the end-state ("CST classes end up as attributes on `sys.modules[cst_module_name]`") and demotes the mechanism to a new Open question `register-classes-module-type` (lines 173-177) citing exploration Q5, with options (a) register-then-pass / (b) pass-directly / (c) artifact-owns-module.
Assessment: contract kept, mechanism released to an open question — matches the suggested fix. Accept.

### requirements-3 — Fixed
Claim: the per-question proposals for `selector-shape (b)` (filesystem path) and `module-name-stability` (path-based) quietly foreclose the submodule-by-name model; if `artifact-build-mechanism` lands on the `fltk._native` submodule pattern (Phase 3's actual, lowest-cost pattern) the path-based selector cannot express it. Consequence: resolving the three coupled open questions in the proposed order risks a selector API the chosen build mechanism cannot support → rework.
Consequence assessment: real rework risk; the three questions are genuinely coupled. Justifies action.
Edit verified: Open Questions section opens with a "Coupling note" (line 141) naming all three questions, stating the path-based proposals are contingent on a standalone-`.so` outcome, that the submodule pattern cannot be expressed by `selector-shape (b)`, and "Do not lock `selector-shape` or `module-name-stability` before `artifact-build-mechanism` is known."
Assessment: matches suggested fix; prevents premature lock-in. Accept.

### requirements-4 — Fixed
Claim: line 99 discharged the API contract for the Rust backend via "validated in Phase 2 acceptance tests," but Phase 2 validated only two hand-written nodes (`Identifier`, `Items`) for two label cases — not the generated full-grammar module against actual `fltk2gsm.py` operations. AC5 is in fact the first real integration. Consequence: doc lulls designer into treating the contract as met, skipping the real test; a generated-code edge case silently breaks the "zero source changes" guarantee.
Consequence assessment: real — the subtle-API-mismatch risk flagged in the prior phase plan. Justifies action.
Edit verified: line 99 reframed — contract is "*claimed* satisfiable for items 6-8 via the Phase 2 `Py<PyList>` approach" but "verified for the Rust backend only by AC5," with AC5 named the binding integration test. AC5 (line 131) marked "the binding verification of the API Contract for the Rust backend"; AC7 (line 133) Rust half "verified by AC5, not pre-discharged by Phase 2."
Assessment: claimed-vs-verified distinction made; AC5 made binding. Matches suggested fix. Accept.

### requirements-5 — Fixed
Claim: AC1 correctly states existing tests pass unchanged on the Python path, but the doc never says whether Rust-path ACs (2-5) run in default `uv run pytest` or only when an artifact is built; given the build may require a slow full-crate rebuild, the policy (skip-when-absent vs hard-require vs marker) is unstated. Consequence: designer may hard-fail default pytest for Python-only contributors (contradicting the opt-in posture) or silently skip and never validate the Rust path in CI.
Consequence assessment: observable test/CI ergonomics, legitimately a requirements-surface decision. Justifies action.
Edit verified: AC section "Test wiring for Rust-path ACs" note (line 135) points to a new Open question `rust-test-policy` (lines 179-184) with options (a) skip-when-absent + CI builds before pytest / (b) hard-require / (c) marker-gated, proposal (a).
Assessment: surfaces the policy as an open question with a posture-consistent proposal. Matches suggested fix. Accept.

### requirements-6 — Fixed (reviewer self-rated minor)
Claim: the `genparser-rs-emit-command` proposal's parenthetical (Typer subcommand vs `python -m`) edges toward prescribing Makefile-orchestration mechanism, a design detail the designer should own. Consequence: low — if read as a directive it nudges an invocation shape without reason; no build-wrong risk. Reviewer rated minor and confirmed it is correctly left open.
Consequence assessment: low, explicitly minor; the cosmetic improvement is fair but not load-bearing.
Edit verified: open question (lines 167-171) adds an "Observable requirement" line (".rs emission must be invocable as a documented, testable step; compilation stays in the Makefile") and relabels the subcommand-vs-one-liner choice as "a design detail the designer owns — no observable contract consequence."
Assessment: trims to the observable requirement, keeps the mechanism hint as a non-binding example. Matches suggested fix. Accept.

## Approved

6 findings: 6 Fixed verified against requirements.md.

---

## Verdict: APPROVED

All six dispositions are Fixed and verified present in the doc; every reviewer finding carries a real consequence (five substantive coherence/scope-edge fixes, one minor cosmetic) and each edit addresses that consequence. Nothing disputed.
