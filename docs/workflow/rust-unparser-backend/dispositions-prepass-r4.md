# Dispositions: prepass round 4

Scope notes (`notes-prepass-scope-r4.md`): "No findings." No scope work required;
no escalation. Only the three slop findings are dispositioned below.

slop-1:
- Disposition: Fixed
- Action: Corrected the typo "lable" -> "label" in the required-suppressed-term
  error message at `fltk/unparse/gsm2unparser_rs.py:511` and in the Python backend
  it mirrors, `fltk/unparse/gsm2unparser.py:529`. Both files kept byte-identical, so
  the design's "same messages as the Python backend" parity intent is preserved while
  the bug is removed. No test asserted on the misspelling (verified via grep).
- Severity assessment: A typo in a user-facing generation-time error message that
  ships in two files; cosmetic but reviewer-visible and easy to fix at the source.

slop-2:
- Disposition: Fixed
- Action: Added a public wrapper `num_child_variants(rule_name) -> int` to
  `RustCstGenerator` (`fltk/fegen/gsm2tree_rs.py`, after `rule_has_labels`),
  paralleling the existing public helpers. Replaced the two cross-class private
  accesses to `_child_variants_for_rule` and their duplicated
  `len(child_classes) + (1 if has_span else 0)` arithmetic in the unparser generator
  (`fltk/unparse/gsm2unparser_rs.py`, `_gen_identifier_term_body` and
  `_gen_validate_span_child`) with calls to the new wrapper. Both call sites only
  needed the variant count, so the wrapper fully centralizes the logic and removes
  the private-method reach-through.
- Severity assessment: Maintainability trap — cross-class private-method access with
  duplicated count arithmetic and no in-code marker; would invite repetition in the
  pending regex/loop increments. The implementation log itself flagged this as a
  candidate wrapper.

slop-3:
- Disposition: Fixed
- Action: Rewrote the new generator's docstrings/inline comments in
  `fltk/unparse/gsm2unparser_rs.py` to state each method's current contract instead
  of narrating the development process. Removed "later increment" / "this increment"
  / "deferred" / "pass-through scaffold for a later increment" phrasing (replaced with
  factual present-tense descriptions of the pass-through bodies) and stripped the
  brittle `gsm2unparser.py:NNNN` (and one `gsm2parser_rs.py:225`) line-number
  cross-references. Trimmed the cross-backend "Where the Python backend..." rationale
  paragraphs, retaining only the load-bearing explanation of the `num_variants > 1`
  match-arm guard. Verified no residual narration/line-refs remain via grep.
- Severity assessment: LLM-tell docstrings that read as a work-session log and would
  go stale (line numbers) or misleading (after the deferred bodies are filled in);
  no behavioral impact, but a clear code-quality/reviewer signal.

Verification: `ruff check` clean on all three files; `pyright` 0 errors;
`fltk/unparse/` + `tests/test_rust_unparser_generator.py` = 316 passed.
