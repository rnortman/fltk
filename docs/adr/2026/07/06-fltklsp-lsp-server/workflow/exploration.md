# Exploration: codebase context for `.fltklsp` design

Scope note relayed verbatim from the requester: "NO DECISIONS HAVE BEEN MADE. This was a
brainstorming session. Everything is malleable at this point." The three docs in this
directory (`README.md`, `brainstorm.md`, `fltklsp-spec.md`) are directional/advisory inputs,
not verified ground truth — claims from them are cross-checked against code below, and
places where the docs' claims don't match what's in the repo are called out explicitly.

This report is facts-about-code only; it does not evaluate or recommend anything about the
proposed `.fltklsp` design.

## 1. Runtime grammar loading (`fltk.plumbing`)

`fltk/plumbing.py` is the single module wiring grammar text to parser/CST/unparser/renderer.
Relevant functions, all synchronous, in-process, no file I/O beyond reading the input text:

- `parse_grammar(grammar_text: str) -> gsm.Grammar` (`fltk/plumbing.py:36-64`): builds a
  `terminalsrc.TerminalSource`, runs the bootstrap `fltk_parser.Parser` (itself generated from
  `fltk/fegen/fegen.fltkg`, committed as `fltk/fegen/fltk_parser.py`), checks
  `result.pos != len(terminals.terminals)` for a full-consumption failure, then converts the
  CST to GSM via `fltk2gsm.Cst2Gsm.visit_grammar`. Raises `ValueError` with a formatted error
  message (via `errors.format_error_message`) on parse failure.
- `parse_grammar_file(grammar_path: Path)` (`:67-87`): thin file-read wrapper around the above;
  raises `FileNotFoundError` if missing.
- `generate_parser(grammar, *, capture_trivia=True) -> ParserResult` (`:90-166`): the "runtime
  everything" entry point. Steps: `create_default_context(capture_trivia=...)` →
  `gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(grammar, context))` →
  `gsm2tree.CstGenerator` generates a Python AST module for CST dataclasses, `exec`'d into a
  fresh `types.ModuleType` registered in `sys.modules` under `f"fltk_grammar_{id(grammar)}"`
  (`:111-121, 156-158`) → `gsm2parser.ParserGenerator` generates the parser class AST,
  `exec`'d with a `from __future__ import annotations` prefix (`:123-144`) → the first class
  whose name ends in `"Parser"` in the exec'd globals is returned as `parser_class`
  (`:146-154`). No files are written; this is why "a generic tool can load any `.fltkg` at
  runtime" — confirmed as-implemented, not aspirational.
- `parse_text(parser_result, text, rule_name=None) -> ParseResult` (`:169-200`): builds a new
  `TerminalSource`, calls `apply__parse_{rule_name}` (defaults to `grammar.rules[0].name`), and
  — load-bearing for the ADR's D6/M3 discussion — **on any failure or partial consumption,
  discards `result` entirely** and returns `ParseResult(None, text, False, error_message)`
  (`:192-198`). There is no code path in `plumbing.py` that returns a partially-parsed CST;
  `result.result` (the successfully-parsed prefix tree) is computed but never surfaced when
  `result.pos != len(terminals.terminals)`. This matches the brainstorm's claim that "even a
  successfully parsed prefix is discarded at the call sites."
- `parse_format_config(config_text) -> FormatterConfig` / `parse_format_config_file` (`:203-254`):
  identical shape to `parse_grammar`/`parse_grammar_file` but using the committed
  `unparsefmt_parser.Parser` (generated from `fltk/unparse/unparsefmt.fltkg`) and
  `fmt_cst_to_config` (see §3) to build a `FormatterConfig`. Empty/whitespace-only text
  short-circuits to `FormatterConfig()` (`:215-216`) without invoking the parser.
