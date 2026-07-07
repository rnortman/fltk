# Design — Round 1: the `.fltklsp` language, loader, classification engine, and `fltk-highlight`

Status: draft for review (pre-freeze).

Provenance: the three docs in `docs/adr/2026/07/06-fltklsp-lsp-server/` (`README.md`,
`brainstorm.md`, `fltklsp-spec.md`) are **directional/advisory only**. Per the requester:
"NO DECISIONS HAVE BEEN MADE. This was a brainstorming session. Everything is malleable at
this point." Codebase facts below come from
`docs/adr/2026/07/06-fltklsp-lsp-server/workflow/exploration.md` and direct source reads;
where the advisory docs conflict with the code, this design says so explicitly (§2).

## 1. Round-1 scope: what and why

**Scope chosen: the ADR's M0 and M1 as one round** — the `.fltklsp` grammar and its
committed generated parser, the config model + loader with load-time GSM validation, the
classification engine (built-in defaults + explicit `scope` painting + def-site paint), and
the standalone `fltk-highlight` CLI (ANSI output). Pure Python, no pygls, no LSP protocol,
no cross-file anything.

Why this cut:

- The grammar is the hard-to-reverse artifact. Everything downstream (server, defs/refs,
  resolver) consumes `.fltklsp` files; once out-of-tree consumers write them, the language
  is public API with the same compatibility obligations as generated code (ADR
  Consequences). So round 1 must get the *whole* language surface parsed and validated —
  including the phase-2 `def`/`ref`/`namespace` statements — even though most phase-2
  semantics stay inert.
- M0 alone has no end-to-end consumer; classification semantics (the painter's rules, the
  default table, contextual keywords) are exactly the kind of thing that looks right on
  paper and is wrong against a real tree. The ADR itself calls the highlighter CLI "the
  test harness for classification semantics" (`README.md`, Incremental plan M1).
  Merging M1 in gives the round a demonstrable, verifiable artifact and forces the token
  stream API — the interface the M2 server will consume — to be designed against a real
  caller.
- Working through the details surfaced a genuine design gap in the advisory docs
  (suppressed terminals never reach the CST — §2.1) whose fix (the analysis-grammar
  transform, §4.4) belongs in the same round as the classifier it enables.

Explicitly out of round 1: pygls server (M2), prefix-CST exposure (M3), symbol tables /
document symbols / rename (M4), resolver plugin (M5), HTML output for the CLI, UTF-16
position conversion, TextMate export.

## 2. Corrections to the advisory docs (facts found in code)

These are the places where "work through the details" changed the plan.

### 2.1 Suppressed-by-default terminals: parse-then-paint cannot read keywords off the CST as-is

`fltk2gsm.Cst2Gsm.visit_item` (`fltk/fegen/fltk2gsm.py:114-122`): an unlabeled `Literal` or
`Regex` item defaults to `Disposition.SUPPRESS`; only labeled items, sub-expressions, and
rule invocations (which get an implicit label equal to the invoked rule name, `:114-115`)
default to `INCLUDE`. `gsm2parser.py:848` then omits suppressed items from the CST
entirely. Consequence: in clockwork's `channel_name := "name" , ":" , expr`, neither
`"name"` nor `":"` exists in the parsed tree — the exact spans the brainstorm's case study
(§3) wants to paint `keyword` are *gaps* in the parent node's span. The brainstorm's
per-occurrence classifier is unimplementable against the normal CST. §4.4 is the fix.

### 2.2 `.fltkfmt` has no load-time GSM anchor validation to reuse

ADR D2 and `fltklsp-spec.md` §1 both claim `.fltklsp` "reuses" `.fltkfmt`'s "load-time
validation of every anchor against the GSM." Exploration §3 found no such validation:
`fmt_config.fmt_cst_to_config` never consults a `gsm.Grammar`, and unmatched anchors
silently no-op at unparser-codegen time (`gsm2unparser.py:1475-1481`,
`fmt_config.py:168-236`). What `.fltklsp` reuses is the *addressing idiom* (anchors,
`rule` blocks, lexical conventions). The validation is **built new in this round** (§4.3);
it is a headline feature, not an inherited one. Backporting it to `.fltkfmt` is noted as a
possible follow-up round, not attempted here.

