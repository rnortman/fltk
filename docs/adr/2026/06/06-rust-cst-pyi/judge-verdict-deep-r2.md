# Judge verdict — deep review, round 2

Phase: deep. Base 46a6639..HEAD f9517ea (rework commit f9517ea on top of ce786b0). Round 2 — APPROVED or ESCALATE only.
Scope: the six dispositions disputed in `judge-verdict-deep.md` (test-6, test-7, reuse-1, efficiency-1, efficiency-2, efficiency-3), re-dispositioned in `dispositions-deep-r2.md`. The 18 round-1-approved findings are not re-walked.
Style: concise, precise, complete. Audience: smart LLM/human.

## Disputed-items walk

### test-6 — Won't-Do (was slugless TODO)
R1 demanded: write the PoC per-class test (mechanical) OR convert to Won't-Do and delete the slugless comment.
Action taken: bare `# TODO:` comment deleted (diff, end of `test_fegen_per_class_no_cast_zero_errors`); disposition Won't-Do with new rationale: PoC classes of the same name are structurally incompatible with the fegen protocol — the test would fail by design.
Verification: structural claim checked against source. PoC `items` rule (`test_gsm2tree_rs.py:_make_poc_grammar`) has labels `no_ws/ws_allowed/ws_required/item` with an `Identifier` child ref; fegen's `items` rule (fegen.fltkg:5) has a different shape with `Item` children. The per-class fixture asserts assignability to `cstp.<ClassName>` (the fegen protocol), so `poc_cst.Items` → `cstp.Items` fails by construction; same for the synthesized PoC `Trivia` lacking `block_comment`/`line_comment` accessors. The reviewer's premise (an explicit PoC test "guards small-grammar edge cases") is a false premise — the test is unwritable against this protocol.
Assessment: Won't-Do is correct on the merits (active-harm bar met: the test would be red by design); convention violation removed. Accept.

### test-7 — Fixed (was slugless TODO)
R1 demanded: drop the `# TODO:` prefix, keep the explanatory comment, re-disposition Fixed.
Verification: diff at `tests/test_gsm2tree_rs.py:876-879` — prefix gone; plain comment documents the quoted-string-only scope of the fast lint and names the pyright conformance tests as authoritative guard. Exactly the reviewer's option (b).
Assessment: accept.

### reuse-1 — Fixed (was TODO(pyi-node-kind-name-reuse))
R1 demanded: delegate to `self._py_gen.node_kind_member_name(rule_name)`; remove TODO comment + TODO.md entry.
Verification: diff — `_node_kind_python_name` now takes `rule_name` and delegates (`gsm2tree_rs.py:339-345`); both call sites (`generate_pyi` :154, `_node_kind_block` :393) pass `rule_name` from `_rule_info()`. TODO comment and `## pyi-node-kind-name-reuse` TODO.md entry both removed. Output equivalence verified: `node_kind_member_name(rule_name)` = `class_name_for_rule_node(rule_name).upper()` (`gsm2tree.py:95-97`), and `_rule_info` derives `class_name` via the same `class_name_for_rule_node(rule.name)` — identical emitted names, no artifact regeneration required. All `.rs`/`.pyi` set-match and determinism tests pass at HEAD.
Assessment: accept.

### efficiency-1 — Fixed (minimum-viable) + narrowed TODO(pyright-batch-tests)
R1 demanded: merge the three fegen pyright tests into one tmpdir/run; narrow the TODO.md entry to the remainder.
Verification: diff — module-scoped `fegen_pyright_diagnostics` fixture writes stub + whole-module fixture + per-class fixture into one `tmp_path_factory` tmpdir; `_run_pyright_over_dir` runs one `uv run pyright --outputjson <dir>` and partitions error diagnostics by file path; all three fegen tests consume it. Pyright invocations for the new tests: 4 → 2 (fegen batch + PoC self-check; the PoC per-class run no longer exists per test-6).
Empirical: all 110 tests in `test_gsm2tree_rs.py` pass at HEAD; batched fixture setup ~1.0 s. Negative probe run by this judge: injected a broken stub through the same helpers — `_run_pyright_over_dir` reports the error (1 diagnostic, correct file key), so the `errors == []` assertions are not vacuous.
Residual TODO: remainder is cross-file harness consolidation (session-scoped tmpdir across test modules + the pre-existing `test_cst_protocol.py` call sites). Q1: yes — real remaining cost. Q2: yes at this scope — cross-module session-scoped fixture restructuring against established per-test precedent (8+ call sites) is the larger refactor R1 already conceded is not mechanical. TODO acceptable as narrowed.
Two hygiene nits in the narrowed entry (do not change the disposition outcome; see Nits): it cites `test_poc_per_class_no_cast_zero_errors`, which was Won't-Do'd and does not exist; and no `TODO(pyright-batch-tests)` code comment remains to pair with the TODO.md entry after both code-side comments were (correctly, per R1) removed.
Assessment: accept.

### efficiency-2 — Fixed (was TODO(fegen-pyi-fixture-sharing))
R1 demanded: module-scoped `fegen_generator` fixture; derive `fegen_source` and `fegen_pyi` from it; remove TODO.md entry.
Verification: diff — `fegen_generator` fixture added (`test_gsm2tree_rs.py:140-163`); `fegen_source` and `fegen_pyi` are now one-line derivations; duplicate parse pipeline deleted; TODO.md entry removed. Tests pass.
Assessment: accept.

### efficiency-3 (residual) — Fixed
R1 demanded: `functools.cache` on `_parse_stub`; drop the comment.
Verification: diff — `@functools.cache` applied (`test_fltk_native_stub.py:54`); TODO comment replaced by a plain docstring sentence; `functools` imported. All 5 stub tests pass.
Assessment: accept.

## Gate checks

- `uv run pytest tests/test_gsm2tree_rs.py tests/test_fltk_native_stub.py` — 115 passed at f9517ea (pyright 1.1.402 available and exercised; durations confirm real subprocess runs).
- `uv run ruff check` + `uv run pyright` on the three r2-changed files — clean.

## Nits (non-blocking, no arbitration needed)

1. `TODO.md` `## pyright-batch-tests` first sentence references `test_poc_per_class_no_cast_zero_errors`, a test Won't-Do'd in test-6 that does not exist. Stale sentence; one-line edit whenever the entry is next touched.
2. The `pyright-batch-tests` TODO.md entry has no paired `TODO(slug)` code comment (both code-side comments were removed in r2). Repo convention pairs entry + comment; a one-line anchor at `_run_pyright_in_tmpdir` or the PoC self-check test would restore sync.
Both are cosmetic doc-hygiene issues with no behavioral consequence and no reviewer/responder disagreement attached; they do not rise to ESCALATE.

## Approved

6 disputed dispositions resolved: 4 Fixed verified (test-7, reuse-1, efficiency-2, efficiency-3), 1 Fixed-plus-narrowed-TODO verified with negative-probe validation (efficiency-1), 1 Won't-Do verified correct on false-premise grounds (test-6). Round-1 approvals (18 entries) unchanged by the r2 diff.

---

## Verdict: APPROVED

All six round-1 disputes resolved as directed or better (test-6's Won't-Do is sounder than either option R1 offered, and is source-verified). Slugless TODOs eliminated; all four rubric-failing deferrals executed; residual TODO properly narrowed and rubric-acceptable. Tests, lint, and types clean at f9517ea. Two TODO.md hygiene nits noted, non-blocking.
