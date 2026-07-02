# Design review notes — `unparser-none-path-diagnostics`

Reviewer: design-reviewer. Design: `design.md` (this directory). Verified against
worktree at `c03a8012` (the review base).

## Verification summary (what was checked and held up)

Adversarial fact-check performed; the design is unusually well-grounded. Confirmed
against source:

- Both TODO sites exist exactly where claimed: `fltk/unparse/gsm2unparser_rs.py:1091`
  (`let text = span.text()?;`, TODO comment at 1086-1090) and `:1366`
  (`if let Some(trivia_result) = self.unparse__trivia(&trivia_node)` with no `else`,
  TODO at 1360-1365). These are the only two `TODO(unparser-none-path-diagnostics)`
  comments in the tree, and each is the only emission site of its kind (single
  `unparse__trivia` call emission per backend; single `span.text()?` emission).
- Python site 1: `gsm2unparser.py:1321` passes no `orelse` to `if_`; `Block.if_`
  (`fltk/iir/model.py:158`) defaults `orelse=False`; `expr_stmt` exists
  (`model.py:153`); `LiteralString` exists (`model.py:~352`). The
  `iir.VarByName("fltk.unparse.pyrt", ...)` pattern is real (`_make_is_span_check`,
  `gsm2unparser.py:380-394`; regex-term `extract_span_text` call at `:1758-1767`).
- `pyrt.extract_span_text` (`fltk/unparse/pyrt.py:34-50`) raises `ValueError` for
  source-bearing spans and falls back to `terminals` slicing for sourceless spans,
  exactly as the design states. `terminalsrc.Span.text_or_raise` at
  `terminalsrc.py:73-87`, `has_source` at `:89-91` — confirmed.
- `Span::text`/`text_str` return-`None` conditions and the `Debug` impl eliding
  source but reporting `has_source` (`crates/fltk-cst-core/src/span.rs:~295-305`,
  `~418-441`) — confirmed. Two-arg Python constructor is sourceless
  (`py_new`, `span.rs:~599-607`) — confirmed.
- No `panic = "abort"` profile anywhere in the workspace, so the PyO3
  panic → `pyo3_runtime.PanicException` (a `BaseException` subclass) claim is sound.
- Regen inventory is complete: the only committed generated unparsers are
  `tests/rust_parser_fixture/src/unparser.rs`, `.../unparser_default.rs`, and
  `crates/fegen-rust/src/unparser.rs` (the `fltkfmt` binary consumes the fegen-rust
  one; no Python-generated unparser is committed in-tree — verified by grep).
