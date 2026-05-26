## Dispositions — Ship-Gate User Notes

note-1:
- Disposition: Fixed
- Action: Added method-level docstrings to all public methods of `SpanProtocol` (`span_protocol.py:20-51`), all public methods of the pure-Python `Span` (`terminalsrc.py:16-83`), and Rust doc comments (`///`) to `SourceInner`, `SourceText`, `SourceText::new`, `Span` struct, and every `#[pymethods]` item in `src/span.rs`. All 453 tests pass; lint and pyright clean.
- Severity assessment: Poor hygiene only — no runtime or correctness impact, but discoverability and maintainability suffer without docstrings on a public API intended to be used by two backends.

note-2:
- Disposition: Fixed
- Action: `intersect()` return type changed from `Span | None` to `Span` (returning `Span(-1, -1)` / `UnknownSpan` on empty intersection) in: `SpanProtocol.intersect` (`span_protocol.py:50-55`), `Span.intersect` pure-Python (`terminalsrc.py:75-85`), `Span::intersect` Rust (`src/span.rs:233-252`). Tests updated: `test_span.py` renamed `test_intersect_adjacent_returns_none` → `test_intersect_adjacent_returns_unknown` and updated assertion; `test_rust_span.py` renamed two disjoint tests and updated assertions to compare with `UnknownSpan`. Design doc updated at all `intersect` signature/prose/code-snippet locations. All 453 tests pass.
- Severity assessment: API contract change — callers checking `is None` would silently get `False` on a sentinel span instead of the intended "no overlap" branch. Returning `UnknownSpan` is consistent with the sentinel pattern already established in the codebase and avoids callers needing to handle two different absence representations.

note-3:
- Disposition: Fixed
- Action: Removed `struct Ping`, its `#[pymethods]` impl block, and `m.add_class::<Ping>()?` from `src/lib.rs`. Replaced the placeholder test in `tests/test_native.py::test_ping` with `test_module_importable` that verifies the three real exports (`Span`, `UnknownSpan`, `SourceText`) are present. All 453 tests pass.
- Severity assessment: Dead code only — `Ping` was scaffolding so the module was non-empty; `Span` and `SourceText` now fulfil that role. No callers outside the removed test.
