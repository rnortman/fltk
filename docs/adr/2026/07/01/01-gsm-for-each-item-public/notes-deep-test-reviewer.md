No findings.

Verified: `git diff e96f0565..a567ca7c` is a pure rename (`_for_each_item` -> `for_each_item`)
across `fltk/fegen/gsm.py` (definition + self-recursive call + two internal call sites) and
`fltk/fegen/regex_corpus.py` (call site + two doc-comment references), plus the matching
`TODO.md` entry removal. `grep -rn '_for_each_item'` over all `.py` files returns zero hits;
only historical burndown docs (deliberately untouched per design) still mention the old name.

New file `tests/test_gsm_walk.py` adds direct unit coverage for `gsm.for_each_item` that did
not exist before (previously only exercised indirectly via
`validate_no_repeated_nil_items`/`validate_no_underscore_only_names` and
`regex_corpus.collect_regexes`):

- `test_flat_items_visited_once_in_order` — asserts exact `(idx, item)` visit sequence for a
  flat `Items`.
- `test_recurses_into_sequence_terms_with_enclosing_relative_index` — asserts depth-first
  order and that nested `Sequence[Items]` indices are relative to the enclosing `Items`, not
  global; this is the one path (nested regex/Sequence recursion) the design doc flags as
  previously uncovered by any in-tree test.
- `test_recurses_regardless_of_outer_quantifier` — asserts a `ZERO_OR_MORE`-quantified
  `Sequence` item is still recursed into.

All three assert exact list equality of `(idx, item)` tuples (dataclass equality, not
identity/smoke checks), so they pin real behavior rather than just "ran without throwing."
Ran `uv run pytest tests/test_gsm_walk.py tests/test_nullable_loop_guard.py
tests/test_regex_grammar_corpus.py -q`: 51 passed, 1 skipped (pre-existing skip, unrelated).

No production behavior changed (name-only), so no adjacent existing test needed updating for
behavioral drift. No gaps identified.