### 2.3 `generate_parser(rust_cst_module=...)` does not exist

ADR D4's native-fast-path description cites a `rust_cst_module=` parameter of
`plumbing.generate_parser`; there is none (exploration §1). The Rust path is an offline
per-grammar codegen + consumer-side compile (`genparser gen-rust-*`). This does not affect
round 1 (pure Python), but it changes the M5 story: the native fast path means the server
loading a consumer-built pyo3 module, and — because of §4.4 — that module would have to be
generated from the *analysis grammar* variant, which needs a `genparser` flag that does not
exist yet. Recorded as a roadmap delta (§7), designed later.

### 2.4 Implicit labels break the spec's global-anchor ambiguity rule

`fltklsp-spec.md` §1 says a global identifier anchor that is both a label and a rule name
is a load error requiring a `label:`/`rule:` qualifier. But because fltk2gsm gives every
unlabeled rule invocation an implicit label equal to the rule name (`fltk2gsm.py:114-115`),
*every* invoked rule name is also a label — the "ambiguous" case is the norm, and the
spec's rule would make nearly every rule-name anchor an error. Round 1 replaces it with
union semantics (§4.3): an unqualified global identifier anchor matches both
interpretations (the two readings coincide except under explicit relabeling); the
qualifiers remain available to restrict.
Note that union semantics is itself a commitment: once out-of-tree `.fltklsp` files use
unqualified ambiguous anchors, tightening to the spec's error rule later would reject
previously-valid files — a breaking change under this project's compatibility standard —
so this choice is being made deliberately, not as a reversible default.

## 3. Deliverables and file layout

New package `fltk/lsp/` (will also host the M2 server later):

| File | Contents |
|---|---|
| `fltk/lsp/__init__.py` | empty package marker |
| `fltk/lsp/fltklsp.fltkg` | the `.fltklsp` grammar (§4.1) |
| `fltk/lsp/fltklsp_cst.py`, `fltklsp_cst_protocol.py`, `fltklsp_parser.py`, `fltklsp_trivia_parser.py` | generated + committed, via a new `gencode` step (§5) |
| `fltk/lsp/lsp_config.py` | config dataclasses + CST→config transform + GSM validation (§4.2–4.3) |
| `fltk/lsp/analysis.py` | `prepare_analysis_grammar()` GSM transform (§4.4) |
| `fltk/lsp/classify.py` | token legend, default classifier, painter engine, `Token` (§4.5–4.6) |
| `fltk/lsp/engine.py` | `AnalysisEngine`: grammar+specs in, tokens+diagnostics out (§4.7) |
| `fltk/lsp/highlight_cli.py` | `fltk-highlight` typer CLI, ANSI output (§4.8) |
| `fltk/plumbing.py` | add `parse_lsp_config(config_text, grammar)` / `parse_lsp_config_file(path, grammar)` wrappers, mirroring `parse_format_config(_file)` (`plumbing.py:203-254`) |
| `fltk/lsp/test_*.py` | tests (§8), colocated per repo convention |

No existing generated artifact changes. Everything here is *new* public surface; nothing
renames or perturbs existing generated symbols (per CLAUDE.md's out-of-tree-consumer
rules).

## 4. Proposed approach

### 4.1 The `fltklsp.fltkg` grammar

Refined from the `fltklsp-spec.md` §5 sketch; deviations noted after the listing. Same
lexical tail as `unparsefmt.fltkg:87-92` (identifier / literal / `//`-only `_trivia`).

