# Exploration: Adding line/column lookup to SpanProtocol

Prior fact-find (base): `~/tps/clockwork/docs/adr/2026/06/15-rust-backend-port/exploration-linecol.md`
This document builds on that prior, adding implementation-surface detail per the six survey areas.

---

## 1. Protocol surface (`fltk/fegen/pyrt/span_protocol.py`)

`SpanProtocol` is a `@runtime_checkable Protocol` at lines 8–56. Its current method inventory
(complete):

| Method | Signature (abbreviated) | Notes |
|--------|-------------------------|-------|
| `text` | `() -> str \| None` | delegates to `Span.text()` on each backend |
| `text_or_raise` | `() -> str` | raises `ValueError` on failure |
| `has_source` | `() -> bool` | |
| `len` | `() -> int` | backend-specific note: codepoints on both backends |
| `is_empty` | `() -> bool` | |
| `merge` | `(other: SpanProtocol) -> SpanProtocol` | |
| `intersect` | `(other: SpanProtocol) -> SpanProtocol` | |

No `line`, `column`, `line_col`, or `pos_to_line_col` method exists (confirmed: `exploration-linecol.md §1`).

The protocol docstring (lines 13–17) deliberately omits `start`/`end` because their semantics differ.
Both backends do expose `.start`/`.end` as attributes (Python: dataclass fields; Rust: `#[getter]` at
`span.rs:563–574`), but they are not on the protocol.

### How `text()` resolves through carried source (the pattern a new method would mirror)

Python `Span.text()` (`terminalsrc.py:57–67`): reads `self._source` (a `str | None` field at line 54),
slices `self._source[start:end]`.

Rust `Span.text()` (`span.rs:286–327`): reads `self.source` (an `Option<Arc<SourceInner>>` field at
line 160), iterates `char_indices()` once to convert codepoint indices to byte offsets, slices.

Pattern: both backends carry their source inside the `Span` struct. A new `line_col()` method on `Span`
would similarly use the carried source, plus a line-ends table that today lives on `TerminalSource` (not
on `Span`).

### `AnySpan` union

`span_protocol.py:59–64`:
```python
AnySpan = _pymod.Span | _RustSpan   # or just _pymod.Span when Rust unavailable
```
`AnySpan` is a type alias; adding a method to `SpanProtocol` does not widen or change `AnySpan`.

### Hand-written vs generated

`span_protocol.py` is hand-written runtime code, not generated. Adding a method here is a direct edit,
not a codegen change.

---

## 2. Python backend: `Span` source-carrying and `pos_to_line_col`

### How `Span` carries source

`terminalsrc.py:48–54` (`Span` dataclass):
```python
@dataclass(frozen=True, eq=True, slots=True)
class Span:
    start: int
    end: int
    _source: str | None = field(default=None, repr=False, compare=False, hash=False)
    kind: Literal[SpanKind.SPAN] = field(...)
```
`_source` is a raw `str` (NOT a `SourceText` object). The `SourceText` wrapper is unwrapped at
`with_source` time (`terminalsrc.py:142–149`): `source._text` is extracted and stored as `str`.

`Span.with_source(start, end, source)` (`terminalsrc.py:131–149`): accepts `str | SourceText`;
unwraps `SourceText` to raw `str`; stores raw `str` in `_source`.

### `TerminalSource.pos_to_line_col` (Python)

`terminalsrc.py:183–205`:
```python
def pos_to_line_col(self, pos: int) -> LineColPos:
```
- `pos` is a raw integer codepoint index (caller passes `span.start` or `tracker.longest_parse_len`).
- Builds `self.line_ends` lazily (list of codepoint indices of `\n`, plus sentinel; cached on instance).
- 0-based line and column.
- `pos == len(terminals)` is clamped to `len - 1` (lines 187–188).
- `pos > len(terminals)` raises `ValueError` (lines 184–186).
- `line_span` in the returned `LineColPos` (line 156–159) is a **sourceless** `Span(start, end)` —
  `_source=None` (lines 197–200). This is a known asymmetry vs the Rust backend.

### What it would take for a `Span` to resolve its own line/column

The Python `Span._source` is a plain `str`. This means a `Span` has all the text needed to scan for
`\n` characters. The `pos_to_line_col` bisect logic (`terminalsrc.py:193–200`) requires only:
1. `self._source` (or equivalent text)
2. `self.start` (integer codepoint index)

