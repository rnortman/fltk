# Reuse review — span-line-col-api (8cd6232..b6c0aac)

## reuse-1 — Python bisect logic duplicated between `Span.line_col` and `TerminalSource.pos_to_line_col`

**Files:**
- `fltk/fegen/pyrt/terminalsrc.py:137-158` (`Span.line_col`, bisect body)
- `fltk/fegen/pyrt/terminalsrc.py:273-296` (`TerminalSource.pos_to_line_col`, bisect body)

**What is duplicated:** The full line-ends build-and-bisect algorithm appears twice in the same Python file. Both copies build `line_ends` identically (lines of `[idx for idx, c in enumerate(src) if c == "\n"]`), apply the same sentinel logic (`src_len if src_len > 0 else -1`), run `bisect.bisect_left`, and compute `(col, line_start, line_end)` with the same arithmetic. The only observable differences are: `Span.line_col` always rebuilds the table from scratch (no cache — noted as `TODO(py-span-linecol-cache)`), while `TerminalSource.pos_to_line_col` caches in `self.line_ends`; and `Span.line_col` produces a source-bearing `line_span` while the legacy method produces a sourceless one.

**Existing function:** The Rust side of this change (§2.5) consolidated this into `fltk_cst_core::resolve_line_col` (`crates/fltk-cst-core/src/span.rs:215`), which is now the single Rust copy. The Python side was explicitly left as two copies — the design acknowledges this in §2.5 final paragraph and §7, and the `TODO(py-span-linecol-cache)` comment at `terminalsrc.py:133` flags the uncached-scan issue. There is no Python equivalent of `resolve_line_col`.

**Consequence:** The two Python copies will diverge independently. Any future fix to the bisect logic (e.g., a corner-case correction, tab-width policy change) must be applied in both places. The sentinel logic and the `bisect_left` body are already byte-for-byte identical, which is the classic sign of copy-paste that will drift. This is the Python analogue of exactly what the Rust move-down fixed on the Rust side, and the design explicitly defers it (no extraction into a shared helper like `_bisect_line_col(src, pos)` that both could call). The `TODO(py-span-linecol-cache)` comment in `line_col` names the caching gap but not the duplication gap.

---

## reuse-2 — `TerminalSource.line_ends` cache vs `SourceInner.line_ends` cache (two tables over same immutable text, Rust side)

**Files:**
- `crates/fltk-parser-core/src/terminalsrc.rs:34` — `TerminalSource.line_ends: OnceLock<Vec<i64>>`
- `crates/fltk-cst-core/src/span.rs:58` — `SourceInner.line_ends: OnceLock<Vec<i64>>`

**What is duplicated:** After this change, when a `TerminalSource` is built over a `SourceText` (the common parser path), both the `TerminalSource` and the underlying `SourceInner` hold independent `OnceLock<Vec<i64>>` caches derived from the same immutable `text`. Both are populated by `resolve_line_col` on first use, both are correct (the text is immutable so both derive deterministically), but two O(N) scans over the source text can occur and two heap allocations hold the same data.

**Existing consolidation path:** `crates/fltk-parser-core/src/terminalsrc.rs:178-180` contains the `TODO(linecol-cache-consolidate)` comment: "A future consolidation could pass `&self.source.inner.line_ends` here." That would make `TerminalSource::pos_to_line_col` pass `&self.source.inner.line_ends` to `resolve_line_col` instead of `&self.line_ends`, eliminating the `TerminalSource`-level cache entirely and making the shared `SourceInner` cache the single copy. The hook is already wired — `resolve_line_col` accepts the cache by reference, so calling `resolve_line_col(self.text(), pos, &self.source.inner.line_ends)` is a one-line change that would complete the consolidation. The `TerminalSource.line_ends` field would then be dead and removable.

**Consequence:** Not a correctness issue. The two caches are redundant state: a parse that calls both `TerminalSource.pos_to_line_col` (e.g. the parse-error formatter in `errors.rs:128`) and `Span.line_col` (via `py_line_col`) on the same source pays the O(N) scan twice and keeps two `Vec<i64>` allocations alive for the duration of the parse. As inputs grow, this doubles the line-ends memory. The deferred TODO is accurately placed; calling it out here so the cost is visible alongside the existing note.

---

No other findings. The Rust `resolve_line_col` consolidation (the primary goal of the crate-move) is complete and verified: `LineColPos` is defined once in `fltk-cst-core/src/span.rs:166`, `fltk-parser-core` re-exports it at `terminalsrc.rs:8` and `lib.rs:27`, and `TerminalSource::pos_to_line_col` is a thin wrapper calling `resolve_line_col` rather than re-implementing the bisect. `format_source_line` reuses `span.line_col_or_raise()` and `lc.line_span.text()` rather than re-deriving them, so no accessors are bypassed.
