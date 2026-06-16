# Test Review Notes — span-line-col-api

Commit reviewed: b6c0aac (branch `span-line-col-api`, base `8cd6232`)

Files assessed:
- `tests/test_span.py`
- `tests/test_rust_span.py`
- `tests/test_span_protocol.py`
- `tests/test_error_formatter.py`
- `crates/fltk-cst-core/src/lib.rs` (`resolve_line_col_tests`)
- `crates/fltk-parser-core/src/terminalsrc.rs` (`pos_to_line_col` wrapper tests)

---

## test-1

**File:** `tests/test_span_protocol.py`, `TestLineColCrossBackend._SOURCE` (line 141) and `test_line_span_text_works` (lines 222–245)

**What's wrong:** The cross-backend equivalence tests for `line_span.end` only ever exercise source texts that end with `\n`. `_SOURCE = "hello\nworld\ncafé\n"` (trailing newline), and `test_line_span_text_works` also uses the trailing-newline variant (the docstring at lines 224–227 explicitly notes "The test source ends with `\n`"). This is the exact class of bug called out in the task brief: both backends could agree identically while both being wrong on the sentinel for the final line without a trailing newline. The original off-by-one (`sentinel = len-1` instead of `len`) would have passed every cross-backend test here because both backends would have returned the wrong value together. The fix landed, but there is no cross-backend sentinel test that would catch a future regression in either direction.

**Consequence:** A regression that changes the sentinel back to `len-1` on either backend for the no-trailing-newline case would not be caught by the cross-backend equivalence tests. The only tests that pin the `sentinel=len` contract for no-trailing-newline are single-backend: `test_line_col_line_span_is_source_bearing` (Python, line 311) and `TestLineCol.test_line_span_text_works` (Rust, line 1209). Those would catch a within-backend regression, but not an asymmetric one, and they are not the equivalence tests.

**Fix:** Add a `TestLineColCrossBackend` case that uses a source without a trailing newline, e.g. `"hello\nworld"`, queries `line_col()` on the last line (position 6), and asserts `py_lc.line_span.end == rs_lc.line_span.end == 11` (not 10). This directly pins the sentinel value and catches the original bug class if it returns.

---

## test-2

**File:** `tests/test_span.py`, `tests/test_rust_span.py`, `tests/test_span_protocol.py`

**What's wrong:** Empty source (`""`) is not tested at all for `line_col()` at the Python or Rust pyo3 level. The design (§3) calls out `SourceText("")` with `start=0` as returning `LineColPos(line=0, col=-1, line_span=Span(0,-1))` — the EOF-clamp fires (`start==len==0` → `pos=-1`), and the sentinel pushed for empty text is `-1`. This is a documented non-trivial corner. The Rust pure-Rust unit test `resolve_empty_input` in `lib.rs:119–127` covers `resolve_line_col("", -1, &cache)` directly, and the Rust `pos_to_line_col_empty_input` test in `terminalsrc.rs:453–459` covers the wrapper. But no Python or pyo3 test calls `Span.with_source(0, 0, SourceText("")).line_col()` and asserts the `col=-1` result.

**Consequence:** An implementation change to the Python span's `line_col()` that incorrectly returns `None` instead of `LineColPos(0, -1, ...)` for empty source (or vice versa) would not be caught by the Python tests. The cross-backend equivalence of empty-source behavior is similarly unverified.

**Fix:** Add to `test_span.py`:
```python
def test_line_col_empty_source():
    """Empty source: start=0==len, EOF clamp fires, col=-1 (inherited algorithm)."""
    st = SourceText("")
    span = Span.with_source(0, 0, st)
    lc = span.line_col()
    assert lc is not None
    assert lc.line == 0
    assert lc.col == -1
```
And a matching case in `test_rust_span.py::TestLineCol` plus a cross-backend case in `TestLineColCrossBackend`.

---

## test-3

**File:** `tests/test_span_protocol.py`, `TestLineColCrossBackend`