- `generate_unparser_source` / `generate_unparser` / `_assemble_unparser_module` (`:257-343`):
  the shared pipeline used by both (source-only vs. exec'd) call sites — re-derives
  `grammar_with_trivia`, calls `gsm2unparser.generate_unparser(grammar_with_trivia, context,
  cst_module_name, formatter_config=...)`, compiles/execs the resulting AST.
- `unparse_cst` / `render_doc` (`:345-391`): drive a generated unparser instance through
  `unparse_{rule_name}`, then `resolve_spacing_specs` (see §4) and `Renderer.render`.

`fltk/unparse_cli.py:29-136` is a complete worked example of the intended loader shape for a
new sidecar-consuming tool: `parse_grammar_file` → `parse_format_config_file` →
`generate_parser(capture_trivia=True)` → `parse_text` → `generate_unparser` → `unparse_cst` →
`render_doc`. A `.fltklsp` loader would plausibly insert a `parse_lsp_config_file` step
alongside `parse_format_config_file` in this same pipeline shape.

### Rust-backend parser generation is a separate, build-time pipeline — not a `plumbing.generate_parser` option

`fltk/plumbing.py`'s `generate_parser` signature is `generate_parser(grammar: gsm.Grammar, *,
capture_trivia: bool = True) -> ParserResult` (`fltk/plumbing.py:90-94`) — there is no
`rust_cst_module` parameter anywhere in the codebase (confirmed by grep across `fltk/**/*.py`).
The actual Rust-backend path is the `genparser` CLI (`fltk/fegen/genparser.py`), which has
separate subcommands (`gen-rust-cst`, `gen-rust-parser`, `gen-rust-lib`, referenced at
`genparser.py:75-134` and `:799-829`) that **write `.rs` source files** for a consumer to
compile themselves via Cargo/Bazel (the `fltk_pyo3_cdylib` Bazel macro is referenced by name in
a docstring at `genparser.py:815` but its definition was not located in this exploration — see
open questions). `fltk/fegen/gsm2parser_rs.py`, `gsm2tree_rs.py`, `gsm2lib_rs.py`, and
`fltk/unparse/gsm2unparser_rs.py` generate pyo3-attributed Rust source (`#[pyo3(...)]`,
`use pyo3::prelude::*`, etc.) that becomes a compiled cdylib loaded as a Python extension
module by the consumer's own build — this is a separate, offline, per-grammar compilation step,
not a runtime option of `fltk.plumbing.generate_parser`.

## 2. Grammar Semantic Model (`fltk/fegen/gsm.py`)

Core dataclasses (all `frozen=True, slots=True`):

- `Grammar(rules: Sequence[Rule], identifiers: Mapping[str, Rule])` (`:22-24`).
- `Rule(name, alternatives: Sequence[Items], is_trivia_rule: bool = False)` (`:28-63`), with a
  memoized `can_be_nil(grammar)` walking alternatives; the memo is invalidated only by
  `dataclasses.replace` producing a new object (documented invariant at `:31-37`: a `Rule`
  object must be queried under a single `Grammar` instance).
- `Items(items: Sequence[Item], sep_after: Sequence[Separator], initial_sep: Separator =
  Separator.NO_WS)` (`:83-117`) — one alternative (one `|`-branch) of a rule.
- `Item(label: str | None, disposition: Disposition, term: Term, quantifier: Quantifier)`
  (`:121-129`) — `label` is the anchor-relevant field: `.fltkfmt`/`.fltklsp` "label" anchors
  resolve against `Item.label`.
- `Term = Union[Invocation, Identifier, Literal, Regex, Sequence[Items]]` (`:175-181`);
  `Identifier.value` is a referenced rule name, `Literal.value` a literal string,
  `Regex.value` a regex pattern string, `Sequence[Items]` a parenthesized sub-expression.
- `Disposition` enum: `SUPPRESS | INCLUDE | INLINE` (`:194-197`) — corresponds to the `%`/`$`/`!`
  grammar-syntax markers (see §5).
- `Quantifier` ABC with `Required`/`NotRequired`/`OneOrMore`/`ZeroOrMore` singletons
  (`:206-264`) — corresponds to absent/`?`/`+`/`*`.
- `Separator` enum `NO_WS | WS_REQUIRED | WS_ALLOWED` (`:66-79`) — corresponds to `.`/`:`/`,`.

