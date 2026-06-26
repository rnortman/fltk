# Dispositions — design review r2

Design: `./design.md`
Reviewer notes: `./notes-design-design-reviewer-r2.md`
Base commit: `49e9701e927d1403065f902b99d54acd7c129e41`

design-1:
- Disposition: Fixed
- Action: Rewrote the §4.1 `tests/test_clean_protocol_consumer_api.py` bullet (now two
  sub-bullets) to direct RETARGET (not delete) of `_rust_cst_grammar` (`:160-168`, the `:163`
  hybrid `generate_parser(rust_cst_module=...)` site): drive the genuine config-2 parser
  `fegen_rust_cst.parser.Parser(grammar_text, capture_trivia=False)` → `apply__parse_grammar(0)` →
  `result.result`, the same API `TestRustParserSelfHosting` uses
  (`tests/test_phase4_fegen_rust_backend.py:252-263`), keeping all `TestCrossBackendDualShapeDispatch`
  assertions. The `:360` `test_fltk2gsm_behavioral_equivalence` site is still removed, with a note
  that its Cst2Gsm-agnosticism property is covered by the kept `TestRustParserSelfHosting`. Added a
  new §4 test-plan bullet ("Consumer-side cross-backend dispatch agnosticism preserved") recording
  that this class is the sole coverage of Shape 1 / Shape 2 dispatch producing identical results on
  Python vs Rust CST. Broadened the §4.1 intro so its retarget clause covers the Rust-parser source,
  not only directly-constructed nodes.
- Severity assessment: Following §4.1 literally would delete `TestCrossBackendDualShapeDispatch`
  by dependency, dropping the only coverage of the mandated consumer-side backend-agnosticism
  property (`requirements.md`: "the CST-consuming code remains agnostic to which backend was
  used"); the kept `test_rust_parser_parity_*` tests check structural parity by `.start`/`.end`,
  not consumer match/case dispatch, so the regression would land squarely on a central requirement.
  Verified: `_rust_cst_grammar:163` feeds `rust_items` (`:579-583`) which feeds the class (`:566`);
  the genuine `fegen_rust_cst.parser.Parser` path exists and produces `fegen_rust_cst.cst.Grammar`
  Rust CST nodes whose span children's `.kind` is the shared `SpanKind.SPAN`, so the dispatch
  assertions still hold.

design-2:
- Disposition: Fixed
- Action: Added `_fegen_grammar_cache` (`:38`) to the §2.3 deletion list, with a note that it is
  referenced only inside the deleted `_load_fegen_grammar` (`:53,66,67`) and that ruff's
  unused-binding rules do not flag module-level globals, so `make check` would not catch it.
- Severity assessment: Low blast radius — orphaned module-level state surviving as silent cruft,
  contradicting §2.3's own "delete the now-dead support code" intent. Verified by grep that
  `_fegen_grammar_cache`'s only references (`plumbing.py:38,53,66,67`) are inside `_load_fegen_grammar`,
  which §2.3 deletes.
