## quality-1

**File:line**: `fltk/unparse/gsm2unparser_rs.py:1365`

**Issue**: `_gen_has_preservable_trivia_method` calls `self._cst._child_variants_for_rule(gsm.TRIVIA_RULE_NAME)` — reaching directly into a private method of `RustCstGenerator`. The naming convention (leading underscore) marks it private; the module-level comment on `num_child_variants` explicitly describes that method as the public accessor for callers needing size information from `_child_variants_for_rule`. The unparser generator now bypasses that boundary to get the names list.

**Consequence**: The abstraction boundary between `RustUnparserGenerator` and `RustCstGenerator` is now porous at this site. Any refactoring of `_child_variants_for_rule` in `gsm2tree_rs.py` — signature change, merge into another helper, split — silently breaks the unparser generator with no compiler or linter signal. The pattern will propagate: the next call site needing class-name filtering will reach for `_child_variants_for_rule` again rather than looking for a public API.

**Fix**: Add a public `child_class_names_for_rule(rule_name: str) -> list[str]` method to `RustCstGenerator`, returning the first element of `_child_variants_for_rule(rule_name)` — a thin wrapper parallel to `num_child_variants`. Replace the private call in `_gen_has_preservable_trivia_method` with `self._cst.child_class_names_for_rule(gsm.TRIVIA_RULE_NAME)`.

---

## quality-2

**File:line**: `fltk/unparse/gsm2unparser_rs.py:1111–1113` and `1226–1228`

**Issue**: The `preserve_blanks` extraction is copy-pasted verbatim into both `_gen_trivia_rule_processing` and `_gen_non_trivia_rule_processing`:

```python
preserve_blanks = 0
if self._formatter_config.trivia_config:
    preserve_blanks = self._formatter_config.trivia_config.preserve_blanks
```

**Consequence**: A future change to how `preserve_blanks` is resolved — e.g., if `trivia_config` gains a rule-aware override, or the sentinel value changes — must be applied to both copies. The copies are separated by ~100 lines of code and doc strings, making silent divergence likely. Both branches port the same Python value read (`:1168`/`:1341`), so they should always agree.

**Fix**: Extract `def _get_preserve_blanks(self) -> int: return self._formatter_config.trivia_config.preserve_blanks if self._formatter_config.trivia_config else 0` and call it from both methods.

---

Commit reviewed: 1fcae0bbe0063b83b1883eb439ababc9da6916d4
