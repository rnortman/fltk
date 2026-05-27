# Dispositions: Requirements Review — Phase 3

Concise. Precise. No padding. Audience: smart LLM/human.

---

requirements-1:
- Disposition: Fixed
- Action: Replaced concrete class/method names in "Public API" section with behavioral contract ("the module must expose a callable that accepts a `gsm.Grammar` and returns a `str`"). Naming left to design.
- Severity assessment: Would unnecessarily constrain the designer to a specific API shape when the observable contract is simple.

requirements-2:
- Disposition: Fixed
- Action: Made "Input" section say "raw `gsm.Grammar`" and "Public API" section say the callable applies trivia preprocessing internally. Removed OQ-trivia-preprocessing (resolved: generator does preprocessing). Consistent throughout.
- Severity assessment: Contradictory instructions (caller preprocesses vs. generator preprocesses) could cause double-added trivia rules or implementer confusion.

requirements-3:
- Disposition: Fixed
- Action: Replaced "Protocols / Method signatures" section (13 Rust signatures) and "Generated Rust file structure" and "lib.rs integration pattern" with a single "Python-visible API contract" paragraph. Behavioral contract is already captured by AC-6 (Phase 2 tests pass) and AC-11 (error messages).
- Severity assessment: Locked the designer into specific Rust/PyO3 patterns; made the requirements fragile to PyO3 version changes.

requirements-4:
- Disposition: Fixed
- Action: Removed as part of the requirements-3 fix (same section replacement). AC-10 (preamble) and AC-5 (register_classes) remain as the observable constraints.
- Severity assessment: Low — file-internal ordering is not externally observable.

requirements-5:
- Disposition: Fixed
- Action: Clarified AC-11 to specify that `maybe_{label}` uses a fixed string "at least 2" (with early break), matching the committed Phase 2 code and test assertions. Added explicit note that these match both source and tests.
- Severity assessment: The ambiguity was real — the Python `gsm2tree.py` uses dynamic `{n}` for both `child_` and `maybe_`, but the hand-written Rust Phase 2 code uses "at least 2" for `maybe_`, and the test asserts this exact string. The generated code must match the committed behavior, not the Python equivalent.

requirements-6:
- Disposition: Fixed
- Action: Removed as part of the requirements-3 fix (same section replacement). AC-4 and AC-5 capture the observable requirements.
- Severity assessment: Low — the integration pattern is obvious and already implied by AC-4/AC-5.

requirements-7:
- Disposition: Fixed
- Action: Weakened from "byte-identical output" to "output should be deterministic to support diffing committed generated files." Retained the ordering constraints (labels sorted, rules in grammar order) as the concrete mechanism.
- Severity assessment: Over-specification that adds testing burden without justification from the phase plan. Determinism for diffability is the actual goal.

requirements-8:
- Disposition: TODO(fegen-compilation-mechanism)
- Action: OQ-fegen-compilation-test already existed but lacked resolution. The question of how to compile and test the fegen.fltkg output (add module to lib.rs? separate extension? source-text only?) has real scope implications. Promoted to a named open question for user decision. Also softened AC-9 to allow source-text-only validation as a design choice.
- Severity assessment: Without resolution, the designer must make a build-system decision that could significantly expand scope. The recommendation (compile into `fltk._native`) is sound but should be confirmed.

requirements-9:
- Disposition: Fixed
- Action: Resolved OQ-empty-label-enum with factual findings: zero-label rules are possible in `gsm2tree.py` (labels populated only from items with non-None `item.label`; Python emits valid empty `Label(enum.Enum)`). Updated the OQ text with this analysis. Left the three options for the designer since all are viable, but noted the Rust generator must handle this case (not crash).
- Severity assessment: Without resolution, the designer might encounter a compile failure on a valid grammar and not know what to do.

requirements-10:
- Disposition: Fixed
- Action: Reworded in-scope item 2 from "instantiate `CstGenerator`... Do not duplicate model-building code" to "must produce output consistent with `gsm2tree.py`'s model analysis... How the generator obtains this model data is a design choice."
- Severity assessment: Locked designer into a specific reuse strategy that might not be the best approach.

requirements-11:
- Disposition: Fixed
- Action: Clarified that 120-char line length applies to the generator's Python source, not to generated Rust output.
- Severity assessment: Would require implementing line-wrapping logic in generated Rust code for no user benefit.

requirements-12:
- Disposition: Fixed
- Action: Added inline note at in-scope item 8 clarifying that the phase plan references `fltk.fltkg` but the correct grammar is `fegen.fltkg`. No behavioral change — the requirements already had the correct grammar.
- Severity assessment: Low — the requirements were already correct; this prevents cross-reference confusion.

requirements-13:
- Disposition: Won't-Do
- Action: None.
- Severity assessment: The scope expansion (fegen.fltkg + minimal grammar testing) is directly called for by the phase plan ("test with at least one non-FLTK grammar"). The user's instruction was narrower but the phase plan is the authoritative scope document.
- Rationale: The phase plan (line 109) explicitly requires testing on at least two grammars. Removing this testing would deviate from the plan. The user's instruction ("replace hand-written code with generated code") is about the primary deliverable, not an exhaustive scope statement. The generality testing is load-bearing for Phase 4 confidence.

requirements-14:
- Disposition: Fixed
- Action: OQ-generated-file-location removed. The answer is implied by AC-2 (cst_poc.rs deleted) and AC-4 (classes in fltk._native) — the generated file must be a committed `.rs` file in `src/`. Exact naming is a design choice.
- Severity assessment: Low — obvious answer, but leaving it open adds unnecessary indecision.
