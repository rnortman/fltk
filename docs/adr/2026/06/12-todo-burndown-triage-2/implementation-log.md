## Increment 1 — validate_no_underscore_only_names: tests + implementation (commit 680b58c)

- fltk/fegen/gsm.py:1: added `from fltk.fegen import naming` import.
- fltk/fegen/gsm.py:289-335: added `_collect_underscore_only_label_errors` (recursive helper) and `validate_no_underscore_only_names` (public validator); predicate is `naming.snake_to_upper_camel(name) == ""`.
- fltk/fegen/gsm.py:340-341: `classify_trivia_rules` now calls `validate_no_underscore_only_names(grammar)` as first line, before the `if not trivia_rule: return grammar` early return.
- fltk/fegen/gsm2tree_rs.py:17-22: deleted `TODO(empty-cn-underscore-rule)` comment block; replaced with note that underscore-only names are rejected upstream by `gsm.validate_no_underscore_only_names`.
- TODO.md: deleted `empty-cn-underscore-rule` entry.
- fltk/fegen/test_name_validation.py: 12 new tests (7 failing-first, 5 regression guards); all pass. Full suite: 1649 passed.