**What's wrong:** The cross-backend test set has no zero-width span `Span(p, p)` `line_col()` case. The design (§2.1, §3) explicitly lists "Zero-width span `Span(p,p)` reports the line/col of `p`" as a supported case. Per-backend tests cover it (`test_is_empty_zero_width` in each file tests `is_empty`, but that is unrelated to `line_col()`), but the cross-backend equivalence tests never call `line_col()` on a zero-width span.

**Consequence:** A backend that returns `None` for a zero-width span (treating `start == end` as empty/sentinel rather than a valid position) would not be caught by the cross-backend suite.

**Fix:** Add to `TestLineColCrossBackend`:
```python
def test_zero_width_span(self):
    """Zero-width span Span(p,p): line_col() returns position p, not None."""
    py = self._make_py_span(3, 3)
    rs = self._make_rs_span(3, 3)
    self._assert_line_col_equal(py, rs)
    py_lc = py.line_col()
    assert py_lc is not None
    assert py_lc.line == 0
    assert py_lc.col == 3  # "hello\nworld\ncafé\n": col 3 on line 0
```

---

## test-4

**File:** `tests/test_span_protocol.py`, `TestDriftAnchor.test_py_span_line_col_agrees_with_terminalsrc_pos_to_line_col` (lines 356–378)

**What's wrong:** The drift-anchor test uses positions `[0, 3, 6, 10, 12, 14]` over `"hello\nworld\ncafé\n"` (with trailing newline). It explicitly notes in the docstring (lines 357–365) that it avoids the no-trailing-newline sentinel divergence between `Span.line_col()` (sentinel=len) and legacy `TerminalSource.pos_to_line_col` (which now also uses sentinel=len after the fix, per `terminalsrc.rs:400–401`). This is correct and consistent. However position 14 is `'é'` — a multibyte character — and the test asserts `lc_span.line_span.end == lc_ts.line_span.end`. The Python `TerminalSource.pos_to_line_col` also returns the corrected sentinel after the fix. This part is fine.

What is missing is a drift-anchor case for the last position in a no-trailing-newline source between `Span.line_col()` and `TerminalSource.pos_to_line_col()` on the Python side, now that both use `sentinel=len`. The current drift anchor explicitly punts on this (line 361: "legacy pos_to_line_col uses sentinel=len-1 — an intentional divergence"). But that comment is now stale: the Rust `pos_to_line_col` was fixed to use `sentinel=len` (per `terminalsrc.rs:400–401`), and the Python `pos_to_line_col` is untouched. If the Python `TerminalSource.pos_to_line_col` was also fixed (it would need to be to match), or if it was not fixed and the comment is stale, neither the test nor the comment is authoritative. The comment says "intentional divergence in the last line's end index" but the design (§2.5, §3) describes the sentinel fix as applying to both backends.

**Consequence:** Stale documentation in the drift-anchor test could mislead future readers about whether the Python `TerminalSource.pos_to_line_col` was fixed. If it was not fixed, then `Span.line_col().line_span.end` (sentinel=len) and `TerminalSource.pos_to_line_col().line_span.end` (sentinel=len-1) diverge on the last line, and no test pins this divergence as intentional vs. accidental. If it was fixed, the comment is wrong.

**Fix:** Add one test for a no-trailing-newline source at a position on the final line comparing `Span.line_col().line_span.end` vs `TerminalSource.pos_to_line_col().line_span.end`, with explicit assertion of the expected value (`11` if both now use sentinel=len), not just `==` comparison. Update the drift-anchor docstring to accurately state which sentinel each implementation uses. Also verify `fltk/fegen/pyrt/terminalsrc.py:pos_to_line_col` to determine if it was updated.

---

## test-5

**File:** `tests/test_error_formatter.py`, `TestCrossBackend.test_same_output_both_backends` (line 182)

