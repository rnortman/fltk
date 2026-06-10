# Judge verdict — deep review (pyright-batch-tests)

Note: concise, precise, complete, unambiguous; no padding.

Phase: deep. Base 8bee6b0..HEAD 5f0b7d2 (impl 8a94dde, docstring fix ff3700b, review fixes 5f0b7d2). Round 1.
Notes: 3 reviewer files; 9 findings (2 reviewer-withdrawn). Spec: request.md (same dir).

Verified by execution at HEAD: all 180 tests in the three changed files pass (`uv run pytest`, 5.69s).

## Added TODOs walk

None. Diff 8bee6b0..5f0b7d2 adds no `TODO(` comments in code; all `+TODO` matches are ADR docs. `TODO(pyright-batch-tests)` slug removed from code and `TODO.md`; `grep -rn 'pyright-batch-tests'` over `*.py` and `TODO.md` is clean (request item 6 satisfied).

## Other findings walk

### correctness-1 — Fixed
Claim: batch tmpdirs in `fltk/fegen/test_cst_protocol.py` lacked `pyrightconfig.json`; pyright config silently changed from repo config to none — lost 3.10 pin, latent vacuity of negative tests on import-resolution drift. Consequence real (violates "no changes to what pyright checks" constraint).
Evidence: `write_pyright_config(tmpdir)` called in both `cst_protocol_pyright_diagnostics` (test_cst_protocol.py:186) and `cst_protocol_negative_pyright_diagnostics` (:207). Helper at `tests/pyright_test_utils.py:68-76` writes `{"pythonVersion": "3.10", "venvPath": <repo_root>, "venv": ".venv"}` — identical to the sibling fixtures' config; `_REPO_ROOT = tests/..` resolves correctly.
Assessment: fix addresses both consequences (pin restored, venv resolution explicit). Accept.

### correctness-2 — Fixed
Claim: check-context (`pyright_available` probes `uv run pyright --version` from repo root) vs run-context (`uv run pyright` with `cwd=tmpdir`) mismatch; without `VIRTUAL_ENV`, 11 tests hard-fail with misleading "non-JSON output" instead of skipping.
Evidence: shared `_run_pyright_over_dir` (`tests/pyright_test_utils.py:38-44`) invokes `["uv", "run", "--project", str(_REPO_ROOT), "pyright", "--outputjson", str(tmpdir)]` with `cwd=str(tmpdir)` — exactly the reviewer's suggested fix. Probed: `env -u VIRTUAL_ENV PATH=/usr/bin:/bin uv run --project <repo> pyright --version` from /tmp resolves pyright (1.1.402). Bonus: `tests/test_gsm2tree_rs.py` now imports the shared helper, so the pre-existing 3-test exposure the reviewer flagged as optional is also fixed.
Assessment: deterministic env resolution; cwd preserved for tmpdir config pickup. Accept.

### test-1 — Fixed
Claim: bare-stem substring keys in `_diags_for_file` (`"shapes_fixture"`, `"castless_probe"`, `"python_backend_consumer"`) fragile against future name collisions; vacuous pass risk.
Evidence: all 11 `_diags_for_file` call sites across both files now pass `.py`-suffixed names (grep confirms: test_clean_protocol_consumer_api.py:252,869,946; test_cst_protocol.py 8 sites already suffixed). Shared helper docstring documents the full-filename convention.
Assessment: matches the reviewer's primary fix. Accept.

### test-2 — Won't-Do
Reviewer explicitly withdrew ("This finding is not a defect... Withdrawing"). Verified: `test_structural_mismatch_contract_preserved` asserts non-empty errors and fails loudly on empty.
Assessment: Won't-Do correct. Accept.

### test-3 — Fixed
Same substance as correctness-1 (missing tmpdir `pyrightconfig.json` → implicit config-walk dependency). Resolved by the same `write_pyright_config()` calls; dedup to correctness-1 is accurate.
Assessment: Accept.

### test-4 — Fixed
Claim: `_run_pyright_over_dir` + `_diags_for_file` duplicated across files; spec allowed a shared test-util module.
Evidence: new `tests/pyright_test_utils.py`; all three local copies deleted (diff ff3700b..5f0b7d2 shows removals in all three files); all three test files import from it. Import path works in practice (180 tests pass; `tests.gsm2tree_helpers` import precedent already existed).
Assessment: Accept.

### test-5 — Won't-Do
Reviewer marked intentional/no-action. Minor factual wrinkle in the original finding (the incumbent gsm2tree_rs helper already pre-filtered to errors-only, so "any severity" was wrong), but the conclusion — no defect — holds either way.
Assessment: Won't-Do correct. Accept.

### quality-1 — Fixed
Same substance as test-4 plus the severity-contract divergence. Evidence: shared helper settles on errors-only pre-filtering (pyright_test_utils.py:50-51, matching the gsm2tree_rs incumbent as the reviewer recommended); the 9 callers in test_cst_protocol.py and the 3 in test_clean_protocol_consumer_api.py dropped their redundant `severity == "error"` filters (diff confirms each site); docstring states the contract once.
Assessment: duplication and contract drift both eliminated. Accept.

### quality-2 — Fixed
Same substance as test-1 (key-convention inconsistency). The reviewer's secondary "consider a loud-failure guard inside `_diags_for_file`" suggestion was not taken; it was phrased as optional ("Consider"), and the primary fix (normalize to full filenames) was applied everywhere. Not a basis for rework.
Assessment: Accept.

## Disputed items

None.

## Approved

9 findings: 7 Fixed verified (3 of which dedupe to 4 distinct fixes), 2 Won't-Do sound (both reviewer-withdrawn).

---

## Verdict: APPROVED

All dispositions acceptable; every Fixed claim verified against the diff and by execution; both Won't-Dos backed by reviewer withdrawal. Commit 5f0b7d2.
