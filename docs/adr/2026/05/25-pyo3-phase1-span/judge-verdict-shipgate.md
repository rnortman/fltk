# Judge verdict — ship-gate user revision

Phase: ship-gate. Base 6121025..HEAD 2910ddfd. Round 1.
Design doc: `docs/adr/2026/05/25-pyo3-phase1-span/design.md`.
Notes: `notes-shipgate-user.md` (3 findings).

## Findings walk

### note-1 — Fixed (docstrings on Protocol + both impls)

Claim: Protocol, pure-Python Span, and Rust Span lack docstrings.
Disposition: Fixed.

Evidence (commit 5a6a2b6):
- `span_protocol.py`: class-level docstring on `SpanProtocol` (lines 10-17) plus per-method docstrings on all 7 protocol methods (lines 19-55).
- `terminalsrc.py`: per-method docstrings on `text`, `text_or_raise`, `has_source`, `len`, `is_empty`, `merge`, `intersect`, `with_source` (diff confirmed at all 8 methods).
- `src/span.rs`: `///` doc comments on `SourceInner`, `SourceText` struct + `SourceText::new`, `Span` struct (lines 46-62 at HEAD), `Span::new`, `with_source`, `text`, `text_or_raise`, `has_source`, `len`, `is_empty`, `merge`, `intersect`, `__repr__`.

Assessment: All three layers covered. Accept.

### note-2 — Fixed (intersect returns UnknownSpan on empty)

Claim: `intersect()` should return `UnknownSpan` sentinel instead of `None` on empty intersection, across Protocol + both impls, with tests and design updated.
Disposition: Fixed.

Evidence (commits 0344ce6, 2910ddf):
- **Protocol** (`span_protocol.py:50`): return type `"SpanProtocol"` (was `"SpanProtocol | None"`); docstring updated to reference `UnknownSpan` sentinel.
- **Pure-Python** (`terminalsrc.py:82`): `return Span(-1, -1)` replaces `return None`; return annotation changed to `"Span"` from `"Span | None"`; docstring updated.
- **Rust** (`src/span.rs`): `fn intersect` returns `PyResult<Span>` (was `PyResult<Option<Span>>`); disjoint branch returns `Span { start: -1, end: -1, source: None }`; doc comment updated.
- **Tests**: `test_span.py` — `test_intersect_disjoint` asserts `== Span(-1, -1)` (was `is None`); `test_intersect_adjacent_returns_unknown` renamed and updated. `test_rust_span.py` — `test_intersect_disjoint_returns_unknown` and `test_intersect_adjacent_returns_unknown` both assert `== UnknownSpan` (was `is None`).
- **Design doc**: 7 locations updated — Protocol snippet, Python `intersect` body, API surface table, utility method signature, prose description, Rust code snippet, and both test plan sections (Python #20, Rust #20). All changed from `None`/`Option` to `UnknownSpan`/`Span(-1,-1)`.
- All 94 tests pass.

Assessment: Comprehensive fix across all layers. Accept.

### note-3 — Fixed (remove struct Ping)

Claim: Remove `struct Ping` from Rust; it was scaffolding.
Disposition: Fixed.

Evidence (commit 0344ce6):
- `src/lib.rs`: `struct Ping`, its `#[pymethods]` impl block, and `m.add_class::<Ping>()?` all removed. Module now registers only `Span`, `SourceText`, `UnknownSpan`.
- `tests/test_native.py`: `test_ping` replaced with `test_module_importable` asserting the three real exports (`Span`, `UnknownSpan`, `SourceText`).
- All 94 tests pass.

Assessment: Clean removal. Accept.

## Approved

3 findings: 3 Fixed verified.

---

## Verdict: APPROVED
