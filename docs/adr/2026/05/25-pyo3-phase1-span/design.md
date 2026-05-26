# Phase 1 Design: Dual-Backend Span with Source-Bearing Capability

Concise. Precise. No padding. Audience: smart human/LLM implementing this.

---

## Root Cause / Context

CST nodes carry `Span(start, end)` but no reference to source text. Users must externally pair CST with a `TerminalSource` or raw `str` to extract text (exploration Section 4, "The Python design's problem"). The requirements mandate both backward-compatible `Span(start, end)` construction and a better API where `span.text()` returns source text directly.

The current `Span` is a frozen dataclass at `terminalsrc.py:7-12`. It is constructed ~80 times in `fltk_parser.py` (keyword args), twice in `terminalsrc.py` (positional), and used as both a node field and a leaf child value in `children` lists. Phase 0 established the build infrastructure (`src/lib.rs`, `Cargo.toml` with PyO3 0.23 + abi3-py310).

**Key architectural constraint (user notes):** Phase 1 delivers *two swappable backends* — the existing pure-Python Span (updated with the better API) and a new Rust-backed Span — not a replacement of Python with Rust. Code that works with either backend uses a `SpanProtocol` for type annotations and an `AnySpan` union type for the rare `isinstance` case.

---

## Proposed Approach

### Architecture: Two Backends + Protocol

```
fltk/fegen/pyrt/
  span_protocol.py      # SpanProtocol (typing.Protocol), AnySpan union alias
  terminalsrc.py         # Pure-Python Span (updated with better API), TerminalSource, etc.

fltk/_native             # Rust extension (from Phase 0)
  Span, SourceText, UnknownSpan   # Rust-backed Span

fltk/fegen/pyrt/span.py  # Backend selector: re-exports from Rust or Python
```

The active backend is selected at import time. Code that needs to be backend-agnostic annotates with `SpanProtocol` (or `AnySpan` for `isinstance`). The existing `terminalsrc.py` import path continues to work — it always provides the pure-Python implementation.

### `SpanProtocol` — Protocol Class

`fltk/fegen/pyrt/span_protocol.py`:

```python
from typing import Protocol, runtime_checkable, Union
import fltk.fegen.pyrt.terminalsrc as _pymod

@runtime_checkable
class SpanProtocol(Protocol):
    def text(self) -> str | None: ...
    def text_or_raise(self) -> str: ...
    def has_source(self) -> bool: ...
    def len(self) -> int: ...
    def is_empty(self) -> bool: ...
    def merge(self, other: 'SpanProtocol') -> 'SpanProtocol': ...
    def intersect(self, other: 'SpanProtocol') -> 'SpanProtocol | None': ...

try:
    from fltk._native import Span as _RustSpan
    AnySpan = Union[_pymod.Span, _RustSpan]
except ImportError:
    AnySpan = _pymod.Span
```

Callers writing backend-agnostic code use `SpanProtocol` in type annotations. The `AnySpan` union is for the rare `isinstance(child, AnySpan)` check (e.g., generated unparser dispatch at `gsm2unparser.py:983`). `@runtime_checkable` on `SpanProtocol` is an alternative for `isinstance`, but the union is more explicit and avoids the performance overhead of structural `isinstance` checks in hot paths.

### Pure-Python Span — Updated with Better API

The existing `Span` dataclass in `terminalsrc.py` is *retained* and extended with the source-bearing API. It remains the default backend — existing code is unaffected.

