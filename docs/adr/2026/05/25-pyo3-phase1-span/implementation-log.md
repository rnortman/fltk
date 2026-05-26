## Increment 1 — Pure-Python Span update: add source-bearing API (commit bf81841)

- `fltk/fegen/pyrt/terminalsrc.py:7-68`: Added `_source: str | None` field (`compare=False, hash=False, repr=False`) to `Span` dataclass; added `text()`, `text_or_raise()`, `has_source()`, `len()`, `is_empty()`, `merge()`, `intersect()`, and `with_source()` classmethod. Added `field` to dataclass imports.
- `tests/test_span.py`: 33 new tests covering all pure-Python backend cases from design test plan (plus an extra `test_empty_span_text`). All pass.
- All 360 pre-existing tests pass without modification.

## Increment 2 — Rust Span backend: `src/span.rs`, `src/lib.rs`, `tests/test_rust_span.py` (commit 9e307eb)

- `src/span.rs`: New file. `SourceInner` (private heap struct), `SourceText` (`#[pyclass(frozen)]`), `Span` (`#[pyclass(frozen, eq, hash)]`). Manual `PartialEq`/`Hash` on `(start, end)` only. Methods: `new`, `with_source`, `text`, `text_or_raise`, `has_source`, `len`, `is_empty`, `merge`, `intersect`, `__repr__`. No `#[pyo3(get)]` on `start`/`end` — Python cannot read raw indices.
- `src/lib.rs`: Added `mod span;`, registered `Span`, `SourceText`, `UnknownSpan` constant (`Span{-1,-1,None}`). Retained `Ping` struct to keep `tests/test_native.py::test_ping` passing (Phase 0 test, cannot modify).
- `fltk/fegen/pyrt/terminalsrc.py:28,44`: Fixed EM101/EM102 lint violations (exception string literals) introduced in increment 1; moved to variables before raise.
- `tests/test_rust_span.py`: 45 new tests. All pass. `pytest.importorskip` gates on Rust extension availability.
- Deviation: `source` field on `Span` made `pub(crate)` (design showed private) to allow struct literal construction in `lib.rs` for `UnknownSpan`. No behavioral impact.
- Old `fltk/_native.cpython-310-x86_64-linux-gnu.so` (Phase 0 abi-specific build) removed — it shadowed the new abi3 build and caused `ImportError`. The abi3 build (`_native.abi3.so`) is the correct artifact going forward.
- All 438 tests pass (438 = 360 pre-existing + 33 py-span + 45 rust-span).

## Increment 3 — `span_protocol.py`, `span.py` backend selector, `tests/test_span_protocol.py` (commit f45dcd9)

- `fltk/fegen/pyrt/span_protocol.py`: New file. `@runtime_checkable SpanProtocol` with `text`, `text_or_raise`, `has_source`, `len`, `is_empty`, `merge`, `intersect`. `AnySpan = _pymod.Span | _RustSpan` (falls back to `_pymod.Span` if Rust unavailable).
- `fltk/fegen/pyrt/span.py`: New file. Backend selector: imports `Span`/`UnknownSpan` from `terminalsrc` by default, then tries to override from `fltk._native`. `SourceText = None` default when Rust unavailable. Deviation: inverted try/except order (default to Python, then try Rust override) to work around pyright `Final` reassignment error — functionally identical to design.
- `tests/test_span_protocol.py`: 10 new tests. All pass. Rust-conditional tests use `pytest.mark.skipif` with module-level availability check (avoids PLC0415 lint).
- All 448 tests pass (448 = 360 pre-existing + 33 py-span + 45 rust-span + 10 protocol).
