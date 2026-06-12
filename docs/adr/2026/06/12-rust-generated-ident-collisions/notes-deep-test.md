Style: concise, precise, no padding, no preamble. Audience: smart LLM/human.

Commit reviewed: 4f66083

---

test-1
File: tests/test_gsm2tree_rs.py:1799
`test_prediction_vs_output_consistency` uses the inline formula `f"Py{cn}"` to predict the handle identifier, rather than `RustCstGenerator.py_handle_name(cn)`. The entire point of `py_handle_name` is to be a single source of truth so that a rename of the `Py{…}` prefix is caught immediately. The drift guard re-inlines the formula it is supposed to guard, so a future change to `py_handle_name`'s body that makes the helper diverge from `f"Py{…}"` will silently pass the test.
Consequence: the "formula drift" protection the design explicitly requires is hollow for the handle-name family; the helper could be changed to `f"Handle{class_name}"` and `test_prediction_vs_output_consistency` would still pass while the emitter used the old helper.
Fix: replace `py_handle = f"Py{cn}"` with `py_handle = RustCstGenerator.py_handle_name(cn)`.

---

test-2
File: tests/test_gsm2tree_rs.py — all collision error tests
No test asserts the family-description strings in the error message ("node struct", "Python handle struct", "child value enum", "label enum") or the "rename one of these rules" suffix. Every collision test checks only that the colliding identifier and the two rule names appear somewhere in the text. A bug that swaps family descriptions (e.g. reporting "child value enum for rule 'foo'" when the collision is on the struct) or omits the action hint would go undetected.
Consequence: error message quality regressions are uncaught; the actionability guarantee (the user knows which rule/family each claimant is) is untested.
Fix: at minimum, add one assertion per collision test that verifies the expected family description appears in the error and that the "rename" instruction is present. For `test_foo_and_foo_child_collide_on_foo_child`, assert "child value enum" and "node struct" both appear; for `test_foo_with_label_and_foo_label_collide_on_foo_label`, assert "label enum" appears; for `test_foo_and_py_foo_collide_on_py_foo`, assert "Python handle struct" appears. One test per family is sufficient.

---

test-3
File: tests/test_gsm2tree_rs.py — TestCrossRuleIdentifierCollisions (absent test)
The design's edge case "Three or more claimants on one identifier: all listed in the message" has no corresponding test. The production code uses a `" vs ".join(...)` over all claimants, but no test verifies that a three-way collision (e.g. three rules each producing `CN = FooBar` via non-injective snake_to_upper_camel: `foo_bar`, `foo__bar`, `foo___bar`) lists all three claimants.
Consequence: a regression that truncates to only the first two claimants (e.g. a `claimants[:2]` bug or an early-exit loop) is not caught.
Fix: add a test with three rules that share a CN (e.g. `foo_bar`, `foo__bar`, `foo___bar`) and assert all three rule names appear in the error text.

---

test-4
File: tests/test_gsm2tree_rs.py — TestCrossRuleIdentifierCollisions (absent test)
The trivia tests cover only the CN-level collision (`trivia` + auto-added `_trivia` → `Trivia`). No test covers a user rule whose CN collides with one of the _trivia rule's *derived* identifiers: `trivia_child` → `TriviaChild` (= `_trivia`'s child enum), `py_trivia` → `PyTrivia` (= `_trivia`'s handle), or `_trivia_label` → `TriviaLabel` (= `_trivia`'s label enum, if `_trivia` has labels). The auto-generated annotation path (`trivia_is_auto_added`) is therefore only exercised for the CN family; the annotation logic for the handle/child-enum/label-enum families is untested.
Consequence: a bug that annotates only the CN claim and not the handle/child-enum claims as auto-generated would not be detected.
Fix: add a test for `trivia_child` (single rule, no explicit `_trivia`) and assert the error names `TriviaChild`, `trivia_child`, and the auto-generated annotation for `_trivia`.
