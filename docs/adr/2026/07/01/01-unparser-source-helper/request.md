### 17. `unparser-source-helper` — DO

- **Problem:** a test file re-implements `plumbing.generate_unparser`'s 7-step assembly
  pipeline line-for-line because plumbing offers no way to get the generated source
  before it's `exec`'d. Any pipeline change must be mirrored in both places.
- **Ground truth:** duplication confirmed; no behavioral drift *yet* (two harmless
  differences already exist — redundant double-run of idempotent trivia steps, and an
  inlined default). The proposed fix is purely additive to `fltk.plumbing`
  (`generate_unparser_source(...)`; existing `generate_unparser` exec's its output),
  which is the safe category per CLAUDE.md.
- **The case for skipping:** the pipeline changes rarely.
- **Recommendation: Do** — classic drift foot-gun with a clean additive fix.
