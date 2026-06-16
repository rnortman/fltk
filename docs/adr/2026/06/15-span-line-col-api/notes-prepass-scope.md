# Scope prepass notes — span-line-col-api

Reviewed: commits 8cd6232..934a846

## scope-1: TODO.md missing required entries for two deferred items

**File:line:** `TODO.md` (missing — design §7 requires entries)
**Expected:** Design §7 explicitly mandates two TODO slugs with paired `TODO.md` entries per CLAUDE.md "TODO System": `linecol-cache-consolidate` (two caches over the same immutable text; consolidation is adjacent but out of scope) and `py-span-linecol-cache` (Python `Span.line_col()` recomputes O(N) per call; caching on `SourceText` deferred). Code comments with `TODO(linecol-cache-consolidate)` appear in `crates/fltk-cst-core/src/span.rs:53`, `crates/fltk-parser-core/src/terminalsrc.rs:167,178`, and `TODO(py-span-linecol-cache)` in `fltk/fegen/pyrt/terminalsrc.py:133` — the code half exists.
**Actual:** `TODO.md` has no entries for either slug. The file was not modified in this diff at all.
**Consequence:** The CLAUDE.md TODO system requires both a code comment AND a `TODO.md` entry; the burndown ground-truth audit fails with no `TODO.md` entry to join against. The code comments become orphaned by convention, making them harder to track and easier to drop.
**Suggested fix:** Add two entries to `TODO.md` under `## \`linecol-cache-consolidate\`` and `## \`py-span-linecol-cache\`` describing the concrete follow-up and naming the code location, exactly as §7 specifies.

## scope-2: `TerminalSource.pos_to_line_col` sentinel changed — design §2.5 said "unchanged"

**File:line:** `fltk/fegen/pyrt/terminalsrc.py:281-283`; `crates/fltk-parser-core/src/terminalsrc.rs:397-401` (test golden value diff)
**Expected:** Design §2.5 (final paragraph): "The legacy `TerminalSource.pos_to_line_col` Python path keeps its current sourceless behavior unchanged." Design §2.12: "The change is additive: … The legacy `TerminalSource.pos_to_line_col` behavior is left untouched." The old sentinel for the final line was `len(terminals) - 1` (Python) / `len - 1` (Rust), causing `line_span.end = len - 1` (last char excluded).
**Actual:** Both Python and Rust `pos_to_line_col` now use sentinel `len` (exclusive-past-end) for the final line without a trailing newline, so `line_span.end = len` (full last line included). The Rust `terminalsrc.rs` test golden value changed from `lc.line_span.end() == 10` to `== 11` for `"hello\nworld"`. Python `test_span.py:392-395` comments acknowledge the divergence but describe the situation incorrectly (says "legacy uses `len-1`" when the current code uses `len`). The implementation log (increment 1) documents this as required for Python/Rust parity in `test_rust_parser_parity_fixture.py`.
**Consequence:** Any out-of-tree consumer that called `TerminalSource.pos_to_line_col(pos).line_span.text()` on text without a trailing newline and expected the last character to be absent from the line span now gets it included. The change is generally a bug fix (the old behavior was wrong — it truncated the last char), but it is an undocumented breaking change relative to what the design promised. The implementation log captures the justification; the design doc does not.
**Suggested fix:** Accept as a justified fix (the old sentinel was incorrect; `len-1` made the last character disappear from the caret line). Update the design doc's §2.5 "unchanged" wording to say "unchanged *except* the sentinel is corrected from `len-1` to `len` for parity with `Span.line_col()` and full-line text fidelity." Update the stale comment in `test_span.py:392-393` from "legacy uses `len-1`" to "both implementations now use `len` (inclusive last char)."

## scope-3: `resolve_line_col` docstring describes old `len-1` sentinel

**File:line:** `crates/fltk-cst-core/src/span.rs:209`
**Expected:** The docstring should accurately describe the sentinel the function actually pushes.
**Actual:** Line 209 says "It stores codepoint indices of `\n` characters plus a final sentinel of `len - 1`" but the code at lines 233-235 pushes `len` (not `len-1`) for non-empty text. The inline code comment at lines 225-229 is correct; only the outer doc comment is stale.
**Consequence:** A reader of the public function doc would expect `line_span.end == len - 1` for the final line but gets `len`. Minor documentation hazard for future callers of `resolve_line_col`.
**Suggested fix:** Change line 209: "final sentinel of `len`" (or "exclusive end of the last line, equal to `len` for non-empty text or `-1` for empty text").

No findings were identified for:
- Protocol methods `line_col` / `line_col_or_raise` / `filename` on `SpanProtocol` (§2.1–2.3) — present.
- `LineColPos` move to `fltk-cst-core`, single `resolve_line_col`, re-export from `fltk-parser-core` (§2.5) — present.
- `LineColPos` pyclass, 4-step registration in `fltk-native` (§2.6.1) — all four steps present.
- pyo3 wrappers `py_line_col`, `line_col_or_raise`, `py_filename` (§2.6.4) — present.
- `OnceLock<Vec<i64>> line_ends` on `SourceInner` (§2.6.3) — present.
- `SourceInner.filename` and threading (§2.8 Rust) — present.
- `TerminalSource::new(text, filename)` — present.
- Rust parser generator changes `gsm2parser_rs.py` (§2.8 Rust parser path) — present; `crates/fegen-rust/src/parser.rs` regenerated.
- Python `_source_filename` on `Span`, `with_source` threading (§2.8 Python) — present.
- Python parser generator `gsm2parser.py` threading `filename` (§2.8 Python) — present; all generated parsers regenerated.
- `pyi` stub additions (`LineColPos`, `Span.line_col/line_col_or_raise/filename`, `SourceText.__init__` with `filename`) (§2.7) — present.
- `error_formatter.py` `format_source_line` (§2.10) — present with correct signature, output format, filename precedence, `line_col_or_raise` usage.
- Protocol annotation `terminalsrc.LineColPos | None` (§2.11) — present.
- Cross-backend equivalence tests `TestLineColCrossBackend` / `TestFilenameCrossBackend` including real-parse parser-filename path (§4.1) — present.
- Protocol conformance and `TestProtocolHasNoStartEnd` extended (§4.2) — present.
- Per-backend tests in `test_span.py`, `test_rust_span.py`, Rust unit tests in `fltk-cst-core/src/lib.rs` (§4.3) — present including deliberate-divergence pins.
- Drift anchor `TestDriftAnchor` (§4.4) — present.
- Error formatter tests `test_error_formatter.py` (§4.5) — present (shape, precedence, multibyte, cross-backend, sentinel-raises).
- Both parser backends regenerated (§4.6) — present.
- Open questions §6 resolved by defaults: start-only, `col=-1` preserved, single annotation, caret-formatter only, both forms shipped — all confirmed.
