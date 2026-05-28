# Dispositions — Phase 4 Runtime Integration requirements review (round 1)

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Source-of-truth: `requirements.md`, `exploration.md`, the reshaped request. Each finding fact-checked before disposition; reviewers can hallucinate — none did here, all findings are grounded in the cited exploration/requirements lines.

---

requirements-1:
- Disposition: Fixed
- Action: Acceptance Criteria section. Added a two-tier preamble: Tier 1 (runtime-contract, Python-side — ACs 1, 2, 4, Python half of 7) ships independently; Tier 2 (artifact-dependent — ACs 3, 5, 6, Rust half of 7) is explicitly gated on Open question `artifact-build-mechanism` being resolved first as a prerequisite. Tagged each AC with its tier.
- Severity assessment: Without the tiering, the doc both defers the build mechanism (Out of Scope) and requires its output as an acceptance gate — a circular dependency that leaves Phase 4 with no end-to-end validation or forces re-importing the scoped-out question. High: it determines whether Phase 4 is declarable done.

requirements-2:
- Disposition: Fixed
- Action: System Behavior → "Rust-backend path behavior" step 2. Demoted the `types.ModuleType` mechanism from asserted fact to a binding end-state contract ("CST classes end up on `sys.modules[cst_module_name]`") plus a new Open question `register-classes-module-type` (added to Open Questions) capturing the unverified PyO3 `Bound<PyModule>` acceptance from exploration Q5.
- Severity assessment: Asserting an unverified mechanism as fact risks the designer building to a contract the runtime cannot satisfy, discovered late. Medium-high: the integration approach in step 2 changes entirely if the assumption fails.

requirements-3:
- Disposition: Fixed
- Action: Open Questions section. Added a "Coupling note" stating `selector-shape`, `module-name-stability`, and `artifact-build-mechanism` must be decided as a set; the path-based proposals are contingent on a standalone-`.so` build outcome; the submodule-of-`fltk._native` pattern (Phase 3's actual, lowest-cost pattern) cannot be expressed by `selector-shape (b)`. Instructed not to lock the selector shape before the build mechanism is known.
- Severity assessment: Resolving the open questions in the proposed per-question order can land a selector API that the later-chosen build mechanism cannot support, forcing rework. Medium: rework risk, not a correctness defect.

requirements-4:
- Disposition: Fixed
- Action: API Contract section closing paragraph + Acceptance Criteria 5 and 7. Reframed the Phase 2 claim: the `Py<PyList>` approach makes items 6-8 *claimed* satisfiable but not *discharged* — Phase 2 covered only two hand-written nodes, not the generated full-grammar module. Marked AC5 as the binding verification for the Rust backend and AC7's Rust half as verified by AC5, not pre-discharged.
- Severity assessment: The doc could lull the designer into treating the contract as already met and skipping the real integration test; a generated-code edge case (empty-children slice, label-enum hash, leaf tuple shape) would silently break `fltk2gsm.py` and the "zero source changes" guarantee. Medium-high: directly the subtle-API-mismatch risk flagged in the prior phase plan.

requirements-5:
- Disposition: Fixed
- Action: Acceptance Criteria section, added "Test wiring for Rust-path ACs" note pointing to a new Open question `rust-test-policy` (added to Open Questions): skip-when-absent vs hard-require vs marker-gated, with proposal (a) skip-when-absent + CI builds artifact before pytest.
- Severity assessment: Without a stated policy the designer may hard-fail default `uv run pytest` on machines without a built artifact (contradicting the opt-in posture) or silently skip and never validate the Rust path in CI. Medium: developer-ergonomics/CI surface, observable behavior.

requirements-6:
- Disposition: Fixed
- Action: Open question `genparser-rs-emit-command`. Added an explicit "Observable requirement" line (".rs emission must be invocable as a documented, testable step; compilation stays in the Makefile") and relabeled the Typer-subcommand-vs-`python -m` choice as a non-binding design detail the designer owns.
- Severity assessment: Low (reviewer also rated minor). The mechanism hint, if read as a directive, nudges the designer toward an invocation shape without reason; no build-wrong risk.
