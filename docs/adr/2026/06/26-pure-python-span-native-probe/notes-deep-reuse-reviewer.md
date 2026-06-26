# Reuse review notes — pure-python-span-native-probe
# Commit reviewed: ab38ec777920f4761f124e56b3cedc995acee46a

## reuse-1

**File:line**: `tests/test_python_parser_span_backend.py:23-41`

**What's duplicated**: `_make_word_grammar()` builds a single-rule grammar with one labeled
regex terminal, INCLUDE disposition, and NO_WS separator.  This is structurally identical to
`_make_regex_grammar(pattern)` in `tests/test_regex_portability.py:47-65`.  The only
differences are trivial: rule name (`"doc"` vs `"word"`), label name (`"word"` vs `"value"`),
and pattern (`r"[a-z]+"` hardcoded vs parameterised).  The new function could be replaced by
calling `_make_regex_grammar(r"[a-z]+")` after either generalising the existing helper to
accept an optional rule/label name, or by accepting the minor naming difference.

**Existing function**: `_make_regex_grammar(pattern: str) -> gsm.Grammar` —
`tests/test_regex_portability.py:47-65`.

**Consequence**: Any change to `gsm.Rule`, `gsm.Items`, `gsm.Item`, `gsm.Disposition`, or
`gsm.Separator` (field names, constructor signatures, renamed enum values) requires independent
updates to both copies.  Because they live in separate test files with no shared import, one
will silently drift if the other is updated.

---

## reuse-2

**File:line**: `fltk/unparse/test_is_span_guard.py:56-78`

**What's duplicated**: `_generate_unparser_source()` manually re-implements the unparser
generation pipeline that `plumbing.generate_unparser()` already performs
(`fltk/plumbing.py:275-289`).  The seven steps — `create_default_context`,
`add_trivia_rule_to_grammar`, `classify_trivia_rules`, `gsm2unparser.generate_unparser`,
`compiler.compile_class`, `ast.Module` assembly, `ast.unparse` — are in exactly the same order
and with the same arguments.  The only difference is that the test helper stops at `ast.unparse`
(returns the source string) rather than calling `exec()`.  The function's own docstring confirms
the relationship: "Mirrors plumbing.generate_unparser up to ast.unparse, without exec'ing."
`plumbing.generate_unparser` offers no way to retrieve the generated source before execution,
so the test was forced to re-implement the pipeline rather than call the higher-level entry
point.

**Existing function**: `plumbing.generate_unparser(grammar, cst_module_name, formatter_config)`
— `fltk/plumbing.py:257-299`.

**Consequence**: If the unparser pipeline changes — new imports added to the assembly list,
trivia-processing steps reordered, or the compilation call modified — both
`plumbing.generate_unparser` and `_generate_unparser_source` must be updated independently.
The helper is called four times in the same file (lines 85, 89, 106, 127), so every invocation
carries the drift risk.  Exposing a `dry_run=True` / `return_source=True` flag on
`plumbing.generate_unparser`, or a separate `plumbing.generate_unparser_source()` helper, would
eliminate the duplication.