- Test-plan feasibility spot-checks pass:
  - Fixture unparsers' `_has_preservable_trivia` is a constant `false`
    (`tests/rust_parser_fixture/src/unparser.rs:25-27`), so site 1 is indeed
    unreachable there and the fegen-rust crate is the right host for the site-1
    Rust test; fegen-rust's `_has_preservable_trivia` matches
    `BlockComment`/`LineComment` child variants (`crates/fegen-rust/src/unparser.rs:25-32`).
  - The claimed test-3 construction was traced through the generated code: an
    empty `LineComment` fails its `item0` bounds check → `unparse_line_comment`
    returns `None` → all three `__trivia` inner alts fail → the `*` loop exits with
    `match_count == 0` → `unparse__trivia` returns `None` (`unparser.rs:1742-1860`).
    `_has_preservable_trivia` still returns `true` (it checks the child variant,
    not the comment's own children), so the new site-1 `else` fires. Rust-side
    construction is possible via the `new(span)`/`push_child()` accessor API the
    CST structs document.
  - `rust_parser_fixture.unparser.Unparser()` is Python-callable
    (used by `tests/test_rust_unparser_parity_fixture.py`), so test 2 works as
    described; `fltk/unparse/test_unparser.py` already builds unparsers with
    `TriviaConfig(preserve_node_names=...)` at test time (line ~553), so test 4's
    premise holds.
- Requirements coverage: the request's shape (site-1 policy call + exact Rust error
  shape, changes in both backends' emitters, regen, tests) maps fully onto changes
  1-5 and the test plan. Scope discipline is good — the `text_str().unwrap_or(0)`
  newline-count paths are explicitly excluded with a defensible reason, Python
  site 2 is correctly left alone, and no `Result` plumbing / API churn is proposed
  (consistent with CLAUDE.md's generated-API stability mandate).
- Backtracking edge case: the design's claim that a panic aborting alternative
  dispatch is safe matches the code — the Python backend's `extract_span_text`
  `ValueError` already aborts dispatch identically today.

## Findings

### design-1 — Stated base commit contradicts the design's own citations

- Section: header, "Base commit: `8fd5ecf`. TODO entry: `TODO.md:43-45`."
- What's wrong: these two claims are mutually inconsistent. At `8fd5ecf` the TODO
  entry sat at `TODO.md:85-87` (exploration.md, which was written against
  `8fd5ecf`, says exactly that). The `TODO.md:43-45` locator is only true at
  `c03a8012` (the "TODO burndown: Delete bad/stale TODOs" commit), which is the
  actual review base. All other line references in the design also match
  `c03a8012`.
- Consequence: an implementer or verifier who checks out the stated base
  `8fd5ecf` to validate the design's line references will find `TODO.md:43-45`
  pointing at a different entry and may conclude other citations are stale too;
  the bookkeeping step ("delete the entry") is still unambiguous via the slug, so
  the impact is confusion/wasted verification time, not wrong code.
- Fix: change the header to `Base commit: c03a8012` (or restate the TODO locator
  for whichever commit is named).

### design-2 — Helper unit test placed in a file scoped to a different module

- Section: Test plan, item 5: "**Helper unit test** (`tests/test_pyrt_errors.py`):
  `raise_preserved_trivia_failure` raises `ValueError` naming the rule."
- What's wrong: `tests/test_pyrt_errors.py` exists, but its documented scope is
  `fltk.fegen.pyrt.errors` — "Tests for fltk.fegen.pyrt.errors —
  escape_control_chars and format_error_message. Expected strings are
  cross-pinned with the Rust unit tests in crates/fltk-cst-core/src/escape.rs"
  (file docstring). The new helper lives in a different package,
  `fltk.unparse.pyrt`, whose existing tests live under `fltk/unparse/`
  (`test_unparser.py`, `test_is_span_guard.py`, etc.). The design's phrasing
  implies this file is the established home for the new helper's test; it is a
  name-collision (`pyrt` appears in both packages), not the right home.
- Consequence: a one-shot implementer following the plan literally will append an
  unrelated `fltk.unparse.pyrt` test to a file whose docstring and cross-pinning
  contract are about parser error formatting, muddying the file's scope and
  misleading future readers about what is cross-pinned with the Rust escape tests.
- Fix: put the helper test alongside the other `fltk.unparse` tests (e.g. a small
  new `fltk/unparse/test_pyrt.py`, or inside the site-1 runtime test module from
  test-plan item 4).

### design-3 — Internal citation inconsistency for the extract_span_text call site

- Section: "Context / root cause" cites "`gsm2unparser.py:1764`" for the regex
  path's `pyrt.extract_span_text` call; "Proposed changes" §3 cites the same call
  as "`(:1758)`".
- What's wrong: the same call site is given two different line numbers in the same
  document. Actual: the `pyrt_module` binding starts at `:1758` and the
  `extract_span_text` call is at `:1764-1767`, so each number points into the
  right code block, but the doc reads as if they were two references to one line.
- Consequence: negligible for implementation (both land in the right ten lines);
  worth a one-character-class cleanup only if the doc is revised for design-1.
  Included for completeness, not weight.

No other findings. Every other substantive claim checked out against source.
