# Design: `gsm-for-each-item-public` — promote `_for_each_item` to public `for_each_item`

Requirements: `docs/adr/2026/07/01/01-gsm-for-each-item-public/request.md`
Exploration: `docs/adr/2026/07/01/01-gsm-for-each-item-public/exploration.md`
Base commit: `8fd5ecf` (exploration) / `c03a801` (current main — no relevant drift; all line numbers below re-verified against the working tree).

## Root cause / context

`fltk/fegen/regex_corpus.py:57` calls `gsm._for_each_item(items, _visit)` — a
single-leading-underscore (private-by-convention) function in another module.
Python doesn't enforce the convention and neither mypy nor pyright flags the
cross-module reach-in, so nothing guards this dependency. The types the walk
operates over (`gsm.Items` at `gsm.py:83`, `gsm.Item` at `gsm.py:121`) are
already public and already imported by `regex_corpus.py`; the function name is
the only private surface touched.

`_for_each_item` (`gsm.py:291-302`) has exactly three call sites:
- `gsm.py:320` — inside `_collect_underscore_only_label_errors`
- `gsm.py:430` — inside `_collect_repeated_nil_errors`
- `regex_corpus.py:57` — the cross-module call carrying the
  `TODO(gsm-for-each-item-public)` comment

No other `gsm._*` cross-module reference exists anywhere in the tree
(exploration, "Other cross-module private-name uses").

Per the requirements, we do **the rename only** (Option A). The alternative
`iter_regexes(grammar)` helper is explicitly rejected: it would move
regex-specific filtering (`isinstance(item.term, gsm.Regex)`,
`regex_corpus.py:52`) into `gsm.py`, which today contains no regex-collection
logic, for the benefit of no additional caller.

## Proposed approach

Pure rename, no signature change, no alias.

### `fltk/fegen/gsm.py`

1. Rename `_for_each_item` → `for_each_item` at its definition (`gsm.py:291`).
   Signature and docstring unchanged:
   `def for_each_item(items: "Items", visitor: "Callable[[int, Item], None]") -> None`.
   The function stays where it is (above both internal callers); no code moves.
2. Update the self-recursive call (`gsm.py:302`) and the two internal call
   sites (`gsm.py:320`, `gsm.py:430`) to the new name. No compatibility alias
   `_for_each_item = for_each_item` is kept: all callers are in-tree and
   updated in the same commit, and private names carry no stability guarantee
   for out-of-tree code.

### `fltk/fegen/regex_corpus.py`

3. Change the call at line 57 to `gsm.for_each_item(items, _visit)` and delete
   the trailing `# TODO(gsm-for-each-item-public): promote to public API`
   comment.
4. Update the two doc-comment references to the old name:
   the `collect_regexes` docstring at line 44 ("The walk uses
   ``gsm._for_each_item`` …") and the inline comment at lines 54-55
   ("gsm._for_each_item recurses into …") both become `gsm.for_each_item`.

### `TODO.md`

5. Remove the `## gsm-for-each-item-public` entry (`TODO.md:11-13`). After
   this change no `TODO(gsm-for-each-item-public)` comment remains in code, so
   both halves of the TODO system stay in sync.

Nothing else changes. Historical burndown docs under
`docs/adr/2026/06/14-rust-backend-assessment/` that mention the slug are
records of past reviews and are left untouched.

## Edge cases / failure modes

- **Out-of-tree callers of the old private name.** `gsm.py` is imported by
  downstream grammar-building code, so in principle an external caller could
  reference `gsm._for_each_item`. Removing it without an alias is acceptable:
  single-underscore names are explicitly outside the public API contract, and
  keeping a deprecated alias would perpetuate exactly the private-name
  dependency this TODO exists to eliminate. This is a deliberate call, not an
  oversight.
- **Missed rename site.** The self-recursion at `gsm.py:302` is the easy one
  to miss; renaming the definition without it raises `NameError` on any
  nested-`Sequence` grammar, which the existing validator tests
  (`tests/test_nullable_loop_guard.py`, exercising
  `validate_no_repeated_nil_items` on nested sub-expressions) would catch
  immediately. A repo-wide grep for `_for_each_item` after the change must
  return zero hits.
- **Behavioral risk.** None: the function body, signature, and call arguments
  are byte-identical apart from the name.

## Test plan

Existing indirect coverage already exercises the walk end-to-end and passes
unchanged after the rename:

- `tests/test_regex_grammar_corpus.py` — runs `collect_regexes` over
  `fegen.fltkg` and `regex.fltkg` (the cross-module call path). Note: neither
  in-tree grammar places a regex term inside a parenthesized sub-expression,
  so these tests do not exercise the walk's `Sequence` recursion via this
  path.
- `tests/test_nullable_loop_guard.py` — `validate_no_repeated_nil_items` on
  grammars with `Sequence` sub-expression terms (`term=[inner_items]`), which
  drives the walk's self-recursion.

New (TDD): the TODO's stated goal is a "stable, **tested** contract", and
today no test targets the walk directly — its contract is only pinned via
consumers, and the nested-regex collection path has no coverage at all. Add a
small direct unit test (new file `tests/test_gsm_walk.py`) for
`gsm.for_each_item` asserting:

1. Every `Item` in a flat `Items` is visited once, with `idx` equal to its
   position in `items.items`.
2. The walk recurses into `Sequence[Items]` terms: items inside a
   parenthesized sub-expression are visited, with `idx` relative to their
   *enclosing* `Items` (not a global index), matching the documented
   depth-first order.
3. Recursion happens regardless of the outer quantifier on the `Sequence`
   item (e.g. a `ZERO_OR_MORE`-quantified sub-expression is still entered),
   per the docstring's "regardless of the outer quantifier".

Written first, this test fails only on the name (`gsm.for_each_item` doesn't
exist yet), which is precisely the change under test.

Verification after implementation: `grep -rn '_for_each_item'` over `fltk/`,
`tests/`, and `TODO.md` returns nothing; `uv run pytest` passes; `uv run ruff
check . && uv run pyright` clean.

## Open questions

None. The requirements fix the option (rename, not helper), and the only
judgment calls — no alias, direct unit test added, historical docs untouched —
are resolved above with rationale.
