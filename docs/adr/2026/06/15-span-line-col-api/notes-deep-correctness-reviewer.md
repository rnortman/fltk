# Deep correctness review — span line/col + filename + error formatter

Commit reviewed: `b6c0aac` (base `8cd6232`), branch `span-line-col-api`.
Scope: cross-backend line/col equivalence (Python `terminalsrc.py` vs Rust `span.rs`/`resolve_line_col`),
1-vs-0-based & sentinel logic, codepoint↔byte conversion, optional-filename threading, error formatter.

Method: read both implementations end-to-end; reimplemented both algorithms in isolation and
exhaustively diffed them (`/tmp/trace*.py`); then ran the **actual compiled backends** (`maturin develop`)
and exhaustively diffed `Span.line_col()` Python-vs-Rust over a corpus covering empty source, final line
with/without trailing `\n`, leading/consecutive newlines, multibyte (`é`, `🎉`), tabs, zero-width spans,
EOF (`start == len`), and out-of-domain (`start > len`). Result: **zero mismatches**.

## Verdict on the focus areas (all correct)

- **Last-line off-by-one fix is genuinely correct.** Both `Span.line_col()` paths AND both legacy
  `pos_to_line_col` paths now push sentinel `= len` (not `len-1`) for a final line without a trailing
  newline (`terminalsrc.py:144-146,281-283`; `span.rs:232-237`). The "covers the entire line" contract
  holds: for every non-newline position, `line_span.text()` equals the full physical line on both
  backends, including the last character of an unterminated final line. Verified at runtime on both
  backends and against the split-on-`\n` oracle.
- **1-vs-0-based / sentinel logic.** `line`/`col` 0-based codepoint indices on both backends; the
  formatter owns the `+1` display convention. Empty-source `col=-1` corner reproduced identically
  (clamp `start==len==0 → pos=-1`), and the `start<0` sentinel guard short-circuits to `None`/raise
  *before* the bisect on both backends, as designed. `partition_point` (Rust) ≡ `bisect_left` (Python)
  confirmed exhaustively.
- **Codepoint↔byte.** `line_ends` stores codepoint indices (`chars().enumerate()`, not `char_indices()`);
  `col` and the caret indent (`' ' * lc.col`) count codepoints on both backends. Multibyte and 🎉
  (astral) cases align. No byte translation in the line/col path — correct.
- **Filename threading reaches parser-produced spans on BOTH backends.**
  - Python: generated `Parser.__init__` builds `SourceText(text=terminalsrc.terminals,
    filename=terminalsrc.filename)` (`fltk_parser.py:16`, emitter `gsm2parser.py:113-123`); spans are
    built via `Span.with_source(..., self._source_text)` which copies `_filename` into
    `_source_filename`. Verified by a real parse → `span.filename() == "grammar.fltkg"`.
  - Rust: `PyParser::new(text, filename, …)` → `Parser::new(text, filename, …)` →
    `SourceText::from_str(text, filename)` (`parser.rs:56-58,1399-1407`, emitter
    `gsm2parser_rs.py:380-381,944-947`). The design-1 "ctor isn't on the parse path" hole is closed.
  Optionality holds end-to-end: `None` default everywhere; no runtime branch on filename.
- **EOF / or_raise boundary symmetric.** `start==len` clamps and succeeds; `start==len+1` returns
  `None` (`line_col`) / raises `ValueError` (`line_col_or_raise`) on both backends. Verified at runtime.
- **No tests pass only because both backends are identically wrong.** The cross-backend tests assert
  field-by-field, and I independently re-derived the expected `(line, col, line_span)` from a pure
  split-on-`\n` oracle (not from either implementation) — both backends match the oracle, not just
  each other.

## Findings

### correctness-1  (stale/contradictory test docstring — documentation defect, not a logic bug)
File: `tests/test_span_protocol.py:358-364` (`TestDriftAnchor.test_py_span_line_col_agrees_with_terminalsrc_pos_to_line_col` docstring).

What's wrong: the docstring asserts a divergence that no longer exists. It states: "When the source has
no trailing newline, `Span.line_col()` uses sentinel=len while the legacy `pos_to_line_col` uses
sentinel=len-1 — an intentional divergence in the last line's end index." This is false for the code as
committed.

Why: `TerminalSource.pos_to_line_col` (`terminalsrc.py:281-283`) now computes the sentinel as
`terminals_len if terminals_len > 0 else -1` — exactly the same `len` sentinel as `Span.line_col()`
(`terminalsrc.py:144-146`). The off-by-one fix (design §2.5 note 3, §5) changed the legacy method from
`len-1` to `len`. I verified by exhaustive trace that the two paths agree on `line`, `col`,
`line_span.start`, AND `line_span.end` for all positions including unterminated final lines — there is
**no** final-line `line_span.end` divergence. The sibling test `tests/test_span.py:389-409`
(`test_line_col_parity_with_terminalsrc_pos_to_line_col`) correctly documents the opposite ("Both
implementations now use sentinel = len … so line_span.end agrees on both paths") and even asserts
`line_span.end` equality — directly contradicting this docstring.

Consequence: no wrong runtime behavior (the test's assertions are correct and pass; it just happens to
use a `\n`-terminated source so the stale claim is never exercised). The risk is to a future maintainer:
the docstring describes a phantom invariant. Acting on it — e.g. "restoring" `len-1` in the legacy
method to match the docstring, or adding a test that pins the claimed final-line divergence — would
reintroduce the off-by-one the fix removed, truncating the last character of unterminated final lines in
`line_span` and breaking the entire-line contract. The only genuine `pos_to_line_col` divergence is at
**negative** positions (the `start<0 → None` guard), which is pinned separately and correctly at
`test_span.py:412-427`.

Suggested fix: replace the docstring's second paragraph to match reality — both paths use sentinel=len
and agree on `line_span.end`; the only deliberate divergence is the negative-start guard (pinned in
`test_span.py::test_line_col_negative_diverges_from_pos_to_line_col`). The cross-reference to
`test_line_col_line_span_is_source_bearing` as a "divergence" test is also misdescribed — that test pins
source-bearing-ness and the `len` sentinel, not a divergence.

## Notes (not findings)

- `cargo test -p fltk-cst-core` cannot link in this sandbox (`-lpython3.10` not on the linker path
  because the `python` feature is default-on). This is an environment limitation, not a code defect; the
  added pure-Rust unit tests (`lib.rs` `resolve_line_col_tests`) and the maturin-built runtime comparison
  cover the same algorithm.
- Cross-backend `Span`/`LineColPos` equality is source-ignoring *within* a backend, but a Rust `Span`
  and a Python `Span` at the same indices are not `==` (distinct classes, no cross-type `__eq__`). This
  is the pre-existing accepted asymmetry; the tests compare field-by-field, so it does not affect
  correctness. Not a finding.
- New error formatter (`error_formatter.py`) caret uses `' ' * lc.col`; `col=-1` empty-source corner is
  harmless (`' ' * -1 == ''`). Caret aligns to codepoint column on both backends. Correct.

Logic of the change is sound; the single finding above is a stale test docstring.
