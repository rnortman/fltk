# Reuse review — round: AnalysisEngine (§4.7), fltk-highlight CLI (§4.8), dogfood fixture (§8)

Commit range reviewed: 87dbc0d..9a085e9 (files: `fltk/lsp/engine.py`, `fltk/lsp/highlight_cli.py`,
`fltk/lsp/test_dogfood.py`, `fltk/lsp/fltklsp.fltklsp`, `fltk/lsp/test_engine.py`,
`fltk/lsp/test_highlight_cli.py`, `pyproject.toml`).

## reuse-1

- **File:line**: `fltk/lsp/engine.py:70-73` (`AnalysisEngine.from_paths`)
- **What's duplicated**: `from_paths` hand-rolls "read the `.fltklsp` file (or use empty text)
  then parse it against the grammar" — `config_text = lsp_path.read_text() if lsp_path is not
  None else ""` followed by a direct call to `load_lsp_config` imported from
  `fltk.lsp.lsp_config`. This re-implements the existence-check + read + parse sequence that
  `plumbing.parse_lsp_config_file` already provides, and bypasses `plumbing.parse_lsp_config`
  (the pure-text wrapper) for the text-parsing step too.
- **Existing function/utility**: `fltk/plumbing.py:274-297` (`parse_lsp_config_file`, which
  checks `config_path.exists()`, raises a curated `FileNotFoundError: LSP config file not
  found: {config_path}`, reads the file, and delegates to `parse_lsp_config` at
  `plumbing.py:258-271`). The design doc itself (§3) says these wrappers exist specifically
  "mirroring `parse_format_config(_file)`" — and the established convention in this codebase is
  that path-taking entry points go through the plumbing wrapper: `fltk/unparse_cli.py:60` calls
  `plumbing.parse_format_config_file(format_spec)` rather than touching `fmt_config` directly.
  `AnalysisEngine.from_paths` is the one new path-taking entry point in this round and is the
  only place in the diff that doesn't follow that convention — grepping the whole package,
  `plumbing.parse_lsp_config`/`parse_lsp_config_file` are exercised only by their own dedicated
  test (`fltk/lsp/test_plumbing_lsp_config.py`), not by any real caller.
- **Consequence**: the two paths already disagree on error message for a missing spec file —
  `plumbing.parse_lsp_config_file` raises `FileNotFoundError: LSP config file not found: <path>`
  while `engine.py`'s `Path.read_text()` raises Python's bare `FileNotFoundError: [Errno 2] No
  such file or directory: '<path>'`. `fltk-highlight`'s `--lsp` option surfaces whichever message
  `AnalysisEngine.from_paths` produces, so the CLI's user-facing error text for a typo'd `--lsp`
  path diverges from the rest of the plumbing layer's curated messages. If `parse_lsp_config_file`
  later gains behavior (e.g. encoding handling, a nicer not-found message, path normalization),
  `engine.py`'s copy won't pick it up since it never calls through the wrapper.

## reuse-2

- **File:line**: `fltk/lsp/highlight_cli.py:30-47` (`_THEME` dict)
- **What's duplicated**: `_THEME` enumerates, as a hardcoded literal, exactly the 16 legend
  member names (`keyword`, `comment`, `string`, `number`, `operator`, `punctuation`, `variable`,
  `parameter`, `property`, `type`, `function`, `enumMember`, `constant`, `macro`, `label`,
  `text`) that the round-1 token legend defines.
- **Existing function/utility**: `TOKEN_LEGEND` in `fltk/lsp/lsp_config.py:45-64` is the
  already-established canonical closed set for the same legend (its own comment says "The
  default classifier and painter (`classify.py`) consume the same legend" — this round's CLI is
  a third consumer that doesn't). `_THEME`'s key set is not derived from or validated against
  `TOKEN_LEGEND`; it is a second, independently-typed enumeration of the identical set.
- **Consequence**: nothing ties the two together, and no test in this round (or the CLI's own
  `test_highlight_cli.py`) asserts `set(_THEME) == TOKEN_LEGEND`. When the legend changes — the
  design doc's own §4.5 notes future legend growth is plausible (LSP-standard vs. custom types)
  — `lsp_config.TOKEN_LEGEND` can be edited without `highlight_cli._THEME` being touched, so a
  new/renamed legend member silently renders uncolored (falls through the `code is None` branch
  in `_render`, `highlight_cli.py:65-67`) with no error, or a removed member leaves dead theme
  entries. This is exactly the kind of maintenance drift a shared source of truth would prevent.

## reuse-3

- **File:line**: `fltk/lsp/test_engine.py:30-35` (`_type_of`) and
  `fltk/lsp/test_dogfood.py:20-25` (`_token_type`)
- **What's duplicated**: both functions are the same "find the single token whose span exactly
  covers `substr` in `text`, assert there is exactly one match, return its `token_type`" logic,
  differing only in parameter/variable names.
- **Existing function/utility**: this exact lookup — `text.index(substr)` → compute `end` →
  filter `tokens` for `t.start == start and t.end == end` → assert `len(matches) == 1` — already
  exists twice in the package: `_token_for` in `fltk/lsp/test_classify_painter.py:34-39` and
  `_token_for` in `fltk/lsp/test_classify.py:32-36` (the latter differing only in returning the
  `Token` rather than its `.token_type`). There is no `conftest.py` or shared test-utility module
  under `fltk/lsp/` to hold a single version of this helper, so this round adds a third and
  fourth copy instead of factoring one out.
- **Consequence**: four independent copies of the same assertion helper across
  `test_classify.py`, `test_classify_painter.py`, `test_engine.py`, and `test_dogfood.py` means a
  future improvement to the matching/error-reporting behavior (e.g. better diagnostics on
  mismatch, tolerance for whitespace-adjacent spans) has to be applied four times to stay
  consistent, and nothing enforces that it will be — the two new copies already show the
  variance starting (one returns `Token`, the other `token_type` directly; error messages already
  differ slightly, "expected exactly one token" vs "expected one token").
