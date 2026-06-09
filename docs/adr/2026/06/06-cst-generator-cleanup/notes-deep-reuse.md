Concise. Precise. No padding. Audience: smart LLM/human.

Commit reviewed: b72aea624b78136bd1388f304281e2fd9ec8eefb

---

## reuse-1

**File:line:** `tests/test_gsm2tree_py.py:22` vs `tests/test_gsm2tree_rs.py:127`

**What's duplicated:** Both files define a `_make_zero_label_grammar()` function that constructs a single-rule grammar where all included items have no label (`label=None`, `disposition=INCLUDE`). The two copies differ only in incidental details: rule name (`"foo"` vs `"token"`), term type (`Literal("x"/"y")` vs `Regex("[a-z]+")`), and item count (2 vs 1). The semantic intent — a grammar whose only included items are label-free, so the resulting `model.labels` is empty — is identical.

**Existing function:** `tests/test_gsm2tree_rs.py:127` — `_make_zero_label_grammar()`.

**Consequence:** The two copies exercise the same boundary condition (zero-label rule) from different generators (Python vs Rust). If the boundary condition semantics ever need to change (e.g. adding a second rule to force trivia injection, or switching from `Literal` to `Regex` for a future parser constraint), both must be updated independently. The copies are in separate files so there is no mechanical check that they stay aligned; a drift would mean the two generator test suites cover subtly different grammars at the zero-label boundary, masking asymmetries between Python and Rust generator behavior.

---

## reuse-2

**File:line:** `tests/test_gsm2tree_py.py:74` (`_make_generator`) vs `tests/test_gsm2tree_rs.py:454-475` (inline `CstGenerator` construction in `test_rule_name_to_class_name_mapping`)

**What's duplicated:** The pattern `CstGenerator(grammar=..., py_module=pyreg.Builtins, context=create_default_context())` appears in both files. `test_gsm2tree_py.py` extracts this into `_make_generator(grammar)` at line 74-75; `test_gsm2tree_rs.py` inlines it at line 474-475 (with a local import block) without calling the already-extracted helper.

**Existing function:** `tests/test_gsm2tree_py.py:74` — `_make_generator(grammar: gsm.Grammar) -> CstGenerator`.

**Consequence:** `test_gsm2tree_rs.py:474` constructs the generator with the same three arguments that `_make_generator` encapsulates. If `CstGenerator`'s constructor signature changes (e.g. a required context argument is renamed or a new required parameter is added), the inline construction in `test_gsm2tree_rs.py` must be updated separately from `_make_generator`. Currently the duplication is contained to one site in `test_gsm2tree_rs.py`, but it establishes a pattern that will recur if new Python-generator tests are added to that file. The `_make_generator` helper is not importable cross-file (module-private by convention), so there is no shared fixture module to reference; the fix would require either promoting the helper to a shared conftest or duplicating it deliberately.
