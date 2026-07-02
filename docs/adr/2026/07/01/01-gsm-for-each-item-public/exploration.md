# Exploration: `TODO(gsm-for-each-item-public)`

Base commit: `8fd5ecf`. All facts below are from direct reads of the working tree at that commit; no code was changed.

## TODO.md entry (verbatim, `TODO.md:33`)

```
## `gsm-for-each-item-public`

`gsm._for_each_item` is a private function used internally by `gsm.py` for
validation passes, but `fltk/fegen/regex_corpus.py` is the first cross-module
caller. Promote it to a public name (`for_each_item`) in `gsm.py`, or add a
public `iter_regexes(grammar)` helper that encapsulates the walk so callers
never need to touch the structural walk API. Gives callers a stable, tested
contract instead of a private-name dependency that mypy/pyright won't flag
across modules. Location: `fltk/fegen/gsm.py` (`_for_each_item`),
`fltk/fegen/regex_corpus.py:58` (call site).
```

## All `TODO(gsm-for-each-item-public)` occurrences in the repo

```
TODO.md:33                                                                     ## `gsm-for-each-item-public`  (entry header)
fltk/fegen/regex_corpus.py:57                                                  gsm._for_each_item(items, _visit)  # TODO(gsm-for-each-item-public): promote to public API
docs/adr/2026/06/14-rust-backend-assessment/burndown/regex-grammar-spike/dispositions-deep.md:149   Disposition: TODO(gsm-for-each-item-public)
docs/adr/2026/06/14-rust-backend-assessment/burndown/regex-grammar-spike/dispositions-deep.md:151   Action note: added the comment + TODO.md entry, no code change
docs/adr/2026/06/14-rust-backend-assessment/burndown/regex-grammar-spike/judge-verdict-deep-round2.md:51,62   references the TODO as the one accepted/retained item from that review round
docs/adr/2026/06/14-rust-backend-assessment/burndown/regex-grammar-spike/judge-verdict-deep.md:11,213         same, plus the finding writeup ("quality-2 — TODO(gsm-for-each-item-public) at regex_corpus.py:58")
```

There is exactly one `TODO(gsm-for-each-item-public)` code comment (`fltk/fegen/regex_corpus.py:57`) and one `TODO.md` entry. No other code location references this slug.

**Location discrepancy**: the TODO.md entry and the prior burndown docs both cite the call site as `regex_corpus.py:58`. The actual call `gsm._for_each_item(items, _visit)` with the TODO comment attached is on **line 57** of the current file; line 58 is a blank line. This is a stale/off-by-one line reference, not a wrong file.

## Is the cross-module private call real?

Yes. `fltk/fegen/regex_corpus.py:31` does `from fltk.fegen import gsm`, and line 57 calls `gsm._for_each_item(items, _visit)`. `regex_corpus.py` and `gsm.py` are separate modules; `_for_each_item` is a single-leading-underscore name, which Python does not enforce as private but is the repo's convention for module-internal helpers (confirmed by the doc comment at `regex_corpus.py:44-45` explicitly naming it `gsm._for_each_item` and describing its recursion behavior, i.e. the caller already knows it's reaching into `gsm`'s internals).

`gsm.py` itself defines `_for_each_item` at line 291 and uses it only from within the same file, at two call sites: `gsm.py:320` (inside `_collect_underscore_only_label_errors`) and `gsm.py:430` (inside `_collect_repeated_nil_errors`). Both in-module callers are themselves private helpers (`_collect_underscore_only_label_errors`, `_collect_repeated_nil_errors`) used by the public validation entry points `validate_no_underscore_only_names` (`gsm.py:323`) and `validate_no_repeated_nil_items` (`gsm.py:433`).

## Signature of `_for_each_item`

```python
# fltk/fegen/gsm.py:291-302
def _for_each_item(items: "Items", visitor: "Callable[[int, Item], None]") -> None:
    """Walk every Item in an Items sequence, recursing into Sequence[Items] sub-expressions.

    Calls visitor(idx, item) for each Item in depth-first order, where idx is the item's
    index within its enclosing items.items list.  The recursion enters every alternative
    of a Sequence term regardless of the outer quantifier, so nested items are always visited.
    """
    for idx, item in enumerate(items.items):
        visitor(idx, item)
        if isinstance(item.term, Sequence):
            for alt in item.term:
                _for_each_item(alt, visitor)
```

