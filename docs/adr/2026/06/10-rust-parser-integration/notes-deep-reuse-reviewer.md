## Reuse review — commit f1423a2

**reuse-1**

File: `tests/test_phase4_fegen_rust_backend.py:253-261` (`_assert_rust_parser_equals_python`)

What's duplicated: The new helper performs `Parser(text, capture_trivia=False)` → `apply__parse_grammar(0)` → result-not-None/pos==len(text) guard → `Cst2Gsm(text).visit_grammar(result.result)`. `plumbing.parse_grammar` (plumbing.py:113-175) implements exactly this three-step composition for both the Python and Rust-CST paths. The Rust path (plumbing.py:155-175) does the same guard, the same `Cst2Gsm(terminals.terminals)`, and the same `visit_grammar` call.

Existing function: `plumbing.parse_grammar` at `fltk/plumbing.py:113`. The new test class also already imports `parse_grammar` (line 40) and calls it as the reference path (line 260). `parse_grammar(text, rust_fegen_cst_module="fegen_rust_cst")` is precisely the Rust-parser→Rust-CST→Cst2Gsm path the new class is testing — which is why `TestAC8RealCst2GsmRustBackend.test_simple_grammar_rust_equals_python` (line 68-72) and the three new tests are structurally the same test at different input scope.

Consequence: `_assert_rust_parser_equals_python` hand-rolls the three-layer composition that `plumbing.parse_grammar` already encapsulates. If `parse_grammar`'s error-handling logic, the `Cst2Gsm` constructor signature, or the `visit_grammar` call site evolve, the hand-rolled copy diverges silently. The new tests would also suppress the `parser.error_message()` diagnostic that `plumbing.py` formats through `errors.format_error_message` (the richer error path), substituting a raw `parser.error_message()` string. Simplification: call `parse_grammar(text, rust_fegen_cst_module="fegen_rust_cst")` as the Rust result and `parse_grammar(text)` as the Python result, collapsing the helper to two calls and an `assert ==` — identical to `TestAC8RealCst2GsmRustBackend`.

Note: the design doc explicitly distinguishes these tests as exercising `fegen_rust_cst.Parser` *directly* rather than via `plumbing.parse_grammar`, which is a valid goal (testing a different composition). But the chosen implementation constructs that composition by hand rather than testing that `parse_grammar` uses it, creating a maintained duplicate rather than an intentional bypass.

---

No other findings.