```
// fltklsp.fltkg — grammar for .fltklsp editor-tooling spec files
lsp_spec := , statement* ;

statement := scope_stmt | rule_config ;

rule_config := "rule" : rule_name:identifier , "{" , ( rule_statement , )* , "}" , ;
rule_statement := scope_stmt | def_stmt | ref_stmt | namespace_stmt ;

scope_stmt := "scope" : anchor_list , ":" , scope:dotted_name , ";" , ;
def_stmt   := "def" : anchor , ":" , kind:dotted_name , ";" , ;
ref_stmt   := "ref" : anchor , ":" , kind_list , ";" , ;
namespace_stmt := "namespace" , ";" , ;

anchor_list := anchor , ( "," , anchor , )* ;
anchor := ( qualifier . ":" )? . name:identifier | literal ;
qualifier := label:"label" | rule:"rule" ;

kind_list := wildcard:"*" | kind:dotted_name , ( "," , kind:dotted_name , )* ;
dotted_name := part:identifier . ( "." . part:identifier )* ;

identifier := name:/[a-zA-Z_][a-zA-Z0-9_]*/ ;
literal := value:/("([^"\n\\]|\\.)+"|'([^'\n\\]|\\.)+')/ ;

_trivia := ( line_comment | line_comment? : )+ ;
line_comment := prefix:"//" . content:/[^\n]*/ . newline:"\n" ;
```

Deviations from the sketch, with reasons:

- **`qualifier` is its own rule with labeled literals** (`label:"label" | rule:"rule"`),
  not an inline `qualifier:("label" | "rule")` sub-expression. Because unlabeled literals
  are suppressed (§2.1), the sketch's form would parse but leave no way to tell *which*
  qualifier matched. (The dogfooding lesson applies to our own grammar too.)
- **`scope_name` dropped**; the statement captures `scope:dotted_name` and the loader
  interprets the single-segment name `none` as suppression. One fewer rule, same language.
- **`kind_list` fixed**: `*` is a complete alternative, not a list head — the sketch
  allowed the meaningless `ref x: *, foo;`.
- **`dotted_name` segments labeled `part`** so the loader reads segments via
  `children_part()` instead of span slicing.
- Keywords are followed by `:` (ws-required) separators, matching `unparsefmt.fltkg`'s
  style (`after := "after" : anchor …`), which also prevents `scopefoo` mis-lexing.

Known parse-level quirk (documented, accepted): an anchor literally named `label` or
`rule` written flush against a colon — `scope label:comment;` or `scope label: comment;` —
fails to parse. The optional qualifier group commits once it consumes `label:` (PEG `e?`
does not backtrack after success), so the flush spellings misparse as a qualified anchor
and error shortly after. Writing whitespace before the colon — `scope label : comment;` —
disambiguates, because the qualifier's `.` separators forbid whitespace, so the qualifier
group never matches. The failure mode is always a visible parse error, never a silent
misclassification. A test pins both the failing and working spellings.

### 4.2 Config model (`lsp_config.py`)

Mirrors the `fmt_config.py` shape (CST in, plain dataclasses out) but — unlike
`FormatterConfig` — resolution happens at load time against a `gsm.Grammar`, because there
is no later codegen step to do it.

```python
@dataclass(frozen=True) class Anchor:            # parsed, pre-resolution
    qualifier: Literal["label", "rule"] | None   # None = unqualified identifier
    name: str | None                             # identifier anchors
    literal: str | None                          # literal anchors (unquoted via ast.literal_eval,
                                                 #   same as fmt_config._extract_literal_text)
    span: SpanProtocol                           # for error reporting

@dataclass(frozen=True) class ScopeStmt:  anchors: tuple[Anchor, ...]; token: str; modifiers: tuple[str, ...]; hints: tuple[str, ...]; index: int
@dataclass(frozen=True) class DefStmt:    anchor: Anchor; kind: tuple[str, ...]; index: int
@dataclass(frozen=True) class RefStmt:    anchor: Anchor; kinds: tuple[tuple[str, ...], ...] | Literal["*"]; index: int
@dataclass(frozen=True) class RuleBlock:  rule_name: str; scopes: ...; defs: ...; refs: ...; is_namespace: bool

@dataclass(frozen=True) class LspConfig:
    global_scopes: tuple[ScopeStmt, ...]
    rule_blocks: tuple[RuleBlock, ...]            # may contain several blocks for one rule
```

Statement `index` is file order, for the later-statement-wins tiebreak. Multiple
`rule X { }` blocks for the same rule are allowed and accumulate in file order (consistent
with later-wins; an error here would buy nothing). Empty/whitespace-only config text
short-circuits to an empty `LspConfig` (mirroring `plumbing.parse_format_config`'s
`plumbing.py:215-216`), and an absent `.fltklsp` file entirely is fully supported — the
built-in defaults alone are the ADR's "usable baseline."

