# Implementation log — step4: M3 prefix-CST exposure and degraded-mode serving

## Increment 1 — analysis-layer prefix exposure + CLI degraded output

Through-line: expose the early-success prefix CST end-to-end through the parse and analysis layers
and the `fltk-highlight` CLI (design §4.1–§4.3, §4.6). No `features.py` or `server.py` changes
(deferred to later increments). Tree stays buildable: the server's existing `_analyze_blocking`
guard (`analysis.error is None and analysis.tokens is not None`) and `_store` last-good condition
(`analysis.error is None and ...`) already exclude partial analyses, so a partial keeps serving
stale exactly as a failed one did today — verified by the full `test_server.py` suite passing
unchanged.

- `fltk/plumbing_types.py:33-46`: `ParseResult` gains defaulted `prefix_cst`/`prefix_pos` fields
  with the §4.1 docstring semantics (present iff the start rule returned a result; may be a
  zero-length prefix).
- `fltk/plumbing.py:199-210`: `parse_text` failure branch sets `prefix_cst=result.result`/
  `prefix_pos=result.pos` on early success without full consumption, both `None` on hard failure
  (`result is None`). No signature/parser/generated-code change.
- `fltk/lsp/engine.py:51-79`: `DocumentAnalysis` gains `prefix_end` + the three-outcome docstring
  table. `:130-192`: `analyze()` failure branch restructured for the partial outcome — an inner
  `try` guards prefix extract+classify and degrades to failed-with-parse-error on `RecursionError`;
  the outer `try` still covers the parse and the success path's extract/classify (nesting-depth
  degrade preserved). `:113-116`: read-only `start_rule` property. `:180-190`: `highlight()`'s
  `error is None` guard on `tokens` made explicit and load-bearing (partial now carries tokens).
- `fltk/lsp/highlight_cli.py:100-118`: `main` switches from `engine.highlight` to `engine.analyze`;
  partial paints the prefix (uncolored tail passes through) to stdout, prints the error to stderr,
  exits 1; hard failure keeps empty stdout + exit 1. Docstring failure-mode sentence updated.
- Tests: `test_plumbing_prefix.py` (new; groups 1–5). `test_engine_analyze.py` extended (groups
  6–12 + prefix-classification-recursion edge case); the two pre-existing failure tests
  (`test_analyze_failure_has_structured_error_with_offset`, `test_analyze_failure_has_no_symbol_table`)
  were repointed at a new non-repetition `_HARD_GRAMMAR` because HELLO/REF are repetition-shaped and
  their old inputs now yield zero-length-prefix *partials*, not failed outcomes. `test_highlight_cli.py`
  (groups 23–24: `test_parse_failure_exits_1` replaced by a partial-paints-prefix test + a
  hard-failure empty-stdout test). `test_dogfood.py` (group 25).
- Deferred to later increments (design items not yet in the log): §4.4 features segments/delta/merge,
  §4.5 server serving policy + `create_server`/`__init__` start-rule dedup (`TODO(lsp-start-rule-dedup)`
  still live at `server.py:140`).

## Increment 2 — features.py segment/delta refactor + stale merge

Through-line: the pure semantic-token encoding surface (design §4.4). No `server.py` changes — the
server still calls `encode_semantic_tokens` unchanged (byte-pinned), so the tree stays buildable;
§4.5 (server serving policy + start-rule dedup, `TODO(lsp-start-rule-dedup)` still live at
`server.py:140`) is the final increment.

- `fltk/lsp/features.py:74-93`: new `TokenSegment` frozen `order=True` dataclass (`line`, `char`,
  `length`, `type_index`, `modifier_bits`), self-contained absolute-position segment; field order
  makes natural ordering positional so a sorted token stream yields a sorted segment list.
- `fltk/lsp/features.py:137-160`: `absolute_segments` — the old encode loop body minus delta
  bookkeeping (legend lookup + drop-and-warn, `_modifier_bits`, `_line_segments`), emitting
  `TokenSegment`s.
- `fltk/lsp/features.py:163-179`: `delta_encode_segments` — the old `prev_line`/`prev_char` delta
  tail, now over segments.
