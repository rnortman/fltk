# Implementation log — `.fltklsp` language, loader, classification engine, `fltk-highlight`

Design: `design.md` (frozen). This log is the running implementation record.

## Increment 1 — the `fltklsp.fltkg` grammar + committed generated parser

Established the `.fltklsp` grammar as a committed, buildable parser artifact (§4.1, §5).

- `fltk/lsp/__init__.py`: empty package marker.
- `fltk/lsp/fltklsp.fltkg`: the grammar, transcribed verbatim from design §4.1.
- `Makefile:271-275`: added the `fltklsp` `gencode` step following the unparsefmt precedent
  (`generate --protocol fltk/lsp/fltklsp.fltkg fltklsp fltk.lsp.fltklsp_cst --output-dir
  fltk/lsp`).
- Generated + committed via that step, then `make fix`-normalized:
  `fltk/lsp/fltklsp_cst.py`, `fltklsp_cst_protocol.py`, `fltklsp_parser.py`,
  `fltklsp_trivia_parser.py`. Top rule → `Parser.apply__parse_lsp_spec`. ruff
  check/format-check and pyright clean.
- `fltk/lsp/test_fltklsp_parse.py`: parses via the committed `fltklsp_parser.Parser`
  (mirroring `plumbing.parse_format_config`). Verifies the worked clockwork example
  (verbatim from `fltklsp-spec.md` §4), empty file, whitespace-only, and comments-only all
  parse with full consumption; every individual statement form (global/rule scope, def,
  ref kinds+wildcard, namespace, qualified/literal/multiple anchors, dotted + `none`
  tokens); grammar-level error cases (missing `;`, missing scope token, `rule` inside
  `rule`, unclosed body) via `_parse_fails`; and the design §4.1 flush-colon quirk in both
  directions (flush `label:`/`rule:`-named anchor fails; whitespace-before-colon spelling
  parses). All 24 pass.

## Increment 2 — the analysis grammar transform (`fltk/lsp/analysis.py`, §4.4)

Implemented `prepare_analysis_grammar` (§4.4): the GSM transform that promotes every
`SUPPRESS` disposition to `INCLUDE` so suppressed terminals/subtrees surface as CST
children, plus the up-front `INLINE`-rejection guard.

