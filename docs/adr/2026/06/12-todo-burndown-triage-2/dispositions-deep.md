Concise. Precise. Complete. Unambiguous. Audience: smart LLM/human.

errhandling: No findings.

correctness: No findings.

security: No findings.

test-1:
- Disposition: Fixed
- Action: Added `plumbing.parse_text(parser_result, "hello", rule_name="root")` and assertion to `test_plumbing_generate_parser_with_underscore_foo_rule` in `fltk/fegen/test_name_validation.py:300-308`.
- Severity assessment: Without parse_text, a regression producing a broken parser for `_foo`-named rules would not be caught by this test.

test-2:
- Disposition: Fixed
- Action: Added `test_rule_named_empty_string_raises` at `fltk/fegen/test_name_validation.py:65-76` — builds Grammar with `rule.name = ""`, asserts `ValueError` with "underscore" in message.
- Severity assessment: If `snake_to_upper_camel` were changed to return a fallback for `""`, the empty-string rejection would silently disappear.

test-3:
- Disposition: Fixed
- Action: Added `test_plumbing_rejects_label_underscore` at `fltk/fegen/test_name_validation.py:344-356` — calls `plumbing.generate_parser` with grammar `x := _:/[a-z]+/ ;`, asserts `ValueError` matching `r"underscore"`.
- Severity assessment: A bypass of `classify_trivia_rules` for the label case in a future refactor would not be caught by the plumbing-level suite.

test-4:
- Disposition: Fixed
- Action: Added `assert "label" in msg.lower()` and `assert "underscore" in msg.lower()` to `test_top_level_label_underscore_raises` (line 92) and `test_nested_label_underscore_raises` (line 145) in `fltk/fegen/test_name_validation.py`.
- Severity assessment: Without these, the label error message could degrade to the rule-name template (mentioning "type names" instead of "accessor names") without test failure.

reuse-1:
- Disposition: Fixed
- Action: Extracted `_for_each_item(items, visitor)` at `fltk/fegen/gsm.py` (before `_collect_underscore_only_label_errors`); refactored both `_collect_underscore_only_label_errors` and `_collect_repeated_nil_errors` to delegate traversal to `_for_each_item`; removed `TODO(gsm-item-walker)` comment and `TODO.md` entry. Added `Callable` to `collections.abc` imports. All 1654 tests pass.
- Severity assessment: The second instance of the traversal skeleton was introduced by this iteration itself; deferral was wrong given Q2 failure (refactor was fully mechanical with no design questions outstanding).
