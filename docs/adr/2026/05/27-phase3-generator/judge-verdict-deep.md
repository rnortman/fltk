# Judge verdict — deep review

Phase: deep. Base 6f82c48..HEAD a79c7eb. Round 1.
Notes: 7 reviewer files; 19 findings.

## Added TODOs walk

### errhandling-4 — TODO(errhandling-count-context) at gsm2tree_rs.py:371
Q1 (worth doing): yes — all generated `child_{label}` methods share the identical panic message; distinguishing which class/label panicked saves debugging time when the invariant fires on a future generator change.
Q2 (design/owner input required): no — mechanical: interpolate `class_name` and `label` into the f-string template that already has access to both values. No design decision; purely a string format change in the generator.
Furthermore: this iteration introduced the generated methods; per rubric, problems this iteration created cannot be silently deferred.
Assessment: Q2 fails — do-now. **However**, the invariant has never fired and is provably unreachable by construction (count==1 implies found.is_some()). The TODO represents diagnostic polish on dead-code-in-practice. Severity is nit. The cost of deferring is near-zero. Leaning toward accepting the TODO given the trivially low consequence, but strictly per rubric this fails Q2. Disposition wrong.

### test-2 — TODO(test-class-is-type-body) at tests/test_fegen_rust_cst.py:67
Q1 (worth doing): yes — the `isinstance(cls, type)` body is vacuous; either strengthening or removing it is an improvement.
Q2 (design/owner input required): yes — whether to (a) delete the assertion body entirely, (b) replace with construction, or (c) mark as import-only smoke test is a test-design call that depends on how AC-7 / AC-8 boundaries are drawn. The AC-8a tests already construct all 14 classes; duplicating construction here is a question of test-suite organization.
Assessment: TODO acceptable.

### reuse-1/2/3 — TODO(extract-rule-name-to-class-name) at gsm2tree_rs.py:18
Q1 (worth doing): yes — four independent copies of the same transform; divergence risk is real.
Q2 (design/owner input required): yes — extraction touches `gsm2tree.py`, `gsm2unparser.py` (x2), and `gsm2tree_rs.py` across two packages. Placement (shared naming module vs method on a base class vs module-level function in gsm2tree.py) needs a design call. The pre-existing duplication (reuse-2/3 from gsm2unparser.py) means this is not a problem this iteration created alone — it added a fourth copy to three existing ones.
Assessment: TODO acceptable.

### quality-3 — TODO(refactor-rule-info-helper) at gsm2tree_rs.py:80
Q1 (worth doing): yes — duplicated derivation between `generate()` and `_register_classes_fn()` could diverge.
Q2 (design/owner input required): no — introducing a `_rule_info()` helper or local list within the same file is a mechanical refactor. No cross-file impact, no API change, no design decision. The two loops are in the same class; extracting shared computation is straightforward.
Furthermore: this iteration created both loops; per rubric, problems this iteration created cannot be silently deferred.
Assessment: Q2 fails — do-now. Disposition wrong.

### efficiency-1 — TODO(perf-label-identity-comparison) at gsm2tree_rs.py:289
Disposition says "Add TODO comment in generated Rust near the `tup.get_item(0)?.eq(&label_obj)?` pattern." No `TODO(perf-label-identity-comparison)` comment exists anywhere in the codebase — not in the Python generator, not in the generated `.rs` files, and not in TODO.md. The TODO was dispositioned but never actually placed.
Furthermore: looking at the substance — the pattern is inherited verbatim from Phase 2 and the design explicitly mandates matching Phase 2. Adding a TODO comment inside a generated Rust file is pointless (regeneration overwrites it). Adding it in the Python generator template is plausible but the generated output is what ships, not the template. The reviewer explicitly stated "not a regression" and "defer until profiling need exists."
Q1 (worth doing): uncertain — optimization of inherited pattern with no measured bottleneck.
Q2: yes — requires profiling data and a design decision on storage structure (identity comparison vs pre-grouped storage vs discriminant check).
Assessment: TODO acceptable in principle, but the TODO comment was never written. Missing TODO comment is a REWORK item.

## Other findings walk

