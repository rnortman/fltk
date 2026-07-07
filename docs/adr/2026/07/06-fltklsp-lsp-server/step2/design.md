# Design — Round 2: `fltk-lsp`, the generic pygls language server (M2)

Status: draft for review (pre-freeze).

Provenance: the advisory docs (`README.md`, `brainstorm.md`, `fltklsp-spec.md`) remain
directional only. Round-1 code at HEAD (a17ba80) is authoritative for what exists;
`step2/exploration.md` records the code facts, re-verified by direct reads where this
design depends on them. Where this design deviates from the advisory docs or from
round-1 assumptions, §2 says so explicitly.

## 1. Round-2 scope: what and why

**Scope chosen: the ADR's M2 — the `fltk-lsp` server** — a generic pygls-based LSP server
invoked as `fltk-lsp --grammar lang.fltkg [--lsp lang.fltklsp] [--fmt lang.fltkfmt]
[--rule START_RULE] [--width N] [--indent N]`, serving: publish-diagnostics, semantic tokens (full + range),
folding ranges, selection ranges, and document formatting via the existing unparse
pipeline; with stale-token serving on parse failure and LSP position-encoding
negotiation. Plus the two small library extensions the server forces:
`AnalysisEngine.analyze()` (structured errors + CST exposure) and
`ParseResult.error_pos` in `fltk.plumbing`.

Why this cut, and not the alternatives:

- **The server is the product.** Everything in rounds 0–1 exists to power editor support
  for out-of-tree DSLs; `AnalysisEngine` was explicitly designed as "the exact object the
  M2 server wraps" (`engine.py:1-8`). The next unit of user-visible value is the server,
  and it is also the forcing function for the decisions no other milestone can force:
  position encoding, token-stream→LSP encoding, stale-serving policy, and the
  protocol-facing packaging surface.
- **M3 (prefix-CST) stays out.** It is a pure quality-of-degradation improvement whose
  central factual question is still open (whether `ApplyResult` carries a *useful* partial
  CST on failure — `step2/exploration.md`, Open factual questions). The server's
  stale-token policy covers the degraded mode meanwhile, and M3 lands later as "a change
  inside the engine's parse step" (`step1/design.md:480-481`) without touching any
  interface this round creates. Bundling an unresolved parser-internals investigation into
  the protocol round would put the riskiest work on the critical path of the most
  valuable deliverable.
- **M4 (defs/refs) stays out.** It is a semantics round (symbol tables, `SymbolKind`,
  ref resolution, namespace scoping) that deserves its own design against a working
  server; the spec itself reserves the syntax precisely so M4 can land without breaking
  files. Nothing in this round precludes it: document symbols, go-to-def, etc. are new
  handlers over the same per-document analysis this round builds.
- **Right size.** The round is substantial (new dependency, new CLI, position math,
  five features) but almost entirely *wiring of existing machinery*: the engine, the
  `ErrorTracker`, and the parse→unparse→render pipeline all exist. The two library
  changes are small and additive.

Explicitly out of round 2: prefix-CST exposure (M3), defs/refs semantics (M4), resolver
plugin and native fast path (M5), semantic-token **deltas** (`.../full/delta`),
completion, hover, document symbols, incremental text sync, a workspace config file
(ADR D4 mentions one; CLI flags only this round), HTML output for `fltk-highlight`,
TextMate export, and error recovery.

## 2. Deltas: corrections and revisions this round makes

### 2.1 `HighlightResult` is not enough for a server; the engine gains `analyze()`

Round 1's `HighlightResult` is `(tokens | None, error: str | None)` (`engine.py:26-36`).
A server needs two more things per analysis: the **CST** (folding and selection ranges
are tree queries, not token queries) and a **structured error position** (an LSP
`Diagnostic` needs a range, not a prose blob). Rather than widen `HighlightResult`,
the engine gains a richer sibling (§4.3); `highlight()` remains, delegating, so the CLI
and any external round-1 caller is untouched.

### 2.2 `plumbing.parse_text` must surface the failure offset (additive)

`parse_text` formats its error from `parser.error_tracker` and then discards the tracker
(`plumbing.py:193-199`); `ParseResult` carries only the formatted string
(`plumbing_types.py:26-32`). The tracker's `longest_parse_len` is a codepoint offset into
the source — `format_error_message` passes it directly to
`TerminalSource.pos_to_line_col` (`errors.py:131`), and `TerminalSource` consumes
literals/regexes by string index (`terminalsrc.py:248-261`). Fix: add
`error_pos: int | None = None` to `ParseResult` and populate it on the failure path
(§4.4). Additive, defaulted — no existing caller changes.