Trivia-related module functions:

- `TRIVIA_RULE_NAME: Final[str] = "_trivia"` (`:18`) — the well-known rule name.
- `classify_trivia_rules(grammar) -> Grammar` (`:348-379`): runs
  `validate_no_underscore_only_names` first (unconditionally, even trivia-less grammars), then
  — only if a `_trivia` rule exists — computes reachability from it via
  `_mark_trivia_reachable`/`_mark_trivia_reachable_in_items` (`:382-403`, walks `Identifier`
  terms and recurses into `Sequence[Items]`), sets `is_trivia_rule=True` on every reachable
  `Rule`, then runs three more validators: `validate_trivia_separation` (non-trivia rules may
  not reference trivia rules, `:456-474`), `validate_trivia_rule_not_nil` (`:406-415`),
  `validate_no_repeated_nil_items` (`:433-453`, with a documented under-approximation caveat
  for context-sensitive regexes at `:439-444`).
- `add_trivia_rule_to_grammar(grammar, context)` (`:477-504`): if no `_trivia` rule is defined
  by the grammar author, synthesizes one matching `Regex(r"[\s]+")` — i.e. a grammar with no
  explicit `_trivia` rule still gets whitespace-only trivia classification for free. Clockwork
  defines no `_trivia` rule at all (confirmed: no `_trivia` line in
  `clockwork/dsl/clockwork.fltkg`), so this synthesized rule is what applies there, and
  clockwork's `doc`/`doc_line` rules (`clockwork.fltkg:2-3`) are **not** reachable from it and
  so are **not** classified as trivia — this is the concrete grammar-level fact behind the
  brainstorm's "comments are not reliably trivia" case study (§3 below).
- `validate_no_underscore_only_names(grammar)` (`:323-345`): rejects rule names or item labels
  that `naming.snake_to_upper_camel` would collapse to the empty string.

`for_each_item(items, visitor)` (`:291-302`) is the generic recursive walker over one `Items`
sequence (recursing into `Sequence[Items]` sub-expressions regardless of outer quantifier);
both `_collect_underscore_only_label_errors` and `_collect_repeated_nil_errors` are built on it
and are the closest existing precedent in-tree for "walk every item of a rule looking for label
matches," relevant to how a `.fltklsp` loader would resolve rule-scoped anchors.

## 3. `.fltkfmt` sidecar language: grammar, CST-to-config transform, addressing core

### Grammar (`fltk/unparse/unparsefmt.fltkg`, full file read)

Top-level shape: `formatter := , statement* ;` where `statement` is one of `default | group |
nest | join | after | before | rule_config | trivia_preserve | preserve_blanks | omit |
render` (`:6-17`). `rule_config := "rule" , rule_name:identifier , "{" , ( rule_statement , )* ,
"}" , ;` (`:23-25`) is the `rule <name> { ... }` block; `rule_statement` is a strict subset of
`statement` (no nested `rule_config`, no `trivia_preserve`) (`:27-28`).

**Anchor grammar rule**: `anchor := label:identifier | literal ;` (`:44`) — exactly two forms,
label-or-literal, matching the ADR's stated inherited limitation that "two unlabeled invocations
of the same rule within one alternative are not independently addressable" (there is no
rule-name anchor form in `.fltkfmt`'s grammar at all; `fltklsp-spec.md`'s `anchor := label |
rule_name | literal` is new relative to this).

Range operations `group`/`nest`/`join` use `from_spec`/`to_spec` (`:34-41`) built on the same
`anchor` rule, with `after`/`before` inclusivity modifiers. Position-scoped `after`/`before`
statements (`:47-50`) attach `position_spec_statement*` (spacing or `preserve_blanks`) to a
single anchor. `omit`/`render` (`:52-56`) attach a disposition to an anchor.

`spacing` (`:60-68`): `nil | nbsp | bsp | soft | hard | blank(N)` — the vocabulary consumed by
`fmt_config._spacing_cst_to_doc` (§below) and by the Doc-combinator pipeline
(`fltk/unparse/combinators.py`, not read in full here).

