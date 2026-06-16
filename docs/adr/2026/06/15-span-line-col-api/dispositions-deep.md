# Dispositions — deep review, round 1

Commit reviewed: `b6c0aac` (base `8cd6232`), branch `span-line-col-api`.
Fixes committed at: `3a61b07`.

---

## efficiency-1

- Disposition: Fixed
- Action: Added `SourceInner.char_count: OnceLock<i64>` in `crates/fltk-cst-core/src/span.rs:58`
  (alongside the existing `line_ends` OnceLock). Both `line_col_inner` (`span.rs:516`) and
  `line_col_or_raise` (`span.rs:782`) now read the cached count in O(1) on warm calls rather than
  paying `chars().count()` (O(N)) each time. The `resolve_line_col` function had its own O(N) scan
  inside `get_or_init` already gated on coldness (moved there per this finding); it remains O(N)
  on cold but O(0) on warm (the closure is skipped). Result: warm `line_col()` calls are O(log
  N_lines) as the design claimed.
- Severity assessment: Without the fix, any consumer resolving many spans against one large source
  (e.g. an LSP-style pass emitting diagnostics) would pay O(source_len) per call instead of O(log
  N_lines), voiding the design's amortization claim for the Rust backend.

---

## errhandling-1

- Disposition: Fixed
- Action: Replaced the false `pos >= 0` precondition bullet in `resolve_line_col`'s docstring
  (`span.rs:201-214`) with an accurate statement that `pos = -1` is accepted for two callers:
  (a) empty-source EOF clamp (`start == len == 0 → pos = -1`) and (b) `ErrorTracker.longest_parse_len`
  initial sentinel on non-empty text. Values `pos < -1` remain unsupported.
- Severity assessment: The false contract was a maintainability trap — a future maintainer trusting
  the stated precondition could add a `pos < 0 → None` guard that would silently break both callers'
  empty-source and parse-error-position behavior, causing "Syntax error at unknown position" fallback
  with no diagnostics.

---

## errhandling-2

- Disposition: Fixed
- Action: Replaced bare `.unwrap()` at `span.rs:795` with
  `.expect("invariant: source is Some — is_none() guard above returned Err already")`,
  matching the `text_or_raise` pattern at `span.rs:664`.
- Severity assessment: A bare `.unwrap()` panic in a guarded invariant site is indistinguishable
  from any other `.unwrap()` failure in crash logs; the `.expect` message provides the diagnostic
  link needed if a future refactor inadvertently reaches this path.

---

## errhandling-3

- Disposition: Fixed
- Action: Replaced the fallthrough message `"could not resolve line/col"` in `line_col_or_raise`
  (`span.rs:803-808`) with `"line_col_inner returned None despite passing all guards — internal
  invariant violation; start={}, source_len={}"`, including both the start position and the
  source length so the failure site can be reconstructed from the error string alone.
- Severity assessment: The old message named only the symptom. If ever reachable (e.g. through a
  future change to `resolve_line_col`), the new message identifies the invariant violation and
  provides the values needed to diagnose it.

---

## correctness-1

- Disposition: Fixed
- Action: Replaced the stale docstring in `TestDriftAnchor.test_py_span_line_col_agrees_with_terminalsrc_pos_to_line_col`
  (`tests/test_span_protocol.py:356-378`) that falsely claimed "Span.line_col() uses sentinel=len while
  the legacy pos_to_line_col uses sentinel=len-1 — an intentional divergence." The corrected docstring
  states that both implementations now use `sentinel=len` (design §2.5 note 3 fixed both) and that the
  only deliberate divergence is at negative positions, cross-referenced to
  `test_line_col_negative_diverges_from_pos_to_line_col`.
- Severity assessment: The phantom "divergence" described in the stale docstring, if acted on by a
  future maintainer, could cause a reintroduction of the off-by-one bug that truncated the last character
  of unterminated final lines in `line_span`.

---

## security-1