### 2.3 The engine's wall-clock promise is only partially dischargeable; recorded as a TODO

`engine.highlight`'s docstring assigns runaway parses (catastrophic regex backtracking,
non-terminating recursion) to "the long-lived server layer" (`engine.py:83-88`). This
round cannot fully honor that: analyses run on a Python worker thread, and threads cannot
be preempted. The server serializes analyses on one worker and stays *protocol*-responsive
during a long parse, but a truly non-terminating parse starves all later analyses.
Full enforcement needs process isolation or parser-level budgets — real design work that
would dominate this round. Disposition: documented limitation (§5) plus
`TODO(lsp-analysis-watchdog)` in `server.py` and `TODO.md`.

### 2.4 Position encoding: negotiate `utf-32` or `utf-16`; nothing FLTK-internal changes

All round-1 offsets are codepoints (`classify.Token`, `SpanProtocol`). LSP 3.17 lets a
server pick from the client's `general.positionEncodings`; `utf-32` **is** codepoints, so
when a client offers it, conversion is free. Otherwise the mandatory `utf-16` default
applies, and the server converts columns per line (§4.5). `utf-8` support is deliberately
omitted: every client must support `utf-16`, so `utf-8` adds byte-unit math for zero
coverage gain. FLTK's core (`SpanProtocol`, `Token`, the engine) stays codepoint-only —
conversion is a server-edge concern, exactly as round 1 assumed.

Related: LSP defines line separators as `\n`, `\r\n`, *and* `\r`, while
`TerminalSource.pos_to_line_col` and `Span.line_col` recognize only `\n`
(`terminalsrc.py:271`, `terminalsrc.py:133`). The server therefore uses its own
`LineIndex` (§4.5) for all protocol position math instead of reusing those — they remain
correct for their existing (parser-diagnostic) purpose and are not modified.

### 2.5 pygls is an optional extra, not a core dependency (new packaging decision)

