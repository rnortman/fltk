# Slop prepass — dcac826..ee68d5

## slop-1
File: fltk/lsp/test_server.py:799 (function `test_create_server_reads_start_rule_from_engine`)

Quote:
```
    # The dedup change: the server takes its start rule from the engine, so the formatting parses and
    # the analysis parses can never disagree on it.
```

What's wrong: narrative/changelog comment describing the edit itself ("The dedup change") rather than what the code currently does. Reads as the author talking to themselves about the refactor instead of documenting the test's intent.

Consequence: a reviewer sees a comment that only makes sense with knowledge of the prior TODO/PR history (`lsp-start-rule-dedup`); it won't age well once that context is gone, and it's the kind of self-narrating comment that signals an unreviewed first draft.

Suggested fix: rewrite to state the invariant being tested, e.g. "`create_server` takes its start rule from the engine so the formatting and analysis parses can never disagree on it," dropping "The dedup change."
