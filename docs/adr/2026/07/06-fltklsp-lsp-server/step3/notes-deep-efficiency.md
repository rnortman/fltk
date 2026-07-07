# Deep efficiency review — step3 (.fltklsp M4)

Base 1ad3141 → HEAD 8966d8ee42840c5f7fbf26090b14ef20eafc28e0.
Scope: symbol tables, navigation, rename, ref-site paint.

## efficiency-1 — extraction adds a third full tree walk on the analyze() hot path
`engine.py:152-159`: `analyze()` now runs `symbols.extract(...)` (one `O(tree)` walk +
per-ref outward-scope resolution) *before* `classify(...)`, which itself walks the tree
twice (`_explicit_intervals` + `_default_intervals`). So each analysis is three tree
traversals plus resolution.

Consequence: `analyze()` runs on every document change (debounced) and is the per-request
hot path for highlighting; the extraction walk is new blocking work added to it, growing
the per-keystroke cost by roughly one-third at every document scale. Bites on large
documents / fast typing.

This is acknowledged: the code comment at `classify.py:400-402` and design §4.4/§5 fold
it into the existing `TODO(lsp-classify-hotpath)` unification (single walk producing
symbols, explicit paints, and defaults together). No separate action needed — recorded so
the reviewer sees the full cost picture and that the direction (fold the three walks into
one) is captured.

## efficiency-2 — symbols._walk resolves rule_for_node twice per non-span node
`symbols.py:214` computes `child_rule_name = classify.rule_for_node(child, tables).name`
for match testing, then `symbols.py:245` recurses `_walk(child, ...)`, whose first line
(`symbols.py:191`) calls `classify.rule_for_node(node, tables)` again on that same child.
Every non-span node's rule is therefore looked up twice.

Consequence: a redundant dict lookup for every interior node, per analysis, on the hot
path from efficiency-1. Individually cheap (a `kind_to_rule.get` + guard), but it doubles
the rule-resolution count over the whole tree on every keystroke. Direction: thread the
already-resolved child `gsm.Rule` into the recursive `_walk` call (pass it as an argument)
so the child does not re-resolve its own rule. (The same double-lookup pattern predates
this round in `classify._explicit_intervals`; the eventual walk-unification TODO would
absorb both — but this new code could avoid it directly now.)

## efficiency-3 — rename verify-reparse runs full analyze when only parse-success is needed
`server.py` `rename_document` → `loop.run_in_executor(self._executor, self._engine.analyze,
renamed)` then checks only `verify.error`. `engine.analyze` runs parse + `symbols.extract`
+ `classify` (three walks); for the verify guard only parse success/failure is consulted,
so the extraction and both classification passes are wasted work.

Consequence: extra CPU on each rename equal to a full symbol-extraction + classification of
the whole renamed document, discarded immediately. Rename is an explicit, infrequent user
action, so the absolute impact is small, and design §2.6 explicitly accepts "one extra
classification pass." Recorded because it is genuinely avoidable: a parse-only entry point
(parse without extract/classify) would give the same guard at a fraction of the cost, if a
cheaper verify is ever wanted. Low priority.

## efficiency-4 (note) — symbol_at/reference_at linear scan vs. designed bisect
`symbols.py:72-84` (`symbol_at`/`reference_at`) call `_smallest_containing`, a linear
`O(n)` scan over all symbols/references. Design §4.3 specified "bisect-over-sorted-starts
with a containment check"; the symbols/references tuples are already sorted by start, so a
bisect to the candidate window is available for free.

Consequence: each navigation/rename request (definition, references, highlight,
prepareRename, rename) scans the entire symbol or reference list. These are user-initiated
(not the per-keystroke path) and symbol counts are modest, so impact is negligible today;
flagged only as a deviation from the design's stated approach. No action required unless
symbol counts grow.

## Not flagged (verified clean)
- Read-only handlers (`document_symbol`, `definition`, `references`, `document_highlight`,
  `prepare_rename`) each do one `_ensure_analyzed` (cached per version) + pure feature
  translation — no redundant re-analysis.
- `rename_document` does exactly two analyses (current text via cached `_ensure_analyzed`,
  renamed text for verify); no extra passes.
- Client-capability accessors (`_hierarchical_symbols`, `_document_changes`) read
  immutable initialize-time capabilities per request — equivalent to caching, no cost.
- `document_symbols`' re-sort by `(range_start, -range_end)` is one required sort per
  request, not hot.
- `occurrences` dedupe and the resolution pass are `O(refs)` / `O(refs × scope depth)`,
  fine at the debounced server's scale.
</content>
</invoke>
