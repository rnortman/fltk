# Round 3: Teaching the editor to understand symbols -- an ELI5 walkthrough

This document explains the step3 design for readers with no prior context on this codebase. It covers what is being built, why, how it works, and what is still undecided. It adds nothing the design does not say.

## What this is about

FLTK is a toolkit for building parsers. You hand it a grammar file (`.fltkg`) describing the syntax of some language, and FLTK generates a parser that produces a concrete syntax tree (CST) -- a structured representation of any source file in that language. Think of it as a compiler-compiler: FLTK builds the parser so the language author does not have to.

One of the things language authors want is editor tooling: syntax highlighting, go-to-definition, find-all-references, rename-a-symbol. The standard way editors get those features is through the Language Server Protocol (LSP), where a "language server" runs alongside the editor, answers questions about the code, and paints it with colors.

FLTK ships a generic language server called `fltk-lsp`. Instead of being hardcoded for one language, it reads a small sidecar file -- a `.fltklsp` file -- that tells it how to map grammar constructs to editor features. A language author writes one `.fltkg` grammar and one `.fltklsp` sidecar, and gets a working LSP server for their language, no custom code required.

The `.fltklsp` sidecar supports several kinds of statements. The ones already working (from prior rounds) are `scope` statements, which control syntax highlighting -- for example, "paint every `typespec` node as a type" or "paint the `doc` subtree as a comment." Those are round 1 and round 2's contribution.

Three other statement forms have existed in the sidecar grammar since day one but have been deliberately inert -- parsed, validated, but doing nothing at runtime:

- `def` -- declares that a grammar construct defines a symbol (e.g., "the `identifier` child of a `cog` rule defines a symbol of kind `type.cog`").
- `ref` -- declares that a grammar construct is a reference to a symbol (e.g., "the `identifier` child of an `expr` rule refers to some symbol").
- `namespace` -- declares that a rule introduces a lexical scope (e.g., "the contents of a `cog` rule are a namespace; symbols inside it are not directly visible from outside").

This round activates those three statement forms. The result: the LSP server learns to understand *symbols* -- named things in the user's source code -- and can offer navigation (go-to-definition, find-references), outline views (document symbols), and safe rename.

## Why this, and why now

Three considerations drove the choice to do this round rather than other possible work.

First, all the groundwork is already in place. The grammar parses `def`, `ref`, and `namespace`; the config model stores them; validation checks their anchors against the grammar. The only missing piece is the *semantics* -- actually building a symbol table and using it. The prior round's design explicitly planned for a symbol table to sit "next to `tokens`" in the analysis result; this round is the payoff of that layering.

Second, the main alternative candidate -- "prefix-CST" (showing a partial syntax tree even when the file has parse errors, labeled M3 in the project's roadmap) -- has an unresolved factual prerequisite: nobody has yet determined whether FLTK's packrat parser internals can yield a useful partial tree on failure. Designing M3 now would mean designing against an unverified assumption. M4 (this work) has no such uncertainty.

Third, the sidecar files authored so far remain valid verbatim. This round adds meaning to statements that already exist in the grammar; it changes no syntax and rejects no previously-valid file. That honoring of backward compatibility was an explicit commitment from the first round.

## The relevant parts of the system

To follow the design, a reader needs to know about a handful of existing pieces. Each is introduced here as briefly as possible.

**The analysis engine** (`engine.py`) is the central coordinator. It holds a grammar, a parser built from that grammar, and a resolved LSP config. When asked to analyze a document, it parses the text into a CST, then classifies (paints) the tree into a list of tokens with semantic types (keyword, type, variable, etc.). The result is a `DocumentAnalysis` containing the tree and the token list. On parse failure, the tree and tokens are `None`.

**The classification engine** (`classify.py`) turns a CST into a flat token stream. It has two layers: a *default* layer (built-in heuristics -- word-shaped literals are keywords, punctuation is punctuation, etc.) and an *explicit* layer (driven by `scope` statements from the `.fltklsp` file). The explicit layer wins over defaults wherever it applies, and among explicit paints, the innermost (most specific) one wins. The machinery that resolves these precedence conflicts -- a "tier" system with source ranks, anchor ranks, and statement indices -- is reused unchanged by this round.

**The resolved config** (`lsp_config.py`) is the product of loading a `.fltklsp` file: it takes the raw parsed statements and resolves them into lookup tables the classifier can use efficiently. Currently it produces "node paints" (whole-node coloring for rule-name anchors) and "child matchers" (per-parent-rule matchers for label/literal/child-rule anchors). This round extends it with three new tables: def matchers, ref matchers, and a set of namespace rules.

**Grammar tables** (`classify.py`, currently private) precompute per-rule information the classifier needs for its tree walk -- things like "which labels exist in this rule" and "which rules does this rule invoke." The symbol extractor needs the same information, so this round promotes these tables from private to public.

**The match predicate** (`classify.py`, currently private) is a function that answers "does this matcher apply to this particular child node?" -- checking label names, literal text, or child rule names. Both the classifier and the new symbol extractor need it, so this round moves it to `lsp_config.py` where both can reach it.

**The LSP server** (`server.py`) is a pygls-based server that handles the LSP protocol. It runs analysis on a background thread, debounces rapid edits, and serves results to the editor. For read-only features (highlighting, folding, etc.), it serves the last-good analysis when the current document has parse errors -- a stale outline is better than no outline. This round adds six new protocol handlers to it.

**`fltk-highlight`** is a standalone CLI tool that highlights source files in the terminal using the same classification engine. It gains ref-site coloring for free from this round because it already flows through the token stream.

## What we are going to do and why

### New data structures: Symbol, Reference, Scope, SymbolTable

The core addition is a *symbol table* -- a data structure that records every definition and every reference in a document, organized into scopes.

A **Symbol** records: the symbol's name (the text of the anchor child), its kind (a dotted name like `type.cog`), the name span (where the name appears -- this becomes the "selection range" in the editor), and the declaration range (the full span of the producing rule node -- this becomes the "range" in outline views, so a `cog` definition's range covers the entire cog block, not just its name).

