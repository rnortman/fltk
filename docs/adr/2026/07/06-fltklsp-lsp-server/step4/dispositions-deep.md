# Deep-review dispositions — step4 (M3 prefix-CST / degraded serving)

Round base `dcac826`; fixes committed at `80418ae`. `make check` green. Reviewer files with
"No findings": correctness, security, reuse, efficiency.

Note: two error-handling findings duplicate two quality findings (errhandling-1≈quality-3,
errhandling-2≈quality-4); each pair got one fix, cross-referenced below.

errhandling-1:
- Disposition: Fixed
- Action: Added a module logger to `fltk/lsp/engine.py` (`_LOGGER`, import at :11-12, defined
  :24) and a `_LOGGER.warning(...)` at the inner prefix-classification `except RecursionError`
  (`engine.py:181-190`) recording the abandoned prefix length. The degrade-to-parse-error
  outcome is unchanged, per design §4.3; only the previously-silent event is now traced.
- Severity assessment: A prefix-classifier stack overflow on otherwise-well-formed input was
  indistinguishable from an ordinary hard failure in logs, so a classifier/grammar-depth bug on
  a valid construct left no on-call signal. Same underlying issue as quality-3.

errhandling-2:
- Disposition: Fixed
- Action: Replaced `analysis.prefix_end or 0` with `assert analysis.prefix_end is not None`
  before computing the boundary in `_analyze_blocking` (`fltk/lsp/server.py:216-221`). The
  partial branch's `DocumentAnalysis` invariant guarantees `prefix_end is not None`; a contract
  break now crashes loudly at the seam instead of silently computing a zero boundary. Same fix as
  quality-4.
- Severity assessment: An engine invariant regression would have masked as a corrupted merge
  (whole stale stream kept, overlapping fresh+stale segments → possible negative
  `deltaStartChar`) with no crash or log.

quality-1:
- Disposition: Fixed
- Action: Dropped the write-only `version` field from `_ServedTokens` (`fltk/lsp/server.py:111-122`)
  and its construction site; updated the docstring to note staleness ordering is enforced by
  `_store`'s `analyzed_version` guard before the write.
- Severity assessment: A dead field invited the false belief that serve-time version consistency
  was checked; no runtime effect, but a maintenance trap.

quality-2:
- Disposition: Fixed
- Action: Deleted the `_ServedPair` tuple alias; `_analyze_blocking` now constructs and returns
  `_ServedTokens | None` directly (`server.py:194-222`), and `_store` stores it without
  unpack/rewrap (`server.py:247-260`). `_AnalysisResult` retyped to reference `_ServedTokens`.
- Severity assessment: Two shapes for one value; a future added field would have to be threaded
  through both. No runtime effect. Naturally paired with quality-1.

quality-3:
- Disposition: Fixed
- Action: Same change as errhandling-1 (logger + warning at `engine.py:181-190`).
- Severity assessment: See errhandling-1 — the one error path leaving no trace anywhere.

quality-4:
- Disposition: Fixed
- Action: Same change as errhandling-2 (`assert` at `server.py:216-218`).
- Severity assessment: See errhandling-2 — defensive fallback masking a "can't happen" invariant
  break as subtly-wrong highlighting.

test-1:
- Disposition: Fixed
- Action: Added `test_analyze_classification_recursion_error_on_complete_parse_degrades`
  (`fltk/lsp/test_engine_analyze.py`), monkeypatching `classify.classify` to raise on a
  fully-parsing text and asserting the failed outcome with the nesting-depth message — pins the
  outer-`try` coverage of the `classify.classify` call on the complete path (design test-plan
  item 9), which prior tests only reached via `symbols.extract`.
- Severity assessment: A future narrowing of the outer `try` around only `extract` would let a
  success-path `RecursionError` escape `analyze()` uncaught with no test catching it.

test-2:
- Disposition: Fixed
- Action: Added `test_folding_served_from_last_good_during_partial` and
  `test_selection_served_from_last_good_during_partial` (`fltk/lsp/test_server.py`), each driving
  `foldingRange`/`selectionRange` against a document whose current state is partial and asserting
  the last-complete tree's folds/selection chain are still returned (design test-plan item 18).
- Severity assessment: `_GoodAnalysis`'s shape changed this round; a regression that blanked
  folding/selection on partial states was previously uncaught.

test-3:
- Disposition: Fixed
- Action: Extended `test_semantic_tokens_range_on_partial_state` with a single range spanning the
  merge boundary (start on line 0 prefix, end on line 1 stale tail), asserting the decoded result
  equals `prefix + tail` (design test-plan item 17, the literal "spanning the boundary" case).
- Severity assessment: The two prior disjoint single-line ranges could mask a compensating
  off-by-one in one of the two bisects that a combined query would expose.
