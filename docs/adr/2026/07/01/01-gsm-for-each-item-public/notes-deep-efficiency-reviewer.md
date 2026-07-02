# Deep efficiency review — gsm-for-each-item-public

Commit reviewed: a567ca7c085032fa99c079f0c6f1f70f59aea55a (base e96f0565)

No findings.

Scope is a pure rename of `_for_each_item` → `for_each_item` in `fltk/fegen/gsm.py`
(definition + self-recursion + two internal callers) and its call/doc references in
`fltk/fegen/regex_corpus.py`, plus a TODO.md entry removal and a new direct unit test.
Function body, signature, call arguments, and control flow are byte-identical apart from
the name. No new work, no loops, no hot-path or startup changes, no data structures, no
concurrency surface. Nothing to flag for efficiency.