A **Reference** records: the reference text, its span, the kinds it is willing to resolve to (from the `ref` statement -- either a list of kinds or the wildcard `*`), and -- after resolution -- the Symbol it resolved to (or `None` if unresolved).

A **Scope** is a region of the document where symbols are visible. There is always a root scope spanning the entire document. `namespace` rules create child scopes nested inside it. Resolution walks outward from the innermost scope containing a reference, so inner symbols shadow outer ones with the same name -- exactly how variable scoping works in most programming languages.

The **SymbolTable** bundles the root scope, all symbols in document order, all references in document order, and provides lookup methods: find the symbol at a given cursor position, find the reference at a position, and find all occurrences of a symbol (its definition plus all references that resolved to it).

### Extended config resolution: def matchers, ref matchers, namespace rules

The config resolver gains three new outputs. A **DefMatcher** pairs a match predicate (by label, literal text, or child rule -- the same matching machinery `scope` uses) with a kind and a tier. A **RefMatcher** is similar but carries a list of acceptable kinds (or the wildcard). The **namespace rules** set records which rule names have a `namespace;` statement in any of their blocks.

These are keyed by parent rule name because `def` and `ref` are grammar-restricted to rule blocks -- there are no global def/ref statements. The existing def-site *paint* (painting declaration sites with the `declaration` modifier) stays in the existing child-matchers table unchanged; the new DefMatcher is a parallel structure used only by the symbol extractor, not by the painter.

All new fields have defaults, so every existing call site and every existing test continues to work unmodified.

### Extraction: one walk, three jobs

The `extract` function does a single depth-first walk of the CST and performs three tasks at each node:

1. **Scope opening.** If the current node's rule is in the namespace-rules set, a new child scope is opened for its span.

2. **Def matching.** For each child of the node, the function tries the parent rule's def matchers. If any match, exactly one symbol is created from the highest-priority matcher (using the same tier-based precedence the painter uses). The symbol goes into the current scope -- except for one important special case described below (the namespace hoist).

3. **Ref matching.** For each child *not* already matched as a definition, the function tries the parent rule's ref matchers. A child that is both a def and a ref is treated only as a def (a declaration is not simultaneously a reference to itself). The highest-priority match creates a Reference.

After the walk, resolution runs: for each reference, find the innermost scope containing it, then walk outward scope by scope. In each scope, look for the first symbol (in document order) whose name matches the reference text and whose kind matches one of the reference's acceptable kinds. Kind matching uses dotted-prefix comparison: a ref accepting kind `type` will match a symbol of kind `type.cog`, but a ref accepting `type.cog` will not match a bare `type`. The first match wins, and the outward walk stops -- inner scopes shadow outer ones. Forward references work: a reference earlier in the document can resolve to a symbol later in the same scope, matching how declaration-order-free DSLs typically behave.

The walk skips trivia nodes (comment subtrees), so definitions and references inside comments do not exist.

### The namespace hoist: a deliberate deviation from the spec's literal wording

The advisory spec says of `namespace`: "symbols defined in its subtree are visible only within it." Read literally, this would trap a namespace's *own name* inside its own scope. Consider the clockwork example: `rule cog { def identifier: type.cog; namespace; }`. If the cog's name symbol lived inside the cog's scope, no reference *outside* the cog could ever resolve to it -- go-to-definition on a cog name mentioned elsewhere would never work, defeating the purpose.

