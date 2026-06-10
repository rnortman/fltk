# Exploration: pyright-batch-tests TODO adversarial verification

Concise. Token-dense. No fluff. Audience: maintainer deciding whether to act on this TODO.

---

## Actual pyright subprocess count (ground truth)

Three files in the codebase invoke `uv run pyright` as subprocesses. Total: **14 invocations** per full test run.

### `fltk/fegen/test_cst_protocol.py` — 8 invocations

`run_pyright()` defined at line 52; called at:

| Line | Test | Expects |
|------|------|---------|
| 315 | `test_wrong_label_value_not_flagged` | 0 errors |
| 331 | `test_member_access_fixture_zero_errors` | 0 errors |
| 343 | `test_wrong_member_access_is_flagged` | ERRORS (negative) |
| 375 | `test_boundary_probe_documents_label_mismatch` | ERRORS (negative) |
| 437 | `test_protocol_is_not_dataclass_specific` | 0 errors |
| 550 | `test_python_backend_consumer_still_type_checks` | 0 errors |
| 568 | `test_rust_backend_span_satisfies_widened_protocol` | 0 errors |
| 614 | `test_python_backend_uncasted_callsite_annotation_churn` | 0 errors |

All 8 tests are not parameterized. Each uses `tmp_path` (function-scoped). No batching exists in this file.

### `tests/test_clean_protocol_consumer_api.py` — 4 invocations

`_run_pyright()` defined at line 91; called at:

| Line | Test | Target | Expects |
|------|------|--------|---------|
| 231 | `test_shapes_fixture_pyright_clean` | tmp `shapes_fixture.py` | 0 errors |
| 300 | `test_fltk2gsm_pyright_clean` | real `FLTK2GSM_PATH` | 0 errors |
| 850 | `test_structural_mismatch_contract_preserved` | tmp `castless_probe.py` | ERRORS (negative) |
| 930 | `test_python_backend_consumer_pyright_clean` | tmp `python_backend_consumer.py` | 0 errors |

`pyright_available` fixture: `scope="session"` at line 76.  
No cwd is passed to `subprocess.run`; process cwd (repo root) is used. The repo-level `pyproject.toml` provides the pyright config for calls against real repo files (`FLTK2GSM_PATH`).

### `tests/test_gsm2tree_rs.py` — 2 invocations

Two helper functions exist: `_run_pyright_in_tmpdir` (line 990, per-file) and `_run_pyright_over_dir` (line 1019, per-dir).

| Line | Site | Covers |
|------|------|--------|
| 1095 | `fegen_pyright_diagnostics` fixture (scope=module) via `_run_pyright_over_dir` | 3 tests: `test_fegen_pyi_self_check_zero_errors`, `test_fegen_whole_module_no_cast_zero_errors`, `test_fegen_per_class_no_cast_zero_errors` |
| 1123 | `test_poc_pyi_self_check_zero_errors` via `_run_pyright_in_tmpdir` | 1 test |

`pyright_available` fixture: `scope="session"` at line 975. This is a duplicate session fixture from the one in `test_clean_protocol_consumer_api.py`; pytest treats them as separate because there is no `conftest.py`.

---

## Timing measurements (this machine)

`uv run pyright --version` cold start: **~0.39s wall clock**.

`uv run pyright --outputjson <file>` on a small fixture file with fltk venv imports: **~0.6s wall clock / ~0.3s pyright internal**.

`uv run pyright --outputjson <dir>` (3–4 files, one pyright invocation): **~0.6s wall clock / ~0.29s pyright internal** — same cost as a single file invocation; pyright does not add substantial per-file cost within one run.

Measured total wall time for all 14 pyright-invoking tests (17 tests selected, some non-pyright): **10.47s** for the combined `fltk/fegen/test_cst_protocol.py` + `tests/test_clean_protocol_consumer_api.py` + `tests/test_gsm2tree_rs.py` run. At ~0.6s per subprocess, 14 subprocesses = ~8.4s attributable to pyright startup overhead. The remaining ~2s is test collection + fegen_generator fixture setup.

Individual test runs for reference:
- `TestGeneratePyiSelfCheck` + `TestGeneratePyiConformance` (4 tests, 1 batched pyright dir + 1 file pyright): **1.58s** wall.
- `test_clean_protocol_consumer_api.py -k pyright` (3 tests, 3 subprocesses): **2.19s** wall.
- `test_structural_mismatch_contract_preserved` (1 test, 1 subprocess): **1.79s** wall.
- `fltk/fegen/test_cst_protocol.py` (12 tests, 8 subprocesses): **5.28s** wall.

---

## TODO accuracy check

The TODO text states three things. Evaluated against the actual code:

**Claim 1**: `test_poc_pyi_self_check_zero_errors` runs a separate `uv run pyright` subprocess.  
**Verdict: TRUE.** `tests/test_gsm2tree_rs.py:1123` calls `_run_pyright_in_tmpdir` directly; this is not batched into `fegen_pyright_diagnostics`.

