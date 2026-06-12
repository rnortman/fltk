Concise. Precise. Complete. Unambiguous. Audience: smart LLM/human.

Commit reviewed: 7999f88

## test-1

File: `fltk/fegen/test_name_validation.py` (no dedicated test)

**What's missing**: Design test plan item 8 — "Rule `_foo` referenced from another rule: `generate_parser` + `parse_text` succeed." The test `test_plumbing_generate_parser_with_underscore_foo_rule` calls `plumbing.generate_parser` but never exercises `parse_text`. The design explicitly required end-to-end parse to confirm the generated parser actually works when the rule name has a leading underscore. The test catches generation failure but not a broken generated parser.

**Consequence**: A regression that generates a parser for `_foo`-named rules but produces malformed parse logic would not be caught — `generate_parser` succeeds but parsing always fails or crashes.

**Fix**: After `plumbing.generate_parser(result)`, exec the returned module and call `parse_text` on a matching input. The existing integration tests in `test_gsm2tree.py` or `test_plumbing.py` show the pattern.

---

## test-2

File: `fltk/fegen/test_name_validation.py` (no test)

**What's missing**: Design edge case "Empty-string name from programmatic GSM construction" — `_make_simple_grammar("")` followed by `validate_no_underscore_only_names`. The design calls this out as a predicate property that must hold, not just an incidental behavior. `naming.snake_to_upper_camel("") == ""` is confirmed true (verified empirically above), so the validator does reject it, but no test pins that behavior.

**Consequence**: If `naming.snake_to_upper_camel` is ever changed so that `""` maps to some fallback non-empty string (a plausible defensive change), the empty-string rejection silently disappears with no test failure.

**Fix**: Add `test_rule_named_empty_string_raises` that builds a `Grammar` with `rule.name = ""`, calls `validate_no_underscore_only_names`, and asserts `ValueError`.

---

## test-3

File: `fltk/fegen/test_name_validation.py` (no test)

**What's missing**: Design test plan item 3 says "grammar `x := _:/[a-z]+/ ;` raises `ValueError` naming rule `x` and label `_`." The unit-level test `test_top_level_label_underscore_raises` covers this via direct `gsm.validate_no_underscore_only_names`. But there is no plumbing-level integration test verifying that `plumbing.generate_parser` raises for a label `_` (analogous to the two plumbing-level tests for rule names). The design calls out that label `_` "currently works end-to-end on the Python backend" — a plumbing-level test would lock that the chokepoint actually fires on this formerly-working path.

**Consequence**: A bypass of `classify_trivia_rules` for the label case (e.g., a future refactor of `add_trivia_rule_to_grammar` that skips classification) would not be caught by the plumbing-level test suite.

**Fix**: Add `test_plumbing_rejects_label_underscore` that calls `plumbing.generate_parser(plumbing.parse_grammar("x := _:/[a-z]+/ ;"))` and asserts `ValueError` with match `r"underscore"`.

---

## test-4

File: `fltk/fegen/test_name_validation.py` (no test)

**What's missing**: `test_top_level_label_underscore_raises` asserts `"'_'" in msg` and `"x" in msg`, but does NOT assert that the message contains the word "label" or "underscore". The rule-name error message tests (`test_rule_named_single_underscore_raises`) do assert `"underscore" in str(exc_info.value).lower()`. For the label case the message content is tested less thoroughly — only that the label literal and rule name appear. If the error message were accidentally swapped to the rule-name template (mentioning "type names" rather than "accessor names"), the test would still pass.

**Consequence**: Cosmetic regression: error message for bad labels could silently degrade to an incorrect/misleading text without test failure.

**Fix**: Add `assert "label" in msg.lower()` and `assert "underscore" in msg.lower()` to `test_top_level_label_underscore_raises` and `test_nested_label_underscore_raises`.