### correctness-1 — Fixed
Claim: Rust generator silently emits degenerate struct for empty-model rules where Python generator raises `RuntimeError`; consequence is silent behavioral divergence between generators.
Diff at `gsm2tree_rs.py:93-99`: `generate()` now catches `KeyError`, checks `if not model.types`, and raises `RuntimeError` with the same message as the Python generator. The check runs before any emission, preventing degenerate structs. `_register_classes_fn()` is called from within `generate()` after the per-rule loop, so the check catches empty models before registration too.
Assessment: fix addresses the finding. Accept.

### errhandling-1 — Fixed
Claim: bare `KeyError` on missing `rule_models` key gives no context about which generator or pipeline stage failed.
Diff at `gsm2tree_rs.py:85-92` and `:456-463`: both loops now catch `KeyError` and re-raise as `RuntimeError` with rule name, function name, and available keys.
Assessment: fix addresses the finding. Accept.

### errhandling-2 — Won't-Do
Claim: `UNKNOWN_SPAN.get().expect()` panics instead of returning `PyResult::Err`; consequence is hard crash on init-order mistake.
Rationale: Phase 2 pattern, intentional design, `PanicException` is catchable from Python, init structure makes mis-ordering practically impossible.
Inspection: the `expect` is in the `#[new]` method template at `gsm2tree_rs.py:226-234`. PyO3 converts Rust panics in `PyResult`-returning methods to `PanicException`, which IS catchable. The init ordering is fixed by PyO3's module framework. The generator faithfully reproduces the Phase 2 template; changing it would be a Phase 2 design change outside this phase's scope.
Assessment: rationale is sound. Accept.

### errhandling-3 — Won't-Do
Claim: `UNKNOWN_SPAN.set().expect()` on double-init is dead code; should return `Err`.
Rationale: programming error sentinel; panic is appropriate; no production scenario reaches this path.
Inspection: `src/lib.rs:27-28`. PyO3's `#[pymodule]` prevents re-init in normal CPython. Panicking on invariant violation is idiomatic Rust. Pre-existing Phase 2 code.
Assessment: rationale is sound. Accept.

### errhandling-5 — Won't-Do
Claim: reviewer explicitly stated no finding; test fixture propagates exception with full traceback.
Rationale: recorded for completeness only.
Assessment: no finding to address. Accept.

### errhandling-6 — Fixed
Claim: `set_item` failure on `sys.modules` gives no context about submodule registration.
Diff at `src/lib.rs:44-49`: `.map_err` wraps the `set_item` error with `"Failed to register fltk._native.fegen_cst in sys.modules: {e}"`.
Assessment: fix addresses the finding. Accept.

### security-1 — Fixed
Claim: unvalidated grammar names interpolated into generated Rust enable build-time code injection.
Diff at `gsm2tree_rs.py:57-72`: `__init__` validates every `rule.name` and `item.label` against `^[_a-z][_a-z0-9]*$`, raising `ValueError` on violations. Validation runs before any emission.
Assessment: fix addresses the finding at the generator trust boundary. Accept.

### security-2 — Won't-Do
Claim: reviewer explicitly stated no finding; `sys.modules` key is a compile-time constant.
Rationale: no attack surface.
Assessment: no finding to address. Accept.

### test-1 — Fixed
Claim: `assert variant is not None` is vacuous; only the `repr` assertion is load-bearing.
Diff at `tests/test_fegen_rust_cst.py:124`: the `assert variant is not None` line is removed.
Assessment: fix addresses the finding. Accept.

### test-3 — Fixed
Claim: determinism tests only use small PoC grammar; multi-label fegen rules could expose ordering bugs.
Diff at `tests/test_gsm2tree_rs.py:408-429`: new `test_fegen_grammar_deterministic` parses `fegen.fltkg` independently and compares against the fixture-generated output.
Assessment: fix addresses the finding. Accept.

### test-4 — Fixed
Claim: four separate generator invocations for minimal grammar; crash-test `assert source` is redundant.
Diff at `tests/test_gsm2tree_rs.py:367-393`: `minimal_source` module-scoped fixture replaces four independent invocations. The crash-test (`test_minimal_grammar_does_not_crash` with `assert source`) is removed; the three content-checking tests use the shared fixture.
Assessment: fix addresses the finding. Accept.

