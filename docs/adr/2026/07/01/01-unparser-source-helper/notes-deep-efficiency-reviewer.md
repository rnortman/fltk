# Deep efficiency review — unparser-source-helper

Commit reviewed: f07852a5ebb26c6c3534be0457f07ac5f13b4041 (base 007401edf41e4950929b01966d276450b1aead9b)

No findings.

Notes:
- Pure refactor of the codegen assembly pipeline (`fltk/plumbing.py`), invoked once per grammar
  generation — not a startup/per-request/per-render hot path. No scaling concern.
- `ast.unparse(module)` still runs exactly once. `_assemble_unparser_module` returns the source,
  the trivia-classified grammar, and coalesced `formatter_config`, so `generate_unparser` reuses
  them for `UnparserResult` rather than re-running trivia steps or re-unparsing. No new redundant
  work, no duplicated pipeline.
- No new blocking work, no unbounded structures, no listener/loop concerns. Test additions
  (`fltk/test_plumbing.py`) exec generated source once each — expected for the contract being pinned.
