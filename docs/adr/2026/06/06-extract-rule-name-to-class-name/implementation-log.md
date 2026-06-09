# Implementation Log: extract-rule-name-to-class-name

## Increment 1 — create naming.py with unit tests (commit 6b42d1d)

- fltk/fegen/naming.py: new leaf module; `snake_to_upper_camel(name: str) -> str` with full edge-case docstring; no FLTK imports.
- tests/test_naming.py: 11 tests covering basic, consecutive/leading/trailing `_` collapse, mid-segment digits, digit-leading segment, `.lower()` applied, empty string. All pass.

## Increment 2 — wire all four call sites to naming.snake_to_upper_camel (commit 8ddd61f)

- fltk/fegen/gsm2tree.py:10: `from fltk.fegen import gsm, naming`; line 47: `class_name_for_rule_node` delegates to `naming.snake_to_upper_camel`.
- fltk/fegen/gsm2tree_rs.py:11: `from fltk.fegen import gsm, naming`; lines 17-22: removed TODO block; line 25-27: `_rust_variant_name` delegates to `naming.snake_to_upper_camel` (gains `.lower()`, inert on all-lowercase grammar identifiers).
- fltk/unparse/gsm2unparser.py:10: `from fltk.fegen import gsm, naming`; line 635: `class_name_for_rule_node` delegates; line 1827: inline list-comp uses `naming.snake_to_upper_camel`.
- tests/test_naming.py:3: removed unused `import pytest` (ruff F401).
- TODO.md: removed `extract-rule-name-to-class-name` entry.
- All 936 tests pass; ruff + pyright clean; pre-commit checks pass.