```python
# terminalsrc.py — updated Span

@dataclass(frozen=True, eq=True, slots=True)
class Span:
    """Span of elements in the range [start, end)"""
    start: int
    end: int
    _source: str | None = field(default=None, repr=False, compare=False, hash=False)

    def text(self) -> str | None:
        if self._source is None:
            return None
        start, end = self.start, self.end
        if start < 0 or end < 0 or start > end:
            return None
        if end > len(self._source):
            return None
        return self._source[start:end]

    def text_or_raise(self) -> str:
        result = self.text()
        if result is None:
            raise ValueError(f"Span({self.start}, {self.end}) has no source text")
        return result

    def has_source(self) -> bool:
        return self._source is not None

    def len(self) -> int:
        if self.start < 0 or self.end < 0:
            return 0
        return max(0, self.end - self.start)

    def is_empty(self) -> bool:
        return self.start >= self.end

    def merge(self, other: 'Span') -> 'Span':
        if self._source is not None and other._source is not None and self._source is not other._source:
            raise ValueError("cannot merge spans from different sources")
        source = self._source if self._source is not None else other._source
        return Span(min(self.start, other.start), max(self.end, other.end), source)

    def intersect(self, other: 'Span') -> 'Span | None':
        s = max(self.start, other.start)
        e = min(self.end, other.end)
        if s >= e:
            return None
        source = self._source if self._source is not None else other._source
        return Span(s, e, source)

    @classmethod
    def with_source(cls, start: int, end: int, source: str) -> 'Span':
        return cls(start=start, end=end, _source=source)
```

Key decisions for the Python backend:
- `_source: str | None` with `compare=False, hash=False` — equality/hashing use only `(start, end)`, satisfying acceptance criterion 13.
- `repr=False` — `repr(Span(1, 5))` still produces `Span(start=1, end=5)`, not leaking the source text.
- `_source` stores a plain `str` reference. In Python, strings are immutable and refcounted — multiple spans sharing the same source string share the same object (no copy). This is the Python-native equivalent of `Arc<str>`.
- `with_source` classmethod for constructing source-bearing spans. The source is a plain `str`, not a `SourceText` wrapper — in pure Python there is no need for the wrapper since Python `str` is already immutable and shared.
- `Span(start, end)` backward compatibility: the `_source` field defaults to `None`, so `Span(1, 5)` and `Span(start=1, end=5)` work unchanged. The leading underscore signals "don't construct with this directly."
- `slots=True` is preserved. Adding `_source` to the slots is automatic with `@dataclass(slots=True)` in Python 3.10+.

### `text_or_raise` — Throwing Variant

`text_or_raise()` returns `str` (not `str | None`). When the span has no source or indices are invalid, it raises `ValueError`. This eliminates the `if text is None: raise ...` boilerplate that pervades source-text-consuming code.

Name rationale: `text_or_raise` clearly communicates the contract — "returns text or raises." Alternatives rejected: `ensure_text` (user: "ensure" implies mutation/setup), `require_text` (implies a side-effect check), `text_strict` (unclear what "strict" means).

Both backends implement this identically.

### Rust Struct Layout

```rust
// src/span.rs

use std::sync::Arc;

/// Shared heap allocation holding source text.
pub(crate) struct SourceInner {
    text: String,
}

/// Core span type exposed to Python. 24 bytes on 64-bit platforms.
/// start/end are byte indices into source UTF-8 text. Not exposed to Python;
/// all access goes through methods (text(), len(), etc.).
#[pyclass(frozen, eq, hash)]
#[derive(Clone)]
pub struct Span {
    start: i64,
    end: i64,
    source: Option<Arc<SourceInner>>,
}
```

Key decisions:
- `source: Option<Arc<SourceInner>>` uses null-pointer optimization — 8 bytes regardless of whether source is present. Total struct size: **24 bytes** (i64 + i64 + 8-byte pointer).
- `Arc<SourceInner>` is `Send + Sync`, satisfying the thread-safety constraint.
- All spans from one parse share a single `Arc<SourceInner>`. Cloning the `Arc` is a ref-count increment — no per-span string allocation.
- `#[pyclass(frozen, eq, hash)]` with PyO3 0.23: `eq` derives `__eq__`/`__ne__` from Rust `PartialEq`; `hash` derives `__hash__` from Rust `Hash`. We implement `PartialEq` and `Hash` manually to use only `(start, end)` — source reference is excluded per requirements (acceptance criterion 13).
- `start` and `end` are **not** exposed as Python attributes (no `#[pyo3(get)]`). All access goes through methods. See "Index Semantics" section.

