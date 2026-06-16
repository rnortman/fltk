# Exploration: provenance and rationale of `cp_to_byte` in `TerminalSource`

## 1. Code surface

**File**: `crates/fltk-parser-core/src/terminalsrc.rs`

**Structure** (`terminalsrc.rs:38-47`):
```rust
pub struct TerminalSource {
    source: SourceText,
    /// cp_to_byte[i] = byte offset of codepoint i; cp_to_byte[len] = text.len() sentinel.
    // Memory note: 8 bytes/codepoint (usize). Acceptable for grammar-sized inputs.
    // If memory ever matters, u32 offsets would halve it — not done now.
    cp_to_byte: Vec<usize>,
    /// Lazy codepoint indices of `\n` plus a final sentinel.
    line_ends: OnceLock<Vec<i64>>,
}
```

**Element type**: `usize` — 8 bytes per codepoint on 64-bit.

**Length relative to input**: `cp_to_byte.len() == codepoint_count + 1` (one entry per codepoint plus a sentinel
equal to `text.len()`). For pure ASCII input, one entry per input byte plus one. For multibyte (e.g. CJK),
fewer entries than bytes.

**True memory cost per input byte**: for ASCII, 8 bytes of table per 1 byte of input (~8x). For pure 4-byte
codepoints, 2 bytes of table per byte of input (~2x). The table size is always proportional to codepoint count,
not byte count.

**Construction** (`terminalsrc.rs:56-68`):
```rust
let mut cp_to_byte: Vec<usize> = Vec::with_capacity(text.len() + 1);
for (byte_idx, _) in text.char_indices() {
    cp_to_byte.push(byte_idx);
}
cp_to_byte.push(text.len()); // sentinel
cp_to_byte.shrink_to_fit();
```

The initial `with_capacity(text.len() + 1)` over-reserves by up to ~4x for multibyte input (one slot per byte,
but only one entry per codepoint). `shrink_to_fit()` releases the slack at construction time.

**`line_ends`** (`terminalsrc.rs:191-206`): `OnceLock<Vec<i64>>` — codepoint indices of `\n` characters plus a
final sentinel. Lazy (initialized on first `pos_to_line_col` call). For a text with L newlines, this is
`(L+1) * 8` bytes — much smaller than `cp_to_byte`. Does NOT duplicate `cp_to_byte`'s index entries;
`line_ends` holds only newline positions, not a full codepoint map.

---

## 2. When introduced and which commit

**Commit**: `490bccf33359e7b38d8a76a207d8b709921718bb`
**Date**: 2026-06-10
**Author**: Randall Nortman
**Commit message slug**: `Phase 1: fltk-parser-core runtime crate`

This commit created `crates/fltk-parser-core/src/terminalsrc.rs` from scratch, introducing both the
`TerminalSource` struct and the `cp_to_byte` field. The file did not exist before this commit.

A subsequent commit (`61f9384`, 2026-06-11, `consume-regex-anchor`) modified `consume_regex` to switch from
`regex::find_at` to `regex_automata::meta::Regex` with `Anchored::Yes`, but did not change the
`cp_to_byte` structure or construction.

---

## 3. Why: stated rationale

### Controlling design: `docs/adr/2026/06/10-rust-parser-runtime-crate/design.md`

**Section 2.3** (the section specifying `terminalsrc.rs`):

> All positions are **codepoint indices, `i64`** (exploration.md §7). ... `cp_to_byte` is built once at
> construction via `char_indices()` plus the final sentinel.

The rationale is in the exploration doc's section 7 and the design's §2.3: the Python runtime uses Unicode
codepoint indices everywhere (Python `str` indexing is codepoint-based). Rust strings are byte-indexed. To
maintain Python parity — all external positions, spans, and parser state are codepoint indices — a translation
table is required at every `consume_literal` and `consume_regex` call. The table makes that translation O(1)
instead of O(n) per call.

**`docs/adr/2026/06/10-rust-parser-runtime-crate/exploration.md`, section 7** (the key factual grounding):

> Rust `TerminalSource` must maintain a `Vec<usize>` codepoint→byte-offset table built once at construction.

