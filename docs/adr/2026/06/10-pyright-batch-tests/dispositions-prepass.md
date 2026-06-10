slop-1:
- Disposition: Fixed
- Action: Updated `_run_pyright_over_dir` docstring in `tests/test_clean_protocol_consumer_api.py:118-122` to say "all diagnostics (warnings + errors); callers filter by severity", matching the `test_cst_protocol.py` version.
- Severity assessment: Contradictory docstrings between the two copies of the same helper would mislead maintainers into skipping the severity filter in new tests, silently accepting warnings as clean.

slop-2:
- Disposition: Fixed
- Action: Added `_diags_for_file` helper at `tests/test_clean_protocol_consumer_api.py:169-174`; replaced the three inline two-step patterns at lines 293, 911, 989 with calls to the new helper.
- Severity assessment: Three inlined copies of the same pattern with no extractor creates latent divergence when the filtering logic changes; the inconsistency with `test_cst_protocol.py` (which already had the helper) compounds the maintenance burden.

slop-3:
- Disposition: Fixed
- Action: Replaced self-explanatory docstring on `_diags_for_file` in `fltk/fegen/test_cst_protocol.py:85-87` with a note on the non-obvious: substring matching against pyright's absolute paths, and why bare filenames work for tmpdir files.
- Severity assessment: The original docstring added no information beyond the function name; the replaced version captures the non-obvious invariant that a future reader would need to know when adapting or debugging the helper.

slop-4:
- Disposition: Fixed
- Action: Removed "Used only for the real-repo-file test (test_fltk2gsm_pyright_clean), which must run against the repo-root pyright config and cannot be batched into a tmpdir." from `_run_pyright` docstring at `tests/test_clean_protocol_consumer_api.py:92`. Left the one-line summary.
- Severity assessment: Caller-reference comments in helper docstrings become silently wrong when a second caller is added; the constraint belongs at the call site, not the helper.