**Why `Arc<SourceInner>` instead of `Arc<str>`:** `Arc<str>` is a fat pointer (16 bytes: pointer + length), making `Option<Arc<str>>` 16 bytes and the Span struct 32 bytes. `Arc<SourceInner>` is a thin pointer (8 bytes) because `SourceInner` is `Sized`. `SourceInner` currently holds only `text: String` but the wrapper leaves room for future cached metadata (line-offset tables, etc.) without changing the `Span` layout.

### `SourceText` Python Exposure (Rust Backend Only)

```python
# Exposed as fltk._native.SourceText
source = SourceText("the full source string")
span = Span.with_source(4, 8, source)
assert span.text() == "full"
```

`SourceText` is a `#[pyclass(frozen)]` wrapping `Arc<SourceInner>`. Construction from Python takes a `&str` (PyO3 extracts from Python `str`), copies it into a heap-allocated `SourceInner` behind an `Arc`. The copy is unavoidable at the Python-Rust boundary (Python `str` is UTF-16/UCS-4 internally; Rust needs UTF-8). This is a one-time cost per parse. The byte indices stored in Rust-backed Spans are offsets into this UTF-8 copy.

The Rust `Span.with_source` takes a `SourceText` argument (not a raw `str`) because it needs to share the `Arc<SourceInner>` across spans. The Python backend's `with_source` takes a raw `str` because Python strings are already immutable and refcounted. This API difference is acceptable — `with_source` is a backend-specific construction method, not part of the cross-backend `SpanProtocol`.

**Phase 1 scope note:** Phase 1 delivers the *capability* for source-bearing spans and validates it via synthetic construction (`Span.with_source`). No production parse path emits source-bearing spans in this phase. Wiring the parser to attach source text is a follow-up phase.

### Rust Python API Surface

```python
# Construction (sourceless)
Span(1, 5)               # positional (byte indices)
Span(start=1, end=5)     # keyword

# Source-bearing construction
Span.with_source(1, 5, source)  # classmethod; source is a SourceText handle

# NO attribute access: span.start and span.end are NOT exposed.
# All access goes through methods.

# Access methods
span.text() -> str | None     # Returns source[start:end] if source exists, None otherwise
span.text_or_raise() -> str   # Returns source[start:end] or raises ValueError
span.has_source() -> bool     # Query whether source reference exists
span.len() -> int             # end - start (byte count)
span.is_empty() -> bool       # start >= end
span.merge(other) -> Span     # smallest enclosing span
span.intersect(other) -> Span | None  # overlap or None

# Standard protocols
repr(span) -> "Span(start=1, end=5)"   # repr shows raw indices for debugging
span == other              # compares (start, end) only
hash(span)                 # hashes (start, end) only
span.start = 5            # raises AttributeError (no such attribute)
```

### `UnknownSpan` Constant

Both backends provide `UnknownSpan = Span(-1, -1)`.

- Pure Python: `UnknownSpan: Final = Span(-1, -1)` in `terminalsrc.py` (unchanged).
- Rust: module-level constant in `fltk._native`:

```rust
#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Span>()?;
    m.add_class::<SourceText>()?;
    let unknown = Span { start: -1, end: -1, source: None };
    m.add("UnknownSpan", Py::new(m.py(), unknown)?)?;
    Ok(())
}
```

### Index Semantics — Abstract Indices

**Core contract change:** `start` and `end` are no longer guaranteed to be codepoint indices. They are *abstract indices* — opaque values whose meaning depends on the backend:

- **Python backend:** codepoint indices into a Python `str` (unchanged from current behavior). `terminals[span.start : span.end]` continues to work.
- **Rust backend:** byte indices into UTF-8 source text. Not directly usable for Python `str` slicing. All text access goes through `span.text()` / `span.text_or_raise()`.

The *access methods* are the contract — not the index values. Code that uses `text()` works identically on both backends. Code that slices `terminals[span.start : span.end]` works on the Python backend (where indices happen to be codepoints) but is not portable to the Rust backend.

