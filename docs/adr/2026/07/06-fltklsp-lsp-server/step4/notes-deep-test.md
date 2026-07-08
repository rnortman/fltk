# Deep test review: dcac826..1060867 (M3 prefix-CST / degraded-mode serving)

Reviewed against `docs/adr/2026/07/06-fltklsp-lsp-server/step4/design.md` §7 test plan. All
79 tests in `fltk/lsp/test_plumbing_prefix.py`, `test_engine_analyze.py`, `test_features.py`,
`test_dogfood.py`, `test_highlight_cli.py` and all 41 in `test_server.py` pass locally. Coverage
of the new prefix/partial-serving surface is broad and assertions are substantive (decoded
token positions, symbol name sets, `RecursionError`-degrade message content, sortedness/overlap
invariants) rather than smoke checks. Three gaps against the design's own test plan.

## test-1: No test for `RecursionError` from `classify.classify` on the *complete* (non-prefix) path

`fltk/lsp/test_engine_analyze.py`. The design's test-plan item 9 explicitly calls for: "a
document that *parses successfully* but raises `RecursionError` during classification still
yields the failed outcome with the nesting-depth message (pins the §4.3 restructure invariant;
today this behavior is only incidentally covered)."

`engine.py`'s outer `try` (lines 161-206) wraps both `symbols.extract(parsed.cst, ...)` (line
188) and `classify.classify(parsed.cst, ...)` (line 189) on the success path. The two existing
tests that exercise `RecursionError` degradation are:

- `test_analyze_extraction_recursion_error_reports_offset_none` — monkeypatches
  `engine_module.symbols.extract` on a *successful* parse. This raises before `classify.classify`
  is ever reached, so it never exercises the outer `try`'s coverage of the `classify.classify`
  call specifically.
- `test_analyze_prefix_classification_recursion_degrades_to_parse_error` — monkeypatches
  `engine_module.classify.classify`, but on `"let a ;\nlet ;\n"`, which is a *partial* (prefix)
  outcome, exercising the new inner `try` (lines 167-180), not the outer one.

No test raises from `classify.classify` on a text that parses to a *complete* result. If a
future edit narrowed the outer `try` so it only covered `symbols.extract` (e.g. moved
`classify.classify` outside the block, or split the two calls across separate exception
scopes), the success-path `RecursionError`-degrades-to-failed-outcome behavior would silently
break and no test would catch it — a `RecursionError` from `classify.classify` on a complete
parse would then propagate uncaught out of `analyze()` instead of degrading to the
nesting-depth message.

Fix: add a test that monkeypatches `engine_module.classify.classify` to raise `RecursionError`
on a text that parses completely (e.g. `"let x ;\nuse x ;\n"` against `_ref_engine()`) and
asserts the failed outcome with `"nesting depth"` in the message, mirroring
`test_analyze_extraction_recursion_error_reports_offset_none` but hitting the classify call
instead of extract.

## test-2: Folding and selection during partial serving are untested

`fltk/lsp/test_server.py`. Design test-plan item 18: "Folding/selection/documentSymbol/
definition during partial: still served from the last complete analysis (assert a symbol past
the error is still reported)."

Only two of the four listed features get partial-state coverage in this round:

- `document_symbol` — new `test_document_symbol_served_from_last_good_during_partial`.
- `definition` — covered only incidentally: `test_navigation_served_from_last_good_after_break`
  is an unmodified pre-existing test that uses `_BROKEN` ("greet 123.") against the `document`
  grammar (`document := , item*`), which — per this round's own semantics — now produces a
  *partial* analysis (zero-length prefix, not a hard failure), so the test happens to exercise
  the partial path without being written or labeled for it.

`folding_range` and `selection_range` (`server.py` lines 634-649) go through the same
`_serveable`/`last_good` mechanism, and `_GoodAnalysis`'s shape did change in this round
(`tokens`/`encoded_tokens` dropped, `segments` added), so it is not purely a "nothing touched
this" case. No test drives `textDocument/foldingRange` or `textDocument/selectionRange` against
a document whose current state is partial to confirm they still return the last-good tree's
folds/selection chains rather than an empty/degraded result.

Fix: extend `test_document_symbol_served_from_last_good_during_partial`'s pattern (open `_SYM`,
`_change` to `_SYM_BROKEN`) with two more assertions (or two new tests) hitting
`textDocument/foldingRange` and `textDocument/selectionRange`, asserting the last-good folds/
selection ranges are still returned unchanged.

## test-3: No `semanticTokens/range` request that itself straddles the merge boundary

`fltk/lsp/test_server.py::test_semantic_tokens_range_on_partial_state`. Design test-plan item
17 asks for range requests "inside the prefix and spanning the boundary." The test issues two
separate, disjoint single-line ranges (line 0 = prefix, line 1 = tail) and checks
`len(prefix) + len(tail) == len(full)` — good indirect evidence the partition is exact, but no
single range request has `start` before the boundary and `end` after it, which is the literal
"spanning the boundary" case (e.g. a user selection covering both the fresh-prefix tail and the
stale-tail head in one `SemanticTokensRangeParams`). The `semantic_tokens_range` handler
(`server.py:620-632`) doesn't special-case the boundary — it bisects uniformly over the merged
`segments` list — so the risk of a boundary-specific bug slipping through is lower than for
test-2, but the two-disjoint-ranges pattern still doesn't prove a single spanning query returns
the union correctly (e.g. an off-by-one in one bisect that happens to cancel out when the two
ranges are queried separately could still misbehave on a combined range).

Fix: add one more range assertion in the same test with `start` on line 0 and `end` on line 1,
asserting the decoded result equals `prefix + tail` from the existing two calls.