- Disposition: Fixed
- Action: Added `_escape_for_display()` in `fltk/fegen/pyrt/error_formatter.py:29-64` that replaces
  C0/C1/DEL control characters and bidi-override/invisible Cf codepoints (U+202A-U+202E, U+2066-U+2069,
  U+200B/C/D, U+FEFF) with their `U+XXXX` Unicode escape forms. Applied to `lc.line_span.text()` before
  interpolation into the formatter output. Caret indent is recomputed from the escaped prefix to stay
  aligned with the escaped text.
- Severity assessment: The source line in `format_source_line` is attacker-controlled (it is the parsed
  input). Without escaping, crafted ESC sequences, CR, or bidi-override characters can corrupt or spoof
  terminal/log output. The sibling Rust formatter (`errors.rs:144-145`) already applied this hardening;
  the Python formatter was a regression of that protection for any consumer printing to a terminal.

---

## security-2

- Disposition: Fixed
- Action: The same `_escape_for_display()` function (security-1) is also applied to the `filename` string
  before interpolation into the `In <file>:L:C:` header (`error_formatter.py:101`). A `\n` in the filename
  becomes `U+000A`, keeping the header on a single line; ANSI/bidi sequences in paths are similarly
  neutralized.
- Severity assessment: Filenames are typically developer-supplied but the formatter offers no restriction
  on their content. A consumer threading an externally-derived path (uploaded filename, import-path from
  the parsed document) would expose log-spoofing / terminal-injection without this escaping.

---

## test-1

- Disposition: Fixed
- Action: Added `TestLineColCrossBackend.test_no_trailing_newline_sentinel`
  (`tests/test_span_protocol.py`) asserting that both backends return `line_span.end == 11` (not 10)
  for `"hello\nworld"` queried at position 6. This is the cross-backend regression guard for the
  sentinel off-by-one fix: the existing cross-backend tests all used sources ending with `\n`, so a
  regression to `sentinel = len-1` on either backend would have passed them.
- Severity assessment: Without this test, the original bug class (last character of an unterminated
  final line absent from `line_span`) could re-emerge asymmetrically (one backend wrong, one right)
  and be invisible to the cross-backend equivalence suite.

---

## test-2

- Disposition: Fixed
- Action: Added `test_line_col_empty_source` to `tests/test_span.py` (Python backend) and
  `test_empty_source_cross_backend` to `TestLineColCrossBackend` in `tests/test_span_protocol.py`.
  Both assert that `Span.with_source(0, 0, SourceText("")).line_col()` returns
  `LineColPos(line=0, col=-1)`, not `None`.
- Severity assessment: The empty-source `col=-1` corner is a documented non-trivial case (design §3);
  without Python/pyo3 tests, a change that incorrectly returned `None` for empty source would go
  undetected.

---

## test-3

- Disposition: Fixed
- Action: Added `TestLineColCrossBackend.test_zero_width_span_cross_backend`
  (`tests/test_span_protocol.py`) asserting that `Span(p, p).line_col()` is not `None` and returns
  the correct position.
- Severity assessment: A backend that returned `None` for zero-width spans (treating `start == end`
  as empty/sentinel) would not be caught by the existing cross-backend suite.

---

## test-4

- Disposition: Fixed
- Action: Same fix as correctness-1 — the stale docstring is the test-4 finding.
  See correctness-1 entry.
- Severity assessment: See correctness-1.

---

## test-5

- Disposition: Fixed
- Action: Added `TestCrossBackend.test_same_output_no_trailing_newline` to `tests/test_error_formatter.py`
  using `"hello\nworld"` (no trailing newline) and asserting `py_result == rs_result` and `"world" in py_result`.
- Severity assessment: A sentinel regression that truncated the last-line display on one backend would
  produce different formatter output between backends but would not be caught by the prior cross-backend
  formatter test (which used a `\n`-terminated source).

---

## test-6

- Disposition: Won't-Do
- Action: No change. The finding acknowledges this is "weak concern" and that the absolute value is
  established transitively (Python absolute assertion + Python==Rust equivalence).
- Severity assessment: Adding a duplicate absolute-value assertion for the Rust side would add
  maintenance burden with no additional defect-catching power beyond what the existing pair of
  tests already provides.
