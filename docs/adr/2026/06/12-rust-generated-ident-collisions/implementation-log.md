## Increment 2 — implement cross-rule collision check + DropWorklistItem reserved name + TODO removal (commit 8c8cb05)

- `fltk/fegen/gsm2tree_rs.py:28-41`: Replaced TODO(rust-generated-ident-collisions) comment with INVARIANT note; added `DropWorklistItem` to `_RESERVED_CLASS_NAMES` (§1).
- `fltk/fegen/gsm2tree_rs.py:553-562`: Added `py_handle_name()` static helper alongside `child_enum_name` (§2).
- `fltk/fegen/gsm2tree_rs.py:742`: Updated `_node_block` to use `self.py_handle_name(class_name)` instead of inline f-string (§2).
- `fltk/fegen/gsm2tree_rs.py:104-151`: Cross-rule collision check in `__init__` — builds `claims` dict over all rules × four identifier families (label enum emitted-only), detects duplicates, raises single `ValueError` with all collisions sorted by identifier; auto-generated trivia annotation keyed on `gsm.TRIVIA_RULE_NAME not in grammar.identifiers` (§3).
- `TODO.md`: Removed `rust-generated-ident-collisions` entry (§4).
- `tests/test_gsm2tree_rs.py`: Minor lint/format fixes (line length, FBT001, formatting).
- All 10 new tests pass; full suite 1617 passed; `make check` clean.

## Increment 1 — failing tests for cross-rule collision check (TDD first) (commit 4dbcff6)

- `tests/test_gsm2tree_rs.py:1566-1584`: Extended `TestReservedClassNameRejection` parametrize with `("drop_worklist_item", "DropWorklistItem", "DropWorklistItem")`.
- `tests/test_gsm2tree_rs.py:1613-1897`: Added `_make_two_rule_grammar` helper and new `TestCrossRuleIdentifierCollisions` class with 9 tests:
  - `test_foo_and_foo_child_collide_on_foo_child` — foo+foo_child → FooChild collision
  - `test_foo_with_label_and_foo_label_collide_on_foo_label` — labeled foo+foo_label → FooLabel collision
  - `test_foo_and_py_foo_collide_on_py_foo` — foo+py_foo → PyFoo collision
  - `test_non_injective_cn_collision` — foo_bar+foo__bar → FooBar same-CN collision
  - `test_foo_without_label_and_foo_label_accepted` — unlabeled foo+foo_label → accepted (emitted-only positive)
  - `test_trivia_collision_annotates_auto_generated` — user rule 'trivia' collides with auto-_trivia; message must say "auto"
  - `test_user_defined_trivia_no_auto_annotation` — user-defined _trivia + trivia → no "auto" annotation
  - `test_multiple_collisions_reported_at_once` — foo+foo_child+bar+bar_child → single error with both FooChild and BarChild
  - `test_non_colliding_multi_rule_grammar_accepted` — alpha+beta → accepted
  - `test_prediction_vs_output_consistency` — drift guard: predicted identifiers appear in generate() output
- 8 of 10 new tests fail (not-yet-raised ValueError); 2 positive tests pass; 166 existing tests unaffected.
