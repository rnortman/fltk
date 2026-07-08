# Deep-quality review notes — step4 (dcac826..1060867)

Reviewed with a long-term-owner lens: diff plus full reads of `fltk/lsp/server.py`,
`fltk/lsp/engine.py`, and the design (`step4/design.md`). The core mechanics are sound — the
merge invariants, the off-loop encoding property, and the `highlight()` one-of contract all
hold as designed. Findings below.

## quality-1: `_ServedTokens.version` is write-only — redundant state

- `fltk/lsp/server.py:120` (field), `fltk/lsp/server.py:250` (only write). No read anywhere:
  the handlers consume only `.segments`/`.encoded`, and the ordering guarantee actually comes
  from `_store`'s `analyzed_version` guard (`server.py:243`), which runs *before* the
  `served_tokens` write.
- The design (§4.5 edge case 10) says the version "participates in the same
  `analyzed_version` ordering guard" — it is *protected by* that guard, not consulted. The
  field duplicates information `_DocState.analyzed_version` already owns.
- **Consequence**: a dead field on a serving record invites the false belief that
  version-consistency is checked at serve time, and future state records copied from this
  pattern will carry the same unread bookkeeping. When someone later needs real per-stream
  versioning, they will have to first establish that this field was never load-bearing.
- **Fix**: drop `version` from `_ServedTokens` and note in its docstring that staleness
  ordering is enforced by `_store`'s `analyzed_version` guard before the write. (If serve-time
  version checking was actually intended, read the field in the handlers instead — but nothing
  in the design's serving policy requires it.)

## quality-2: `_ServedPair` tuple and `_ServedTokens` are two shapes for one value

- `fltk/lsp/server.py:44` (`_ServedPair = tuple[list[TokenSegment], list[int]]`),
  `server.py:221` (worker builds the tuple), `server.py:249-250` (`_store` immediately unpacks
  it and rewraps the same two values into `_ServedTokens`).
- The worker computes exactly the payload the handlers serve, but hands it across as an
  anonymous positional tuple that gets re-boxed one call later. With quality-1 applied
  (`version` dropped), `_analyze_blocking` can construct and return `_ServedTokens | None`
  directly; the `_ServedPair` alias, the tuple unpack in `_store`, and the `*fresh`/`*stale`
  splats in tests all simplify to a single named type.
- **Consequence**: two representations of the same value drift independently — any future
  field added to the served payload must be threaded through both the tuple alias and the
  dataclass, and positional `tuple[list[...], list[int]]` signatures are the kind of thing
  that silently survives an argument-order mistake.
- **Fix**: make `_analyze_blocking` return
  `tuple[DocumentAnalysis, LineIndex, _ServedTokens | None]` and delete `_ServedPair`.

## quality-3: prefix-classification `RecursionError` is swallowed with no telemetry

- `fltk/lsp/engine.py:177-180`: when classifying an assembled prefix raises
  `RecursionError`, `analyze()` degrades to the plain failed outcome carrying the parse
  error. The degrade itself is the designed behavior (§4.3), but it is *silent*: the returned
  `DocumentAnalysis` is indistinguishable from an ordinary hard failure, and nothing is logged.
- Contrast the sibling paths: the outer `RecursionError` handler at least surfaces "maximum
  nesting depth" in the error message the user sees, and `features.absolute_segments` logs a
  warning when it drops an unknown token type. This new error path is the only one whose
  occurrence leaves no trace anywhere.
- **Consequence**: during an incident ("highlighting for this file went fully stale even
  though only the tail is broken"), there is no way to tell from logs or client state that a
  prefix *was* assembled and classification blew up. Field evidence for the deferred
  hard-failure salvage work (§3.2 says "revisit if field experience shows...") also depends on
  this kind of signal existing.
- **Fix**: add a module logger to `engine.py` (matching `features.py`'s convention) and emit a
  `warning` in this handler, e.g. noting the prefix length that was abandoned. One line; the
  event is rare by construction, so it cannot become noise.

## quality-4: `analysis.prefix_end or 0` masks an invariant violation

- `fltk/lsp/server.py:218`: on the partial branch (`tokens is not None and error is not
  None`), `DocumentAnalysis`'s documented invariant guarantees `prefix_end is not None`, yet
  the code defensively falls back with `or 0`. The idiom also conflates the legitimate value
  `0` with `None` (harmless today only because the fallback happens to be `0` too).
- **Consequence**: if the engine invariant ever regresses (a partial outcome without
  `prefix_end`), the server silently computes boundary `(0, 0)` and serves a plausible-looking
  merged stream instead of failing loudly — exactly the hard-to-diagnose "why is highlighting
  subtly wrong" class of bug the invariant table in `DocumentAnalysis` was written to prevent.
  Defensive fallbacks that hide broken invariants also propagate: the next consumer of
  `prefix_end` will copy the `or 0`.
- **Fix**: trust the documented invariant — `assert analysis.prefix_end is not None` (with the
  invariant cited) before computing the boundary, mirroring the `assert analysis.tokens is not
  None` narrowing already used in `highlight_cli.py`.

## Checked and clean

- Comment hygiene: no design-doc references or changelog-style comments in the shipped code;
  the load-bearing-guard comment in `engine.highlight()` and the merge/bisect comments describe
  current behavior.
- No workaround-for-existing-bug patterns: the plumbing change fixes the discard at its source
  rather than papering over it downstream.
- `TODO(lsp-start-rule-dedup)` removal is complete on both sides (code comment and `TODO.md`),
  matching the TODO-system convention.
