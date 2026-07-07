# ELI5: Building a syntax highlighter for any FLTK-based language

This document explains the round-1 design for `.fltklsp` support -- a new configuration language and highlighting engine -- assuming zero prior knowledge of FLTK or this codebase. It is a plain-language rendering of the design doc; every decision described here originates there.

## The problem, from scratch

FLTK (Formal Language ToolKit) is a Python library for building parsers and compilers. You write a grammar file (`.fltkg`) that describes a language's syntax, and FLTK generates a parser that can read source code in that language and produce a structured tree of what it found -- a Concrete Syntax Tree (CST). The key audience is *other projects* that use FLTK to define their own domain-specific languages (DSLs). One such project is "clockwork," a real DSL for hardware configuration that lives outside the FLTK repository.

None of these FLTK-powered languages currently have editor support. No syntax highlighting, no error squiggles as you type, no "go to definition." The long-term goal is a Language Server Protocol (LSP) server -- a background process that editors talk to for smart code features. But the first step, and the subject of this design, is the foundation that such a server would build on: a way to describe how the tokens of a given language should be classified (this keyword is a "keyword," that string is a "string," this identifier is a "type"), and a tool to verify the results.

### Why a grammar alone is not enough

You might think the grammar already contains enough information to figure out what to highlight. After all, it knows which things are literal keywords, which are regular expressions matching identifiers, and so on. The design investigated this by running a mechanical grammar-only classifier against clockwork's real grammar. The results were informative:

- Actual keywords like `cog` and `execute when` were classified correctly.
- But boolean values (`true`, `false`), unit suffixes (`s`, `ms`), and enum values (`single`, `multiple`) all collapsed into "keyword" because they are all defined as literal strings in the grammar. They should each be a different color.
- Comments in clockwork are defined as a structural grammar rule called `doc`, not as the special "trivia" mechanism FLTK uses for whitespace and comments. A grammar-only classifier does not know that `doc` is a comment -- it gets no highlighting at all.
- Type names like `Float64` look identical to variable names like `engine_monitor` because both are parsed by the same regex. Only a human (or a small annotation file) can say which labels carry type information.

The conclusion: a grammar gives you the segmentation for free (the parser already knows exactly where each token starts and ends, and which grammar rule matched it), but the *classification* of those segments needs a small amount of human-authored guidance. That guidance is what the `.fltklsp` file provides.

## What this round delivers

The original roadmap laid out six milestones (M0 through M5). This round merges M0 and M1 into a single delivery. It produces:

1. **The `.fltklsp` language** -- a new configuration format for describing how to classify tokens. This includes the grammar definition, a parser generated from it, and committed generated code.
2. **A config loader with validation** -- code that reads a `.fltklsp` file, cross-checks every name in it against the target grammar (catching typos at load time, not silently at runtime), and produces a resolved configuration.
3. **A classification engine** -- the logic that takes a parsed CST and the resolved configuration and produces a stream of classified tokens.
4. **`fltk-highlight`, a command-line tool** -- a standalone program that loads a grammar and an optional `.fltklsp` file, parses a source file, and prints it to the terminal with ANSI color highlighting.

Explicitly *not* in this round: the actual LSP server, partial parsing on errors, cross-file navigation, symbol tables, or HTML output.

### Why merge M0 and M1?

Three reasons drove the decision to combine the grammar/loader milestone with the CLI highlighter milestone:

- The grammar is the hard-to-reverse artifact. Once external projects write `.fltklsp` files, the language becomes public API with strong backward-compatibility obligations. Getting the full language surface right (including the phase-2 `def`/`ref`/`namespace` syntax, even though those features stay mostly inert) justifies doing it in one careful pass.
- M0 by itself has no end-to-end consumer. Classification rules that look correct on paper might be wrong against a real tree. The CLI highlighter forces every piece to work together and makes the results visible.
- Working through the details revealed a genuine technical gap (described next) whose fix belongs in the same round as the classifier it enables.

## The suppressed-terminals problem

This is the single most consequential technical discovery in the design process, and it drove a significant architectural decision.

### How FLTK grammars handle terminals

In an FLTK grammar, every item (keyword, punctuation mark, regex-matched token) has a "disposition" that controls whether it appears in the parsed tree:

