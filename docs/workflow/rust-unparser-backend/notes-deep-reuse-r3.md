## reuse-1

**File:line:** `fltk/unparse/gsm2unparser_rs.py:139–141`

**What's duplicated:**

```python
def _class_name(self, rule_name: str) -> str:
    return self._cst._py_gen.class_name_for_rule_node(rule_name)
```

**Existing function/utility:** `RustCstGenerator.class_name_for_rule` at
`fltk/fegen/gsm2tree_rs.py:779` — a public method whose docstring explicitly
states "Public wrapper… lets callers compute derived identifier families without
reaching into `_py_gen` directly." The identical one-liner also exists as
`RustParserGenerator._class_name` at `fltk/fegen/gsm2parser_rs.py:229`
(pre-existing). Both the new method and the parser generator's copy bypass the
public wrapper and reach through `_cst._py_gen` directly.

**Consequence:** The delegation chain (`_cst._py_gen.class_name_for_rule_node`)
is now hardcoded in three places. If `class_name_for_rule_node` is renamed or
the `_py_gen` indirection is restructured inside `RustCstGenerator`, all three
callsites diverge independently. The public `class_name_for_rule` wrapper
already exists precisely to insulate callers from this internal path; the new
method ignores it.
