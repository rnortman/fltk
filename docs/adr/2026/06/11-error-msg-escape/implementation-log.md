## Increment 1 — escape_control_chars + format_error_message, both backends (commit e715573)

- `fltk/fegen/pyrt/errors.py`: added `escape_control_chars` (public) with named constants for magic values; updated `format_error_message` to split line at `col`, escape prefix + suffix separately, compute pad from `len(escaped_prefix)`.
- `crates/fltk-parser-core/src/errors.rs`: added `pub fn escape_control_chars`; replaced raw `line_text` embed and `spaces = " ".repeat(col.max(0))` with escaped-prefix/suffix construction and `pad = escaped_prefix.chars().count()`; replaced security-note + TODO doc comment with escaping/parity doc.
- `crates/fltk-parser-core/src/lib.rs`: re-exported `escape_control_chars` alongside `format_error_message`.
- `TODO.md`: removed `error-msg-escape` entry (lines 35–44).
- `tests/test_pyrt_errors.py` (new): 14 tests — `escape_control_chars` table, edge cases, `format_error_message` golden (controls in line, caret alignment, no-raw-controls assertion, col==-1, empty input, ASCII-clean unchanged).
- `crates/fltk-parser-core/src/errors.rs` `#[cfg(test)]`: 4 new tests — `escape_control_chars_table`, `escape_control_chars_empty`, `format_error_message_with_controls_in_line`, `format_error_message_caret_alignment_with_escaped_prefix`, `format_error_message_no_raw_controls_in_output`.
- `tests/test_rust_parser_parity_fixture.py`: 2 new FAIL corpus entries with controls in failing line (exercises cross-backend byte-equal header check).
- All 54 Rust unit tests, 1350 Python tests, `make check` pass.
