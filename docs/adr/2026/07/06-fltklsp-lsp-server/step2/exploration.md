# Exploration — round 2 context (state of round 1 at HEAD, dd442340 / a17ba80)

Reminder carried forward verbatim from the task: the ADR/brainstorm/spec docs under this
directory are advisory only — "NO DECISIONS HAVE BEEN MADE. This was a brainstorming
session. Everything is malleable at this point." Round-1 code (already implemented and
committed) is the authoritative source for what exists; `step1/design.md` is the
already-implemented round's design record and is more authoritative than the ADR/spec/
brainstorm docs but is still a doc, not code — line-number citations below point at current
code, checked directly, not copied from that doc.

## 1. Round-1 code surface — `fltk/lsp/`

Files (generated parser/CST artifacts vs. hand-written modules):

| File | Nature | Role |
|---|---|---|
| `fltk/lsp/fltklsp.fltkg` | hand-written grammar source | defines the `.fltklsp` language |
| `fltk/lsp/fltklsp_parser.py`, `fltklsp_trivia_parser.py`, `fltklsp_cst.py`, `fltklsp_cst_protocol.py` | generated (committed) | parser + CST node classes for `.fltklsp`, produced by `genparser` (mirrors the `unparsefmt` precedent) |
| `fltk/lsp/fltklsp.fltklsp` | hand-written, dogfood fixture | a `.fltklsp` spec for the `.fltklsp` language itself |
| `fltk/lsp/lsp_config.py` | hand-written | CST→model transform, load-time GSM validation, anchor resolution |
| `fltk/lsp/analysis.py` | hand-written | analysis-grammar transform (`SUPPRESS`→`INCLUDE`) |
| `fltk/lsp/classify.py` | hand-written | default classifier + explicit-paint painter engine |
| `fltk/lsp/engine.py` | hand-written | `AnalysisEngine` / `HighlightResult` — the seam |
| `fltk/lsp/highlight_cli.py` | hand-written | `fltk-highlight` typer CLI |
| `fltk/lsp/conftest.py`, `test_*.py` | tests | colocated per-repo convention |

### `AnalysisEngine` (`fltk/lsp/engine.py`)

```python
class AnalysisEngine:
    def __init__(self, grammar: gsm.Grammar, resolved_config: ResolvedLspConfig, *, start_rule: str | None = None) -> None
    @classmethod
    def from_paths(cls, grammar_path: Path, lsp_path: Path | None = None, *, start_rule: str | None = None) -> AnalysisEngine
    def highlight(self, text: str) -> HighlightResult
```
(`engine.py:47-98`). Construction (`__init__`, line 47) does the one-time expensive work:
`plumbing.generate_parser(prepare_analysis_grammar(grammar))` (line 54) then
`classify.build_grammar_tables(self._parser_result.grammar)` (line 55) — both cached on the
instance. `highlight` (line 77) calls `plumbing.parse_text(...)` then `classify.classify(...)`,
catching `RecursionError` from pathologically deep input (line 96) and reporting it as a
parse failure rather than propagating. `HighlightResult` (lines 26-36) is
`tokens: list[Token] | None, error: str | None` — `tokens is None` on parse failure, with
`error` carrying `parsed.error_message` verbatim (the `ErrorTracker`-formatted string from
`plumbing.parse_text`, itself from `errors.format_error_message`).

This is the exact object the docstring (lines 1-8) says "an LSP server wraps": engine stays
in codepoint offsets and returns tokens or a formatted error string; "stale-token serving,
debouncing, and `Diagnostic`-shaped errors are server policy layered on top."

### `classify.py` — `Token`, legend, tables

`Token` (lines 25-36): frozen, `order=True` dataclass, fields `start: int, end: int,
token_type: str, modifiers: tuple[str, ...]` — codepoint offsets, "same coordinate space as
`SpanProtocol`." `token_type == "none"` never appears in output (suppression is applied, not
emitted).

Two entry points:
- `default_tokens(tree, grammar, text, *, tables=None) -> list[Token]` (line 204) — the
  built-in default table alone, no `.fltklsp`.
- `classify(tree, grammar, resolved_config, text, *, tables=None) -> list[Token]` (line 363)
  — explicit paints layered over defaults. Both return "a sorted, non-overlapping,
  adjacent-merged token stream ... all within `[0, len(text))`" (docstrings, lines 212-213,
  378-379).