**Rust backend: `start`/`end` are private.** No `#[pyo3(get)]` — Python code cannot read `span.start` or `span.end` on a Rust-backed Span. This forces all access through the method API and ensures future Rust-only code is clean. The Python backend retains public `start`/`end` for backward compatibility (existing code depends on `terminals[span.start : span.end]`).

**Consequence for `SpanProtocol`:** The protocol does not include `start`/`end` properties. Backend-agnostic code cannot rely on index access — it uses `text()`, `len()`, `is_empty()`, `merge()`, `intersect()`.

**Consequence for existing consumers:** The following call sites use `terminals[span.start : span.end]` and remain valid because they use the Python backend:
- `fltk2gsm.py:24,126,130` — CST-to-GSM visitors
- `bootstrap2gsm.py:24,118,122` — bootstrap CST-to-GSM visitors
- `unparse/pyrt.py:33-35` — `extract_span_text()`
- `fmt_config.py:360,445,451,480,682,892` — format config parsing
- Generated parser code (`fltk_parser.py`, `fltk_trivia_parser.py`) — uses `span.start`/`span.end` for position tracking

These consumers import from `terminalsrc` and always get the Python backend. When (in a future phase) the Rust backend produces spans, these sites must migrate to `span.text()` or `span.text_or_raise()`. That migration is out of scope for Phase 1.

### Utility Methods

Both backends expose these methods to support operations that would otherwise require direct index access:

```python
# On SpanProtocol and both implementations:
def len(self) -> int: ...       # end - start; semantic: "size in index units" (codepoints or bytes)
def is_empty(self) -> bool: ... # start == end (or start < 0, i.e., unknown/sentinel)
def merge(self, other: Self) -> Self: ...      # smallest span covering both; raises if different sources
def intersect(self, other: Self) -> Self | None: ... # overlap region; None if disjoint
```

**`len()`** returns `end - start`. For the Python backend this is character count; for the Rust backend it is byte count. This is intentionally *not* `__len__` — Span is not a collection and `len(span)` would be misleading. Named method `len()` is unambiguous.

**`is_empty()`** returns `True` if `start >= end` (covers both zero-width `Span(5,5)` and sentinels like `Span(-1,-1)`).

**`merge(other)`** returns `Span(min(self.start, other.start), max(self.end, other.end))`. Source propagation: if both spans have the same source (by identity), the result carries that source; if only one has a source, the result carries that source; if both have sources and they differ, raises `ValueError` (merging spans from different documents is a bug).

**`intersect(other)`** returns the overlapping region, or `None` if the spans are disjoint (including when either is a sentinel/unknown span).

Rust implementations:

```rust
fn len(&self) -> i64 {
    if self.start < 0 || self.end < 0 { return 0; }
    (self.end - self.start).max(0)
}

fn is_empty(&self) -> bool {
    self.start >= self.end
}

#[pyo3(signature = (other,))]
fn merge(&self, other: &Span) -> PyResult<Span> {
    // Check source compatibility
    match (&self.source, &other.source) {
        (Some(a), Some(b)) if !Arc::ptr_eq(a, b) => {
            return Err(PyValueError::new_err("cannot merge spans from different sources"));
        }
        _ => {}
    }
    let source = self.source.clone().or_else(|| other.source.clone());
    Ok(Span {
        start: self.start.min(other.start),
        end: self.end.max(other.end),
        source,
    })
}

#[pyo3(signature = (other,))]
fn intersect(&self, other: &Span) -> Option<Span> {
    let s = self.start.max(other.start);
    let e = self.end.min(other.end);
    if s >= e { return None; }
    let source = self.source.clone().or_else(|| other.source.clone());
    Some(Span { start: s, end: e, source })
}
```

### Backend Selection — `fltk/fegen/pyrt/span.py`

```python
# fltk/fegen/pyrt/span.py
try:
    from fltk._native import Span, UnknownSpan, SourceText
except ImportError:
    from fltk.fegen.pyrt.terminalsrc import Span, UnknownSpan
    SourceText = None  # not available in pure-Python backend
```