- `fltk/lsp/analysis.py:19-49` `prepare_analysis_grammar(grammar) -> gsm.Grammar`: scans
  for `INLINE` items first (raises a clean `ValueError`, "grammar uses `!` (inline), not
  supported by the analysis engine (rules: ...)"), then rebuilds every rule with
  `SUPPRESS`→`INCLUDE` and a fresh `identifiers` map via `dataclasses.replace` (resets the
  per-object nil memo, per gsm's single-grammar invariant).
- `fltk/lsp/analysis.py:52-88`: `_find_inline_rules` (uses `gsm.for_each_item`, so the scan
  recurses into `Sequence[Items]` sub-expressions), `_transform_rule`, `_transform_items`,
  `_transform_item` (recurses through sub-expression terms).
- `fltk/lsp/test_analysis.py`: 7 tests, all pass — suppressed literal/regex/subtree surface
  as span/node children (via std-vs-analysis parse comparison); node spans of the standard
  tree are a subset of the analysis tree's with identical root span; transform idempotent
  and non-mutating of the input grammar; `!`-bearing grammars (top-level and nested in a
  sub-expression) rejected with the clean error; sub-expression suppression promoted.
- Uses `SpanKind.SPAN` (`span_protocol`) to discriminate span children from node children
  when walking generated CSTs, per §4.6.

## Increment 3 — config model + CST→LspConfig transform (§4.2)

Implemented the pre-resolution config dataclasses and the CST→model transform (§4.2). No
GSM validation or anchor resolution yet (§4.3, next increment).

- `fltk/lsp/lsp_config.py:39-100`: frozen dataclasses `Anchor`, `ScopeStmt`, `DefStmt`,
  `RefStmt`, `RuleBlock`, `LspConfig` per design §4.2, plus `LSP_STANDARD_MODIFIERS`
  (the LSP 3.17 predefined modifier set from §4.3 rule 6) used to split a scope's dotted
  name into token/modifiers/hints.
- `fltk/lsp/lsp_config.py:181-201` `lsp_cst_to_config(lsp_spec, terminal_src) -> LspConfig`:
  walks `LspSpec` statements, building global `ScopeStmt`s and `RuleBlock`s. A single
  file-order `_IndexCounter` (`:167-178`) is shared across global and rule-block statements,
  giving the unique `stmt_index` §4.6 needs.
- `fltk/lsp/lsp_config.py:103-164`: `_parse_anchor` (qualifier via `maybe_qualifier`,
  literal unquoted through `ast.literal_eval` like `fmt_config._extract_literal_text`),
  `_parse_scope_stmt`, `_parse_def_stmt`, `_parse_ref_stmt` (wildcard `"*"` sentinel vs
  dotted-name kinds), `_parse_rule_block` (accumulates scopes/defs/refs, `is_namespace`).
- Deviation: added `RuleBlock.rule_name_span` (not in the §4.2 sketch) so §4.3's rule-name
  validation can report a source location; consistent with `Anchor.span`.
- `_span_text` mirrors `fmt_config._span_text` (Python span slice vs native `.text()`),
  local copy rather than importing another module's private helper.
- `fltk/lsp/test_lsp_config.py`: 14 tests, all pass — empty/comments-only → empty config;
  single/multiple/qualified/literal anchors; modifiers-vs-hints split; `none` token;
  rule-block scopes/defs/refs; `namespace`; ref wildcard vs kinds; multi-block
  accumulation for one rule; file-order indices across global + block statements. The
  qualified-anchor form is flush (`label:name`), per the §4.1 quirk note.

## Increment 4 — GSM anchor-matching index (foundation for §4.3)

Built the per-rule and grammar-wide anchor-matchable indexes that §4.3's anchor-validation
rules 2-5 (and later anchor resolution) consume. Pure functions, no error raising yet.

- `fltk/lsp/lsp_config.py:270-292`: `RuleIndex` (labels / literals / invoked_rules, all
  `frozenset[str]`) and `GrammarIndex` (per-rule `rules` map plus grammar-wide `rule_names`,
  `all_labels`, `all_literals`).
- `fltk/lsp/lsp_config.py:295-336`: `_index_rule` walks each alternative via
  `gsm.for_each_item` (so `Sequence[Items]` sub-expressions recurse), collecting every
  `Item.label` (explicit + fltk2gsm's implicit rule-name label for unlabeled invocations),
  `Literal` term values, and `Identifier` (invocation) term values. `build_grammar_index`
  assembles the per-rule map and the grammar-wide unions; `rule_names` from
  `grammar.identifiers`.
- Added `from fltk.fegen import gsm` import and a `TYPE_CHECKING` `Mapping` import.
- `fltk/lsp/test_grammar_index.py`: 6 tests, all pass — explicit+implicit label capture,
  literals, invoked-rules-distinct-from-labels (labeled invocation `k:word` keeps `word` in
  invoked_rules), grammar-wide unions, sub-expression recursion, alternative merging.
- ruff check/format-check and pyright clean; existing `test_lsp_config.py` (14) still green.

## Increment 5 — load-time anchor/rule/token validation (§4.3 rules 1-6)

Implemented the validation pass of §4.3: walk a parsed `LspConfig` against a `GrammarIndex`
(increment 4), collect **all** offenses (not fail-fast), and raise one `LspConfigError`
rendering each via `error_formatter.format_source_line`. Anchor *resolution* into
`ResolvedLspConfig` (node_paints / child_matchers) is deferred to a later increment.

- `fltk/lsp/lsp_config.py:415-524`: `LspConfigError(ValueError)` plus `validate_config(config,
  index, terminals)`. Rule 1 (unknown `rule X`), rules 2-3 (`_validate_local_anchor`:
  anchor inside `rule X` matches that rule's labels/invoked-rules/literals, with `label:`/`rule:`
  qualifiers restricting and unqualified taking the union), rules 4-5 (`_validate_global_anchor`:
  global anchor matches the grammar-wide union of rule names and item labels, literals against
  all_literals), rule 6 (`_validate_scope_token`: first segment in the legend, or a sole `none`).
  Rule 7 (def/ref kind vocabulary) is intentionally open — not validated. When a rule block names
  an unknown rule, its anchors are skipped (nothing to match against) but its scope tokens still
  validate.
- `fltk/lsp/lsp_config.py:426-434` `_render_offense`: the stored config spans come from the
  Python-backend parser and carry no source (`terminalsrc.Span(pos, end)` has no `_source`), so
  the source is re-attached via `terminalsrc.Span.with_source(..., SourceText(text, filename))`
  before `format_source_line`. Offenses are sorted by span start/end before rendering so the
  combined message is in source order under a `"N error(s) …"` header.
- `fltk/lsp/lsp_config.py:59` (deviation): added `ScopeStmt.token_span` (the scope dotted-name
  span) so rule 6 can point its caret at the offending token; parallels increment 3's
  `RuleBlock.rule_name_span`. `_parse_scope_stmt` populates it.
- `fltk/lsp/lsp_config.py:40-61` (deviation): defined `TOKEN_LEGEND` (the frozen §4.5 legend,
  minus the `none` pseudo-token) here rather than in classify.py, because rule-6 validation needs
  it now and classify.py does not exist yet; consistent with increment 3 placing the shared
  `LSP_STANDARD_MODIFIERS` vocabulary in this module. classify.py will import it later.
- Added `error_formatter` to the `fltk.fegen.pyrt` import.
- `fltk/lsp/test_lsp_validation.py`: 13 tests, all pass — valid config; rule 1 unknown rule;
  rule 6 unknown token and sole-`none` violation; local label/literal anchors pass+fail; local
  qualifier restriction (label vs rule readings); global union + qualifier restriction; global
  literal; def/ref anchors validated; multi-error collection (count + both messages); error
  message carries line + caret. `test_lsp_config.py` (14) still green.
- ruff check/format-check and pyright clean.

## Increment 6 — anchor resolution into `ResolvedLspConfig` (§4.3)

Implemented the resolution half of §4.3: turn a validated `LspConfig` + `GrammarIndex`
into the classifier's precomputed matcher tables. No painter/engine yet (§4.6 consumes
these; next increment).

- `fltk/lsp/lsp_config.py:440-523`: match types `ByLabel` / `ByLiteralText` / `ByChildRule`
  (+ `Match` union alias), `Paint` (token + modifiers), `Tier` (frozen, `order=True`, fields
  in §4.6 comparison order: source/anchor/block rank + stmt_index — the classifier prepends
  matched-node depth), `NodePaint`, `ChildMatcher`, and `ResolvedLspConfig`
  (`node_paints` keyed by rule name, `child_matchers` keyed by parent rule name,
  `global_child_matchers` for global label/literal scopes). Precedence-rank constants
  `SOURCE_RANK_SCOPE/DEF`, `ANCHOR_RANK_LABEL_LITERAL/RULE_NAME`, `BLOCK_RANK_RULE/GLOBAL`.
- `fltk/lsp/lsp_config.py:526-553` `_resolve_local_anchor`: anchor inside `rule X` → child
  matcher(s); unqualified identifier that is both a label and an invoked rule emits both
  readings (union), matching validation.
- `fltk/lsp/lsp_config.py:555-583` `_resolve_global_anchor`: global scope anchor → node paint
  (rule-name reading) and/or global by-label/by-literal matcher; unqualified rule-and-label
  identifier emits both.
- `fltk/lsp/lsp_config.py:585-627` `resolve_config`: global scopes → node paints + global
  matchers; per rule block, scopes → local child matchers (source_rank SCOPE), `def` →
  declaration-site paint (kind first segment if in `TOKEN_LEGEND`, `declaration` modifier,
  source_rank DEF); `ref`/`namespace` inert (§4.2). Empty per-rule matcher lists are dropped
  so a block contributing nothing (refs-only, non-legend def) leaves no key.
- `fltk/lsp/test_lsp_resolve.py`: 13 tests, all pass — empty config; global rule-name → node
  paint; global label/literal → global matcher; unqualified rule+label union (via implicit
  label on an unlabeled invocation); local scope anchors (label/literal/`rule:` qualifier);
  def paint in-legend adds `declaration`; def kind not in legend emits nothing; ref/namespace
  inert; `none` paint preserved; explicit-scope-outranks-def + later-wins tier ordering;
  multi-block accumulation. Full `fltk/lsp/` suite green (80); ruff + pyright clean.

## Increment 7 — `Token` + default classification layer (§4.5)

Implemented `fltk/lsp/classify.py`'s `Token` type and the default classification layer
(§4.5): a single depth-first walk of an analysis-grammar CST emitting default tokens. No
explicit-paint painter layer (§4.6) and no engine/CLI yet.

- `fltk/lsp/classify.py:24-38` `Token` (frozen, `order=True`): `start`/`end` codepoint
  offsets, `token_type` legend member, `modifiers` tuple — the §4.6 stream element.
- `fltk/lsp/classify.py:70-119` `_TerminalTable`/`_GrammarTables` + `_build_terminal_table`
  / `build_grammar_tables`: per-rule terminal-provenance tables (label→literals/regexes and
  rule-wide literal/regex unions, via `gsm.for_each_item` so sub-expressions recurse) plus
  the CST-`kind.name`→rule map (`naming.snake_to_upper_camel(name).upper()`).
- `fltk/lsp/classify.py:122-172` classification: `_classify_literal_text`
  (word→keyword / punctuation-set→punctuation / else operator), `_classify_regex_text`
  (quote→string / digit→number / identifier→variable / else text), `_classify_span_text`
  (provenance literal-first: labeled span restricted to its label's items, unlabeled/label-less
  falls back to rule-wide unions; classify by matched text shape).
- `fltk/lsp/classify.py:175-201` `_default_intervals`: depth-first walk. Trivia-rule node →
  one `comment` interval over its whole span unless whitespace-only, and **no descent**
  (terminals inside a comment never repaint). Other nodes classify span children and recurse
  into node children; whitespace-only spans emit nothing. Span children are the `Span`
  objects themselves (accessed via `.start`/`.end`, discriminated by `kind == SpanKind.SPAN`).
- `fltk/lsp/classify.py:204-227` `_merge_intervals` + `default_tokens`: sort intervals and
  merge contiguous same-type runs into a sorted, non-overlapping, adjacent-merged token
  stream (modifiers empty in the default layer).
- Deviation: text is sliced from the passed `text` string (not `span.text()`) throughout, so
  classification is independent of span source attachment. Consistent with §4.6's `text` param.
- Note: `default_tokens` rebuilds the grammar tables per call; the §4.7 engine will hold them
  once. `build_grammar_tables` is already factored out so the §4.6 painter and the engine can
  reuse it without rework.
- `fltk/lsp/test_classify.py`: 6 tests, all pass — every default-table row (word/punct/
  operator literals; quote/digit/identifier/other regexes) via one labeled-terminal rule;
  suppressed unlabeled `";"` surfacing + unlabeled provenance; contextual-keyword boundary
  (same spelling `let` as literal→keyword and regex→variable); whitespace-only trivia emits
  nothing; structured `//` comment → single `comment` token, non-descent (no inner repaint);
  token-stream invariants (sorted, non-overlapping, in-bounds, adjacent-merged). Full
  `fltk/lsp/` suite green (86); ruff check/format-check and pyright clean.

## Increment 8 — painter explicit layer + combined `classify` (§4.6)

Implemented the two-layer interval model of §4.6: `classify(tree, grammar, resolved_config,
text) -> list[Token]`, layering explicit `.fltklsp` paints over increment 7's default layer.

- `fltk/lsp/classify.py:212-244` `_matches` / `_explicit_intervals`: one depth-first walk of
  the analysis CST collecting explicit intervals `(start, end, paint, key)` where
  `key = (depth, Tier)`. A whole-node paint (`node_paints[rule]`) is recorded at the node's
  own depth; a child match (`child_matchers[rule]` + `global_child_matchers`, tried against
  each child) at `depth + 1`, so a deeper match outranks a shallower one over their overlap
  (§4.6 rule 3). `ByLabel` compares the child's uppercase label enum name to `name.upper()`;
  `ByLiteralText` compares span source text; `ByChildRule` compares the child node's rule name.
  The walk descends into every node child (including trivia — explicit paints inside trivia
  subtrees still apply, §4.5).
- `fltk/lsp/classify.py:247-266` `_winner_segments`: endpoint sweep over the explicit
  intervals; between consecutive boundaries the max-key interval wins (`none` included — it
  occupies its segment, occluding losers and suppressing defaults, but emits no token);
  adjacent same-paint segments merged.
- `fltk/lsp/classify.py:269-306` `_merge_ranges` / `_subtract` / `_merge_tokens`: coverage
  union of all explicit intervals, per-default-interval subtraction of that coverage (§4.6
  rule 2), and final sort + contiguous-run merge keyed on token type **and** modifiers.
- `fltk/lsp/classify.py:309-339` `classify`: explicit winner tokens (dropping `none`) plus
  default tokens on positions no explicit interval covers, merged.
- `fltk/lsp/classify.py:16` imports `lsp_config` at runtime (for the `Match`/`Paint`/`Tier`
  types and `isinstance` dispatch); no import cycle (`lsp_config` does not import `classify`).
- Deviation: `classify` rebuilds grammar tables per call, same as increment 7's
  `default_tokens`; the §4.7 engine will hold them once. `build_grammar_tables` stays factored
  out for that reuse.
- `fltk/lsp/test_classify_painter.py`: 9 tests, all pass — explicit-over-default,
  `none` occlusion, innermost-wins (inner scope beats outer whole-node paint), rule-block-
  over-global, label-anchor-outranks-rule-name (anchor_rank dominates stmt_index), later-wins,
  def paint + `declaration` modifier + explicit-scope-beats-def-at-same-node, literal-anchor
  paint, and token-stream invariants (sorted, non-overlapping, in-bounds, adjacent-merged on
  type+modifiers, `none` emits nothing). Full `fltk/lsp/` suite green (95); ruff
  check/format-check and pyright clean.

## Increment 9 — `load_lsp_config` top-level loader (§4.3)

Added the single `load_lsp_config(config_text, grammar) -> ResolvedLspConfig` entry point
that ties together the pieces built in increments 3-6.

- `fltk/lsp/lsp_config.py:632-660` `load_lsp_config`: empty/whitespace-only text
  short-circuits to an empty `ResolvedLspConfig` (mirroring `plumbing.parse_format_config`'s
  `plumbing.py:215-216`); otherwise parses via the committed `fltklsp_parser.Parser`
  (`apply__parse_lsp_spec`, full-consumption check like `test_fltklsp_parse._parse`), then
  runs `lsp_cst_to_config` → `build_grammar_index` → `validate_config` → `resolve_config`.
  A parse failure raises `LspConfigError` with the `errors.format_error_message`-rendered
  message; validation offenses raise `LspConfigError` from `validate_config` as before.
- `fltk/lsp/lsp_config.py:16-18`: added `errors` to the `fltk.fegen.pyrt` import and
  imported `Parser` from `fltk.lsp.fltklsp_parser`.
- Deviation: parse failures raise `LspConfigError` (a `ValueError`) rather than a bare
  `ValueError` as `parse_format_config` does, so a single caught exception type covers both
  parse and validation failures of a `.fltklsp` file; `LspConfigError`'s docstring already
  frames it as the load-failure type.
- `fltk/lsp/test_load_lsp_config.py`: 7 tests, all pass — empty/whitespace-only/comments-only
  text → empty config; valid end-to-end config → expected node paint + child matchers;
  validation offense (unknown global anchor), unknown rule block, and grammar parse failure
  each raise `LspConfigError`. Full `fltk/lsp/` suite green (102); ruff check/format-check
  and pyright clean.

## Increment 10 — `plumbing.parse_lsp_config`/`parse_lsp_config_file` wrappers (§3 table)

Added the two `.fltklsp` loader wrappers to `fltk/plumbing.py`, mirroring the
`parse_format_config`/`parse_format_config_file` pair (`plumbing.py:203-254`).

- `fltk/plumbing.py:257-297`: `parse_lsp_config(config_text, grammar)` delegates to
  `lsp_config.load_lsp_config`; `parse_lsp_config_file(config_path, grammar)` is the
  file-read wrapper (raises `FileNotFoundError` on a missing file, like
  `parse_format_config_file`) around `parse_lsp_config`.
- `fltk/plumbing.py:23`: added `from fltk.lsp.lsp_config import ResolvedLspConfig,
  load_lsp_config`. No import cycle (`lsp_config`/`classify` do not import `plumbing`).
- `fltk/lsp/test_plumbing_lsp_config.py`: 5 tests, all pass — empty text; valid text →
  expected child matcher; validation offense raises `LspConfigError`; file wrapper reads +
  parses a `tmp_path` file; missing file raises `FileNotFoundError`.
- ruff check/format-check and pyright clean on both files.

## Increment 11 — `AnalysisEngine` (§4.7)

Implemented `fltk/lsp/engine.py`: the grammar+specs → tokens seam an M2 server will wrap.

- `fltk/lsp/engine.py:27-38` `HighlightResult` (frozen): `tokens: list[Token] | None`,
  `error: str | None` — tokens on success, formatted parser message on parse failure.
- `fltk/lsp/engine.py:41-79` `AnalysisEngine`: `__init__(grammar, resolved_config, *,
  start_rule=None)` generates one analysis parser via
  `plumbing.generate_parser(prepare_analysis_grammar(grammar))` (so `!`-bearing grammars
  raise `ValueError` at construction, per §4.4) and stores the resolved config + start rule.
- `fltk/lsp/engine.py:52-67` `from_paths(grammar_path, lsp_path=None, *, start_rule=None)`:
  `plumbing.parse_grammar_file` + `load_lsp_config` (empty text when no `lsp_path`, giving
  the defaults-only baseline) → `__init__`, per the design §4.7 comment.
- `fltk/lsp/engine.py:69-79` `highlight(text)`: `plumbing.parse_text` (start rule or the
  grammar's first rule) → on failure `HighlightResult(None, parsed.error_message)` (the
  ErrorTracker-formatted message verbatim), on success `classify.classify` over the
  parser's trivia-classified analysis grammar.
- Deviation: constructor takes `(grammar, resolved_config)` and `from_paths` is a thin
  classmethod over it, so the engine is directly unit-testable without temp files (the
  design §4.7 only specifies `from_paths` + `highlight`; this adds a seam, changes no
  behavior).
- Note: `classify` still rebuilds the grammar tables per call; holding them on the engine
  is the already-tracked `TODO(lsp-classify-hotpath)` (see `classify.py`), not done here.
- `fltk/lsp/test_engine.py`: 7 tests, all pass — defaults-only highlight; explicit config
  repaint; parse failure → tokens None + non-empty error; `from_paths` with and without an
  `.fltklsp` file (tmp files); `start_rule=None` first-rule fallback; `!`-grammar rejected
  at construction. Full `fltk/lsp/` suite green (116); ruff check/format-check and pyright
  clean.

## Increment 12 — `fltk-highlight` CLI + `[project.scripts]` entry (§4.8)

Implemented the standalone `fltk-highlight` CLI and registered it as the project's first
console script (§4.8).

- `fltk/lsp/highlight_cli.py`: typer app (`pretty_exceptions_enable=False`, mirroring
  `unparse_cli.py`). `main(FILE, --grammar, --lsp, --rule)` builds an `AnalysisEngine` via
  `from_paths`, reads FILE, and highlights.
  - `highlight_cli.py:29-47` `_THEME`: private, non-configurable 16-color ANSI foreground
    map, one code per legend member (§4.5 legend).
  - `highlight_cli.py:52-74` `_render`: wraps each token's source slice in its ANSI color
    (bold `1;` prefix for the `declaration` modifier), passes unpainted gaps and
    theme-less token types through verbatim; walks the sorted, non-overlapping token stream
    the classifier returns.
  - `highlight_cli.py:77-99` `main`: engine construction wrapped in `except ValueError`
    (covers grammar parse / `!`-grammar / `LspConfigError` load failures, since
    `LspConfigError` is a `ValueError`) → formatted message to stderr, exit 1; a `tokens is
    None` parse failure → engine's error message to stderr, exit 1; success → `_render`
    written to `sys.stdout` (not `typer.echo`, so ANSI survives a non-tty).
- `pyproject.toml`: added `[project.scripts] fltk-highlight =
  "fltk.lsp.highlight_cli:app"` — the project's first console script (§4.8, §9 user
  decision).
- `fltk/lsp/test_highlight_cli.py`: 4 tests, all pass — defaults-only golden ANSI (exact
  stdout: keyword/variable/operator colored, whitespace passed through); explicit-spec
  repaint (`world` becomes `type`, not `variable`); parse-failure exit 1 + empty stdout +
  non-empty stderr; bad `.fltklsp` (unknown rule) load error exit 1 + empty stdout +
  non-empty stderr. Uses `typer.testing.CliRunner` (typer's, not click's — click's
  `CliRunner` cannot invoke a `Typer` app directly).
- Full `fltk/lsp/` suite green (120); ruff check/format and pyright clean.

## Increment 13 — dogfood fixture `fltk/lsp/fltklsp.fltklsp` + its test (§8)

Wrote the dogfood fixture: a `.fltklsp` spec for the `.fltklsp` language itself, addressing
`fltklsp.fltkg`'s own rules/labels/literals, plus a test that loads it against the committed
grammar and highlights a sample `.fltklsp` file (§8 final bullet).

- `fltk/lsp/fltklsp.fltklsp`: rule blocks painting the statement keywords (`rule`/`scope`/
  `def`/`ref`/`namespace`), the `rule_config` rule-name as `type`, the `qualifier`
  contextual keywords (`label`/`rule`), `dotted_name` `part` segments as `property`, and
  `literal` `value` as `string`; plus one global literal anchor list (`";", ":"` →
  `punctuation`). Every anchor resolves against a real rule/label/literal in `fltklsp.fltkg`.
- Deviation from an initial draft: dropped a blanket `rule identifier { scope name:
  variable; }` block. A `name`-label paint on the `identifier` rule sits one depth below
  every `rule_name:`/`part:` label anchor (which match the identifier *invocation* node), so
  it outranks and erases those context paints; and bare identifier names already default to
  `variable`. The fixture leaves them to the default classifier and comments the reason
  inline.
- `fltk/lsp/test_dogfood.py`: 2 tests, both pass — the spec loads against its own grammar
  (expected rule-block + global matcher keys), and highlighting a sample `.fltklsp` paints
  the statement keyword, rule name (`type`), quoted anchor literal (`string`), qualifier
  keyword, dotted scope-token segments (`property`), and a bare identifier anchor (default
  `variable`) each as expected.
- `make check` (full precommit gate: lint, format-check, pyright, pytest, all cargo steps)
  passes. Full `fltk/lsp/` suite green (122).
