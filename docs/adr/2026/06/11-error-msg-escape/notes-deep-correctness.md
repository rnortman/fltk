# Deep correctness review — error-msg-escape

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Reviewed: ef8288c..8da7924. Files: `crates/fltk-parser-core/src/errors.rs`, `crates/fltk-parser-core/src/lib.rs`, `fltk/fegen/pyrt/errors.py`, `tests/test_pyrt_errors.py`, `tests/test_rust_parser_parity_fixture.py`.

## Verified clean

- **Escape condition parity.** Rust `(cp <= 0x1F && cp != 0x09) || cp == 0x7F || (0x80..=0x9F).contains(&cp)` ≡ Python `(cp <= 0x1F and cp != 0x09) or cp == 0x7F or (0x80 <= cp <= 0x9F)`. Representation `\xHH` lowercase two-digit: Rust `format!("\\x{:02x}")` ≡ Python `f"\\x{cp:02x}"`; all escaped codepoints ≤ 0x9F so two digits always suffice.
- **Prefix/suffix split.** Python slicing clamps implicitly; Rust clamps via `split.min(chars.len())`. The clamp is never lossy: from `pos_to_line_col` (both backends), `col = pos - line_start` and `line_span` ends at `line_ends[idx]`, so `col ≤ len(line_text)` in every case (sentinel last line: pos ≤ len-1 after the `pos == len` decrement, line_text length = (len-1) - line_start; newline-terminated line: max pos is the `\n` index, col = len(line_text)). Therefore prefix/suffix and pad are identical cross-backend, and for control-free lines pad == col == old behavior — the "ASCII-clean output unchanged" claim holds.
- **Pad units.** Python `len(escaped_prefix)` and Rust `escaped_prefix.chars().count()` both count codepoints; escape sequences are pure ASCII; multibyte passthrough chars count 1 on both sides.
- **`col == -1`.** `max(col, 0)` / `col.max(0)` → empty prefix, pad 0 — matches old `' ' * -1 == ''` / `col.max(0)` repeat. Verified against `pos_to_line_col(-1)` on both backends (col = -1, line_span valid; empty-input `Span(0, -1)` → `""` via Python slice `[0:-1]` on `""` and Rust `text().unwrap_or_default()`).
- **`\n` in escape set but unreachable at call site** — `line_span` excludes the terminating newline on both backends; helper stays total.
- **Parity comparator interaction.** `_parse_error_message` splits with `splitlines()`; escaped output contains no raw C0/C1, so no spurious line splits (raw `\x0b`/`\x0c`/`\x85`/U+2028 would have split before this change — escaping removes the hazard, not adds one). Header byte-equality holds given the pinned escape parity above.
- **Parity corpus entries.** Both new entries are FAIL-expected; even if the traced failure position in the `"x\r=\r@"` comment were off, the parity assertion compares both backends' actual output, so the test cannot pass on divergent behavior.
- **Unit tests' expected values** re-derived by hand against `pos_to_line_col` (sentinel quirk included): `"hello world"` golden (`line_span=[0,10)`, pad 5), `"\x1b[31mabc"` (col 0, line drops trailing `c`), `"ab\x1bcd\n"` (line_ends=[5], pad 6) — all asserted values correct.

## Findings

### correctness-1

- **File:line:** `crates/fltk-parser-core/src/errors.rs:374` (test `format_error_message_caret_alignment_with_escaped_prefix`)
- **What:** Comment claims `Use "ab\x1bcd\n" — line_ends=[7], line_span=[0,7)="ab\x1bcd"`. The input is 6 codepoints (`a b ESC c d \n`); the `\n` is at codepoint index 5, so `line_ends=[5]` and `line_span=[0,5)`.
- **Why:** `pos_to_line_col` collects codepoint indices of `\n` (`terminalsrc.rs:191-206`); index 7 does not exist in a 6-char string. The string `"ab\x1bcd"` is 5 chars, not 7 — `[0,7)` cannot equal it.
- **Consequence:** None at runtime — the test's assertions (`lines[1] == "ab\\x1bcd"`, pad 6) are correct for the actual `line_span=[0,5)`. But the comment documents a derivation that is arithmetically impossible, and a maintainer extending the test from it (e.g. choosing a failure position relative to the claimed span end) would compute wrong expected values.
- **Fix:** Correct the comment to `line_ends=[5], line_span=[0,5)="ab\x1bcd"`. The mirrored Python test's comment (`tests/test_pyrt_errors.py:71-73`) does not make the erroneous claim and needs no change.
