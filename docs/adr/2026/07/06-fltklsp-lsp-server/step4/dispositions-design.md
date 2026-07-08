# Dispositions — step4 design review, round 1

Findings from `notes-design-design-reviewer.md`, fact-checked against `fltk/lsp/server.py` and
`fltk/lsp/engine.py` at `46c17e5`. All three findings verified accurate; all three fixed in
`design.md`.

design-1:
- Disposition: Fixed
- Action: §4.5 "Handler changes" — the `semantic_tokens_range` bullet now opens with the
  `served_tokens is None` case (empty `lsp.SemanticTokens(data=[])`, mirroring the full handler
  and today's `good is None` path at `server.py:590-591`). Test plan item 15 gains the sibling
  case: a document whose only analysis is a hard failure gets empty data from both `full` and
  `range` with no crash.
- Severity assessment: Verified real — `_DocState.served_tokens` defaults to `None` and the
  design's own `_store` rule leaves it `None` after a hard first failure, so a literal
  implementation of the original sketch would raise `AttributeError` in the range handler for
  any document opened with a hard parse failure, a regression from today's empty-response path
  (`server.py:590-591`). Client-visible request error on a reachable state; cheap one-sentence
  spec fix.

design-2:
- Disposition: Fixed
- Action: §4.5 "Worker changes" — `_analyze_blocking`'s sketch now returns
  `(segments, delta_encode_segments(segments))` computed on the worker; a following paragraph
  states the preserved invariant (all O(tokens) encoding stays off the protocol loop, per the
  load-bearing docstring at `server.py:178-183`) and notes that per-request encoding of range
  *slices* on the loop thread is today's behavior and kept. §4.5 "`_store` rules" updated to
  `_ServedTokens(version, *served)` with an explicit "`_store` does no encoding work", and the
  `last_good` rule to `segments=served[0]`. (Also corrected an indentation slip in the revised
  sketch so `served` is only built when `analysis.tokens is not None`.)
- Severity assessment: Verified real — the original sketch silently moved the O(segments)
  delta-encode from the worker (`server.py:192-195`) into `_store` on the loop thread, run
  after every debounced analysis of every document, eroding the never-block-the-loop property
  the current structure deliberately documents. Avoidable for free since the worker already
  holds the segments.

design-3:
- Disposition: Fixed
- Action: §4.3 RecursionError note rewritten — it now states what the existing single `try`
  (`engine.py:144-161`) actually guards (the parse **and** the success path's
  `symbols.extract` + `classify.classify`), states the restructure invariant (parse-raised and
  success-path-classify-raised `RecursionError` both keep producing today's nesting-depth
  failed outcome; only the new inner prefix-classification guard degrades to
  failed-with-parse-error), and explicitly forbids narrowing the outer `try` to just
  `parse_text`. Test plan item 9 gains the success-path `RecursionError` regression test.
- Severity assessment: Verified real — the parenthetical "(which guards the parse itself)"
  understated the existing `try`'s coverage; a plausible implementation of the prescribed
  restructure would let a success-path `RecursionError` escape `analyze()`, turning a clean
  diagnostic into an unpublished worker exception in the server and a raw traceback in
  `fltk-highlight`. Spec-ambiguity fix plus a pinning test.

No Won't-Do or TODO dispositions this round. Design edits were localized (three sections plus
two test-plan items); no cleanup-editor pass was needed.
