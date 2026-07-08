# ELI5: Prefix-CST exposure and degraded-mode serving (M3)

## What this is about

FLTK is a toolkit for building parsers for custom languages. When you define a language with FLTK, you get a parser that reads source code and produces a tree structure (a Concrete Syntax Tree, or CST) representing everything in the file. A companion project built on top of FLTK is a Language Server Protocol (LSP) server -- the kind of background process that powers syntax highlighting, error diagnostics, go-to-definition, and similar features in code editors like VS Code.

The LSP server works by parsing whatever the user is editing, then walking the resulting tree to figure out how to paint (highlight) each token. The problem is: **when the file has a syntax error, the parser currently throws away everything it learned.** The whole analysis comes back empty, and the editor falls back to showing highlighting from the last time the file parsed successfully -- which may have been many edits ago, with positions drifting further and further off.

This is painful in a specific, common scenario: you are typing in the middle of a file that has an error further down. Everything you write above the error is perfectly valid syntax, but the server cannot highlight any of it freshly because the overall parse "failed." You see stale highlighting for the whole document, with positions that no longer line up.

The fix this design describes: **keep the successfully-parsed prefix of the file** (all the valid content before the error) and use it to provide fresh, accurate highlighting for that region. Only the part of the file after the error falls back to stale data. This is exactly the improvement the project's roadmap sketched as milestone M3.

## The relevant parts of the system

A few pieces of the system matter for understanding this design:

**The parser and `parse_text`.** When you ask FLTK to parse a document, it returns a `ParseResult` that says either "success, here is the full tree" or "failure, here is an error message." The parser is a packrat parser (PEG-based), which means it tries to match the grammar's start rule against the input. The start rule for most grammars has a repeating structure at the top level -- for instance, "a module is a sequence of entities" or "a document is a sequence of items."

**Early success without full consumption.** When the parser hits a broken construct partway through the file, the top-level repetition stops, and the start rule reports success over everything it managed to match. The parser has, at that moment, a fully assembled tree for the valid prefix of the file. But the current code notices that the parser did not consume the whole input, declares the parse a failure, and discards that tree. This design recovers it.

**Hard failure.** In contrast, sometimes the very first thing in the file is broken, so the start rule itself cannot match at all and returns nothing. In this case there genuinely is no assembled tree to recover -- only scattered fragments in the parser's internal memo cache. Salvaging those fragments would be new engineering with real correctness risks (the cache contains speculative sub-parses from branches the parser never committed to). This design does not attempt it.

**The analysis engine.** The `AnalysisEngine` is the layer between the raw parser and the LSP server. It takes text, parses it, classifies every token (assigns semantic types like "keyword", "string", "type"), builds a symbol table (tracking definitions and references), and returns a `DocumentAnalysis` bundle. Currently it has two outcome shapes: complete (everything worked) and failed (parse error, nothing usable).

**The LSP server and stale serving.** The server keeps a snapshot of the last complete analysis (called `_GoodAnalysis`). When a parse fails, the server serves that snapshot to the editor for all features -- highlighting, folding, symbol outline, go-to-definition, and so on. This is the "all stale" policy that this design improves for semantic tokens specifically.

**Semantic tokens.** These are the data the server sends to the editor to tell it how to color each piece of text. They are encoded as a flat list of numbers in a specific delta format defined by the LSP protocol. The current code fuses three steps together: looking up each token in the legend (the agreed-upon color vocabulary), splitting multi-line tokens into single-line segments with absolute positions, and then delta-encoding those positions. This design separates those steps so that fresh and stale segments can be combined before the final encoding.

## What we are going to do and why

### Expose the prefix tree from the parser (plumbing layer)

The `ParseResult` dataclass gains two new optional fields: `prefix_cst` (the tree for the valid prefix) and `prefix_pos` (how many characters that prefix covers). These are populated only in the "early success without full consumption" case, where the parser already has the tree assembled. On a full success, both are `None` (the full tree is in the main `cst` field). On a hard failure (no match at all), both are also `None`.