This module is the recommended import point for code that wants whichever backend is available. Existing code importing from `terminalsrc` is unaffected — it always gets the pure-Python version.

**Note:** The `terminalsrc.py` import path is *not* changed to re-export from Rust. Both backends coexist. Code that imports `from fltk.fegen.pyrt.terminalsrc import Span` always gets the Python Span. Code that imports `from fltk._native import Span` always gets the Rust Span. Code that imports `from fltk.fegen.pyrt.span import Span` gets whichever is available (preferring Rust).

### File Changes

| File | Change |
|---|---|
| `src/lib.rs` | Add `mod span;`, register `Span`, `SourceText`, `UnknownSpan` in `_native` module |
| `src/span.rs` | New file: Rust `Span`, `SourceText`, `SourceInner` |
| `fltk/fegen/pyrt/terminalsrc.py` | Update `Span` dataclass: add `_source` field, `text()`, `text_or_raise()`, `has_source()`, `len()`, `is_empty()`, `merge()`, `intersect()`, `with_source()` classmethod |
| `fltk/fegen/pyrt/span_protocol.py` | New file: `SpanProtocol`, `AnySpan` |
| `fltk/fegen/pyrt/span.py` | New file: backend selector re-exports |
| `Cargo.toml` | No changes needed (PyO3 dependency already present) |

### Rust Implementation Details

**`#[new]` constructor:**
```rust
#[new]
#[pyo3(signature = (start, end))]
fn new(start: i64, end: i64) -> Self {
    Span { start, end, source: None }
}
```

**`with_source` classmethod:**
```rust
#[classmethod]
#[pyo3(signature = (start, end, source))]
fn with_source(_cls: &Bound<'_, PyType>, start: i64, end: i64, source: &SourceText) -> Self {
    Span { start, end, source: Some(source.inner.clone()) }
}
```

**`text` method:**

Indices are byte offsets into the UTF-8 `SourceInner.text`. Slicing is O(1) — no character-index conversion needed. The Rust backend never promises that indices are codepoint offsets (see "Index Semantics" section above).

```rust
fn text(&self) -> Option<String> {
    let inner = self.source.as_ref()?;
    let start = self.start as usize;
    let end = self.end as usize;
    if self.start < 0 || self.end < 0 || start > end {
        return None;
    }
    let src = &inner.text;
    if end > src.len() { return None; }
    // Validate UTF-8 boundary: start and end must land on char boundaries.
    if !src.is_char_boundary(start) || !src.is_char_boundary(end) {
        return None;
    }
    Some(src[start..end].to_owned())
}
```

**`text_or_raise` method:**
```rust
fn text_or_raise(&self) -> PyResult<String> {
    self.text().ok_or_else(|| {
        PyValueError::new_err(format!("Span({}, {}) has no source text", self.start, self.end))
    })
}
```

Returns `Option<String>` (not `Option<&str>`) because PyO3 cannot return a reference into `Arc` data — the borrow would outlive the GIL-holding call.

**`PartialEq` and `Hash` implementations:**
```rust
impl PartialEq for Span {
    fn eq(&self, other: &Self) -> bool {
        self.start == other.start && self.end == other.end
    }
}
impl Eq for Span {}

impl Hash for Span {
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.start.hash(state);
        self.end.hash(state);
    }
}
```

**`__repr__`:**
```rust
fn __repr__(&self) -> String {
    format!("Span(start={}, end={})", self.start, self.end)
}
```

**Frozen enforcement:** `#[pyclass(frozen)]` prevents attribute assignment from Python.

### `SourceText` Struct

```rust
#[pyclass(frozen)]
pub struct SourceText {
    inner: Arc<SourceInner>,
}

#[pymethods]
impl SourceText {
    #[new]
    fn new(text: &str) -> Self {
        SourceText {
            inner: Arc::new(SourceInner {
                text: text.to_owned(),
            }),
        }
    }
}
```

---

## Edge Cases / Failure Modes

