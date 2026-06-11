# Dispositions: prepass review

---

## slop-1

- Disposition: Won't-Do
- Action: no change
- Severity assessment: Finding describes a multi-line "thought-log" comment at
  gsm2parser_rs.py:346-352 quoting text that does not exist in the file. The file
  is 647 lines (post-edits); lines 345-349 contain a normal `.expect()` string,
  not the quoted narrative. Finding is a hallucination.
- Rationale (Won't-Do): The described comment does not exist in the source; no
  change is applicable.

---

## slop-2

- Disposition: Fixed
- Action: gsm2parser_rs.py:271 — added docstring to `_gen_parser_struct` stating
  the open-but-not-closed impl block postcondition; removed the inline trailing
  comment that previously described the same fact.
- Severity assessment: Minor readability issue; the inline comment was accurate
  but misplaced as a trailing note rather than a method contract.

---

## slop-3

- Disposition: Fixed
- Action: test_gsm2parser_rs.py:213 — extracted the allowlist to module-level
  `_EXPECTED_NON_APPLY_PUB_FNS`; rewrote loop to use `.removeprefix("pub fn ")`
  and check `startswith("apply__")` first, eliminating the confusing double-negative
  condition. Logic is identical; the code no longer reads as contradictory.
- Severity assessment: The test was correct but confusing; a maintenance author
  adding a new pub fn to Parser could miss the allowlist.

---

## slop-4

- Disposition: Fixed
- Action: test_gsm2parser_rs.py:345 — renamed `test_no_regex_table_when_no_regexes`
  to `test_regex_table_present_for_trivia_even_without_user_regexes`; updated
  docstring to explain why the table is always present; added assertion that the
  only pattern in the table is the trivia whitespace pattern `[\\s]+`.
- Severity assessment: The old name flatly contradicted the assertion; anyone
  reading the test suite would be misled about generator behavior.

---

## slop-5

- Disposition: Fixed
- Action: test_gsm2parser_rs.py:406 — replaced the vague docstring with one that
  names the specific CstGenerator AssertionError path (non-Identifier INLINE),
  explains why both exception types are accepted, and references the separately
  pinned test for Identifier-INLINE. No code change to the `pytest.raises` call —
  the two-type tuple remains correct because the rejection genuinely depends on
  which layer fires.
- Severity assessment: The docstring was actively misleading ("doesn't know when
  or what type"); the replacement explains the design without changing behavior.

---

## slop-6

- Disposition: Fixed
- Action: tests/rust_cst_fegen/src/native_parser_tests.rs:35 — replaced the
  dead no-assertion failure branch with `assert!(result.is_none())` and
  `assert!(parser.error_position().is_some())`. The input `"grammar := !!!invalid;"`
  reliably fails to parse.
- Severity assessment: The test was completely inert in the failure branch —
  it passed unconditionally and provided no coverage of `error_position()`.

---

## scope-1, scope-2, scope-3, scope-4

- Disposition: ESCALATE
- Action: See escalation-respond.md for per-finding rationale.
- Severity assessment: Collectively represent design-mandated implementation work
  (new generator feature, Makefile wiring, new grammar content + regenerated
  committed artifacts + Rust test functions) that was not shipped. Neither Fixed
  nor TODO is appropriate; re-entering incremental mode is the correct path.
