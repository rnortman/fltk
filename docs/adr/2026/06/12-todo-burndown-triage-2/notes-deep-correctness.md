# Deep correctness review — empty-cn-underscore-rule (a48f820..7999f88)

No findings.

Verified:
- Predicate `snake_to_upper_camel(name) == ""` fires exactly for zero-`[a-z0-9]` names (incl. `""`); `_foo`/`_trivia`/`foo_`/`a__b` derive non-empty CNs and pass.
- `isinstance(item.term, Sequence)` recursion is safe: all non-sub-expression Term variants (Identifier/Literal/Regex/Invocation) are slotted dataclasses, not `collections.abc.Sequence`; plain `str` never appears as a term. Pattern identical to existing `_collect_repeated_nil_errors` / `_mark_trivia_reachable_in_items`.
- Validator placement in `classify_trivia_rules` (gsm.py:344) precedes the trivia-less early return (gsm.py:346-348), so trivia-less grammars are checked.
- All pipeline entry points reach the validator: `plumbing.generate_parser` (plumbing.py:239), `plumbing.generate_unparser` (plumbing.py:410), `RustCstGenerator.__init__` (gsm2tree_rs.py, classify call before its identifier/collision loops — the updated `_IDENTIFIER_RE` comment's "fires before this loop" claim is accurate).
- No import cycle: `naming` is a leaf module; `fltk/fegen/__init__.py` is empty.
- `fltk/fegen` test subset (145 tests) and the new `test_name_validation.py` (15 tests) pass.
