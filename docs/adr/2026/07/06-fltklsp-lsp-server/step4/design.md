# Step 4 design: M3 — prefix-CST exposure and degraded-mode serving

Round scope, chosen by this design: **M3** (the milestone skipped by rounds 2 and 3), plus the
small, already-tracked `TODO(lsp-start-rule-dedup)` surface fix that this round's server edits
make cheap to do correctly. Inputs: `step4/exploration.md` (authoritative survey of code at
`46c17e5`), the step1–step3 designs/implementation logs (authoritative for what M0–M2/M4
decided), and the advisory ADR docs (directional only; per the requester, **"NO DECISIONS HAVE
BEEN MADE. This was a brainstorming session. Everything is malleable at this point."**).

## 1. Root cause and context

When a document fails to parse, the analysis pipeline throws away everything it learned:

- `plumbing.parse_text` (`fltk/plumbing.py:170-208`) has exactly one success shape —
  `result` truthy **and** `result.pos == len(terminals.terminals)`. Every other outcome
  returns `ParseResult(None, text, False, error_msg, error_pos=...)`. In the
  early-success-without-full-consumption case, `result.result` at that moment **is a real,
  well-formed CST** for `[0, result.pos)` — the start rule matched; the input just kept going.
  The tree is discarded on the floor of that `if`.
- `AnalysisEngine.analyze` (`fltk/lsp/engine.py:144-170`) consequently returns
  `tree=None, tokens=None, symbols=None` on any failure, and the server
  (`fltk/lsp/server.py`) can only fall back to `_GoodAnalysis` — the last *complete* analysis
  of some older document version — for every feature.

The UX cost of all-stale serving is concentrated in one scenario: **editing a document that
currently has a syntax error further down.** Everything the user types above the error is
served from the old snapshot — new constructs get no highlighting at all, and every edit that
changes text length makes the old token positions drift for the *entire* document. A fresh
prefix fixes both: the region up to the error is exact and current on every analysis, and only
the region past the error degrades to stale. That is precisely the improvement the ADR's D6
sketched ("expose the successfully-parsed prefix CST … so only the region after the error
degrades") — advisory, but confirmed worth doing by this round's own reading of the code.

What the exploration verified about *how* a prefix can be obtained (`step4/exploration.md`
§2), which this design treats as ground truth:

1. **Early success without full consumption** yields an assembled prefix tree for free. For
   real grammars this is the dominant mid-document failure shape: clockwork's
   `module := … (use* , entity+)` and greet's `document := , item*` both have top-level
   repetition, so a broken construct N stops the repetition and the start rule succeeds over
   constructs 1..N-1. No parser or codegen change is needed — only the plumbing's decision to
   keep the tree.
2. **Hard failure** (the start rule itself returns `None`) leaves only per-rule fragments in
   the packrat memo cache (`fltk/fegen/pyrt/memo.py`: `MemoEntry` per `(rule_id, pos)`).
   Nothing assembles them; a salvage pass would be new engineering with real correctness
   hazards (see §3.2). Out of scope this round.

## 2. Deltas from the advisory ADR docs

Following the step1–step3 convention, deviations from the ADR/brainstorm/spec are recorded
here; this design supersedes those documents where they conflict.

- **ADR M3 says "both backends"; this round is Python-plumbing-only.** There is no Rust
  runtime analysis path to change: the Rust side is offline per-grammar codegen compiled by
  the consumer (exploration §3), no analysis-grammar Rust parser exists, and the only Rust
  discard point (`fltk-fmt-cli`'s `fully_consumed`) guards a *formatter*, which must keep
  rejecting partial parses on both backends (formatting a prefix would truncate the user's
  file — see §6). The prefix information itself (`ApplyResult { pos, result }`) already exists
  identically in both parser cores; nothing in this round touches generated code or the parser
  runtime on either backend, so cross-backend parser equivalence is unaffected. Obligation
  recorded for the future: whatever round designs the M5 native analysis path must expose the
  same prefix surface from the native seam.
- **ADR D6's framing "the prefix CST that `parse_text`/`fully_consumed()` currently discard"
  is accurate only for the early-success case.** On hard failure there is no assembled tree
  to expose (exploration §2, verified against `memo.py` and `memo.rs`). This round exposes
  exactly the early-success prefix; memo-cache salvage is explicitly deferred, not silently
  narrowed (§3.2).
- **Degraded-mode serving applies to semantic tokens only.** The ADR's "only the region after
  the error degrades" is implemented as fresh-prefix + clipped-stale-tail for the semantic
  token features; folding, selection, outline, and navigation deliberately keep serving the
  last complete analysis (rationale in §5.4).

## 3. Scope

### 3.1 In scope

1. `plumbing.parse_text` / `ParseResult`: expose the early-success prefix CST and its
   consumed length (additive, defaulted fields; no existing caller changes behavior).
2. `AnalysisEngine.analyze` / `DocumentAnalysis`: a third analysis outcome, **partial** —
   prefix tree, prefix tokens, prefix symbol table, *and* the parse error, plus the prefix
   boundary offset. `highlight()`'s round-1 contract is preserved exactly.
3. `features.py`: factor semantic-token encoding into absolute segments + delta encoding, and
   add a pure merge of fresh prefix segments with clipped stale segments.
4. `server.py`: semantic-token handlers serve fresh-prefix + stale-tail on partial analyses;
   all other features keep the existing last-good policy; rename keeps refusing anything with
   a parse error (already enforced by its `analysis.error is not None` check).
5. `fltk-highlight`: degraded output — on a partial analysis, render the prefix-highlighted
   text to stdout, the error to stderr, and still exit 1.
6. `TODO(lsp-start-rule-dedup)` (`server.py:140`): add a read-only `AnalysisEngine.start_rule`
   property and drop the duplicate `start_rule` parameter from
   `FltkLanguageServer.__init__`/`create_server`.

### 3.2 Out of scope, with rationale

- **Hard-failure memo-cache salvage.** Three reasons, in decreasing order of weight:
  (a) *Correctness*: memo entries include successful sub-parses from ordered-choice branches
  the final parse would never commit to; a greedy longest-entry cover can paint text with
  structure that isn't there. (b) *Type shape*: salvage yields a forest, and every downstream
  walker (`classify`, `symbols.extract`, `features.folding_ranges`, `_spans_containing`)
  assumes a single rule-backed root — `rule_for_node` raises `AssertionError` on any kind not
  derived from a grammar rule, so a synthetic root is a new invariant to design, not a detail.
  (c) *Payoff*: hard failure means no complete top-level construct parsed, which for
  repetition-shaped grammars confines it to errors at the very top of the file, where stale
  serving already covers the gap. Deferred as future work, **not** a `TODO(slug)`: there is no
  evidence yet that anyone needs it, and the TODO convention reserves slugs for concrete work
  that is known to be wanted. Revisit if field experience shows top-of-file errors blanking
  documents in practice.
- **Rust-side changes** (§2, first delta).
- **Parser error recovery** (skip-and-resync, synthetic nodes): explicitly out of scope in
  the ADR and remains so.
- **Partial-analysis serving for folding/selection/outline/navigation** (§5.4).
- **`TODO(lsp-analysis-watchdog)`, `TODO(lsp-classify-hotpath)`,
  `TODO(lsp-rule-surface-index)`, `TODO(lsp-cst-text-helpers)`**: untouched; none of this
  round's changes make them cheaper or dearer. This round adds no new per-analysis tree walks
  on the success path (the partial path runs the same extract+classify the success path runs,
  on a smaller tree).

## 4. Proposed changes, by file

### 4.1 `fltk/plumbing_types.py` — `ParseResult` gains the prefix fields

```python
@dataclass
class ParseResult:
    cst: Any | None
    terminals: str
    success: bool
    error_message: str | None = None
    error_pos: int | None = None
    prefix_cst: Any | None = None
    prefix_pos: int | None = None
```

New-field semantics (docstring must state all of this):

- On success: `cst` is set; `prefix_cst`/`prefix_pos` are `None` (there is no "prefix"
  distinct from the whole parse).
- On failure where the start rule matched but did not consume the input (early success
  without full consumption): `cst` stays `None` and `success` stays `False` — **no existing
  caller's behavior changes** — while `prefix_cst` carries the start rule's CST covering
  `[0, prefix_pos)` and `prefix_pos` carries the consumed codepoint length (`result.pos`).
  `prefix_pos` may be `0` (e.g. `item*` matching zero items); a zero-length prefix is still
  exposed uniformly — the invariant is "prefix present iff the start rule returned a result",
  with no magic thresholds.
- On hard failure (start rule returned `None`) and on the unknown-start-rule early return:
  both prefix fields are `None`.
- `prefix_cst is not None` ⟺ `prefix_pos is not None`.

### 4.2 `fltk/plumbing.py` — `parse_text` keeps the tree it already has

Only the failure branch changes:

```python
if not result or result.pos != len(terminals.terminals):
    error_msg = ...            # unchanged
    error_pos = ...            # unchanged (tracker / result.pos / 0)
    prefix_cst = result.result if result else None
    prefix_pos = result.pos if result else None
    return ParseResult(None, text, False, error_msg, error_pos=error_pos,
                       prefix_cst=prefix_cst, prefix_pos=prefix_pos)
```

No signature change, no parser-runtime change, no generated-code change. The formatter path
(`server._format_blocking`, `fltk-format`-style CLIs, verify-reparse guards) checks
`parsed.success` and is untouched: a prefix is never formatted (§6, "formatter must not
truncate").

### 4.3 `fltk/lsp/engine.py` — the partial analysis outcome

`DocumentAnalysis` gains one field:

```python
prefix_end: int | None = None
```

Three outcome shapes, to be documented in the class docstring as a table:

| outcome  | tree | tokens | symbols | error | prefix_end |
|----------|------|--------|---------|-------|------------|
| complete | set  | set    | set     | None  | None       |
| partial  | set  | set    | set     | set   | set        |
| failed   | None | None   | None    | set   | None       |

Invariant: `prefix_end is not None` ⟺ (`error is not None` and `tree is not None`). In the
partial outcome, `tree`/`tokens`/`symbols` describe the prefix `[0, prefix_end)` of the
*current* text, and `error` is the same `ParseErrorInfo` a failed outcome would carry.

`analyze()`'s failure branch becomes:

```python
if not parsed.success:
    error = ParseErrorInfo(message=parsed.error_message or "", offset=parsed.error_pos)
    if parsed.prefix_cst is None:
        return DocumentAnalysis(tree=None, tokens=None, error=error)
    try:
        symbol_table = symbols.extract(parsed.prefix_cst, self._tables, self._resolved_config, text)
        tokens = classify.classify(parsed.prefix_cst, self._parser_result.grammar,
                                   self._resolved_config, text,
                                   tables=self._tables, symbol_table=symbol_table)
    except RecursionError:
        return DocumentAnalysis(tree=None, tokens=None, error=error)
    return DocumentAnalysis(tree=parsed.prefix_cst, tokens=tokens, error=error,
                            symbols=symbol_table, prefix_end=parsed.prefix_pos)
```

Notes:

- `classify` and `symbols.extract` need **no changes**: both already operate on any subtree
  handed to them (confirmed in step1's design and re-confirmed by this round's reading — the
  walks are structural over `kind`/`span`/`children`).
- A `RecursionError` raised while classifying the prefix degrades to the plain **failed**
  outcome carrying the *parse* error (the more actionable message), not the recursion
  message. Note what the existing single `try` (`engine.py:144-161`) actually guards: the
  parse **and** the success path's `symbols.extract` + `classify.classify`. The invariant the
  restructure must preserve: a `RecursionError` raised by the parse itself *or* by
  success-path extraction/classification keeps producing today's failed outcome with the
  "maximum nesting depth" message; only the new *prefix*-classification guard (the inner
  `try` sketched above) gets the degrade-to-failed-with-parse-error behavior. Do not narrow
  the outer `try` to just the `parse_text` call — that would let a success-path
  `RecursionError` escape `analyze()` entirely.
- Ref-paint inside the prefix resolves against the prefix-only symbol table, so a reference
  to a symbol defined *past* the error paints as default rather than its kind. Known,
  accepted behavior — fresh-and-approximately-painted beats stale-and-misplaced, and the
  stale tail policy (§4.5) covers the region where the definitions went missing.

`highlight()` keeps its round-1 one-of contract **exactly** (pinned by existing tests):

```python
analysis = self.analyze(text)
return HighlightResult(
    tokens=analysis.tokens if analysis.error is None else None,
    error=analysis.error.message if analysis.error is not None else None,
)
```

The explicit `if analysis.error is None` guard is now load-bearing (previously
`analysis.tokens` was always `None` when `error` was set); a comment must say so. Callers
that want degraded output use `analyze()` — that is the CLI change in §4.6.

`AnalysisEngine` also gains the dedup property:

```python
@property
def start_rule(self) -> str | None:
    """The start-rule override this engine parses with; None means the grammar's first rule."""
    return self._start_rule
```

### 4.4 `fltk/lsp/features.py` — segments, delta encoding, and the stale merge

The existing `encode_semantic_tokens` fuses three things: legend lookup, line splitting into
absolute `(line, char, length)` positions, and delta encoding. The merge needs the absolute
middle form as a first-class value, because fresh and stale tokens live in *different
documents' coordinate systems* and can only be combined after each is rendered to absolute
positions against its own `LineIndex`. Refactor:

```python
@dataclasses.dataclass(frozen=True, order=True)
class TokenSegment:
    """One single-line semantic-token segment at an absolute LSP position.

    line/char are in the negotiated encoding's units against the document the segment was
    computed from; length likewise. Self-contained: no LineIndex needed to consume it.
    """
    line: int
    char: int
    length: int
    type_index: int
    modifier_bits: int

def absolute_segments(tokens, line_index, enc) -> list[TokenSegment]: ...
def delta_encode_segments(segments) -> list[int]: ...

def encode_semantic_tokens(tokens, line_index, enc) -> list[int]:
    return delta_encode_segments(absolute_segments(tokens, line_index, enc))
```

- `absolute_segments` is the current loop body minus delta bookkeeping: legend lookup with
  the existing drop-and-warn behavior, `_modifier_bits`, `_line_segments`. Output is sorted
  and non-overlapping because its input token stream is.
- `delta_encode_segments` is the current `prev_line`/`prev_char` tail.
- `encode_semantic_tokens`'s public signature and output are unchanged; a regression test
  pins byte-identical output on streams covering multi-line tokens and astral characters.

The merge:

```python
def merge_stale_segments(
    fresh: list[TokenSegment],
    stale: list[TokenSegment],
    boundary: tuple[int, int],
) -> list[TokenSegment]:
    """Fresh prefix segments plus the stale segments at or past ``boundary``.

    ``fresh`` is computed against the current text, ``stale`` against the last successfully
    analyzed text; ``boundary`` is the (line, char) of the fresh prefix's end in the current
    text. A stale segment is kept iff its start position >= the floor -- the max of
    ``boundary`` and the end position of the last fresh segment -- so the result is sorted
    and non-overlapping even when an edit shifted the stale coordinates backward.
    """
```

Implementation: `floor = boundary`; if `fresh` is non-empty,
`floor = max(boundary, (last.line, last.char + last.length))` (defensive — fresh segments end
at or before the boundary by construction, since fresh tokens are confined to
`[0, prefix_end)`). Append every `stale` segment whose `(line, char) >= floor`. Pure,
independently testable, no server state.

Coordinate honesty: kept stale segments carry positions from the *old* text. That is exactly
today's whole-document stale-serving behavior, now confined to the tail; positions past the
current document's end are clamped or ignored by clients, same as today. No attempt is made
to shift stale positions by edit deltas — the server uses full-document sync and has no edit
deltas to shift by.

### 4.5 `fltk/lsp/server.py` — serving policy

**State reshape.** Semantic-token serving moves out of `_GoodAnalysis` into its own record,
because what the token handlers serve is no longer always "the last complete analysis":

```python
@dataclasses.dataclass(frozen=True)
class _ServedTokens:
    """What the semantic-token handlers serve: absolute segments plus their wire encoding.

    Either a complete analysis's fresh segments, or a partial analysis's fresh-prefix
    segments merged with the clipped stale tail of the previous complete analysis.
    """
    version: int | None
    segments: list[features.TokenSegment]   # sorted, non-overlapping
    encoded: list[int]                       # delta_encode_segments(segments), precomputed
```

- `_DocState` gains `served_tokens: _ServedTokens | None = None`.
- `_GoodAnalysis` **drops** `tokens` and `encoded_tokens` and **gains**
  `segments: list[features.TokenSegment]` (the fresh segments of that complete analysis —
  the stale input to later merges). It keeps `version`, `line_index`, `tree`, `symbols` for
  the features that still serve last-good. `_GoodAnalysis` and `_DocState` are module-private;
  this is not a public-surface change.

**Worker changes.** `_analyze_blocking` gains the stale snapshot as a parameter (read on the
loop thread at submit time — `last_good` is only ever written by `_store` on the loop thread,
so the snapshot is race-free):

```python
def _analyze_blocking(self, text: str, stale: _GoodAnalysis | None)
        -> tuple[DocumentAnalysis, LineIndex, tuple[list[features.TokenSegment], list[int]] | None]:
    analysis = self._engine.analyze(text)
    line_index = LineIndex(text)
    served: tuple[list[features.TokenSegment], list[int]] | None = None
    if analysis.tokens is not None:
        enc = self._encoding()
        fresh = features.absolute_segments(analysis.tokens, line_index, enc)
        if analysis.error is None:
            segments = fresh
        else:
            boundary = line_index.offset_to_position(analysis.prefix_end or 0, enc)
            segments = features.merge_stale_segments(fresh, stale.segments if stale else [], boundary)
        served = (segments, features.delta_encode_segments(segments))
    return analysis, line_index, served
```

The full-stream `delta_encode_segments` pass runs here, on the worker, alongside
`absolute_segments` and the merge — preserving the current docstring's load-bearing property
that all O(tokens) encoding work stays off the protocol loop (`server.py:178-183`). `_store`
only stores. (Per-request encoding of range *slices* on the loop thread is today's behavior
and is kept — slices are bounded by the requested range, not the document.)

`_analysis_for` reads the URI's current `last_good` (or `None`) on the loop thread and passes
it when submitting. The single-flight future's payload type changes from
`(analysis, line_index, encoded)` to `(analysis, line_index, served)` per the signature
above — update the `_inflight` annotation.

**`_store` rules** (existing epoch and version-ordering guards unchanged and now also
protecting `served_tokens`):

- `served is not None` (complete or partial): set
  `state.served_tokens = _ServedTokens(version, *served)` — both the segments and their
  encoding were computed on the worker; `_store` does no encoding work.
- `served is None` (failed, or the degraded-to-failed RecursionError path): leave
  `state.served_tokens` untouched — the previously served stream (which may itself have been
  a merge) keeps serving, mirroring today's keep-serving-stale behavior.
- The `last_good` update keeps its current condition (`analysis.error is None and ...`), now
  storing `segments=served[0]` (on the complete path the served segments *are* the fresh
  segment list). Partial analyses never touch `last_good` — the existing condition already
  guarantees this because partial has `error is not None`.

**Handler changes.** Only the two semantic-token handlers change:

- `semantic_tokens_full`: after `_ensure_analyzed`, return
  `lsp.SemanticTokens(data=list(state.served_tokens.encoded))` (empty list when
  `served_tokens is None`).
- `semantic_tokens_range`: when `state.served_tokens is None` (e.g. a document whose only
  analysis so far is a hard failure), return an empty `lsp.SemanticTokens(data=[])` — the same
  answer the full handler gives and the same answer today's `good is None` path gives
  (`server.py:590-591`). Otherwise filter `state.served_tokens.segments` to those overlapping the
  requested range — keep segments with `(seg.line, seg.char) < (end.line, end.character)`
  and `(seg.line, seg.char + seg.length) > (start.line, start.character)` — then
  `delta_encode_segments` the slice. The current offset-bisect against `good.tokens` and
  `good.line_index` is removed; position-tuple comparison needs no line index at all and is
  correct for stale segments too (their positions are already client-coordinate
  approximations, same as full serving). Segments are sorted, so the window is found with
  two `bisect`es on `(line, char)` keys, preserving the current handler's O(log n + k).

**Everything else is deliberately unchanged:**

- Diagnostics: partial analyses carry `error`, so `_publish` emits the diagnostic exactly as
  for failed ones. No change.
- Folding, selection, outline, definition/references/documentHighlight/prepareRename: still
  `_serveable` → `last_good`. Rationale: for these features *completeness beats freshness*.
  A prefix tree would silently drop every fold, symbol, and reference past the error —
  find-references quietly missing results is worse than serving a complete-but-stale table,
  and an outline/folding view that loses half its entries on every keystroke inside a broken
  region churns the editor UI. Semantic tokens are the one feature where the tradeoff
  inverts, because painting is per-position (a missing token degrades one span, not a query
  answer) and the drift cost of stale positions is visible on every line.
- Rename: `rename_document` refuses when `analysis.error is not None`, which now also covers
  partial — renaming from a prefix-only symbol table would silently miss occurrences past
  the error. Add a test pinning the refusal on a partial analysis; no code change.

**`create_server` signature change** (the `TODO(lsp-start-rule-dedup)` fix, a deliberate
called-out decision, not a drive-by):

```python
def create_server(engine, formatter_config, renderer_config) -> FltkLanguageServer: ...
```

`FltkLanguageServer.__init__` likewise drops `start_rule` and sets
`self._start_rule = engine.start_rule`. `server_cli.py` stops passing it. This removes the
only way to construct a server whose formatting pipeline and analysis engine disagree on the
start rule. It is a breaking change to a Python API that shipped in M2 (July 7, unreleased);
doing it now, before out-of-tree consumers can exist, is the compatibility-conscious moment.
The `fltk-lsp` CLI surface — the consumer-facing entry point — is unchanged. Remove the TODO
comment and the `TODO.md` entry (`lsp-start-rule-dedup`) as part of this round.

### 4.6 `fltk/lsp/highlight_cli.py` — degraded output

`main` switches from `engine.highlight(text)` to `engine.analyze(text)`:

- complete → render to stdout, exit 0 (unchanged behavior).
- partial → render `_render(text, analysis.tokens)` to stdout (the tail past the prefix
  passes through `_sanitize`d and uncolored, which `_render` already does for unpainted
  gaps), print `analysis.error.message` to stderr, exit 1.
- failed → error to stderr, empty stdout, exit 1 (unchanged).

Called-out behavior change: on parse failure the CLI may now emit (sanitized, partially
colored) document text on stdout where it previously emitted nothing. The exit code remains
1, which is the contract scripts should key on; and the CLI is the designated manual test
harness for classification semantics, where seeing the prefix paint is the point. The
docstring's failure-mode sentence must be updated.

`HighlightResult` and `engine.highlight()` are untouched (§4.3), so no other round-1 caller
sees any change.

## 5. Edge cases and failure modes

1. **Zero-length prefix** (`prefix_pos == 0`, e.g. greet's `item*` with a broken first item
   and no leading trivia): partial outcome with an empty/near-empty token list; merge floor
   is `(0, 0)`, so the whole stale stream is kept — byte-equivalent to today's all-stale
   serving. No special case in code.
2. **Prefix ending inside trailing trivia**: repetition rules typically consume trivia after
   the last complete construct, so `prefix_pos` can sit past the last construct's text.
   Harmless — fresh trivia tokens (comments) end at or before it, and the boundary only
   clips stale segments.
3. **Prefix classification raises `RecursionError`** while the parse itself did not: degrade
   to the failed outcome with the original parse error (§4.3). The token stream serves stale,
   as today.
4. **Edit shrinks the document** so stale tail segments start *before* the new boundary or
   even before the last fresh segment: the merge floor drops them; output stays sorted and
   non-overlapping. Stale segments past the new end-of-document survive the merge and are
   clamped/ignored client-side — identical to the existing stale-serving behavior.
5. **First-ever analysis of a document is partial** (opened with an error): no `last_good`,
   so the merge input is empty and the client gets fresh-prefix-only tokens — strictly better
   than today's empty response.
6. **Formatter safety**: `parse_text` still returns `success=False` with `cst=None` for
   every non-total parse, so no formatter or verify-reparse path can ever see a prefix as a
   full tree. This is the invariant that makes prefix exposure safe to add at the plumbing
   layer at all; a test pins that `_format_blocking` declines to format a document that
   parses only as a prefix.
7. **Hard failure after a partial** (e.g. the user breaks the very first construct): worker
   returns `served_segments=None`; `_store` leaves the previous `_ServedTokens` (a merge) in
   place. Serving a stale merge is the same risk class as serving any stale stream.
8. **Encoding**: fresh and stale segments are always produced under the same
   `PositionEncoding` — it is fixed per session at initialize — so segments from different
   document versions are unit-compatible. `_analyze_blocking` already calls
   `self._encoding()` on the worker today (via `encode_semantic_tokens`); that pattern is
   preserved.
9. **Range requests during partial serving** use current-document client coordinates against
   segments that are partly old-document coordinates; the filter is an approximation for the
   stale tail, exactly as approximate as full-stream serving of those same segments.
10. **`version=None` (never-opened, disk-backed) documents**: `_ServedTokens.version`
    participates in the same `analyzed_version` ordering guard as the analysis itself;
    behavior matches the existing stale policy.

## 6. What this round must *not* do (guard rails)

- Never format, rename against, or verify-reparse with a prefix tree. Enforced structurally:
  `ParseResult.cst` stays `None` on any non-total parse, and rename's
  `analysis.error is not None` refusal covers partial.
- Never promote a partial analysis to `_GoodAnalysis`.
- Never change `encode_semantic_tokens` output for complete analyses (byte-pinned).
- Never change `HighlightResult`'s one-of contract or `classify`/`symbols.extract`
  signatures (round-1/round-3 callers stay byte-identical).
- No generated-code, grammar, or Rust changes; no new dependencies; no `Makefile`/`gencode`
  changes.

## 7. Test plan

TDD order: each numbered group is written failing before its implementation lands.

**`fltk/lsp/test_plumbing_prefix.py`** (new; alongside `test_plumbing_error_pos.py`):
1. Greet grammar, error mid-document (`"greet alice.\ngreet 42x.\n"`-style): failure result
   has `success=False`, `cst is None`, `prefix_cst is not None`, `prefix_pos` at the end of
   the first item (± trailing trivia), `error_pos >= prefix_pos`.
2. Hard failure (single-alternative sequence grammar, e.g. `pair := "a" , "b"` on `"ax"`):
   prefix fields `None`, error fields as today.
3. Success: prefix fields `None`.
4. Unknown start rule: all of `error_pos`/`prefix_cst`/`prefix_pos` `None` (existing early
   return untouched).
5. Zero-length prefix (`item*` grammar, garbage input): `prefix_pos == 0`,
   `prefix_cst is not None`.

**`fltk/lsp/test_engine_analyze.py`** (extend):
6. Partial outcome shape: all five fields per the §4.3 table; `prefix_end` equals the
   plumbing `prefix_pos`; every token satisfies `token.end <= prefix_end`.
7. Prefix symbols: a `def` before the error appears in `symbols`; one after it does not.
8. Ref before the error to a def after it: paints default (documented degradation), does not
   crash.
9. Failed outcome unchanged (hard-failure grammar): `prefix_end is None`, tokens `None`.
   Also unchanged: a document that *parses successfully* but raises `RecursionError` during
   classification still yields the failed outcome with the nesting-depth message (pins the
   §4.3 restructure invariant; today this behavior is only incidentally covered).
10. Complete outcome regression: `prefix_end is None` and tokens byte-identical to
    pre-change expectations.
11. `highlight()` on a partial analysis returns `tokens=None, error=<message>` (contract
    pin).
12. `AnalysisEngine.start_rule` property round-trips the constructor argument and `None`.

**`fltk/lsp/test_features.py`** (extend):
13. `delta_encode_segments(absolute_segments(...)) == ` byte-for-byte the pre-refactor
    `encode_semantic_tokens` expectations, including multi-line tokens, astral characters
    under UTF16, and the unknown-type/unknown-modifier drop paths.
14. `merge_stale_segments`: fresh-only (empty stale); stale-only (empty fresh, boundary
    `(0,0)` keeps all); boundary clipping (stale segment starting before boundary dropped,
    at boundary kept); floor from last fresh segment beats an earlier boundary; result
    sorted and non-overlapping in every case.

**`fltk/lsp/test_server.py`** (extend, in-process + pytest-lsp as per existing patterns):
15. Open a document with a mid-file error (no prior good version): `semanticTokens/full`
    returns exactly the fresh prefix encoding; tail contributes nothing. Sibling case: a
    document whose only analysis is a *hard* failure (`served_tokens is None`) gets empty
    data from **both** `semanticTokens/full` and `semanticTokens/range` — no crash.
16. Open a good document, then `didChange` introducing a mid-file error: full tokens =
    fresh prefix segments + stale segments clipped at the boundary (assert on decoded
    positions, not just lengths).
17. `semanticTokens/range` inside the prefix and spanning the boundary on the partial state.
18. Folding/selection/documentSymbol/definition during partial: still served from the last
    complete analysis (assert a symbol past the error is still reported).
19. Rename during partial: refused with the parse-errors message.
20. Hard failure after a partial: previously served (merged) tokens still served.
21. `create_server(engine, fmt, renderer)` new signature; formatting still parses with the
    engine's start rule (regression for the dedup change).
22. Diagnostics on partial: one Error diagnostic at `error_pos`, exactly as failed.

**`fltk/lsp/test_highlight_cli.py`** (extend):
23. Partial: stdout contains sanitized full text with ANSI paint confined to the prefix,
    stderr carries the parse error, exit code 1.
24. Hard failure: stdout empty, stderr error, exit 1 (regression).

**`fltk/lsp/test_dogfood.py`** (extend):
25. `.fltklsp` source with an error partway through, analyzed by the dogfood engine:
    partial outcome with painted prefix (uses the existing highlighting-only
    `fltklsp.fltklsp` fixture, which per step3 must not grow def/ref statements).

## 8. Explicitly deferred future work

- Hard-failure prefix salvage from the memo cache (§3.2) — needs its own exploration round
  if wanted.
- Native (M5) analysis path must expose the same prefix surface (§2).
- `expected_context`-driven terse diagnostics / completion — untouched seam, as recorded in
  step2 §7.

## 9. Open questions

None. The two judgment calls this round makes — the `create_server` signature break and the
`fltk-highlight` stdout-on-failure change — are decided and called out in §4.5/§4.6 for
review rather than left open: both surfaces are pre-release and days old, and deferring
either would let out-of-tree consumers form around the worse contract.