`def`/`ref`/`namespace` are parsed, validated, and stored now so that phase-1 files remain
valid verbatim when M4 lands (the ADR's D1 commitment). In round 1 their only *semantic*
effect is def-site paint (§4.6); `ref` and `namespace` are inert.

### 4.3 Load-time validation and anchor resolution

`load_lsp_config(config_text, grammar) -> ResolvedLspConfig` — parse, transform, validate,
resolve, in one call; `plumbing.parse_lsp_config` wraps it. Validation collects **all**
errors (not fail-fast) and raises one `LspConfigError` whose message renders each offense
with `error_formatter.format_source_line` (`fltk/fegen/pyrt/error_formatter.py:67-120`)
against the `.fltklsp` source — file:line:col, caret, message.

Validation rules (each is a load error unless marked warn):

1. `rule X { … }`: `X` must be in `grammar.identifiers`.
2. Identifier anchor inside `rule X`: must match, among `X`'s items (recursed through
   `Sequence[Items]` sub-expressions via `gsm.for_each_item`, `gsm.py:291-302`), an
   `Item.label` (explicit or implicit) — or, with the `rule:` qualifier, an invoked rule
   name. Unqualified matches the union of both readings (they coincide except under
   explicit relabeling).
3. Literal anchor inside `rule X`: must equal some `Literal` term value among `X`'s items
   (same recursion).
4. Global identifier anchor, unqualified: must be a rule name in `grammar.identifiers` or
   an `Item.label` somewhere in the grammar. Matches the **union**: all CST nodes of that
   rule, plus all children carrying that label. See §2.4 for why this replaces the spec's
   ambiguity error. `label:`/`rule:` qualifiers restrict to one reading (and then that
   reading must exist).
5. Global literal anchor: must appear as a `Literal` term value somewhere in the grammar.
6. `scope` token name: first segment must be in the legend (§4.5) or be `none` (`none`
   must be the sole segment). Remaining segments: those in the LSP standard-modifier set
   (`declaration`, `definition`, `readonly`, `static`, `deprecated`, `abstract`, `async`,
   `modification`, `documentation`, `defaultLibrary`) become modifiers; others are carried
   as `hints` (used by the CLI theme layer later if ever; dropped by the LSP layer).
7. `def`/`ref` kinds: any dotted name is accepted (kind vocabulary is deliberately open;
   M4 maps first segments to `SymbolKind` with an Object fallback per the spec).

No dead-anchor warning is needed in round 1: in the analysis grammar (§4.4) suppressed
subtrees surface as real nodes, so every resolvable anchor can match, and `INLINE`-bearing
grammars are rejected outright before validation runs (§4.4).

Resolution output (`ResolvedLspConfig`) precomputes, per grammar rule, the matcher lists
the classifier consumes: `node_paints[rule_name]` (whole-node paints from global rule-name
anchors), and `child_matchers[rule_name]` — ordered lists of
`(match: ByLabel(name) | ByLiteralText(text) | ByChildRule(name), paint | def_kind, tier)`.
Tier records (rule-block vs global, label/literal vs rule-name, statement index) for the
precedence key in §4.6.

### 4.4 The analysis grammar (fix for §2.1)

New GSM-level transform, `fltk/lsp/analysis.py`:

```python
def prepare_analysis_grammar(grammar: gsm.Grammar) -> gsm.Grammar
```

Returns a structurally identical grammar in which every `Item` with
`disposition == SUPPRESS` is replaced (`dataclasses.replace`) with `INCLUDE`, recursively
through `Sequence[Items]` sub-expressions and across all rules. For `SUPPRESS`/`INCLUDE`,
disposition affects only CST construction, not matching (`gsm2parser.py:848` gates child
emission), so the analysis grammar parses exactly the same language with exactly the same
spans — but its CST contains a child for every terminal the parser touched: suppressed
literals and regexes surface as unlabeled span children; suppressed subtrees surface as
nodes.

The engine (§4.7) feeds `prepare_analysis_grammar(grammar)` to the existing
`plumbing.generate_parser(...)` (`plumbing.py:90-166`), whose exec'd in-memory module is
never written to disk — so the fatter child unions of the analysis CST classes are
invisible to downstream consumers and change no public API. Precedent that
unlabeled-INCLUDE terminals already work end-to-end: `$"tag"` in the committed fixture
grammar `fltk/fegen/test_data/rust_parser_fixture.fltkg:48`.

