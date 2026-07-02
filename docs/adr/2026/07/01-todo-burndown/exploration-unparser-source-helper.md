# Exploration: TODO(unparser-source-helper)

Base commit: 8fd5ecf.

## TODO marker locations

- Code comment: `fltk/unparse/test_is_span_guard.py:62-66` (single occurrence in code).
- Master list entry: `TODO.md:81-83`.
- Historical references (pre-existing, from the prior review chain that produced this TODO, not new occurrences to burn down): `docs/adr/2026/06/26-pure-python-span-native-probe/judge-verdict-deep.md:15,76`, `docs/adr/2026/06/26-pure-python-span-native-probe/dispositions-deep.md:114-115`.

No other `TODO(unparser-source-helper)` comments exist anywhere in the tree (checked with a recursive grep over `*.py`/`*.md`).

Note: a stray, git-untracked directory `.claude/worktrees/agent-ab295be24eef6e7ce/` contains a full duplicate checkout of the repo (leftover from an earlier agent run) and shows up in naive greps for `generate_unparser`. It is not part of the tracked source tree (`git ls-files .claude/worktrees` returns nothing) and is not a real second call site.

## Does the duplication exist as described?

Yes. Side-by-side comparison of the two assembly sequences:

`fltk/plumbing.py:257-299` (`generate_unparser`):
1. `context = create_default_context(capture_trivia=True)` (line 275)
2. `formatter_config = formatter_config or FormatterConfig()` (line 276)
3. `grammar_with_trivia = gsm.add_trivia_rule_to_grammar(grammar, context)` (line 278)
4. `grammar_with_trivia = gsm.classify_trivia_rules(grammar_with_trivia)` (line 279)
5. `gsm2unparser.generate_unparser(grammar_with_trivia, context, cst_module_name, formatter_config=formatter_config)` (lines 281-286)
6. `compiler.compile_class(unparser_class, context)` (line 288)
7. `ast.fix_missing_locations(ast.Module(body=[*imports, unparser_ast], type_ignores=[]))` (line 289)
8. `exec(ast.unparse(module), exec_globals)` (line 292) — then builds `UnparserResult` (lines 294-299)

`fltk/unparse/test_is_span_guard.py:56-84` (`_generate_unparser_source`):
1. `parse_grammar_file(grammar_path)` + `generate_parser(grammar, capture_trivia=True)` (lines 68-69) — not present in plumbing's pipeline; needed because the test starts from a grammar file path and needs a `cst_module_name`.
2. `context = create_default_context(capture_trivia=True)` (line 71)
3. `grammar_with_trivia = gsm.add_trivia_rule_to_grammar(parser_result.grammar, context)` (line 72)
4. `grammar_with_trivia = gsm.classify_trivia_rules(grammar_with_trivia)` (line 73)
5. `gsm2unparser.generate_unparser(grammar_with_trivia, context, parser_result.cst_module_name, formatter_config=FormatterConfig())` (lines 74-79)
6. `compiler.compile_class(unparser_class, context)` (line 80)
7. `ast.fix_missing_locations(ast.Module(body=[*imports, unparser_ast], type_ignores=[]))` (line 81)
8. `return ast.unparse(module)` (line 82) — no exec, no `UnparserResult`

Steps 2-7 in the test helper are a line-for-line re-implementation of `plumbing.generate_unparser`'s steps 1,3-7 (the "7-step assembly pipeline" named in the TODO: `create_default_context` → `add_trivia_rule_to_grammar` → `classify_trivia_rules` → `gsm2unparser.generate_unparser` → `compiler.compile_class` → `ast.Module` assembly → `ast.unparse`). The only structural difference is the final step (`ast.unparse` returned as a string vs. `exec`'d into a class + wrapped in `UnparserResult`), which is exactly the seam the TODO proposes to expose.

Confirmed call count: `_generate_unparser_source` is called at lines 91, 95, 112 (via `self._module()` at line 111, itself called from `test_future_annotations_is_first_statement` line 115, `test_no_module_top_level_span_protocol_import` line 122, `test_span_protocol_import_under_type_checking` line 141), and 133 — 4 direct call sites (91, 95, 133, and the shared `_module()` helper at 111-112 which is itself called 3x). So "called 4x" in the TODO refers to 4 distinct call expressions of `_generate_unparser_source` in the file (lines 91, 95, 112, 133), consistent with the file content.

## Has drift already occurred?

