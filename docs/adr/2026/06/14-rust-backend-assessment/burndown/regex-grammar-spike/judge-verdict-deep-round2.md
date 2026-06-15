# Judge verdict — deep review (round 2)

Phase: deep. Base 61df5ff..HEAD 4bc9b36 (rework commit). Round 2 — APPROVED or ESCALATE only.
Subject: regex-grammar-spike. Round 1 flagged exactly two TODO dispositions as wrong
(quality-3, errhandling-2+quality-5) — both do-now work dressed as design deferral (failed
rubric Q2). Every other disposition (17 findings) was accepted in round 1 and is unchanged by
the rework diff (verified: `git diff bb46e3e..4bc9b36` touches only `TODO.md`, the
dispositions doc, and `tests/test_regex_grammar_corpus.py`). This round re-walks only the two
disputed items.

## Reworked items walk

### quality-3 — was TODO(corpus-test-count-to-set), now Fixed
Round-1 defect: deferred replacing `assert len(patterns) == 12` (magic-number change-detector)
with a named-set assertion, on the false premise that "listing all 12 patterns" is non-trivial
design work — it is mechanical (the patterns are already enumerated by `collect_regexes`).
Rework (`test_regex_grammar_corpus.py:223-247`): `assert len == 12` replaced with
`assert set(patterns) == expected_patterns`, where `expected_patterns` is a 12-element
`frozenset` of the distinct terminals, each with an inline naming comment, and the failure
message prints the added/removed diff. TODO comment removed from the test; `corpus-test-count-to-set`
removed from `TODO.md` (verified: `grep` finds no residual reference anywhere in code/`TODO.md`).
Ground truth: ran the live parser — `collect_regexes(parse_grammar_file(regex.fltkg))` yields
exactly 12 distinct patterns, and `test_regex_fltkg_self_referential` (which now carries the
frozenset assertion) is among the 185 passing tests — so the pinned set matches the live
output exactly, not a stale transcription.
Assessment: the named-set change-detector the reviewer asked for, no design/owner input
consumed, TODO retired. Fix correct. Accept.

### errhandling-2 + quality-5 — was TODO(corpus-test-collection-error-context), now Fixed
Round-1 defect: deferred wrapping the two module-level `_corpus_cases(...)` calls, on the
premise that the fix "requires restructuring parametrize ... non-trivial" — when both reviewers
explicitly offered the cheap ~3-line `try/except → pytest.skip/UsageError` alternative.
Rework (`test_regex_grammar_corpus.py:57-65`): the two `_corpus_cases(...)` calls are wrapped in
`try/except Exception` that re-raises `pytest.UsageError` naming both grammar files and pointing
at `uv run --group dev maturin develop`. No parametrize restructuring — the cheap path the
reviewers named. TODO comment removed from the test; `corpus-test-collection-error-context`
removed from `TODO.md` (verified: no residual reference). `quality-5` was correctly merged under
the same slug and is resolved by the same wrapper.
Ground truth: `pytest.UsageError` confirmed a real pytest symbol; the corpus + adversarial
suites collect cleanly and 185 tests pass (so the wrapper does not break the happy-path
collection it guards).
Assessment: the exact cheap fix both reviewers offered, applied; failed Q2 no longer applies
because the work was done, not deferred; TODO retired. Fix correct. Accept.

## Approved

19 findings total, all dispositions now acceptable. 17 carried unchanged and accepted from
round 1 (9 Fixed verified against the live parser/tests — correctness-1, correctness-2,
errhandling-1, test-1, test-2, test-3, quality-1, quality-4, efficiency-1; 6 Won't-Do sound —
correctness-3, security-1, test-4, reuse-1, reuse-2, efficiency-2; 1 TODO acceptable —
quality-2 / gsm-for-each-item-public, which remains intact in `TODO.md`). The 2 round-1
disputed items (quality-3, errhandling-2+quality-5) are now Fixed and verified above.

---

## Verdict: APPROVED

Both round-1 REWORK items were resolved with real code changes, verified against ground truth:
the frozenset of 12 patterns matches the live `collect_regexes` output (the self-referential
test passes), and the `try/except pytest.UsageError` wrapper is the cheap fix both reviewers
named (suites green, 185 passed). Both TODO comments and both `TODO.md` entries were removed;
the one accepted TODO (gsm-for-each-item-public) is correctly retained. No remaining disputed
items. Commit 4bc9b36.