**`INLINE` (`!`) is different and out of scope.** The Python runtime parser generator does
not implement it at all — `gsm2parser.py:828-830` raises a raw `NotImplementedError` on
any `INLINE` item (the Rust generator likewise rejects it; the only in-tree grammar using
`!`, `fltk.fltkg`, is labeled "intentionally broken" in the Makefile). So `INLINE`-bearing
target grammars cannot be loaded by any `plumbing.generate_parser`-based engine today.
`prepare_analysis_grammar` therefore scans for `INLINE` dispositions up front and raises a
clean, formatted "grammar uses `!` (inline), not supported by the analysis engine" error
instead of letting the generator's `NotImplementedError` escape. Inline-aware
classification is a roadmap item contingent on `gsm2parser` gaining `INLINE` support (§7).

Alternative considered and rejected: *gap scanning* — keep the normal CST, compute
`node.span` minus child spans, and re-tokenize gap text against the rule's suppressed
terminal set. Rejected because it re-implements lexing heuristically (multiple suppressed
items can share one gap; suppressed `%rule` subtrees put entire sub-languages in gaps),
whereas the transform gets exact spans from the parser that already did the work. Cost:
one extra in-memory parser variant and somewhat larger trees; acceptable for a tool that
owns its parser. Consequence for the M5 native fast path noted in §7.

Formatting (M2) is unaffected: the server will keep a *standard*-disposition parser for
the format code path; parsing twice per format request is fine.

### 4.5 Default classification (built-ins)

Token legend, frozen for round 1 (spec OQ5 → start frozen): `keyword`, `comment`,
`string`, `number`, `operator`, `punctuation`, `variable`, `parameter`, `property`,
`type`, `function`, `enumMember`, `constant`, `macro`, `label`, `text`, plus the
pseudo-token `none`. (Four legend members — `punctuation`, `text`, `constant`, `label` —
are not in LSP 3.17's predefined `SemanticTokenTypes`; the LSP semantic-tokens legend is
server-defined strings, so M2 can register all four as custom types — clients that don't
theme them simply won't color them. `constant` matters in practice: the spec's clockwork
worked example paints `boolean`/`unit_identifier` as `constant`, so M2/theme docs must
account for it. No round-1 impact.)

Defaults apply **only where no explicit paint covers the position** (§4.6). Per CST
occurrence in the analysis tree:

- Node of an `is_trivia_rule` rule → `comment` over the whole node span, **unless** the
  node's text is entirely whitespace, in which case no token (otherwise every synthesized
  `/[\s]+/` trivia match — clockwork has no `_trivia` rule at all — would emit useless
  comment tokens over plain whitespace). **The default walk does not descend into
  `is_trivia_rule` nodes**: the outermost trivia node emits at most one `comment`
  interval, and its subtree contributes no further defaults. This is what keeps the
  default layer overlap-free — without it, nested trivia nodes (e.g. `Trivia` containing
  `LineComment`, both trivia rules) would double-paint `comment`, and terminals inside a
  comment (e.g. the `prefix:"//"` literal) would repaint as `operator` inside every
  comment. Explicit paints inside trivia subtrees still apply per painter rule 1
  (mirroring the spec's own rule-2 example: the `"//"` inside a `comment`-scoped node
  doesn't repaint).
- Terminal (span) children classify by **provenance, then text shape**. Provenance: a
  labeled span resolves through the owning rule's GSM items with that label; an unlabeled
  span resolves literal-first — exact match against the rule's `Literal` values, else
  `re.fullmatch` against the rule's `Regex` patterns. Per-rule terminal tables are
  precomputed from each rule's own items (recursing through `Sequence[Items]`
  sub-expressions; `INLINE` never arises — §4.4 rejects it).
  - Provenance = `Literal`: word-shaped — the literal starts with a match of
    `[A-Za-z_][A-Za-z0-9_]*`, which includes multi-word literals like `execute when` —
    → `keyword`; text in `( ) [ ] { } , ; : .` → `punctuation`; else → `operator`.
  - Provenance = `Regex`: classified by the **matched text's** shape — quote-started →
    `string`, digit-started → `number`, identifier-shaped → `variable`, else `text`.
    (Deviation from the spec's §2.2 pattern-shape table: text shape needs no regex-pattern
    introspection and is per-occurrence — a regex that matches both `"abc"` and `abc`
    classifies each occurrence correctly, which pattern-shape cannot. Same intent, simpler
    and strictly more precise.)
  - No provenance found (theoretically possible if a literal and regex overlap oddly) →
    no token; the editor's default styling shows through.
