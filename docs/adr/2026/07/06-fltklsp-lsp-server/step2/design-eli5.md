# ELI5 -- Building the `fltk-lsp` Language Server (Round 2 / Milestone M2)

## What this is about

FLTK is a toolkit for building parsers and compilers. You give it a grammar file (a `.fltkg` file), and it generates a parser that can read source code written in that grammar's language and produce a structured tree (a "Concrete Syntax Tree," or CST) representing the parsed source.

FLTK's main consumers are external projects that define their own domain-specific languages (DSLs). One such project, clockwork, has its own grammar and uses FLTK to parse clockwork source files. But today, when someone opens a clockwork file in their editor, they get nothing -- no syntax coloring, no red-squiggle error diagnostics, no code folding, no automatic formatting. The grammar already describes the language's structure in enough detail to power all of those features, but there is no bridge between FLTK's parsing machinery and the Language Server Protocol (LSP) that editors speak.

This design builds that bridge: a program called `fltk-lsp` that any FLTK-based language can use to get editor support, with no per-language server code required.

### What already exists (rounds 0 and 1)

Two earlier rounds of work laid the groundwork:

- A sidecar spec language called `.fltklsp`. A language author writes a short `.fltklsp` file alongside their grammar to tell the system things the grammar alone cannot express -- for example, that a particular keyword should be colored as a "type" rather than a generic "keyword," or that comment-like rules should be treated as comments for highlighting purposes. The `.fltklsp` file is loaded and validated against the grammar at startup.

- An `AnalysisEngine` class that takes a grammar (and optionally a `.fltklsp` spec), parses source text, and produces a list of classified tokens -- each token carrying a start/end position, a type (like "keyword" or "comment"), and optional modifiers (like "declaration"). This engine already does the hard classification work. It also transforms the grammar internally so that normally-hidden punctuation and keywords appear in the parse tree, which is what makes per-occurrence classification possible.

- A CLI tool called `fltk-highlight` that uses the engine to print ANSI-colored source code to the terminal. This was the first consumer of the classification engine and served as its test harness.

- A formatting pipeline: given a grammar and an optional `.fltkfmt` formatting spec, FLTK can parse source code, "unparse" its CST into an abstract layout document, and render that document to reformatted text. This pipeline is what powers deterministic code formatting for FLTK-based languages.

All of this machinery exists and is tested. What does not exist is the LSP server that wraps it for editor consumption.

## The design at a high level

This round builds `fltk-lsp`, a generic LSP server, plus two small additions to FLTK's core library that the server needs. The server is a Python program using the `pygls` library (a Python implementation of LSP) that communicates with editors over the standard LSP protocol. It provides five features:

1. **Diagnostics** -- red-squiggle parse errors, published to the editor as the user types.
2. **Semantic tokens** -- fine-grained syntax coloring driven by the classification engine.
3. **Folding ranges** -- collapsible regions in the editor, derived from multi-line CST nodes.
4. **Selection ranges** -- "expand selection" in the editor, walking from the innermost syntax node outward.
5. **Document formatting** -- reformat-on-demand using the existing unparse/render pipeline.

The server also handles a graceful degradation policy: when a document has a parse error and cannot be fully analyzed, the server serves the token data from the last successful parse rather than showing the user a blank, uncolored file.

### Why this scope, and not more or less

The server is the product -- everything built so far exists to power editor support, and the server is where that value is delivered. But the design deliberately excludes several things that could have been included:

- **Prefix-CST (milestone M3)** is about improving the degraded-mode experience by showing fresh tokens for the part of the file before the error, rather than stale tokens for the whole file. This requires investigating whether FLTK's parser internals actually produce a useful partial tree on failure -- a question that is still open. Bundling an unresolved parser-internals investigation into the server round would put the riskiest work on the critical path of the most valuable deliverable. The stale-token policy covers the gap in the meantime.

