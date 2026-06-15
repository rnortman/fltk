# Deep efficiency review — regex-grammar-spike

Base 61df5ff..HEAD 88282829. Reviewed: `fltk/fegen/regex_corpus.py`,
`tests/test_regex_grammar_corpus.py`, `tests/test_regex_grammar_adversarial.py`,
`Makefile` (1 line). Generated artifacts (`regex_cst*.py`, `regex_parser.py`,
`regex_trivia_parser.py`) are machine-emitted and excluded from authored-code review.

This is a test/tooling spike — no production hot path, startup path, or per-request
path is touched. The runtime regex-engine cost (`TerminalSource.consume_regex` calling
`re.compile` per terminal per position, `terminalsrc.py:178`) is pre-existing and
unchanged by this diff — out of lane. Findings below are the redundant-work items in
the new authored code; all are low-stakes because they sit in a test suite that runs
once, but they are real duplicated computation and one is a latent foot-gun.

---

## efficiency-1 — `test_regex_fltkg_self_referential` re-parses + re-collects a grammar already held at module scope

File: `tests/test_regex_grammar_corpus.py:181-200` (also `_corpus_cases` at :50-58).

The problem. Module load already does:

```python
_REGEX_CORPUS = _corpus_cases(_REGEX_FLTKG)   # parse_grammar_file + collect_regexes
```

so the distinct regex list for `regex.fltkg` is computed once and retained. Then
`test_regex_fltkg_self_referential` (line 188-189) calls `parse_grammar_file(_REGEX_FLTKG)`
and `collect_regexes(grammar)` *again* from scratch to get the identical list, and
`test_cli_entry_point_accepts_in_tree_grammar` (line 177) calls `_run_cli([str(_REGEX_FLTKG)])`
which parses `regex.fltkg` a *third* time. `parse_grammar_file` runs the full fegen
meta-parser (read file + `parse_grammar` over the whole grammar text), the single most
expensive step in the module — the parametric sweep's per-pattern `classify_pattern` calls
are cheap by comparison. So `regex.fltkg` is fully meta-parsed three times per test run, and
`collect_regexes` walked three times, to produce data already sitting in `_REGEX_CORPUS`.

Consequence. Redundant meta-parse work on every `pytest` invocation of this module — two
extra full grammar parses of `regex.fltkg` plus two extra GSM walks. It is bounded and
test-only, so the cost is a small constant added to every CI test run, not a scaling
ceiling. It bites every time the suite runs.

Fix. Reuse `_REGEX_CORPUS`. `test_regex_fltkg_self_referential` can derive its pattern
list as `[p for p, _ in _REGEX_CORPUS]` (or hoist `collect_regexes(...)` once into a
module-level `_REGEX_PATTERNS` and have both `_corpus_cases` and this test read it). The
CLI smoke test legitimately needs to exercise the `_run_cli` wiring end-to-end, so its
re-parse is the one defensible repeat — keep it, but the self-referential test's parse is
pure duplication of module-load work.

## efficiency-2 — `_IDS` / `_UNPACKED` and the parametrize `ids=[...]` rebuild the case list twice each

File: `tests/test_regex_grammar_adversarial.py:966-972`; `tests/test_regex_grammar_corpus.py:63`.

The problem. In the adversarial module, `_IDS` and `_UNPACKED` are each a full list
comprehension over `CASES` (~150 rows), and in the corpus module the `ids=[_pattern_id(p)
for p, _ in _ALL_CORPUS]` argument re-walks `_ALL_CORPUS` a second time alongside the
`_ALL_CORPUS` passed as the parameter values. These are one-time module-collection costs.

Consequence. Trivial — a few hundred string slices/replaces at import time, paid once per
collection. Noting it only for completeness; not worth restructuring on its own.

Fix. None warranted. Listed so the reviewer record is complete; the cost is negligible and
the readability of separate `_IDS`/`_UNPACKED` is worth more than the saved iteration.

---

Note on what was checked and cleared:

- `classify_pattern` (`regex_corpus.py:67-83`) constructs a fresh `RegexParser` and
  `TerminalSource` per call — this is correct, not wasteful: the parser carries per-input
  packrat/error state and cannot be reused across patterns. No memoization is appropriate
  (each test pattern is distinct).
- `collect_regexes` uses an insertion-ordered dict for dedup (`regex_corpus.py:49`) and a
  single `gsm._for_each_item` walk — no redundant traversal, correct choice over re-walking.
- `_run_cli` reads the grammar exactly once and loops patterns once — clean.
- No unbounded structures, no listener/handle leaks, no polling loops, no concurrency
  opportunity (the work is inherently sequential per-pattern and test-bound).
