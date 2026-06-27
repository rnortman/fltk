test-1: `test_empty_alternative_body_is_passthrough` does not assert `_node` in the empty-alt method signature.

- File:line: `tests/test_rust_unparser_generator.py:419`
- What's wrong: Production code at `fltk/unparse/gsm2unparser_rs.py:366` added `node_param = "node" if alt.items else "_node"` so degenerate empty-alternative methods emit `_node` in their parameter list. The test only checks body content (`Some(UnparseResult::new(acc, pos))`, absence of `let mut pos/acc`) — it does not assert that `_node` appears in the method signature string that `_gen_alternative_body` returns.
- Consequence: If the `"node" if alt.items else "_node"` conditional is removed or inverted, the Python test still passes. The regression would surface only during a Rust `-D warnings` / clippy build on grammars that have an empty alternative.
- Fix: Add `assert "_node: &cst::R" in body` (or the equivalent class-name-agnostic check `"(_node:" in body`) to `test_empty_alternative_body_is_passthrough`.

---

test-2: Quantified INLINE-literal inner method's `_node` parameter has no test.

- File:line: `fltk/unparse/gsm2unparser_rs.py:744-748` (production call site); no coverage in `tests/test_rust_unparser_generator.py`
- What's wrong: `_gen_inner_method` calls `self._node_param(body)` at line 746 before constructing the inner method signature. The comment at line 744 explicitly names the reachable case: an INLINE (`!`) literal with a multiple quantifier (`+`/`*`) produces a term body that never reads `node` → `_node_param` returns `"_node"`. All existing inner-method tests (`test_quantified_loop_emits_inner_method_with_literal_term_body`, `test_quantified_identifier_inner_recurses_into_ref_rule`, etc.) use grammars where the inner body reads `node.children()` via a labeled INCLUDE item, so `_node_param` always returns `"node"` in those tests. The INLINE + quantified path — reachable with e.g. `r := !"x"+;` — goes untested.
- Consequence: Removing `_node_param` from `_gen_inner_method` and hardcoding `"node"` produces Rust with an unused-variable error for INLINE + quantified items under `-D warnings`. No Python test catches this; only a Rust compilation step would.
- Fix: Add a test using `RustUnparserGenerator(parse_grammar('r := !"x"+;')).generate()`, extract the `unparse_r__alt0__item0__inner` method body via `_method_body(src, ...)`, and assert the signature line contains `_node: &cst::R` (not `node: &cst::R`).
