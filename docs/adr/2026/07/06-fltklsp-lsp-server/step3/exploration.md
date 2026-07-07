# Exploration: state of `.fltklsp` / FLTK LSP tooling at HEAD (76124f9)

Context for this survey: the ADR docs (`README.md`, `brainstorm.md`, `fltklsp-spec.md`) and the
step1/step2 design docs are **advisory/directional**, per the requester's explicit framing —
"NO DECISIONS HAVE BEEN MADE." Where a design doc's plan differs from what's actually in the
tree, this doc cites the code, not the doc. M0 (`.fltklsp` grammar/loader/classifier), M1
(`fltk-highlight`), and M2 (`fltk-lsp` pygls server) are implemented and merged (commits
a17ba80, 76124f9). Nothing below is a recommendation or a diagnosis.

## 1. `.fltklsp` machinery (M0)

### Grammar and generated parser
- Grammar source: `fltk/lsp/fltklsp.fltkg` (25 lines). Top rule `lsp_spec := , statement* ;`;
  `statement := scope_stmt | rule_config`; `rule_config := "rule" : rule_name:identifier , "{" , ( rule_statement , )* , "}" , ;`.
  Statement forms: `scope_stmt`, `def_stmt`, `ref_stmt`, `namespace_stmt` (`fltklsp.fltkg:6-12`).
  `anchor := ( qualifier . ":" )? . name:identifier | literal ;` with `qualifier := label:"label" | rule:"rule" ;`
  (`fltklsp.fltkg:15-16`) — `qualifier` is its own rule with labeled literals (not an inline
  sub-expression) specifically so an unlabeled literal isn't silently suppressed from the CST
  (design rationale at `step1/design.md:150-155`).
- Generated + committed artifacts: `fltk/lsp/fltklsp_cst.py` (2404 lines),
  `fltklsp_cst_protocol.py` (1031 lines), `fltklsp_parser.py` (1379 lines),
  `fltklsp_trivia_parser.py` (1410 lines) — produced by `fltk.fegen.genparser generate` per the
  `Makefile`'s `gencode` target (mirrors the `unparsefmt` precedent, per `step1/design.md:441-445`).
- Known documented parse quirk: an anchor literally named `label` or `rule` flush against a
  colon (`scope label:comment;`) fails to parse because the optional qualifier group commits
  once it consumes `label:` (PEG `e?` doesn't backtrack after success); `scope label : comment;`
  (space before colon) works. Pinned by `test_fltklsp_parse.py:164-176`
  (`test_flush_label_named_anchor_fails`, `test_flush_rule_named_anchor_fails`,
  `test_spaced_label_named_anchor_parses`, `test_spaced_rule_named_anchor_parses`).

### Config model and GSM validation (`fltk/lsp/lsp_config.py`, 664 lines)
- Pre-resolution dataclasses: `Anchor` (`qualifier`/`name`/`literal`/`span`), `ScopeStmt`,
  `DefStmt`, `RefStmt`, `RuleBlock`, `LspConfig` (`lsp_config.py:67-116`).
- `lsp_cst_to_config(lsp_spec, terminal_src) -> LspConfig` (`lsp_config.py:230-246`): walks the
  CST into the model; `_parse_scope_stmt` splits a scope's dotted name into `token` (first
  segment) plus `modifiers`/`hints` (`lsp_config.py:160-176`), filtering against
  `LSP_STANDARD_MODIFIERS` (the 10 LSP 3.17 standard modifier names, `lsp_config.py:27-40`).
  `TOKEN_LEGEND` is the frozen 16-member scope-token legend (`lsp_config.py:45-64`).
- `GrammarIndex`/`RuleIndex` (`lsp_config.py:249-317`, built by `build_grammar_index`): per-rule
  `labels`/`literals`/`invoked_rules` plus grammar-wide unions, computed by `_index_rule` walking
  `gsm.for_each_item` (recurses through `Sequence[Items]` sub-expressions, `gsm.py:291-302`).
  `TODO(lsp-rule-surface-index)` (`lsp_config.py:280-281`, also `classify.py:72-73`) notes this
  walk parallels `classify._build_terminal_table` and both should unify into one rule-surface
  index (tracked in `TODO.md`, not yet done).