Core `dependencies` stay `["astor", "typer"]` (`pyproject.toml:25`). The server's
dependency goes in `[project.optional-dependencies] lsp = ["pygls>=1.3,<2"]`; downstream
consumers who use FLTK only for parser generation pay nothing new. The `fltk-lsp` console
script is always installed (script entries can't be conditional on extras), so its CLI
module imports pygls lazily and, on `ImportError`, prints an actionable
"install `fltk[lsp]`" message and exits 1 (§4.1). This is new, deliberate packaging
surface, called out per CLAUDE.md's compatibility rules: one new console script, one new
extra. No existing surface changes.

pygls major version: `1.3` is the current stable line (LSP 3.17 via `lsprotocol`); 2.x is
pre-release at design time. The implementer verifies the current stable at implementation
time; the features used (feature registration, full text sync, publish-diagnostics,
stdio loop) exist in both lines, so a bump is contained to `server.py`/`server_cli.py`.

### 2.6 Server capabilities vs. the ADR's M2 list

The ADR's M2 line item (`README.md:107-108`) is implemented as written — diagnostics,
semantic tokens, folding ranges, selection ranges, document formatting,
stale-tokens-on-failure — with one confirmation and one refinement:

- Confirmed from `step1/design.md` §7: the server holds **two** parser instances — the
  engine's analysis-grammar parser for tokens/folding/selection, and a
  standard-disposition parser for the formatting path (the analysis CST contains
  suppressed terminals the unparser must never see).
- Refinement: formatting is registered **always**, with `FormatterConfig()` defaults when
  `--fmt` is absent. `formatter_config=None` is a first-class mode of the existing
  pipeline (`plumbing.py:311`), formatting only runs when a user explicitly invokes it
  (format-on-save is the user's own editor setting), and a `.fltkfmt`-less language still
  deserves deterministic formatting. The alternative (register only with `--fmt`) was
  considered and rejected as withholding a working feature to guard against a setting the
  user controls. A verify-reparse guard (§4.8) contains formatter bugs regardless.

### 2.7 Render geometry: `--width`/`--indent` flags; client `FormattingOptions` ignored (new decision)

`.fltkfmt` carries formatting *structure* (spacing, grouping, per-nest indent overrides,
`fmt_config.py:118`) but no global line width or indent unit; those live in
`RendererConfig` (`renderer.py:22-26`, defaults `indent_width=4`, `max_width=80`), which
`render_doc` constructs implicitly when no config is passed (`plumbing.py:422-433`). The
in-tree CLI formatter treats them as caller-supplied: `fltk-unparse` exposes `--width`
(default 80) and `--indent` (default **2**) and builds `RendererConfig` explicitly
(`unparse_cli.py:37-38, 125`). `fltk-lsp` does the same: `--width`/`--indent` flags with
`fltk-unparse`'s defaults (80/2 — so editor formatting and a downstream project's
CLI/CI `fltk-unparse` runs produce identical output out of the box), building an explicit
`RendererConfig` used in §4.8.

Client `FormattingOptions` (`tab_size` etc.) are **deliberately ignored** — a called-out
decision, not an oversight: render geometry is server-invocation configuration, so every
client of the same server invocation (and the project's CI formatter, given matching
flags) formats identically. Honoring per-client `tab_size` would make formatted output
depend on which editor asked, reintroducing exactly the churn the flags exist to prevent.

## 3. Deliverables and file layout

All new files under the existing `fltk/lsp/` package; two small edits elsewhere.

| File | Contents |
|---|---|
| `fltk/lsp/positions.py` | `LineIndex`: LSP-conformant line table + codepoint-offset ↔ LSP `Position` conversion in the negotiated encoding (§4.5) |
| `fltk/lsp/features.py` | pure feature logic: semantic-token legend + encoding, folding ranges, selection ranges (§4.6) |
| `fltk/lsp/server.py` | pygls wiring: capabilities, document lifecycle, debounce, executor, stale policy, formatting handler (§4.7–4.8) |
| `fltk/lsp/server_cli.py` | `fltk-lsp` typer CLI: arg parsing, startup validation, lazy pygls import (§4.1) |
| `fltk/lsp/engine.py` | add `ParseErrorInfo`, `DocumentAnalysis`, `AnalysisEngine.analyze()`, and two read-only properties (`source_grammar`, `trivia_kind_names`); `highlight()` delegates (§4.3) |
| `fltk/plumbing_types.py`, `fltk/plumbing.py` | `ParseResult.error_pos: int \| None = None`, populated in `parse_text` (§4.4) |
| `pyproject.toml` | `[project.optional-dependencies] lsp`, `fltk-lsp` script entry, `pytest-lsp` in the `test` group (§2.5, §6) |
| `TODO.md` | `lsp-analysis-watchdog` entry (§2.3) |
| `fltk/lsp/test_*.py`, `fltk/lsp/test_data/` | tests + a small fixture language (grammar/lsp/fmt triple) (§6) |

No generated artifacts change. No Rust changes. Bazel untouched (the server is
pure-Python runtime code; Bazel consumers get it through the Python package as usual).

## 4. Proposed approach

### 4.1 `fltk-lsp` CLI and startup (`server_cli.py`)

```
fltk-lsp --grammar lang.fltkg [--lsp lang.fltklsp] [--fmt lang.fltkfmt] [--rule START_RULE] [--width N] [--indent N]
```

A typer app registered as `[project.scripts] fltk-lsp = "fltk.lsp.server_cli:app"`,
mirroring `fltk-highlight`'s flag names and error style (`highlight_cli.py`); `--width`
(default 80) and `--indent` (default 2) mirror `fltk-unparse` (§2.7). Startup
sequence, fail-fast, before any protocol I/O:

1. Import `fltk.lsp.server`; on `ImportError` of pygls, print
   `fltk-lsp requires the 'lsp' extra: pip install 'fltk[lsp]'` to stderr, exit 1.
2. `AnalysisEngine.from_paths(grammar, lsp, start_rule=rule)` — this validates the
   grammar and `.fltklsp` (raising `LspConfigError`/`ValueError` with the existing
   formatted messages) and pays the analysis-parser generation once.
3. If `--rule` given: validate it against the grammar's rule names (the analysis
   transform preserves rule names, so one check covers the formatting parser too — the
   engine currently stores the name unchecked, `engine.py:47-57`, and a bad rule would
   otherwise surface only as a position-less "No parse method" diagnostic on every
   document, `plumbing.py:187-189`). Unknown rule → stderr message listing the valid
   rule names, exit 1.
4. If `--fmt` given: `plumbing.parse_format_config_file(path)` now, so a broken
   `.fltkfmt` is a startup error, not a surprise at first format request. The standard
   parser + unparser themselves are built lazily (§4.8).
5. Construct the server (§4.7) and `start_io()` (stdio transport; the standard editor
   arrangement, and the only transport this round).

