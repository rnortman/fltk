# Dispositions — deep review, round 1

Commit with fixes: `280259b3acadf32d19def52cf0687c97841d92ee` (base `1d277ce8`, prior HEAD `462cf1c9`).

Reviewers with no findings: error-handling, security, test, reuse, efficiency.

## correctness-1

- Disposition: Fixed
- Action: Rewrote the `_gen_non_trivia_rule_processing` docstring bullet
  (`fltk/unparse/gsm2unparser_rs.py:1309-1315`) to describe the emitted
  panic-on-failure `else` arm and its Python `raise_preserved_trivia_failure`
  mirror, and clarified that `pos` advances only on success. Also qualified the
  later "`pos` always advances" sentence (`:1326`) so it does not contradict the
  corrected bullet (the advance is emitted unconditionally but the failure
  `panic!` aborts before reaching it).
- Severity assessment: No wrong runtime behavior, but the docstring asserted the
  exact silent-continue semantics this commit removed and cited a Python line
  whose behavior this commit changed — a code/documentation contradiction that
  could mislead a maintainer into reintroducing the silent path. Design change 2
  explicitly mandated this docstring update, so it was an omission, not a
  judgment call.

## quality-1

- Disposition: Fixed
- Action: Added `_get_pyrt_module()` helper next to `_get_combinators_module` /
  `_get_accumulator_module` (`fltk/unparse/gsm2unparser.py:380-388`) and routed
  all four `fltk.unparse.pyrt` module-reference sites through it (the new site
  plus the three pre-existing inline copies at the former lines 388, 958, 1775).
  Emitted code is byte-identical (`_get_pyrt_module` returns the same
  `iir.VarByName`), verified by the full `check` gate.
- Severity assessment: Low. Pure maintainability — the change had added a fourth
  identical inline copy where a helper convention already existed for sibling
  modules; consolidating removes the divergent convention and the four-site edit
  cost of any future rename. Mechanical and low-risk, so fixed rather than
  deferred.

## quality-2

- Disposition: Fixed
- Action: Added a module-level `_expected_span_text_panic(rule, item_desc)`
  helper in `tests/test_rust_unparser_generator.py` (after `_method_body`) and
  replaced the five copy-pasted site-2 panic-string assertion literals with calls
  to it; the single site-1 literal is left inline as the reviewer noted.
- Severity assessment: Low, test-only. Centralizes the expected diagnostic
  wording so a future rewording is a one-line edit instead of five coordinated
  ones, and surfaces the one thing each test varies (the item descriptor). All
  affected tests pass.