- Whitespace-only spans → no token, always (defaults tier only; an explicit scope that
  covers them still paints, per painter rule 1).

This preserves the case study's guarantee: the keyword/identifier *boundary* is decided by
provenance (which item the parser matched), never by spelling — `name` the option-key
literal paints `keyword`, `name` the identifier paints `variable`, in textually identical
positions.

### 4.6 Painter engine and token stream

```python
@dataclass(frozen=True, order=True)
class Token:
    start: int              # codepoint offsets, same coordinate space as SpanProtocol
    end: int
    token_type: str         # legend member; "none" never appears in output
    modifiers: tuple[str, ...]

def classify(tree, grammar, resolved_config, text) -> list[Token]
```

Output invariants: sorted by `start`, non-overlapping, within `[0, len(text))`, adjacent
tokens with identical type+modifiers merged. UTF-16 conversion is an M2 concern; round 1
stays in codepoints end-to-end.

Two-layer interval model implementing the spec's painter's rules 1–5:

1. **Explicit layer.** Walk the analysis tree once. For each node, consult
   `node_paints[kind]` and, for each child, `child_matchers[parent_kind]` (plus global
   label/literal/rule matchers). Every match contributes an interval
   `(span, paint, key)` covering the *entire* matched node/child span (rule 1), where
   `key = (depth, source_rank, anchor_rank, block_rank, stmt_index)`:
   - `depth`: tree depth of the matched node — innermost explicit wins (rule 3);
   - `source_rank`: explicit `scope` (2) beats def-derived paint (1) *at the same node*
     (spec §3: "explicit `scope` always wins"; a def-derived paint on a **descendant**
     still beats an ancestor's explicit scope via `depth` — the sane reading of the two
     clauses together, called out here because the spec is ambiguous on it);
   - `anchor_rank`/`block_rank`/`stmt_index`: label-or-literal beats rule-name anchor,
     rule-block beats global, later statement wins ties (rule 4).
   A sweep over interval endpoints assigns each text position the max-key paint.
   `none` participates with a real key and yields no token but occludes losers (rule 5).
   Def-derived paint = the def's kind first segment **if** it is in the legend (else no
   paint), with modifier `declaration` added (spec §3).
2. **Default layer.** Positions covered by *no* explicit-layer interval (rule 2: any
   explicit paint suppresses defaults over its whole span, including `none`) get the §4.5
   defaults, which are emitted per terminal span / trivia node during the same walk and
   simply filtered against explicit coverage. Default intervals are disjoint by
   construction: terminal spans under one parent don't overlap, and the trivia
   non-descent rule (§4.5) removes the only nesting source — so no within-layer
   precedence is needed.

Kind-to-rule-name mapping for the walk: build `{node_kind_member_name(rule.name): rule}`
once from the grammar using the same naming the generator uses
(`gsm2tree.py:95, 262-266` — `kind` is a `NodeKind` discriminant on every generated node);
span-vs-node discrimination via the existing `kind == SpanKind.SPAN` convention
(`span_protocol.py:76-79`).

### 4.7 `AnalysisEngine` (the seam for M2+)

```python
class AnalysisEngine:
    @classmethod
    def from_paths(cls, grammar_path, lsp_path=None, *, start_rule=None) -> AnalysisEngine
    # grammar = plumbing.parse_grammar_file(...); config = load_lsp_config(...) or empty;
    # analysis parser = plumbing.generate_parser(prepare_analysis_grammar(grammar))

    def highlight(self, text: str) -> HighlightResult
    # HighlightResult: tokens: list[Token] | None, error: str | None  (parse failure →
    # tokens None, error carries plumbing's ErrorTracker-formatted message verbatim)
```

