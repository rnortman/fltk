# Implementation Log — Round 2 (`fltk-lsp`, M2)

Design: `docs/adr/2026/07/06-fltklsp-lsp-server/step2/design.md` (frozen).

## Increment 1 — non-pygls library foundation

Through-line: the additive, pygls-free library surface the feature logic and server build
on, each piece independently unit-tested. No pygls import anywhere in this increment.

- `fltk/plumbing_types.py:26-35`: added `ParseResult.error_pos: int | None = None`
  (additive, defaulted — no existing caller changes).
- `fltk/plumbing.py:193-208`: `parse_text` failure branch now sets `error_pos` —
  `error_tracker.longest_parse_len` when `>= 0`, else `result.pos` when truthy, else `0`
  (§4.4). The no-such-rule early return (`plumbing.py:189`) leaves it `None`.
- `fltk/lsp/engine.py`: added `ParseErrorInfo` (message + offset) and `DocumentAnalysis`
  (tree/tokens/error) frozen dataclasses; `AnalysisEngine.analyze()` (former `highlight`
  body, now carrying `parsed.cst` and `parsed.error_pos`, `RecursionError`→`offset=None`);
  rewrote `highlight()` as a thin delegating wrapper; `__init__` stores original grammar
  and precomputes `_trivia_kind_names`; added `source_grammar` and `trivia_kind_names`
  read-only properties (§4.3).
- `fltk/lsp/positions.py` (new): `PositionEncoding` enum + `LineIndex` — LSP-conformant
  line table (`\n`, `\r\n`, lone `\r`), codepoint-offset ↔ LSP `(line, character)` in
  utf-16/utf-32, clamping, `end_position` (§4.5). No pygls types.
- Tests: `test_positions.py` (17 cases: separators, empty/trailing-newline, astral utf-16
  vs utf-32, round trips, clamping), `test_plumbing_error_pos.py` (4 cases), and
  `test_engine_analyze.py` (8 cases incl. `RecursionError` via monkeypatch, `highlight`
  delegation pin, both properties). 33 pass with `test_engine.py`; full `plumbing`/`parse`
  suite green.
- Deviation: `test_plumbing_error_pos.py` uses self-contained labeled grammars rather than
  `conftest.HELLO_GRAMMAR` — the standard-disposition parser suppresses unlabeled terminals,
  so HELLO's unlabeled `word` regex yields an empty CST node class and fails codegen (that
  grammar is only ever fed to the analysis transform elsewhere).

## Increment 2 — pure feature logic `features.py` + LSP packaging

Through-line: the entire pure, pygls-free feature layer (§4.6) — the second self-contained
unit atop increment 1's `DocumentAnalysis`/`LineIndex`/`PositionEncoding`, plus the packaging
(§2.5/§4.2) that makes lsprotocol types available to it and its tests. All logic here is
testable without a running server; the next increment becomes protocol wiring over these
functions.

- `fltk/lsp/features.py` (new): `SEMANTIC_TOKEN_TYPES` (16 legend members, fixed wire order)
  and `SEMANTIC_TOKEN_MODIFIERS` (10 standard modifiers, fixed order);
  `encode_semantic_tokens(tokens, line_index, enc) -> list[int]` (LSP relative 5-int encoding,
  multi-line tokens split at line boundaries via `_line_segments`, columns/lengths in the
  negotiated encoding, unknown token type skipped / unknown modifier dropped);
  `folding_ranges(tree, trivia_kind_names, line_index) -> list[FoldingRange]` (pre-order
  `_walk_nodes`, multi-line nodes only, trivia kinds get `FoldingRangeKind.Comment`, dedup by
  `(start_line, end_line)` keeping outermost); `selection_ranges(tree, offsets, line_index,
  enc) -> list[SelectionRange]` (`_spans_containing` root-to-innermost descent incl. terminal
  spans, identical spans collapsed for strict widening, zero-width range for an uncontained
  offset). Imports `lsprotocol.types` but not pygls.
- `pyproject.toml`: added `[project.optional-dependencies] lsp = ["pygls>=2,<3"]` and
  `pytest-lsp` to the `test` group (§2.5/§4.2); the latter transitively provides
  pygls 2.1.1 + lsprotocol 2025.0.0 in the test env so `test_features.py` imports resolve.
- `fltk/lsp/test_features.py` (new, 15 cases): legend set-equality vs
  `TOKEN_LEGEND`/`LSP_STANDARD_MODIFIERS`; hand-computed relative encodings (two lines,
  within-line deltas, multi-line split, token ending exactly at a newline, modifier bits +
  unknown-modifier drop, unknown-type skip, astral utf-16 vs utf-32); folding (multi vs
  single line, trivia Comment kind, dedup outermost, plus a real engine-tree smoke test);
  selection (terminal-span head + strict widening + collapsed identical ancestors,
  end-of-document zero-width, multiple offsets). Full suite green (2777 passed, 1 skipped).
- Deviation (design §2.5): the extra pins `pygls>=2,<3`, not the design's literal
  `pygls>=1.3,<2`. §2.5 explicitly delegates the version choice to implementation time
  ("verifies the current stable ... a bump is contained to server.py/server_cli.py"); at
  implementation time pygls 2.x is the stable line and `pytest-lsp` (the §6 end-to-end test
  tool) requires pygls>=2, so `<2` and pytest-lsp cannot co-resolve. lsprotocol's
  `FoldingRange`/`SelectionRange`/`Range`/`Position` surface used here is stable across the
  bump.