- **INCLUDE** (`$`): the item shows up as a child of its parent node in the CST.
- **SUPPRESS** (`%`): the item is parsed and matched, but then *thrown away* -- it does not appear in the tree.
- **INLINE** (`!`): not implemented in the current parser generator; grammars using it cannot be loaded at all.

The critical rule: when a grammar author writes an unlabeled literal or regex (which is the common case for keywords and punctuation), FLTK defaults to SUPPRESS. So in a clockwork rule like `channel_name := "name" , ":" , expr`, neither the keyword `"name"` nor the colon `":"` exists in the parsed tree. They are gaps -- the parser consumed them, verified they were there, but did not record them as children.

### Why this matters for highlighting

The entire highlighting approach is "parse the source code, then walk the tree and paint each node." But if keywords and punctuation are not *in* the tree, there is nothing to paint. The advisory brainstorm documents proposed classifying tokens by looking at CST children, but those children do not exist for most of the things you want to highlight.

### The solution: the analysis grammar

The design introduces a "GSM-level transform" -- a function called `prepare_analysis_grammar` that takes a grammar and returns a modified copy where every SUPPRESS disposition is replaced with INCLUDE. Because disposition only affects whether a child is recorded in the tree (not whether the parser matches it), the modified grammar parses exactly the same language with exactly the same spans. But now every terminal the parser touched shows up as a child node, available for the classifier to inspect.

This modified grammar is used only internally by the analysis engine. It is never written to disk, and the fatter CST nodes it produces are invisible to downstream consumers. The engine generates a parser from the analysis grammar in memory at startup using FLTK's existing runtime parser-generation machinery.

### The alternative that was rejected

An approach called "gap scanning" was considered: keep the normal CST, compute which byte ranges are gaps (parent span minus child spans), and try to figure out which suppressed terminals live in each gap. This was rejected because it would mean re-implementing lexing heuristically. Multiple suppressed items can share a single gap, and suppressed rule invocations (not just simple terminals) can put entire sub-languages in gaps. The analysis-grammar transform gets exact spans from the parser that already did the work, at the cost of one extra in-memory parser variant and somewhat larger trees.

### The INLINE disposition

Grammars using the INLINE (`!`) disposition cannot be processed at all, because the parser generator itself raises a `NotImplementedError` on any INLINE item. Rather than letting that raw error escape, `prepare_analysis_grammar` scans for INLINE dispositions up front and raises a clear, formatted error message explaining the limitation.

## The `.fltklsp` language