`build_grammar_tables(grammar) -> _GrammarTables` (line 101) precomputes, once per grammar:
per-rule `_TerminalTable` (literal/regex provenance, keyed by uppercased label or rule-wide
union) and `kind_to_rule: Mapping[str, gsm.Rule]` keyed by uppercased UpperCamel class name
(`node.kind.name`). `AnalysisEngine.__init__` builds this once (line 55) and threads it into
every `classify` call via the `tables=` kwarg — the seam a future caller reuses across many
`highlight()` calls on the same grammar.

Two known efficiency TODOs left in place, not fixed in round 1:
- `TODO(lsp-classify-hotpath)` at `classify.py:293` — `_winner_segments` rescans all
  intervals per boundary pair, O(n²); a sweep-line would be O(n log n).
- `TODO(lsp-classify-hotpath)` at `classify.py:393` — `classify` walks the tree twice
  (once for explicit intervals, once for `_default_intervals`); could be folded into one walk.
- `TODO(lsp-rule-surface-index)` at `classify.py:72` and `lsp_config.py:280` — the per-rule
  item walk in `_build_terminal_table` and `_index_rule` duplicate each other; flagged for a
  unified rule-surface index, not built yet.

### `lsp_config.py` — config model, validation, resolution

Pipeline, in one call: `load_lsp_config(config_text: str, grammar: gsm.Grammar) ->
ResolvedLspConfig` (line 639). Steps: parse with the generated `Parser`
(`fltklsp_parser.Parser`) → `lsp_cst_to_config` (CST→plain-dataclass model, line 230) →
`build_grammar_index(grammar)` (line 304) → `validate_config(config, index, terminals)`
(line 404, raises `LspConfigError` collecting *every* offense, not fail-fast) →
`resolve_config(config, index) -> ResolvedLspConfig` (line 599). Empty/whitespace-only text
short-circuits to an all-empty `ResolvedLspConfig` (lines 646-647) — "the built-in defaults
alone are a usable baseline."

Model dataclasses (pre-resolution): `Anchor` (qualifier/name/literal/span, line 67),
`ScopeStmt` (line 78), `DefStmt` (line 88), `RefStmt` (line 95), `RuleBlock` (rule_name +
scopes/defs/refs + `is_namespace: bool`, line 102), `LspConfig` (global_scopes +
rule_blocks, line 112).

`TOKEN_LEGEND` (lines 45-64) is the frozen round-1 legend: `keyword, comment, string,
number, operator, punctuation, variable, parameter, property, type, function, enumMember,
constant, macro, label, text` — 16 members; the `none` pseudo-token is validated separately
(`_validate_scope_token`, line 340) and is not a legend member.
`LSP_STANDARD_MODIFIERS` (lines 27-40) is the fixed LSP 3.17 modifier set used to split a
scope statement's trailing dotted-name segments into `modifiers` vs. `hints` (the CLI drops
hints; nothing else currently consumes them).

Resolved output, `ResolvedLspConfig` (lines 521-533):
```python
node_paints: Mapping[str, tuple[NodePaint, ...]]           # rule name -> whole-node paints
child_matchers: Mapping[str, tuple[ChildMatcher, ...]]     # parent rule name -> child matchers
global_child_matchers: tuple[ChildMatcher, ...]            # label/literal matchers, any parent
```
`Match = ByLabel | ByLiteralText | ByChildRule` (line 470); `Paint(token: str, modifiers:
tuple[str, ...])` (line 474); `Tier(source_rank, anchor_rank, block_rank, stmt_index)`
(line 495, `order=True`) is the resolution-time half of the classifier's precedence key —
`classify._explicit_intervals` prepends tree depth to make the full key.

`GrammarIndex`/`RuleIndex` (lines 250-317) are the anchor-matchable surfaces of a grammar
(labels, literals, invoked_rules per rule; grammar-wide unions) — built fresh here; this is
the "headline feature, not inherited" load-time validation (see §2 for why `.fltkfmt` has
none of this to reuse).

`resolve_config` (line 599) is explicit that `ref` and `namespace` contribute **no**
matchers: "`ref` and `namespace` are inert in round 1 and contribute no matchers; `def`
contributes a declaration-site paint when its kind's first segment is a legend token."
(lines 603-605). Concretely, `resolve_config`'s loop over `block.rule_blocks` (lines
616-630) reads `block.scopes` and `block.defs` only; `block.refs` and `block.is_namespace`
are never read anywhere in this function.