- Note: `features.py` imports lsprotocol at module load, so it requires the `lsp` extra —
  consistent with it being server-only code (only `server.py`, next increment, imports it);
  `fltk-highlight` and the rest of `fltk.lsp` never import it, so non-LSP consumers are
  unaffected.

## Increment 3 — pygls server wiring + CLI (completes the design)

Through-line: the protocol layer turning increments 1–2's pure library into a running
`fltk-lsp`. This is the last design item; after it every §-item in the §3 deliverables table
has a log entry.

- `fltk/lsp/server.py` (new, §4.7–4.8): `FltkLanguageServer(LanguageServer)` +
  `create_server(engine, formatter_config, renderer_config, *, start_rule) ->
  FltkLanguageServer`. `_GoodAnalysis` (frozen, bundles version+line_index+tree+tokens+
  encoded_tokens computed against one text) and `_DocState`. `_constrain_pygls_encodings()`
  at module load narrows `pygls.capabilities._SUPPORTED_ENCODINGS` to `{utf-16, utf-32}` so
  pygls's own negotiation is the single encoding owner; `_encoding()` reads the advertised
  `workspace.position_encoding` back (§4.5). `ThreadPoolExecutor(max_workers=1)` analysis on
  `_analyze_blocking`; `_analysis_for` single-flights per URI; push = didOpen-immediate +
  didChange-debounce (`_DEBOUNCE_SECONDS = 0.2`, cancellable asyncio task); pull handlers
  await `_ensure_analyzed`. Diagnostics via `_publish` (one-codepoint range from
  `error.offset`, `offset=None`→0,0). Stale policy: `_serveable` returns `last_good`
  (current on success, else prior). Handlers: semantic tokens full (`_GoodAnalysis.
  encoded_tokens`) + range (offset-filtered re-encode against the *matching* line index),
  folding, selection over `features.py`; formatting via lazy `_ensure_format_pipeline`
  (standard-disposition parser+unparser from `engine.source_grammar`, memoized-on-failure)
  and `_format_blocking` (parse-guard → unparse/render in a broad `except` → verify-reparse
  → whole-doc `TextEdit` or `[]`), logs deferred to the loop thread. `TODO(lsp-analysis-
  watchdog)` at `_analyze_blocking`.
- `fltk/lsp/server_cli.py` (new, §4.1): typer app; lazy `from fltk.lsp.server import
  create_server` with actionable `fltk[lsp]` ImportError message; `AnalysisEngine.from_paths`;
  `--rule` validated against `engine.source_grammar` rule names (lists valid on miss);
  `--fmt` parsed at startup; `--width`/`--indent` (defaults 80/2) → `RendererConfig`;
  `start_io()`. `if __name__ == "__main__": app()` so tests launch it via `-m`.
- `pyproject.toml`: `[project.scripts] fltk-lsp = "fltk.lsp.server_cli:app"`.
- `TODO.md`: `lsp-analysis-watchdog` entry (§2.3).
- `fltk/lsp/test_data/greet.{fltkg,fltklsp,fltkfmt}`: fixture language — greetings + quoted
  strings (astral-capable) + multi-line `block_comment` (trivia) + line comment; `.fltklsp`
  repaints `greeting.name`→type, `note.text`→string; `.fltkfmt` preserves comments and gives
  a spacing-visible canonical form.
- `fltk/lsp/test_server.py` (13 tests): 3 pytest-lsp end-to-end via `python -m
  fltk.lsp.server_cli` — encoding negotiation (utf-32, utf-16-only, utf-8-first→utf-16 with
  emitted-token agreement, astral utf-16 length=6 vs utf-32=5); didOpen clean diag+tokens;
  breaking edit → one error diag at col 6 + stale tokens still served; fixing edit; folding
  Comment kind on the block comment; selection widening; formatting reformattable→one edit
  (exact canonical) / idempotent→`[]` / unparseable→None; didClose+reopen. Plus an in-process
  unit test pinning the format-build-failure memoization (`generate_unparser` monkeypatched to
  raise → called once, both requests `None`, both log).
- `fltk/lsp/test_server_cli.py` (6 tests): missing/invalid grammar, invalid `.fltklsp`,
  invalid `.fltkfmt`, unknown `--rule` (lists valid rules), pygls-missing via `__import__`
  hook → stderr + exit 1.
- Deviation: encoding single-owner is implemented by mutating pygls's module-level
  `_SUPPORTED_ENCODINGS` frozenset (design §4.5's "constrain pygls's supported-encodings set …
  if its API permits" — pygls exposes no injection point, so the module attribute is set
  directly). `choose_position_encoding` reads that name at call time, so the constraint takes
  effect; verified by the utf-8-first test.
- Deviation: over the 500–700 target (server.py ~360 LOC + CLI ~55 + tests ~330); naturally
  indivisible — the design's `done` requires the server, its CLI, and their end-to-end tests
  together, and the CLI is meaningless without the server it launches.
- Full `make check` Python lane green: `ruff check .`, `ruff format --check`, `pyright`
  (0 errors), `uv run pytest` (2796 passed, 1 skipped).