### Pure-Python `_source` field visibility
The `_source` field is technically accessible as `span._source` from Python (leading underscore is convention, not enforcement). This is acceptable — frozen dataclasses make it read-only, and the underscore signals "private." The Rust backend's `source` field is truly hidden (no `#[pyo3(get)]`).

### Backward compatibility of `_source` in `__init__`
Adding `_source` as a keyword arg with a default does not break existing `Span(1, 5)` or `Span(start=1, end=5)` construction. However, `Span(1, 5, "some source")` would work positionally — the leading underscore and `repr=False` discourage this, but it is technically possible. The `with_source` classmethod is the documented API.

### `dataclass(eq=True)` with `compare=False` on `_source`
Python's `@dataclass(eq=True)` auto-generates `__eq__` using only fields where `compare=True`. Since `_source` has `compare=False`, equality uses only `(start, end)`. Similarly, `hash=False` on `_source` means `__hash__` uses only `(start, end)`. This matches the Rust behavior and satisfies acceptance criterion 13.

### Negative indices in `text()`
`Span(-1, -1)` (UnknownSpan) with a source reference: `text()` returns `None` when `start < 0 || end < 0 || start > end`. `text_or_raise()` raises `ValueError`. Both backends handle this consistently.

### Out-of-bounds indices
`Span(0, 999)` on a 10-character source: `text()` returns `None`.

### Empty spans
`Span(5, 5)` (zero-width): `text()` returns `""` — valid empty slice.

### `UnknownSpan` identity vs equality
`UnknownSpan is Span(-1, -1)` is `False` (different Python object). `UnknownSpan == Span(-1, -1)` is `True`. No evidence in codebase of `is` comparison on spans.

### Hash values differ between backends
The Rust backend uses Rust's `Hash` trait; the Python backend uses Python's `hash((start, end))` (generated by `@dataclass`). Two spans from different backends with the same `(start, end)` may not have the same hash value. This is acceptable — the two backends are not intended to be mixed within a single dict or set. The invariant `a == b implies hash(a) == hash(b)` holds *within* each backend.

### Cross-backend `__eq__`
`python_span == rust_span` where both have the same `(start, end)`: the Python dataclass `__eq__` checks `type(other) is type(self)` and returns `NotImplemented` for non-matching types. The Rust `__eq__` similarly checks the type. So cross-backend equality returns `NotImplemented` → Python falls back to identity comparison → `False`. This is acceptable since the backends are not mixed at runtime.

### Thread safety
`#[pyclass(frozen)]` makes Rust `Span` `Send + Sync`. The pure-Python `Span` is a frozen dataclass — immutable, safe across threads under the GIL.

### Mid-codepoint byte indices (Rust backend)
If a Rust-backed Span has `start` or `end` at a UTF-8 continuation byte (not a char boundary), `text()` returns `None` and `text_or_raise()` raises `ValueError`. This is a safety check — well-formed spans from a correctly functioning parser will never hit this, but it prevents undefined behavior if indices are corrupted or manually constructed with bad values.

### `merge()` / `intersect()` with sentinel spans
`merge(Span(-1, -1), Span(3, 8))` produces `Span(-1, 8)` — `min(-1, 3) = -1`. The result is a non-standard span (negative start). Callers merging with unknown/sentinel spans should check `is_empty()` first. No special-casing in the implementation — sentinel handling is the caller's responsibility.

### `isinstance(x, Span)` with mixed backends
The generated unparser uses `isinstance(child, Span)` for dispatch. If the Rust backend is active, unparser code must import `Span` from the Rust backend (or use `AnySpan`). In Phase 1, no generated code changes — the unparser still imports from `terminalsrc` and gets the Python `Span`. The `AnySpan` union and `SpanProtocol` are available for future phases or user code that needs cross-backend compatibility.

---

## Test Plan

### Existing tests (must pass unmodified)
All tests in the repository exercise `Span` transitively through parser/unparser/visitor paths. `uv run pytest` is the gate. No test file modifications permitted. These tests exercise the *pure-Python* backend since `terminalsrc.py` imports are unchanged.

