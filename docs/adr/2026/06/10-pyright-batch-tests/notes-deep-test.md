# Test review: pyright-batch-tests (8bee6b0..ff3700b)

## test-1

**File:line** `tests/test_clean_protocol_consumer_api.py:296,914` — `_diags_for_file(…, "shapes_fixture")` and `_diags_for_file(…, "castless_probe")`.

**What's wrong** The `_diags_for_file` helper does substring matching (`if filename in path`). Two unrelated files share a common substring: "shapes_fixture" matches "shapes_fixture.py" uniquely, but "castless_probe" matches any path that contains that literal. More importantly, both the positive batch (`protocol_pyright_diagnostics`) and `fltk/fegen/test_cst_protocol.py`'s negative batch write a file named `castless_probe.py`. The lookup key is just the bare filename without the `.py` suffix in `test_clean_protocol_consumer_api.py:914` (`_diags_for_file(…, "castless_probe")`), which would also match a file named `castless_probe_v2.py` or any path segment containing that string. This is a weak key — not an immediate bug because no such collision exists today, but the negative test for structural mismatch (`test_structural_mismatch_contract_preserved`) depends on it producing errors, so a silent empty-match would cause a false-pass only if the batch produced *no* diagnostics at all for any `castless_probe*` path. The real risk is the positive tests: `_diags_for_file(…, "python_backend_consumer")` matches `python_backend_consumer.py`, which exists in *both* `cst_protocol_pyright_diagnostics` (in `test_cst_protocol.py`) and `protocol_pyright_diagnostics` (in `test_clean_protocol_consumer_api.py`) — no cross-contamination possible since they are different dict objects, but the substring key is fragile against future file additions. No test exercises what happens when `_diags_for_file` returns an empty list for a negative test because the batch silently failed to write or run that file.

**Consequence** If a future file added to the batch has a name that is a substring of an existing filter key (or vice versa), a positive test could silently pass with zero errors that are actually attributable to the wrong file, or a negative test could silently pass with errors from the wrong file. Undetected regression.

**Fix** Use the `.py` suffix consistently in all `_diags_for_file` calls (several calls in `test_clean_protocol_consumer_api.py` omit it: `"shapes_fixture"`, `"castless_probe"`, `"python_backend_consumer"`). Alternatively, filter on `path.endswith(filename)` rather than `filename in path` — absolute paths make endswith-with-basename safe.

---

## test-2

**File:line** `tests/test_clean_protocol_consumer_api.py:905–920` — `test_structural_mismatch_contract_preserved` (negative test).

**What's wrong** This test asserts `errors` is non-empty (good) but has no guard that the batch fixture actually ran pyright (i.e., that `protocol_pyright_diagnostics` is not an empty dict from a partial failure). `_run_pyright_over_dir` returns an empty dict `{}` when pyright produces zero `generalDiagnostics` — which is valid output. If pyright encountered an import error or the `castless_probe.py` file was not found by pyright (e.g., the `pyrightconfig.json` in the tmpdir caused it to exclude the file), the partitioned dict would contain no entry for `castless_probe`, `_diags_for_file` would return `[]`, the `errors` list would be empty, and `assert errors` would **fail** — so at least the test would not silently pass. However, if pyright reported only warnings (not errors) for `castless_probe.py`, `_diags_for_file` returns warnings too, then the `errors = [d for d in diags if d.get("severity") == "error"]` filter would produce `[]`, and `assert errors` would fail correctly. This is fine. The actual concern is narrower: the test has no assertion about *how many* errors are expected (the prior implementation in `fltk/fegen/test_cst_protocol.py:429–432` says "at least one"; the new implementation in `test_clean_protocol_consumer_api.py` says the same implicitly via `assert errors`). Both are correct. **This finding is not a defect** — the negative test correctly fails when errors are absent.

**Consequence** None — marking withdrawn. The assertion is adequate.

**Fix** No action needed. Withdrawing this finding.

---

## test-3

**File:line** `fltk/fegen/test_cst_protocol.py:213–232` — `cst_protocol_pyright_diagnostics` positive batch.

