# Quality review: span-line-col-api (8cd6232..b6c0aac)

Reviewed: hand-written Rust (`span.rs`, `terminalsrc.rs`, `lib.rs`), pyo3 shim (`src/`),
Python pyrt (`terminalsrc.py`, `span_protocol.py`, `error_formatter.py`), gsm2 generators,
and the `.pyi` stub. Generated grammar files (the volume of `*_parser.py` and `*_trivia_parser.py`
changes) judged against the templates only.

---

## quality-1

**File:line:** `crates/fltk-cst-core/src/span.rs:201-214` (`resolve_line_col` docstring)

**Issue: Precondition in doc is wrong for both callers.**

The function's docstring states:

> **Preconditions** (caller is responsible):
> - `pos >= 0` (negative-index sentinels must be short-circuited by the caller).

Both callers violate this:

1. `TerminalSource::pos_to_line_col` passes `pos = -1` for non-empty text when
   `ErrorTracker.longest_parse_len` is still at its initial `-1` value (the
   `pos < -1` guard rejects values below -1 but explicitly passes -1 through).
2. `Span::line_col_inner` passes `pos = -1` for empty text after the EOF clamp
   (`start == len == 0 → pos = 0 - 1 = -1`).

The function actually handles both cases correctly via the `-1` sentinel entry in the
`line_ends` cache (for empty text, `push(-1)`; for non-empty text, `bisect_left([-1-or-N,...], -1)
= 0 → col = -1`). So the function's behavior is correct; the documented contract is not.

**Consequence:** a future maintainer who adds a third caller, reads the precondition, and
short-circuits `pos == -1` for non-empty text will break the `ErrorTracker` sentinel path.
A future refactor guided by the stated contract could introduce a real bug. The misdescription
propagates: `Span::line_col_inner`'s own doc says "negative-index sentinels must be
short-circuited by the caller" without noting the empty-text exception that passes `pos = -1`
straight through to `resolve_line_col`.

**Fix:** Replace the `pos >= 0` precondition bullet with the actual contract:

```
/// **Preconditions** (caller is responsible):
/// - `pos >= -1`: `pos = -1` is accepted and produces `LineColPos(line=0, col=-1)`.
///   This is the intended path for: (a) empty text after EOF clamp (`start==len==0 → pos=-1`),
///   and (b) the `ErrorTracker.longest_parse_len` initial sentinel on non-empty text.
///   Values `pos < -1` are not meaningful and will produce incorrect results.
/// - `pos < text.chars().count()` after any EOF clamp (i.e., the caller must decrement
///   `start == len` to `len - 1` before calling; the value `len` itself is not accepted).
```

---

## quality-2

**File:line:** `fltk/fegen/pyrt/terminalsrc.py:115-158` (Python `Span.line_col` bisect body)  
vs. `fltk/fegen/pyrt/terminalsrc.py:273-295` (`TerminalSource.pos_to_line_col` bisect body)

**Issue: Python bisect algorithm is copy-pasted, not unified — and the existing TODO captures only the cache, not the algorithm duplication.**

The sentinel-building + `bisect_left` + `(col, line_start, line_end)` computation is identical
across both Python methods (diff:

```python
# Span.line_col():
line_ends = [idx for idx, c in enumerate(src) if c == "\n"]
ends_with_newline = bool(line_ends) and line_ends[-1] == src_len - 1
if not ends_with_newline:
    line_ends.append(src_len if src_len > 0 else -1)
idx = bisect.bisect_left(line_ends, pos)
if idx > 0:
    col = pos - line_ends[idx - 1] - 1
    line_start = line_ends[idx - 1] + 1
    line_end = line_ends[idx]
else:
    col = pos
    line_start = 0
    line_end = line_ends[0]

# TerminalSource.pos_to_line_col() — identical except uses self.line_ends (cached list)
```

The Rust side was deliberately unified into the single shared `resolve_line_col` function.
The Python side has two identical copies. The existing `TODO(py-span-linecol-cache)` defers
unifying the *cache* via `SourceText._line_ends`; it does not capture the *algorithm*
duplication, which is fixable now without the cache plumbing.

**Consequence:** the two Python copies can drift. The sentinel sentinel behavior already changed
once in this PR (from `len-1` to `len` for the final-line end). Both copies were updated
correctly this time, but any future algorithm change (e.g., tab expansion, bidi codepoint
handling) needs two edits. The risk compounds if a third call site (e.g., a future
`SourceText.line_ends()` accessor) is added before the cache refactor happens.

**Fix:** Extract a private helper in `terminalsrc.py` that takes the source string and a
pre-built `line_ends` list (empty list = uncached) and returns `(idx, col, line_start, line_end)`.
Both callers pass the list (Span passes a freshly-built local list; TerminalSource passes `self.line_ends`).
The helper needs no cache awareness. This removes the algorithm duplication now; the
`TODO(py-span-linecol-cache)` remains for the follow-up cache-via-`SourceText` work.
Example signature:

```python
def _bisect_line_col(
    src: str, pos: int, line_ends: list[int]
) -> tuple[int, int, int, int]:
    """Return (line_idx, col, line_start, line_end) for pos in src, using line_ends cache.

    line_ends may be empty (will be populated in-place on first call).
    """
```

Alternatively, update the `TODO(py-span-linecol-cache)` description to explicitly call out
that it should also unify the algorithm, so the bifurcation point is visible.

---

## TODO pairing audit

Both deferred TODOs are legitimately paired:

- `TODO(linecol-cache-consolidate)`: entry in `TODO.md` (line 62); code comments at
  `crates/fltk-cst-core/src/span.rs:53`, `crates/fltk-parser-core/src/terminalsrc.rs:167`
  and `178`. Concrete, deferrable, "done is obvious." ✓
- `TODO(py-span-linecol-cache)`: entry in `TODO.md` (line 66); code comment at
  `fltk/fegen/pyrt/terminalsrc.py:133`. Concrete location, legitimate cold-path deferral. ✓

Neither is masking a present defect: both are acknowledged performance trade-offs
over immutable data where correctness is preserved (separate caches derive identically from
immutable text; Python O(N) scan on cold error paths).

---

## API surface / public-API cleanliness

The additive surface (`line_col`, `line_col_or_raise`, `filename` on `SpanProtocol` and both
backend `Span` types; `filename` constructor param on `SourceText`/`TerminalSource`/generated
parsers; `LineColPos` pyclass; `error_formatter.format_source_line`) is consistent and
non-breaking. No existing public symbol is renamed or signature-changed. The `filename` param
defaults to `None` everywhere so all existing call sites (`SourceText(text)`,
`TerminalSource(text)`, `Parser(source)`) are unaffected. The `fltk_parser_core::LineColPos`
re-export is preserved so downstream Rust consumers see no churn. No annotation-churn for
out-of-tree consumers typing `SpanProtocol`. ✓

The `line_col_or_raise` / `py_line_col` Rust implementations follow the established
`text_or_raise` / `py_text` pre-check-then-delegate pattern. The duplication of guard
conditions between `line_col_or_raise` and `line_col_inner` mirrors `text_or_raise` vs
`text_inner`. No issue.

The `py_filename` method clones `Option<String>` on each call (required by pyo3; consistent
with the existing `py_text` / `py_text_or_raise` allocation pattern). The pure-Rust
`filename_inner` returns `Option<&str>` for zero-copy Rust callers. ✓

`SpanProtocol.line_col` is annotated `-> "LineColPos | None"` with the Python
`terminalsrc.LineColPos` as the canonical type, matching the design decision (§2.11, §6 OQ3).
The `AnyLineColPos` deferral is explicitly acknowledged in the design. No issue.
