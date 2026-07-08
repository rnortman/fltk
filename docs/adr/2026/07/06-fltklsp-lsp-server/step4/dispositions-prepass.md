# Prepass dispositions — step4 M3

slop-1:
- Disposition: Fixed
- Action: Reworded the comment at fltk/lsp/test_server.py:799-800 to state the invariant under test ("The server takes its start rule from the engine, so the formatting parses and the analysis parses can never disagree on it") instead of the changelog-style "The dedup change:" framing that referenced the prior TODO/refactor history.
- Severity assessment: Cosmetic. A self-narrating comment that only makes sense with knowledge of the removed `lsp-start-rule-dedup` TODO; harmless to behavior but violates the project's comment-hygiene standard (no changelog/what-changed comments).

Scope prepass: no findings (all six §3.1 in-scope items present and matching; §3.2 out-of-scope correctly untouched). Nothing to disposition.