- `validate_config(config, index, terminals)` (`lsp_config.py:404-439`): collects **every**
  offense (not fail-fast) and raises one `LspConfigError` (a `ValueError` subclass,
  `lsp_config.py:320-325`) whose message renders each offense via
  `error_formatter.format_source_line` (file:line:col + caret). Rules implemented:
  rule-block name must exist (`_validate_local_anchor` skipped, unknown-rule error added
  instead, `lsp_config.py:418-423`); local anchors must match a label/invoked-rule/literal of
  the block's rule (`_validate_local_anchor`, `:353-377`); global anchors match the union of
  rule names / labels / literals (`_validate_global_anchor`, `:380-401`, **union semantics** —
  a deliberate deviation from the spec's ambiguity-error rule, because fltk2gsm gives every
  unlabeled rule invocation an implicit label equal to the rule name, making "is both a label
  and rule name" the norm, not the exception; documented as a compatibility commitment in
  `step1/design.md:79-92`); scope-token first segment must be in `TOKEN_LEGEND` or be `none`
  (`_validate_scope_token`, `:340-350`). `def`/`ref` kind vocabulary is deliberately unvalidated
  (open vocabulary, `lsp_config.py:409`).
- `resolve_config(config, index) -> ResolvedLspConfig` (`lsp_config.py:599-636`): builds the
  classifier's matcher tables — `node_paints` (whole-node paints from global rule-name anchors),
  `child_matchers` (per-parent-rule matcher lists), `global_child_matchers`. Precedence is
  encoded in a `Tier` (`source_rank, anchor_rank, block_rank, stmt_index`, `lsp_config.py:494-501`)
  with named rank constants (`SOURCE_RANK_SCOPE=2`, `SOURCE_RANK_DEF=1`,
  `ANCHOR_RANK_LABEL_LITERAL=1`, `ANCHOR_RANK_RULE_NAME=0`, `BLOCK_RANK_RULE=1`,
  `BLOCK_RANK_GLOBAL=0`, `lsp_config.py:486-491`). `def` statements contribute a paint only
  when the kind's first segment is in `TOKEN_LEGEND`, with modifier `("declaration",)`
  (`lsp_config.py:625-628`) — def-site paint is live now, not deferred to M4
  (`step1/design.md:538-542`, a called-out user decision).
- `load_lsp_config(config_text, grammar) -> ResolvedLspConfig` (`lsp_config.py:639-664`) is the
  one-call parse→transform→validate→resolve entry point; empty/whitespace text short-circuits to
  an all-empty `ResolvedLspConfig` (`:646-647`). Wrapped by `plumbing.parse_lsp_config` /
  `parse_lsp_config_file` (`fltk/plumbing.py:265-304`), mirroring
  `parse_format_config`/`parse_format_config_file` (`plumbing.py:211-262`).

### The analysis-grammar transform (`fltk/lsp/analysis.py`, 81 lines)
- `prepare_analysis_grammar(grammar) -> gsm.Grammar` (`analysis.py:19-40`): promotes every
  `Disposition.SUPPRESS` item to `INCLUDE` recursively (`_transform_item`, `:72-81`), so terminals
  that `fltk2gsm.Cst2Gsm.visit_item` (`fltk/fegen/fltk2gsm.py:108-128`, defaulting unlabeled
  literal/regex items to `SUPPRESS` at `:117-122`) would otherwise omit from the CST
  (`gsm2parser.py:848` gates child emission on disposition) now surface as unlabeled span
  children, with identical spans/language. `INLINE`-bearing grammars are rejected up front with
  a clean `ValueError` (`_find_inline_rules`/`_rule_uses_inline`, `:43-59`), because
  `gsm2parser.py:828-830` raises a bare `NotImplementedError` on any `INLINE` item and the Rust
  generator has the same gap.
- Tested by `test_analysis.py`: suppressed literal/regex/subtree surfacing as children with
  unchanged spans (`:46-64`), node-span equivalence to the standard parser
  (`test_node_spans_unchanged`), idempotence (`test_transform_is_idempotent`), the clean
  `INLINE` rejection and its subexpression recursion (`:95-121`), and that the *original*
  grammar object's dispositions are untouched (`test_original_grammar_disposition_unchanged`).