Any exception in 2–4 → formatted message to stderr, exit 1 (matches
`highlight_cli.py:99-111`). Editors surface a failed server start in their logs; the same
command run by hand shows the same message. One server process serves one language
(one grammar); this is the LSP-standard one-server-per-language shape and is documented
in the CLI help.

### 4.2 Dependencies and packaging

Per §2.5: `lsp = ["pygls>=1.3,<2"]` extra; `pytest-lsp` added to the `test` dependency
group (`pyproject.toml:42-45`) for end-to-end tests (§6). No other new dependencies:
`lsprotocol` (the LSP type bindings) comes with pygls. `typer` is already core.

### 4.3 Engine extension: `analyze()` (`engine.py`)

```python
@dataclasses.dataclass(frozen=True)
class ParseErrorInfo:
    message: str          # the ErrorTracker-formatted message, verbatim (as today)
    offset: int | None    # codepoint offset of the furthest failure; None if unavailable

@dataclasses.dataclass(frozen=True)
class DocumentAnalysis:
    tree: Any | None                        # analysis-grammar CST root; None on failure
    tokens: list[classify.Token] | None     # None on failure
    error: ParseErrorInfo | None            # None on success

class AnalysisEngine:
    def analyze(self, text: str) -> DocumentAnalysis: ...
```

`analyze` is `highlight`'s body today (`engine.py:89-98`) with three changes: keep
`parsed.cst` in the result, carry `parsed.error_pos` into `ParseErrorInfo`, and map the
existing `RecursionError` catch to `ParseErrorInfo(message=..., offset=None)`.
`highlight()` becomes a thin wrapper (`analyze` → `HighlightResult(a.tokens,
a.error.message if a.error else None)`), preserving round-1 behavior and types exactly —
`fltk-highlight` and any out-of-tree caller of `highlight()` see no change.

The `tree` field is typed `Any` deliberately: analysis CSTs are per-grammar exec'd
classes with no cross-grammar base class (`brainstorm.md` §1); consumers walk them
structurally via `kind`/`span`/`children`, as `classify.py` already does.

The engine also gains two read-only properties the server needs, both exposing state the
engine already holds or receives:

- `source_grammar: gsm.Grammar` — the grammar passed to `__init__`, *pre*
  analysis-transform (the engine currently keeps only the transformed
  `self._parser_result.grammar`; `__init__` additionally stores the original — one line).
  The formatting pipeline (§4.8) must be built from this, never from the analysis
  variant.
- `trivia_kind_names: frozenset[str]` — the analysis-tree `kind` names whose rules are
  trivia rules, derived once in `__init__` from the engine's private tables
  (`self._tables.kind_to_rule`, filtering on `rule.is_trivia_rule`). Folding (§4.6) needs
  exactly this one bit per kind. The tables themselves (`_GrammarTables`,
  `classify.py:64-68`) stay private: publishing that underscore-private structure as
  engine API would freeze it right before its planned restructuring
  (`TODO(lsp-rule-surface-index)`, `classify.py:72`), creating the annotation-churn
  situation CLAUDE.md forbids. The names are built from the analysis grammar, which is
  exactly what the analysis tree's `kind` names resolve against.

### 4.4 `ParseResult.error_pos` (`plumbing.py`, `plumbing_types.py`)

`ParseResult` gains `error_pos: int | None = None`. `parse_text`'s failure branch
(`plumbing.py:193-199`) sets it to `parser.error_tracker.longest_parse_len` when that is
`>= 0`; otherwise (tracker never recorded a terminal failure — e.g. a rule succeeded
early without consuming all input and no alternative failed beyond it) to `result.pos`
when `result` is truthy, else `0`. The no-such-rule early return (`plumbing.py:189`)
leaves it `None` — that error has no source position. `parse_grammar` and
`parse_format_config` raise instead of returning `ParseResult` and are not touched.

