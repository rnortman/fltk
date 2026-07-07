# Scope review notes — FINAL round (87dbc0d..9a085e9)

No findings.

## Round-slice check (increments 11-13, this diff)

- Increment 11 (`AnalysisEngine`, §4.7): `fltk/lsp/engine.py` matches the log — `HighlightResult`,
  `AnalysisEngine.__init__`/`from_paths`/`highlight` all present, with the disclosed
  constructor-seam deviation (adds testability, no behavior change). `test_engine.py` (7 tests)
  present and matches described cases; suite green.
- Increment 12 (`fltk-highlight` CLI, §4.8): `fltk/lsp/highlight_cli.py` (theme table, `_render`,
  `main`) and `pyproject.toml`'s `[project.scripts] fltk-highlight = ...` both present, matching
  §4.8 and the §9 console-script user decision verbatim. `test_highlight_cli.py` (4 tests) matches
  the log's description.
- Increment 13 (dogfood fixture, §8 last bullet): `fltk/lsp/fltklsp.fltklsp` and
  `fltk/lsp/test_dogfood.py` (2 tests) present, matching the log's description of what each rule
  block paints and the dropped-blanket-rule deviation.
- `uv run pytest fltk/lsp -q` → 122 passed, matching the log's running total. Full repo suite
  (`uv run pytest -q`) → 2730 passed, 1 skipped — green.
- No new dependencies, no Rust/Bazel changes — diff is exactly `engine.py`, `highlight_cli.py`,
  `fltklsp.fltklsp`, three new test files, and the one-line `pyproject.toml` addition, all
  traceable to §4.7/§4.8/§8/§9.

## Whole-design check (log increments 1-13 vs. design §4.1-§8, §9)

Walked the full implementation log against every design section:

- §4.1 grammar → increment 1 (`fltklsp.fltkg` + committed generated parser + `Makefile` gencode
  step, matches §5).
- §4.2 config model → increment 3.
- §4.3 validation/resolution → increments 4 (index), 5 (validation), 6 (resolution), 9
  (`load_lsp_config` entry point), 10 (`plumbing` wrappers).
- §4.4 analysis grammar → increment 2, including the `INLINE`-rejection guard.
- §4.5 default classification → increment 7.
- §4.6 painter engine → increment 8.
- §4.7 `AnalysisEngine` → increment 11 (this round).
- §4.8 CLI → increment 12 (this round).
- §8 test plan → every named test file exists (`test_fltklsp_parse.py`, `test_lsp_config.py`,
  `test_analysis.py`, `test_classify.py`, `test_highlight_cli.py`, dogfood fixture + test), plus
  extra finer-grained files (`test_grammar_index.py`, `test_lsp_validation.py`,
  `test_lsp_resolve.py`, `test_classify_painter.py`, `test_load_lsp_config.py`,
  `test_plumbing_lsp_config.py`) that split the design's coarser groupings — not scope creep,
  just finer test organization of the same design-mandated coverage.
- §9 user decisions → console-script registration (increment 12) and def-site paint live in
  round 1 (increment 6, def-paint with `declaration` modifier) both implemented as decided.
- §7 (roadmap deltas) is prose about future milestones, not implementation scope for this round;
  correctly nothing was built against it.
- Explicitly out-of-round-1 items per §1 (pygls server/M2, prefix-CST/M3, symbol tables/M4,
  resolver/M5, HTML CLI output, UTF-16 positions, TextMate export) are absent from both diff and
  log, as designed — not a completeness gap.

No design item is missing a log entry or a TODO. The four self-identified TODOs
(`lsp-cst-text-helpers`, `lsp-test-parse-helper`, `lsp-classify-hotpath`, `lsp-rule-surface-index`)
are internal reuse/perf refactors the implementer flagged beyond what the design required (the
design never mandates a single canonical span-text helper or sub-quadratic `classify`); they are
legitimate self-imposed punts with rationale and matching `TODO(slug)` comments plus `TODO.md`
entries, not unfinished design scope. (Minor, non-blocking: `lsp-test-parse-helper`'s comment in
`test_lsp_validation.py:23` says to fold into `plumbing.parse_lsp_config` "once that wrapper
lands" — it landed in increment 10 and the fold was never revisited. Not logged as a finding: the
TODO targets internal test-helper duplication, not a design deliverable, and the fold isn't
actually a clean fit since `_parse` deliberately parses *without* validating so `validate_config`
can be tested directly, unlike the wrapper.)

Nothing in the diff or log claims work outside the effective design (design.md; no delta docs
exist in this ADR's workflow directory). No undesigned/undelta'd scope creep found.
