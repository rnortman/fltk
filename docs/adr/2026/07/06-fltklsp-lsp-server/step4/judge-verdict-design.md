# Judge verdict — design review

Phase: design. Doc: `docs/adr/2026/07/06-fltklsp-lsp-server/step4/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 3 findings. Dispositions: all Fixed.

## Findings walk

### design-1 — Fixed
Claim: §4.5's `semantic_tokens_range` sketch unconditionally dereferenced
`state.served_tokens.segments`; consequence is an `AttributeError` (client-visible request
error) for any document whose only analysis is a hard failure — a regression from today's
empty-response path at `server.py:590-591` (`good is None` → `SemanticTokens(data=[])`,
verified in current code).
Design now: the range bullet opens with "when `state.served_tokens is None` … return an empty
`lsp.SemanticTokens(data=[])` — the same answer the full handler gives and the same answer
today's `good is None` path gives (`server.py:590-591`)". Test plan item 15 gained the sibling
case: hard-failure-only document gets empty data from **both** `full` and `range`, no crash.
Assessment: the reachable-`None` state was real (`_DocState` defaults `served_tokens` to
`None`; `_store` leaves it untouched on failure). Fix mirrors the full handler and pins it with
a test. Accept.

### design-2 — Fixed
Claim: the original `_analyze_blocking` sketch returned only absolute segments, moving the
O(segments) `delta_encode_segments` pass into `_store` on the loop thread; consequence is
eroding the documented never-block-the-loop property (load-bearing docstring verified at
`server.py:178-183`: "The semantic-token encoding is done here, not on the loop thread…").
Design now: §4.5 worker sketch returns
`tuple[DocumentAnalysis, LineIndex, tuple[list[TokenSegment], list[int]] | None]` with
`served = (segments, features.delta_encode_segments(segments))` computed on the worker; a
following paragraph states the preserved invariant (all O(tokens) encoding stays off the
protocol loop, citing `server.py:178-183`) and keeps per-request range-slice encoding on the
loop thread as today's bounded behavior (`server.py:600`). `_store` rules updated to
`_ServedTokens(version, *served)` with an explicit "`_store` does no encoding work", and
`last_good` stores `segments=served[0]`. The sketch's `served` is built only under
`if analysis.tokens is not None:` (the indentation slip the dispositions note is fixed —
covers complete and partial, excludes failed, per the §4.3 outcome table).
Assessment: fix puts the encode back on the worker at zero cost (worker already holds the
segments) and documents why. Accept.

### design-3 — Fixed
Claim: §4.3's parenthetical "(which guards the parse itself)" understated what the existing
single `try` covers; a plausible restructure narrowing the outer `try` to `parse_text` would
let a success-path classification `RecursionError` escape `analyze()`. Verified in current
code: `engine.py:144-161` — `parse_text`, the failure return, `symbols.extract`, and
`classify.classify` all sit inside the one `try`, with `except RecursionError` at `:161` the
only thing converting a success-path blowup into a reportable `DocumentAnalysis`.
Design now: §4.3's note states what the existing `try` actually guards (parse **and** the
success path's extract + classify), states the restructure invariant (parse-raised and
success-path-classify-raised `RecursionError` both keep today's nesting-depth failed outcome;
only the new inner prefix-classification guard degrades to failed-with-parse-error), and
explicitly forbids narrowing the outer `try` to just `parse_text`. Test plan item 9 gained the
success-path `RecursionError` regression test pinning the invariant.
Assessment: the ambiguity is removed, the invariant is stated and test-pinned. Accept.

## Disputed items

None.

## Approved

3 findings: 3 Fixed verified, 0 Won't-Do, 0 TODOs.

---

## Verdict: APPROVED

All three dispositions are Fixed and verified in the design text; the underlying code claims
(`engine.py:144-161`, `server.py:178-183`, `server.py:590-591`) were independently confirmed
against the source. No unresolved findings.
