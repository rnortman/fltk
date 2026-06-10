# Implementation Report: pyright-batch-tests

## Summary

Batched 14 `uv run pyright` subprocesses down to 4, as directed.

## Timing

**Before** (baseline, three-file combined run):
- `fltk/fegen/test_cst_protocol.py` + `tests/test_clean_protocol_consumer_api.py` + `tests/test_gsm2tree_rs.py`: **10.3s wall clock**

**After** (same selection):
- Same three files: **5.9–6.0s wall clock**

Net saving: **~4.3–4.4s** on this machine (all 1042 tests: 14.5s, down from the prior run baseline of ~18s).

## Subprocess count: 14 → 4

| File | Before | After | Batch |
|------|--------|-------|-------|
| `fltk/fegen/test_cst_protocol.py` | 8 | 2 | positive fixtures (6 files) + negative fixtures (2 files) |
| `tests/test_clean_protocol_consumer_api.py` | 4 | 2 | 3 tmp-file tests batched; `test_fltk2gsm_pyright_clean` stays solo (repo-root config) |
| `tests/test_gsm2tree_rs.py` | 2 | 1 | poc_cst.pyi folded into `fegen_pyright_diagnostics` batch (now 4 files in one run) |

## Changes made

### `fltk/fegen/test_cst_protocol.py`
- Replaced per-file `run_pyright()` helper with `_run_pyright_over_dir()` + `_diags_for_file()` helpers.
- Added two module-scoped fixtures:
  - `cst_protocol_pyright_diagnostics`: writes 6 positive fixture files to a shared tmpdir, one run.
  - `cst_protocol_negative_pyright_diagnostics`: writes 2 negative fixture files to a separate shared tmpdir, one run. Separated from positive batch so expected errors in negative fixtures don't appear as noise in positive test filtering.
- Updated all 8 pyright-invoking test functions to consume these fixtures instead of writing and running per-test.
- Removed `tmp_path` and `pyright_available` parameters from the 8 affected tests; they now request only the module-scoped batch fixture.

### `tests/test_clean_protocol_consumer_api.py`
- Added `_run_pyright_over_dir()` helper.
- Added `_REPO_ROOT` path constant.
- Added `_CASTLESS_PROBE_FIXTURE` module-level constant (extracted from inline local in `test_structural_mismatch_contract_preserved`).
- Added module-scoped `protocol_pyright_diagnostics` fixture: writes `shapes_fixture.py`, `castless_probe.py`, `python_backend_consumer.py` + `pyrightconfig.json` (absolute venvPath) to a shared tmpdir, one run.
- Updated `test_shapes_fixture_pyright_clean`, `test_structural_mismatch_contract_preserved`, `test_python_backend_consumer_pyright_clean` to use the shared fixture.
- `test_fltk2gsm_pyright_clean` (line ~362): left as a solo `_run_pyright()` subprocess — runs against the real repo file `fltk/fegen/fltk2gsm.py` using repo-root pyright config; cannot be batched into a tmpdir without copying the file.

### `tests/test_gsm2tree_rs.py`
- Updated `fegen_pyright_diagnostics` fixture to also accept `poc_pyi` and write `poc_cst.pyi` + `poc_cst.py` into the shared tmpdir before the single pyright run. The `pyrightconfig.json` write is idempotent (same content for both calls to `_write_pyi_tmpdir`).
- Updated `test_poc_pyi_self_check_zero_errors` to filter from `fegen_pyright_diagnostics` (keyed on `"poc_cst.pyi"` in path) instead of running a separate subprocess.

### `TODO.md`
- Removed the `## pyright-batch-tests` entry.

## Attribution sanity check

Perturbed `_WRONG_ACCESS_FIXTURE` in `fltk/fegen/test_cst_protocol.py` (replaced the bad `no_such_method()` call with a valid `.span` access, so pyright reports no errors for that file). Result: only `test_wrong_member_access_is_flagged` failed; `test_wrong_label_value_not_flagged` (different fixture file, different batch key) passed unaffected. Attribution is intact.

## Deviations from design

None significant. The design said "If folding [PoC] into `fegen_pyright_diagnostics` is clean ... do that; otherwise leave it." Folding was clean: `poc_pyi` is already a module-scoped fixture in the same module, so adding it as a parameter to `fegen_pyright_diagnostics` is straightforward.

The design said "two batches (positive/negative) is fine" for `test_cst_protocol.py` negative tests. Shipped exactly that: positive batch (6 files) + negative batch (2 files) = 2 subprocesses for that file.

`grep -rn 'pyright-batch-tests'` (excluding `docs/adr/`) returns nothing.