### Classification engine (`fltk/lsp/classify.py`, 399 lines)
- `Token` (`start`, `end`, `token_type`, `modifiers`, frozen/ordered, `classify.py:25-36`).
- Default layer: `_build_terminal_table`/`build_grammar_tables` precompute per-rule
  `label_literals`/`label_regexes`/`literals`/`regexes` (`:47-111`); `_classify_span_text`
  resolves a terminal span by provenance first (labeled span restricted to its label's items,
  else rule-wide unions), literal match before regex, and regex provenance is tested
  *positionally* (`pattern.match(full_text, start)` ending exactly at `end`) rather than
  `fullmatch` on the isolated slice, so lookahead/lookbehind patterns resolve the way the parser
  actually matched them (`:133-159`, exercised by
  `test_classify.py:66-79 test_lookahead_regex_span_classifies_by_positional_provenance`).
  `_classify_literal_text`/`_classify_regex_text` implement the default table
  (word-shaped literal → keyword; punctuation set `()[]{},;:.` → punctuation; else → operator;
  quote-started regex text → string; digit-started → number; identifier-shaped → variable; else
  text) (`:114-130`). `_default_intervals` (`:176-201`) emits at most one `comment` interval per
  trivia node (`rule.is_trivia_rule`) and does **not** descend into it (so nested trivia rules
  and terminals-inside-comments never repaint); whitespace-only spans emit nothing.
- Explicit painter layer: `_explicit_intervals` (`:248-283`) walks the tree collecting
  `(start, end, Paint, (depth, Tier))` intervals from `node_paints`/`child_matchers`/
  `global_child_matchers`; `_winner_segments` (`:286-311`) sweeps interval endpoints picking the
  max-key paint per segment (`none` occupies the segment, occluding losers, but emits no token).
  `TODO(lsp-classify-hotpath)` flags this sweep as O(n²) (rescans all intervals per boundary
  pair) and notes `classify()` walks the tree twice (explicit pass + default pass) — recorded at
  `classify.py:293-294, 393-394` and in `TODO.md`, not yet addressed.
- `classify(tree, grammar, resolved_config, text, *, tables=None) -> list[Token]`
  (`:363-399`) composes both layers: explicit paints win over their whole span; positions with
  no explicit coverage fall back to defaults via `_subtract`. Output invariants (sorted,
  non-overlapping, adjacent-same-type merged, within `[0, len(text))`) are enforced by
  `_merge_tokens` (`:345-360`) and asserted directly in tests
  (`test_classify.py:108-121 test_token_stream_invariants`,
  `test_classify_painter.py:133-149`).
- Default classifier is exercised standalone via `default_tokens(...)` (`:204-218`), covered by
  `test_classify.py:33-44 test_default_table_rows` and the contextual-keyword-boundary test
  (`:54-64`, same spelling as option-key literal vs. identifier resolves differently by
  provenance, not spelling — the brainstorm's clockwork case study's central claim).

## 2. `fltk-highlight` (M1) and `fltk-lsp` (M2)

### `fltk-highlight` (`fltk/lsp/highlight_cli.py`, 117 lines)
- Typer app `fltk-highlight --grammar lang.fltkg [--lsp lang.fltklsp] [--rule START_RULE] FILE`
  (`:91-96`), registered as `[project.scripts] fltk-highlight = "fltk.lsp.highlight_cli:app"`
  (`pyproject.toml:31`).
- `main()` builds an `AnalysisEngine.from_paths(...)`, reads the file, calls
  `engine.highlight(text)`; on `HighlightResult.tokens is None` prints the formatted error to
  stderr and exits 1 (`:99-111`).
- `_render(text, tokens)` (`:64-88`) wraps each token's source slice in a fixed 16-color ANSI
  SGR code from `_THEME` (`:31-48`, one entry per legend member), bold for the `declaration`
  modifier, unpainted text passed through. `_sanitize` (`:53-61`) escapes control/bidi
  characters via `errors.escape_control_chars` per line (preserving `\n`) before emission —
  untrusted-input hardening against terminal-escape injection.
- Tests: `test_highlight_cli.py` — defaults-only run, explicit-spec repaint, parse-failure exit
  1, bad `--lsp` exit 1, def-site bold rendering, missing grammar/lsp/input-file exit paths,
  and a `test_theme_covers_the_legend` pin that `_THEME` has an entry for every `TOKEN_LEGEND`
  member.

