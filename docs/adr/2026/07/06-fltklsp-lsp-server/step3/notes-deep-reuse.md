# Deep reuse review — step3 (M4 defs/refs/namespace)

Round base: 1ad3141. HEAD: 8966d8ee42840c5f7fbf26090b14ef20eafc28e0.

## reuse-1

- `fltk/lsp/symbols.py:205-219` (`_walk`'s per-child dispatch) vs `fltk/lsp/classify.py:251-262`
  (`_explicit_intervals`'s per-child dispatch).
- Both functions duplicate the identical ~12-line block that turns one `(label, child)` pair of a
  CST node into `is_span`, `cstart`/`cend`, `child_text`, `child_rule_name`, and `label_name`:
  check `child.kind == SpanKind.SPAN`, branch to `child.start/end` + source-text slice vs
  `child.span.start/end` + `rule_for_node(child, tables).name`, then `label.name if label is not
  None else None`. `symbols.py` even calls `classify.rule_for_node` directly to do it, rather than
  sharing a helper — the design doc (`step3/design.md` §4.2) itself notes extraction is "the same
  structural walk shape as `classify._explicit_intervals`" but the implementation still pastes the
  shape a second time instead of factoring it out.
- Existing/reused elsewhere: `classify.rule_for_node` (`classify.py:164-175`, promoted to public
  this round precisely so `symbols.py` could reuse it) and `lsp_config.match_applies`
  (`lsp_config.py:473-489`, moved this round for the same sharing reason) show the round's own
  precedent of factoring out CST-walk primitives into shared functions — the per-child shape
  extraction (`is_span`/`cstart`/`cend`/`child_text`/`child_rule_name`/`label_name`) was the next
  obvious candidate and was left inline in both call sites instead.
- Consequence: any future change to how a child's shape is derived (e.g. a new `SpanKind`, a
  change to how node-child rule names are resolved) must be made in both places by hand; the
  `TODO(lsp-classify-hotpath)` note in `classify.py:400-402` already tracks unifying the *tree
  walks* (symbols/explicit/defaults) into one pass for performance, but a shared child-dispatch
  helper would remove this duplication immediately, independent of that larger unification, and
  reduce the risk the two copies quietly diverge (e.g. one is updated for a grammar-shape edge
  case and the other isn't) before that unification ever lands.

## reuse-2

- `fltk/lsp/test_server.py:86-95`, new helper `_line_col(text, offset, enc)`.
- Re-implements codepoint-offset → LSP `(line, character)` conversion (line counting by `\n`,
  UTF-16 character counting via `len(col_text.encode("utf-16-le")) // 2`) instead of using
  `fltk.lsp.positions.LineIndex.offset_to_position`, the module already built and tested for
  exactly this conversion and already relied on elsewhere in the same test suite
  (`fltk/lsp/test_features.py` builds an `IDX = LineIndex(...)` and calls
  `offset_to_position`/feeds it through `features._render_range` rather than hand-rolling the
  math). `test_server.py` even imports `fltk.lsp.positions.PositionEncoding` already (line 24),
  just for monkeypatching `_encoding`, not for this conversion.
- `LineIndex`'s implementation (`fltk/lsp/positions.py:29-58`) additionally recognizes `\r\n` and
  lone `\r` as line separators and counts astral characters as width-2 UTF-16 units per codepoint
  (`_column`, `positions.py:79-83`); `_line_col` only splits on `\n` and computes UTF-16 length via
  `str.encode`, a narrower reimplementation that happens to agree with `LineIndex` for the
  `\n`-only, single-line-astral fixtures used in this round's tests.
- Consequence: a second, independently-maintained position-math implementation in the test suite
  can silently diverge from `LineIndex` (e.g. if a future test adds `\r\n` fixtures, or `LineIndex`
  changes its surrogate-pair handling) — at that point `_line_col`-derived expected values and the
  server's actual `LineIndex`-derived positions could both look self-consistent while masking a
  real regression, since the test would no longer be checking the server against the canonical
  conversion. Calling `LineIndex(text).offset_to_position(offset, enc)` (with a small
  `t.PositionEncodingKind` → `PositionEncoding` mapping) would remove the duplicate and keep the
  test asserting against the same math the server uses.