This is a general-purpose improvement (M3's prefix exposure will want the same position),
not server-private plumbing — hence it lands in `plumbing` rather than being worked
around inside the engine.

### 4.5 Position math (`positions.py`)

One class, built once per analyzed document text, self-contained (no pygls types):

```python
class PositionEncoding(enum.Enum):
    UTF16 = "utf-16"
    UTF32 = "utf-32"

class LineIndex:
    def __init__(self, text: str) -> None: ...          # line-start offsets; \n, \r\n, \r
    def offset_to_position(self, offset: int, enc: PositionEncoding) -> tuple[int, int]
    def position_to_offset(self, line: int, character: int, enc: PositionEncoding) -> int
    def line_of(self, offset: int) -> int
    def line_bounds(self, line: int) -> tuple[int, int]  # [start, end) codepoints, excl. terminator
    def end_position(self, enc: PositionEncoding) -> tuple[int, int]
```

- Line table: LSP's three separators (`\n`, `\r\n`, `\r`), unlike
  `TerminalSource.pos_to_line_col` (§2.4). Lookup by `bisect` over line starts.
- `utf-32` column = codepoint column (free). `utf-16` column = codepoints in the line
  prefix counted as `1 + (ord(c) > 0xFFFF)` each — computed by slicing the line, O(line
  length), only in the utf-16 case.
- Everything clamps rather than raises: offsets beyond `len(text)` map to the end
  position; positions beyond a line's end map to the line's last valid offset; positions
  beyond the last line map to end-of-text. Clamping is the LSP-idiomatic behavior for the
  racy inputs a server sees (client and server momentarily disagree about the document).

Encoding negotiation lives in `server.py`, with **one owner**: the encoding the server
computes is, by construction, the encoding the client is told. pygls 1.x negotiates
`position_encoding` itself when building `ServerCapabilities`, and its supported set
includes `utf-8` — which `LineIndex` deliberately does not implement — so pygls's
negotiation must not be left free-running alongside the server's own picker (two
independent decision-makers is the coordinate-mixing bug class `_GoodAnalysis`, §4.7,
exists to rule out). Concretely: constrain pygls's supported-encodings set to `{utf-32, utf-16}`
if its API permits; otherwise set `ServerCapabilities.position_encoding` explicitly from
the server's picker (utf-32 if the client offers it, else utf-16), overriding whatever
pygls computed. Either way, the server then reads the *advertised* capability value back
and derives its `PositionEncoding` from that single value — there is exactly one
variable, and `LineIndex` math, token encoding, and every emitted `Range` use it. All
conversion *math* stays in `LineIndex`, so correctness never depends on pygls internals;
`test_server.py` pins that the advertised encoding and the encoding the emitted tokens
are computed in agree, including for a client that offers `utf-8` first (§6).

### 4.6 Feature logic (`features.py`)

Pure functions from `(DocumentAnalysis, LineIndex, PositionEncoding)` to lsprotocol
values; no server state, fully unit-testable.

**Semantic-token legend.** The wire legend needs *ordered* type/modifier lists;
round 1's `TOKEN_LEGEND` / `LSP_STANDARD_MODIFIERS` are frozensets
(`lsp_config.py:27-64`). `features.py` defines `SEMANTIC_TOKEN_TYPES: tuple[str, ...]`
(the 16 legend members, fixed order) and `SEMANTIC_TOKEN_MODIFIERS: tuple[str, ...]`
(the 10 standard modifiers, fixed order), each with a test asserting set-equality against
the round-1 frozensets so the pairs cannot drift. Order is negotiated per session at
`initialize`, so it carries no cross-version compatibility burden; it is still kept
stable for sanity. The four non-LSP-predefined members (`punctuation`, `text`,
`constant`, `label`) are registered as custom types exactly as `step1/design.md` §4.5
anticipated — legal per LSP (server-defined strings); unthemed clients simply don't
color them. Modifier bits: `classify` only ever emits modifiers from the standard set
(scope statements split non-standard segments into hints at load time; def-paint adds
`declaration`), so every `Token.modifiers` maps to legend bits — a defensive
`assert`-level check drops any unknown modifier rather than crashing the handler.