- Rationale (Won't-Do): The finding's own text states "No critical gap; noted for completeness."
  Adding a third assertion testing the same output literal via a different path does not catch any
  class of bug that the existing absolute test (`test_full_string_literal`) plus equivalence test
  (`test_same_output_both_backends`) together miss.

---

## test-7

- Disposition: Fixed
- Action: Added `match=` patterns to the three Rust `line_col_or_raise` error tests in
  `tests/test_rust_span.py:1225-1240`: `match="has no source"`, `match="negative"`,
  `match="out of bounds"`. Matches the Python equivalents in `test_span.py:362-376`.
- Severity assessment: Without message patterns, a Rust implementation that raised a generic
  `ValueError("unknown error")` would pass the tests; the design (§2.2) specifies the message
  family for diagnostic quality.

---

## test-8

- Disposition: Fixed
- Action: Two changes in `tests/test_span_protocol.py`:
  1. Removed `@pytest.mark.skipif(not _rust_available)` from `test_parser_produced_span_filename_python`
     — this is a Python-parser test that has nothing to do with Rust availability.
  2. In `test_parser_produced_span_filename_rust`, replaced the silent `pytest.skip` on
     `getattr(fegen_rust_cst, "parser", None)` with a direct attribute access (`fegen_rust_cst.parser`)
     that will `AttributeError`-fail (not skip) if `fegen_rust_cst` is importable but lacks `.parser`.
- Severity assessment: The Python parser test was silently skipped on Python-only installs with the old
  gate. The Rust test's silent skip on a missing attribute would let a broken `fegen_rust_cst` install
  masquerade as "tested."

---

## reuse-1

- Disposition: TODO(py-span-linecol-cache)
- Action: No code change. The Python bisect-algorithm duplication between `Span.line_col`
  (`terminalsrc.py:115-158`) and `TerminalSource.pos_to_line_col` (`terminalsrc.py:273-295`) is
  pre-acknowledged in the design (§7 item 1) and tracked by the existing `TODO(py-span-linecol-cache)`
  at `terminalsrc.py:133` and `TODO.md:66`. The quality reviewer's suggestion to extract a
  `_bisect_line_col()` helper is absorbed into the scope of that TODO (updating the `TODO.md` entry
  to explicitly include algorithm deduplication, not just caching).
- Severity assessment: The two copies can drift independently, but the sentinel behavior was updated
  correctly in both this PR. The TODO is concrete and the deduplication can be done without the cache
  plumbing by extracting a pure helper function that takes a pre-built list — acknowledged for the
  follow-up.

---

## reuse-2

- Disposition: TODO(linecol-cache-consolidate)
- Action: No code change. The two Rust `OnceLock<Vec<i64>>` caches (`SourceInner.line_ends` and
  `TerminalSource.line_ends`) over the same immutable text are pre-acknowledged in the design (§7 item 2)
  and tracked by `TODO(linecol-cache-consolidate)` at `span.rs:53-57` and `terminalsrc.rs:178-180`,
  with a `TODO.md` entry at line 62. Not a correctness issue; the deduplication is the one-line
  `resolve_line_col(self.text(), pos, &self.source.inner.line_ends)` change noted in both the design
  and the reuse review.
- Severity assessment: Two independent O(N) scans and two Vec<i64> allocations over the same immutable
  text on a large source; accepted as noted duplication per the design. The fix is not in scope for this
  respond round.

---

## quality-1

- Disposition: Fixed
- Action: Same fix as errhandling-1 — the quality-1 finding is identical to errhandling-1.
  See errhandling-1 entry.
- Severity assessment: See errhandling-1.

---

## quality-2

- Disposition: TODO(py-span-linecol-cache)
- Action: No code change. Same as reuse-1. The algorithm duplication is subsumed by the existing
  `TODO(py-span-linecol-cache)` and will be addressed together with the cache work.
- Severity assessment: Same as reuse-1. The two copies currently produce identical output and any
  future one-liner sentinel fix would need to be applied in both places, but this is a maintenance
  risk rather than a present defect.