This is deliberately the exact object the M2 server wraps: it owns "grammar+specs →
parser+config once, then text → tokens many times." Stale-token serving, debouncing, and
diagnostics-as-`Diagnostic` are server policy layered on top; prefix-CST (M3) changes only
the internals of `highlight`. Startup cost (one runtime parser generation) is the ADR's
accepted profile.

### 4.8 `fltk-highlight` CLI

`fltk/lsp/highlight_cli.py`, typer app (typer is already a runtime dependency):

```
fltk-highlight --grammar lang.fltkg [--lsp lang.fltklsp] [--rule START_RULE] FILE
```

- Success: source rendered to stdout with a small fixed ANSI-color theme (one 16-color
  mapping per legend member; `declaration` modifier → bold; unpainted text passes
  through). Theme is a private table, not configurable surface, in round 1.
- `.fltklsp` load errors or FILE parse errors: formatted message to stderr, exit 1
  (matches `unparse_cli.py` behavior).
- Registered as the project's first console script: `[project.scripts] fltk-highlight =
  "fltk.lsp.highlight_cli:app"` (maturin supports `project.scripts`). This is new
  packaging surface for the wheel; the user confirmed keeping the CLI as a real console
  script (§9).

HTML output (ADR M1 mentions it) is deferred: it adds surface without exercising any new
semantics. The `Token` stream is renderer-agnostic, so it bolts on later.

## 5. Build wiring

- `Makefile` `gencode` gains one step, following the unparsefmt precedent exactly
  (`Makefile:267-270`):
  `uv run python -m fltk.fegen.genparser generate --protocol fltk/lsp/fltklsp.fltkg
  fltklsp fltk.lsp.fltklsp_cst --output-dir fltk/lsp`
  then the regen → `make fix` → commit flow per CLAUDE.md.
- No new dependencies (no pygls, no pygments/rich). No Rust changes. Bazel untouched.

## 6. Edge cases and failure modes

- **Target-text parse failure** → no tokens + diagnostic (engine returns error; CLI exits
  1). Degraded modes are M2/M3.
- **Valid anchor, zero occurrences in a given input** → no-op, by design (validity is
  about the grammar, not any one document).
- **Literal anchor vs. identical regex-matched text in the same rule** (rule has literal
  `"s"` and a regex that can produce `s`): provenance resolves literal-first, so both the
  default and an explicit `scope "s": …` treat such a span as the literal. Inherent
  text-level ambiguity; documented limitation, same family as `.fltkfmt`'s
  two-unlabeled-invocations limitation.
- **`INLINE`-bearing target grammars**: unsupported today at the parser-generator level
  (`gsm2parser.py:828-830` raises `NotImplementedError`). `prepare_analysis_grammar`
  rejects them up front with a clean, formatted error (§4.4) rather than letting the raw
  exception escape.
- **`label`/`rule`-named anchors flush against a colon**: visible parse error, documented
  with the whitespace workaround (§4.1).
- **Grammars with no `_trivia` rule** (clockwork): synthesized whitespace trivia
  (`gsm.py:477-504`) is whitespace-only → no comment tokens over plain whitespace (§4.5).
- **Overlapping explicit paints**: totally ordered by the §4.6 key; no ties possible
  (stmt_index is unique).
- **Unicode**: codepoint offsets throughout; ANSI rendering is offset-based slicing, so
  astral-plane text is safe. UTF-16 is M2.
- **Pathological config sizes**: resolution precomputes per-rule tables once; classify is
  one walk + one endpoint sweep, O(matches log matches) per parse.

## 7. How round 1 lays the roadmap foundation (and the deltas it makes)

- **M2 server**: wraps `AnalysisEngine`; `line_col()` (`span_protocol.py:127-139`) gives
  positions; formatting uses the existing unparse pipeline behind a second,
  standard-disposition parser (§4.4). Delta: the server holds two parser instances — a
  detail the ADR didn't have.
- **M3 prefix-CST**: purely a change inside `highlight()`'s parse step; `classify` already
  works on any subtree.
- **M4 defs/refs**: the grammar, config model, validation, and anchor resolution for
  `def`/`ref`/`namespace` all exist after round 1; M4 adds symbol-table construction, the
  `SymbolKind` mapping, and ref-site paint — no `.fltklsp` file written for round 1 ever
  changes. Def-site paint semantics are already live in round 1 (user decision, §9), with
  the explicit understanding that M4's design round may revise them.
- **M5 resolver / native fast path**: resolver is untouched by round 1. Delta: the native
  fast path (a) has no `rust_cst_module=` shortcut (§2.3), and (b) must build its pyo3
  module from `prepare_analysis_grammar` output, implying a future `genparser` flag.
  Both recorded here so M5's design starts from facts.
- **Roadmap shape delta**: M0+M1 merge into one round (rationale §1). Later milestones
  unchanged in intent.
- **Follow-up noted, not scheduled**: backport load-time anchor validation to `.fltkfmt`
  (§2.2), where today's typos silently no-op. Separately: if/when `gsm2parser` gains
  `INLINE` support, inline-aware classification (spliced-terminal tables, anchor
  resolution through `!` invocations) needs its own design round — round 1 rejects `!`
  grammars outright (§4.4).

## 8. Test plan (TDD; all under `fltk/lsp/`, colocated per repo convention)

- `test_fltklsp_parse.py` — the grammar: worked clockwork example from `fltklsp-spec.md`
  §4 parses; empty file; comments-only; every statement form; error cases (missing `;`,
  bad nesting, `rule` inside `rule`); the `label:`-flush quirk (both the failing spelling
  and the whitespace workaround).
- `test_lsp_config.py` — CST→model fidelity (indices, multi-block accumulation, hints vs
  modifiers, `none`); validation: each §4.3 rule's pass and fail cases, multi-error
  collection, error messages carry file:line:col; union semantics for unqualified global
  anchors; qualifier restriction.
- `test_analysis.py` — `prepare_analysis_grammar`: suppressed literal/regex/subtree
  surface as children with unchanged spans; node spans identical to the standard parser's
  on the same input; transform is idempotent; a grammar containing an `!` item is
  rejected with the clean unsupported-`INLINE` error (not a raw `NotImplementedError`).
- `test_classify.py` — a purpose-built mini-grammar covering every default-table row
  (word literal → keyword, punctuation set, operator, quote/digit/identifier regex texts,
  structural comment rule à la clockwork's `doc`, whitespace-only trivia emits nothing,
  trivia non-descent: `//` inside a structured comment stays `comment`, never `operator`);
  the contextual-keyword boundary (same spelling as option-key literal and as identifier
  in textually identical positions); painter precedence matrix (explicit-over-default,
  innermost-wins, rule-block-over-global, anchor-rank, later-wins, `none` occlusion,
  def-paint + `declaration` + explicit-beats-def-at-same-node); token-stream invariants
  (sorted, non-overlapping, merged, in-bounds) as property-style assertions on every case.