The line-ends cache (`self.line_ends`) currently lives on `TerminalSource`. A span-level method would
either: (a) recompute line-ends every call (no cache — O(n) per call), or (b) cache line-ends on the
`Arc<SourceInner>` (Rust) or on a separate data structure.

On the Python backend, `Span` is a frozen dataclass with `__slots__`; adding a mutable line-ends cache
to `Span` directly is not possible without changing the class structure. A method that recomputes on
every call is possible.

---

## 3. Rust backend: Span/SourceText source-carrying, pyo3 layer, `pos_to_line_col`

### Rust `Span` struct (`crates/fltk-cst-core/src/span.rs`)

```rust
pub struct Span {
    pub(crate) start: i64,
    pub(crate) end: i64,
    pub(crate) source: Option<Arc<SourceInner>>,   // line 160
}

pub struct SourceInner {
    pub(crate) text: String,   // line 48
}
```

`Span` carries an `Arc<SourceInner>` (the full source text). `SourceInner` today contains only `text:
String`. The `Arc` indirection was noted at `span.rs:43–48` as leaving "room for future cached metadata
(e.g. line-offset tables) without changing the `Span` struct layout."

Existing `text()` method (lines 286–327): iterates `char_indices()` each call to translate codepoint
indices to byte offsets.

### Where `pos_to_line_col` lives in Rust

`crates/fltk-parser-core/src/terminalsrc.rs:180`:
```rust
pub fn pos_to_line_col(&self, pos: i64) -> Option<LineColPos>
```
Lives on `TerminalSource` (defined at `terminalsrc.rs:38–47`). `TerminalSource` is **not a pyo3
class** — no `#[pyclass]` annotation; not in `fltk/_native/__init__.pyi`. It is Rust-internal only.

`TerminalSource` holds:
- `source: SourceText` (the `Arc`-shared source, same allocation as parser-produced spans)
- `cp_to_byte: Vec<usize>` (codepoint-to-byte-offset table, built at construction)
- `line_ends: OnceLock<Vec<i64>>` (lazily built on first `pos_to_line_col` call)

