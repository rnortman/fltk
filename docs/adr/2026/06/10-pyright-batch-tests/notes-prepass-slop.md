slop-1. `tests/test_clean_protocol_consumer_api.py:553-556`
Quote: `"""Run pyright --outputjson over a directory; return errors partitioned by file path.\n\n    Returns a dict mapping each file's absolute path string to its list of error diagnostics.`
What's wrong: Docstring says "list of error diagnostics" but the function returns ALL diagnostics (all severities); callers do their own `d.get("severity") == "error"` filter. The parallel implementation in `fltk/fegen/test_cst_protocol.py:279` correctly says "all severities, not just errors — callers filter by severity." The two copies of the same helper have contradictory docstrings about what they return.
Consequence: A maintainer reading only this file's `_run_pyright_over_dir` will think the output is pre-filtered to errors and either skip the severity filter (accepting warnings as clean) or not know to add it in a new test.
Fix: Update `test_clean_protocol_consumer_api.py:555` to match `test_cst_protocol.py`: "Returns a dict mapping each file's absolute path string to its list of all diagnostics (warnings + errors); callers filter by severity."

slop-2. `tests/test_clean_protocol_consumer_api.py:622, 665-666, 684-687`
Quote: `diags = [d for path, errs in protocol_pyright_diagnostics.items() if "shapes_fixture" in path for d in errs]` / `errors = [d for d in diags if d.get("severity") == "error"]`
What's wrong: Three call sites in `test_clean_protocol_consumer_api.py` inline an identical two-step pattern (path-substring filter → severity filter) directly in the test body. `fltk/fegen/test_cst_protocol.py` extracted this into `_diags_for_file(partitioned, filename)` + separate severity filter. The `test_clean_protocol_consumer_api.py` file duplicates the pattern three times without extracting a helper, producing inconsistent style between the two files added in the same diff.
Consequence: If the filtering logic changes (e.g., key on absolute path rather than substring match, or filter severities upstream), it must be updated at three inline sites in one file and one helper in another — latent divergence between two files that implement the same pattern differently.
Fix: Add `_diags_for_file` to `test_clean_protocol_consumer_api.py` (or import from a shared conftest) and use it at all three call sites, mirroring the pattern in `test_cst_protocol.py`.

slop-3. `fltk/fegen/test_cst_protocol.py:313-314`
Quote: `def _diags_for_file(partitioned: dict[str, list[dict[str, Any]]], filename: str) -> list[dict[str, Any]]:\n    """Return all diagnostics whose file path contains filename."""`
What's wrong: Self-explanatory docstring restates the function name and parameters in English with zero added information.
Consequence: Reads as LLM-generated filler. The non-obvious detail worth documenting (that pyright returns absolute paths so bare filenames work as substrings for files in a tmpdir) is omitted entirely.
Fix: Replace with a note on the non-obvious: "Matches by substring against pyright's absolute file paths; bare filenames work for files written into a tmpdir."

slop-4. `tests/test_clean_protocol_consumer_api.py:536-540`
Quote: `"""Run pyright --outputjson on file_path; return list of error diagnostics.\n\n    Used only for the real-repo-file test (test_fltk2gsm_pyright_clean), which must run\n    against the repo-root pyright config and cannot be batched into a tmpdir.\n    """`
What's wrong: "Used only for the real-repo-file test (test_fltk2gsm_pyright_clean)" is a caller-reference comment in a helper's docstring. It documents the current call graph, not what the function does. If a second non-batchable test is added and also calls `_run_pyright`, the comment becomes silently wrong.
Consequence: Couples helper documentation to the call graph; misleads future authors who add a second caller.
Fix: Remove the "Used only for..." sentence. The constraint (repo-root config, not batchable) belongs in `test_fltk2gsm_pyright_clean`'s own docstring, not the helper.