**What's wrong:** The source text used is `"hello\nworld\n"` (trailing newline). The formatter test that pins cross-backend output identity therefore never exercises the formatter on a span from the last line of a no-trailing-newline source. The sentinel fix affects `line_span.text()`, which determines the displayed source line. If the sentinel were wrong on one backend, the caret line would be truncated — but this test would not catch it.

**Consequence:** A regression in sentinel computation that truncates the last-line display on one backend (e.g., `"worl"` instead of `"world"`) would produce different formatter output between backends but would not be caught by the cross-backend formatter test.

**Fix:** Add a `TestCrossBackend` variant that uses `"hello\nworld"` (no trailing newline), queries the last line (`pos=6`), and asserts `py_result == rs_result` and that the result contains `"world"` (full last line).

---

## test-6

**File:** `tests/test_error_formatter.py`, `TestOutputShape.test_with_explicit_filename` (lines 19–34) and `test_full_string_literal` (lines 38–47)

**What's wrong:** Both tests use Python-only spans. There is no single-backend test that asserts the full literal formatter output for a **Rust** span (without the cross-backend equality shortcut). The cross-backend test `test_same_output_both_backends` uses `py_result == rs_result` — a relative assertion — which is correct but means if both backends produce the same wrong string, neither test catches it.

**Consequence (minor):** This is a weak concern because the absolute-value assertion (`test_full_string_literal`) nails the Python side, and `test_same_output_both_backends` nails equivalence. Together they do establish the absolute value for Rust transitively. No critical gap; noted for completeness.

---

## test-7

**File:** `tests/test_rust_span.py`, `TestLineCol.test_line_col_or_raise_sourceless_raises` (line 1225) and `test_line_col_or_raise_negative_raises` (line 1230) and `test_line_col_or_raise_out_of_bounds_raises` (line 1236)

**What's wrong:** These three tests assert `pytest.raises(ValueError)` without checking the message content. The Python equivalents in `test_span.py` (lines 362–376) do check message content (`match="has no source"`, `match="negative"`, `match="out of bounds"`). Inconsistent verbosity is minor, but the Rust tests do not pin the error message family, which the design (§2.2) specifies.

**Consequence (minor):** A Rust implementation that raised `ValueError("unknown error")` instead of the specified message family would pass the Rust `line_col_or_raise` tests. The tests confirm error type but not diagnostic quality.

**Fix:** Add `match=` patterns to the Rust `line_col_or_raise` error tests, matching the message family the design specifies: `"has no source"`, `"negative"`, `"out of bounds"`.

---

## test-8

**File:** `tests/test_span_protocol.py`, `TestFilenameCrossBackend.test_parser_produced_span_filename_rust` (lines 331–350)

**What's wrong:** This test (which covers the design's most important case — that a parser-produced Rust span carries the filename) is guarded by two `pytest.skip` calls: one for `fegen_rust_cst` availability (line 13, at module level), and one for `fegen_rust_cst.parser` attribute presence (line 343). If `fegen_rust_cst` is available but has no `.parser` attribute, the test silently skips rather than failing. Similarly, the Python-side parser test `test_parser_produced_span_filename_python` at line 319 is marked `@pytest.mark.skipif(not _rust_available)` — this is a Python parser test gated on Rust availability, which is the wrong condition (it would run on Python-only installs and should always be available when `fltk_parser` is importable).

**Consequence:** The most important filename regression guard (parser-produced spans carry filename, design §2.9) silently skips if the optional fixture is absent. CI lanes without `fegen_rust_cst.parser` never exercise this path. The Python test `test_parser_produced_span_filename_python` carries a `skipif(not _rust_available)` that has nothing to do with whether the Python parser is importable.

**Fix:** Remove `skipif(not _rust_available)` from `test_parser_produced_span_filename_python` — it should run whenever the fltk Python package is importable. For the Rust variant, replace the silent skip on `getattr(fegen_rust_cst, "parser", None)` with an assertion failure (if `fegen_rust_cst` is importable it must have `.parser`), while keeping the outer `importorskip` for the fixture itself.