### `analysis.py` — the analysis-grammar transform

`prepare_analysis_grammar(grammar: gsm.Grammar) -> gsm.Grammar` (line 19): promotes every
`Disposition.SUPPRESS` item to `INCLUDE` (recursing through `Sequence[Items]`
sub-expressions and every rule), so "the resulting grammar matches the identical language
with identical spans, but its CST contains a child for every terminal and subtree the
parser consumed." Raises `ValueError` up front (not letting a raw `NotImplementedError`
escape) if any item carries `Disposition.INLINE` (`!`), "not supported by the analysis
engine" (lines 29-33, `_find_inline_rules`/`_rule_uses_inline`, lines 43-59). This exists
because `fltk2gsm.Cst2Gsm.visit_item` (`fltk/fegen/fltk2gsm.py:114-121`) defaults an
unlabeled `Literal`/`Regex` item to `SUPPRESS` (only labeled items, sub-expressions, and rule
invocations — which get an implicit label equal to the invoked rule name — default to
`INCLUDE`), and the normal runtime parser omits `SUPPRESS` items from the CST entirely, so
keyword/punctuation terminals would otherwise never reach the classifier as spans.

### `highlight_cli.py` — the CLI

`fltk-highlight --grammar lang.fltkg [--lsp lang.fltklsp] [--rule START_RULE] FILE`
(registered in `pyproject.toml`: `[project.scripts] fltk-highlight =
"fltk.lsp.highlight_cli:app"`). Builds an `AnalysisEngine.from_paths(...)`, calls
`.highlight(text)`, and on success writes ANSI-colored output to stdout via `_render` (line
64); a fixed private `_THEME: dict[str, str]` (lines 31-48) maps each of the 16 legend
members to a 16-color ANSI code, `declaration` modifier renders bold (line 83), unthemed
token types and unpainted gaps pass through uncolored/unescaped-content but still run
through `_sanitize`/`escape_control_chars` (line 61) to neutralize control/bidi bytes in
untrusted workspace text. Errors (`LspConfigError`, other `ValueError`s, `OSError`) print to
stderr and exit 1 (lines 99-111).

## 2. What round 1 explicitly deferred or left inert

Per `step1/design.md:39-41` ("Explicitly out of round 1") and cross-checked against code:

- **pygls server (M2)** — no pygls import or dependency anywhere. `pyproject.toml`
  `dependencies = ["astor", "typer"]` (no `pygls`); `grep -rn pygls` across the repo (source,
  toml, lock) returns nothing. `AnalysisEngine` is pure library code with no protocol
  handling, no LSP types, no request/response loop.
- **Prefix-CST exposure (M3)** — `plumbing.parse_text` (`fltk/plumbing.py:170-201`)
  discards the parse result whenever `not result or result.pos != len(terminals.terminals)`
  (line 193), returning `ParseResult(None, text, False, error_msg)` (line 199) — even when
  `result` itself is a truthy `ApplyResult(pos, result)` (`fegen/pyrt/memo.py:69-71`)
  carrying a partially-built CST, that CST is thrown away, not surfaced. There is no
  `fully_consumed()` method or similarly named API anywhere in the codebase (grepped); the
  ADR's phrasing referencing it is descriptive, not a literal symbol to find. `AnalysisEngine.highlight`
  (`engine.py:89-92`) inherits this all-or-nothing behavior unchanged.
- **Symbol tables / document symbols / rename / go-to-def (M4)** — the grammar, parser,
  model, validation, and resolution for `def`/`ref`/`namespace` statements all exist and are
  exercised by round 1's tests, but no symbol table, `SymbolKind` mapping, or ref-site paint
  is built anywhere. `resolve_config` (`lsp_config.py:599-636`) is the single place these
  would be consumed and it explicitly does not read `block.refs` or `block.is_namespace`.
  `DefStmt.kind` is used only to derive a paint (`kind[0]` checked against `TOKEN_LEGEND`,
  `lsp_config.py:626-628`); no other segment of `kind`, and no `RefStmt.kinds` at all, is
  read anywhere in `fltk/lsp/`.
- **Resolver plugin (M5)** — no resolver hook, plugin-loading mechanism, or cross-file
  concept exists in `fltk/lsp/` (grepped for `resolver`/`Resolver`, zero hits outside the
  advisory docs).
