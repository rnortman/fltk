# Implementation log: error-msg-bidi-escape

## Increment 5 — Python backend, parity corpus, format_error_message tests, CST-bridge test, TODO cleanup (commit 1a7e1f5)

- `fltk/fegen/pyrt/errors.py`: added module-level constants (`_ALM`, `_ZW_START/_END`, `_LS_PS_START/_END`, `_WJ`, `_ISO_START/_END`, `_BOM`) and `_needs_escape(cp)` predicate sharing logic between fast-path and loop; extended `escape_control_chars` to emit `\uXXXX` for cp > `_C1_END`; removed `TODO(error-msg-bidi-escape)` comment; updated docstring with full spec and cross-pin reference. PLR2004 satisfied via constants.
- `tests/test_pyrt_errors.py`: updated cross-pin header to name `crates/fltk-cst-core/src/escape.rs`. Added 9 new escape tests mirroring Rust (bidi-embedding-override, bidi-isolates, bidi-implicit-marks, line-paragraph-separators, zero-width-chars, passthrough-boundary-chars, mixed-xhh-and-uxxxx). Added 4 new `format_error_message` tests: extended-set sweep, bidi golden, bidi caret alignment. All invisible/ambiguous chars replaced with `\uXXXX` Python escapes to satisfy PLE2502/RUF001.
- `tests/test_rust_parser_parity_fixture.py`: added 3 new FAIL corpus entries (`("num", "‮123")`, `("name", "⁦​abc")`, `("stmt", "x = @")`); invisible chars replaced with Python `\uXXXX` escapes.
- `crates/fltk-parser-core/src/errors.rs`: added 3 new `format_error_message` tests: `no_raw_extended_set_in_output`, `bidi_golden`, `bidi_caret_alignment`.
- `tests/test_rust_span.py`: added `test_with_source_unchecked_escape_in_type_name` to `TestAbiMarkerClassattr` — passes `type("Fake‮Src\t\x85", ...)` and asserts `TypeError` text contains `\\u202e`, `\\x85` (single codepoint, not UTF-8 bytes), raw TAB, no raw U+202E/U+0085. Type name uses `‮` Python escape to satisfy PLE2502.
- `TODO.md`: removed `error-msg-bidi-escape` entry.
- `make check` clean (lint, format-check, typecheck, test, cargo-* all pass).

## Increment 4 — `cross_cdylib.rs`: delete `escape_control_chars_for_msg`; use canonical (commit a2d5f98)

- `crates/fltk-cst-core/src/cross_cdylib.rs`: added `use crate::{escape::escape_control_chars, ...}`. Deleted 16-line `escape_control_chars_for_msg` (divergent: escaped TAB, per-UTF-8-byte C1, wrong comment). Updated `py_any_type_name` and `py_type_obj_name` to call `escape_control_chars` directly. Replaced 4 inline `escape_control_chars_for_msg` calls in `check_abi_pair` with `escape_control_chars`. Behavioral change (deliberate, called out in design): TAB now passes through; C1 now `\xHH`; new bidi/zero-width set escaped.
- All 38 `fltk-cst-core --no-default-features` tests pass; `cargo build -p fltk-cst-core --features python` clean.

## Increment 3 — Python backend extension + cross-pin test updates (not a separate commit; merged into Increment 5)

(See Increment 5 entry above — Python work shipped together with tests in one commit.)

## Increment 2 — replace `errors.rs` local definition with re-export from `fltk_cst_core::escape` (commit 582c7b0)

- `crates/fltk-parser-core/src/errors.rs:82-90`: removed local 20-line `escape_control_chars` (with its obsolete `TODO(error-msg-bidi-escape)` comment and old-range-only `needs_escape`); replaced with `pub use fltk_cst_core::escape::escape_control_chars;` plus a short doc comment pointing at the escape.rs spec.
- `crates/fltk-parser-core/src/errors.rs` `format_error_message` doc: updated to mention `\uXXXX` and reference `escape.rs`.
- `pub use errors::escape_control_chars` in `lib.rs` unchanged — chain `lib.rs → errors.rs → fltk_cst_core::escape` preserves the public paths `fltk_parser_core::escape_control_chars` and `fltk_parser_core::errors::escape_control_chars`.
- All 55 `fltk-parser-core` tests pass; all 38 `fltk-cst-core --no-default-features` tests pass; `make check` clean.

## Increment 1 — new `crates/fltk-cst-core/src/escape.rs` with extended predicate + unit tests (commit 9a7d525)

- `crates/fltk-cst-core/src/escape.rs`: new file. `needs_escape(cp)` predicate covers existing C0/DEL/C1 ranges plus U+061C (ALM), U+200B–U+200F (ZWSP/ZWNJ/ZWJ/LRM/RLM), U+2028–U+202E (LS/PS/LRE/RLE/PDF/LRO/RLO), U+2060 (WJ), U+2066–U+2069 (LRI/RLI/FSI/PDI), U+FEFF. `escape_control_chars`: fast-path scan unchanged; cp ≤ 0x9F → `\xHH`, cp > 0xFF → `\uXXXX`. Module doc states full spec and cross-pin to Python + test files.
- `crates/fltk-cst-core/src/lib.rs:4`: `pub mod escape;` added.
- `crates/fltk-cst-core/src/escape.rs` `#[cfg(test)]`: 9 test functions — existing table + empty rows (moved verbatim from design's intent; literals unchanged), plus bidi-embedding-override, bidi-isolates, bidi-implicit-marks, line-paragraph-separators, zero-width-chars, boundary-passthroughs, mixed-xhh-and-uxxxx. All 38 cst-core tests pass; all 55+13 parser-core tests unaffected.
- Note: `errors.rs` local definition not yet replaced; that is the next increment (design §Part (b): re-export from cst-core).
