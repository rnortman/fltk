# Efficiency review — fltk-grammar-lsp dogfood LSP

Commit reviewed: 0e6b0c5096e6b8f7b0211da2f905143d49181aa3 (base 9473bf9)

Scope of diff: declarative spec files (`.fltklsp`/`.fltkfmt`), CLI wiring
(`grammar_cli.py`, `server_cli.py` refactor), VS Code extension, Bazel/packaging.
No changes to server request handling, engine, or any per-request/per-render/startup
hot path. The `serve` extraction in `server_cli.py` is a pure refactor with no behavior
change. `extension.js` uses lazy per-language client start (process count = distinct
fltk languages actually opened) — a good efficiency choice, not a problem.

## efficiency-1 (product code): No findings.

The new runtime product code (`grammar_cli.py`, `server_cli.serve`) is one-shot CLI
startup work: `resolve_paths` materializes each packaged file once via an `ExitStack`
held for the server lifetime; `serve` validates specs once before protocol I/O. Nothing
redundant, nothing added to a hot loop.

## efficiency-2 (test-lane, courtesy — not my lane, defer to test-reviewer)

- Snippet: `fltk/lsp/test_grammar_lsp.py:44-50` (`_format`) and `:138-153`
  (`test_formatting_roundtrip_on_real_files`).
- Problem: `_format` calls `plumbing.generate_parser` and `generate_unparser` (code
  generation — the expensive step) on every invocation. The round-trip test calls
  `_format` twice per sample file (once for `once`, once for the idempotence `twice`),
  and there are 3 sample files per language × 3 languages, so the parser/unparser is
  regenerated ~18 times even though grammar+cfg are identical within a language.
- Consequence: shows up only as test-suite wall time (codegen is not cheap); no
  production impact. Bites CI runtime, not users.
- Direction (optional): generate parser/unparser once per language (grammar+cfg are
  loaded once already at `:143-145`) and pass them into a format helper, rather than
  regenerating inside `_format` on each call. Purely a test-speed cleanup.