`trivia_preserve := "trivia_preserve" , ":" , trivia_node_list , ";" , ;` (`:79`), where
`trivia_node_list := identifier , ( "," , identifier )* ;` (`:81`) — plain identifiers, no
label/literal distinction; see §6 for what these identifiers actually mean.

Lexical tail, shared verbatim in spirit with `fegen.fltkg`'s `_trivia`/`identifier`/`literal`
rules: `identifier := name:/[a-zA-Z_][a-zA-Z0-9_]*/ ;`, `literal := value:/("([^"\n\\]|\\.)+"|'...')/
;`, `integer := value:/[0-9]+/ ;`, and `_trivia := ( line_comment | line_comment? : )+ ;` with
`line_comment := prefix:"//" . content:/[^\n]*/ . newline:"\n" ;` (`:87-93`) — `//`-only line
comments, no block comments (unlike `fegen.fltkg`, which additionally has `block_comment`,
`fegen.fltkg:19-21`).

### CST → `FormatterConfig` transform (`fltk/unparse/fmt_config.py`, full file read)

`fmt_cst_to_config(formatter, terminal_src) -> FormatterConfig` (`:818-936`) is the single
entry point invoked by `plumbing.parse_format_config` (`plumbing.py:231`). It dispatches on
`statement.maybe_<kind>()` accessor methods generated onto the `Statement` CST node (the
`maybe_X`/`child_X`/`children_X` accessor pattern is the generic CST access convention used
throughout — see `gsm2tree.py`, not fully read here, for its origin) for each of the eleven
statement kinds, and separately re-dispatches the `rule_statement` subset inside a
`rule_config` block (`:887-935`).

Anchor resolution to string keys happens per-statement-kind in small helper functions
(`_process_after_statement`, `_process_before_statement`, `_process_omit_statement`,
`_process_render_statement`, `_process_range_operation`, all `fmt_config.py:530-810`): each
extracts `anchor.maybe_label()` / `anchor.maybe_literal()`, builds a selector
(`ItemSelector.LABEL` or `ItemSelector.LITERAL`, `:62-67`) with a string value (identifier text
via `_extract_identifier_text`, or unquoted literal text via `_extract_literal_text` using
`ast.literal_eval`, `:482-493`), and stores an `AnchorConfig` keyed by a composite string
`f"{position}:{selector_type.value}:{selector_value}"` (e.g. `"after:label:condition"`,
comment at `:146-149`) in either the global `FormatterConfig.anchor_configs` dict or a
per-rule `RuleConfig.anchor_configs` dict (`:139-166`).

