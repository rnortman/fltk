# Requirements Review — Phase 4 Runtime Integration

Adversarial review of `requirements.md` against the reshaped request + `exploration.md`. Big-picture sanity check. Did not read code.

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Overall: strong doc. Correctly interprets the reshape (runtime-contract-only, dual backend, no silent fallback, static-consumer immutability). Properly fences the `UNKNOWN_SPAN` build problem out as a non-requirement. Defers design choices to open questions rather than over-specifying. Findings below are scope-edge and coherence issues, not structural defects.

---

## requirements-1 — Acceptance criterion 3/5 + AC6 presuppose a working build artifact, but artifact production is Out of Scope

Section: Acceptance Criteria 3, 5, 6; cross-ref Out of Scope ("Resolving the `crate::UNKNOWN_SPAN` linkage").

What's wrong: AC3 ("a full parse → CST → unparse round trip on a non-FLTK grammar succeeds"), AC5 (`fltk2gsm.py` against a Rust-backed CST module for the FLTK grammar), and AC6 (Makefile produces a loadable artifact) all require a *real, loadable, correct* Rust CST `.so` for a specific grammar to exist. But the doc explicitly scopes out "Resolving the `crate::UNKNOWN_SPAN` linkage architecture" and labels `artifact-build-mechanism` an unresolved open question. Exploration is blunt: "No viable Rust-level solution exists without architectural changes" (exploration line 254); options A–E each carry a cost (full crate rebuild, codegen change, workspace restructure). If no build mechanism is chosen, AC3/AC5/AC6 cannot be met — the runtime contract is testable only against an artifact that the open question may not yet permit.

Why: Out of Scope, line 29: "The requirement is that *some* build path produces an artifact exposing `register_classes`; how it resolves `UNKNOWN_SPAN` is a design/build decision." Yet AC6 (line 130) demands "The Makefile produces a loadable Rust CST artifact." The doc both defers the build mechanism and requires its output as an acceptance gate.

Consequence: Phase 4 cannot be declared done without resolving the open question it declares out of scope — a circular dependency. The designer hits a wall: either the open question must be answered inside Phase 4 (contradicting Out of Scope), or AC3/5/6 are untestable and Phase 4 has no end-to-end validation, reducing it to plumbing that nothing exercises.

Suggested fix: State the dependency explicitly — Phase 4's end-to-end ACs (3, 5, 6) are gated on `artifact-build-mechanism` being resolved first, and that resolution is a prerequisite, not a parallel concern. Or split: runtime-contract ACs (1, 2, 4, 7-Python-side) ship independently; artifact-dependent ACs (3, 5, 6) move behind the build-mechanism decision. The reviewer should not silently inherit a chicken-and-egg gate.

## requirements-2 — `register_classes` against a Python-created `types.ModuleType` is an unverified assumption, treated as settled

Section: Rust-backend path behavior, step 2 (line 54); Acceptance Criteria 2.

