scope-1:
- Disposition: Fixed
- Action: Added `test_plumbing_rejects_rule_named_single_underscore` and `test_plumbing_rejects_rule_named_double_underscore` to `fltk/fegen/test_name_validation.py`. Both call `plumbing.generate_parser(plumbing.parse_grammar(...))` as the design specified and assert `ValueError` with `"underscore"` in the message.
- Severity assessment: Without these tests, a future refactor that introduced a bypass path in `generate_parser` (skipping `classify_trivia_rules`) would leave the plumbing integration silently uncovered while all existing tests continued to pass. Low probability but non-trivial consequence.

scope-2:
- Disposition: Fixed
- Action: Added `test_plumbing_capture_trivia_pipeline_passes` to `fltk/fegen/test_name_validation.py`. Calls `plumbing.generate_parser(grammar, capture_trivia=True)` and asserts no exception is raised, explicitly locking that the auto-added `_trivia` rule and its `content` label pass `validate_no_underscore_only_names`.
- Severity assessment: Without this test, accidental tightening of the validator (e.g. treating leading-underscore names as invalid) would break every grammar using trivia capture without any dedicated test catching it. The full-suite green check provides only incidental coverage.
