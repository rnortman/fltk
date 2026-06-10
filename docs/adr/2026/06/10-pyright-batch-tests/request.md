# Request: pyright-batch-tests

Style: concise, precise, no padding, no preamble. Self-contained — downstream agents do not see the triage conversation.

**Type**: test-infrastructure refactor. Behavior-preserving (same assertions, fewer subprocesses). No production code changes.

## Background

The test suite spawns 14 separate `uv run pyright` subprocesses (~0.6s each; ~8.4s measured overhead per full run). Validation (see `exploration.md` in this dir) mapped the real call sites — note the original TODO was factually wrong (named a nonexistent test; misattributed call sites to `tests/test_fltk_native_stub.py`, which has zero) and missed the largest offender entirely:

- `fltk/fegen/test_cst_protocol.py` — **8 calls** (`run_pyright()` at line 52; call sites at 315, 331, 343, 375, 437, 550, 568, 614; two are negative tests expecting errors).
- `tests/test_clean_protocol_consumer_api.py` — **4 calls** (`_run_pyright()` at line 91; sites at 231, 300, 850, 930). Three use tmp fixture files; the fourth (line 300) runs against the real repo file `fltk/fegen/fltk2gsm.py` using repo-root pyright config.
- `tests/test_gsm2tree_rs.py` — **2 calls**: the module-scoped `fegen_pyright_diagnostics` batch fixture (line 1095, already batching 3 tests via `_run_pyright_over_dir`, line 1019) and the unbatched PoC self-check (`test_poc_pyi_self_check_zero_errors`, line 1123).

The proven pattern already exists in-tree: `_run_pyright_over_dir` + path-keyed error filtering (`tests/test_gsm2tree_rs.py:1019-1048`) — one pyright run over a directory, each test filters diagnostics for its own file. Negative tests assert their file's errors are non-empty. Attribution is preserved.

## Direction (decided at triage — do not second-guess)

**Per-file batching only.** Explicitly NOT doing the original TODO's cross-module session-scoped tmpdir consolidation (poor win/complexity ratio: session-scope promotion of the generator fixture pipeline, new conftest plumbing).

1. `fltk/fegen/test_cst_protocol.py`: batch the 8 calls into 1–2 module-scoped directory runs using the `_run_pyright_over_dir` pattern. Each test writes (or a fixture pre-writes) its fixture file into the shared dir; tests filter diagnostics by their own file path. Negative tests (lines 343, 375) filter the same way and assert non-empty. If the fixtures' contents make a single batch awkward (e.g. deliberately-broken files needed by negative tests), two batches (positive/negative) is fine.
2. `tests/test_clean_protocol_consumer_api.py`: batch the three tmp-file tests (231, 850, 930) into one directory run. Leave the real-repo-file test (line 300) as its own subprocess — it depends on repo-root config and is not worth contorting.
3. `tests/test_gsm2tree_rs.py`: fold `test_poc_pyi_self_check_zero_errors` (line 1123) into a batched run. If folding it into `fegen_pyright_diagnostics` is clean (write `poc_cst.pyi` + stub into the same dir before the fixture's single run), do that; otherwise leave it — this one is the smallest win and not worth distortion.
4. Result target: 14 subprocesses → ~4 (1–2 + 2 + 1). Don't chase further.
5. Rewrite is not needed for helpers that already exist; prefer reusing/moving `_run_pyright_over_dir` over inventing a new harness. If sharing it across the three files requires a `conftest.py` helper, a plain importable test-util module is also acceptable — pick whichever matches repo convention.
6. Remove the `TODO(pyright-batch-tests)` code comments and the `TODO.md` entry.

## Constraints / non-goals

- Every existing assertion is preserved: same positive zero-error checks, same negative expects-errors checks, per-test attribution intact (a failure must name the offending fixture file).
- No production code changes. No changes to what pyright checks — only how many times it launches.
- Do not weaken negative tests into "some error somewhere in the batch": they must filter to their own file.
- Timeouts/skips: preserve the existing `pyright_available` session-fixture behavior (both copies; consolidating the duplicate fixture is allowed but optional).

## Verification

- `uv run pytest` green, full suite.
- Demonstrate the speedup: time the affected test files before/after (rough wall-clock in the implementation report is fine; expect ~6s improvement).
- Sanity-check attribution: deliberately perturb one fixture locally (not committed) and confirm only its test fails. State in the report that this was done.
- `grep -rn 'pyright-batch-tests'` returns nothing.
