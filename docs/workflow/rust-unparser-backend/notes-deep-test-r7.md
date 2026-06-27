## Test review — batch 7 (trivia/separator processing + PyO3 wrapper)

Commit reviewed: 1fcae0bbe0063b83b1883eb439ababc9da6916d4

---

### test-1

**File:line:** `tests/test_rust_unparser_generator.py` — `test_python_bindings_module_and_pyclass` and related PyO3 tests

**What's wrong:** No test in this batch (or anywhere in the diff) asserts that `"#[pymethods]"` is present in the generated output. The generator emits `lines.append("    #[pymethods]")` at `gsm2unparser_rs.py:1575`, but every PyO3 test that checks for method presence (`test_python_binding_per_rule_method_runs_full_pipeline`, `test_python_binding_one_method_per_rule_with_handle_types`, etc.) only asserts on method signatures and pipeline body lines — not on the attribute that tells pyo3 to expose them. `test_python_bindings_module_and_pyclass` checks for `#[pyclass]` but not `#[pymethods]`.

**Consequence:** If `#[pymethods]` were accidentally dropped or misspelled (e.g., a stray rename), the generated Rust would still compile and all generator tests would still pass. Python callers would get `AttributeError` at runtime because pyo3 would not register any methods on the class. This is exactly the class of silent breakage that generator tests exist to catch.

**Fix:** Add `assert "#[pymethods]" in src` to `test_python_bindings_module_and_pyclass` (or a dedicated test). Also assert `"impl PyUnparser {"` follows it, confirming the impl block opens correctly.

---

### test-2

**File:line:** `tests/test_rust_unparser_generator.py:1934` — `test_python_bindings_module_and_pyclass`

**What's wrong:** The assertion `assert "use super::cst;" in src` (line 1948) passes because the top-level header independently emits `use super::cst;` (no indent) in every generated file. The `mod python_bindings` block needs its own inner `    use super::cst;` (4-space indent), but whether it is present is not tested: the substring `"use super::cst;"` appears inside `"    use super::cst;"` so it would also match via the outer-module occurrence. If the inner module's import were dropped, the test would still pass but the generated code would fail to compile (references to `cst::Py{CN}` inside the module would be unresolved).

**Consequence:** A regression that removes the inner `use super::cst;` from `_gen_python_bindings` is undetected by tests until the generated Rust is compiled.

**Fix:** Tighten the assertion to `assert "    use super::cst;" in src` (4-space indent, matching the module-interior indentation), which cannot be satisfied by the top-level import. Similarly, check the other inner imports: `"    use super::Unparser;"`, `"    use super::{Renderer, RendererConfig, resolve_spacing_specs};"`.

---

### test-3

**File:line:** `tests/test_rust_unparser_generator.py:1735` — `test_gen_trivia_processing_unit_no_ws_and_dispatch`

**What's wrong:** The dispatch assertions `assert gen._gen_trivia_processing("_trivia", "Trivia", gsm.Separator.WS_REQUIRED, "        ")` and `assert gen._gen_trivia_processing("r", "R", gsm.Separator.WS_REQUIRED, "        ")` test truthiness only (non-empty list). Both paths produce output for WS separators, so this is satisfied regardless of which branch was taken. If the `rule.is_trivia_rule` guard were inverted — routing all rules to the trivia-rule branch and none to the non-trivia branch — both assertions would still pass, because each branch returns non-empty for WS. The integration tests do cover the branch-specific shapes, so actual behavior is exercised, but the unit test adds no additional precision.

**Consequence:** The unit test offers false confidence that dispatch was verified. A future regression that routes non-trivia rules into the trivia-rule branch (or vice-versa) would be caught only by the integration tests, not by this targeted unit test.

**Fix:** Assert on branch-identifying text: for the trivia-rule invocation check `any("if let (None, cst::TriviaChild::Span(span))" in line for line in result)`, and for the non-trivia-rule invocation check `any("!acc.last_was_trivia()" in line for line in result)`. These fingerprints are unique to their respective branches.

---

### test-4

**File:line:** `tests/test_rust_unparser_generator.py:1858` — `test_count_newlines_in_trivia_helper_emitted`

**What's wrong:** The test uses a grammar with a single-item (Span-only) synthetic `_trivia`, so `num_child_variants = 1` and the `_ => {}` catch-all is correctly absent. The test verifies this (`assert "_ => {}" not in body`). However, the complementary case — a multi-variant trivia child enum where `_ => {}` must be present — is not tested for `_count_newlines_in_trivia`. The grammar `'doc := a:"x" : b:"y" ; _trivia := ws:/[ ]+/ : comment ; comment := text:/[#][a-z]*/ ;'` (used in `test_has_preservable_trivia_matches_configured_node_types`) gives a multi-variant `TriviaChild`, but `_count_newlines_in_trivia` is not checked in that test.

**Consequence:** If `num_variants > 1` guard was dropped (making catch-all never emitted), the single-variant test would still pass. The generated code for multi-variant trivia would produce a Rust compile error (`non-exhaustive patterns`) only discovered at compile time, not at test time.

**Fix:** Add a test that uses a multi-variant trivia grammar and checks `"_ => {}" in _method_body(src, "_count_newlines_in_trivia")`.

---

### test-5

**File:line:** `tests/test_rust_unparser_generator.py` — separator processing tests generally

**What's wrong:** No test exercises the per-rule spacing override path through `_add_default_separator_spec_lines`. Every trivia/separator test uses a bare `RustUnparserGenerator(parse_grammar(...))` (no `FormatterConfig`) or a `FormatterConfig` with only `trivia_config` set. The `get_spacing_for_separator` method in `fmt_config.py` has a rule-specific branch (`rule_config.ws_required_spacing` / `rule_config.ws_allowed_spacing`) that activates when `rule_configs` has an entry for the rule. This branch is never exercised via the separator processing path in the test suite.

**Consequence:** If `_add_default_separator_spec_lines` passed the wrong `rule_name` to `get_spacing_for_separator` (e.g., a hardcoded string or a class_name instead of rule_name), per-rule spacing overrides would be silently ignored in generated code while all tests continued to pass.

**Fix:** Add a test with a `FormatterConfig(rule_configs={"r": RuleConfig(ws_required_spacing=comb.hardline())})` applied to a WS_REQUIRED grammar and verify the emitted `separator_spec` carries the configured `HardLine` instead of the global default `Line`.
