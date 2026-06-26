# Design review (r2): two-backends-only / hybrid removal

Scope verified against source at base commit `49e9701`. The core fix (§2.1 retarget
`_make_span_expr` + `_source_text` construction to `terminalsrc`; §2.2 lazy annotations +
`TYPE_CHECKING` span import + warning removal; §2.3 hybrid plumbing deletion) is well
grounded and technically sound. Spot-checks that PASSED:

- `_make_span_expr` (gsm2parser.py:259-281) and the `Construct(SourceTextType)` `_source_text`
  init (gsm2parser.py:105-137) exist as described; the IIR substitution
  (`MethodAccess(...).call(...)` → `fltk.fegen.pyrt.terminalsrc.{Span.with_source,SourceText}`)
  compiles correctly via compiler.py:285-289,305-309,329-330 (MethodCall emits
  `bound_to.member(args)`, VarByName emits `expr.name` verbatim). `Construct` routes through the
  registry (compiler.py:312-315 → reg.py:26-29) to `span.*`, confirming why a string/IIR-node
  swap (not a registry edit) is required to avoid annotation churn.
- Registry entries for `Span`/`SourceText` stay at `("fltk","fegen","pyrt","span")`
  (context.py:113-132, gsm2parser.py:78-84); child span annotations render
  `fltk.fegen.pyrt.span.Span` (toy_cst.py:150, toy_cst_protocol.py:98) — frozen-surface claim holds.
- Committed parser runtime uses of `span` are exactly the two construction sites + lazy-able
  annotations (fltk_parser.py:16,83,...; return types at :80,:90,...). pygen exposes
  `module/if_/import_/stmt/expr`; gsm2tree.py:185-202 is the cited working pattern.
- `make gencode` regenerates exactly the 10 parser files listed in §2.5.
- Parity helper compares spans by `.start`/`.end`, not `==` (parser_parity.py:15-18,39-42), so
  config-1 (terminalsrc.Span) vs config-2 (_native.Span) parity survives — §3.3 verified, not assumed.
- `extract_span` is at cross_cdylib.rs:422 (PyTypeError reject) — §1.3 reference accurate.
- Hybrid-symbol grep (`rust_cst_module`, `rust_fegen_cst_module`, `_load_rust_cst_classes`,
  `RustBackendUnavailableError`, `_load_fegen_grammar`, `_fegen_rust_parser_cache`) finds NO
  callers outside plumbing.py + the four test files §4.1 enumerates. No dangling `native_span`
  selection survives in non-test code. Hybrid removal is complete w.r.t. these symbols.

## design-1 — Cross-backend dual-shape DISPATCH tests risk deletion instead of retarget

- Section: §4.1, bullet `tests/test_clean_protocol_consumer_api.py` ("remove the
  `generate_parser(..., rust_cst_module=...)` site (`:163`) ... plus any fixtures/asserts that
  depend only on them").
- What's wrong: `_rust_cst_grammar` (tests/test_clean_protocol_consumer_api.py:160-168, the `:163`
  hybrid `generate_parser(rust_cst_module="fegen_rust_cst.cst")` site) is the data source for the
  `rust_items` fixture (`:580-583`) feeding `TestCrossBackendDualShapeDispatch` (`:566`). Its tests
  — `test_shape2_rust_backend_dispatches_correctly`, `test_shape2_python_and_rust_structurally_identical`
  (`:650`), `test_shape1_*`, `test_span_kind_narrows_rust_backend_span_children` (`:676`) — verify
  that a *consumer's* match/case (Shape 2) and interleaved-walk (Shape 1) dispatch produce
  identical results on a Python CST vs a Rust CST. Per the literal §4.1 instruction these get
  removed by dependency. Unlike the §4.1 guidance for `test_phase4_*` ("may be retained by
  constructing Rust nodes directly"), this file gets NO retarget guidance.
- Why: These are NOT hybrid-enforcing tests in the user's sense (the user said "remove unit tests
  that enforce the presence of [the hybrid] option", notes-design-user.md). They exercise the
  exact swap-ability/agnosticism guarantee the requirements demand ("the CST-consuming code remains
  agnostic to which backend was used", requirements.md) and that CLAUDE.md names a hard constraint
  (cross-backend behavioral equivalence). The hybrid is only their incidental vehicle for obtaining
  a Rust CST. A Rust CST is still obtainable via the genuine config-2 path — `fegen_rust_cst.parser.Parser`
  — which the design itself keeps and uses elsewhere (§4: `TestRustParserSelfHosting` drives
  `fegen_rust_cst.parser.Parser`). So `_rust_cst_grammar` should be RETARGETED to that parser, not deleted.
- Consequence: If the implementer follows §4.1 literally, the project loses the only coverage of
  consumer-side cross-backend dispatch agnosticism (Shape 1 / Shape 2 producing identical output on
  Python vs Rust CST). The kept config-2 tests (`test_rust_parser_parity_*`) check structural
  parity by `.start`/`.end`, not the consumer match/case dispatch pattern — so the regression is
  real and lands squarely on the central requirement. The design should explicitly direct
  retargeting `_rust_cst_grammar` to `fegen_rust_cst.parser.Parser` (drop the hybrid
  `generate_parser(rust_cst_module=...)` call, keep the dispatch assertions).
- Note: the parametrized-both class `TestAC7BothBackends` (tests/test_phase4_rust_fixture.py:581,
  consumes both `_python_pr` and `_rust_pr`) is the same shape but IS covered by this file's §4.1
  retarget clause ("construct phase4_roundtrip_cst.cst nodes directly"); only the
  clean_protocol_consumer_api dispatch tests lack that clause.

## design-2 — `_fegen_grammar_cache` left dangling after `_load_fegen_grammar` deletion

- Section: §2.3 ("Delete the now-dead support code: ... `_fegen_rust_parser_cache` (`:44`), and
  `_load_fegen_grammar` (`:47-67`) ... Remove the now-unused `importlib` import").
- What's wrong: §2.3 enumerates the dead symbols to delete but omits `_fegen_grammar_cache`
  (plumbing.py:38). Grep confirms its only references are at plumbing.py:38,53,66,67 — all inside
  `_load_fegen_grammar`, which §2.3 deletes. After the deletion it is an orphaned module-level
  variable.
- Why: The design's stated intent is to "Delete the now-dead support code"; leaving
  `_fegen_grammar_cache` contradicts that and is inconsistent with the same paragraph's removal of
  `_fegen_rust_parser_cache` and the `importlib` import for identical "now-unused" reasons.
- Consequence: Dead module-level state remains in plumbing.py. Ruff's unused-binding rules (F841)
  do not cover module-level globals, so `make check` will NOT catch it — it survives as silent
  cruft contradicting the design's own cleanup goal. Low blast radius; add `_fegen_grammar_cache`
  (`:38`) to the §2.3 deletion list.
