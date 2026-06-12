# Deep correctness review — error-msg-bidi-escape

Reviewed: 108ee61..65279b7 (HEAD = 65279b7). Working tree has uncommitted edits to
`crates/fltk-parser-core/src/errors.rs` and `tests/test_pyrt_errors.py` on top of HEAD;
out of scope, reviewed committed state only.

Verified clean (no findings):
- `needs_escape`/`_needs_escape` predicates byte-identical across backends (same 9 ranges,
  same TAB carve-out); fast path and loop share the predicate in both.
- Representation split identical: `cp <= 0x9F → \xHH`, else `\uXXXX` (Rust
  `crates/fltk-cst-core/src/escape.rs:185-204`, Python `fltk/fegen/pyrt/errors.py`).
  Design phrases the split as "cp > 0xFF → \uXXXX"; no set member lies in 0xA0–0xFF, so
  the `> 0x9F` implementation is equivalent over the set.
- Caret pad: Python `len(escaped_prefix)`, Rust `escaped_prefix.chars().count()` — escapes
  are pure ASCII, so counts agree; 6 columns per `\uXXXX` confirmed by both backends' tests.
- Position semantics: both backends codepoint-indexed (`terminalsrc.rs` cp_to_byte table;
  Python str indexing); `fail_literal(1, ...)` after a 3-byte U+202E is correct in both.
- `cross_cdylib.rs`: all six former `escape_control_chars_for_msg` call sites now call the
  canonical function; the TAB/C1/extended-set behavioral change is deliberate and pinned by
  `tests/test_rust_span.py::test_with_source_unchecked_escape_in_type_name`.
- Re-export chain `fltk_parser_core::lib.rs → errors.rs → fltk_cst_core::escape` intact;
  `escape.rs` ungated, `fltk-parser-core` consumes cst-core with `default-features = false`.
- `cargo test -p fltk-cst-core --no-default-features`: 38/38 pass (escape.rs unmodified in tree).

## correctness-1

- File: `tests/test_pyrt_errors.py:25-27` (also `:192`)
- What: Commit 1a7e1f5 replaced the readable source escapes `"\u009b"`, `"\u0080"`,
  `"\u009f"` in `test_escape_control_chars_c1` with raw, invisible C1 bytes (0xC2 0x9B etc.).
  The extended-set test input at line 192 likewise contains a raw invisible U+009B between
  `\x7f` and `\u061c`. Base 108ee61 had readable escapes at 25-27.
- Why: The rendered source reads `assert escape_control_chars("") == "\\x9b"` — apparently
  asserting that the empty string escapes to `\x9b`. The actual content is an invisible C1
  char, so the assertion is functionally unchanged, but the code does not do what it appears
  to do. This also directly contradicts the in-range record: implementation-log Increment 5
  claims "All invisible/ambiguous chars replaced with `\uXXXX` Python escapes", and commit
  40fbd00 / disposition slop-1 claim raw C1 bytes were removed for diff readability — the
  opposite was committed at these lines. (ruff PLE2502 flags only bidi chars, so raw C1
  passes lint silently.)
- Consequence: The cross-language pin convention ("duplicated literal strings" — design
  §Context) is unverifiable by inspection at exactly the C1 rows: the Rust twin
  (`escape.rs` test `escape_control_chars_table`) uses visible `\u{009b}` literals while the
  Python side is invisible; a reviewer diffing either side cannot confirm the literals match.
  Any future edit that drops or duplicates the invisible byte produces a confusing failure
  (or, at line 192, a silent input change — see correctness-2 for a realized instance).
- Fix: Restore `"\u009b"`, `"\u0080"`, `"\u009f"` escapes at lines 25-27 and replace the raw
  U+009B at line 192 with `\u009b`.

## correctness-2

- File: `tests/test_pyrt_errors.py:175-188` (`test_format_error_message_no_raw_controls_in_output`)
- What: Commit 1a7e1f5 silently removed the raw U+009B from the test input. Base:
  `_ts("\x00\x01\x1b\r\x7f<U+009B>abc\n")`; HEAD: `_ts("\x00\x01\x1b\r\x7fabc\n")`. Because
  the removed char is invisible, the diff hunk renders as an unchanged-looking line; the
  change is not mentioned in the implementation log.
- Why: The test's comment still says "Assert no raw C0 (except \t/\n), no U+007F, no
  U+0080-U+009F in output", and the assertion still checks `0x80 <= cp <= 0x9F`, but the
  input now contains no C1 character — the C1 clause is vacuous. The Rust twin
  (`errors.rs:392-409` at HEAD, `format_error_message_no_raw_controls_in_output`) retains
  `\u{009b}` in its input, so the cross-pinned test pair now exercises different inputs.
- Consequence: A Python-only regression that leaks raw C1 through the `format_error_message`
  path would no longer be caught by this test (coverage survives only via the extended-set
  test at line 192, whose C1 char is itself an invisible raw byte — fragile per
  correctness-1). The test asserts less than it appears and claims to.
- Fix: Restore U+009B to the input as a visible `\u009b` escape, matching the Rust twin.

No other findings. No logic bugs in shipped (non-test) code.