### `fltk-lsp` (M2)
- CLI: `fltk/lsp/server_cli.py` (71 lines). `fltk-lsp --grammar ... [--lsp] [--fmt] [--rule]
  [--width 80] [--indent 2]`, registered as `fltk-lsp = "fltk.lsp.server_cli:app"`
  (`pyproject.toml:32`). Startup sequence (`server_cli.py:44-67`): lazy `from fltk.lsp.server
  import create_server` inside a `try`/`except ImportError` that prints
  `"fltk-lsp requires the 'lsp' extra: pip install 'fltk[lsp]'"` and exits 1 (`:45-48`);
  `AnalysisEngine.from_paths(grammar, lsp, start_rule=rule)`; if `--rule` given, validates it
  against `engine.source_grammar.rules` names, else lists valid rules and exits 1 (`:52-57`);
  `plumbing.parse_format_config_file(fmt)` if `--fmt` given; any `ValueError`/`OSError` in this
  block → formatted message to stderr, exit 1 (`:59-63`); builds `RendererConfig(max_width=width,
  indent_width=indent)` and `create_server(...).start_io()` (`:65-67`).
- Packaging: `pyproject.toml:28` declares `lsp = ["pygls>=2,<3"]` as an optional extra (core
  `dependencies` unaffected); `pytest-lsp` is in the `test` dependency group (`pyproject.toml:49`).
  Note: the step2 design doc's §2.5 anticipated `pygls>=1.3,<2` as "the current stable line" and
  explicitly deferred the exact pin to implementation time (`step2/design.md:114-117`) — the
  installed pin is `pygls>=2,<3`, i.e. the implementer verified 2.x as current at build time,
  per the design's own contingency.
