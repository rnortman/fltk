# Exploration: SpanProtocol `.start`/`.end` Omission — Is the Rationale Current?

## Question

The `SpanProtocol` docstring says `.start` and `.end` are omitted because "codepoint indices in Python; byte indices in Rust." The user believes the Rust backend has since switched to codepoint indices. This exploration verifies or refutes that claim.

---

## 1. Where the SpanProtocol Is Defined and What It Omits

**File:** `fltk/fegen/pyrt/span_protocol.py`

The `SpanProtocol` is a `typing.Protocol` declared at lines 10–86. The rationale for omitting `.start`/`.end` is in the class docstring:

```
# fltk/fegen/pyrt/span_protocol.py:11-17
class SpanProtocol(Protocol):
    """Structural protocol satisfied by both the pure-Python and Rust Span backends.

    Backend-agnostic code should annotate with ``SpanProtocol`` rather than a
    concrete ``Span`` type.  The protocol intentionally omits ``start``/``end``
    attributes because their semantics differ between backends (codepoint indices
    in Python; byte indices in Rust).  All text access must go through the
    methods below.
    """
```

A second instance of the stale claim appears at `span_protocol.py:34`:

```python
    def len(self) -> int:
        """Return the span length in backend-specific index units (codepoints for Python, bytes for Rust).
```

`SpanProtocol` exposes: `text()`, `text_or_raise()`, `has_source()`, `len()`, `is_empty()`, `merge()`, `intersect()`, `line_col()`, `line_col_or_raise()`, `filename()`. It does NOT expose `.start` or `.end`.

---

## 2. Python Backend: Index Semantics

**File:** `fltk/fegen/pyrt/terminalsrc.py`

The Python `Span` is a frozen dataclass:

```python
# terminalsrc.py:51-58
@dataclass(frozen=True, eq=True, slots=True)
class Span:
    """Span of elements in the range [start, end)"""

    start: int
    end: int
    _source: str | None = field(default=None, repr=False, compare=False, hash=False)
```

`start` and `end` are used directly as Python string indices (`self._source[start:end]`, line 71). Python string indexing is by Unicode codepoint. `TerminalSource.consume_literal` (line 252) sets `end = pos + len(literal)` where `len()` on a Python str counts codepoints. `consume_regex` (line 261) uses `re.compile(regex).match(self.terminals, pos=pos)` and takes `match.end()`, which is a byte offset in the underlying buffer — **but** for pure ASCII inputs this is identical to the codepoint offset, and the regex is matched against the Python `str` directly where `.pos` is a codepoint index.

**Conclusion:** Python backend uses codepoint indices throughout.

---

## 3. Rust Backend: Current Index Semantics

**File:** `crates/fltk-cst-core/src/span.rs`

The Rust `Span` struct (lines 292–296):

```rust
pub struct Span {
    pub(crate) start: i64,
    pub(crate) end: i64,
    pub(crate) source: Option<Arc<SourceInner>>,
}
```

The struct-level doc comment at line 275:

```rust
/// Half-open **Unicode-codepoint** index range ``[start, end)`` into a shared UTF-8 source string.
///
/// **Index semantics:** ``start`` and ``end`` are *codepoint* (Unicode character) indices,
/// matching Python's string indexing semantics.  ``text()`` / ``text_or_raise()`` translate
/// these to byte offsets internally.
```

The `text()` method (lines 421–462) takes `start` and `end` as codepoint indices and translates to byte offsets via a single forward scan over `src.char_indices()`.

The `Span::start()` accessor (line 363): doc says "Return the start codepoint index (Rust accessor — not a Python getter)."

The `get_start` Python getter (line 741): doc says "Return the start codepoint index as a Python integer."

**File:** `crates/fltk-parser-core/src/terminalsrc.rs`

`TerminalSource` (lines 26–35) builds a `cp_to_byte: Vec<usize>` table mapping codepoint index i → byte offset. All parser positions are described as "codepoint indices (`i64`), matching Python's string-indexing semantics" (module docstring, lines 1–5). `consume_literal` (line 98) and `consume_regex` (line 129) both take `pos: i64` as a codepoint index and use `cp_to_byte[pos as usize]` to get the byte offset.

**Conclusion:** The Rust backend uses codepoint indices. It translates internally to byte offsets but the `start`/`end` fields and all public APIs are codepoint-indexed.

---

## 4. The `.start`/`.end` Python Getters on the Rust Span

**File:** `fltk/_native/__init__.pyi` (lines 70–73):

```python
    @property
    def start(self) -> int: ...
    @property
    def end(self) -> int: ...
```

**File:** `crates/fltk-cst-core/src/span.rs` (lines 735–751):

```rust
    #[getter]
    fn get_start(&self) -> i64 {
        self.start
    }

    #[getter]
    fn get_end(&self) -> i64 {
        self.end
    }
```

The Rust `Span` already exposes `.start` and `.end` as Python properties returning codepoint indices. The Python `Span` exposes them as plain dataclass fields (also codepoint indices).

---

## 5. When the Rust Backend Switched from Byte to Codepoint Indices

From `git log -- crates/fltk-cst-core/src/span.rs`:

- Commit `60f5c3f` ("Increment 1: fltk-cst-core split crate"): the `Span` doc said "Half-open byte-index range" with "start and end are byte offsets."
- Commit `490bccf` ("Phase 1: fltk-parser-core runtime crate"): the diff shows the switch — "Half-open byte-index range" → "Half-open **Unicode-codepoint** index range", and "start and end are byte offsets" → "start and end are codepoint (Unicode character) indices."

The protocol file `span_protocol.py` was first written at commit `0f9b786` ("Phase 1: Rust + pure-Python Span backends with source-text access"). At that point the Rust backend **was** using byte indices, so the comment was accurate when written. The switch to codepoint indices happened in commit `490bccf` (the fltk-parser-core phase). The `span_protocol.py` comment was not updated at that time.

---

## 6. Summary

| Claim in SpanProtocol docstring | Current reality |
|---|---|
| "codepoint indices in Python" | CORRECT |
| "byte indices in Rust" | **INCORRECT** — Rust switched to codepoint indices at commit `490bccf` |
| `len()` "bytes for Rust" | **INCORRECT** — `Span::len()` returns `(end - start)` in codepoints |

**The comment is outdated.** Both backends now use codepoint indices for `start` and `end`. The original rationale for omitting `.start`/`.end` from `SpanProtocol` no longer holds.

The Rust `Span` already exposes `.start` and `.end` as Python properties (`get_start`/`get_end` getters, codepoint semantics). The Python `Span` exposes them as plain dataclass fields. Adding `.start: int` and `.end: int` to `SpanProtocol` would now be semantically consistent across both backends.

The only remaining question before exposing them in the protocol is whether there are any Rust-specific callsites that still rely on the `start`/`end` fields as byte offsets internally — but from the code, internal byte-offset translation happens entirely within `text()` and `TerminalSource` methods; the public `start`/`end` surface is codepoint-indexed everywhere.
