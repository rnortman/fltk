# Judge verdict — deep review (regex-portability-lint), round 2

Phase: deep. Base 034252d..HEAD b57dc36. Round 2 (APPROVED or ESCALATE only).
Notes: 7 reviewer files; 22 findings. Round-1 verdict: REWORK on the single disposition
reuse-1 (TODO → do-now).
Design: `burndown/regex-portability-lint/design.md`.

Round-1 disposition of all findings except reuse-1 was accepted (13 Fixed verified, 3
Won't-Do sound, 1 TODO acceptable — see `judge-verdict-deep.md`). The round-2 diff
(`git diff 6a43f9c..b57dc36`) touches only four files and is exactly the reuse-1 rework:
`fltk/fegen/regex_corpus.py`, `fltk/fegen/regex_portability.py`, `TODO.md`, and the
dispositions doc. No code, grammar, generated artifact, or test outside the reuse-1
rework changed, so no previously-accepted finding can have regressed. This walk
re-adjudicates only the reworked item.

## Reworked item walk

### reuse-1 — was TODO(regex-portability-check-reuse), now Fixed
Round-1 verdict: TODO failed rubric Q2 — the shared-predicate extraction between
`check_regex_portable` and `classify_pattern` is mechanical, single-package, needs no
design cycle or owner input → do-now. Required: land the refactor and convert to Fixed,
OR supply a concrete reason for deferral.

Rework applied (verified in `6a43f9c..b57dc36`):
- `regex_corpus.py:classify_pattern` body collapsed from the duplicated
  `TerminalSource → _RegexParser → apply__parse_regex(0) → result is not None and
  result.pos == len(...)` driver to a single delegation:
  `return check_regex_portable(pattern) is None` (`regex_corpus.py:77`). The
  accept/reject predicate now has one canonical home in `check_regex_portable`.
- The duplicated boilerplate's unused imports were removed from `regex_corpus.py`
  (`from ...pyrt import terminalsrc`, `from ...regex_parser import Parser as RegexParser`),
  replaced by `from fltk.fegen.regex_portability import check_regex_portable`.
- `TODO(regex-portability-check-reuse)` comment removed from `regex_portability.py:88`.
- The `## regex-portability-check-reuse` entry removed from `TODO.md` (confirmed absent
  via grep across `TODO.md`, `fltk/`, `tests/`).

Equivalence check (the one behavioral subtlety the round-1 reuse reviewer flagged): the
old `classify_pattern` compared `result.pos == len(terminals.terminals)` while
`check_regex_portable` compares `result.pos == len(pattern)`. For a `TerminalSource`
built over the same `str`, `len(terminals.terminals) == len(pattern)`, so the predicate
is identical — the delegation does not change any accept/reject verdict.

Cycle check: `regex_portability.py` imports only `pyrt.terminalsrc` and `regex_parser`
(no `regex_corpus` import) — the new `regex_corpus → regex_portability` edge introduces
no import cycle.

Verification: `tests/test_regex_portability.py` + `tests/test_regex_grammar_corpus.py`
run green (159 passed, 1 skipped — the skip is the pre-existing shell-escaping-artifact
corpus case, not a regression). The corpus suite (which drives `classify_pattern`) and the
portability unit/whole-tree suites (which drive `check_regex_portable`) both pass through
the single delegated predicate.

Assessment: the TODO was converted to a landed, mechanical, behavior-preserving refactor
exactly as the round-1 verdict required. Disposition now correct. Accept.

## Disputed items

None. The sole round-1 dispute (reuse-1) is resolved.

## Approved

22 findings: 13 Fixed verified in round 1, 3 Won't-Do sound in round 1, 1 TODO acceptable
in round 1 (test-4), plus reuse-1 now Fixed (reworked from TODO this round). No
non-reuse-1 file changed between rounds, so the 21 round-1 dispositions stand unre-walked.

---

## Verdict: APPROVED

The single round-1 defect (reuse-1 TODO → do-now) is reworked into a landed,
behavior-preserving delegation; the duplicated predicate and its TODO (code comment +
TODO.md entry) are gone, tests pass, no import cycle, no regression in the other 21
findings (round-2 diff is reuse-1-only). All dispositions acceptable.

Commit: b57dc36.