- **Definitions and references (M4)** -- go-to-definition, find-references, document symbols -- are semantics features that need their own design round (symbol tables, namespace scoping, reference resolution). The `.fltklsp` spec already reserves the syntax for these features so they can be added later without breaking existing spec files. Nothing in this round's design prevents M4 from landing as new handlers over the same per-document analysis state.

- **Resolver plugins (M5)** and several other features (completion, hover, incremental text sync, semantic-token deltas) are all explicitly deferred.

The result is a round that is substantial -- a new dependency, a new CLI entry point, position math, five LSP features -- but is almost entirely wiring of existing machinery rather than building new algorithms.

## How the pieces fit together

### The CLI entry point

The server is invoked as:

```
fltk-lsp --grammar lang.fltkg [--lsp lang.fltklsp] [--fmt lang.fltkfmt] [--rule START_RULE] [--width N] [--indent N]
```

One server process serves one language (one grammar). This is the standard LSP pattern -- an editor spawns a separate server process for each language it needs to support. The flags tell the server which grammar to use, optionally which `.fltklsp` classification spec and `.fltkfmt` formatting spec to apply, which grammar rule to start parsing from, and what line width and indent size to use for formatting.

The startup sequence is deliberately fail-fast: the server validates the grammar, the `.fltklsp` spec, and the `.fltkfmt` spec before doing any protocol I/O. If anything is wrong -- a malformed grammar, an invalid `.fltklsp` anchor, a broken `.fltkfmt` file, an unknown start rule -- the server prints a clear error to stderr and exits. Editors surface failed server starts in their logs, and the same command run by hand in a terminal shows the same message. This means configuration errors are always caught immediately at startup rather than surfacing as confusing runtime failures on the first document the user opens.

One specific startup validation is new: if `--rule` is specified, it is checked against the grammar's actual rule names. Without this check, a bad rule name would only surface as a cryptic "No parse method" diagnostic on every document, with no indication of what went wrong.

### Packaging: pygls as an optional dependency

FLTK's core purpose is parser generation and code generation. Most consumers of FLTK never run an LSP server -- they just generate parsers and use them. The design therefore makes `pygls` (the LSP library) an optional dependency, installed via `pip install fltk[lsp]` rather than being pulled in by every `pip install fltk`.

There is a subtlety here: Python packaging does not allow console scripts (like `fltk-lsp`) to be conditionally installed based on extras. The `fltk-lsp` command is always installed, but it imports `pygls` lazily -- if `pygls` is not available, it prints a clear message telling the user to install `fltk[lsp]` and exits.

### Two small library additions the server needs

**A richer analysis result from the engine.** The existing `AnalysisEngine.highlight()` method returns tokens and an error string. A server needs two more things: the CST itself (because folding ranges and selection ranges are tree queries, not token queries) and a structured error position (because an LSP diagnostic needs a line/column range, not just a prose error message). Rather than changing `highlight()`'s return type and breaking existing callers, the engine gains a new `analyze()` method that returns a richer `DocumentAnalysis` object containing the CST, the tokens, and a structured `ParseErrorInfo` (with both the formatted message and a codepoint offset). The existing `highlight()` method is rewritten as a thin wrapper around `analyze()`, so its behavior and return type are preserved exactly -- the CLI tool and any external caller see no change.

The engine also gains two new read-only properties the server needs:

- `source_grammar` -- the original grammar, before the analysis transform that promotes suppressed items. The formatting pipeline must be built from the original grammar, not the analysis variant, because analysis CSTs contain extra terminals that the unparser does not expect.

- `trivia_kind_names` -- the set of CST node kinds that correspond to trivia rules (like comments and whitespace). Folding ranges need this to mark comment folds with the right kind, so editors can fold comments differently from code.

Both properties expose information the engine already holds internally; they are just making it accessible.

**An error position in `ParseResult`.** Down in FLTK's plumbing layer, when a parse fails, the `ParseResult` object carries a formatted error string but discards the numeric position of the failure. The error tracker inside the parser knows exactly where in the source text parsing got stuck (its "furthest failure" position), but that number is used only to format the error string and then thrown away. The design adds an `error_pos` field to `ParseResult` so this position is preserved. This is a general-purpose improvement -- the prefix-CST work in M3 will also want this position -- so it lands in the core plumbing rather than being worked around inside the server.

