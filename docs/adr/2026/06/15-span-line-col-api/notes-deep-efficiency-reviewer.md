# Deep efficiency review — span line/col + text + filename + formatter

Base `8cd6232` → HEAD `b6c0aac`. Branch `span-line-col-api`.
Scope: complexity of the new line/col + text paths; per-call recomputation; per-span allocation;
formatter source scanning. Generated grammar/parser files treated as codegen output (not reviewed for
hand-written efficiency).

Bottom line: the new surface is on cold error-reporting paths (no in-tree caller invokes `line_col` /
`filename` / `format_source_line` outside tests; the only hot integration is the once-per-parser
filename threading in the `_source_text` ctor, which adds nothing per-span). One real finding: the
Rust warm-cache path does NOT match the design's claimed O(log N_lines) amortization — it pays O(N)
`chars().count()` scans on every call regardless of cache state. Everything else checks out.

---

## efficiency-1: Rust `Span::line_col()` is O(N) per call even when `line_ends` is warm — does not meet the design's claimed amortization

File: `crates/fltk-cst-core/src/span.rs:516-535` (`line_col_inner`), `:215-239` (`resolve_line_col`),
`:782-810` (`line_col_or_raise`).

Problem. The design (§2.6.3, §7 item 1) states the Rust backend amortizes line/col lookup to
"O(log N_lines) per call after the first scan" via the `SourceInner.line_ends` `OnceLock` cache,
contrasted against Python's accepted per-call O(N) recompute. The cache for `line_ends` is built once
as designed (partition_point bisect is genuinely O(log N_lines)). BUT the surrounding codepoint-count
computations are recomputed in full on every call and are not cached:

- `line_col_inner` (`span.rs:521`): `let len = source.text.chars().count()` — full O(N) codepoint
  scan, every call, for the `start > len` domain check and the EOF clamp.
- `resolve_line_col` (`span.rs:216`): `let len = text.chars().count()` — a second full O(N) scan,
  every call. After the cache is warm this `len` is consumed only inside the `get_or_init` closure
  (lines 232, 236), i.e. it is dead work on every warm call but is still computed unconditionally
  before the `get_or_init`.
- `line_col_or_raise` (`span.rs:796`): a third `chars().count()` for its own pre-check, then it calls
  `line_col_inner` which does the two scans above — up to three full O(N) scans per raising call.

So warm-cache cost is O(N) (codepoint count of the whole source), not O(log N_lines). The bisect being
O(log N_lines) is swamped by the unconditional linear scans around it.

Consequence. Where it bites: any consumer that resolves many spans against one large source — e.g. an
error reporter or LSP-style diagnostic pass emitting line/col for N findings over a long file — pays
O(source_len) per finding instead of O(log lines). The design sold the Rust backend as the fast path
relative to Python precisely on this point; as implemented the asymptotic advantage over Python's
"accepted because cold" recompute is gone. Cold-path framing still holds for one-shot error reporting,
so this is a design-vs-implementation gap rather than a live hot-path regression — but if a consumer
treats Rust `line_col` as cheap-when-warm (which the design invites), it is not.

Fix direction (pick per appetite; all small):
- Cheapest: in `resolve_line_col`, move the `len = text.chars().count()` *inside* the `get_or_init`
  closure (it is only used there) so warm calls skip it. Removes one of the two scans for free, no
  signature change.
- For the `line_col_inner` / `line_col_or_raise` domain checks: the codepoint count is already known
  once `line_ends` is built — the last sentinel entry equals `len` for non-`\n`-terminated text (and
  `\n`-terminated text's count is recoverable). Alternatively cache the codepoint count on
  `SourceInner` (a second cheap `OnceLock<i64>`, or fold it into the existing `line_ends` init) and
  read it for the `start > len` / EOF-clamp checks instead of rescanning. That brings warm calls to the
  intended O(log N_lines).
- If the team accepts cold-path-only and does not want the cache work, the lower-cost action is to
  correct the design text (§2.6.3, §7 item 1) so it no longer claims warm O(log N_lines) — right now
  the doc overstates the implemented behavior.

Note: the existing `TerminalSource::pos_to_line_col` path does NOT have this problem — `TerminalSource`
carries `cp_to_byte` and derives `len()` as `cp_to_byte.len()-1` in O(1) (`terminalsrc.rs:77-80`), and
its `resolve_line_col` call (`terminalsrc.rs:181`) inherits only the one dead `len` scan from
`resolve_line_col` itself (same line 216). So the parser's own error path is close to the claimed
amortization; only the new pyo3 `Span` path regresses it.

---

## Confirmed clean (checked, no finding)

- Python `terminalsrc.py` per-call line-ends recompute (`Span.line_col`, `terminalsrc.py:137`). Real
  and present: O(N) `[idx for idx,c in enumerate(src) ...]` plus the `bisect` on every call, no cache
  on the frozen+slots `str`-bearing Python `Span`. This is exactly what the design flagged (§7 item 1,
  `TODO(py-span-linecol-cache)`) and consciously accepted as cold. Not re-raised — it is documented,
  bounded to error paths, and has no in-tree hot caller. The legacy `TerminalSource.pos_to_line_col`
  (`terminalsrc.py:267`) correctly caches in `self.line_ends` and builds once.

- Filename threading is once-on-source, not per-span. `SourceInner.filename: Option<String>`
  (`span.rs:50`) stored at construction; `Span.filename()` is a borrow/clone of that one field
  (`span.rs:540-542`, `:814-816`). Python mirrors it: `_source_filename` is a `compare=False,
  hash=False` field populated by `with_source` from `SourceText._filename` (`terminalsrc.py:59`,
  `:223-232`) — no new per-span storage in the equality/hash surface, no per-span allocation. The
  generator change (`gsm2parser.py`) threads `filename` into the single `_source_text` construction
  (once per parser instance), not per span. Matches the design's "once-on-source" requirement.

- `format_source_line` does not scan the whole source. It renders only the offending line: it calls
  `line_col_or_raise()` then `lc.line_span.text()` (`error_formatter.py:53-54`). `line_span` is the
  single-line span `[line_start, line_end)`. On Python, `text()` is an O(line) `str[start:end]` slice.
  On Rust, `Span::text()` (`span.rs:411-452`) is a single `char_indices()` forward pass that breaks at
  `end` — i.e. O(line_end), proportional to the byte offset of the line, not a full-source scan, and it
  already replaced the prior three-restart implementation (comment at `span.rs:422-426`). No caret loop
  scans the source; `" " * lc.col` is O(col). Fine for an error path. (The only residual is the
  `line_col_or_raise` cost in efficiency-1, inherited here.)

- `line_ends` / `cp_to_byte` caches are correct and unbounded-data-safe: both keyed to immutable
  `text`, `OnceLock`-guarded (no staleness, no re-entrancy rebuild), `cp_to_byte` is `shrink_to_fit`'d
  after construction (`terminalsrc.rs:56`). The two-tables-over-one-source duplication is acknowledged
  (`TODO(linecol-cache-consolidate)`, `span.rs:53-57`, `terminalsrc.rs:178-180`) — state duplication,
  a few words/source, not a code or correctness issue. No memory-growth or listener-leak concerns; all
  structures are bounded by source size and freed with the source `Arc`.

- `LineColPos.line_span` getter clones an `Arc` pointer only (O(1), `span.rs:191-193`), not the source
  string — as designed. No per-access string copy.

- No missed concurrency / no recurring no-op state update / no broad-read-when-slice-suffices issues
  in this diff — the surface is pure lazy-compute accessors on immutable data, no loops, intervals,
  handlers, or store updates introduced.

Reviewed: `b6c0aac`.