**`encode_semantic_tokens(tokens, line_index, enc) -> list[int]`.** Standard LSP
relative encoding, 5 ints per token. Tokens spanning multiple lines are **always split
at line boundaries** (one output token per covered line segment, skipping empty
segments) — legal whether or not the client advertises `multilineTokenSupport`, and one
code path instead of two. Whole-doc `comment` paints (e.g. clockwork's `doc` subtrees)
are the common multi-line case. `deltaStart` and `length` are computed in negotiated
units via `LineIndex`. Input tokens are already sorted and non-overlapping
(`classify.py` output invariants), so encoding is a single pass.

**`folding_ranges(tree, trivia_kind_names, line_index) -> list[FoldingRange]`.** Walk the
analysis tree; for every non-span node (`kind != SpanKind.SPAN`) compute
`start_line = line_of(span.start)`, `end_line = line_of(max(span.start, span.end - 1))`;
emit when `end_line > start_line`. Nodes of trivia rules get
`FoldingRangeKind.Comment` (kind-name membership in the engine's `trivia_kind_names`
property, §4.3); others get no kind. Deduplicate
by `(start_line, end_line)`, keeping the first (outermost) — nested nodes sharing line
extents would otherwise produce duplicates. Structural comment rules (clockwork's `doc`)
are *not* specially detected as comment folds this round — that would require consulting
paint config, and the fold still exists, just unkinded. Noted, not built.

**`selection_ranges(tree, offsets, line_index, enc) -> list[SelectionRange]`.** The
server converts each requested `Position` to a codepoint offset (`LineIndex`) before
calling. For each offset: walk from the root, collecting every node/span whose
`[start, end)` contains the offset; the innermost element (including terminal `Span`
children — word-level selection) becomes the head `SelectionRange`, each successive
ancestor its `parent`, skipping ancestors with an identical span (LSP requires
strictly-widening ranges); the chain's `Range`s are rendered via `line_index`/`enc`.

### 4.7 The server (`server.py`)

`create_server(engine, formatter_config, renderer_config, *, start_rule) ->
LanguageServer` builds and wires everything (`renderer_config` is the
`RendererConfig` built from `--width`/`--indent`, §2.7); `server_cli` calls it then
`start_io()`. Keeping construction separate from the CLI makes the server testable
in-process.

**Text sync: full.** `TextDocumentSyncKind.Full` — every parse is whole-document anyway
(no incremental reparse exists; `brainstorm.md` §1), so incremental sync would buy
string-splicing complexity and nothing else. pygls's `Workspace` manages document text
and versions; the server keeps only its own per-URI analysis state:

```python
@dataclasses.dataclass
class _DocState:
    analyzed_version: int | None = None
    analysis: DocumentAnalysis | None = None        # for analyzed_version's text
    line_index: LineIndex | None = None             # ditto
    last_good: _GoodAnalysis | None = None          # last successful parse, any version

@dataclasses.dataclass(frozen=True)
class _GoodAnalysis:
    version: int
    line_index: LineIndex
    tree: Any
    tokens: list[classify.Token]
    encoded_tokens: list[int]      # encoded once, against the matching text
```

`_GoodAnalysis` snapshots the *matching* `LineIndex` and pre-encoded token data so stale
serving can never mix coordinates from two document versions — the classic stale-token
corruption bug is ruled out by construction.

**Analysis scheduling.** All parsing/classification runs in a
`ThreadPoolExecutor(max_workers=1)` — one analysis at a time process-wide, protocol loop
never blocked. Two triggers:

- *Push (diagnostics)*: `didOpen` analyzes immediately; `didChange` debounces
  (`_DEBOUNCE_SECONDS = 0.2`, module constant, not configurable this round) by
  (re)scheduling a cancellable asyncio task per URI. When an analysis completes and its
  version still matches the workspace document, the server updates `_DocState` and
  publishes diagnostics (with the document `version`, so clients drop stale ones).
- *Pull (semantic tokens / folding / selection)*: async handlers `await` an
  analysis-for-current-version — reusing the in-flight one if the pending version
  matches, else submitting fresh. Per-URI single-flight bookkeeping prevents duplicate
  work when a request and the debounce timer race.

`didClose` drops the URI's state. `didSave` is a no-op.

**Diagnostics.** Success → publish `[]` (clears). Failure → publish one `Diagnostic`:
range from `ParseErrorInfo.offset` (converted via `LineIndex`; span of one codepoint,
zero-length at end-of-text; `offset=None` → zero-length at position 0,0), severity
`Error`, `source="fltk-lsp"`, message = the formatted message verbatim. The message
includes the source line + caret block — redundant next to an editor squiggle but
accurate; deriving a terser message from `ErrorTracker.expected_context` is deferred
until the completion milestone gives expected-sets a real consumer.
`.fltklsp`/`.fltkfmt`/grammar problems never become document diagnostics — they are
startup failures (§4.1).

**Stale-token policy (ADR D6).** `semanticTokens/full` returns, in order of preference:
current version's `encoded_tokens`; else `last_good.encoded_tokens` (computed against the
last-good text — positions may drift from what's on screen until the next successful
parse; that is the accepted tradeoff versus flicker-to-blank); else `[]`.
`semanticTokens/range` filters the same `Token` list (current-or-last-good) to tokens
overlapping the range, then delta-encodes the subset. Folding and selection ranges use
the same current-or-last-good tree with its matching `LineIndex`.

### 4.8 Document formatting (`server.py`, lazy)

Built on first `textDocument/formatting` request and memoized on the server:

1. `plumbing.generate_parser(engine.source_grammar)` — a **standard-disposition** parser
   (`capture_trivia=True`, the default) from the original grammar (§4.3), never the
   analysis transform: analysis CSTs contain suppressed terminals the generated unparser
   doesn't expect.
2. `plumbing.generate_unparser(...)` on the same grammar and the resulting
   `cst_module_name`, with the startup-parsed `FormatterConfig` (or defaults when
   `--fmt` absent, §2.6).

The build is exec-based codegen and can itself raise. Its failure disposition:
**memoized-as-failed** — any exception is caught, logged once via `window/logMessage`
(full detail), and the URI-independent "formatting unavailable" state is recorded;
subsequent formatting requests return `None` immediately with a one-line log, never
retrying multi-second codegen per keystroke. Recovery is a server restart (the inputs —
grammar and `.fltkfmt` — are fixed at startup, so retrying without a restart cannot
succeed).

Handler, per request. Client `FormattingOptions` (tab size etc.) are ignored; structure
comes from `.fltkfmt`, render geometry from the explicit
`RendererConfig(max_width=width, indent_width=indent)` built from the CLI flags — a
deliberate decision, rationale in §2.7. The whole sequence, including the lazy build,
runs on the same single-worker analysis executor (§4.7) — it is CPU-bound and must not
block the protocol loop. Steps 2–3 (and the build) are wrapped in a catch of
`Exception`, not just `ValueError`: the silent-`None` unparser-bug family this guard
exists for (c0534e3) can surface as `KeyError`/`AttributeError`/`TypeError` from
generated code, and any of those must degrade to "no edits + log", never a raw LSP
request error:

1. `parse_text` with the standard parser on the current document text. Failure → return
   `None` (no edits) and `window/logMessage` the parse error — formatting a broken
   document must never destroy it.
2. `unparse_cst` → `render_doc(doc, renderer_config)`. Any exception (including the
   unparser's "Unparsing failed" `ValueError` path, `plumbing.py:415-417`) → log,
   return `None`.
3. **Verify-reparse guard**: parse the rendered output with the same standard parser;
   failure → log loudly, return `None`. This doesn't prove semantic equality, but it
   blocks gross corruption from unparser bugs (the silent-`None` family diagnosed in
   c0534e3) at the cost of one extra parse per explicit format request.
4. If output equals input → `[]`; else one whole-document `TextEdit`
   (`Position(0,0)`..`LineIndex.end_position(enc)`).

## 5. Edge cases and failure modes

- **Client offers neither `utf-32` nor a `positionEncodings` capability** → `utf-16`
  (the LSP-mandated default every client supports).
- **Windows line endings in documents** — `LineIndex` handles `\r\n`/`\r` for protocol
  positions; whether the *grammar* accepts `\r` is a property of the grammar and surfaces
  as an ordinary parse diagnostic. Not the server's problem to paper over.
- **Requests before the first analysis completes** — pull handlers await the analysis;
  no empty-flash. A request for a URI the workspace doesn't know returns the feature's
  empty value.
- **Racy positions** (client edited while a request was in flight) — `LineIndex` clamps;
  stale-serving already tolerates version skew by design.
- **Astral-plane text** — the exact reason the utf-16 column math exists; pinned by
  tests (§6). Token *lengths* are also converted, not just starts.
- **Tokens at end-of-file / empty documents** — `Token` invariants keep spans within
  `[0, len(text))`; empty text yields empty legend data, no diagnostics, no folds.
- **Runaway analysis** (catastrophic regex, non-terminating recursion) — protocol stays
  responsive; that document's diagnostics/tokens stop updating and later analyses queue
  behind it. Documented limitation + `TODO(lsp-analysis-watchdog)` (§2.3).
  `RecursionError` specifically is already caught by the engine and becomes a normal
  parse-failure diagnostic (`offset=None` → position 0,0).
- **Formatter failure of any kind** → no edits, logged; never a partial or unverified
  edit (§4.8). Editors treat a `None` formatting result as a silent no-op; the log entry
  is the operator's breadcrumb.
- **`.fltklsp`/`.fltkfmt`/grammar errors** → startup failure with the existing formatted
  messages; never a running server that half-works.
- **Multiple `fltk-lsp` instances** (several languages, or several editors) — each is an
  isolated process with per-process state; nothing shared, nothing to design.
- **Stale tokens visibly misaligned during an edit burst** — inherent to the ADR D6
  policy until M3 (prefix CST) narrows the degraded region; accepted.

## 6. Test plan

New tests colocated in `fltk/lsp/`; fixture language (a small grammar + `.fltklsp` +
`.fltkfmt` triple exercising multi-line comment rules, astral-capable strings, and at
least one formatting-visible spacing rule) under `fltk/lsp/test_data/`.

- `test_positions.py` — `LineIndex`: all three separators, mixed; empty text; no trailing
  newline; astral characters (utf-16 vs utf-32 columns differ); offset↔position round
  trips; clamping (offset past EOF, character past line end, line past last);
  `end_position`.
- `test_engine_analyze.py` — `analyze()` returns tree+tokens on success; structured
  error with correct codepoint offset on failure; `RecursionError` → `offset=None`;
  `highlight()` output is byte-for-byte what round 1 produced (delegation regression
  pin).
- `test_plumbing_error_pos.py` — `error_pos` on: mid-input terminal failure,
  early-success-without-full-consumption, unknown start rule (`None`), success (`None`).
- `test_features.py` — legend tuples set-equal to `TOKEN_LEGEND`/`LSP_STANDARD_MODIFIERS`;
  delta encoding against hand-computed expectations; multi-line token split (incl. token
  ending exactly at a newline); utf-16 vs utf-32 encodings of the same tokens; folding:
  multi-line nodes fold, single-line don't, trivia nodes get `Comment` kind, duplicate
  extents deduped; selection: innermost-to-outermost chain, strictly widening,
  terminal-span head.
- `test_server.py` — end-to-end over `pytest-lsp` against the real `fltk-lsp` command
  with the fixture language: initialize (capabilities + negotiated encoding, for a
  utf-32-offering client, a utf-16-only client, **and** a client offering utf-8 first —
  which must be answered with utf-32 or utf-16, and in every case the emitted tokens'
  positions must agree with the *advertised* encoding, §4.5); didOpen → clean
  diagnostics + tokens; breaking edit → one error diagnostic at the right position
  **and** stale tokens still served; fixing edit → diagnostics clear, tokens fresh;
  folding + selection round trips; formatting: idempotent doc → `[]`, reformattable doc
  → one whole-doc edit whose application yields parseable text and honors
  `--indent`/`--width` (matching `fltk-unparse` output for the same flags, §2.7),
  unparseable doc → `None`; a formatter-pipeline build failure → `None` + logged, and a
  second request returns `None` without rebuilding (§4.8); didClose then re-open.
- `test_server_cli.py` — missing/invalid grammar, `.fltklsp`, `.fltkfmt`, and unknown
  `--rule` (message lists valid rules, §4.1) → stderr + exit 1 (no protocol traffic);
  pygls-missing path unit-tested by import-hook simulation.
- Existing suites stay green: `uv run pytest` (notably round-1 `fltk/lsp` tests —
  `highlight()` untouched), `uv run ruff check . && uv run pyright`.

## 7. How round 2 lays the roadmap foundation

- **M3 (prefix CST)**: `ParseResult.error_pos` (§4.4) is the first half of the surface M3
  needs (position of the failure); M3 adds the partial tree next to it and changes only
  `analyze()`'s parse step. The server's stale-serving code path becomes
  "stale-past-the-error" with no protocol changes.
- **M4 (defs/refs)**: document symbols, go-to-def, references, and rename are new
  handlers over the same `_DocState` per-document analysis; `DocumentAnalysis` grows a
  symbol table next to `tokens`. Nothing this round hard-codes tokens-only assumptions
  into the state model.
- **M5 (resolver / native fast path)**: untouched. The engine remains the single seam a
  native analysis parser would slot into; the server never touches parser internals.
- **Completion (spec OQ4)**: `ErrorTracker.expected_context` survives to the server edge
  now that `parse_text` failure state is partially surfaced; a future round can widen
  `ParseErrorInfo` with expected-sets without touching the protocol layer built here.
- **Deferred, recorded**: semantic-token deltas (`.../full/delta`) — worthwhile only if
  full-token payloads prove heavy in practice; workspace config file (ADR D4) — flags
  cover the one-language case; comment-kind folds for structural comment rules (§4.6);
  terser diagnostic messages from expected-sets (§4.7).

## 8. Open questions

None. Three judgment calls were decided rather than deferred, with rationale recorded
for review: pygls as an optional `fltk[lsp]` extra (§2.5), formatting registered without
`--fmt` using default config (§2.6), and render geometry from `--width`/`--indent` flags
with client `FormattingOptions` deliberately ignored (§2.7). All are called-out,
deliberate additions to public surface per CLAUDE.md; reviewers should treat them as
challengeable decisions, not settled precedent.