The critical safety property: the main `cst` field stays `None` and `success` stays `False` for every non-total parse. This means every existing caller -- the formatter, the verify-reparse guard, anything that checks `parsed.success` -- continues to behave exactly as before. The prefix tree lives in a new, separate field that only code that specifically opts in will ever look at.

This approach was chosen because it requires zero changes to the parser runtime or generated code. The tree already exists at the moment it would be discarded; we simply stop discarding it.

### A third analysis outcome: partial

The analysis engine's `DocumentAnalysis` gains a new outcome shape, "partial," sitting between "complete" and "failed." A partial analysis has a tree, tokens, and a symbol table -- but they cover only the prefix of the file, not the whole thing. It also carries the parse error (so diagnostics still fire) and a `prefix_end` offset marking where the fresh data ends.

When the engine sees a prefix tree from the parser, it runs the same classification and symbol-extraction passes it would run on a full tree, just on the prefix. These passes already work on any subtree handed to them (they walk structurally over `kind`/`span`/`children`), so they need no modification.

A consequence: if the prefix contains a reference to a symbol defined after the error, that reference will not resolve (it paints as a default/unstyled token rather than its semantic kind). This is accepted behavior -- fresh-and-approximately-painted is better than stale-and-misplaced, and the stale tail covers the region where the definitions went missing.

If classification of the prefix itself triggers a recursion error (a degenerate grammar scenario), the engine falls back gracefully to the plain "failed" outcome with the original parse error message.

### Refactoring semantic-token encoding into composable steps

The existing `encode_semantic_tokens` function does everything in one pass: legend lookup, position calculation, and delta encoding. To merge fresh prefix tokens with stale tail tokens, we need an intermediate representation: absolute position segments. The refactoring introduces:

- `TokenSegment` -- a frozen dataclass representing one painted span at an absolute (line, column) position in the document.
- `absolute_segments(tokens, line_index, encoding)` -- converts classified tokens into segments using a document's line index.
- `delta_encode_segments(segments)` -- turns sorted segments into the LSP wire format.
- `encode_semantic_tokens` becomes a trivial composition of the two, with identical output (pinned by regression tests).

This separation is necessary because fresh segments and stale segments come from different document versions. Each must be converted to absolute positions using its own document's line index before they can be meaningfully compared and merged.

### The merge algorithm

`merge_stale_segments` takes fresh prefix segments, stale segments from the last good analysis, and a boundary position (the line/column where the prefix ends in the current document). It outputs a single sorted, non-overlapping segment list: all fresh segments, followed by those stale segments whose start position is at or past a "floor." The floor is the maximum of the boundary and the end of the last fresh segment (a defensive guard ensuring no overlap even if coordinates have drifted).

The stale segments carry positions from the old document. No attempt is made to shift them by edit deltas -- the server uses full-document sync and has no edit deltas available. This is the same approximation the server already makes when serving an entirely stale token stream; the difference is that now only the tail is approximate, and the prefix is exact.

### Server serving policy: semantic tokens get the prefix; everything else stays last-good

This is a deliberate split based on the nature of each feature:

**Semantic tokens benefit from the prefix.** Highlighting is per-position: a missing token degrades one span, and stale positions drift visibly on every line. Fresh prefix tokens are strictly better than stale tokens for the region they cover.

**Folding, outline, selection, definition/references stay on last-good.** For these features, completeness beats freshness. A prefix-only fold list would silently drop every fold past the error. A find-references result from only the prefix would quietly miss occurrences. An outline that loses half its entries on every keystroke inside a broken region churns the editor UI. Stale-but-complete is the better tradeoff for query-answer features.

**Rename stays refused during errors.** Renaming from a prefix-only symbol table would silently miss occurrences past the error, potentially leaving the codebase in an inconsistent state. The existing refusal (when the analysis has a parse error) now also covers partial analyses.

### Server state changes

Semantic-token serving is extracted from the general "last good analysis" snapshot into its own record (`_ServedTokens`), because what the token handlers serve is no longer always the last complete analysis -- it might be a fresh prefix merged with a stale tail.

