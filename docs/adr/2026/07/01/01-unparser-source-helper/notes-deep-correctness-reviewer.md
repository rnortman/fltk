# Deep correctness review — unparser-source-helper

Reviewed: 007401e..f07852a (HEAD f07852a5ebb26c6c3534be0457f07ac5f13b4041)

No findings.

Verified traces:
- `generate_unparser` refactor is behavior-preserving: `_assemble_unparser_module` runs the
  identical pipeline (context, `formatter_config or FormatterConfig()` coalescing, trivia
  add/classify, `gsm2unparser.generate_unparser`, `compile_class`, `ast.Module` +
  `fix_missing_locations`, `ast.unparse`) and `generate_unparser` execs exactly that string;
  `UnparserResult` fields (grammar_with_trivia, coalesced config, `trivia_config` fallback) are
  built from the same values as before.
- Test helper in `fltk/unparse/test_is_span_guard.py` passes the already-trivia-processed
  `parser_result.grammar`; re-application inside the helper is idempotent
  (`fltk/fegen/gsm.py:480-481` early-return; `classify_trivia_rules` re-derives identical flags)
  and matches the pre-existing production call pattern. Config divergence (explicit
  `FormatterConfig()` vs `None`) collapses to the same coalesced value.
- Imports in the rewritten test file: `ast`, `terminalsrc`, `pyrt`, `importlib`, `pytest` all
  still used; removed imports are all dead. `sys.modules.pop` cleanup retained in `finally`.
- New `fltk/test_plumbing.py` tests: `cst_module_name` comes from the same grammar object
  registered in `sys.modules` by `generate_parser`, so the exec'd source's CST import resolves;
  exec with empty globals mirrors `generate_unparser`'s own exec semantics.
