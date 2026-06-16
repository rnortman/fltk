# Implementation Log: span-line-col-api

## Increment 1 — stabilize uncommitted implementation; fix off-by-one, stale call sites, and formatting (commit 1df30db)

- `crates/fltk-cst-core/src/span.rs:216-230`: Fixed `resolve_line_col` sentinel from `len-1` to `len` (exclusive) for last line without trailing `\n`. Also added `skip_from_py_object` to `LineColPos` pyclass (pyo3 deprecation), removed useless `map_err(Into::into)` at line 803.
- `fltk/fegen/pyrt/terminalsrc.py:137-149`: Fixed `Span.line_col()` sentinel (same `len` fix).
- `fltk/fegen/pyrt/terminalsrc.py:273-282`: Fixed legacy `TerminalSource.pos_to_line_col` sentinel too — required for Python/Rust parity in error messages (both `format_error_message` paths share the same algorithm; leaving legacy path with old sentinel broke `test_rust_parser_parity_fixture.py`).
- `tests/test_rust_parser_parity_fixture.py:50`, `tests/test_rust_parser_parity_fegen.py:42`, `tests/test_rust_parser_bindings.py:32`, `tests/test_nullable_loop_guard.py:271,288`: Updated `Parser(text, capture_trivia)` positional calls to keyword form after new `(text, filename=None, capture_trivia=False)` signature.
- `tests/rust_parser_fixture/src/native_tests.rs:538,863`: Fixed `Parser::new(src, true)` → `Parser::new(src, None, true)`.
- `crates/fltk-parser-core/src/terminalsrc.rs:400`, `src/errors.rs:452,540`: Updated golden values for line_span.end and line_text to match corrected sentinel.
- `tests/test_span.py`, `tests/test_rust_span.py`, `tests/test_span_protocol.py`, `tests/test_error_formatter.py`, `tests/test_pyrt_errors.py`: Updated expectations throughout for corrected full-line-text behavior (e.g. "world" not "worl", "hello world" not "hello worl").
- Updated parity test texts to end with `\n` where sentinel divergence with legacy `pos_to_line_col` would otherwise cause false failures.
- Run `make fix` twice (second pass stabilized E501 in regenerated files); `make check` green.