### Position math: bridging codepoint offsets and LSP positions

All of FLTK's internal position tracking uses codepoint offsets -- each character in the source text, regardless of how many bytes it takes to encode, counts as one unit. LSP, however, allows clients and servers to negotiate which unit to use for column numbers. The three options are UTF-32 (which is codepoints -- exactly what FLTK uses), UTF-16 (which counts surrogate pairs for characters outside the Basic Multilingual Plane as two units), and UTF-8 (which counts bytes).

The server negotiates with the client at startup. If the client supports UTF-32, the server picks it, and conversion is free -- FLTK's codepoint offsets are already UTF-32 columns. Otherwise, the server falls back to UTF-16, which is the mandatory default that every LSP client must support. UTF-8 support is deliberately omitted: since every client already supports UTF-16, adding UTF-8 would mean implementing byte-unit math for zero additional coverage.

A new `LineIndex` class handles all the conversion. It is built once per document text and provides bidirectional conversion between codepoint offsets and LSP line/column positions in the negotiated encoding. It handles all three line-ending conventions LSP requires (`\n`, `\r\n`, and `\r`) -- this is different from FLTK's existing line/column utilities, which only recognize `\n`. The existing utilities are correct for their purpose (parser diagnostics) and are not modified; the server uses its own `LineIndex` for all protocol-facing position math.

One important design constraint: the negotiated encoding must be a single, unambiguous value that flows through the entire server. There must never be a situation where one part of the server thinks it is using UTF-16 columns while another part thinks it is using UTF-32. The design achieves this by having one owner for the encoding decision -- the server reads the encoding it advertised to the client and derives everything from that single value. If `pygls` (the LSP library) has its own encoding negotiation, the server constrains or overrides it so the two cannot disagree. Tests pin that the advertised encoding and the encoding used to compute token positions always match.

`LineIndex` clamps out-of-bounds inputs rather than raising errors. An offset past the end of the file maps to the last position; a column past the end of a line maps to the line's last character. This is the LSP-idiomatic behavior for the inherently racy inputs a server sees -- the client and server may momentarily disagree about the document's contents because an edit is in flight.

### Feature logic: from analysis results to LSP responses

The five features are implemented as pure functions that take a `DocumentAnalysis`, a `LineIndex`, and the negotiated encoding, and return LSP protocol objects. They have no server state and are independently unit-testable.

**Semantic tokens.** LSP's semantic token protocol requires an ordered legend (a list of token types and modifiers) and a stream of integers encoding each token's position relative to the previous token. The classification engine's output is a sorted, non-overlapping list of tokens with string-valued types and modifiers -- the feature logic maps these to legend indices and produces the integer stream.

