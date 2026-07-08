# Design review findings — step4 (M3 prefix-CST exposure + start-rule dedup)

Verification pass at base commit `46c17e5`. The design's factual grounding is very good: every
file/line citation I checked is accurate (`plumbing.py:170-208` failure branch, `plumbing_types.py`
`ParseResult` shape, `engine.py` analyze failure branch, `server.py:140` TODO, rename's
`analysis.error is not None` refusal at `server.py:421-423`, `_encoding()` already called on the
worker at `server.py:194`, `_GoodAnalysis.tokens`/`encoded_tokens` consumed only by the two
semantic-token handlers). External claims verified too: greet's `document := , item*` and
clockwork's `module := … (use* , entity+)` are as quoted; generated star rules return an
`ApplyResult` on a zero-length match (checked `fltklsp_parser.py:parse_lsp_spec__alt0__item0`),
so the zero-length-prefix invariant in §4.1 holds; `ApplyResult` is a plain frozen dataclass
(always truthy when non-`None`), so `prefix_cst = result.result if result else None` is sound;
the "unreleased" claim for the M2 `create_server` API is true (last release tag `v0.2.0` is
commit `29b4dc1`, 2025-07-22, which predates all `fltk/lsp/` work — same for `fltk-highlight`'s
stdout-behavior change); the ADR README's D6 and M3 wording is quoted accurately; and the
memo-cache salvage out-of-scope rationale is code-backed (`memo.py` `MemoEntry` fragments,
`classify.py:174` `AssertionError` in `rule_for_node`). Scope is coherent and requirement
coverage (as scoped by the design itself, which the review brief permits) maps cleanly onto the
test plan. Three findings, all bounded.

---

## design-1: `semantic_tokens_range` behavior is unspecified when `served_tokens is None`

**Section:** §4.5, "Handler changes" — "`semantic_tokens_range`: filter
`state.served_tokens.segments` to those overlapping the requested range …"

**What's wrong:** The full handler's spec explicitly covers the no-served-tokens case ("empty
list when `served_tokens is None`"), but the range handler's spec unconditionally dereferences
`state.served_tokens.segments`. `served_tokens` is `None` whenever a document's first-ever
analysis is a hard failure (design's own `_store` rule: `served_segments is None` → leave
`served_tokens` untouched, and `_DocState` defaults it to `None`) — the same state the current
code reaches via `good is None` and answers with `SemanticTokens(data=[])`
(`server.py:590-591`).

**Why:** `_DocState` gains `served_tokens: _ServedTokens | None = None` (§4.5, "State
reshape"), and edge case 7 / `_store` rules confirm the `None` state is reachable. Nothing in
§4.5 or the test plan (tests 15-17 all have a serveable state) covers the range request
against `None`.

**Consequence:** An implementer following the sketch literally writes
`state.served_tokens.segments` and gets an `AttributeError` crashing the range handler (an LSP
request error surfaced to the client) for any document opened with a hard parse failure —
a behavioral regression from today's empty-response path.

**Suggested fix:** One sentence in §4.5 mirroring the full handler ("empty `SemanticTokens`
when `served_tokens is None`") and fold the case into server test 15 or a sibling.

---

## design-2: delta encoding moves from the worker thread to the loop thread in `_store`

**Section:** §4.5, "`_store` rules" — "set `state.served_tokens = _ServedTokens(version,
served_segments, features.delta_encode_segments(served_segments))`".

**What's wrong:** Today the *entire* token encoding runs inside `_analyze_blocking` on the
worker, and its docstring makes that load-bearing: "The semantic-token encoding is done here,
not on the loop thread, so its O(tokens x line-prefix) cost never blocks the protocol loop"
(`server.py:178-183`). The redesigned `_analyze_blocking` returns only absolute segments; the
`delta_encode_segments` pass (O(segments), plus building the 5-ints-per-segment list) now runs
in `_store`, which is called on the loop thread after every analysis of every document,
including per-keystroke debounced ones. The expensive line-prefix math does stay on the worker,
but the design nowhere acknowledges shifting the encode tail onto the loop thread, and the
shift is avoidable for free: the worker already has `served` in hand and could return
`(served, delta_encode_segments(served))`.

**Why:** §4.5's `_analyze_blocking` sketch returns
`tuple[DocumentAnalysis, LineIndex, list[features.TokenSegment] | None]` — no encoded form —
while the `_store` rule constructs the encoding inline. Contrast `server.py:192-195` (current
worker-side encoding) and the docstring cited above.

**Consequence:** Per-analysis O(segments) work (segment count ≈ token count, i.e. proportional
to document size) lands on the protocol loop for large documents, eroding the documented
never-block-the-loop property that the current code structure deliberately bought — and the
design presents the reshape as preserving that pattern (edge case 8 argues continuity for
`_encoding()` but is silent on the encode itself).

**Suggested fix:** Have `_analyze_blocking` also compute and return
`delta_encode_segments(served)` (or return a ready `_ServedTokens` minus the version); `_store`
just stores it. Note: per-request encoding of range *slices* on the loop thread is today's
behavior (`server.py:600`) and fine to keep.

---

## design-3: §4.3 mischaracterizes what the existing `except RecursionError` guards, making the restructure instruction ambiguous

**Section:** §4.3 — "the existing outer `except RecursionError` (which guards the parse
itself) keeps its current message for the parse-raised case. This requires restructuring the
current single `try` so the prefix-classification guard is separate".

**What's wrong:** The existing single `try` (`engine.py:144-161`) guards the parse **and** the
success path's `symbols.extract` + `classify.classify` (`engine.py:152-160`). Calling it the
guard for "the parse itself" understates its coverage. The design's sketch shows only the new
failure branch; if an implementer takes "guards the parse itself" at face value and narrows the
outer `try` to just the `parse_text` call during the restructure, a `RecursionError` raised
while classifying a *successfully parsed* but deeply nested document — today a clean failed
analysis with the "Input exceeds the maximum nesting depth" message — escapes `analyze()`
entirely.

**Why:** Read `engine.py:144-169`: `parse_text`, the failure return, `symbols.extract`, and
`classify.classify` all sit inside the one `try`; the `except RecursionError` at `:161` is the
only thing that turns a success-path classification blowup into a reportable
`DocumentAnalysis`. The design's guard rails (§6) pin the failure-path shapes but nothing pins
the success-path RecursionError degrade, and the test plan (tests 6-12) has no test for it
either.

**Consequence:** A plausible implementation of the prescribed restructure regresses the
success-path RecursionError handling: in the server the exception propagates out of the worker
into `_debounced_analyze`'s catch-all (logged, but diagnostics never published and stale state
frozen); in `fltk-highlight` it becomes a raw traceback instead of a formatted error + exit 1.

**Suggested fix:** One sentence in §4.3 stating the invariant to preserve: parse-raised and
success-path-classify-raised `RecursionError` both keep producing the current
nesting-depth-failed outcome; only the *prefix*-classification `RecursionError` gets the new
degrade-to-failed-with-parse-error behavior. Optionally add a regression test for the
success-path case (it is currently untested only incidentally).