### New tests (`tests/test_span.py`) — Pure-Python Backend

1. **Construction:** `Span(1, 5)`, `Span(start=1, end=5)`, `Span(-1, -1)` — verify `start`/`end` values.
2. **Equality:** `Span(1, 2) == Span(1, 2)`, `Span(1, 2) != Span(1, 3)`.
3. **Hash:** `hash(Span(1, 2)) == hash(Span(1, 2))`, `{Span(1,2): "x"}[Span(1,2)] == "x"`.
4. **Repr:** `repr(Span(1, 5)) == "Span(start=1, end=5)"`.
5. **Frozen:** `with pytest.raises(AttributeError): span.start = 5`.
6. **UnknownSpan:** `UnknownSpan == Span(-1, -1)`, `UnknownSpan.start == -1`.
7. **Source-bearing span:** `Span.with_source(6, 11, "hello world")` → `span.text() == "world"`.
8. **Sourceless span text:** `Span(1, 5).text() is None`.
9. **text_or_raise sourceless:** `with pytest.raises(ValueError): Span(1, 5).text_or_raise()`.
10. **text_or_raise source-bearing:** `Span.with_source(0, 5, "hello").text_or_raise() == "hello"`.
11. **has_source:** source-bearing returns `True`, sourceless returns `False`.
12. **Equality ignores source:** `Span.with_source(1, 5, "x" * 10) == Span(1, 5)` is `True`.
13. **Hash ignores source:** `hash(Span.with_source(1, 5, "x" * 10)) == hash(Span(1, 5))`.
14. **Negative index text():** `Span.with_source(-1, -1, "hello").text() is None`.
15. **Out-of-bounds text():** `Span.with_source(0, 999, "hello").text() is None`.
16. **Unicode source (codepoint indices):** `Span.with_source(1, 4, "héllo").text() == "éll"` — validates Python backend uses codepoint indices.
17. **len():** `Span(1, 5).len() == 4`, `Span(-1, -1).len() == 0`.
18. **is_empty():** `Span(5, 5).is_empty()` is `True`, `Span(1, 5).is_empty()` is `False`, `Span(-1, -1).is_empty()` is `True`.
19. **merge():** `Span(1, 5).merge(Span(3, 8)) == Span(1, 8)`. Source-bearing: merge preserves shared source. Different sources: raises `ValueError`.
20. **intersect():** `Span(1, 5).intersect(Span(3, 8)) == Span(3, 5)`. Disjoint: returns `None`.

### New tests (`tests/test_rust_span.py`) — Rust Backend

Mirrors `test_span.py` but imports from `fltk._native`, uses `SourceText` for source-bearing construction, and accounts for byte-index semantics. Note: Rust `Span` does **not** expose `start`/`end` attributes.