`Items` (`gsm.py:83`) and `Item` (`gsm.py:121`) are both already public classes (no leading underscore), and `regex_corpus.py` already imports/uses them directly as `gsm.Items` and `gsm.Item` in its own type annotations (`regex_corpus.py:50-51`). So the only private surface actually touched by the cross-module call is the function name `_for_each_item` itself — the data types it walks are already public.

### What each proposed shape would mean for the call site

- **Option A — rename `_for_each_item` to `for_each_item` (module-level, still generic walk + visitor callback)**: `regex_corpus.py:57` would change from `gsm._for_each_item(items, _visit)` to `gsm.for_each_item(items, _visit)`, a one-token rename at the one call site. The two in-module callers (`gsm.py:320`, `gsm.py:430`) would need the same rename (or could keep calling the private name internally while a public alias wraps it — not specified in the TODO). No signature change; `visitor: Callable[[int, Item], None]` stays generic (works for the label-check, repeated-nil-check, and regex-collection use cases alike).

- **Option B — add a public `iter_regexes(grammar)` helper**: this is a different, narrower shape — it takes a `Grammar` (not `Items`) and presumably returns/yields regex bodies directly, folding in the `isinstance(item.term, gsm.Regex)` filter and the `Items`/`Item` iteration that currently lives in `regex_corpus.py:50-56` (`_collect_items`/`_visit` closures) and the outer `for rule in grammar.rules: for alternative in rule.alternatives` loop at `regex_corpus.py:59-61`. This would let `collect_regexes` (`regex_corpus.py:36-63`) be replaced by a thin wrapper (or removed in favor of calling `gsm.iter_regexes` directly), and `regex_corpus.py` would no longer need to know about the `Items`/`Item` walk shape at all — it wouldn't import `Items`/`Item` for this purpose either. This is a bigger change: it moves regex-specific logic (the `isinstance(item.term, gsm.Regex)` check, currently at `regex_corpus.py:52`) into `gsm.py`, a module that otherwise has no regex-collection-specific code today (confirmed by scanning `gsm.py`'s function list above — no existing `Regex`-filtering helper).

The TODO presents these as alternatives ("Promote it to a public name … **or** add a public `iter_regexes(grammar)` helper") without picking one; the two options differ in scope (generic walk rename vs. a grammar-level, regex-specific convenience function) and Option B would require writing new code and tests, not just a rename.

## Other cross-module private-name uses of `gsm` internals

`grep -rn 'gsm\._[a-zA-Z_]*' --include='*.py'` across the repo (excluding `gsm.py` itself, which naturally uses its own private names) turns up only the `regex_corpus.py` occurrences already listed above (the doc comment at line 44, the doc comment at line 54, and the call at line 57). No other file references any `gsm._*` private symbol.

One superficially similar but unrelated pattern exists: `tests/test_phase4_fegen_rust_backend.py:70` and a duplicate under `.claude/worktrees/agent-ab295be24eef6e7ce/tests/test_phase4_fegen_rust_backend.py:129` (a worktree copy, not part of the reviewed tree) both contain a docstring reference to `fltk2gsm._span_text` ("Pins the contracts required by fltk2gsm._span_text (used by visit_identifier, ..."). This is a different module (`fltk2gsm`, not `gsm`) and a different private symbol (`_span_text`, not `_for_each_item`), referenced only in a test docstring, not an executable cross-module call. It is out of scope for this TODO's slug but is the same *category* of issue (private-name dependency named in a comment) if the reviewer wants a broader sweep later.

## Summary of verified facts

- The cross-module call is real: `regex_corpus.py:57` calls `gsm._for_each_item`, a name private to `gsm.py`.
- `_for_each_item` has two in-module call sites (`gsm.py:320`, `gsm.py:430`) besides the one cross-module call.
- The `Items`/`Item` types it operates over are already public; only the function name is private.
- The TODO's cited call-site line number (`regex_corpus.py:58`) is off by one — the actual line is 57.
- No other `gsm._*` cross-module references exist anywhere in the tree.
- The two remediation options named in the TODO (bare rename vs. new `iter_regexes(grammar)` helper) are not equivalent in scope: the rename is a one-line change at the single call site plus two internal call sites; the `iter_regexes` helper would require moving `regex_corpus.py`'s `Regex`-filtering logic into `gsm.py` and does not currently exist in any form.
