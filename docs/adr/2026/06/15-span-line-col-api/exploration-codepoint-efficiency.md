# Exploration: Codepoint indexing — why and how efficiently

Scope: Rust backend storage of codepoint indices, the `cp_to_byte` table, `pos_to_line_col` lookup
complexity, `Span::text()` complexity, and Python comparison.

---

## 1. Why codepoints, not byte offsets

The Rust backend stores positions as **codepoint (Unicode character) indices** (`i64`) matching Python's
string-indexing semantics exactly. The rationale is stated in the Phase 1 design doc
(`docs/adr/2026/06/10-rust-parser-runtime-crate/design.md §2.3`):

> "All positions are codepoint indices, `i64` (exploration.md §7)."

And in `crates/fltk-cst-core/src/span.rs:140–148` (the `Span` struct doc comment):

> "Index semantics: `start` and `end` are codepoint (Unicode character) indices, matching Python's
> string indexing semantics. `text()` / `text_or_raise()` translate these to byte offsets internally.
> This ensures spans produced by the Python-based `TerminalSource` parser are interpreted identically
> on both Python and Rust backends."

The driver is **cross-backend parity**: Python's `TerminalSource` produces `Span(start, end)` where
`start`/`end` are whatever `re.match(...).end()` returns — which for Python's `str` is a codepoint
index, not a byte offset. If the Rust backend stored byte offsets while the Python backend produced
codepoint indices, the same grammar position would yield a different `Span.start`/`Span.end` for any
non-ASCII input. The CLAUDE.md requirement that downstream consumers not be forced to update call sites
wholesale made this parity non-negotiable.

The commit that introduced `TerminalSource` is `490bccf` ("Phase 1: fltk-parser-core runtime crate",
2026-06-10). The file header at `crates/fltk-parser-core/src/terminalsrc.rs:1–5` encodes the rationale:

```rust
//! `TerminalSource` holds a `SourceText` (the single owner of the input) plus a
//! codepoint-to-byte-offset table built once at construction. All external positions
//! are codepoint indices (`i64`), matching Python's string-indexing semantics.
```

---

## 2. How source is indexed: the `cp_to_byte` table

`TerminalSource` (`terminalsrc.rs:38–47`) holds:

```rust
pub struct TerminalSource {
    source: SourceText,
    cp_to_byte: Vec<usize>,          // cp_to_byte[i] = byte offset of codepoint i;
                                     // cp_to_byte[len] = text.len() sentinel
    line_ends: OnceLock<Vec<i64>>,   // lazy: codepoint indices of '\n' + sentinel
}
```

### `cp_to_byte` construction (`terminalsrc.rs:56–74`)

Built **once at construction** via a single `char_indices()` walk:

```rust
let mut cp_to_byte: Vec<usize> = Vec::with_capacity(text.len() + 1);
for (byte_idx, _) in text.char_indices() {
    cp_to_byte.push(byte_idx);
}
cp_to_byte.push(text.len()); // sentinel: cp_to_byte[len] = text.len()
cp_to_byte.shrink_to_fit();
```

This is a one-time O(N_bytes) scan over the input at construction time. After that, every lookup of
`cp_to_byte[i]` is O(1) by direct index.

The capacity over-reservation note (`terminalsrc.rs:60–68`) explains why `shrink_to_fit()` is called:
`Vec::with_capacity(text.len() + 1)` reserves one slot per byte, but only one entry per codepoint is
pushed for multibyte inputs, so `shrink_to_fit` releases the excess rather than leaving memory
proportional to byte count rather than codepoint count persistent across the parse.

### `line_ends` construction (`terminalsrc.rs:191–206`)

Built **lazily on first `pos_to_line_col` call** via `OnceLock::get_or_init`:

```rust
let line_ends = self.line_ends.get_or_init(|| {
    let text = self.text();
    let mut ends: Vec<i64> = text
        .chars()
        .enumerate()
        .filter(|(_, c)| *c == '\n')
        .map(|(cp_idx, _)| cp_idx as i64)
        .collect();
    if ends.last() != Some(&(len - 1)) {
        ends.push(len - 1);
    }
    ends
});
```

This is a one-time O(N_codepoints) scan, after which the `Vec<i64>` is cached in the `OnceLock`.
Subsequent calls do not recompute it.

---

## 3. Lookup complexity by operation

### 3.1 Codepoint → byte offset

**O(1)** via direct index into `cp_to_byte`. Example from `consume_literal` (`terminalsrc.rs:114`):

```rust
let byte_pos = self.cp_to_byte[pos as usize];
```

### 3.2 Byte offset → codepoint index (regex end conversion)

**O(log N_codepoints)** via binary search on `cp_to_byte` (`terminalsrc.rs:160`):

```rust
let end_cp = self.cp_to_byte.partition_point(|&b| b < end_byte);
```

`partition_point` is Rust's `bisect_left`; since regex match boundaries are always UTF-8 char
boundaries, the search hits an exact entry (verified by a `debug_assert` at line 161–164). This is used
only for `consume_regex`'s end position; the start byte offset is already O(1) via `cp_to_byte[pos]`.

### 3.3 `pos_to_line_col` (`terminalsrc.rs:180–228`)

**Amortized O(log N_lines)** after first call.