1. **Construction:** `Span(1, 5)`, `Span(start=1, end=5)` — no error.
2. **Equality:** `Span(1, 2) == Span(1, 2)`, `Span(1, 2) != Span(1, 3)`.
3. **Hash:** `hash(Span(1, 2)) == hash(Span(1, 2))`, `{Span(1,2): "x"}[Span(1,2)] == "x"`.
4. **Repr:** `repr(Span(1, 5)) == "Span(start=1, end=5)"` (repr shows raw indices for debugging).
5. **Frozen / no attribute access:** `with pytest.raises(AttributeError): span.start`. `with pytest.raises(AttributeError): span.start = 5`.
6. **UnknownSpan:** `UnknownSpan == Span(-1, -1)`.
7. **Source-bearing span:** `SourceText("hello world")` → `Span.with_source(6, 11, src)` → `span.text() == "world"`.
8. **Sourceless span text:** `Span(1, 5).text() is None`.
9. **text_or_raise sourceless:** `with pytest.raises(ValueError): Span(1, 5).text_or_raise()`.
10. **text_or_raise source-bearing:** `Span.with_source(0, 5, SourceText("hello")).text_or_raise() == "hello"`.
11. **has_source:** source-bearing returns `True`, sourceless returns `False`.
12. **Equality ignores source:** `Span.with_source(1, 5, src) == Span(1, 5)` is `True`.
13. **Hash ignores source:** `hash(Span.with_source(1, 5, src)) == hash(Span(1, 5))`.
14. **Negative index text():** `Span.with_source(-1, -1, src).text() is None`.
15. **Out-of-bounds text():** `Span.with_source(0, 999, src).text() is None`.
16. **Unicode source (byte indices):** `SourceText("héllo")` — `"é"` is 2 bytes UTF-8, so `Span.with_source(0, 3, src).text() == "hé"` (bytes 0..3). `Span.with_source(1, 3, src).text() == "é"` (bytes 1..3). `Span.with_source(1, 2, src).text() is None` (byte 2 is mid-codepoint, not a char boundary).
17. **len():** `Span(1, 5).len() == 4`.
18. **is_empty():** `Span(5, 5).is_empty()` is `True`, `Span(1, 5).is_empty()` is `False`.
19. **merge():** `Span(1, 5).merge(Span(3, 8)) == Span(1, 8)`. Different sources: raises `ValueError`.
20. **intersect():** `Span(1, 5).intersect(Span(3, 8)) == Span(3, 5)`. Disjoint: returns `None`.
21. **SourceText opaque:** Verify `SourceText` has no exposed attributes beyond construction.
22. **Import paths:** `from fltk._native import Span, UnknownSpan, SourceText` — all resolve.
23. **TypeError on bad args:** `with pytest.raises(TypeError): Span("a", "b")`.

### New tests (`tests/test_span_protocol.py`) — Protocol and Backend Selection

1. **Protocol conformance (Python):** `isinstance(py_span, SpanProtocol)` is `True` (with `@runtime_checkable`).
2. **Protocol conformance (Rust):** `isinstance(rust_span, SpanProtocol)` is `True`.
3. **AnySpan isinstance (Python):** `isinstance(py_span, AnySpan)` is `True`.
4. **AnySpan isinstance (Rust):** `isinstance(rust_span, AnySpan)` is `True`.
5. **Backend selector:** `from fltk.fegen.pyrt.span import Span` resolves (to Rust if available, Python otherwise).
6. **Protocol has no start/end:** Verify `SpanProtocol` does not require `start`/`end` properties.

---

## Open Questions

1. **`SourceText` API surface:** Phase 1 exposes `SourceText("...")` as an opaque constructor. Should it also expose a `len` property or `text` property for diagnostic use? Minimal is safer for forward-compatibility. User-judgment call.

2. **Should the Python `Span.with_source` accept a `SourceText` too?** Currently the Python backend takes a raw `str` and the Rust backend takes a `SourceText`. This asymmetry is acceptable since `with_source` is backend-specific, but user feedback may prefer uniform syntax. Deferrable.

## Decided (not open)

- **Two backends vs replacement:** Two backends coexist (user note 1). Pure-Python Span is retained and updated.
- **Protocol vs ABC:** Protocol (structural typing) over ABC (nominal typing). Avoids requiring both backends to inherit from a common base. More Pythonic for duck-typed code.
- **Throwing variant name:** `text_or_raise` (user rejected "ensure_text"; `text_or_raise` follows `x_or_raise` convention).
- **`Span.with_source` vs `Span(start, end, source=src)`:** Classmethod `Span.with_source` — more explicit, avoids signature confusion.
- **`isinstance` with `Union` in Python 3.10+:** Verified: `isinstance(x, Union[A, B])` works in Python 3.10+. `AnySpan` as a `Union` type alias is valid for `isinstance` checks. No fallback to tuple form needed.
- **Index semantics:** Abstract indices — codepoints in Python, bytes in Rust. Access methods (`text()`, `len()`, etc.) are the contract, not the raw index values. Rust backend hides `start`/`end`; Python backend retains them for backward compatibility. The `is_ascii` optimization and O(N) char-index conversion are eliminated entirely.
