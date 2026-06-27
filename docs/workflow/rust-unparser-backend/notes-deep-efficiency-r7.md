# Deep efficiency review — batch 7 (rust-unparser-backend)

Commit reviewed: 1fcae0bbe0063b83b1883eb439ababc9da6916d4 (base 72ea1e4…).
Scope: emitted-runtime perf of the generated unparser (generator
`fltk/unparse/gsm2unparser_rs.py`) plus the two tiny crate additions
(`separator_spec`, `last_was_trivia`). Crate additions are trivial and fine.

## efficiency-1 — newline counting allocates a full String per inter-token gap

Emitted code (generator sites):
- `fltk/unparse/gsm2unparser_rs.py:1126` — trivia-rule branch emits
  `let newline_count = span.text().map(|t| t.matches('\n').count()).unwrap_or(0);`
- `fltk/unparse/gsm2unparser_rs.py:1407` — `_count_newlines_in_trivia` emits the
  same `span.text().map(|t| t.matches('\n').count())…` per `Span` child.

Problem: the only CST span accessor is `Span::text() -> Option<String>`
(`crates/fltk-cst-core/src/span.rs:421`), which heap-allocates an owned copy of
the span's text (`src[bs..be].to_owned()`). The generated newline counter
allocates that String purely to scan it for `\n` and immediately drops it. There
is no borrowing accessor today. Worse, `text()` translates codepoint→byte offsets
by scanning `char_indices()` from byte 0 of the *whole source* up to `end`
(span.rs:440), so each call is O(end-from-source-start), independent of the
allocation.

Consequence: this is the inter-token-gap hot path. In the formatting use case
(capture_trivia=True — exactly what the parity harness exercises) every WS gap in
the input pays one heap allocation + memcpy of the whitespace/trivia text, plus an
O(end) prefix scan of the source. Across a large source the per-gap O(end) scans
compound toward O(n²) in source size, with N discarded String allocations on top.
Bites at scale (large files / many gaps), which is precisely where a formatter is
used.

Fix direction: add a borrowing `Span::text_str(&self) -> Option<&str>` to
fltk-cst-core (return `Some(&src[bs..be])`; lifetime tied to `&self`, which holds
the source `Arc`) and have the generator emit `.text_str()` in the two
newline-counting sites — `span.text_str().map(|t| t.matches('\n').count())`. Keep
`.text()` (owned) only where a `String` is actually consumed, i.e. the regex term
body (`gsm2unparser_rs.py:953`, `add_non_trivia(text(text))`). This removes the
per-gap allocation; the residual O(end) scan would need a byte-offset cache to
address and is out of scope here.

## efficiency-2 — trivia children walked twice per gap when `preserve_node_names` is set

Emitted code: `_gen_non_trivia_rule_processing` emits, per gap,
`self._has_preservable_trivia(&trivia_node)` (gsm2unparser_rs.py:1246) followed by
either `self.unparse__trivia(&trivia_node)` (preservable, :1248) or
`self._count_newlines_in_trivia(&trivia_node)` (:1262). When
`trivia_config.preserve_node_names` is a non-empty filtered set, the emitted
`_has_preservable_trivia` body loops every trivia child
(gsm2unparser_rs.py:1375), then the follow-up call loops them all again.

Consequence: an extra O(trivia-children) pass per inter-token gap, only in the
configured-preserve-names case (when `preserve_node_names is None` the helper is a
constant `true` with no walk; empty filter is constant `false`). Bounded by trivia
size, so minor — and it is a faithful mirror of the Python backend's two-pass
structure. Noted for completeness; combined with efficiency-1 it doubles the
allocating `span.text()` calls over the same children in that branch (the
text_str fix above neutralizes the allocation half regardless).

No other findings: `node.children()` is a free slice accessor (returns
`self.children.as_slice()`), so the repeated inline `node.children()` calls in the
trivia branches cost nothing; accumulator `clone()`/`doc()` flattening is the
intended cheap-Rc / per-merge linear behavior; the PyO3 binding runs the pipeline
once per call.