- **First call**: O(N_codepoints) to build `line_ends`, then O(log N_lines) bisect for the lookup.
- **Subsequent calls**: O(1) `OnceLock::get` to retrieve the cached `line_ends`, then O(log N_lines)
  binary search (`partition_point` at line 209):
  ```rust
  let idx = line_ends.partition_point(|&e| e < pos);
  ```

The one-time build is absorbed across all subsequent lookups; per-call cost is O(log N_lines).

### 3.4 `Span::text()` (`crates/fltk-cst-core/src/span.rs:286–327`)

**O(end_codepoint)** — a single forward scan of `char_indices()` to locate both byte offsets, exiting
early once `end` is found:

```rust
let mut char_count = 0usize;
for (byte_idx, _) in src.char_indices() {
    if char_count == start { byte_start = Some(byte_idx); }
    if char_count == end   { byte_end = Some(byte_idx); break; }
    char_count += 1;
}
```

The code comment at line 297–301 notes this was explicitly optimized from "two-restart" to a single
pass. `Span::text()` does NOT use `cp_to_byte` from `TerminalSource` because `Span` lives in
`fltk-cst-core` while `cp_to_byte` lives in `fltk-parser-core`. The `Arc<SourceInner>` inside `Span`
holds only the raw `String` — no precomputed table. The design doc (`span.rs:43–48`) notes the `Arc`
indirection was chosen to leave "room for future cached metadata (e.g. line-offset tables) without
changing the `Span` struct layout," but no such cache exists yet in `SourceInner`. This means
`Span::text()` is O(end) per call.

### 3.5 Summary table

| Operation | Complexity | Precompute | Location |
|-----------|-----------|------------|----------|
| `cp_to_byte` build | O(N_bytes) once | at `TerminalSource::new` | `terminalsrc.rs:58–64` |
| codepoint → byte (`consume_*`) | O(1) | via `cp_to_byte[pos]` | `terminalsrc.rs:114, 145` |
| byte → codepoint (regex end) | O(log N_cp) | binary search on `cp_to_byte` | `terminalsrc.rs:160` |
| `line_ends` build | O(N_cp) once | first `pos_to_line_col` call | `terminalsrc.rs:191–206` |
| `pos_to_line_col` (after first) | O(log N_lines) | binary search on `line_ends` | `terminalsrc.rs:209` |
| `Span::text()` | O(end) per call | none — walks `char_indices()` | `span.rs:305–314` |

---

## 4. Python comparison

### `pos_to_line_col` (`terminalsrc.py:183–205`)

The Python implementation uses the same algorithmic structure:

```python
def pos_to_line_col(self, pos: int) -> LineColPos:
    if not self.line_ends:
        self.line_ends = [idx for idx, c in enumerate(self.terminals) if c == "\n"]
        if not self.line_ends or self.line_ends[-1] != len(self.terminals) - 1:
            self.line_ends.append(len(self.terminals) - 1)
    idx = bisect.bisect_left(self.line_ends, pos)
```

Key similarities:
- `line_ends` is also lazy — built on first call (lines 189–192), stored on the `TerminalSource`
  instance, and reused thereafter.
- The lookup is `bisect.bisect_left` = O(log N_lines) after first call.

Key differences:
- Python's `TerminalSource.__init__` does NOT build a `cp_to_byte` table. There is no analog of the
  Rust precomputed table. Python's `str` indexing (`self.terminals[pos + i]`) is O(1) for codepoints
  natively (CPython's `str` stores code points directly as fixed-width integers internally), so Python
  does not need to translate codepoints to byte offsets at all.
- Python `TerminalSource.consume_regex` uses `re.match(pattern, string, pos=pos)` where `pos` is a
  codepoint index — CPython passes this directly to the regex engine's codepoint-indexed string. There
  is no byte conversion step and no `cp_to_byte` lookup.

### `Span.text()` (Python, `terminalsrc.py:57–67`)

```python
def text(self) -> str | None:
    return self._source[self.start:self.end]
```

**O(end - start)** due to CPython's slice copying. No scan to find byte offsets — Python `str` slicing
is already codepoint-aware. The exploration doc notes (`15-span-line-col-api/exploration.md §2`):
"A span-level method [for `pos_to_line_col`] would either: (a) recompute line-ends every call
(no cache — O(n) per call), or (b) cache line-ends on the `Arc<SourceInner>` (Rust)."

The current Python `Span` carries `_source: str` in a frozen dataclass with `__slots__`, so it has no
mutable cache slot. If `line_col()` were added to `Span` on the Python side without extending
`SourceText`, it would be O(N_codepoints) per call with no caching.

---

## Open factual questions

1. `Span::text()` in the Rust backend is O(end) per call because `SourceInner` holds only `text:
   String` with no precomputed byte-offset table. The `span.rs:43–48` comment anticipates adding a
   `line_ends`-style cache to `SourceInner` via an `OnceLock`, but this has not been done. A
   `cp_to_byte`-style table on `SourceInner` would reduce `Span::text()` from O(end) to O(1) codepoint
   lookup + O(end-start) copy, but the design has deferred this.

2. `line_ends` is cached on `TerminalSource` (parser side) but not on `SourceInner` (span side). Spans
   produced after the parser completes cannot reuse `TerminalSource.line_ends`. A `Span.line_col()`
   method on the Rust side would need to either build `line_ends` from `SourceInner.text` with its own
   cache on `SourceInner`, or do O(N) per call.