One difference beyond the described seam: `plumbing.generate_unparser` accepts `grammar` directly and applies `add_trivia_rule_to_grammar`/`classify_trivia_rules` to it once (`fltk/plumbing.py:278-279`). The test helper instead first calls `generate_parser(grammar, capture_trivia=True)` (`fltk/unparse/test_is_span_guard.py:69`), which internally already runs `add_trivia_rule_to_grammar`/`classify_trivia_rules` on the grammar (`fltk/plumbing.py:105-107`, inside `generate_parser`), and then the test helper applies both functions *again* to `parser_result.grammar` (lines 72-73) — i.e., the pair runs twice for the test helper's path vs. once for `plumbing.generate_unparser`'s path.

This was checked for behavioral impact: `gsm.add_trivia_rule_to_grammar` (`fltk/fegen/gsm.py:477-504`) guards on `TRIVIA_RULE_NAME in grammar.identifiers` (lines 480-481) and returns the input grammar unchanged if a trivia rule already exists, and `gsm.classify_trivia_rules` (`fltk/fegen/gsm.py:348-379`) recomputes `is_trivia_rule` purely from current rule-reachability from `_trivia_` (lines 356-369), not from any prior classification state — so it is a pure/idempotent function of the current grammar structure, not of history. Re-running the pair a second time is confirmed to be a no-op producing an identical grammar (also noted in existing code comments, e.g. `fltk/unparse/gsm2tree_rs.py:233`: "`add_trivia_rule_to_grammar` is idempotent when present"). So this is redundant work in the test helper, not an observable drift/bug — the two pipelines' results agree functionally today, even though the test helper's call sequence isn't a literal 1:1 mirror of plumbing's (it additionally routes through `generate_parser` first, which the TODO's "mirrors ... up to ast.unparse" docstring comment at line 59 doesn't fully capture).

Also note: `plumbing.generate_unparser`'s `formatter_config = formatter_config or FormatterConfig()` null-coalescing step (line 276) is inlined away in the test helper by always passing `formatter_config=FormatterConfig()` directly (line 78) — functionally equivalent for the test's purposes (it never passes `None`), but it means the test helper doesn't exercise/mirror that specific line; a future change to that null-coalescing logic (e.g., validation added there) would not be reflected by the test helper.

## Public-surface impact of the proposed refactor

`fltk/plumbing.py` is FLTK's documented out-of-tree consumer entry point: `README.md:20` shows `from fltk.plumbing import parse_grammar, generate_parser, parse_text` as the canonical usage example, and the module docstring (`fltk/plumbing.py:1-6`) describes it as "the essential plumbing that connects all the pieces." `plumbing.py` has no `__all__` restricting its exports.

The TODO's proposed shape — add a new function `plumbing.generate_unparser_source(grammar, cst_module_name, formatter_config)` returning unparsed source, and have the existing `generate_unparser` call it internally then `exec` the result — is additive only:
- `generate_unparser`'s existing signature (`grammar, cst_module_name, formatter_config=None`) and return type (`UnparserResult`) are unchanged per the TODO's own description ("with `generate_unparser` exec'ing its output").
- No existing symbol is renamed or removed.
- This matches the CLAUDE.md guidance that additive, non-breaking changes to `fltk.plumbing.py` are the safe category; nothing here forces downstream annotation or call-site churn as long as `generate_unparser`'s public contract is preserved verbatim in the refactor (this exploration does not verify a proposed implementation, since none exists yet — it only confirms the TODO's stated shape is additive).

## Summary of facts

- Duplication as described: confirmed, `fltk/plumbing.py:275-292` vs. `fltk/unparse/test_is_span_guard.py:68-82`.
- Drift status: no behavioral drift yet; one harmless redundancy (double application of idempotent trivia steps via `generate_parser` + explicit re-application) and one inlined default (`formatter_config=FormatterConfig()` vs. `formatter_config or FormatterConfig()`) exist between the two paths today, both non-observable in current test outcomes.
- Call count "4x" in TODO.md/comment: verified against the 4 call expressions in `fltk/unparse/test_is_span_guard.py` (lines 91, 95, 112, 133).
- Public API risk: `fltk.plumbing` is the documented consumer-facing module (`README.md:20`); proposed change is purely additive (new function; `generate_unparser`'s existing signature/behavior preserved), so it does not fall into the CLAUDE.md-flagged breaking-change categories (symbol rename, annotation-surface churn) as described.
