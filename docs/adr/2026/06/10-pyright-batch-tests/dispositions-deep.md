# Dispositions: pyright-batch-tests deep review

Commit reviewed: ff3700b. Fixes committed at: 5f0b7d2.

---

correctness-1:
- Disposition: Fixed
- Action: `write_pyright_config()` called in both `cst_protocol_pyright_diagnostics` and `cst_protocol_negative_pyright_diagnostics` fixtures (fltk/fegen/test_cst_protocol.py:185,200). The helper writes `{"pythonVersion": "3.10", "venvPath": <repo_root>, "venv": ".venv"}` to the tmpdir, matching the sibling fixtures.
- Severity assessment: Real correctness gap. Without a pyrightconfig.json, pythonVersion floated with the interpreter pyright discovered; negative tests could silently pass on import errors instead of the intended type errors if venv resolution degraded.

correctness-2:
- Disposition: Fixed
- Action: Shared `_run_pyright_over_dir` in `tests/pyright_test_utils.py` uses `["uv", "run", "--project", str(_REPO_ROOT), "pyright", "--outputjson", str(tmpdir)]` with `cwd=str(tmpdir)`. The `--project` flag makes uv's venv resolution deterministic (reads from project at repo root) regardless of where tmpdir is on disk; cwd ensures pyright picks up the tmpdir's pyrightconfig.json.
- Severity assessment: Real regression under non-uv invocation paths. The check (`pyright_available` at repo root) and act (run from tmpdir) probed different environments; without VIRTUAL_ENV exported, 11 tests would hard-fail with a misleading "non-JSON output" message rather than skipping.

test-1:
- Disposition: Fixed
- Action: All three `_diags_for_file` call sites in `tests/test_clean_protocol_consumer_api.py` updated to pass full filenames with `.py` extension: `"shapes_fixture.py"` (line 253), `"castless_probe.py"` (line 871), `"python_backend_consumer.py"` (line 949). `fltk/fegen/test_cst_protocol.py` already used `.py`-suffixed names throughout.
- Severity assessment: Fragile substring keys could silently return wrong diagnostics if a future file's name contains an existing key as a substring. Positive (zero-error) tests would pass vacuously. Low immediate risk but high maintenance hazard.

test-2:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: Reviewer withdrew this finding. The negative test's assertion is correct — it fails loudly when errors are absent, not silently.
- Rationale (Won't-Do): Finding explicitly marked withdrawn by reviewer; no defect exists.

test-3:
- Disposition: Fixed
- Action: Same as correctness-1 — the two findings are identical in substance. Both resolved by `write_pyright_config()` in the positive and negative batch fixtures.
- Severity assessment: See correctness-1.

test-4:
- Disposition: Fixed
- Action: Extracted `_run_pyright_over_dir` and `_diags_for_file` into `tests/pyright_test_utils.py` (new file). All three test files now import from there; local copies removed. Contract settled on errors-only pre-filtering (matching the `test_gsm2tree_rs.py` incumbent); callers in the other two files had their redundant `severity == "error"` filter removed.
- Severity assessment: Maintenance divergence was already present (severity-filter placement differed across the three copies). Leaving three copies would propagate the discrepancy to every future batch test. Extraction eliminates the drift surface.

test-5:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: Reviewer notes behavior is deliberate — self-check tests assert zero diagnostics of any severity. No defect.
- Rationale (Won't-Do): Finding explicitly noted as intentional by reviewer; the absence of a severity filter is the correct contract for self-check tests.

quality-1:
- Disposition: Fixed
- Action: Same as test-4. See above.
- Severity assessment: Three diverging copies with different severity-filter contracts. Extraction to `tests/pyright_test_utils.py` resolves both the duplication and the contract inconsistency.

quality-2:
- Disposition: Fixed
- Action: Same as test-1. See above.
- Severity assessment: Inconsistent key convention (bare stem vs `.py`-suffixed) with no guardrail; a typo in a key silently returns empty results, making zero-error assertions vacuously true.