**No GSM cross-check was found in this pipeline.** `fmt_cst_to_config` builds `AnchorConfig`
entries purely from the `.fltkfmt` CST's own identifier/literal spans; it never consults a
`gsm.Grammar` object, and nothing in `fmt_config.py` raises if a label or literal names nothing
that exists in a given grammar. Anchor *matching against grammar items* happens later, at
unparser-**codegen** time, in `fltk/unparse/gsm2unparser.py`'s `_item_matches_anchor` (`:1475-
1481`, trivial equality check against `item.label` or `item.term.value`) and the
`FormatterConfig.get_anchor_config`/`get_item_anchor_config` lookups (`fmt_config.py:168-236,
356-381`) — both simply return `None` on no match, which callers treat as "no operation to
apply" (e.g. `gsm2unparser.py:1498-1499, 1543`) rather than as an error. **No code path was
found, in either `fmt_config.py` or `gsm2unparser.py`, that reports an anchor which matched
nothing against the grammar** — a mistyped label/literal in a `.fltkfmt` file appears to
silently produce no formatting effect rather than a load error, as far as this exploration
found. (This is a fact about the current `.fltkfmt` pipeline, offered because
`fltklsp-spec.md` and the ADR's D2 both assert `.fltkfmt` already does "load-time validation of
every anchor against the GSM" and `.fltklsp` will "reuse" that; this exploration did not find
that validation in the `.fltkfmt` Python pipeline. It may exist in the Rust `fltkfmt` CLI
(`crates/fltkfmt/`) — that crate's source was not read in this pass beyond confirming no
`crates/fltkfmt/src/*.rs` files contain the substring `validate`/`Validat`; see open questions.)

### The `trivia_preserve` name-convention inconsistency, concretely

`TriviaConfig.preserve_node_names` docstring: *"The names refer to the CST class names (e.g.,
"LineComment", "BlockComment"). These are the actual node types that appear as children of
Trivia nodes."* (`fmt_config.py:44-49`). A real, committed `.fltkfmt` file confirms this
in practice: `fltk/fegen/fegen.fltkfmt:1` reads `trivia_preserve: LineComment, BlockComment;` —
PascalCase, matching the generated CST class names — while the same file's `rule` blocks
address grammar rule names verbatim: `rule item { ... }`, `rule term { ... }`, `rule
block_comment { ... }` (`fegen.fltkfmt:40, 45, 55`, lower-snake-case, matching
`fegen.fltkg`'s rule names `item`, `term`, `block_comment` exactly). The PascalCase-vs-snake
name is produced by `naming.snake_to_upper_camel` (`fltk/fegen/naming.py:7-22`,
`"".join(part.capitalize() for part in name.lower().split("_"))`) — i.e. `trivia_preserve`'s
identifiers are post-conversion class names while every other addressing surface in the same
file (`rule <name>`, `label:` anchors) uses pre-conversion grammar rule/label names. This is
the exact inconsistency the ADR's D2 proposes to "canonicalize on grammar rule names" for the
shared `.fltklsp`/`.fltkfmt` addressing core.

## 4. `resolve_spacing_specs` (`fltk/unparse/resolve_specs.py`, full file read)

Post-processes a `Doc` tree of `AfterSpec`/`BeforeSpec`/`SeparatorSpec` control nodes (defined
in `fltk/unparse/combinators.py`, not read) into concrete spacing, via: `_expand_joins` (Join →
Concat + SeparatorSpecs, `:67-118`), `_extract_all_boundary_specs` (pulls leading/trailing
specs out of `Concat`/`Group`/`Nest`, `:121-169`), `_resolve_patterns`/`_resolve_concat_patterns`
(a small ordered pattern-matcher over a sliding `deque` window with named mutators —
`_mutate_after_sep_before`, `_mutate_after_sep`, `_mutate_sep_before`,
`_mutate_standalone_sep`, `_mutate_standalone_after_before`, `_mutate_text_newline`,
`_mutate_consecutive_specs`, `:198-543`), and a final `_collapse_hardline_sequences` pass
(`:285-326`). This is purely a Doc-combinator-tree transform; it consumes `AnchorConfig`-derived
`Doc` values already resolved by `gsm2unparser.py` and has no direct bearing on anchor
addressing itself, but it is the module `plumbing.unparse_cst` calls after `unparse_{rule}`
(`plumbing.py:376`).

## 5. `SpanProtocol`, `line_col()`, `ErrorTracker`, `error_formatter`

`fltk/fegen/pyrt/span_protocol.py` (full file read): `SpanProtocol` (`:56-146`) is a
`runtime_checkable` `Protocol` satisfied structurally by both the pure-Python
`terminalsrc.Span` and the native `fltk._native.Span`. Members: `start`/`end` (codepoint
indices, half-open), `kind: Literal[SpanKind.SPAN]` (discriminant for `match`/`case` dispatch
over mixed span/node children unions), `text()`/`text_or_raise()`, `has_source()`,
`len()`/`is_empty()`, `merge(other: Self)`/`intersect(other: Self)` (raise `ValueError` on
cross-source operands), `filename()`, and the two line/col methods:
`line_col() -> LineColPosProtocol | None` (`:127-133`, returns `None` for sourceless/negative/
out-of-bounds spans) and `line_col_or_raise()` (`:135-139`, raises `ValueError` in the same
cases). `LineColPosProtocol` (`:24-53`) exposes `line`/`col`/`line_span` (0-based codepoint
line/col, and a `SpanProtocol` covering the whole line exclusive of trailing `\n`) — the
`line_span` return being covariant (`terminalsrc.Span` on the Python backend) is why these are
declared as read-only `@property` members rather than plain attributes (`:33-38` comment).
`AnySpan` (`:149-157`) is a runtime union type, falling back to the pure-Python `Span` alone if
`fltk._native` is not importable.

`fltk/fegen/pyrt/errors.py` (full file read): `ErrorTracker[RuleId]` (`:24-49`) tracks
`longest_parse_len` and `expected_context: list[ParseContext]`; `fail_literal`/`fail_regex`
(`:29-49`) implement furthest-failure semantics — a new failure at a strictly greater position
resets the expected-set, an equal position appends to it, a lesser position is ignored.
`ParseContext(rule_id, token_type: TokenType.LITERAL|REGEX, token: str)` (`:17-21`) groups
expectations by originating rule. `format_error_message(tracker, terminals, rule_name_lookup)`
(`:126-152`) renders `"Syntax error at line N col M:\n<source line>\n<caret>\nExpected:\n"` plus
one `From rule "<name>":` section per distinct `rule_id` with its literal/regex token set —
this is what both `plumbing.parse_grammar`/`parse_text`/`parse_format_config` and
`genparser._read_and_parse_grammar` call on parse failure. `escape_control_chars`/`_needs_escape`
(`:69-123`) escape a broad control/bidi/zero-width codepoint set for safe terminal display, and
are explicitly pinned byte-identical to a Rust port (`crates/fltk-cst-core/src/escape.rs`,
comment at `:106-109`).

`fltk/fegen/pyrt/error_formatter.py` (full file read): `format_source_line(span: SpanProtocol,
message, *, filename=None)` (`:67-120`) is a separate, `SpanProtocol`-only (not tracker-based)
renderer — `In <file>:<line>:<col>:\n<line>\n<caret>\n<message>\n`, degrading to `At line N,
column M:` when no filename is resolvable. Its docstring (`:1-8`) states it factors out logic
already duplicated by an out-of-tree consumer, clockwork's `format_line_with_error`
(`clockwork/dsl/ir/cst_util.py:70-92`, not verified in this pass since it's outside this repo).

## 6. Structured/optional trivia — CST shape

`fltk/fegen/fltk_cst_protocol.py:754-816` (partial read) shows the generated `Trivia` protocol
class for the FLTK-grammar-parsing-itself bootstrap: `children: list[tuple[Label | None,
BlockComment | LineComment | SpanProtocol]]`, with per-labeled-child-kind accessor bundles
(`append_line_comment`, `children_line_comment`, `child_line_comment`, `maybe_line_comment`,
same for `block_comment`) alongside the generic `append`/`extend`/`child`/`insert`/`remove_at`/
`replace_at`/`clear` sequence-protocol methods. This is the concrete shape `TriviaConfig.
preserve_node_names` (§3) filters against: a `Trivia` node's children are typed unions of
either raw plain-whitespace `SpanProtocol` slices or structured `LineComment`/`BlockComment`
CST nodes, and `capture_trivia` (the flag threaded through `plumbing.generate_parser` and
`create_default_context`) controls whether this structure is captured at all versus trivia
being skipped as bare whitespace.

## 7. The `.fltkg` grammar-authoring format itself

`fltk/fegen/fegen.fltkg` (full file read, 22 lines) is the self-hosted grammar for `.fltkg`:

```
grammar := , rule+ ;
rule := name:identifier , ":=" , alternatives , ";" , ;
alternatives := items , ( "|" , items , )* ;
items :=
  ( no_ws:"." | ws_allowed:"," | ws_required:":" )? ,
  item ,
  ( ( no_ws:"." | ws_allowed:"," | ws_required:":" ) , item , )* ,
  ( no_ws:"." | ws_allowed:"," | ws_required:":" )? ,
  ;
item := ( label:identifier . ":" )? . disposition? . term . quantifier? , ;
term :=
  identifier | literal | "/" . regex:raw_string . "/" | "(" , alternatives , ")" ;
disposition := suppress:"%" | include:"$" | inline:"!" ;
quantifier := optional:"?" | one_or_more:"+" | zero_or_more:"*" ;
identifier := name:/[_a-z][_a-z0-9]*/ ;
raw_string := value:/([^\/\n\\]|\\.)+/ ;
literal := value:/("([^"\n\\]|\\.)+"|'([^'\n\\]|\\.)+')/ ;
_trivia := ( line_comment | line_comment? : | block_comment )+ ;
line_comment := prefix:"//" . content:/[^\n]*/ . "\n" ;
block_comment := start:"/*" . content:/(?:[^*]|\*+[^\/\*])*/ . end:/\*+\// ;
```

This is a bootstrap grammar (parsed by a hand/self-generated `fltk_parser.py`) — the same
`.fltkg` syntax is used to define `.fltkg` itself, `unparsefmt.fltkg` (§3), `toy.fltkg`
(`fltk/unparse/toy.fltkg`), `regex.fltkg`, and `bootstrap.fltkg`. A new `.fltklsp` grammar
(sketched, not implemented, in `fltklsp-spec.md` §5) would be authored in this same `.fltkg`
syntax and go through the identical `parse_grammar` → `generate_parser` runtime pipeline (§1) —
`fltklsp-spec.md`'s sketch already reuses `fegen.fltkg`'s exact `identifier`/`literal`/
`_trivia`/`line_comment` lexical tail verbatim (compare `fltklsp-spec.md:189-193` to
`fegen.fltkg:16,18,19-20` and `unparsefmt.fltkg:87-88,91-92`).

## 8. Case-study grammar grounding (clockwork)

Cross-checked against `/home/rnortman/tps/clockwork/clockwork/dsl/clockwork.fltkg` (outside
this repo, in the additional working directory) since the brainstorm's §3 case study and the
worked example in `fltklsp-spec.md` §4 both cite it:

- No `_trivia` rule exists in the file (grep confirms zero matches) — so
  `add_trivia_rule_to_grammar` (§2) synthesizes the default whitespace-only trivia rule, and
  `doc := (/ */ . "//" . line:doc_line)+ . / */;` / `doc_line := (" " . text:/[^\n]*/)? .
  "\n";` (`clockwork.fltkg:2-3`) are ordinary structural rules, not trivia-reachable.
- `condition_spec` (`:53`), `channel_option_publishers` (`:135`), `unit_identifier` (`:281`),
  `boolean` (`:282`), and `clk_generate_target` (`:287`) all exist verbatim as named in
  `fltklsp-spec.md`'s worked example (§4 of that doc), confirming the example's anchors
  (`"time_since_last_exec"`, `single`/`multiple`/`diagnostics`/`bridge_status`/
  `c2c_bridge_status`, `s`/`ms`/`us`/`bit`/`byte`, `true`/`false`, `cpp`/`proto`/`go_proto`/`py`/
  `nanobind`) are drawn from real, currently-committed grammar rules rather than invented ones.

## Open factual questions

1. Whether `.fltkfmt` anchors are validated against a `gsm.Grammar` at load time anywhere
   outside the Python pipeline traced in §3 (e.g. in `crates/fltkfmt/` or
   `fltk/unparse/gsm2unparser_rs.py`) was not conclusively resolved — `crates/fltkfmt/src/`
   contains no `validate`/`Validat` substring, but a rename/differently-worded check was not
   ruled out, nor was `fltk/unparse/gsm2unparser_rs.py`'s anchor-matching logic (the Rust-CST
   unparser generator) inspected as closely as the Python `gsm2unparser.py` was.
2. The `fltk_pyo3_cdylib` Bazel macro referenced by name in `fltk/fegen/genparser.py:815` (as
   the injector of `#![recursion_limit]` at assembly time) was not located during this
   exploration — its definition site (presumably a `.bzl` file) was not searched for.
3. `clockwork/dsl/ir/cst_util.py:70-92` (`format_line_with_error`, cited by
   `error_formatter.py`'s docstring as the pre-existing duplicated logic) was not opened in
   this pass; the claimed duplication was not independently verified line-by-line.