On a partial analysis, `_ServedTokens` is updated to the merged result. On a hard failure (no prefix available), the previously served tokens are left in place (same keep-serving-stale behavior as today). On a complete analysis, `_ServedTokens` becomes the fresh complete segments, and `_GoodAnalysis` is also updated (providing the stale input for future merges).

All the heavy computation (classification, segment generation, merging, delta encoding) stays on the background worker thread. The protocol loop only stores results and serves precomputed data, preserving the existing performance property.

### CLI changes: `fltk-highlight` shows the prefix

The standalone highlighting CLI tool (`fltk-highlight`) previously printed nothing on a parse error. With this change, on a partial analysis it prints the full document text to stdout with ANSI color applied to the prefix region (the tail passes through uncolored), prints the error message to stderr, and still exits with code 1. This is a deliberate behavior change to the stdout contract, but the exit code -- which is what scripts should key on -- is unchanged. The tool's purpose is as a manual test harness for classification, where seeing the prefix paint is the whole point.

### Fixing the start-rule duplication (`TODO(lsp-start-rule-dedup)`)

A minor cleanup bundled into this round: the `create_server` function currently takes a `start_rule` parameter separately from the `AnalysisEngine`, even though the engine already knows its own start rule. This creates the possibility of passing mismatched values with no error. The fix: expose a read-only `start_rule` property on `AnalysisEngine` and remove the redundant parameter from the server's constructor. This is a breaking change to a Python API, but that API shipped only days ago, is unreleased, and has no out-of-tree consumers yet -- doing it now is the compatibility-conscious moment, before anyone can depend on the old signature.

## What could go wrong and how it is handled

**Zero-length prefix** (the grammar expects a repeating structure but the very first item is broken): the prefix tree exists but is empty or near-empty, producing few or no fresh segments. The merge floor starts at (0, 0), so the entire stale stream is kept -- byte-equivalent to today's all-stale serving. No special case needed.

**Edit shrinks the document** so stale segments now point past the new end-of-file: those segments survive the merge (they are past the floor) and are clamped or ignored by the editor client, identical to the existing stale-serving behavior.

**First-ever analysis is partial** (document opened with an error, no prior good version): the stale input to the merge is empty, so the client gets fresh-prefix-only tokens. Strictly better than today's empty response in this case.

**Hard failure after a partial** (user breaks the very first construct after previously getting a partial): the worker returns no served segments, so the store leaves the previous `_ServedTokens` (which was a merge) in place. Serving a stale merge is the same risk class as serving any stale stream.

**Formatter safety**: the formatter path checks `parsed.success`, which remains `False` for prefixes. The main `cst` field remains `None`. A prefix can never be mistakenly formatted (which would truncate the user's file). A test explicitly pins this.

**Encoding consistency**: fresh and stale segments are always produced under the same position encoding (UTF-16 or UTF-32), which is fixed for the lifetime of the server session. So segments from different document versions are unit-compatible.

**Range requests during partial serving**: the filter for a range request uses position-tuple comparison against segments that are partly from an old document. This is an approximation for the stale tail -- the same approximation as serving those segments in a full-stream response.

## What is still open

The design declares no open questions. Both judgment calls it makes -- the `create_server` signature break and the `fltk-highlight` stdout-on-failure change -- are decided and documented, because both surfaces are pre-release and only days old. Deferring either would let out-of-tree consumers form around the worse contract.

Two areas are explicitly deferred as future work (but are not open design questions for this round):

- **Hard-failure prefix salvage from the memo cache**: extracting a usable partial tree when the start rule itself fails would require new engineering with correctness hazards (the memo cache contains speculative sub-parses the parser never committed to). Deferred until field experience shows top-of-file errors blanking documents in practice.

- **Native (Rust) analysis path**: the Rust side has the same discard point, but there is no Rust analysis path to modify today. Whatever future round designs the native fast path must expose the same prefix surface.
