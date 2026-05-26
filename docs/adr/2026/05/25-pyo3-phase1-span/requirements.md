# Phase 1 Requirements: Span Rust Implementation

Concise. Precise. No padding. Audience: smart human/LLM.

---

## Goals

Replace `terminalsrc.Span` with a PyO3 Rust implementation. Provide both a backward-compatible API and a better API that allows accessing source text directly from a span.

---

## In Scope

- Rust-backed `Span` exposed as a Python class via PyO3, frozen (immutable).
- Backward-compatible API: `Span(start, end)`, attribute access, equality, hashing, repr.
- `UnknownSpan` module-level constant (`Span(-1, -1)`).
- Better API: source-text-bearing spans with `span.text()` or equivalent, covering parsed source, synthetic/private source, and no-source cases.
- Re-export preserving all existing import paths.
- Full test suite passes with no modifications to existing test files or non-`terminalsrc.py` Python source.

## Out of Scope

- `TerminalSource` Rust implementation (stays Python for now).
- CST node classes (Phase 2+).
- Generated parser/unparser changes.
- Performance benchmarking.
- `LineColPos` migration (stays as Python dataclass).

---

## System Behavior

### Backward-Compatible Span API

| Input | Output |
|---|---|
| `Span(1, 5)` (positional) | Frozen `Span` with `start=1`, `end=5` |
| `Span(start=1, end=5)` (keyword) | Same |
| `Span(-1, -1)` | Value-equal to `UnknownSpan` |

Negative values are valid inputs (used as sentinels: `-1` for unknown/unclosed).

#### Attribute Access

- `span.start` returns `int`.
- `span.end` returns `int`.
- Both are read-only. Assignment raises `AttributeError`.

#### Equality and Hashing

- `Span(a, b) == Span(a, b)` is `True`.
- `Span(a, b) == Span(c, d)` is `False` when `a != c` or `b != d`.
- `hash(Span(a, b)) == hash(Span(a, b))`.
- Equality with non-Span objects returns `NotImplemented`.
- Equality and hashing are determined solely by `(start, end)` — source reference presence does not affect equality or hash.

#### Repr

- `repr(Span(1, 5))` produces `Span(start=1, end=5)`.

#### isinstance

- `isinstance(x, Span)` works for type discrimination (used in generated unparser dispatch).

#### Source Text Slicing (unchanged)

- `terminals[span.start : span.end]` continues to work — `start` and `end` are character indices into a Python `str`.

### UnknownSpan

- Module-level constant, value `Span(-1, -1)`.
- `UnknownSpan == Span(-1, -1)` is `True`.

### Better API: Source-Bearing Spans

Spans must support carrying an optional reference to their source text. Three states must be representable:

1. **Parsed source** — span references a shared source string from a parse operation.
2. **Synthetic/private source** — span references its own source string (e.g., from a refactoring tool creating synthetic nodes).
3. **No source** — span has no source reference (e.g., `UnknownSpan`, freshly constructed nodes).

Required capabilities:
- A way to construct a source-bearing span (factory method, extended constructor, or separate type — design decides).
- `span.text()` or equivalent — returns the source text slice when a source reference exists, indicates absence otherwise.
- A way to query whether a span has a source reference.
- Backward-compatible: existing code that constructs `Span(start, end)` and never calls source-text methods continues to work unchanged.

### Import Paths

All of these continue to resolve:
- `from fltk.fegen.pyrt.terminalsrc import Span`
- `from fltk.fegen.pyrt.terminalsrc import UnknownSpan`
- `from fltk._native import Span`

### Error Messages

- `Span("a", "b")` raises `TypeError` indicating `start` and `end` must be integers.
- `span.start = 5` raises `AttributeError` (frozen).

---

## Constraints

- **Python compatibility:** 3.10+.
- **Negative values:** `start` and `end` accept negative integers.
- **Character indices:** `start` and `end` are character indices into Python `str`, not byte offsets. This is an invariant of the existing design and must be preserved.
- **Thread safety:** Span must be safe to share across threads. If a source reference is stored, it must also be thread-safe.
- **Memory efficiency (Rust):** Holding source text and retrieving source text subspans in Rust must be memory-efficient, ideally zero-copy. The Rust representation should avoid per-span allocation of source text.
- **Memory efficiency (Python):** Retrieving source text from Python may be less efficient than the Rust path, but ideally still uses non-copying slicing of immutable data rather than allocating new strings per access.
- **Source backing:** The Rust backend need only support UTF-8 text as the terminal source. Supporting arbitrary backing types (as the Python implementation nominally does) is not required.
- **mmap:** File-backed source text via mmap or similar would be ideal but is not a requirement.
- **Sourceless span overhead:** Sourceless spans should not pay significant per-instance overhead for source-reference capability.
- **No existing test modifications:** The Rust `Span` must be a drop-in replacement. If any test fails, the implementation is wrong, not the test.
- **Build:** Must compile via `maturin develop` and pass `uv run pytest`.

---

## Acceptance Criteria

1. `uv run pytest` passes with zero test modifications.
2. `Span(1, 2)` and `Span(start=1, end=2)` both construct successfully.
3. `span.start` and `span.end` return correct values.
4. `Span(1, 2) == Span(1, 2)` is `True`; `Span(1, 2) == Span(1, 3)` is `False`.
5. `hash(Span(1, 2))` is deterministic and consistent with equality.
6. `repr(Span(1, 2))` produces `Span(start=1, end=2)`.
7. `isinstance(Span(1, 2), Span)` is `True`.
8. `UnknownSpan == Span(-1, -1)` is `True`.
9. Assignment to `span.start` raises `AttributeError`.
10. No existing test files or non-`terminalsrc.py` Python source files are modified.
11. Source-bearing spans can be constructed and `text()` (or equivalent) returns the correct slice of source text.
12. Sourceless spans return an appropriate indicator (e.g., `None`) when source text is requested.
13. Two spans with the same `(start, end)` but different source references compare equal and hash equal.