- `fltk/lsp/features.py:182-189`: `encode_semantic_tokens` reduced to
  `delta_encode_segments(absolute_segments(...))`; signature/output unchanged.
- `fltk/lsp/features.py:192-217`: `merge_stale_segments(fresh, stale, boundary)` — pure merge, floor
  = `max(boundary, end of last fresh segment)`, keeps stale segments with `(line, char) >= floor`;
  result sorted and non-overlapping by construction. No stale-position shifting (full-doc sync).
- Tests: `test_features.py` groups 13 (`absolute_segments` sort/split + drop paths;
  `delta_encode_segments` empty; composition byte-identical to `encode_semantic_tokens` across
  multi-line, astral-UTF16, and both drop paths) and 14 (`merge_stale_segments`: fresh-only,
  stale-only boundary-(0,0), boundary clipping, floor-from-last-fresh, sorted+non-overlapping).
- `import dataclasses` added; `import itertools` added to the test module (pairwise non-overlap
  check). ruff + pyright clean on both files; full `test_features.py` (41) and `test_server.py` (33)
  pass — the latter confirms the byte-pin.

## Increment 3 — server serving policy + start-rule dedup

Through-line: the final design item, §4.5 — reshape server semantic-token serving to `_ServedTokens`
(fresh-prefix + clipped-stale-tail merge) and land the `TODO(lsp-start-rule-dedup)` signature fix.
Closes the design; `make check` passes green.

- `fltk/lsp/server.py:89-129`: `_GoodAnalysis` drops `tokens`/`encoded_tokens`, gains
  `segments: list[features.TokenSegment]` (the fresh segments a later partial merges against); new
  `_ServedTokens` frozen record (`version`, `segments`, `encoded`); `_DocState` gains
  `served_tokens`.
- `fltk/lsp/server.py:35-45`: TYPE_CHECKING-only `_ServedPair`/`_AnalysisResult` aliases (worker
  output type); dropped the now-unused `classify` import.
- `fltk/lsp/server.py:124-148`: `__init__` drops the `start_rule` param and sets
  `self._start_rule = engine.start_rule`; `_inflight` retyped to `_AnalysisResult`.
- `fltk/lsp/server.py:178-233`: `_analyze_blocking(text, stale)` computes absolute segments, the
  §4.4 stale-tail merge (partial) or the fresh list (complete), and the delta encoding — all on the
  worker; `_store(..., served, ...)` sets `served_tokens` when `served is not None` and promotes to
  `last_good` only on the complete path; `_analysis_for` snapshots `last_good` on the loop thread
  and passes it in.
- `fltk/lsp/server.py:566-586`: `semantic_tokens_full`/`semantic_tokens_range` serve
  `state.served_tokens` (empty when `None`); the range handler bisects the sorted segments on
  position tuples (no line index) and `delta_encode_segments` the slice.
- `fltk/lsp/server.py:546-557`: `create_server` drops the `start_rule` keyword; `server_cli.py:66`
  stops passing it. `TODO(lsp-start-rule-dedup)` comment removed; `TODO.md` entry deleted.
- Tests (`test_server.py`): updated the 5 in-process call sites to the new `_analyze_blocking(text,
  stale)` / `create_server(...)` signatures; added a `client_rule` fixture (`--rule greeting`, the
  only way to force a *failed* analysis since `document := , item*` never hard-fails) + `_decode`/
  `_range_tokens` helpers. New tests (groups 15–22): partial-on-open fresh-prefix + diagnostic;
  hard-failure empty from both handlers; didChange mid-file merge (fresh line-0 `alicia` len-6 +
  stale line-1 tail); range on partial (prefix subset + stale tail partition); documentSymbol from
  last-good during a zero-length-prefix partial; rename refused on partial; hard-failure-after-
  partial keeps serving; `create_server` reads the engine's start rule and formats with it.
- Deviation: group 15's hard-failure sibling and group 20 needed a start rule that can hard-fail;
  used `--rule greeting` (a `client_rule` fixture) rather than the default `document` rule, which
  always assembles at least a zero-length prefix.