The exploration doc notes:
- `terminalsrc.py:165`: `terminals_len = len(terminals)` — codepoint count
- `terminalsrc.py:168-175`: `consume_literal` iterates `self.terminals[pos + i]` — codepoint indexing
- `span.rs:133`: doc comment confirms codepoint semantics

The entire Rust span and position model uses `i64` codepoint indices matching Python's string semantics. There
was no option to use byte indices without breaking the cross-backend (Python/Rust) position contract.

### Was memory explicitly considered?

Yes, in two places:

1. **In the code comment at the struct field** (present verbatim since the original commit `490bccf`):
   ```rust
   // Memory note: 8 bytes/codepoint (usize). Acceptable for grammar-sized inputs.
   // If memory ever matters, u32 offsets would halve it — not done now.
   ```

2. **In the design doc** (`design.md §3`, "Edge cases / failure modes"):
   > **`cp_to_byte` memory**: 8 bytes/codepoint (`Vec<usize>`). Acceptable for grammar-sized inputs; if it
   > ever matters, `u32` offsets halve it — not done now, noted in a code comment only (no TODO: no concrete
   > trigger).

3. **The efficiency reviewer** flagged the 4x over-reservation issue during deep review
   (`notes-deep-efficiency-reviewer.md`, finding efficiency-5):
   > `Vec::with_capacity(text.len() + 1)` reserves one slot per **byte**; the vec holds one entry per
   > **codepoint**. For heavily multibyte text (codepoints ≈ bytes/3 for CJK) up to ~3/4 of the reservation
   > is dead capacity... e.g. a 10 MB CJK source reserves ~80 MB for a table needing ~27 MB.

   This was **fixed** in the same review cycle (`dispositions-deep.md`, efficiency-5): `shrink_to_fit()` was
   added after the build loop, releasing the over-reservation via a single realloc at construction time. The
   committed code already includes this fix.

### Were alternatives discussed or rejected?

The design doc explicitly names one alternative and defers it:
- **`Vec<u32>` instead of `Vec<usize>`**: named in both the code comment and design doc as the natural
  follow-on if memory ever matters. Not done because no concrete trigger existed.

The design doc does NOT discuss:
- Bisection over a line/char-boundary table (i.e., no full codepoint table)
- On-demand conversion (O(n) per call)
- Lazy/partial table

The exploration doc implicitly ruled out O(n) conversion per call by specifying a table, which is consistent
with the packrat parser's design — `consume_literal` and `consume_regex` are called once per (rule, position)
pair (first attempt; subsequent hits are memoized), but with N rules and N positions, that is still O(N) table
lookups per parse, each of which must be O(1).

---

## 4. What depends on `cp_to_byte` today

Three methods in `TerminalSource` use `cp_to_byte` directly:

1. **`len()`** (`terminalsrc.rs:90-92`): derives codepoint count as `cp_to_byte.len() - 1` (O(1); avoids
   a separate counter field).

2. **`consume_literal()`** (`terminalsrc.rs:110-126`): `cp_to_byte[pos as usize]` to get the byte offset
   for `text[byte_pos..]`. Called by every literal match attempt in every generated parser.

3. **`consume_regex()`** (`terminalsrc.rs:141-166`): `cp_to_byte[pos as usize]` to get the byte start
   for the `Input::span(byte_pos..text.len())` anchored search; also `partition_point` binary search on
   `cp_to_byte` to convert the match-end byte offset back to a codepoint index. Called by every regex match
   attempt.

`line_ends` does NOT use `cp_to_byte` — after efficiency-4 was fixed in deep review, it uses
`chars().enumerate()` which yields codepoint indices directly (no byte-to-codepoint conversion needed).

`pos_to_line_col()` uses `line_ends` only (not `cp_to_byte`).

`cp_to_byte` is load-bearing for both terminal-match paths (literal and regex) on every parser invocation.
Removing it would require either: (a) a linear scan to convert each codepoint position to bytes at every match
attempt, or (b) switching the entire position model to byte indices (a breaking change to the span/position
API contract shared with the Python backend and downstream consumers).