**What's wrong** The positive batch includes `python_backend_consumer.py` and `rust_backend_consumer.py`. Both of these fixtures import `fltk._native` (for the Rust span type). If the native extension is not built, pyright will report import errors for those files. The old per-test implementation also had this property — each file would get its own errors. In the batched version, if pyright reports import errors for one file and not another, the per-file filtering still works correctly. No regression here. However: the batch runs without a `pyrightconfig.json` in its tmpdir (`cwd=str(tmpdir)` is set but no config is written). Pyright will use project-root discovery to find `pyrightconfig.json` — walking up from `tmpdir` through `/tmp/...` until it finds the repo root's config. This works in practice (the report says tests pass), but it is an implicit dependency on repo-root config rather than an explicit one, unlike `test_clean_protocol_consumer_api.py` which writes `pyrightconfig.json` explicitly. If pytest's tmp_path is ever placed outside the repo tree (e.g., in CI with a different tmpfs mount point), pyright would use its defaults (no venv resolution) and every fixture would get import errors, causing false failures on positive tests and false passes on negative tests (since errors would appear from missing imports, not from type mismatches).

**Consequence** In CI environments where `tmp_path_factory.mktemp` returns a path outside the repo tree, all positive batch tests fail and negative batch tests pass vacuously (import errors present but are not the "right" errors — though `assert errors` still passes). Latent portability failure.

**Fix** Write a `pyrightconfig.json` into `tmpdir` in both `cst_protocol_pyright_diagnostics` and `cst_protocol_negative_pyright_diagnostics` (same pattern as `test_clean_protocol_consumer_api.py:159–162`). This makes the venv resolution explicit and independent of the cwd pyright config walk.

---

## test-4

**File:line** `fltk/fegen/test_cst_protocol.py:84–89` and `tests/test_clean_protocol_consumer_api.py:169–174` — `_diags_for_file` helper duplicated verbatim.

**What's wrong** The same helper is copy-pasted into two files with identical semantics. This is a quality issue noted in the spec ("reusing/moving `_run_pyright_over_dir` over inventing a new harness... a plain importable test-util module is also acceptable"). No conftest or shared util was created; instead the helper (and `_run_pyright_over_dir`) is duplicated. This is not a correctness issue for existing tests, but it means a future bug fix or improvement to the matching logic must be applied in multiple places.

**Consequence** Maintenance divergence; a fix to substring-matching behavior (see test-1) applied in one copy is silently missed in the other.

**Fix** Extract `_run_pyright_over_dir` and `_diags_for_file` into a shared test utility module (e.g., `tests/pyright_harness.py` importable from both test files), as the spec allowed. Or at minimum apply the endswith fix from test-1 consistently to both copies at the same time.

---

## test-5

**File:line** `tests/test_gsm2tree_rs.py:1140` — `test_poc_pyi_self_check_zero_errors` assertion.

**What's wrong** The assertion filters only diagnostics with `"poc_cst.pyi"` in path. It does NOT filter by severity — it asserts `pyi_errors == []` where `pyi_errors` is all diagnostics (any severity) for that file. The parallel `test_fegen_pyi_self_check_zero_errors` at line 1129 does the same: no severity filter, asserts the whole list is empty. This is intentional and correct for self-check tests (zero errors AND zero warnings expected). No defect here — documenting for completeness.

**Consequence** None. The behavior is deliberate.

**Fix** No action needed.

---

## Summary of actionable findings

| ID | Actionable | Summary |
|----|-----------|---------|
| test-1 | Yes | Substring key fragility in `_diags_for_file`; use `.py`-suffixed names or `endswith` matching. |
| test-2 | Withdrawn | Negative test assertion is adequate. |
| test-3 | Yes | `cst_protocol_pyright_diagnostics` / negative fixture batch relies on implicit pyright config discovery; write explicit `pyrightconfig.json` into tmpdir. |
| test-4 | Yes | `_run_pyright_over_dir` + `_diags_for_file` duplicated in two files; extract to shared util. |
| test-5 | Withdrawn | Intentional — self-check expects zero diagnostics of any severity. |
