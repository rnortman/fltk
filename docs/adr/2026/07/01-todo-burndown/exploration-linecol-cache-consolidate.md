# Exploration: `TODO(linecol-cache-consolidate)`

Base commit: `8fd5ecf`. Ground truth from direct file reads, not from other ADR
notes (those are cited only where they independently corroborate).

## TODO.md entry

`TODO.md:62-64` (`## \`linecol-cache-consolidate\``), verbatim claim:

> `TerminalSource` carries its own `line_ends: OnceLock<Vec<i64>>`
> (`crates/fltk-parser-core/src/terminalsrc.rs:46`) while `SourceInner` ... also
> carries `line_ends: OnceLock<Vec<i64>>` (`crates/fltk-cst-core/src/span.rs`).
> ... A follow-up could point `TerminalSource::pos_to_line_col` at
> `&self.source.inner.line_ends` (the shared `resolve_line_col` function already
> accepts a caller-supplied `OnceLock`) and drop `TerminalSource`'s own field.
> Location: `crates/fltk-parser-core/src/terminalsrc.rs:46` (`line_ends` field)
> and the `pos_to_line_col` wrapper (~line 167,178).

## Do both fields still exist as described?

Yes, both exist, matching the described types and duplication.

- `crates/fltk-parser-core/src/terminalsrc.rs:34`: `line_ends: OnceLock<Vec<i64>>,` — a private field on `struct TerminalSource` (`terminalsrc.rs:26-35`).
- `crates/fltk-cst-core/src/span.rs:61`: `pub(crate) line_ends: OnceLock<Vec<i64>>,` — a field on `struct SourceInner` (`span.rs:46-62`), with its own `TODO(linecol-cache-consolidate)` doc comment at `span.rs:56-60`.

**Line-number drift**: the TODO.md text cites `terminalsrc.rs:46` for the `line_ends` field twice (once for the field, once implicitly via "Location"). The field is actually at `terminalsrc.rs:34` now. The doc-comment/TODO-comment location "~line 167,178" for the `pos_to_line_col` wrapper is accurate: the doc comment referencing the sibling cache is at `terminalsrc.rs:166-167`, and the inline `TODO(linecol-cache-consolidate)` comment is at `terminalsrc.rs:178-180`. So one of the two cited locations (`:46`) has drifted from the code; the other (`~167,178`) still matches exactly.

## Is `self.source.inner.line_ends` actually reachable from `TerminalSource`?

**No — not as literally written.** This is the key adversarial finding.

- `TerminalSource.source` is a private field of type `SourceText` (`terminalsrc.rs:27`), and `SourceText` is defined in the separate crate `fltk-cst-core` (`crates/fltk-cst-core/src/span.rs:70-72`):
  ```rust
  pub struct SourceText {
      pub inner: Arc<SourceInner>,
  }
  ```
  The `inner` field is `pub`, so `self.source.inner` (an `Arc<SourceInner>`) is reachable from `fltk-parser-core`.
- However, `SourceInner.line_ends` itself is declared `pub(crate)` (`span.rs:61`), i.e. visible only within `fltk-cst-core`. `fltk-parser-core` is a separate crate (confirmed by `crates/fltk-parser-core/Cargo.toml:16`: `fltk-cst-core = { path = "../fltk-cst-core", default-features = false }`, a normal external path dependency, not a submodule/same-crate include).
- Consequently `&self.source.inner.line_ends` inside `crates/fltk-parser-core/src/terminalsrc.rs` would fail to compile with a privacy error (`line_ends` is private to `fltk-cst-core`), exactly as the field is currently declared.
- `SourceText`'s public API (`crates/fltk-cst-core/src/span.rs`, non-`#[cfg(feature = "python")]` `impl SourceText` block) exposes only two methods: `from_str(...)` and `text(&self) -> &str` (`span.rs:74-92`). There is no existing public/`pub(crate)`-to-caller accessor for `line_ends` (no `.line_ends()` method, no re-exported field). The `python`-gated `impl SourceText` block (pyo3 methods) also exposes no such accessor — only `_fltk_cst_core_abi` and a layout-probe classattr.