One detail: tokens that span multiple lines are always split at line boundaries into one output token per line segment. This is legal regardless of whether the client advertises multi-line token support, and it means the server has one code path instead of two. Multi-line comment tokens (like clockwork's structural `doc` subtrees) are the common case where this matters.

**Folding ranges.** The server walks the analysis CST and emits a folding range for every node that spans more than one line. Nodes from trivia rules (comments, whitespace) are marked with the "comment" folding kind so editors can fold them separately. Duplicate ranges (nested nodes that happen to share the same start and end lines) are deduplicated.

**Selection ranges.** When the user triggers "expand selection," the editor sends positions and the server returns a chain of increasingly wider ranges. The server walks from the CST root, collecting every node whose span contains the requested position, then builds the chain from innermost to outermost, skipping nodes with identical spans (LSP requires strictly widening ranges). Terminal spans (individual keywords, identifiers) serve as the innermost, word-level selection.

### The server itself: lifecycle, scheduling, and stale serving

**Text synchronization.** The server uses full-document sync -- every time the user types, the editor sends the entire document text. This is the simplest mode and costs nothing extra here because FLTK has no incremental reparsing; every analysis is a full parse of the whole document anyway.

**Per-document state.** The server maintains state per open document: the most recent analysis result (tokens, CST, line index) and a snapshot of the last successful analysis. The last-good snapshot is the key to the stale-serving policy -- when a parse fails, the server can still serve the tokens and tree from the last time the document parsed successfully.

The last-good snapshot bundles together the line index, tree, tokens, and pre-encoded token data that were all computed against the same document text. This bundling is a deliberate design choice to prevent a subtle bug: if stale tokens (computed against an old version of the text) were converted using a line index built from the current text, the positions would be wrong. By keeping the matching line index alongside the stale tokens, the server can never accidentally mix coordinates from two different document versions.

**Analysis scheduling.** All parsing and classification runs on a single background thread, so the protocol loop (which handles editor messages) is never blocked by a slow parse. Two mechanisms trigger analysis:

- Push (for diagnostics): opening a document triggers immediate analysis; edits are debounced with a 200ms delay, so rapid typing does not cause a flood of re-parses.
- Pull (for tokens, folding, selection): when the editor requests these features, the server awaits an analysis of the current document version, reusing one that is already in flight if the version matches.

Per-document bookkeeping prevents duplicate work when the debounce timer and a pull request race each other.

**Diagnostics.** On a successful parse, the server publishes an empty diagnostic list (clearing any previous error). On a failed parse, it publishes a single error diagnostic whose range is derived from the structured error position. The diagnostic message is the full formatted error string from the error tracker, including the source line and caret -- somewhat redundant next to an editor squiggle, but accurate. A more concise message format is deferred to a future milestone.

**Stale-token policy.** When the editor asks for semantic tokens, the server returns (in order of preference): the current version's tokens if available, the last-good version's tokens if a current analysis has not succeeded, or an empty list if no successful parse has ever occurred. The accepted tradeoff is that stale tokens may be visually misaligned during an edit burst -- they were computed against an older version of the text, so positions may have shifted. This is inherent to the approach and is the accepted cost of avoiding a flash to completely uncolored text. The prefix-CST work in M3 will narrow the misaligned region.

### Document formatting

Formatting is built lazily -- the server does not construct the formatting pipeline at startup, but on the first formatting request. This is because the pipeline involves code generation (building a parser and unparser from the grammar), which is expensive. If the user never formats, the cost is never paid.

The formatting pipeline requires a second parser instance built from the original grammar (not the analysis-transformed grammar). This is because the analysis transform promotes suppressed terminals so they appear in the CST, but the unparser was generated against the original grammar and does not expect those extra terminals. The design keeps these two parsers strictly separate.

**Why formatting is always available, even without a `.fltkfmt` file.** When no `--fmt` flag is given, the server still registers the formatting capability, using default formatting settings. The rationale: formatting only runs when a user explicitly invokes it (or has format-on-save enabled in their editor, which is the user's own choice), and a language without a `.fltkfmt` file still gets deterministic formatting from the defaults. The alternative -- only registering formatting when `--fmt` is provided -- was considered and rejected as withholding a working feature to guard against a setting the user controls.

**Render geometry.** The `--width` and `--indent` flags control the line width and indent size used for formatting. These are deliberately server-invocation settings, not per-editor settings. The design explicitly ignores the editor's `FormattingOptions` (which include `tab_size`). The rationale: formatting output should be identical regardless of which editor triggers it, and should match what the project's CI formatter produces (given matching flags). If the server honored each editor's `tab_size`, formatted output would depend on which editor asked, reintroducing exactly the formatting churn the flags exist to prevent.

**Safety guards.** The formatting handler has several layers of protection:

- If the document cannot be parsed, formatting returns no edits (never destroys a broken document).
- If the unparse or render step throws any exception, formatting returns no edits and logs the error. The catch is deliberately broad (any `Exception`, not just `ValueError`) because unparser bugs can surface as various unexpected exception types from generated code.
- A verify-reparse guard: after formatting, the server parses the formatted output with the same parser. If the formatted output does not parse, something went wrong in the formatter, and the server returns no edits rather than corrupting the user's file. This does not prove the formatted output is semantically identical to the input, but it blocks gross corruption.
- If the formatting pipeline itself fails to build (the code-generation step throws), the failure is memoized. Subsequent formatting requests return immediately without retrying, because the inputs (grammar and `.fltkfmt` file) are fixed at startup and retrying cannot succeed. Recovery requires restarting the server.

## What could go wrong and how it is handled

**Runaway parses.** The engine's documentation assigns responsibility for timeouts on runaway parses (catastrophic regex backtracking, non-terminating recursion) to "the long-lived server layer." This round cannot fully honor that promise. Analyses run on a Python worker thread, and Python threads cannot be forcibly terminated. The server stays protocol-responsive during a long parse (the protocol loop is not blocked), but a truly non-terminating parse will starve all subsequent analyses for that server process. Full enforcement would need process isolation or parser-level budgets -- real design work that would dominate this round. This is documented as a known limitation with a TODO for future work. `RecursionError` specifically is already caught by the engine and converted to a normal parse-failure diagnostic.

**Windows line endings.** The `LineIndex` correctly handles `\r\n` and `\r` for LSP position math. Whether the grammar itself accepts `\r` in source text is a property of the grammar, not the server -- if it does not, the user gets a parse error, which is the correct behavior.

**Requests arriving before the first analysis completes.** Pull handlers (semantic tokens, folding, selection) await the analysis rather than returning empty data, so the user does not see a flash of uncolored text on file open.

**Race conditions between edits and requests.** The `LineIndex` clamps out-of-bounds positions, and the stale-serving policy tolerates version skew by design.

**Characters outside the Basic Multilingual Plane** (emoji, CJK extensions, etc.). This is the exact reason the UTF-16 column math exists. Token lengths, not just start positions, are converted to the negotiated encoding. Tests cover this case explicitly.

**Formatter failures of any kind.** No edits are applied, a log entry is written, and the editor treats the null result as a silent no-op. The user's document is never partially edited.

**Configuration errors.** Grammar, `.fltklsp`, and `.fltkfmt` problems are all startup failures with clear error messages. The server never runs in a half-configured state.

**Multiple server instances.** Each `fltk-lsp` process is isolated with its own state. Multiple instances (for different languages, or different editor windows) do not interact.

## What is still open

The design declares no open questions. Three decisions are explicitly flagged as challengeable -- meaning they are made and reasoned about, but the author invites reviewers to push back:

1. **pygls as an optional `fltk[lsp]` extra** rather than a core dependency. The reasoning is that most FLTK consumers only generate parsers and should not pay for an LSP library they never use. The tradeoff is a slightly more complex installation story for LSP users (`pip install fltk[lsp]` instead of just `pip install fltk`).

2. **Formatting registered even without a `--fmt` flag**, using default config. The reasoning is that formatting only runs on explicit user action and works fine with defaults. A reviewer might argue that offering formatting without a spec is surprising or that defaults might not produce good output for all grammars.

3. **Client `FormattingOptions` deliberately ignored**, with render geometry coming from `--width`/`--indent` flags instead. The reasoning is consistency: all editors and CI should produce the same formatted output. A reviewer might argue that ignoring editor settings violates the principle of least surprise for users who have configured their editor's tab size.

## How this sets up future work

The design is shaped so future milestones can land without breaking what this round builds:

- **Prefix-CST (M3)** will change only the engine's parse step. The server's stale-serving code path becomes "stale past the error point" with no protocol changes needed.
- **Definitions and references (M4)** will add new LSP handlers (document symbols, go-to-definition, find-references) over the same per-document analysis state. The `DocumentAnalysis` type can grow a symbol table field without affecting existing features.
- **Resolver plugin (M5)** slots into the engine, which remains the single seam between the server and parser internals.
- **Completion** can reuse the error tracker's expected-token sets, which are now surfaced to the server edge through the structured `ParseErrorInfo`.