- **HTML output for the CLI** — `highlight_cli.py` only ever writes ANSI escapes
  (`_render`, `_THEME`); no HTML renderer, no `--format` flag. `Token` itself carries no
  color/format opinion, so per `step1/design.md:436-437` "it bolts on later."
- **UTF-16 position conversion** — `Token.start/end` and everything upstream (`SpanProtocol`,
  `LineColPosProtocol`) are documented and implemented purely in codepoint offsets
  (`span_protocol.py:31, 42, 47, 67-72`). No UTF-16 code-unit conversion exists anywhere in
  `fltk/lsp/` or `fegen/pyrt/`.
- **TextMate export** — no exporter of any kind exists; this is `fltklsp-spec.md` open
  question 3, unaddressed in code.

## 3. Existing FLTK infrastructure the next milestones would build on

### `fltk.plumbing` (`fltk/plumbing.py`)

- `parse_grammar(text) -> gsm.Grammar` / `parse_grammar_file(path)` (lines 37-88).
- `generate_parser(grammar: gsm.Grammar, *, capture_trivia: bool = True) -> ParserResult`
  (lines 91-167): generates and `exec`s a fresh Python CST module + parser class per call
  (module name `fltk_grammar_{id(grammar)}`, registered in `sys.modules` only after success,
  line 159); returns `ParserResult(parser_class, cst_module, cst_module_name, grammar,
  capture_trivia)` (`plumbing_types.py:14-22`). This is what every `AnalysisEngine`
  construction pays for once.
- `parse_text(parser_result, text, rule_name=None) -> ParseResult` (lines 170-201): builds a
  fresh `terminalsrc.TerminalSource`, invokes `apply__parse_{rule_name}(0)` (defaulting to
  the grammar's first rule), and on success returns `ParseResult(result.result, text, True)`
  — the CST is `result.result`, an `ApplyResult`'s payload.
- `parse_format_config(text) -> FormatterConfig` / `parse_format_config_file(path)` (lines
  204-255) — parses `.fltkfmt` text via the generated `unparsefmt_parser.Parser`, then
  `fmt_cst_to_config`.
- `parse_lsp_config(text, grammar)` / `parse_lsp_config_file(path, grammar)` (lines
  258-297) — thin wrappers around `lsp_config.load_lsp_config`, already used by
  `AnalysisEngine.from_paths`.
- `generate_unparser_source` / `generate_unparser(grammar, cst_module_name,
  formatter_config=None) -> UnparserResult` (lines 300-386): builds an unparser class from
  `gsm2unparser.generate_unparser`, `exec`s it, returns
  `UnparserResult(unparser_class, grammar, formatter_config, trivia_config)`
  (`plumbing_types.py:36-42`). Requires the parser to have been generated with
  `capture_trivia=True`.
- `unparse_cst(unparser_result, cst, terminals, rule_name=None) -> Doc` (lines 388-419) and
  `render_doc(doc, config=None) -> str` (lines 422-433) — the parse→unparse→render pipeline
  a document-formatting milestone would drive, already used end-to-end elsewhere in the
  codebase (not re-verified here beyond signatures).

### `ErrorTracker` / error formatting (`fltk/fegen/pyrt/errors.py`)

`ErrorTracker[RuleId]` (lines 25-49): tracks `longest_parse_len: int` and
`expected_context: list[ParseContext]` (each `ParseContext(rule_id, token_type, token)`,
`token_type: TokenType.LITERAL | REGEX`). `fail_literal`/`fail_regex` implement
furthest-failure semantics: a failure at a position behind the tracked max is dropped; one at
the exact max position appends to the expected-set; one past the max resets the set (lines
29-49) — the "expected token sets" a completion/diagnostics milestone could reuse directly.
`format_error_message(tracker, terminals, rule_name_lookup) -> str` (lines 126-152) renders
the `Syntax error at line N col M: ... ^ ... Expected: From rule "X": LITERAL: '...'` message
every current parse-failure path (`plumbing.parse_grammar`, `parse_text`,
`parse_format_config`, `lsp_config.load_lsp_config`) already emits verbatim. There is no
separate `error_formatter.format_source_line`-based per-offense mechanism reused here for
target-file diagnostics beyond what `.fltklsp`'s own validation (`lsp_config._render_offense`,
line 328) uses for config errors — the *target document's* parse errors go through
`format_error_message`, not `format_source_line`.

### `SpanProtocol` (`fltk/fegen/pyrt/span_protocol.py`)