**Claim 2**: `test_poc_per_class_no_cast_zero_errors` runs a separate `uv run pyright` subprocess.  
**Verdict: FALSE — this test does not exist.** Exhaustive search of `tests/test_gsm2tree_rs.py` finds no such test name. The fegen per-class test (`test_fegen_per_class_no_cast_zero_errors` at line 1187) is already batched into `fegen_pyright_diagnostics`. There is no PoC per-class conformance test.

**Claim 3**: "stub B4 tests in `tests/test_fltk_native_stub.py` call pyright via `test_cst_protocol.py` call sites."  
**Verdict: FALSE on both counts.**
- `tests/test_fltk_native_stub.py` contains zero `subprocess` or pyright invocations (201 lines, no import of subprocess).
- `tests/test_cst_protocol.py` does not exist at that path. The file is `fltk/fegen/test_cst_protocol.py` (a different location). `test_fltk_native_stub.py` does not import from it.
- `fltk/fegen/test_cst_protocol.py` does contain 8 pyright subprocess calls, but they are entirely independent of `test_fltk_native_stub.py`.

The TODO's description of the remaining work is substantially wrong about claims 2 and 3.

---

## Consolidation feasibility

### What the TODO proposes
"Shared session-scoped tmpdir across both test modules."

### Actual constraint analysis

**`tests/test_gsm2tree_rs.py` — PoC self-check** (`test_poc_pyi_self_check_zero_errors`, line 1115):  
Writes a `poc_cst.pyi` + empty `poc_cst.py` + `pyrightconfig.json` to `tmp_path`. The pyi content comes from `poc_pyi` (module-scoped fixture, line 746) which generates the stub from a 2-rule grammar. To batch this with `fegen_pyright_diagnostics`, the poc pyi would need to be written into the same tmpdir before `fegen_pyright_diagnostics` runs. The issue: `fegen_pyright_diagnostics` is `scope=module` while `poc_pyi` is also `scope=module` in the same module. Promotion to `scope=session` and a shared conftest.py fixture would be needed; this is mechanically feasible but requires moving fixture logic to a `conftest.py` that does not currently exist.

**`tests/test_clean_protocol_consumer_api.py`** — 4 pyright tests, 4 fixtures, 4 tmpdirs:  
Three of the four (shapes, castless probe, python-backend consumer) import only from `fltk` packages and could share a tmpdir with a single `pyrightconfig.json`. The fourth (`test_fltk2gsm_pyright_clean`, line 300) runs pyright on the real repo file `fltk/fegen/fltk2gsm.py` with no explicit cwd — it picks up pyright config from `pyproject.toml` at repo root. This one cannot be naively added to a tmpdir batch without copying/symlinking the file and ensuring fltk package resolution.

Batching the 3 batchable tests in `test_clean_protocol_consumer_api.py` into one tmpdir: feasible, saves ~1.2s (2 subprocess calls eliminated). Requires a session-scoped fixture that writes all three fixture files before the first test runs.

**Cross-module session-scoped tmpdir**: Would require a `conftest.py`. The `fegen_pyright_diagnostics` fixture (`scope=module`) depends on `fegen_pyi` which depends on `fegen_generator` (both `scope=module` in `test_gsm2tree_rs.py`). Promoting to `scope=session` and sharing a tmpdir with `test_clean_protocol_consumer_api.py` tests is feasible in principle but entails moving the generator pipeline to session scope. The file sets are disjoint (fegen_cst.pyi vs shapes_fixture.py etc.) so there is no content conflict — they could coexist in one tmpdir.

**`fltk/fegen/test_cst_protocol.py`**: 8 separate pyright calls, no batching. The fixtures cover different semantic questions (wrong-member-access, label-mismatch, stand-in class, span-widening variants). These could be batched into 2–3 grouped calls using the `_run_pyright_over_dir` pattern already established in `test_gsm2tree_rs.py`. Negative tests (lines 343, 375) simply need a path-keyed filter on the combined output.

### Failure attribution concern

The `_run_pyright_over_dir` approach (already used in `fegen_pyright_diagnostics`) partitions errors by file path. Each test filters its own file's errors. Negative tests assert `errors != []`. This pattern cleanly preserves per-test attribution with no loss of debuggability. The existing implementation at `test_gsm2tree_rs.py:1043-1048` demonstrates this works correctly.

### Win estimate

Current: 14 subprocess invocations × ~0.6s = ~8.4s of pyright startup overhead in the full test suite.

If fully consolidated to 2–3 batched directory runs (one per logical group): ~1.2–1.8s of pyright startup overhead. Net saving: ~6–7s of wall-clock time per full test run.

The saving is real at the test-suite level. On this machine, the full pyright-invoking tests run in 10.47s; consolidation would reduce that to ~4–5s. In CI, pyright startup may be slower (cold JVM/Node, slower disk), so the saving could be larger.

---

## Open factual questions

1. The TODO's claim about `test_poc_per_class_no_cast_zero_errors` — was this test planned but never written, or written and then removed? Git log for `tests/test_gsm2tree_rs.py` could resolve this but was not checked.
2. `fltk/fegen/test_cst_protocol.py` is not mentioned in the TODO at all, but contains 8 of the 14 pyright subprocess calls — more than twice the count in either file the TODO names. This is the largest consolidation opportunity.
