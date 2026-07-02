# Dispositions — design review round 1 (`unparser-none-path-diagnostics`)

Design: `design.md` (this directory). Reviewer notes:
`notes-design-design-reviewer.md`. All three findings were independently
fact-checked against source before disposition.

design-1:
- Disposition: Fixed
- Action: Header of `design.md` now states `Base commit: c03a8012` and notes
  that exploration.md was written against `8fd5ecf` (where the TODO entry sat
  at `TODO.md:85-87`), with all design line references pinned to `c03a8012`.
  Verified independently: `grep -n` shows the entry at `TODO.md:43` at
  `c03a801` (current HEAD) and at `:85` in `git show 8fd5ecf:TODO.md` — the
  reviewer's claim is exactly right.
- Severity assessment: No wrong code would result (the slug disambiguates the
  bookkeeping step), but a verifier checking out the stated base would find the
  `TODO.md:43-45` locator false and could wrongly distrust the design's other
  citations. Worth fixing precisely because this design's credibility rests on
  its citations.

design-2:
- Disposition: Fixed
- Action: Test-plan item 5 in `design.md` now targets a new
  `fltk/unparse/test_pyrt.py` alongside the other `fltk.unparse` tests, with an
  explicit warning that `tests/test_pyrt_errors.py` is a name collision — its
  docstring scopes it to `fltk.fegen.pyrt.errors`, cross-pinned with
  `crates/fltk-cst-core/src/escape.rs`. Verified: the docstring reads exactly as
  the reviewer quoted, and the new helper lives in the distinct package
  `fltk.unparse.pyrt`, whose tests all live under `fltk/unparse/`.
- Severity assessment: A literal one-shot implementer would have appended an
  unrelated test to a file with a documented cross-pinning contract, muddying
  its scope and misleading future readers about what is pinned against the Rust
  escape tests. Cheap to fix now, annoying to untangle later.

design-3:
- Disposition: Fixed
- Action: Proposed-changes §3 in `design.md` now cites the `extract_span_text`
  call as `:1764`, matching the "Context / root cause" citation for the same
  call site. Verified: `pyrt_module` binding begins at `gsm2unparser.py:1758`
  and the `extract_span_text` call is at `:1764-1767`; `:1764` is the accurate
  locator for "the call" in both places.
- Severity assessment: Negligible — both original numbers landed inside the
  right ten-line block; this is a consistency cleanup taken because the doc was
  already being revised for design-1.
