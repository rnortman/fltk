Style: concise, precise, complete, unambiguous. No padding, no preamble.

Commit reviewed: 4fe645d

---

test-1
File: tests/test_gsm2tree_rs.py:1302-1306
What: `test_parser_apply_result_rules_accepted` only asserts the generator constructs without error (`assert gen is not None`). Design §4 test plan item 2 specifies a stronger requirement: the generated cst source must contain `name = "Parser"` / `name = "ApplyResult"` pyclass handles (proving the rule's CST class is correctly emitted), and the generated parser source must still contain the fixed `name = "Parser"` / `name = "ApplyResult"` from the parser machinery (proving both coexist). Neither the cst source content nor the parser source content is inspected.
Consequence: A regression that silently renames or omits the generated pyclass handle for a `parser`/`apply_result` rule would pass this test. The compile-level proof in `TestCollisionFixture` catches the runtime endpoint but not the source-level contract (and requires a built artifact to run).
Fix: After constructing the generator, call `gen.generate()` and assert both `'name = "Parser"'` and `'name = "ApplyResult"'` appear in the cst source. Also generate from `RustParserGenerator` on the same grammar and assert the parser source still contains `'name = "Parser"'` from the fixed `ApplyResult` / `Parser` parser class. The `source_text` variant should similarly verify the cst source contains `'name = "SourceText"'` (to document positive case for a non-reserved name).

test-2
File: tests/test_module_split.py (§4.6 TestPocCstSubmodule)
What: `fltk._native.poc_cst` reachability is verified via top-level imports at module load time (`import fltk._native.poc_cst`, `from fltk._native.poc_cst import Identifier`) and attribute access on `fltk_native`. `sys.modules["fltk._native.poc_cst"]` is never checked. By contrast, §4.4 `TestImportMechanics` explicitly checks `sys.modules["fegen_rust_cst.cst"] is fegen_rust_cst.cst` and `sys.modules["fegen_rust_cst.parser"] is fegen_rust_cst.parser`. The `register_submodule` helper inserts the sys.modules key as a deliberate behavior; the poc_cst and fegen_cst submodules under `fltk._native` are not covered by any sys.modules assertion.
Consequence: A bug where `sys.modules["fltk._native.poc_cst"]` is absent or points to a different object (e.g. the key registered under a wrong path like `"_native.poc_cst"`) would not be caught. `import fltk._native.poc_cst` succeeds via attribute traversal even without a sys.modules entry, so the existing test does not exercise the sys.modules insertion at all.
Fix: Add `assert "fltk._native.poc_cst" in sys.modules` and `assert sys.modules["fltk._native.poc_cst"] is fltk._native.poc_cst` to `TestPocCstSubmodule`. Mirror for `fltk._native.fegen_cst`.

test-3
File: crates/fltk-cst-core/src/py_module.rs (unit tests, lines 101-136)
What: `user_facing_name` has four unit tests: double-nested stripped, different-segments unchanged, top-level (no dot) unchanged, triple-nested double-match ("a.b.b" → "a.b"). Missing: a three-distinct-segment case like `"fltk._native.sub"` (all three segments different, last two differ from each other), to verify the function returns the full string unchanged rather than incorrectly stripping. The `different_segments_unchanged` test only covers two segments (`"fltk._native"`); the function's behavior for three-different segments is untested.
Consequence: If `user_facing_name("fltk._native.sub")` were to incorrectly strip to `"fltk._native"`, the submodule would be registered as `"fltk._native.sub"` under the wrong parent key. This case does not arise in the current in-tree code (no three-segment parent module names are used), so the gap is latent.
Fix: Add `assert_eq!(user_facing_name("fltk._native.sub"), "fltk._native.sub");` to the `different_segments_unchanged` test or a new test case.

test-4
File: tests/test_module_split.py:109-124 (TestCollisionFixture::test_collision_fixture_parse_and_access_cst_node)
What: The test does `item_child.maybe_p()` and, if not None, asserts `isinstance(parser_child, cst_parser_cls)`. However, the input `"foo"` is a bare token that matches the `parser` rule (the regex `[a-z_]+` matches "foo"), so `maybe_p()` should return a node. The `if parser_child is not None:` guard means the assertion is only exercised conditionally — if the accessor returns None, the test passes vacuously. If the grammar or parser changes such that "foo" routes to the `apply_result` alternative instead, the test produces no signal.
Consequence: If `maybe_p()` silently returns None (e.g. due to a label name change or accessor regression), the `isinstance` check is skipped and no failure is reported.
Fix: Use `assert parser_child is not None, f"expected maybe_p() to return a Parser node for input 'foo'"` before the isinstance check, or use input that unambiguously routes to the `parser` rule (e.g. verify the grammar's alternative ordering and assert unconditionally).

test-5
File: tests/test_module_split.py (§4.6 TestPocCstSubmodule)
What: The test checks `Identifier` and `Items` classes are reachable at `fltk._native.poc_cst` and absent from `fltk._native` top level, but does not verify `fltk._native.poc_cst.NodeKind` is present. The PoC grammar has a `NodeKind` enum registered in the cst module; if registration were accidentally dropped (e.g. misrouted to top level), no test would detect it.
Consequence: A registration defect that drops `NodeKind` from `poc_cst` or misplaces it at the top level would be missed.
Fix: Add `assert hasattr(fltk._native.poc_cst, "NodeKind")` to `TestPocCstSubmodule`. This is low-cost and mirrors the `test_cst_has_node_kind` check in `TestImportMechanics`.