What's wrong: The doc states `register_classes` is "called against a freshly created `types.ModuleType`, populating it with the CST node classes." But exploration Open Factual Question 5 (lines 262) flags exactly this as unverified: `register_classes(module: &Bound<'_, PyModule>)` is currently fed a Rust-created `PyModule::new` object in `lib.rs`; whether a Python-side `types.ModuleType` (especially one not yet in `sys.modules`) is accepted as `Bound<PyModule>` "needs verification." The requirement asserts the mechanism works; exploration says it might not.

Why: Exploration line 262: "a freshly created `types.ModuleType` on the Python side — before it is registered in `sys.modules` — may not be accessible this way... Compatibility needs verification." Requirements line 54 presents this as the definite path with no caveat or open question.

Consequence: If `register_classes` rejects a Python `types.ModuleType`, the entire integration approach in step 2 must change (e.g., register in `sys.modules` first, then import and let PyO3 see it; or have the artifact create its own module). A requirement asserting an unverified mechanism as fact risks the designer building to a contract the runtime can't satisfy, discovered late.

Suggested fix: Demote the `types.ModuleType` mechanism from asserted fact to a constraint-with-open-question: "the artifact's `register_classes` must populate the CST module the runtime registers in `sys.modules`; whether that module is a Python-created `types.ModuleType` or one the artifact creates is an open question pending verification (exploration Q5)." Keep the *contract* (classes end up in `sys.modules[cst_module_name]`); release the *mechanism*.

## requirements-3 — `module-name-stability` open question is partially undercut by the `selector-shape (b)` proposal, leaving an unstated tension

Section: Module-name convention (line 68); Open questions `selector-shape`, `module-name-stability`.

What's wrong: The doc proposes `selector-shape (b)` (a filesystem path → Rust) and `module-name-stability: path-based` (keep `fltk_grammar_{id(grammar)}`, load per call). This is internally consistent, but it quietly forecloses the by-name discovery model that exploration spent significant effort on (exploration lines 144-156, 187-195, "the module name must be deterministic"). If the chosen build mechanism (open question `artifact-build-mechanism`) turns out to be Option A/E — user grammar compiled *as a submodule of `fltk._native`* — then the artifact is NOT a standalone `.so` at a path; it is `fltk._native.{name}`, and `selector-shape (b)`'s path argument cannot reference it. The doc notes this dependency once (line 153) but the proposed answers to the two selector questions assume the standalone-`.so` world.

Why: Open question `artifact-build-mechanism` line 153: "the runtime selector's artifact-reference form (`selector-shape`) depends on whether the artifact is a standalone `.so` path or a `fltk._native` submodule name." Exploration Option A/E (lines 136, 144) is the pattern Phase 3 actually uses and the only one needing no architectural change — making submodule-by-name the *most likely* build outcome, yet the one `selector-shape (b)` can't express.

Consequence: If the designer answers `selector-shape` and `module-name-stability` first (per the proposals) and `artifact-build-mechanism` later lands on submodule-in-`_native`, the selector API must be reworked. The three open questions are coupled and must be resolved together; the doc's per-question proposals invite resolving them in an order that creates rework.

Suggested fix: Add an explicit note that `selector-shape`, `module-name-stability`, and `artifact-build-mechanism` are coupled and must be decided as a set; the path-based proposals are contingent on the build mechanism producing a standalone artifact. Do not let the reviewer/designer lock the selector shape before the build mechanism is known.

## requirements-4 — Static-consumer immutability is asserted for both backends but only verified for one

Section: Constraints "Static-consumer immutability" (line 116); API Contract (lines 82-99); Acceptance Criteria 7.

What's wrong: The doc requires `fltk_parser.py`, `fltk_trivia_parser.py`, `fltk2gsm.py`, and formatter CST modules to "work against either backend with zero source changes," and AC7 says both backends produce modules "satisfying every item in the API Contract." For the Rust backend this is asserted as satisfied "via the Phase 2 `Py<PyList>` approach (validated in Phase 2 acceptance tests)" (line 99). But Phase 2 validated *hand-written* nodes (`Identifier`, `Items`) for *two label cases* (phase-plan lines 67-92). It did not validate the *generated* Rust CST for the full FLTK grammar against the *actual* `fltk2gsm.py` operations (stride slices on odd-length lists, `children[0][0] in (...)`, all 12 contract items across 14 classes). Phase 3 tested "API equivalence" but the doc gives no evidence Phase 3 ran `fltk2gsm.py` itself against the generated Rust module.

Why: Requirements line 99 leans on "validated in Phase 2 acceptance tests" to discharge the contract, but Phase 2's scope (phase-plan lines 66-88) is two hand-written nodes, not the generated full-grammar module that the static consumers actually touch. AC5 (line 129) is in fact the *first* place `fltk2gsm.py` runs against a Rust-backed FLTK CST — so the contract is being asserted as pre-validated when AC5 is what would actually validate it.

Consequence: The doc may lull the designer into treating the contract as already met, skipping the real integration test. If a generated-code path differs from the hand-written Phase 2 nodes (e.g., a label-enum `__hash__` edge case, an empty-children slice, a leaf-node tuple shape), `fltk2gsm.py` breaks and the "zero source changes" guarantee fails — exactly the subtle-API-mismatch risk phase-plan R-Phase-5 (line 186) flags.

Suggested fix: Reframe line 99: the contract is *claimed* satisfiable by the `Py<PyList>` approach but is *verified* only by AC5 (full `fltk2gsm.py` against generated Rust FLTK CST). Make AC5 the binding verification, not a redundant check on top of an already-discharged contract.

## requirements-5 — "Existing tests pass unchanged" is correct for Python path but ambiguous about whether any test exercises the Rust path by default

Section: Constraints "Existing tests pass unchanged" (line 117); Acceptance Criteria 1.

What's wrong: AC1 says Python-backend behavior is "exactly as today; all existing tests pass unchanged." Good. But the doc never states whether the Rust-path ACs (2-5) run in the *default* test suite (`uv run pytest`) or only when a Rust artifact has been built. Given the build mechanism is unresolved and may require a slow full-crate rebuild (exploration line 136, Q4 line 260), the Rust-path tests may be un-runnable in ordinary CI without the Makefile build step having run first. The doc does not say whether these tests are skipped-when-absent, gated behind a marker, or hard-required.

Why: AC6 (line 130) requires the Makefile to produce the artifact; AC2-5 require the artifact to exist to test. Constraints line 117 and CLAUDE.md both note the Rust extension must be built before tests. But the doc is silent on test wiring for the Rust path — whether absence of a built artifact skips or fails those tests.

Consequence: Without a stated policy, the designer may write Rust-path tests that hard-fail on any machine/CI lane that hasn't run the Makefile build, breaking the default `uv run pytest` for contributors without the artifact — directly contradicting the "first-class, opt-in, no friction for Python users" posture (Constraints line 119). Or, conversely, silently skip and never actually validate the Rust path in CI.

Suggested fix: Add an acceptance note specifying the test policy for Rust-path ACs: e.g., "Rust-backend tests require the Makefile artifact target to have run; in its absence they skip (not fail), and CI runs the build target before pytest." This is a behavior/surface decision (CI + test ergonomics), not an implementation detail.

## requirements-6 — `genparser-rs-emit-command` open question may leak Makefile-orchestration design into a requirements concern, but is correctly left open — minor

Section: User-Visible Surface (line 108); Open question `genparser-rs-emit-command`.

What's wrong: The open question and its proposal ("Makefile invokes a thin emit step (CLI subcommand or `python -m` one-liner)") edge toward prescribing *how* the Makefile calls the generator. That is build-orchestration design, not a runtime-contract requirement. It is correctly flagged as an open question rather than mandated, so this is minor — but the proposal's parenthetical ("CLI subcommand or `python -m` one-liner") is the kind of mechanism choice the designer should own.

Why: The doc's own framing (line 11, line 26) puts build orchestration in the Makefile and out of the runtime contract. Whether `.rs` emission is a Typer subcommand vs a module entry point is a design detail with no observable contract consequence beyond "discoverable + documented" (already stated for Makefile targets, line 107).

Consequence: Low. If the proposal is read as a directive, the designer is nudged toward a specific invocation shape without reason. No build-wrong risk if treated as the open question it is labeled.

Suggested fix: Trim the proposal to the observable requirement only: "`.rs` emission must be invocable as a documented, testable step; compilation stays in the Makefile." Drop the subcommand-vs-one-liner mechanism hint, or keep it explicitly as a non-binding example.

---

Note: this file authored per the review brief — concise, precise, complete, unambiguous; no padding; audience smart LLM/human.