The `.fltklsp` format belongs to the same language family as `.fltkfmt` (FLTK's existing formatting configuration): `//` line comments, semicolon-terminated statements, global statements plus `rule <name> { ... }` blocks for rule-specific overrides, and anchors that name positions in the grammar. Sharing this family means authors of FLTK-powered languages learn one addressing idiom for both formatting and editor-tooling configuration.

### What you can write

A `.fltklsp` file contains statements of several kinds:

- **`scope`** statements assign a token type (like `keyword`, `comment`, `type`, `constant`) to one or more anchors. An anchor can be a label name, a rule name, or a quoted literal. Example: `scope doc: comment;` says "every occurrence of the `doc` rule is a comment." `scope boolean, unit_identifier: constant;` says "every occurrence of `boolean` or `unit_identifier` is a constant."

- **`rule` blocks** scope statements to a specific grammar rule. `rule condition_spec { scope "time_since_last_exec": function; }` says "inside `condition_spec`, the literal `time_since_last_exec` is a function."

- **`def`** statements mark definition sites (this is where a symbol is defined). Parsed and validated in round 1, but only the highlighting effect (painting definition sites) is active; the full symbol-table machinery comes in a later milestone.

- **`ref`** statements mark reference sites (this is where a symbol is used). Parsed and validated in round 1 but semantically inert.

- **`namespace`** statements mark a rule as introducing a lexical scope. Parsed and validated in round 1 but semantically inert.

The language is designed so that `.fltklsp` files written today -- including the phase-2 `def`/`ref`/`namespace` statements -- remain valid and unchanged when later milestones land. This is a deliberate forward-compatibility commitment.

### Scope names and the token legend

The first segment of a scope name must be one of a fixed set of token types: `keyword`, `comment`, `string`, `number`, `operator`, `punctuation`, `variable`, `parameter`, `property`, `type`, `function`, `enumMember`, `constant`, `macro`, `label`, `text`, or the special value `none` (which suppresses all highlighting for that span). Additional dot-separated segments after the first become either LSP semantic-token modifiers (if they match standard modifier names like `declaration`, `readonly`, `deprecated`) or free-form hints (carried for future use by the CLI theme layer, dropped in LSP output).

Four of these token types (`punctuation`, `text`, `constant`, `label`) are not in LSP 3.17's predefined set, but LSP's semantic-tokens legend is server-defined strings, so they can be registered as custom types when the server is built later.

### Grammar refinements from the spec sketch

The design refines the grammar sketch from the advisory documents in several ways, each for a concrete reason:

- **The `qualifier` rule got its own labeled alternatives.** The sketch used an inline sub-expression for the `label:`/`rule:` qualifier prefix, but because unlabeled literals are suppressed (the same problem described above), that form would parse but leave no way to tell *which* qualifier was used. The design gives `qualifier` its own rule with labeled literals so the loader can distinguish them.

- **`scope_name` was dropped as a separate rule.** The `none` case is just a single-segment dotted name, so the loader interprets it directly instead of needing a separate grammar rule.

- **`kind_list` was fixed.** The sketch allowed meaningless constructs like `ref x: *, foo;` (a wildcard followed by specific kinds). The design makes `*` a complete alternative that cannot be followed by more kinds.

- **`dotted_name` segments are labeled.** Each segment is labeled `part` so the loader reads them via typed accessor methods rather than doing string slicing on the span.

### A known parsing quirk

An anchor that happens to be literally named `label` or `rule`, written flush against a colon (like `scope label:comment;`), will fail to parse. This is because the optional qualifier prefix (`label:` or `rule:`) commits once the parser sees `label:` -- PEG parsing does not backtrack after a successful match. Writing whitespace before the colon (`scope label : comment;`) disambiguates, because the qualifier's no-whitespace separators prevent the qualifier group from matching. The failure mode is always a visible parse error, never a silent misclassification. A test pins both the failing and working spellings.

## How anchors are validated against the grammar

A central design goal is that every name in a `.fltklsp` file is checked against the target grammar at load time. A typo in an anchor name is a load error, not a silent no-op. This is a property that spelling-based highlighting systems (like TextMate grammars) can never offer, and it is *new* -- despite what the advisory documents claimed, the existing `.fltkfmt` pipeline does not actually perform this validation. Typos in `.fltkfmt` anchors silently produce no formatting effect. The validation is built from scratch in this round; backporting it to `.fltkfmt` is noted as a possible future improvement.

### Validation rules

The loader collects *all* errors (not failing on the first one) and raises a single error whose message renders each offense with file, line, column, a source-line caret, and a human-readable message. The rules:

1. A `rule X { ... }` block's `X` must name a rule that exists in the grammar.
2. An identifier anchor inside `rule X` must match a label or invoked rule name among X's items.
3. A literal anchor inside `rule X` must match a literal value among X's items.
4. A global identifier anchor must name a rule or label somewhere in the grammar.
5. A global literal anchor must appear as a literal somewhere in the grammar.
6. A scope name's first segment must be in the token legend (or be `none`).
7. `def`/`ref` kind names are deliberately unconstrained (any dotted name is accepted).

### The union-semantics decision for global anchors

The advisory spec said that a global identifier anchor which could be read as both a label name and a rule name should be a load error, requiring explicit `label:` or `rule:` qualification to disambiguate. But in practice, FLTK gives every unlabeled rule invocation an implicit label equal to the rule name. This means nearly every rule name is also a label name -- the "ambiguous" case is the norm, not the exception, and the spec's rule would make almost every rule-name anchor an error.

The design replaces this with union semantics: an unqualified global identifier anchor matches *both* interpretations (all CST nodes of that rule, plus all children carrying that label). The `label:` and `rule:` qualifiers remain available to restrict to one reading. This is called out as a deliberate, irreversible commitment: once external `.fltklsp` files use unqualified ambiguous anchors, tightening to the spec's error rule later would reject previously-valid files.

## The classification engine

### Built-in defaults

Even with an empty (or absent) `.fltklsp` file, the classifier produces a usable baseline. It walks the analysis-grammar CST and classifies each terminal by a two-step process:

1. **Determine provenance**: figure out which grammar item (literal or regex) produced this terminal. For labeled spans, look up the label in the rule's items. For unlabeled spans, try literal-first (exact text match against the rule's literal values), then regex (pattern match against the rule's regex patterns).

2. **Classify by provenance and text shape**:
   - A literal that looks like a word (`execute`, `when`, `name`) becomes `keyword`.
   - A literal that is punctuation (`(`, `)`, `,`, `;`, etc.) becomes `punctuation`.
   - Any other literal becomes `operator`.
   - A regex match that starts with a quote becomes `string`.
   - A regex match that starts with a digit becomes `number`.
   - A regex match that looks like an identifier becomes `variable`.
   - Any other regex match becomes `text`.

Trivia rules (the grammar's `_trivia` mechanism, used for whitespace and comments) get `comment` classification over their entire span, *unless* the span is entirely whitespace (which avoids painting every inter-token gap as a comment). The classifier does not descend into trivia nodes -- the outermost trivia node emits at most one `comment` interval, preventing nested trivia structures from double-painting or allowing terminals inside comments (like `//`) from repainting as `operator`.

This provenance-based approach is what gives the classifier its key advantage over spelling-based highlighters: the keyword/identifier boundary is decided by which grammar item the parser matched, not by the text content. The word `name` appearing as a literal option key is classified `keyword`; the same word `name` appearing as a regex-matched identifier is classified `variable`.

### The painter's rules (explicit overrides)

When a `.fltklsp` file provides explicit `scope` statements, they interact with the defaults through a layered system:

1. **Whole-span painting**: a `scope` statement paints the *entire span* of the matched node, including all descendants.

2. **Explicit beats default**: inside the span of any explicitly-scoped node, built-in defaults are suppressed entirely. So `scope doc: comment;` yields one uniform comment span without the `//` literal inside it repainting as punctuation.

3. **Innermost explicit wins**: an explicit scope on a descendant overrides an ancestor's explicit scope within the descendant's span.

4. **Tiebreaking among explicit scopes on the same node**: rule-block statements beat global statements; label/literal anchors beat rule-name anchors; among remaining ties, the later statement in the file wins.

5. **`none` is explicit**: it suppresses both defaults and inherited paint for that span, and it participates in precedence like any other scope.

Def-site paint (from `def` statements) works by using the definition kind's first segment as a token type if it is in the legend, with the `declaration` modifier added. At the same node, an explicit `scope` statement beats def-derived paint.

### The token stream

The classifier outputs a list of `Token` objects, each with a start offset, end offset, token type, and modifiers tuple. The output is guaranteed to be sorted by start position, non-overlapping, within bounds, and with adjacent tokens of identical type and modifiers merged. All offsets are in codepoints (not UTF-16 code units -- that conversion is a later milestone's concern).

## The AnalysisEngine

The engine is a class that ties everything together. It is deliberately shaped to be exactly what the future LSP server will wrap:

- Construction (via `from_paths`): loads the grammar, loads and validates the `.fltklsp` config (if provided), generates an analysis-grammar parser in memory.
- `highlight(text)`: parses the text and returns either a list of tokens (on success) or an error message (on parse failure).

The engine owns the "load once, highlight many times" lifecycle. Concerns like debouncing, stale-token serving, and diagnostic formatting are server policy layered on top in a later milestone.

## The `fltk-highlight` CLI

A command-line tool registered as a console script:

```
fltk-highlight --grammar lang.fltkg [--lsp lang.fltklsp] [--rule START_RULE] FILE
```

On success, it prints the source file to stdout with ANSI colors (one color per token type from a small fixed 16-color theme; the `declaration` modifier adds bold). On failure (either a bad `.fltklsp` file or a parse error in the source file), it prints a formatted error to stderr and exits with code 1.

The theme is a private implementation detail, not a configurable surface, in round 1. HTML output is deferred because it adds surface without exercising any new semantics.

## Corrections to the advisory documents

The design process found several places where the advisory brainstorm and spec documents either mischaracterized the codebase or proposed things that do not work against the actual code. These are not bugs to fix; they are facts that changed the plan:

- **Suppressed terminals** (described in detail above): the brainstorm's case-study approach of reading keywords off the CST is impossible against the normal CST because suppressed terminals are not in the tree. The analysis-grammar transform is the fix.

- **No existing anchor validation in `.fltkfmt`**: the advisory documents claimed `.fltklsp` would "reuse" `.fltkfmt`'s load-time anchor validation. No such validation exists in the `.fltkfmt` pipeline -- unmatched anchors silently no-op. The validation is built new.

- **No `rust_cst_module=` parameter**: the advisory documents described a `rust_cst_module=` parameter on `generate_parser` for the native fast path. This parameter does not exist; the Rust path is an offline per-grammar codegen step. This does not affect round 1 (pure Python) but changes the future M5 story.

- **Union semantics replaces the ambiguity error** (described in detail above).

## Edge cases and failure modes

- **Parse failure in the target text**: no tokens are produced; the engine returns an error message. Degraded highlighting modes (serving stale tokens, exposing the successfully-parsed prefix) are later milestones.
- **Valid anchor, zero occurrences in a particular input**: no-op by design. Validity is about the grammar, not any one document.
- **Literal/regex ambiguity**: if a rule has both a literal `"s"` and a regex that can also match `s`, provenance resolves literal-first. This is a documented limitation in the same family as `.fltkfmt`'s existing ambiguity limitation.
- **Grammars with no `_trivia` rule**: FLTK synthesizes a whitespace-only trivia rule automatically. Since the synthesized trivia matches only whitespace, and the classifier skips whitespace-only trivia spans, no spurious comment tokens are emitted.
- **Overlapping explicit paints**: totally ordered by the precedence key (depth, source rank, anchor rank, block rank, statement index). No ties are possible because statement index is unique.
- **Unicode**: codepoint offsets throughout. ANSI rendering is offset-based slicing, so astral-plane text works correctly.

## How this round sets up the future

- **M2 (LSP server)**: wraps `AnalysisEngine`. One new detail the advisory documents did not anticipate: the server will hold *two* parser instances -- the analysis-grammar parser for highlighting and a standard-disposition parser for formatting. Parsing twice per format request is acceptable.
- **M3 (prefix-CST)**: changes only the internals of `highlight()`'s parse step; the classifier already works on any subtree.
- **M4 (defs/refs)**: the grammar, config model, validation, and anchor resolution for `def`/`ref`/`namespace` all exist after round 1. M4 adds symbol-table construction and ref-site paint. No `.fltklsp` file written for round 1 needs to change.
- **M5 (resolver/native fast path)**: the native fast path must build its compiled module from the *analysis grammar* variant, which requires a future `genparser` flag that does not exist yet. Recorded so M5's design starts from facts.

## What is still undecided

### 1. Console-script registration

Round 1 adds the project's first `[project.scripts]` entry, making `fltk-highlight` installable as a command. This is new distribution surface for the Python wheel -- previously the project had no console scripts at all. The question is whether to commit to this packaging surface now, or to keep the tool accessible only as `python -m fltk.lsp.highlight_cli` until the packaging implications are better understood. The functional behavior is identical either way; the difference is whether `fltk-highlight` appears as an installed command in the user's PATH after `pip install fltk`.

### 2. Def-site paint in round 1

`def` statements already produce a highlighting effect: they paint definition sites with the def kind's first segment as the token type plus a `declaration` modifier. For example, `rule cog { def identifier: type.cog; }` would cause the identifier in a `cog` definition to be painted as `type` with a `declaration` modifier (typically rendered as bold). This makes the clockwork worked example fully functional immediately.

The tension: this freezes one slice of phase-2 (M4) semantics before M4's own design round. If the highlighting behavior of `def` changes during M4's design, files relying on round-1's behavior might need updating. The design recommends keeping it -- the behavior is small, already specified, and forward-compatible with the phase-2 intent. The alternative is making `def`/`ref` entirely inert until M4, which would leave the worked example only partially functional.