`SpanProtocol.line_col(self) -> LineColPosProtocol | None` (lines 127-133) and
`line_col_or_raise` (lines 135-138) return 0-based codepoint `line`/`col`/`line_span`
(`LineColPosProtocol`, lines 25-53) — "None when the span is sourceless, has a negative
start, or has a start that exceeds the source length." Both `start`/`end` (lines 65-72) are
explicitly documented as codepoint indices "on both backends" (Python `terminalsrc.Span` and
the native Rust `Span`, unified as `AnySpan` at lines 149-157). No UTF-16 code-unit
conversion is defined anywhere on this protocol or its backends.

### The unparse/formatter pipeline (`fltk/unparse/`)

- `.fltkfmt` grammar: `fltk/unparse/unparsefmt.fltkg`, generated parser/CST at
  `unparsefmt_parser.py`/`unparsefmt_cst.py`.
- `fmt_config.py`: `FormatterConfig` (dataclass with `anchor_configs`, `rule_configs`,
  `trivia_config`, etc., lines 160-166) and `fmt_cst_to_config` (CST→model transform, referenced
  by `plumbing.parse_format_config`). `get_anchor_config` (lines 168-236) merges global +
  rule-specific `AnchorConfig`s by string key (`f"{position}:{selector_type.value}:
  {selector_value}"`, line 186) and **returns `None` silently** (lines 197-198) when neither
  config has an entry — confirmed: there is no GSM-anchor-validation call anywhere in this
  method or elsewhere in `fmt_config.py`, and no raise on an anchor that resolves to nothing.
  This directly grounds `step1/design.md §2.2`'s claim that `.fltklsp`'s load-time anchor
  validation (`lsp_config.validate_config`) is new work, not something reused from
  `.fltkfmt`.
- `gsm2unparser.py`: `generate_unparser` builds the unparser class `plumbing.generate_unparser`
  execs; consumed by the same formatting pipeline a document-formatting milestone would
  drive (`unparse_cst` → `render_doc`).
- `Renderer`/`RendererConfig` (`fltk/unparse/renderer.py`, imported into `plumbing.py:27`) and
  `resolve_spacing_specs` (`fltk/unparse/resolve_specs.py`, `plumbing.py:28`) round out the
  Doc-combinator → text rendering step `unparse_cst` calls into.

### pygls dependency status

Confirmed absent: `pyproject.toml`'s only runtime `dependencies` are `["astor", "typer"]`
(no lockfile in the repo to separately check); a repo-wide `grep -rn pygls` over `*.py`,
`*.toml` returns zero matches.

## 4. Roadmap options as the docs frame them, plus code facts bearing on each (no scope choice made here)

The ADR's numbered milestones (`README.md:102-115`, "Incremental plan") and design.md §7's
per-milestone "roadmap foundation" notes (`step1/design.md:474-497`) describe intent, not
committed decisions (per the carried-forward reminder). Restated here purely as the docs'
framing, annotated with code facts:

