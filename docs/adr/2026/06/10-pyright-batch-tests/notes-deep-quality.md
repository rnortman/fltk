# Quality Notes: pyright-batch-tests

Commit reviewed: ff3700b

---

## quality-1

**File:line**: `fltk/fegen/test_cst_protocol.py:52–89`, `tests/test_clean_protocol_consumer_api.py:109–174`, `tests/test_gsm2tree_rs.py:1033–1063`

**Issue**: `_run_pyright_over_dir` and `_diags_for_file` are copy-pasted across all three changed files with slight variation. The design spec explicitly anticipated a shared conftest.py or importable test-util module and left that choice to the implementer (request.md §Direction item 5). Instead, identical helpers were duplicated in all three files — three definitions of `_run_pyright_over_dir`, two of `_diags_for_file`.

The copies are not equivalent: `tests/test_gsm2tree_rs.py:1059` pre-filters on `severity == "error"` inside the partitioning loop (so callers get only errors), while the two new copies in `test_cst_protocol.py` and `test_clean_protocol_consumer_api.py` include all severities and require callers to filter. This is exactly the "slight variation" pattern that copy-paste with drift produces. The divergence is currently benign (callers in the new files do filter by severity), but means any future fix or behavioral change to `_run_pyright_over_dir` must be applied to three places, with per-copy judgment about whether the severity-filter placement should change.

**Consequence**: Every future change to the pyright invocation pattern (e.g., adding `--pythonversion`, changing timeout, adjusting partitioning) requires three edits with three opportunities to re-diverge. The severity-filter inconsistency is a latent defect that will confuse the next reader: the docstrings disagree (`test_gsm2tree_rs.py` says "error diagnostics"; the new copies say "all severities"), and callers rely on different contracts. This will propagate: the next batched pyright helper written in a new test file will have a fourth copy to choose from.

**Fix**: Extract `_run_pyright_over_dir` and `_diags_for_file` into a shared module — either `tests/pyright_test_utils.py` (importable from any test file that can reach `tests/`) or a `conftest.py` at the `tests/` level. Decide on the severity-filter contract once (filtering in the partitioner is slightly cleaner since callers don't repeat the `severity == "error"` guard) and apply it consistently. Remove the three local copies. The `test_gsm2tree_rs.py` copy is the incumbent; the other two should be replaced with imports from the shared module.

---

## quality-2

**File:line**: `tests/test_clean_protocol_consumer_api.py:296` — `_diags_for_file(protocol_pyright_diagnostics, "shapes_fixture")` (no `.py` extension); compare `fltk/fegen/test_cst_protocol.py:375` — `_diags_for_file(..., "wrong_label_value_fixture.py")` (with extension).

**Issue**: The filename key passed to `_diags_for_file` is inconsistent between the two new call sites: `test_clean_protocol_consumer_api.py` uses bare stem names (e.g., `"shapes_fixture"`, `"castless_probe"`, `"python_backend_consumer"`) while `test_cst_protocol.py` uses full filenames with `.py` extension. Both happen to work because `_diags_for_file` does substring matching on the absolute path — `"shapes_fixture"` is a substring of both `shapes_fixture.py` and any path containing `shapes_fixture`. But the inconsistency is a stringly-typed API with no guardrail: a caller passing `"shapes_fixtur"` would silently return empty results (no match, no error), making a zero-error assertion vacuously true and masking a broken test.

**Consequence**: A future caller can copy either convention and get the other one wrong. A typo in the filename key silently produces an empty list; positive tests then assert `errors == []` on empty input and pass vacuously, providing zero coverage while appearing green. This is especially dangerous for positive (zero-error) tests where vacuous success is indistinguishable from real success.

**Fix**: Normalise all `_diags_for_file` call sites to use full filenames (with extension). Consider adding a guard inside `_diags_for_file` that asserts `any(filename in path for path in partitioned)` and raises a `KeyError`/`AssertionError` when no path matches — so a mistyped key fails loudly instead of returning silently empty results.
