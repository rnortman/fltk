# Deep reuse review — round 2 (`fltk-lsp` pygls server)

Base: 9719bab7, HEAD: d9ab841. Design: `docs/adr/2026/07/06-fltklsp-lsp-server/step2/design.md`.

## reuse-1

- **File:line**: `fltk/lsp/test_engine_analyze.py:17-20`
- **What's duplicated**: A private `_engine()` test helper that parses `HELLO_GRAMMAR` via
  `plumbing.parse_grammar`, resolves the `.fltklsp` config via `load_lsp_config`, and constructs an
  `AnalysisEngine` — the exact same three-call sequence, over the exact same shared fixture grammar,
  as the pre-existing helper.
- **Existing function/utility**: `fltk/lsp/test_engine.py:15-18` (`_engine(config_text, *,
  start_rule="top")`), in the same package, built on the same `fltk.lsp.conftest` fixtures
  (`HELLO_GRAMMAR`, `HELLO_LSP`, `token_type_at`) that round 1 already centralized in
  `fltk/lsp/conftest.py` for exactly this kind of cross-test-file sharing.
- **Consequence**: the two helpers have already begun to diverge in this same diff —
  `test_engine.py`'s takes a `start_rule` keyword (default `"top"`) and returns only the engine;
  `test_engine_analyze.py`'s hardcodes `start_rule="top"` and returns `(engine, grammar)` — so a
  future change to engine construction (e.g. a new required constructor argument, or a change to how
  `start_rule` defaulting is tested) has two call sites to update in lockstep with no compiler/test
  linkage between them. `conftest.py` is precisely where this project already puts shared
  test-construction logic (it does so for the grammar text and token lookup helpers); this helper
  should have been added there once and imported by both files.

## reuse-2

- **File:line**: `fltk/lsp/positions.py:73-77` (`LineIndex._column`)
- **What's duplicated**: The utf-16 code-unit-counting formula — `1 + (ord(c) > 0xFFFF)` per
  character, i.e. 2 units for any codepoint beyond the Basic Multilingual Plane, 1 otherwise — and
  the equivalent no-op utf-32 case (`len(prefix)`).
- **Existing function/utility**: `pygls.workspace.position_codec.Utf16.code_units_for_char` /
  `Utf32.code_units_for_char` (via `is_beyond_basic_multilingual_plane`, testing the same `0xFFFF`
  cutoff), in `pygls/workspace/position_codec.py` — part of the `pygls` dependency this very round
  adds (`pyproject.toml` `lsp` extra, §2.5 of the design). `pygls.workspace.TextDocument` already
  wires a `PositionCodec` per document, keyed off the same negotiated `workspace.position_encoding`
  this server reads in `server.py:_encoding()`, with `offset_at_position` / `client_position_at_offset`
  helpers doing the same offset↔position conversion `LineIndex` implements from scratch.
- **Consequence**: this is a narrow, well-scoped duplication (the design at §2.4/§4.5 gives an
  explicit, considered reason not to reuse pygls's *line-splitting* — `TextDocument.lines` is built
  from `str.splitlines(True)`, which recognizes a broader separator set than LSP's three, so
  `LineIndex`'s own line table is justified). But the column-counting subroutine itself carries no
  such justification for being independently reimplemented rather than delegated to
  `pygls.workspace.position_codec.impls[encoding].code_units_for_char`: if a future LSP revision or a
  pygls bugfix changes the BMP-boundary rule (e.g. to handle unpaired surrogates or a spec erratum),
  the fix lands in pygls and this parallel copy silently keeps the old behavior, producing
  column-math bugs that only reproduce with astral input and are easy to miss since both
  implementations currently agree.

## Not flagged (considered and set aside)

- `LineIndex`'s line-start table (bisect over `\n`/`\r\n`/`\r`) vs. `fltk.fegen.pyrt.terminalsrc`'s
  `\n`-only `pos_to_line_col` / `Span.line_col`: the design (§2.4) explicitly evaluates and rejects
  reusing these for exactly this reason, and does not touch them. Not a finding.
- `LineIndex` vs. `pygls`'s full `PositionCodec`/`TextDocument` position machinery as a whole: the
  design (§4.5) explicitly considers pygls's negotiation and states a reason (single encoding owner,
  correctness independent of pygls internals) for keeping all conversion math in `LineIndex`. Only
  the narrow sub-piece in reuse-2 above lacks that same justification.
- The repeated `except (ValueError, OSError): typer.echo(...); raise typer.Exit(1)` shape in
  `server_cli.py` matches `highlight_cli.py` and other in-tree CLIs (`genparser.py`,
  `regex_corpus.py|py`) — this is pre-existing, repo-wide CLI convention rather than something round 2
  invented or could have factored out via an already-existing shared helper.