- `test_highlight_cli.py` — end-to-end: mini-grammar + spec + source → golden ANSI
  output; no-spec (defaults-only) run; parse-failure exit code + stderr; bad `--lsp` file
  exit path.
- Dogfood fixture: `fltk/lsp/fltklsp.fltklsp` — a spec for the spec language itself;
  test that it loads against `fltklsp.fltkg` and highlights a sample `.fltklsp` file.
- Existing suites (`uv run pytest`) stay green; `make gencode` produces zero diff after
  the committed generation.

## 9. Resolved questions (user decisions)

Both round-1 open questions were put to the user and answered; the answers are folded
into the body above and recorded here for provenance.

1. **Console-script registration — keep it.** Round 1 registers `fltk-highlight` as the
   project's first `[project.scripts]` entry (§4.8), not a `python -m`-only tool. The new
   wheel distribution surface is accepted.
2. **Def-site paint — live in round 1.** `def` statements paint declaration sites (kind's
   first segment + `declaration` modifier, per `fltklsp-spec.md` §3) as specified in
   §4.6, making the clockwork worked example fully functional now. This is not a freeze
   of phase-2 semantics: per the user, "Round 2 can change whatever it needs to" — M4's
   design round may revise def/ref semantics (§7 notes the same).

No open questions remain for round 1.