Every mainstream language handles this the other way: a class's name lives in the enclosing scope; the class's *members* live inside. The design follows that convention: a symbol whose `def` is anchored in a namespace rule is defined into the *enclosing* scope, not the namespace's own scope. Symbols produced by other rules inside the namespace's subtree stay inside. Self-reference still works because resolution walks outward and finds the hoisted name in the parent scope.

This is called out as a deliberate deviation from the spec's literal text, in service of its evident intent.

### Ref-site paint: coloring references by what they refer to

The spec says a resolved reference should inherit the token type of its defining symbol's kind. For example, if `identifier` in an `expr` resolves to a symbol of kind `type.cog`, that identifier should be painted as a `type`.

This cannot be precomputed at config-resolution time because *which* kind a reference resolves to depends on the document -- which defs exist, in which scopes. So the classification pipeline gains a new input: the symbol table. When provided, each resolved reference whose kind's first segment is a recognized token type contributes a paint interval to the explicit layer, at a precedence rank equal to def paint (rank 1) and below explicit `scope` paint (rank 2). This means:

- An explicit `scope` statement always wins over ref paint, as the spec requires.
- Ref paint suppresses defaults over its span.
- Unresolved references and references whose kind is not in the token legend get no paint and fall through to defaults. No new failure mode is introduced.

The `classify` function's signature gains an optional keyword argument (`symbol_table=None`), so all existing callers are unaffected.

### Feature functions: pure translations from symbols to LSP responses

A new module provides pure functions that translate the symbol table into LSP protocol values. None of these functions touch server state; they take the symbol table, a line index (for offset-to-line/column conversion), and an encoding, and return LSP data structures.

**Document symbols** produces the outline view. Each symbol becomes a `DocumentSymbol` with its name, detail (the dotted kind joined with dots), kind (mapped through a fixed table: `type` becomes Class, `function` becomes Function, `variable` becomes Variable, and so on -- unknown first segments fall back to Object), range (the declaration range), and selection range (the name span). Nesting is by declaration-range containment, not by namespace scoping: a `schema_field` nests under its `schema` in the outline because the schema_field's rule node is physically inside the schema's rule node, regardless of whether either is a namespace. The design specifically handles a subtle case where the name anchor appears *after* child members in the grammar (e.g., `outer := "{" , member* , "}" , "as" , name:ident`) by sorting on declaration range rather than name position.

A flat fallback (`SymbolInformation` instead of `DocumentSymbol`) is provided for clients that do not support hierarchical symbols; the server picks which to use based on the client's declared capabilities at startup.

**Symbol target** is a shared helper: given a cursor offset, find the symbol whose name span contains it, or else the resolved symbol of the reference at that offset, or else nothing. Every navigation feature builds on it.

**Go-to-definition** returns the target symbol's name span as a location. Going to the definition of a definition returns itself -- the conventional editor behavior.

**Find references** returns all occurrences of the target symbol (its definition plus all resolved references), with a flag controlling whether the definition itself is included.

**Document highlight** returns the same occurrence set but marked with Write for the definition and Read for references -- the standard convention that lets the editor dim or brighten each role.

**Prepare rename** returns the exact span under the cursor when a target exists, or nothing (so the editor can tell the user "this element cannot be renamed" before they even type a new name). This feature was not in the original roadmap but falls out at near-zero cost from the same occurrence query and is included as a called-out scope addition.

**Rename occurrences** returns the raw set of text ranges to edit. The server (not the feature function) turns this into a `WorkspaceEdit` after additional safety checks described below.

### Rename safety: the one feature that edits the document

All the other features are read-only: they look at the document and report information. Rename is different -- it produces edits. Because edits can corrupt the document if applied against stale data, rename gets a stricter policy than the read-only features.

**No stale analysis.** The read-only features are happy to serve last-good results when the current document has errors (a slightly stale outline is better than none). Rename refuses: if the current document version has no successful analysis, the request fails with a message ("cannot rename while the document has parse errors"). Applying edits computed from a stale tree to current text would corrupt the file.

**Verify-reparse guard.** Before returning edits, the server applies them to the current text *in memory* and reparses. If the result does not parse -- for instance, the new name collides with a contextual keyword and breaks the grammar -- the request fails with an explanatory message and no edits reach the editor. This mirrors an existing guard in the formatting pipeline. One residual risk the design documents: a rename that still parses but changes meaning (the "scannerless grammar hazard," where in a grammar without a separate lexer, changing a name can cause adjacent text to be tokenized differently). The reparse catches gross parse failures but cannot catch meaning shifts; the next analysis pass will repaint, making any such shift visible immediately.

**Versioned edits against client-side races.** Between the handler's two awaits on the worker thread (analysis, then verify-reparse), a `didChange` notification from the editor could land, meaning the document has changed since the analysis. To prevent applying stale offsets to new text, the server returns edits as a versioned `TextDocumentEdit` (carrying the analyzed document version) when the client advertises support for `documentChanges`. A conforming client will refuse to apply the edit if the version no longer matches. Clients without that capability get the unversioned fallback; for them alone, the race is a residual risk that LSP provides no mechanism to close.

