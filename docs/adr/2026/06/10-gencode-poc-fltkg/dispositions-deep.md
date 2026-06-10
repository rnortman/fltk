# Dispositions — gencode-poc-fltkg deep review (commit 815c95f → 8e599f4)

## correctness-1

- Disposition: Fixed
- Action: Replaced inline fixture body with `_parse_grammar_raw(fltkg_path)` at `tests/test_gsm2tree_rs.py:1181-1183`. That function delegates to `_read_and_parse_grammar`, which asserts `result.pos == len(terminals.terminals)` at `genparser.py:50` and exits with a structured error on partial parse. The fixture no longer duplicates the pipeline.
- Severity assessment: The missing full-parse check would have caused the drift-guard to report false green for any perturbation that appended unparsable content after a valid rule, contradicting the spec's verification criterion. Not a current regression (the grammar is correct), but a structural gap in the guard.

## correctness-2

- Disposition: Fixed
- Action: Added `assert fltkg_alt.initial_sep == expected_alt.initial_sep` to the parameterized `test_rule_items` at `tests/test_gsm2tree_rs.py:1200`. Both the `identifier` and `items` rules are now covered.
- Severity assessment: A divergence in `initial_sep` between the `.fltkg` file and `_make_poc_grammar()` would have passed the drift-guard silently. No current output impact (the Rust generator does not consume `initial_sep`), but the guard's stated purpose is to catch GSM-level divergence before it matters.

## test-1

- Disposition: Fixed
- Action: Same fix as correctness-2 — `initial_sep` assertion added in `test_rule_items`. Covered by both the `identifier` and `items` parametrize cases.
- Severity assessment: Same as correctness-2: future grammar edits that introduce leading separators would silently diverge.

## test-2

- Disposition: Fixed
- Action: The two duplicate per-rule test methods (`test_identifier_rule_items`, `test_items_rule_items`) were replaced with a single `@pytest.mark.parametrize("rule_name", ["identifier", "items"])` test at `tests/test_gsm2tree_rs.py:1192-1206`. The suggestion to use whole-Grammar `__eq__` was evaluated and rejected: `Grammar.rules` is a `list` in the parsed path and a `tuple` in `_make_poc_grammar()`, so dataclass `__eq__` returns False despite identical contents. The parametrized explicit-field approach is correct and eliminates the duplication.
- Severity assessment: No correctness regression — purely a maintainability issue. Adding a new rule to the grammar would have required a third copy-pasted method; the parametrized form extends naturally.

## test-3

- Disposition: Fixed
- Action: Same fix as correctness-1 — fixture now calls `_parse_grammar_raw` directly (`tests/test_gsm2tree_rs.py:1181-1183`).
- Severity assessment: If `_read_and_parse_grammar` gains a pre-processing step, the old inline reimplementation would silently diverge from the real pipeline, providing false confidence.

## quality-1

- Disposition: Fixed
- Action: Same fix as test-3 / correctness-1 — inline reimplementation replaced with `_parse_grammar_raw`. The import of `fltk2gsm`, `fltk_parser`, and `terminalsrc` is removed; only `_parse_grammar_raw` is imported.
- Severity assessment: Duplicate pipeline logic creates a maintenance burden and omits the position check; both issues are resolved.

## quality-2

- Disposition: Fixed
- Action: Same fix as test-2 — two copy-paste methods collapsed into one parameterized test.
- Severity assessment: Maintainability: bug fixes and new assertions applied in one place instead of two.
