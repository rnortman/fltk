# Judge verdict — deep review (round 2, M2 fltk-lsp)

Phase: deep. Base 9719bab7..HEAD c852131f (round-1 fixes in 6e3a55d; rework in c852131). Round 2.
Round 1 returned REWORK on a single disposition (efficiency-3: TODO failed rubric Q2 — do-now).
All 26 other dispositions were verified and accepted in round 1; only the reworked item and its
knock-on hygiene are re-examined here. Verified by direct diff inspection of 6e3a55d..c852131 and a
full run: `uv run pytest fltk/lsp/ -q` → 196 passed at HEAD.

## Added TODOs walk

### quality-5 — TODO(lsp-start-rule-dedup) at `fltk/lsp/server.py` (`FltkLanguageServer.__init__`)
Unchanged from round 1; accepted there (Q1 yes — real latent drift between engine and server
`start_rule`; Q2 yes — the fix removes a design-§4.7-specified parameter from new public surface,
a deliberate surface decision requiring a design amendment). Still present and unmodified at HEAD.
Assessment: TODO acceptable (unchanged).

### efficiency-3 — formerly TODO(lsp-range-token-bisect)
No longer a TODO — repromoted to Fixed per the round-1 verdict. Walked below with the other
findings. Hygiene: `git grep lsp-range-token-bisect` at HEAD finds the slug only in the
dispositions doc's description of the removal; the `server.py` comment and the `TODO.md` entry are
both gone. Clean.

## Other findings walk

### efficiency-3 — Fixed (reworked)
Claim: `semantic_tokens_range` scanned all of `good.tokens` linearly per range request, recurring
at scroll frequency on the protocol loop thread.
Diff (6e3a55d..c852131, `server.py:475-483`): the linear
`[token for token in good.tokens if token.start < end and token.end > start]` is replaced by
`lo = bisect.bisect_right(tokens, start, key=lambda tok: tok.end)` and
`hi = bisect.bisect_left(tokens, end, key=lambda tok: tok.start)`, slicing `tokens[lo:hi]`.
Correctness check: `good.tokens` is documented sorted by `start` and non-overlapping, so `end` is
monotonic; `bisect_right` on `end` yields the first token with `end > start`, `bisect_left` on
`start` yields the first token with `start >= end` — the slice is exactly the overlap window
`{t : t.end > start and t.start < end}` the old predicate computed, in O(log n + subset).
`key=` is valid on the project's Python floor (3.10). `import bisect` added. The comment explains
the invariant the bisects rely on — contract language, no workflow references.
Tests: `test_semantic_tokens_range_returns_line_subset` (added for test-2 in round 1) pins the
subset/delta-basing behavior and passes; full LSP suite 196 passed at HEAD.
The subset re-encode remaining on the loop matches the half of the finding the reviewer explicitly
allowed accepting (small subset); accepted in round 1.
Assessment: this is precisely the fix the round-1 verdict prescribed, implemented correctly, within
design §4.7's filter-then-encode structure. Accept.

### All other findings (26)
Verified and accepted in round 1 (see that walk, preserved in the dispositions doc's per-item
records): errhandling-1..4, correctness-1..2, security-1, test-1..7, reuse-1, quality-1..4/6/7,
efficiency-1/2/4 Fixed and verified against the d9ab841..6e3a55d diff; reuse-2 Won't-Do sound
(design §4.5 quote — delegating conversion math to pygls internals would reintroduce the exact
coupling this round converted to fail-closed). The rework commit touches only `server.py`'s range
handler, the removed TODO comment, `TODO.md`, and the dispositions doc — no accepted disposition is
disturbed. Not re-walked.

## Disputed items

None. The single round-1 dispute (efficiency-3) is resolved by the rework.

## Approved

27 findings: 25 Fixed verified (including three multi-reviewer reconciliations and the reworked
efficiency-3), 1 Won't-Do sound (reuse-2), 1 TODO acceptable (quality-5). Test suite green at HEAD
(196 passed).

---

## Verdict: APPROVED

The round-1 REWORK item is fixed exactly as prescribed; all other dispositions stand as verified in
round 1.
