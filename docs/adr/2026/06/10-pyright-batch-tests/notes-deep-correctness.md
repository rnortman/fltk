# Deep correctness review — pyright-batch-tests

Commit reviewed: ff3700b (base 8bee6b0). Files: `fltk/fegen/test_cst_protocol.py`, `tests/test_clean_protocol_consumer_api.py`, `tests/test_gsm2tree_rs.py`, `TODO.md`.

Verified by execution: all 180 tests in the three files pass (`uv run pytest`, 5.76s). Verified by probe: pyright over a directory DOES analyze an un-imported `.pyi` (wrote a deliberately broken `poc_cst.pyi` into a replica tmpdir; both errors reported against it) — the folded `test_poc_pyi_self_check_zero_errors` is not vacuous. Substring keys in `_diags_for_file` were checked pairwise across each batch; no filename is a substring of another within any batch, so attribution filtering is sound.

## correctness-1 — `test_cst_protocol.py` batch tmpdirs have no `pyrightconfig.json`; pyright config silently changed from repo config to none

`fltk/fegen/test_cst_protocol.py:225-232` (`cst_protocol_pyright_diagnostics`) and `:245-248` (`cst_protocol_negative_pyright_diagnostics`).

What's wrong: both fixtures write only fixture `.py` files into the tmpdir and run pyright with `cwd=tmpdir` (`:71`). No `pyrightconfig.json` is written. The other two batch fixtures in this change write one (`tests/test_clean_protocol_consumer_api.py:160-162`, `tests/test_gsm2tree_rs.py:1078-1080` via `_write_pyi_tmpdir`); this module is the odd one out.

Why it matters: the old `run_pyright` ran with inherited cwd = repo root, so every run was governed by `pyproject.toml [tool.pyright]` (`pythonVersion = "3.10"`, `venvPath = ".venv"`, `stubPath = ""`). The new runs are governed by no config at all: `fltk.*` import resolution now works only because the pytest process (launched via `uv run pytest`) exports `VIRTUAL_ENV`/`PATH` and pyright falls back to the python found there, and `pythonVersion` floats with whatever interpreter pyright finds instead of the 3.10 pin. Probed empirically: with the venv env inherited, the config-less tmpdir run resolves `fltk` and flags `no_such_method` (current behavior is correct); the venv is currently Python 3.10.20, so the lost pin has no visible effect today.

Consequence:
- Violates the request constraint "No changes to what pyright checks — only how many times it launches" (request.md, Constraints).
- Latent vacuity of the negative tests: if import resolution degrades (venv interpreter bumped past 3.10, different/absent `VIRTUAL_ENV`, IDE test runner), `wrong_access_fixture.py` and `castless_probe.py` produce `reportMissingImports` errors instead of the intended diagnostics — `test_wrong_member_access_is_flagged` and `test_boundary_probe_documents_label_mismatch` keep passing on the wrong errors (they only assert non-empty). The contract they guard (attribute flagging; the `_DEFAULT_CST` cast being required) would go unverified, masked behind green tests. The positive batch would fail loudly, but it is a separate pyright run over a separate dir, so the negative batch's degradation is not self-evident.
- Lost `pythonVersion = "3.10"` pin: when the dev venv moves to a newer interpreter, these fixtures get checked under newer-version semantics while the repo (and out-of-tree consumers per CLAUDE.md) target a 3.10 floor — silent drift from what the in-repo gate checks.

Fix: write the same config the sibling fixtures write into both tmpdirs:
`(tmpdir / "pyrightconfig.json").write_text(json.dumps({"pythonVersion": "3.10", "venvPath": str(pathlib.Path(__file__).parents[2]), "venv": ".venv"}))`.

## correctness-2 — check-context vs run-context mismatch: `uv run pyright` probed at repo root but executed from /tmp; hard FAIL (not skip) when pytest isn't launched via `uv run`