A no-op rename (new name equals old name) returns an empty edit.

### Server wiring

The analysis engine's `DocumentAnalysis` gains a `symbols` field (defaulting to `None`, so existing consumers are unaffected). On a successful parse, the engine runs extraction and passes the symbol table into classification for ref-site paint. On failure, `symbols` is `None`.

The server registers six new handlers: `textDocument/documentSymbol`, `textDocument/definition`, `textDocument/references`, `textDocument/documentHighlight`, `textDocument/prepareRename`, and `textDocument/rename`. All follow the established pattern of ensuring analysis, then calling the pure feature functions. The server captures two client capabilities at initialization: whether the client supports hierarchical document symbols, and whether it supports versioned `documentChanges` for workspace edits.

### Qualified-name references degrade gracefully

Some languages have compound references like `ns::Type` or `a.b.c`. A `ref` anchored on such a node simply compares the full span text against symbol names. Since no symbol is named `ns::Type`, it will not resolve -- graceful degradation, no error, default paint applies. A proper "qualified ref" form (resolve the first segment, then walk into namespaces) is real design work entangled with the cross-file resolver question and is deferred. Practical advice for spec authors: if the grammar labels the segments, anchor the `ref` on the segment label to get single-segment resolution now.

### Two scope additions beyond the original roadmap

The roadmap listed document symbols, go-to-definition, find-references, and same-file rename. Two adjacent features are included because they fall out of the same occurrence query at near-zero marginal cost: **document highlight** (cursor-on-symbol highlights all occurrences) and **prepare rename** (a preflight check that tells the editor whether the thing under the cursor is renamable). Both are called out as scope additions and are open to challenge in review.

## What could go wrong and how it is handled

**Unresolved references** are silent: no paint, no diagnostic, go-to-definition returns nothing. This is deliberate. With cross-file resolution absent until a future milestone, unresolved is the normal state for imported names. Diagnosing it would produce sustained false-positive noise. The future cross-file resolver is the layer that could upgrade this to an error.

**A child matched by both a def and a ref** -- the def wins. The child is a declaration only. This prevents a single token from being simultaneously a definition and a reference to itself.

**Duplicate same-name defs in one scope** -- both appear in the outline. References resolve to the document-order-first one. Whether duplicates are an error is the DSL's own semantic concern, not the generic tooling's.

**Overlapping occurrence spans** -- possible when a node-anchored ref covers the same text as a span-anchored ref through a single-child chain. The `occurrences` method deduplicates by start/end, so rename never emits overlapping edits (which LSP forbids).

**Rename to a name that breaks the parse** -- caught by the verify-reparse guard; the request fails, the document is untouched. A rename that parses but re-means (the scannerless-grammar hazard) is beyond the guard; it is a documented residual risk, immediately visible via repaint.

**Rename on a stale analysis** -- refused. Read-only features keep their stale-serving behavior.

**Rename racing a keystroke** -- the versioned `documentChanges` payload lets a conforming client refuse a stale edit. Only clients without that capability retain the race.

**Definitions or references inside comments** -- cannot occur because extraction skips trivia subtrees.

**Empty document or no defs** -- the symbol table is empty; every feature returns its empty/null value.

**A kind whose first segment is not in the token legend** -- no paint effect, but symbol and navigation semantics are identical. The kind vocabulary is deliberately open; only the LSP rendering has a fixed fallback.

**Performance** -- extraction is one additional tree walk plus resolution work proportional to the number of references times the scope depth. At the scale the debounced server operates (single files, sub-second analysis), this is fine. The existing performance TODO about unifying tree walks is extended to note the third walk.

## What is still open

The design states that no questions require user judgment, but records several judgment calls with rationale that review may challenge. These are the decisions that were made (not left open), each recapped here so a reviewer can evaluate them:

- The namespace hoist (a construct's own name is defined into the enclosing scope, deviating from the spec's literal wording).
- Flat-text degradation for qualified names (compound references like `ns::Type` simply fail to resolve rather than being handled with a new language form).
- The two added features beyond the roadmap (document highlight and prepare rename).
- The rename safety policy (refuse on stale analysis, verify-reparse guard, versioned edits).
- Silent unresolved references (no diagnostic for references that fail to resolve).
- First-in-document-order resolution for duplicate same-name defs in one scope.

Each of these is explained in the relevant section above. The design invites review to challenge any of them.

The larger questions that remain genuinely open but are explicitly out of scope for this round: prefix-CST exposure (needs its own exploration of parser internals first), cross-file resolution and the resolver plugin API, qualified-name resolution as a language form, completion, hover, workspace symbols, and diagnostics for unresolved references.
