Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

---

## correctness-1

- Disposition: Fixed
- Action: Add `not model.types` check in `generate()` and `_register_classes_fn()` before emitting per-rule blocks; `gsm2tree_rs.py:50-55` and `:404-415`.
- Severity assessment: Design doc (design.md:338-340) incorrectly claims the check is inherited from `CstGenerator`; it is in `py_class_for_model` (emit path only), not in `__init__` (analysis path). The Rust generator silently emits a degenerate struct for empty-model rules where the Python generator raises `RuntimeError`. A grammar with a fully-suppressed rule would diverge silently — Python rejects, Rust accepts. No current test exercises this path, but it is a real behavioral divergence.

---

## errhandling-1

- Disposition: Fixed
- Action: Add explicit `assert`/`RuntimeError` for missing `rule_models` key in `generate()` and `_register_classes_fn()`; `gsm2tree_rs.py:51` and `:405`.
- Severity assessment: Bare `KeyError` with only the rule name is adequate for debugging within the generator but provides no context about which generator or pipeline stage failed. Since both loops use the same `_py_gen`, a missing key is an invariant violation; an informative error message here is cheap insurance.

---

## errhandling-2

- Disposition: Won't-Do
- Action: no change
- Severity assessment: `expect` on `UNKNOWN_SPAN.get()` panics when module init ordering is wrong; PyO3 converts Rust panics to Python `PanicException`, so it is recoverable. Changing to `PyResult::Err` would be marginally cleaner but this is intentional design inherited from Phase 2. The current init structure makes mis-ordering practically impossible for normal use.
- Rationale (Won't-Do): The Phase 2 pattern is intentional and validated. A `PanicException` with the message `"UNKNOWN_SPAN not initialized; fltk._native module not loaded"` is diagnostic enough. Converting to `Err(PyRuntimeError::...)` would be a Phase 2 pattern change outside this phase's scope. The generator faithfully reproduces the template; the template is correct by design.

---

## errhandling-3

- Disposition: Won't-Do
- Action: no change
- Severity assessment: `UNKNOWN_SPAN.set().expect(...)` on double-init is dead code in practice — PyO3's `#[pymodule]` framework prevents re-initialization in normal CPython use. Panicking on an invariant violation is correct.
- Rationale (Won't-Do): This is a programming error sentinel, not an expected runtime condition. The panic is appropriate. No production scenario reaches this path.

---

## errhandling-4

- Disposition: TODO(errhandling-count-context)
- Action: Add TODO comment at `gsm2tree_rs.py:323` (the `found.expect(...)` template line) noting that embedding class and label in the message would aid diagnosis if this invariant ever fires.
- Severity assessment: The invariant holds by construction; this has never fired in practice. The missing context (class name + label) would matter only during debugging of a logic error introduced by future generator changes. Low urgency.

---

## errhandling-5

- Disposition: Won't-Do
- Action: no change
- Severity assessment: Noted by reviewer as non-issue. Test fixture propagates `Exception` from `visit_grammar` as a fixture-setup error with full traceback — adequate for tests.
- Rationale (Won't-Do): Reviewer explicitly stated no finding. Recorded for completeness only.

---

## errhandling-6

- Disposition: Fixed
- Action: Add `.map_err` context wrapper on `set_item` call in `src/lib.rs:44`.
- Severity assessment: Failure of `import("sys")` or `getattr("modules")` is pathological (stripped/embedded interpreter only), but when it occurs the resulting error gives no indication that submodule registration was the goal. A one-liner context wrap makes the failure self-describing.

---

## security-1

- Disposition: Fixed
- Action: Add identifier validation in `RustCstGenerator.__init__`: validate every `rule.name` and every `item.label` across all rules matches `^[_a-z][_a-z0-9]*$`, raising `ValueError` for violations. Location: `gsm2tree_rs.py`, end of `__init__`.
- Severity assessment: Today the only production grammar producer is the regex-constrained `fegen.fltkg` parser, making this latent rather than live. However, `RustCstGenerator` is a public API accepting any `gsm.Grammar`, and programmatic grammar construction (already used in tests) is explicitly supported. A `rule.name` or `item.label` containing `"`, `;`, or `{` would produce malformed Rust or executable code in a `#[pymethods]` body — build-time RCE on the developer/CI host at `maturin develop` time. Validation is cheap and makes the trust assumption explicit.

---

## security-2

- Disposition: Won't-Do
- Action: no change
- Severity assessment: Reviewer noted this as not a finding. The `sys.modules` key is a compile-time constant; no injection vector.
- Rationale (Won't-Do): No attack surface identified by reviewer. Recorded for audit completeness.

---

## test-1

- Disposition: Fixed
- Action: Remove `assert variant is not None` from `tests/test_fegen_rust_cst.py:120` — the `repr` assertion subsumes it.
- Severity assessment: Vacuous assertion: every non-`None` Python object satisfies `x is not None`, and a missing attribute raises `AttributeError` before this line anyway. The only load-bearing assertion is `repr(variant) == ...`. Removing the dead assertion prevents misleading readers into thinking a meaningful null-check exists.

---

## test-2

- Disposition: TODO(test-class-is-type-body)
- Action: Add TODO comment at `tests/test_fegen_rust_cst.py:67` noting the assertion is weaker than the test name claims; a construction test would be stronger.
- Severity assessment: `isinstance(cls, type)` passes for any imported class including a misimported alias. Import success is the real AC-7 check; the body assertion adds little. The construction round-trip tests (AC-8a) already provide a stronger check. Weak but not wrong.

---

## test-3

- Disposition: Fixed
- Action: Add a determinism test in `tests/test_gsm2tree_rs.py` that instantiates two separate `RustCstGenerator` instances from the `fegen_source` fixture (or equivalently, generates the fegen grammar twice and compares).
- Severity assessment: Current determinism tests use the small PoC grammar (2 rules, ≤4 labels per rule). Multi-label fegen rules (e.g., `Item` with 6+ labels) could expose dict/set ordering bugs invisible with the 2-rule test. The determinism constraint is important for committed artifacts; strengthening the test is low-cost.

---

## test-4

- Disposition: Fixed
- Action: Consolidate `TestMinimalGrammar` into a `minimal_source` module-scoped fixture and remove the standalone crash-test whose only assertion (`assert source`) is subsumed by the content-checking sibling tests. `tests/test_gsm2tree_rs.py:339-363`.
- Severity assessment: Four separate generator invocations for the same grammar with no shared state. The crash-test's `assert source` is strictly weaker than the other three. Consolidation removes redundancy without losing coverage, and reduces fixture duplication for future maintainers.

---

## test-5

- Disposition: Fixed
- Action: Change `>= 2` to `>= 3` in `tests/test_gsm2tree_rs.py:228` and `:231` (`test_allow_non_camel_case_types`, `test_derive_clone_partialeq_eq_hash`).
- Severity assessment: PoC grammar has 3 label-bearing rules (`Identifier`, `Items`, `Trivia`); `>= 2` would silently pass if one enum were dropped in a regression. Correct threshold is `>= 3`; exact `== 3` with a comment is even better but `>= 3` is a correct minimal fix.

---

## test-6

- Disposition: Fixed
- Action: Add parameterized tests for `extend_{label}` and `maybe_{label}` in `tests/test_fegen_rust_cst.py` covering at least one representative fegen class each.
- Severity assessment: PoC tests cover these methods for `Identifier`/`Items`, but fegen classes are separate compiled objects. A generator bug in `_per_label_methods` that affects only `extend_*` or `maybe_*` for fegen classes would not be caught by any existing test. One test per method (not exhaustive over all 14 classes) is sufficient.

---

## test-7

- Disposition: Fixed
- Action: Replace fragile `source.index("\n}", impl_start)` brace-matching with `re.search(r'impl Token \{(.+?)\n\}', source, re.DOTALL)` in `tests/test_gsm2tree_rs.py:400-410`, or assert `Token_Label` is absent from the entire source (already done by `test_zero_label_rule_omits_label_enum`) and drop the impl-block extraction.
- Severity assessment: `\n}` matches the first zero-indented closing brace after `impl Token {`. If the auto-inserted `Trivia` impl block follows `Token` and has a different structure, or if any inner brace sits at column 0, the extraction silently truncates. False-passing risk is real if the generator's output structure ever changes slightly.

---

## reuse-1 / reuse-2 / reuse-3

- Disposition: TODO(extract-rule-name-to-class-name)
- Action: Add TODO comment at `fltk/fegen/gsm2tree_rs.py:15-17` (`_rust_variant_name`) noting the four-site duplication of the `class_name_for_rule_node` transform across `gsm2tree.py`, `gsm2unparser.py` (×2), and `gsm2tree_rs.py`, referencing a future extraction to a shared `rule_name_to_class_name` helper.
- Severity assessment: Four independent definitions of the same underscore-to-CamelCase transform. A behavioral change (e.g., digit handling, consecutive underscores) must be applied in four places manually. The duplication is pre-existing in `gsm2unparser.py` (reuse-2, reuse-3); this phase adds a fourth copy. Extraction is the right fix but touches multiple files and is out of this phase's scope.

---

## quality-1

- Disposition: Fixed
- Action: Remove `class_name: str` parameter from `_generic_append`, `_generic_extend`, `_generic_child` and remove the three `# noqa: ARG002` suppressions; update call sites in `_node_block`. `gsm2tree_rs.py:201,213,234`.
- Severity assessment: Unused parameter suppressed with `noqa` masks intent, misleads future maintainers into thinking the parameter has meaning, and may propagate to new methods. Removing the parameter is a clean 3-line fix.

---

## quality-2

- Disposition: Fixed
- Action: Either delete `FEGEN_RULE_NAMES` constant from `tests/test_gsm2tree_rs.py:298-302` (it is never referenced), or add a test pairing it with `FEGEN_CLASS_NAMES` to verify the name mapping.
- Severity assessment: Dead constant in a new file. Signals an intended test that was omitted; when `class_name_for_rule_node` behavior changes, no test catches the broken mapping. Either add the test or remove the dead constant.

---

## quality-3

- Disposition: TODO(refactor-rule-info-helper)
- Action: Add TODO comment at `gsm2tree_rs.py:50` (`generate()` loop) noting the duplicated `(model, class_name, labels)` derivation between `generate()` and `_register_classes_fn()`; a shared `_rule_info` helper or per-rule namedtuple would eliminate the duplication.
- Severity assessment: Duplicated derivation logic in two loops. If a conditional skip is added to one loop but not the other, emit and registration diverge silently. Low risk currently (the loops are 5 lines apart and obviously parallel), but will grow if a third loop (doc comments, trait impls) is added. Deferred as a refactor; does not affect correctness today.

---

## efficiency-1

- Disposition: TODO(perf-label-identity-comparison)
- Action: Add TODO comment in generated Rust near the `tup.get_item(0)?.eq(&label_obj)?` pattern (template at `gsm2tree_rs.py:289`) noting that identity comparison (`is`) or pre-grouped storage would be O(1) per access vs O(children); defer until profiling need exists.
- Severity assessment: Faithful reproduction of Phase 2 template; not a regression. The O(children) cost is the structural ceiling for label-accessor performance. Not actionable inside the "match Phase 2 exactly" constraint of this phase.

---

## efficiency-2

- Disposition: Won't-Do
- Action: no change
- Severity assessment: Dev-time generator only; no build-time invocation hook. Double-computation across `generate()` and `_register_classes_fn()` is a one-off cost per regeneration. Negligible.
- Rationale (Won't-Do): Reviewer explicitly flagged as not worth fixing. `quality-3` / `TODO(refactor-rule-info-helper)` covers the structural concern. No runtime impact.