- Server module: `fltk/lsp/server.py` (511 lines), importing pygls at module load (so
  `server_cli` must import it lazily). Key pieces:
  - `_constrain_pygls_encodings()` (`:58-83`), run at import time (`:83`), monkeypatches
    `pygls.capabilities._SUPPORTED_ENCODINGS` to `{Utf16, Utf32}` (excluding `utf-8`, which
    `LineIndex` doesn't implement), raising `RuntimeError` up front if that private attribute
    is missing (pygls upgrade guard).
  - `_GoodAnalysis` (`:86-99`) / `_DocState` (`:102-109`): per-URI state; `_GoodAnalysis`
    snapshots `line_index`/`tree`/`tokens`/`encoded_tokens` all from the *same* successful
    parse, ruling out cross-version coordinate mixing by construction.
  - `FltkLanguageServer(LanguageServer)` (`:112-427`): one `ThreadPoolExecutor(max_workers=1)`
    (`:139`) serializes all analysis/formatting off the asyncio loop.
    `_analyze_blocking` (`:174-191`) runs `engine.analyze`, builds a `LineIndex`, and (only on
    success) `features.encode_semantic_tokens` — all on the worker thread. `_store` (`:193-224`)
    guards against out-of-order versions and against a stale epoch (see `drop`, `:327-337`,
    which bumps `self._epochs[uri]` so a late-completing analysis for a since-closed doc is
    discarded). `_analysis_for`/`_ensure_analyzed` (`:226-252`) implement per-URI single-flight
    plus debounce (`schedule_debounced`/`_debounced_analyze`, `:297-325`,
    `_DEBOUNCE_SECONDS = 0.2`, module constant).
  - Diagnostics: `_publish` (`:256-284`) builds one `Diagnostic` from `ParseErrorInfo.offset`
    (zero-length range at 0,0 when `offset is None`) or clears diagnostics on success.
  - Stale-serving: `_serveable(state) -> state.last_good` (`:341-343`) is the single accessor
    every pull feature reads through — current-or-last-good, never a hard failure blanking the
    file (ADR D6).
  - Formatting pipeline: `_ensure_format_pipeline` (`:347-371`) lazily builds a
    **standard-disposition** parser (`plumbing.generate_parser(engine.source_grammar)` — the
    pre-analysis-transform grammar, never the analysis variant, per the comment at `:362-365`)
    plus an unparser, memoizing a build failure (`self._fmt_failed`) so later requests short
    -circuit without retrying codegen. `_format_blocking` (`:373-417`) runs parse →
    unparse → render → **verify-reparse** (parse the rendered output again) before ever
    returning an edit; any failure at any step degrades to `None` + a logged message, never a
    raw exception or a partial edit. Client `FormattingOptions` are ignored; geometry comes
    from the CLI's `--width`/`--indent` (`RendererConfig`).
  - `create_server(...)` (`:429-511`) wires `didOpen`/`didChange`/`didClose`,
    `semanticTokens/full` and `/range` (the range handler bisects the sorted, non-overlapping
    `good.tokens` by `end`/`start`, `:481-482`), `foldingRange`, `selectionRange`, and
    `textDocument/formatting`.
- Position math: `fltk/lsp/positions.py` (119 lines). `PositionEncoding` enum (`UTF16`/`UTF32`,
  deliberately no `UTF8`). `LineIndex(text)` builds a line-start table recognizing `\n`,
  `\r\n`, and lone `\r` (unlike `TerminalSource.pos_to_line_col`, which is `\n`-only per
  `step2/design.md:97-101`); `offset_to_position`/`position_to_offset`/`line_of`/
  `line_bounds`/`end_position` all clamp out-of-range inputs rather than raising.
- Feature translation: `fltk/lsp/features.py` (229 lines), pure functions, no server state.
  `SEMANTIC_TOKEN_TYPES`/`SEMANTIC_TOKEN_MODIFIERS` (`:33-66`) are ordered tuples pinned
  set-equal to `lsp_config.TOKEN_LEGEND`/`LSP_STANDARD_MODIFIERS` by
  `test_features.py:61-76`. `encode_semantic_tokens` (`:114-137`) does the standard 5-int
  relative encoding, splitting multi-line tokens at line boundaries unconditionally
  (`_line_segments`, `:88-111`). `folding_ranges` (`:148-170`) walks non-span nodes
  (`_walk_nodes`, `:140-145`), one fold per multi-line node, `FoldingRangeKind.Comment` when
  `node.kind.name in trivia_kind_names`, deduping identical `(start_line, end_line)` keeping
  the first (outermost). `selection_ranges` (`:204-229`) builds the innermost-to-outermost
  chain via `_spans_containing` (`:173-191`, includes terminal `Span` children as the
  innermost element), collapsing same-span ancestors (LSP requires strictly-widening ranges).

## 3. FLTK plumbing surfaces the LSP code leans on

- `fltk/plumbing.py` (441 lines): `parse_grammar`/`parse_grammar_file` (`:37-88`);
  `generate_parser(grammar, *, capture_trivia=True) -> ParserResult` (`:91-167`) execs a
  freshly-generated Python CST module + parser class in memory (registered under
  `sys.modules[f"fltk_grammar_{id(grammar)}"]` only after success, `:157-159`) — there is **no**
  `rust_cst_module=` parameter; the Rust path is offline codegen only (see §4 below).
  `parse_text(parser_result, text, rule_name=None) -> ParseResult` (`:170-208`): on failure,
  computes `error_pos` from `parser.error_tracker.longest_parse_len` if `>= 0`, else
  `result.pos` if `result` is truthy, else `0` (`:199-205`) — this `error_pos` plumbing was
  added in M2 (`ParseResult.error_pos: int | None = None`,
  `fltk/plumbing_types.py:26-35`) specifically to give diagnostics a source position; the
  no-such-start-rule early return (`:189`) leaves `error_pos` at its default `None`.
  `parse_lsp_config`/`parse_lsp_config_file` (`:265-304`) wrap `lsp_config.load_lsp_config`.
  `generate_unparser`/`generate_unparser_source`/`unparse_cst`/`render_doc` (`:307-441`) are the
  formatting pipeline the server's `_ensure_format_pipeline`/`_format_blocking` call.
- `fltk/fegen/pyrt/span_protocol.py`: `SpanProtocol` (`runtime_checkable` Protocol, `:56-146`)
  exposes `start`/`end` (codepoint indices), `kind` (`SpanKind.SPAN` discriminant),
  `text()`/`text_or_raise()`, `merge`/`intersect`, and `line_col()` returning a
  `LineColPosProtocol | None` (`line`, `col`, `line_span`, `:24-53`). Both backends (pure-Python
  `terminalsrc.Span` and, if present, `fltk._native.Span`) satisfy it structurally.
- `fltk/fegen/pyrt/errors.py`: `ErrorTracker` (`:24-49`, `longest_parse_len` +
  `expected_context: list[ParseContext]`, tracked via `fail_literal`/`fail_regex`);
  `format_error_message(tracker, terminals, rule_name_lookup)` (`:126-152`) renders the
  `file:line:col` + caret + expected-token-by-rule block every parse-failure message in this
  codebase (grammar, `.fltklsp`, target-language parses) shares. `escape_control_chars`
  (`:96-123`) is the control/bidi-escaping routine `highlight_cli._sanitize` reuses, pinned
  cross-backend against `crates/fltk-cst-core/src/escape.rs`.
- Unparse/formatter pipeline: `plumbing._assemble_unparser_module` (`plumbing.py:307-333`)
  chains `gsm.add_trivia_rule_to_grammar` → `gsm.classify_trivia_rules` →
  `gsm2unparser.generate_unparser` → `compiler.compile_class` → exec. `render_doc` uses
  `Renderer(RendererConfig)` (`fltk/unparse/renderer.py`, `RendererConfig` defaults
  `indent_width=4, max_width=80` per `step2/design.md:141-142`; the CLI/server override with
  their own `--width`/`--indent` defaults of 80/2, matching `fltk-unparse`'s existing CLI
  defaults referenced in `unparse_cli.py:37-38,125`, not directly re-read here).
- Trivia handling: `gsm.classify_trivia_rules(grammar)` (`gsm.py:348-...`) sets
  `Rule.is_trivia_rule` by reachability from the synthesized `_trivia` rule
  (`TRIVIA_RULE_NAME = "_trivia"`, `gsm.py:18`); `gsm.add_trivia_rule_to_grammar` synthesizes one
  when the source grammar has none (relevant to clockwork, which the brainstorm notes has no
  `_trivia` rule at all — its `is_trivia_rule` flag never gets set on `doc`, matching the
  brainstorm's case-study finding). `classify.default_tokens`/`classify.classify` require the
  **trivia-classified** grammar (`ParserResult.grammar`, not the raw pre-`generate_parser`
  grammar) — `AnalysisEngine.__init__` builds `classify.build_grammar_tables` from
  `self._parser_result.grammar` (`engine.py:85-86`), not `self._source_grammar`.
- Native/pyo3 parser module hooks: confirmed absent as a `plumbing.generate_parser` parameter.
  The Rust path is exclusively offline, consumer-driven codegen via
  `fltk.fegen.genparser` (`genparser.py`) subcommands `gen-rust-cst` (`:329-...`),
  `gen-rust-parser` (`:570-...`), `gen-rust-unparser` (`:596-...`) — each writes a `.rs` file the
  consumer's own `Cargo`/maturin build compiles into a separate cdylib; there is no in-process
  "load a compiled pyo3 module for this grammar" call in `fltk.plumbing` today. This confirms
  the step1 design's §2.3 correction (ADR D4's `rust_cst_module=` citation does not exist in
  code) and step2's M5 delta note (`step2/design.md:563`) that a native fast path would need a
  new `genparser` flag to build from the analysis-grammar variant specifically.

## 4. ADR's M3/M4/M5 and where their seams currently sit in code

- **M3 (prefix-CST exposure)**: `AnalysisEngine.analyze` (`engine.py:128-162`) currently returns
  `tree=None` on any parse failure — `plumbing.parse_text` (`plumbing.py:170-208`) returns
  `ParseResult(None, text, False, error_msg, error_pos=...)` on failure; there is no partial/CST
  fragment carried anywhere in that path today. `step2/design.md:31-37` records this as an
  explicitly-open factual question ("whether `ApplyResult` carries a *useful* partial CST on
  failure") not resolved in round 2. The Rust side's analogous discard point is
  `fully_consumed` (`crates/fltk-fmt-cli/src/lib.rs:88` and its call sites,
  e.g. `:351`) — a boolean gate on `parser.pos` vs. source length, with no partial-tree
  extraction visible in that crate either. `ParseResult.error_pos` (`plumbing_types.py:26-35`,
  populated in `parse_text`, `plumbing.py:199-205`) is called out in step2 as "the first half of
  the surface M3 needs" (`step2/design.md:555-556`); a partial tree would be the second half.
- **M4 (defs/refs/document symbols/namespace scoping)**: the grammar, config model, and
  validation for `def`/`ref`/`namespace` statements are fully implemented and load-bearing now
  (`lsp_config.DefStmt`/`RefStmt`/`RuleBlock.is_namespace`, `lsp_config.py:88-109`;
  `_validate_local_anchor` runs against `def`/`ref` anchors too, `lsp_config.py:430-433`;
  `resolve_config` turns `def` into a declaration-site `Paint`, `lsp_config.py:625-628`) — but
  `ref` and `namespace` are semantically inert past validation: `resolve_config`'s docstring says
  so explicitly ("`ref` and `namespace` are inert in round 1 and contribute no matchers",
  `lsp_config.py:604-606`), and `test_lsp_resolve.py:105-110`
  (`test_ref_and_namespace_are_inert`) pins exactly that. No symbol-table type, `SymbolKind`
  mapping, or `documentSymbol`/`definition`/`references`/`rename` LSP feature exists anywhere in
  `fltk/lsp/`. `DocumentAnalysis` (`engine.py:52-64`) carries only `tree`/`tokens`/`error` — no
  symbol-table field yet; `step2/design.md:559-562` records M4 as adding one "next to `tokens`"
  without disturbing the state model.
- **M5 (resolver plugin API / native fast path)**: no resolver-plugin loading mechanism, no
  cross-file reference handling, and no native-analysis-parser wiring exist in `fltk/lsp/`.
  `AnalysisEngine.__init__` (`engine.py:77-91`) always builds its parser via
  `plumbing.generate_parser(prepare_analysis_grammar(grammar))` — a pure-Python exec'd parser,
  unconditionally. The seam step1/step2 point at for a future native path is exactly this one
  call plus the `genparser` gap noted in §3 above (a `genparser` flag that emits Rust from the
  *analysis*-grammar variant does not exist yet, `step1/design.md:69-77`, `step2/design.md:563`).
- **Recorded, not-yet-acted-on follow-ups** in `TODO.md` (all still open at HEAD): `TODO(lsp-cst-text-helpers)`
  (span-text/identifier/literal extraction duplicated across `lsp_config`/`fmt_config`/
  `unparse.pyrt`); `TODO(lsp-test-parse-helper)` (test-only duplication of the
  parse-then-config-load sequence in `test_lsp_config.py`/`test_lsp_validation.py`, noted as
  resolved in spirit by `plumbing.parse_lsp_config` but the tests haven't been migrated to it);
  `TODO(lsp-analysis-watchdog)` (`server.py`'s single-worker executor has no wall-clock/
  cancellation bound on a runaway parse — `server.py:180-184`); `TODO(lsp-start-rule-dedup)`
  (`server.py` threads `start_rule` as a second copy alongside the engine's own,
  `server.py:136-138`); `TODO(lsp-classify-hotpath)` (`classify.py`'s O(n²) interval sweep and
  double tree traversal, `classify.py:293-294,393-394`); `TODO(lsp-rule-surface-index)`
  (`lsp_config._index_rule` and `classify._build_terminal_table` should unify,
  `lsp_config.py:280-281`, `classify.py:72-73`).

## 5. Existing tests: location, shape, coverage

All colocated under `fltk/lsp/` per repo convention (`test_*.py` alongside the module under
test), 18 test modules, ~4,000 lines of test code total (see file sizes in the directory
listing). Shared fixtures: `fltk/lsp/conftest.py` (`HELLO_GRAMMAR`/`HELLO_LSP` mini-language,
`build_hello_engine`, `token_for`/`token_type_at` helpers reused across engine/classify tests)
and `fltk/lsp/test_data/` (`greet.fltkg`/`greet.fltklsp`/`greet.fltkfmt`, the fixture language
`test_server.py`/`test_server_cli.py` drive over a real subprocess).

By module (test function names enumerated in the survey; not reproduced in full here):

- `test_fltklsp_parse.py` (24 tests): grammar-level parse acceptance/rejection — the worked
  clockwork example, empty/whitespace/comments-only files, every statement form, syntax-error
  cases (missing `;`, `rule` inside `rule`, unclosed body), and the flush-qualifier quirk (both
  spellings).
- `test_grammar_index.py` (6 tests), `test_lsp_config.py` (17 tests),
  `test_lsp_validation.py` (14 tests), `test_lsp_resolve.py` (12 tests),
  `test_load_lsp_config.py` (7 tests): the `lsp_config.py` pipeline stage-by-stage — index
  building, CST→dataclass fidelity (multi-block accumulation, statement-index ordering,
  modifier/hint splitting, literal unquoting incl. escape errors), validation (every rule's
  pass/fail case, multi-error collection, message file:line:col), resolution (tier construction,
  union semantics, def-paint-in/out-of-legend), and the one-call `load_lsp_config` entry point.
- `test_analysis.py` (7 tests): the analysis-grammar transform, described in §1 above.
- `test_classify.py` (7 tests) + `test_classify_painter.py` (10 tests): default-table coverage,
  contextual-keyword boundary, positional regex provenance, trivia non-descent, and the full
  painter precedence matrix (explicit-over-default, innermost-wins, rule-block-over-global,
  anchor-rank, later-wins, `none` occlusion, def-paint interaction) plus token-stream invariant
  checks in both files.
- `test_engine.py` (8 tests) + `test_engine_analyze.py` (7 tests): `AnalysisEngine`/`analyze`/
  `highlight` — defaults-only, explicit-config, parse-failure, `from_paths` with/without a
  `.fltklsp`, start-rule defaulting, engine reuse across calls, `INLINE`-grammar rejection at
  construction, structured-error offset on failure, `RecursionError` → `offset=None`,
  `highlight()`-delegates-to-`analyze()` regression pin, and the two new read-only properties
  (`source_grammar`, `trivia_kind_names`).
- `test_highlight_cli.py` (9 tests): end-to-end CLI behavior described in §2 above.
- `test_dogfood.py` (3 tests): `fltklsp.fltklsp` (the spec-for-the-spec-language) loads against
  `fltklsp.fltkg` and highlights a sample `.fltklsp` file, including def/ref/namespace/qualifier
  constructs.
- `test_plumbing_lsp_config.py` (5 tests), `test_plumbing_error_pos.py` (4 tests): the
  `fltk.plumbing` wrapper functions (`parse_lsp_config[_file]`, `ParseResult.error_pos` on
  success/mid-input-failure/early-success-without-consumption/unknown-rule).
- `test_positions.py` (13 tests): `LineIndex` — all three separators, empty text, no trailing
  newline, astral columns (utf-16 vs utf-32), offset↔position round trips, every clamp case.
- `test_features.py` (16 tests): semantic-token legend set-equality, delta encoding, multi-line
  splitting (incl. a token ending exactly at a newline), utf-16 vs utf-32 lengths on astral
  text, folding (multi-line-only, dedup-keep-outermost, over a real engine tree), selection
  (innermost-span head, strictly-widening chain, multiple offsets).
- `test_server_cli.py` (6 tests): missing/invalid grammar/`.fltklsp`/`.fltkfmt`, unknown
  `--rule` message, and a simulated missing-pygls import path.
- `test_server.py` (25 tests, both `pytest_lsp`-driven subprocess tests and in-process unit
  tests against `_fixture_server()`): full protocol round trips over the real `fltk-lsp`
  command — encoding negotiation (utf-32-offered, utf-16-only, utf-8-first-must-be-answered-
  with-something-else), clean/broken document diagnostics and stale-token serving on a breaking
  edit, folding, selection, formatting (reformats + idempotent, unparseable-doc → no edits,
  build-failure memoization, render-exception degrades to `None`, formatting-without-`--fmt`
  uses defaults), close/reopen, plus lower-level unit tests for `_store`'s version-ordering
  guard, drop-then-late-analysis discard, debounce reschedule/cancel bookkeeping, and
  single-flight analysis sharing.
- Build/regen: `Makefile`'s `gencode` target includes the `fltklsp.fltkg` → `fltk.lsp.*`
  generation step (referenced, not independently re-verified in this pass beyond the design
  doc's citation of `Makefile:267-270`); the committed generated files listed in §1 are the
  output of that step.

## Open factual questions

- Whether a partial/prefix CST is obtainable from the existing `ApplyResult`/parser internals on
  a failed parse (the concrete blocker for M3) was flagged as unresolved in `step2/design.md:31-37`
  and this pass did not find any code path (Python or the `fully_consumed`-gated Rust CLI) that
  currently extracts one — but a from-scratch determination of *whether the parser machinery
  could support it* would require reading the packrat/memo internals (`fltk/fegen/pyrt/memo.py`
  and `gsm2parser.py`'s generated-method shape) in more depth than this pass covered.
- The Makefile's exact `gencode` invocation for `fltklsp.fltkg` (cited by the step1 design at
  `Makefile:267-270`) was not independently re-read in this pass; only the resulting committed
  files were inspected.
