# Deep efficiency review — Rust CST native-span source-preservation range

Base f8fdb53 → HEAD 1b54878. Scope: native span `source_text` accessor + getter/`to_pyobject`
source preservation, native constructors, §2.7 widening. Reporting only NEW regressions in this
range; span-boundary allocation items already covered by `notes-interim-efficiency.md`
(efficiency-1/2/3) are not re-reported. Concise. Precise. No padding.

## efficiency-deep-1 — span getter / `to_pyobject` copies the ENTIRE source string twice per call (Rust backend)

Files: `crates/fltk-cst-core/src/span.rs:77-79` (`source_full_text_str`); generated
`src/cst_fegen.rs:314-320` (span getter) and `:1438-1441` (`to_pyobject` Span arm), repeated at
every getter / per-label / `to_pyobject` site (lines 314, 700, 1145, 1438, 1548, 2161, 2774,
3266, 3366, 3789, 3887, … — every span-returning accessor in the file). Emitted by
`gsm2tree_rs.py` span getter block and `_child_enum_block` `to_pyobject` Span arm.

The source-preservation fix does, on **every** span-returning call:
1. `self.span.source_full_text_str()` → `self.source.as_ref().map(|arc| arc.text.clone())` — a
   full heap copy of the **entire input string** (the whole parsed file), not the span slice.
2. `get_source_text_type(py)?.call1((full_text.as_str(),))` → `SourceText::new(&str)` →
   `text.to_owned()` — copies the whole string **again** into a fresh `Arc<SourceInner>`.

So each `node.span` read (and each terminal child surfaced through `children` /
`children_<label>` / `child` / `child_<label>` / `maybe_<label>`) allocates and copies the full
source twice. This directly defeats the `Span`/`SourceText` `Arc`-sharing design documented at
`span.rs:14-32` ("cloning a span is a reference-count increment, not a string copy"): the
boundary throws the `Arc` away and rebuilds from a `String`.

Consequence: per-accessor cost is O(total source length), not O(span length) and not O(1). The
span getter and per-label child accessors are on the per-node CST read hot path — any traversal
that touches spans (e.g. fltk2gsm `text_or_raise()` reads, §2.6, or any downstream walk) pays a
full-file copy ×2 per node visited. On an N-node tree over an M-byte file, a single full
traversal is O(N·M) byte copies. For a 100 KB grammar with a few thousand nodes this is hundreds
of MB of transient allocation per pass. It bites the moment any Rust-backend consumer reads spans
in a loop — i.e. the primary use of the CST.

Additionally, because each call builds a **fresh** `SourceText`/`Arc`, the spans handed out do
not share source even when they came from the same input — losing the dedup the `Arc` was
designed to provide, and inflating peak memory if a consumer retains many returned spans.

Fix direction: do not round-trip through the full string. Hand the existing `Arc<SourceInner>`
across the boundary instead of copying its `String`. Concretely: add a Rust-level
`Span::with_source_arc` / `SourceText::from_arc(arc)` (or expose `source_as_py` — already added at
`span.rs:41-51`, which clones only the `Arc`, a refcount bump) and build the Python `Span` from
that shared `SourceText` rather than from `full_text: String`. The cross-cdylib concern the
comment cites (`get_source_text_type`) is about the *type object* identity, not the payload;
passing a `Py<SourceText>` built via `source_as_py` (already present, already `Arc`-sharing) to
`with_source` keeps O(1) per call and preserves `Arc` sharing. If `with_source` cannot accept a
pre-built `SourceText`, add a constructor that takes one. This removes both full-string copies and
restores `Arc` dedup.

## Notes

- Parse path is clean: `_source_text` is constructed once per parser
  (`fltk_parser.py:16`, `gsm2parser.py:_source_text_init`) and the shared instance is passed to
  every `Span.with_source(...)` call (`fltk_parser.py:83,93,115,124,…`). On both backends this
  shares one source allocation across all spans of a parse. No per-span source copy at parse time.
  The regression is exclusively at the getter/`to_pyobject` read boundary, not the write/parse path.
- `FLTK_NATIVE_SOURCE_TEXT_TYPE` is a process-wide `GILOnceCell` (`span.rs`-style preamble,
  `cst_fegen.rs:55-65`): the *type-object* import is amortized correctly (one import per process).
  The per-call cost is the string double-copy above, not the type lookup.
- `source_as_py` (`span.rs:41-51`) and `text_str` (`:58-69`) are correctly `Arc`-clone /
  slice-only — no full-source copy. The regression is specifically `source_full_text_str` +
  `SourceText` reconstruction being chosen at the getter sites instead of these.
- §2.7 protocol widening (`gsm2tree.py:571`, union annotation; `TYPE_CHECKING` imports at
  `:486-497`) is annotation-only under `from __future__ import annotations` — no runtime cost.
  No finding.
- `get_start`/`get_end` `#[getter]`s (`span.rs:93-104`) are trivial field reads. No finding.