### test-5 — Fixed
Claim: `>= 2` threshold would pass if one of three label enums were dropped.
Diff at `tests/test_gsm2tree_rs.py:228-233`: changed to `>= 3` with comment explaining PoC grammar has 3 label-bearing rules.
Assessment: fix addresses the finding. Accept.

### test-6 — Fixed
Claim: no test for `extend_{label}` or `maybe_{label}` on fegen classes.
Diff at `tests/test_fegen_rust_cst.py:166-225`: new `TestExtendAndMaybe` class with parameterized tests over all 14 classes for `extend_{label}` (append two via extend, verify count), `maybe_{label}` returns None when empty, returns child when one match, raises on two matches.
Assessment: fix addresses the finding thoroughly. Accept.

### test-7 — Fixed
Claim: `source.index("\n}", impl_start)` brace-matching is fragile.
Diff at `tests/test_gsm2tree_rs.py:455-458`: replaced with `re.search(r"impl Token \{(.+?)\n\}", source, re.DOTALL)`.
Assessment: fix addresses the finding. Accept.

### quality-1 — Fixed
Claim: unused `class_name` parameter suppressed with `# noqa: ARG002` in three generic methods.
Diff at `gsm2tree_rs.py:249,262,283`: `class_name: str` parameter and `# noqa: ARG002` removed from `_generic_append`, `_generic_extend`, `_generic_child`. Call sites at `:208-210` updated accordingly.
Assessment: fix addresses the finding. Accept.

### quality-2 — Fixed
Claim: `FEGEN_RULE_NAMES` is defined but never referenced.
Diff at `tests/test_gsm2tree_rs.py:312-313`: `FEGEN_RULE_TO_CLASS` zip now uses both constants. New `test_rule_name_to_class_name_mapping` at `:338-361` verifies each rule name maps to the expected class name via `class_name_for_rule_node`.
Assessment: fix addresses the finding by adding the missing test. Accept.

### efficiency-2 — Won't-Do
Claim: double-computation of per-rule derivation across `generate()` and `_register_classes_fn()`.
Rationale: dev-time generator only, negligible one-off cost. quality-3 TODO covers the structural concern.
Inspection: generator runs once per regeneration; no build-time hook. Reviewer explicitly flagged as not worth fixing.
Assessment: rationale is sound. Accept.

## Disputed items

- **errhandling-4 / TODO(errhandling-count-context)**: fails Q2 (mechanical string interpolation in the same f-string template). The invariant is provably unreachable and the consequence is nit-level. However, rubric says do-now when Q2 fails. Need: either do it now or provide a concrete reason it cannot be done now without design input.

- **quality-3 / TODO(refactor-rule-info-helper)**: fails Q2 (mechanical extraction of shared computation within the same file/class). This iteration created both loops. Need: either extract the helper now or provide a concrete reason it requires design input.

- **efficiency-1 / TODO(perf-label-identity-comparison)**: the TODO comment was dispositioned but never written anywhere in code. No `TODO(perf-label-identity-comparison)` exists in any source file or in TODO.md. Need: either place the TODO comment (with TODO.md entry) or change the disposition.

- **All four code TODOs** (`errhandling-count-context`, `extract-rule-name-to-class-name`, `refactor-rule-info-helper`, `test-class-is-type-body`) are missing from `TODO.md`. Per CLAUDE.md: "Adding a TODO requires both an entry in `TODO.md` and a `TODO(slug)` comment at the relevant location." Need: add entries for all accepted TODOs to TODO.md.

## Approved

15 findings: 10 Fixed verified, 4 Won't-Do sound, 1 TODO acceptable (test-2).

---

## Verdict: REWORK

Five issues:
1. `errhandling-4` TODO fails Q2 — do it now (interpolate class_name + label into the expect message template).
2. `quality-3` TODO fails Q2 — do it now (extract `_rule_info` helper or equivalent).
3. `efficiency-1` TODO comment never written — either place it or change disposition.
4. All four code TODOs missing from `TODO.md` — add entries per project convention.
5. `reuse-1/2/3` TODO acceptable but missing from `TODO.md`.
