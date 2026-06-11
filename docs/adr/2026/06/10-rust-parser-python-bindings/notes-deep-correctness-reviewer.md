# Correctness review — Phase 3 Python bindings + parity (b668897..b107645)

Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Verified clean: `check_pos` types and units (TerminalSource::len() returns i64 codepoint count, matching Python `len(text)` — no byte/codepoint confusion, no i64/usize mismatch); `use super::cst` inside `python_bindings` resolves via the parser module's private import binding (visible to child modules); per-rule bindings cover every rule including `_trivia` in both regenerated artifacts; rule-id renumbering after grammar extension is consistent (`_trivia` 15→18, RULE_NAMES updated); `assert_cst_equal` recursion, species discrimination, and `_parse_error_message` grouping match the actual `format_error_message` formats on both backends (group headers indented 2, token lines indented 4); `assert_error_equiv` `-1`⇔`None` mapping is correct; `_assert_messages_equiv` arg unpacking order is correct.

## correctness-1

- **File:line**: `tests/test_rust_parser_parity_fixture.py:126-133` (PARTIAL branch of `test_parity`)
- **What's wrong**: The branch has no exhaustive else. Structure:
  ```python
  elif isinstance(expected, PARTIAL):
      if expected.pos == 0 and py_result is None:
          assert rust_result is None
      elif py_result is not None:
          ... asserts ...
  ```
  When `py_result is None` and `expected.pos != 0`, neither arm asserts anything — the test passes vacuously. The branch also never asserts `py_result is not None` for a PARTIAL expectation.
- **Why**: Trace: `expected = PARTIAL(5)` (the only PARTIAL entry, `("expr", "1+2+3 ", PARTIAL(5))`). If a regression makes the Python parser return `None`, `expected.pos == 0` is False → first arm skipped; `py_result is not None` is False → second arm skipped; function falls through and pytest records a pass. Same outcome when Python returns `None` and Rust returns a result — exactly the cross-backend disagreement the suite exists to catch.
- **Consequence**: Violates the design invariant (design.md §2.4: "An entry where the backends *disagree on outcome* always fails — the expectation flag prevents a both-backends-broken corpus from passing vacuously"). A Python-side regression, a Rust-side regression returning Some where Python returns None, or both backends returning None on a PARTIAL entry all produce green tests. The PARTIAL(0)+None special case additionally treats PARTIAL(0) as "both fail", which is a FAIL semantics leak into PARTIAL.
- **Suggested fix**: Make PARTIAL strict, mirroring SUCCESS: `assert py_result is not None; assert rust_result is not None; assert py_result.pos == expected.pos; assert rust_result.pos == expected.pos; assert_cst_equal(...)`. If a "both fail" expectation is needed, that is FAIL, not PARTIAL(0).

## correctness-2

- **File:line**: `tests/test_rust_parser_parity_fegen.py:115-118` and `tests/test_rust_parser_parity_fixture.py:134-137` (FAIL branch of `test_parity`)
- **What's wrong**: The FAIL branch asserts each backend independently did not fully succeed (`X is None or X.pos < len(text)`), then compares error trackers. It never asserts the backends agree on outcome: (a) Python returning `None` while Rust returns a partial result (or vice versa) passes both per-backend assertions; (b) both returning partial results at *different* positions also passes — `assert_error_equiv` compares farthest-failure positions, which can be equal while the returned `result.pos` values differ.
- **Why**: `assert py_result is None or py_result.pos < len(text)` and the Rust twin are satisfiable by any (None, partial), (partial, None), (partial@5, partial@12) combination. `assert_error_equiv` constrains only `error_tracker.longest_parse_len` / `error_position()` and the message, not the apply-result shape. Design.md §2.4 specifies FAIL as "both backends return falsy/None at top level" and states outcome disagreement must always fail; the implementation loosened it (necessarily — e.g. `('grammar', 'ok := "x" ;\nbad :=\n', FAIL)` partially succeeds at rule 1 on both backends) but dropped the agreement check in the process.
- **Consequence**: A generator drift where the Rust parser returns a partial parse and the Python parser returns `None` for the same input (or both partial at different stop positions) is not detected, provided the farthest-failure trackers coincide — which they typically do, since both record the same deepest terminal failure. This is precisely the drift class the parity suite is the contract against (controlling design §2.7).
- **Suggested fix**: In the FAIL branch add `assert (py_result is None) == (rust_result is None)`; when both are non-None, additionally `assert py_result.pos == rust_result.pos` and `assert_cst_equal(py_result.result, rust_result.result)` before `assert_error_equiv`.

## correctness-3

- **File:line**: `fltk/fegen/gsm2parser_rs.py:884-886` (emitted `register_classes`), interacting with the CST module's `register_classes` when both are wired into one `#[pymodule]` (`tests/rust_cst_fegen/src/lib.rs:21`, `tests/rust_parser_fixture/src/lib.rs:12-17`).
- **What's wrong**: The parser bindings register classes under the fixed Python names `"Parser"` and `"ApplyResult"` on the same module that already registers one class per grammar rule (plus `Span`/`SourceText`). A grammar containing a rule named `parser` or `apply_result` (both valid rule names) generates a CST class named `Parser`/`ApplyResult`; `module.add_class` is attribute assignment, so the second registration silently shadows the first (registration order in both lib.rs files: cst first, parser bindings last → the pyclass `Parser` wins and the CST node class becomes unreachable as a module attribute). No generator-side validation rejects or even warns about the collision. Same pre-existing hazard for rules named `span`/`source_text`; this change adds two new reserved-in-practice names without reserving them.
- **Why**: `_gen_python_bindings` emits the fixed names unconditionally; `RustCstGenerator` validates rule names as identifiers but has no reserved-name check (exploration's "no name collisions" claim was verified only for the fegen grammar). pyo3's `add_class` does not error on duplicate names.
- **Consequence**: For a downstream grammar with a rule named `parser` (plausible — fltk is a parser toolkit), the generated extension imports cleanly but `module.Parser` is the parser binding, not the CST node class; `isinstance(node, module.Parser)` checks and constructor access for that node class silently break. Invariant violated: every grammar rule's generated class is reachable as a public module attribute (CLAUDE.md: generated classes are public API for out-of-tree consumers).
- **Suggested fix**: In the generator (CST or parser side), reject grammars whose rule class names collide with the fixed registered names (`Parser`, `ApplyResult`, `Span`, `SourceText`) with an explicit generation-time error, or namespace the parser classes.

Commit reviewed: b107645 (base b668897).
