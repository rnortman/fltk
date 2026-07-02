# Correctness review — gsm-for-each-item-public

Reviewed: e96f0565..a567ca7c (`gsm: promote _for_each_item to public for_each_item`)

No findings.

Verification performed:
- Rename is byte-identical apart from the name: definition (`fltk/fegen/gsm.py:291`), self-recursion (`gsm.py:302`), both internal call sites (`gsm.py:320`, `gsm.py:430`), and the cross-module call (`fltk/fegen/regex_corpus.py:57`) all updated consistently.
- `grep -rn '_for_each_item'` over `fltk/`, `tests/`, and `TODO.md` returns zero hits — no stale reference, no missed self-recursion site.
- New `tests/test_gsm_walk.py` constructs match the real GSM model (`Items(items, sep_after)` lengths agree; `Item` field names/order correct; `gsm.Term | None` annotation is valid at runtime on 3.10+ since typing `Union` supports `|`). Expected visit orders in all three tests match a manual trace of `for_each_item`'s depth-first walk, including the enclosing-relative index semantics for nested `Items`.
- `uv run pytest tests/test_gsm_walk.py tests/test_regex_grammar_corpus.py tests/test_nullable_loop_guard.py` — 51 passed, 1 skipped.
- TODO.md entry removal is consistent with the TODO system: the matching `TODO(gsm-for-each-item-public)` code comment is deleted in the same commit.