`fltk/fegen/test_cst_protocol.py:65-72` and `tests/test_clean_protocol_consumer_api.py:122-129` (new `_run_pyright_over_dir` helpers, `cwd=str(tmpdir)`), vs. `pyright_available` (`test_cst_protocol.py:37-49`, `test_clean_protocol_consumer_api.py:76-88`) which runs `uv run pyright --version` with no cwd (inherits repo root).

What's wrong: `uv run` resolves its environment from the cwd's project, falling back to `VIRTUAL_ENV`. From the repo root it always finds the project, so `pyright_available` returns True. From a pytest tmpdir under /tmp there is no project; resolution depends entirely on an exported `VIRTUAL_ENV`. Probed empirically: with `VIRTUAL_ENV` unset and `.venv/bin` off PATH, `uv run pyright --outputjson <tmpdir>` from the tmpdir fails with `error: Failed to spawn: pyright`, stdout empty — which the helpers turn into `pytest.fail("pyright produced non-JSON output: ")`, not a skip.

Why it's a regression: the replaced per-file helpers (`run_pyright`, `_run_pyright` for the three tmp-file tests) passed no `cwd`, so they executed from the repo root and worked even when pytest was invoked directly (`.venv/bin/pytest`, IDE runners) without uv's exported env. After this change, that invocation mode hard-fails 9 newly-batched call paths (8 in `test_cst_protocol.py`, 3 tests sharing 1 run in `test_clean_protocol_consumer_api.py`) that previously passed. The check (`pyright_available` at repo root) and the act (run from tmpdir) probe different environments — check-then-act mismatch.

Consequence: under `pytest` invoked without `uv run`, 11 tests flip from pass to error/fail with a misleading "non-JSON output" message; the `pyright_available` skip mechanism the request said to preserve no longer reflects whether the actual run can launch. (Pre-existing exposure: `tests/test_gsm2tree_rs.py` helpers already used `cwd=tmpdir`; this change extends the exposure from 3 tests to 14.)

Fix: invoke as `["uv", "run", "--project", str(_REPO_ROOT), "pyright", "--outputjson", str(tmpdir)]` while keeping `cwd=tmpdir` (cwd is what makes pyright pick up the tmpdir `pyrightconfig.json`; `--project` makes uv's environment resolution deterministic and matches the probe context). Applies to both new helpers and, optionally, the pre-existing ones in `test_gsm2tree_rs.py`.

## Checked and clean

- Attribution filtering: per-batch filename sets have no substring collisions (`python_backend_consumer.py` vs `python_backend_uncasted_callsite.py` are not substrings of each other; `poc_cst.pyi` does not match `poc_cst.py` paths). Negative tests filter to their own file, as the request requires.
- PoC fold (`tests/test_gsm2tree_rs.py:1107-1112`): `poc_pyi` is module-scoped, so the module-scoped fixture dependency is scope-legal; double `_write_pyi_tmpdir` writes byte-identical `pyrightconfig.json` (constant content) — idempotent as claimed; un-imported `.pyi` is analyzed by a dir-level pyright run (probed).
- Severity handling: the two new helpers return all severities and every caller filters `severity == "error"`; net assertions identical to the old error-only helpers. (The `test_gsm2tree_rs.py` original filters to errors inside the helper — a divergence in helper contract across the three copies, but each is used consistently.)
- Skip semantics: module-scoped batch fixtures call `pytest.skip` via the helper when pyright is unavailable; pytest propagates fixture skips to all dependent tests — equivalent to the old per-test skips (within the env caveat of correctness-2).
- Mixing the negative `castless_probe.py` into the positive batch in `test_clean_protocol_consumer_api.py` is safe: no cross-file imports, per-file filtering isolates its expected errors; the request's item 2 explicitly directed batching those three.
- `test_fltk2gsm_pyright_clean` correctly left on the solo repo-config `_run_pyright` path.
- `TODO.md` entry removed; `grep -rn 'pyright-batch-tests'` outside `docs/adr/` is clean.

Minor (doc-only, no behavior): `fltk/fegen/test_cst_protocol.py:57-59` docstring says "return errors partitioned" then "(all severities, not just errors)" — first line is stale copy from the gsm2tree_rs original.
