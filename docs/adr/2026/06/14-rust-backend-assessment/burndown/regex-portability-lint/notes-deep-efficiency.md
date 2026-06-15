# Deep efficiency review — regex-portability-lint

Commit reviewed: ba953c8 (base 034252d). Scope: the new portability check
(`fltk/fegen/regex_portability.py`), its wiring into the Rust generator
(`gsm2parser_rs.py`), the corpus/CLI helper (`regex_corpus.py`), and the new tests.

This is a generation-time (build-time) code path, not a runtime/per-request hot path:
`check_regex_portable` runs once per `gsm.Regex` term while the Rust parser is being
generated, which itself runs in `make gencode`. Cost magnitudes are therefore small in
absolute terms; findings are framed accordingly.

---

## efficiency-1 — Portability check is per-term, not per-distinct-pattern (redundant re-parse of duplicate regexes)

`fltk/fegen/gsm2parser_rs.py:790` (the `gsm.Regex` branch of `_gen_consume_term`).

`check_regex_portable(term.value)` is called every time `_gen_consume_term` reaches a
`gsm.Regex` term. The very next line, `idx = self._regex_idx(term.value)`
(`:798`), exists precisely because the same pattern string commonly appears at multiple
term sites — `_regex_idx`/`_regex_index` dedups patterns into one table entry. The
portability check has no such dedup: a pattern used in N rules is fully re-parsed N
times, each time building a fresh `TerminalSource`, a fresh `_RegexParser`, and running
the packrat regex parse from scratch.

**Consequence:** wasted CPU at Rust-parser generation time, proportional to the number
of *duplicate* regex term occurrences in a grammar (not distinct patterns). For in-tree
grammars this is a handful of extra parses; for a large downstream grammar that reuses a
nontrivial regex across many rules it scales with occurrence count. It is pure waste —
the result is identical every time for a given string. The design itself anticipates
this (§6: "re-checking a repeated pattern is harmless (memoize on the pattern string if
ever a concern)").

**Fix direction:** check only on first registration of a pattern. Cheapest form — gate
the check on the dedup miss so it runs once per distinct pattern:

```python
if term.value not in self._regex_index:
    issue = check_regex_portable(term.value)
    if issue is not None:
        raise ValueError(...)
idx = self._regex_idx(term.value)
```

This preserves the design's "check at the user-term site, not inside `_regex_idx`"
intent (the gate is still at the `gsm.Regex` branch, not inside the shared helper used
for the internal `\s+` trivia pattern), while collapsing N re-checks of the same string
to one. Alternatively memoize a `set[str]` of already-validated patterns on the
generator instance.

---

## efficiency-2 — Test parametrization parses each Rust-target grammar twice at collection time

`tests/test_regex_portability.py:434-447` (the `@pytest.mark.parametrize` for
`test_committed_rust_target_grammar_regex_is_portable`).

`_load_grammar_regexes(grammar_path)` — which calls `parse_grammar_file` (a full grammar
parse) — is invoked inside both the params list comprehension and the `ids=` list
comprehension, over the same three grammars. So each of the three Rust-target grammars
(including `fegen.fltkg`, the largest) is parsed **twice** during pytest collection, every
test session, regardless of which tests are selected (parametrize runs at import/collection
time).

**Consequence:** every `pytest` collection over this module pays an extra full parse of
three grammars (one of them the full FLTK self-hosting grammar). It is small but it is
paid on every test run and every `-k`/collection-only invocation, and it is invisible
waste (the cost shows up as slower collection, not in any single test's timing).

**Fix direction:** compute the `(grammar_path, regexes)` pairs once into a module-level
list, then derive both `params` and `ids` from that single list:

```python
_TARGET_CASES = [
    (str(gp), pat)
    for gp in _RUST_PARSER_TARGET_GRAMMARS
    for pat in _load_grammar_regexes(gp)
]
...
@pytest.mark.parametrize(
    "grammar_path,pattern",
    _TARGET_CASES,
    ids=[f"{Path(gp).name}::{pat[:40]}" for gp, pat in _TARGET_CASES],
)
```

(`test_regex_grammar_corpus.py` already follows this single-list pattern with
`_ALL_CORPUS`, so this aligns the two modules.)

---

## Checked and clear

- **Fresh parser per call inside `check_regex_portable`** — building a new
  `TerminalSource`/`_RegexParser` per call is correct and necessary (the parser carries
  per-parse memo/error state and is not reusable across inputs). The waste is only in
  *how often it is called* (efficiency-1), not in the per-call construction itself.
- **Empty-pattern short-circuit** (`regex_portability.py:83`) avoids parser construction
  for the empty string — good, the cheap path is taken first.
- **`collect_regexes` dedup** (`regex_corpus.py`) uses an ordered dict to return distinct
  patterns once — correct, no redundant downstream classification.
- **Docstring/`REGEX_PATTERNS` emission, parity-fixture and cst.rs additions** — pure
  data/text additions; no new per-request or per-render work introduced.
- **No new startup/import-time work of note** — `regex_portability` imports the committed
  `regex_parser` at module load (a pure-Python import, no Rust build, no parse), consistent
  with the existing committed-parser pattern.