So the literal one-line change the TODO describes ("point `TerminalSource::pos_to_line_col` at `&self.source.inner.line_ends`") is not achievable today without also changing `SourceInner.line_ends`'s visibility or adding a new accessor method on `SourceText`/`SourceInner` — neither of which the TODO text mentions or accounts for.

## Does `resolve_line_col` accept a caller-supplied `OnceLock` as claimed?

Yes, confirmed exactly as described. `crates/fltk-cst-core/src/span.rs:224`:
```rust
pub fn resolve_line_col(text: &str, pos: i64, line_ends: &OnceLock<Vec<i64>>) -> Option<LineColPos>
```
It is `pub` (not `pub(crate)`), so it is already callable from `fltk-parser-core` — and indeed is: `TerminalSource::pos_to_line_col` calls it today at `terminalsrc.rs:181` as `resolve_line_col(self.text(), pos, &self.line_ends)`. The signature takes the `OnceLock` by reference from any caller-supplied location, so the mechanism described ("the shared `resolve_line_col` function already accepts a caller-supplied `OnceLock`") is accurate in isolation — the blocker is strictly the visibility of `SourceInner.line_ends`, not the shape of `resolve_line_col`.

`fltk-cst-core` itself already relies on this generality: `span.rs:553` calls `resolve_line_col(&source.text, pos, &source.line_ends)` from `Span`'s own `line_col`-style method, passing `SourceInner`'s private field directly — legal only because that call site is inside `fltk-cst-core` itself.

## All `TODO(linecol-cache-consolidate)` comment sites in code

Exactly two, both confirmed present:

1. `crates/fltk-parser-core/src/terminalsrc.rs:178-180`:
   ```rust
   // TODO(linecol-cache-consolidate): self.line_ends is independent of
   // self.source.inner.line_ends — two caches over the same immutable text.
   // A future consolidation could pass &self.source.inner.line_ends here.
   ```
   (immediately followed by the `resolve_line_col(self.text(), pos, &self.line_ends)` call at line 181)
2. `crates/fltk-cst-core/src/span.rs:56-60` (doc comment on the `SourceInner.line_ends` field):
   ```rust
   /// TODO(linecol-cache-consolidate): TerminalSource also maintains its own
   /// `line_ends` over the same immutable text — two independent caches over
   /// identical data. A future consolidation could have TerminalSource read
   /// source_inner.line_ends instead of maintaining its own field. Out of scope
   /// for the span-line-col-api change.
   ```

No other occurrences of the slug in `crates/` outside these two files (verified via repo-wide grep). Occurrences elsewhere in the tree are all in `docs/adr/2026/06/15-span-line-col-api/*.md` narrative/notes files, not code.

## Summary of facts

| Claim | Status |
|---|---|
| `TerminalSource.line_ends: OnceLock<Vec<i64>>` field exists | True (now at `terminalsrc.rs:34`, TODO.md says `:46` — drifted) |
| `SourceInner.line_ends: OnceLock<Vec<i64>>` field exists | True (`span.rs:61`) |
| Both derive from same immutable `text` | True by inspection (both built by scanning `text`/`self.text()` for `\n`) |
| `resolve_line_col` accepts a caller-supplied `OnceLock` | True (`span.rs:224`, `pub fn`) |
| `&self.source.inner.line_ends` reachable from `TerminalSource` in `fltk-parser-core` | **False** — `SourceInner.line_ends` is `pub(crate)` inside `fltk-cst-core`; `fltk-parser-core` is a separate crate (path dependency) with no accessor exposed for this field |
| `pos_to_line_col` wrapper location `~line 167,178` | True (doc comment `166-167`, TODO comment `178-180`) |
| Both TODO(linecol-cache-consolidate) code comments present | True, exactly 2 sites (`terminalsrc.rs:178-180`, `span.rs:56-60`) |
