Concise. Precise. Complete. Unambiguous. Audience: smart LLM/human.

Commit reviewed: 7999f88 (base: a48f820).
Changed files: TODO.md, fltk/fegen/gsm.py, fltk/fegen/gsm2tree_rs.py, fltk/fegen/test_name_validation.py.

---

reuse-1

File: fltk/fegen/gsm.py:291-310 (new `_collect_underscore_only_label_errors`) vs gsm.py:408-427 (existing `_collect_repeated_nil_errors`).

Both functions share an identical recursion skeleton:
1. Iterate `for item in items.items`.
2. Evaluate a per-item predicate, appending to an `errors` list on match.
3. `if isinstance(item.term, Sequence): for alt in item.term: recurse(alt, ...)`.

The new function even cites the existing one in its docstring: "Mirrors the recursion pattern in `_collect_repeated_nil_errors`."

Existing utility: `_collect_repeated_nil_errors` at gsm.py:408. There is no shared `_walk_items` helper that both could delegate the traversal to.

Consequence: the recursion logic is now duplicated in two places. If the GSM gains a new term type that requires different traversal (e.g., `Invocation` sub-terms), both functions must be updated independently. Future validators — the pattern is clearly becoming a convention — will each repeat the same skeleton a third, fourth time.

A generic `_for_each_item(items, visitor)` walker (or a `visit_items` method on `Items`) would let both callsites register only the predicate, with traversal owned once. This is not a blocking defect; the current duplication is two instances and both are correct. Worth addressing before a third validator is added.

---

No other findings. The label-iteration loop in gsm2tree_rs.py:105-121 (flat, non-recursive) vs the new recursive walker is a pre-existing acknowledged gap noted in design.md:110-112, not a new reuse opportunity introduced by this diff.
