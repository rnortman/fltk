Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Commit reviewed: 65279b7

test-1
File: tests/test_pyrt_errors.py:192
Python `test_format_error_message_no_raw_extended_set_in_output` input string is `"\x00\x1b\r\x7f؜​‎ ‮⁠⁦﻿abc\n"`. The comment on the same line reads "C1(U+009B)" but U+009B is absent — confirmed by inspecting codepoints. The Rust twin at `errors.rs:416` includes `\u{009b}`. The Python predicate at lines 198–208 correctly includes `0x80 <= cp <= 0x9F`, but since no C1 char ever enters the message, the predicate branch for C1 is never triggered. A C1 escape bug would not be caught by this test.
Consequence: regression in C1 escaping (e.g., `escape_control_chars` stops escaping U+009B) passes the Python sweep test silently; only the Rust test would catch it.
Fix: insert `` into the Python input string, e.g. `"\x00\x1b\r\x7f؜​‎ ‮⁠⁦﻿abc\n"`.

test-2
File: crates/fltk-cst-core/src/escape.rs:296–317, tests/test_pyrt_errors.py:630–639
The upper boundary of the LRI/RLI/FSI/PDI range (U+2066–U+2069) is not tested as a passthrough. `passthrough_boundary_chars` (both backends) tests U+2065 (below the range) but has no assertion for U+206A (one above U+2069). All other range boundaries are fenced on both sides: U+200A/U+2010 bracket the ZW range, U+2027/U+202F bracket the LS/embedding range.
Consequence: an off-by-one that extends the range to U+206A (or beyond) would not be caught.
Fix: add `assert_eq!(escape_control_chars("\u{206a}"), "\u{206a}");` in `passthrough_boundary_chars` (Rust) and `assert escape_control_chars("⁪") == "⁪"` in `test_escape_passthrough_boundary_chars` (Python).

test-3
File: tests/test_pyrt_errors.py:196–208
The Python no-raw-extended sweep hardcodes the escape-set predicate as a block of range conditions, duplicating what `_needs_escape` already implements. The Rust twin at `errors.rs:400–413` uses `escape_control_chars` itself as the oracle (clever: if `escape_control_chars(single_char) != single_char`, the char is in the escape set), so it cannot drift from the actual implementation. The Python hardcoded predicate CAN drift — e.g., if a new range is added to `_needs_escape` but the test predicate is not updated, the test still passes while the new chars would escape correctly (less severe) but the sweep would fail to verify they're absent from output.
Consequence: predicate drift means the sweep silently stops verifying newly-added escape classes. Less severe than test-1 (the unit tests for individual classes would still catch escaping failures), but the sweep's all-classes property is the cross-check value.
Fix: rewrite the Python sweep predicate to use `escape_control_chars` as the oracle — `from fltk.fegen.pyrt.errors import _needs_escape` and replace the hardcoded block with `assert not _needs_escape(cp) or cp in (0x09, 0x0A)`.
