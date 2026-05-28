Concise. Precise. No padding. Audience: smart LLM/human.

## slop-1
- Disposition: Fixed
- Action: Deleted stray meta-instruction line from `docs/rust-cst-extension-guide.md:7`
- Severity assessment: Stray writing instruction shipped verbatim in user-facing guide; embarrassing but no functional impact.

## slop-2
- Disposition: Fixed
- Action: Added comment at `fltk/fegen/fltk2gsm.py:81` explaining that `cst_label` is a local walrus variable and `visit_identifier` reads only span offsets — no `self.cst` isinstance dispatch needed.
- Severity assessment: The claim that `cst_label` "references nothing in scope" was factually wrong (walrus assigns a local variable); the real concern was future-reader confusion. Comment addresses that without a code change.

## slop-3
- Disposition: Fixed
- Action: Replaced multi-line task-tracker docstring at `fltk/fegen/test_genparser.py:1-7` with a single-sentence reader-facing description.
- Severity assessment: Cosmetic; no test logic affected.

## slop-4
- Disposition: Fixed
- Action: Changed test docstring at `fltk/test_plumbing.py:450` from "behavior identical to before" to "Python backend is used; parser and cst_module are populated as usual."
- Severity assessment: Cosmetic narrative tell; no logic affected.

## scope-1
- Disposition: Fixed
- Action: Added `TestCst2GsmDefaultNamespace` class to `fltk/test_plumbing.py` with two tests: `test_default_cst_is_fltk_cst` (asserts `cst2gsm.cst is _fltk_cst`) and `test_default_namespace_produces_correct_grammar` (directly instantiates `Cst2Gsm(terminals.terminals)` without `cst=`, calls `visit_grammar`, compares rule names to `parse_grammar` baseline).
- Severity assessment: Missing unit guard for the DI refactor's backward-compatibility guarantee; a regression in the default `cst` path in `fltk2gsm.py` would only surface through integration paths rather than a focused unit test.

## scope-2
- Disposition: Fixed
- Action: Added `build-native build-test-user-ext build-fegen-rust-cst` build step to `.github/workflows/ci.yml` before `make check`, so all three Rust artifacts are built before pytest runs and Tier-2 tests execute rather than skip.
- Severity assessment: Without this wiring, every Tier-2 test (including binding ACs AC3, AC5, AC8) silently skipped in CI. The design explicitly states "a CI lane that skips every Tier-2 test is a failure signal." CI was not wired to build the artifacts despite the design assuming it was; this leaves the primary artifact-dependent verification suite inert in CI. The fix is mechanical: one added CI step.