**M2 — `fltk-lsp` (pygls): diagnostics, semantic tokens, folding ranges, selection ranges,
document formatting, stale-tokens-on-failure.** Per the ADR (`README.md` D4, lines 59-71):
"a generic pygls-based server invoked as `fltk-lsp --grammar lang.fltkg [--lsp
lang.fltklsp] [--fmt lang.fltkfmt]`," with an optional `--native-module` fast path via a
consumer-built pyo3 module. Design.md §7 (`step1/design.md:476-479`) notes a delta versus the
ADR: "the server holds two parser instances" — one analysis-grammar parser (via
`AnalysisEngine`, `SUPPRESS`→`INCLUDE`) for highlighting, and a second, standard-disposition
parser (via plain `plumbing.generate_parser`) for the formatting pipeline, "a detail the ADR
didn't have." Code facts: no pygls dependency exists yet (§3 above); `AnalysisEngine.highlight`
already returns exactly `(tokens, error)` shaped for `Diagnostic`/semantic-token translation;
`ErrorTracker`'s furthest-failure `expected_context` is available for diagnostics beyond the
single top-line message `format_error_message` currently renders; `SpanProtocol.line_col()`
supplies codepoint line/col directly usable for LSP `Position` after a units decision (see M3
below re: UTF-16); document formatting would reuse `plumbing.parse_format_config` +
`generate_unparser` + `unparse_cst` + `render_doc` unchanged.

**M3 — prefix-CST exposure in `fltk.plumbing` (both backends), for degraded-mode
highlighting past the last-good parse.** Per the ADR (D6, lines 92-100): "expose the
successfully-parsed prefix CST that `plumbing.parse_text` ... currently discard[s], so only
the region after the error degrades" — explicitly scoped to *not* include generated
error-recovery parsing ("a future, much larger project"). Design.md §7
(`step1/design.md:480-481`) frames this as "purely a change inside `highlight()`'s parse
step; `classify` already works on any subtree." Code fact: confirmed in `plumbing.parse_text`
(§2 above) — the discard point is a single `if` (lines 193-199); whatever `result.result`
holds when `result` is truthy but `pos != len(terminals.terminals)` is currently thrown away
rather than returned.

**M4 — defs/refs: document symbols, go-to-def, find-references, same-file rename,
`namespace` scoping.** Per `fltklsp-spec.md` §3 (lines 92-124, "phase 2 syntax, reserved
now"): `def`/`ref`/`namespace` statements, a `SymbolKind` mapping table keyed on `kind`'s
first dotted segment, prefix-matching `ref` kinds against `def` kinds, `namespace` rules
introducing lexical scopes with outward-walking resolution, wildcard `ref ...: *;` for pure
rename/find-references participation, and "defs/refs also feed highlighting: a def site with
no explicit `scope` inherits its kind's token type plus the `declaration` modifier; a
resolved ref inherits the defining kind's token type" (lines 118-120) — of which only the
def-site-paint half is implemented (§2 above). Design.md §7 (`step1/design.md:482-486`)
states "the grammar, config model, validation, and anchor resolution for
`def`/`ref`/`namespace` all exist after round 1; M4 adds symbol-table construction, the
`SymbolKind` mapping, and ref-site paint — no `.fltklsp` file written for round 1 ever
changes," and separately flags that "M4's design round may revise" the def-site-paint
semantics decided in round 1 (§9, `step1/design.md:538-542`, e.g. `declaration` modifier
placement). Code facts: `DefStmt`/`RefStmt`/`RuleBlock.is_namespace` are fully parsed,
validated (`_validate_local_anchor`), and carried in the pre-resolution `LspConfig` model
(`lsp_config.py:88-109`); `resolve_config` reads only `block.defs` for paint purposes and
never `block.refs`/`is_namespace` (confirmed by direct read of the function body, lines
616-630).

**M5 — resolver plugin API for cross-file navigation; optional native-module acceleration
documentation; evaluate a Rust `fltk_lsp_main!` tier if demand exists.** Per the ADR (D5,
lines 84-90): cross-file resolution (the example given is clockwork's
`use @repo::path::Type` with aliases) is explicitly out of `.fltklsp`'s declarative scope,
"handled by an optional per-language Python resolver hook loaded by the server. Without a
resolver, features degrade gracefully to same-file behavior." Design.md §2.3
(`step1/design.md:69-77`) records a correction to the ADR's native-fast-path description:
`plumbing.generate_parser` has no `rust_cst_module=` parameter — "the Rust path is an
offline per-grammar codegen + consumer-side compile (`genparser gen-rust-*`)" — so a native
fast path for M5 would mean "the server loading a consumer-built pyo3 module, and ...
that module would have to be generated from the *analysis grammar* variant, which needs a
`genparser` flag that does not exist yet" — recorded there as "a roadmap delta, designed
later." Code fact: no resolver hook, plugin-loading mechanism, or `rust_cst_module`
parameter exists anywhere in the current codebase (confirmed by grep and by direct read of
`plumbing.generate_parser`'s signature, `plumbing.py:91-95`, which takes only `grammar` and
`capture_trivia`).

## Open factual questions

- Whether an `ApplyResult` (or `ParseResult`) ever carries a genuinely useful *partial* CST
  when a rule's top-level alternative fails partway (as opposed to succeeding early and
  merely not consuming all input) was not traced through `gsm2parser`'s generated parser
  bodies — only the `plumbing.parse_text` discard point and the `ApplyResult(pos, result)`
  shape (`memo.py:69-71`) were confirmed directly.
- Whether any lockfile (e.g. `uv.lock`) exists and pins transitive dependencies was not
  checked; the pygls-absence finding rests on `pyproject.toml`'s `dependencies` list and a
  repository-wide grep, not a resolved dependency tree.