The `line_ends` computation mirrors Python's exactly (terminalsrc.rs:191–206 vs terminalsrc.py:189–192).
`LineColPos` returned by Rust has **source-bearing `line_span`** (improvement over Python's sourceless).

### pyo3 exposure of Span

All current Python-visible `Span` methods in `span.rs:382–603` (under `#[cfg(feature = "python")]`
`#[pymethods]`):
`py_new`, `with_source`, `_with_source_unchecked`, `py_text`, `text_or_raise`, `py_has_source`,
`py_len`, `py_is_empty`, `py_merge`, `py_intersect`, `get_start` (getter), `get_end` (getter),
`__repr__`, `__eq__`, `__hash__`, `kind` (getter).

Adding a `line_col` pyo3 method to `Span` would require:
1. A Rust method on `Span` that replicates `pos_to_line_col` logic from `TerminalSource`, but using
   the `Arc<SourceInner>` already carried in `self.source`.
2. A `#[pyo3(name = "line_col")]` wrapper under `#[pymethods]` returning a Python-visible `LineColPos`
   (or a tuple).
3. `LineColPos` is currently not a pyo3 class — it is only used internally and in `fltk-parser-core`'s
   Rust API. Exposing it via pyo3 requires either adding `#[pyclass]` to a new struct or returning a
   tuple.

### Byte-vs-codepoint note

The Rust `Span` stores codepoint indices (`i64`), matching Python. The existing `text()` method
translates codepoints to byte offsets internally (`span.rs:296–326`). A `line_col()` method would use
codepoint indices directly (no byte-offset translation needed for line/col counting).

### How existing pyo3 text methods bridge the gap

`py_text` and `text_or_raise` both call the inner Rust `text()` which does byte-offset translation
internally. The pyo3 surface returns Python `str | None`. A new `line_col` method would follow the same
pattern: inner Rust method does the work, pyo3 wrapper converts return type to Python-visible form.

---

## 4. Span construction in parsers: which spans carry source

### Python generated parsers

`gsm2parser.py:254–276` (`_make_span_expr`):
```python
return iir.MethodAccess("with_source", span_class_ref).call(
    start_expr,
    end_expr,
    iir.SelfExpr().fld._source_text.load(),
)
```
Every terminal span in generated parsers is constructed via `Span.with_source(start, end,
self._source_text)`. `self._source_text` is a `SourceText` instance initialized at parser construction
(`gsm2parser.py:105–130`) from `terminalsrc.terminals`.

**All spans produced by generated parsers are source-bearing.** A consumer receiving a span from a
parser-parsed tree will have `.has_source() == True` and can call `line_col()` if it exists.

### Spans that would NOT support line/column

- `UnknownSpan` (`Span(-1, -1)`, no source): the default initial span on CST node fields
  (`fltk_cst.py:88`, etc.). A `line_col()` call on this span would fail (no source, negative indices).
- Any span built by consumer code without a `SourceText` (e.g., `Span(0, 5)` constructed directly).
- The `line_span` field inside `LineColPos` on the Python backend is a sourceless span — it cannot
  recursively call `line_col()`.

A `line_col()` method should return `None` or raise when `has_source()` is `False` or when `start < 0`,
consistent with the `text()` / `text_or_raise()` pattern.

---

## 5. Cross-backend equivalence tests and conventions

### Existing span test files

- `tests/test_span.py`: pure-Python `Span` backend tests (terminalsrc). Imports from
  `fltk.fegen.pyrt.terminalsrc`. 196 lines, covers construction, equality, hash, text, merge, intersect.
  No `pos_to_line_col` tests.
- `tests/test_rust_span.py`: Rust `Span` backend tests (`fltk._native`). 1090 lines. Covers
  construction, equality, hash, source-bearing spans, merge, intersect, ABI markers, cross-cdylib.
  No `pos_to_line_col` tests.
- `tests/test_span_protocol.py`: `SpanProtocol` conformance tests for both backends (115 lines).
  Tests `isinstance(s, SpanProtocol)` for both backends; also tests `AnySpan`, backend selector,
  portable `with_source`.

### Existing `pos_to_line_col` tests

- `fltk/fegen/test_regression_error_reporting.py`: tests Python `TerminalSource.pos_to_line_col`
  directly.
- `fltk/fegen/test_regression_line_col_error.py`: further Python `TerminalSource.pos_to_line_col`
  regression tests.
- `crates/fltk-parser-core/src/terminalsrc.rs:424–519`: inline Rust `#[cfg(test)]` tests for
  `TerminalSource::pos_to_line_col`.

No existing tests exercise `pos_to_line_col` on a `Span` object or via `SpanProtocol`.

### TDD/EDTC convention (CLAUDE.md)

CLAUDE.md specifies TDD: failing tests first, then implementation. For a new `line_col()` method on
`SpanProtocol`, the natural test location is `tests/test_span_protocol.py` (cross-backend conformance)
and `tests/test_span.py` / `tests/test_rust_span.py` (per-backend behavior).

### Codegen → `make fix` → commit flow

`span_protocol.py`, `terminalsrc.py`, and `span.rs` are hand-written (not generated). No codegen
step is needed for changes to these files. `make fix` (ruff check + ruff format) is still required
before commit; `make check` is the precommit gate (runs lint, format-check, typecheck, test, cargo-check,
cargo-clippy, cargo-test).

---

## 6. Public-API / compat considerations

### Adding a method to `SpanProtocol`

`SpanProtocol` is `@runtime_checkable`. Adding a new method to a `@runtime_checkable Protocol` makes
`isinstance(x, SpanProtocol)` return `False` for any existing class that implements the old method set
but not the new one. However, the only two classes that need to satisfy `SpanProtocol` are Python `Span`
and Rust `Span` — both would be updated together.

Third-party implementors of `SpanProtocol` (out-of-tree) would have their `isinstance` checks break.
This is a protocol-extension breakage. Whether it matters depends on whether any out-of-tree consumer
has written a class that `isinstance`-checks against `SpanProtocol`. The prior exploration
(`exploration-linecol.md §4 "Consequence for clockwork"`) shows at least `cst_util.py` in the clockwork
consumer uses `SpanProtocol` for type annotation, but does not write custom `SpanProtocol`
implementors.

**Annotation churn**: adding `line_col()` to the protocol means any consumer typing `x: SpanProtocol`
gets the new method for free — no annotation churn for callers. But consumers who have written their own
`SpanProtocol`-conformant stub classes must add the method.

### Generated code and regen

Generated parsers (`bootstrap_parser.py`, `fltk_parser.py`) produce `Span` objects via
`Span.with_source(...)` — they do not call `line_col()`. No regeneration of parsers is needed to add
`line_col()` to the protocol and the two `Span` implementations.

CST node files (`fltk_cst.py`, `bootstrap_cst.py`, etc.) store spans as fields but do not call any
span methods. No regeneration needed.

### Return type: `LineColPos` vs tuple

`LineColPos` is defined in `terminalsrc.py:155–159` as a frozen dataclass with `line: int`, `col: int`,
`line_span: Span`. This is an in-tree Python type, not pyo3-exposed. Returning it from the new protocol
method would require either:
- Keeping `LineColPos` as a Python dataclass (works on Python backend; Rust pyo3 method returns it as a
  Python object constructed from Rust data).
- Or returning a tuple `(int, int)` only (omits `line_span`; simpler pyo3 surface).

`line_span` is useful for error-formatting (see `errors.py:133`) but adds complexity to the pyo3 return
path. The Rust `LineColPos.line_span` is source-bearing (improvement over Python's sourceless version),
so equivalence is observable in the `line_span.text()` behavior.

### `SourceInner` and caching

`Arc<SourceInner>` (`span.rs:46–48`) has a comment explicitly anticipating "future cached metadata
(e.g. line-offset tables)." Adding a `line_ends: OnceLock<Vec<i64>>` field to `SourceInner` (Rust) is
the natural place for the cache on the Rust backend — it would be shared across all spans pointing to
the same source allocation. This changes the `SourceInner` struct layout, which affects
`_fltk_cst_core_abi_layout` (the ABI probe checks `sizeof::<SourceText as PyClassImpl>::Layout>`, not
`sizeof::<SourceInner>`, so this change does NOT affect the ABI probe).

On the Python backend, no cache equivalent exists on the span; the `TerminalSource.line_ends` cache
would not be reachable from a `Span` that only holds `_source: str`. A span-level method on the Python
backend would recompute line-ends on every call unless `SourceText` is extended to hold a cache (it is
currently a thin wrapper `@dataclass(frozen=True, slots=True)` over a single `str` field).

### Error contract

Python `pos_to_line_col` raises `ValueError` for `pos > len(terminals)`. Rust returns `Option<None>`.
For a `Span.line_col()` method, both backends should agree: the natural analogue of `text() -> str |
None` is `line_col() -> LineColPos | None` (returns `None` when sourceless or indices are invalid).

---

## Open factual questions

1. **`SourceInner` mutation vs immutability**: `SourceInner` is not `pub` but `Arc<SourceInner>` is
   shared. Adding `OnceLock<Vec<i64>>` to `SourceInner` requires interior mutability — `OnceLock`
   provides this already, but `SourceInner` would need to be `Send + Sync` (which `OnceLock<Vec<i64>>`
   is). This is the same pattern already used in `TerminalSource` (`terminalsrc.rs:46`). Not confirmed:
   whether any consumer crate places constraints on `Sync`-ability of `SourceInner`.

2. **`LineColPos` Python type for the protocol return**: the protocol must declare a concrete return
   type. `LineColPos` from `fltk.fegen.pyrt.terminalsrc` is the only existing dataclass for this.
   Alternatively, a new type in `span_protocol.py` or `span.py` could be defined. Not confirmed:
   whether clockwork or other consumers already import and construct `LineColPos` directly (would affect
   whether it can be moved).

3. **`line_span` in the protocol return type**: returning `line_span: Span` where `Span` is the
   concrete backend class (Python or Rust) means the return type is not fully `SpanProtocol`-typed.
   This is the same asymmetry already present in `merge`/`intersect` (Python returns `Span`, Rust
   returns `Span`; both satisfy `SpanProtocol`). Not a blocker, just worth noting for type annotation
   precision on the `line_span` field.

4. **Empty-string / negative-index behavior parity**: Python `pos_to_line_col(-1)` on empty string
   returns `LineColPos(line=0, col=-1, line_span=Span(-1, -1))`. Rust returns the same result (confirmed
   by `terminalsrc.rs:496–502`). A span-level `line_col()` with `start=-1` (e.g., `UnknownSpan`) would
   hit this path. Confirmed: returns `(line=0, col=-1)` on both backends. But `UnknownSpan.line_col()`
   is arguably meaningless — returning `None` for negative-index spans is cleaner and already the
   pattern used by `text()`.
