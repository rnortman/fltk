# Round 5 design, explained from scratch

## What this is about

FLTK is a Python library for building parsers and compilers. You give it a grammar file describing your programming language, and it generates a parser that can break source code into a structured tree (a "Concrete Syntax Tree," or CST). On top of that parsing engine, FLTK ships a language server called `fltk-lsp` that speaks the Language Server Protocol (LSP) -- the standard that lets code editors like VS Code offer features such as syntax highlighting, code formatting, and "go to definition."

Through four previous rounds of development, `fltk-lsp` has learned to do quite a lot for any language whose grammar is expressed in FLTK -- but everything it does happens one file at a time. It can highlight your code, format it, show you an outline of definitions, and navigate between definitions and references, all within a single file. The moment your language has a concept of imports -- where one file refers to something defined in another file -- the server hits a wall. It sees an import reference, recognizes that it cannot resolve the reference to anything in the current file, and shrugs. The unresolved reference sits there as a silent "I don't know" value. Nothing breaks, but nothing navigates across files either.

This round closes that gap. Its theme is cross-file navigation, end to end, demonstrated in a real editor.

## The three deliverables

Round 5 produces three things, each building on the last:

**First, a resolver plugin API.** This is a small Python interface that a downstream language author implements to teach `fltk-lsp` how their language's imports work. Every language has its own import syntax and rules for how file paths map to module names, so there is no generic way for the server to figure this out on its own. Instead, the server delegates to a language-specific "resolver" plugin that understands the language's import constructs.

**Second, a demo language called "gear."** This is a toy language -- not a real programming language -- created entirely within the FLTK repository to serve as the reference implementation and test fixture for the resolver API. It has `.gear` files with types, functions, constants, imports, comments, strings, operators, and enough structure to exercise every feature the server supports. The `.gear` file extension was chosen deliberately because no real language uses it, so VS Code cannot accidentally confuse it with something else.

**Third, a VS Code extension for gear.** This is a minimal extension that spawns `fltk-lsp` and wires it up to `.gear` files in VS Code. It demonstrates the complete pipeline: syntax highlighting, code formatting, and cross-file go-to-definition and find-references, all working in a real editor against multiple files. The automated test suite covers everything below the editor layer; the final acceptance is a human sitting in VS Code and seeing it work.

### What is explicitly out of scope

Several things are deferred by design:

- Rust/native acceleration -- the server stays pure Python this round.
- Cross-file rename -- renaming stays same-file, with a new safety guard (described below) to prevent it from silently breaking other files.
- Workspace-wide symbol search, call hierarchies, and file-change watchers -- these are future consumers of the same infrastructure being built here.
- Any changes to the `.fltklsp` specification language -- cross-file knowledge lives entirely in the resolver plugin, not in the spec language.
- TextMate grammar export -- the VS Code demo relies on semantic tokens (LSP-based highlighting) alone, with a `language-configuration.json` for comments and brackets but no TextMate grammar.

## The parts of the system you need to understand

### The SymbolTable: what the server already knows about one file

When the server analyzes a file, it produces a `SymbolTable` -- a data structure listing every definition ("symbol") and every usage ("reference") found in that file. Each symbol has a name, a kind (like "type" or "function"), and character offsets marking where it appears. Each reference similarly has a name, offsets, and a pointer to the symbol it refers to.

The critical detail: when the server's same-file resolution pass runs and cannot find a matching symbol for a reference anywhere in the file's scope chain, it sets that reference's symbol pointer to `None`. This is not an error -- it is a deliberate, first-class "I don't know" value. These `None` references are exactly the seam the resolver plugs into: they represent imports, qualified names, and any other reference that can only be resolved by looking at other files.

### How the server works today: single-file, single-thread

The server processes each file independently. It keeps a dictionary mapping file URIs to per-file state. When you open or edit a file, the server submits an analysis job to a single background worker thread (keeping the LSP protocol loop responsive), and the results -- the CST, the SymbolTable, semantic tokens, etc. -- are stored per-URI.

Critically, the server today does not know about the workspace. It never reads the workspace root folder that the editor sends at startup. It has no concept of "the other files in this project." Definition and references queries are cheap lookups into the single file's stored state, running directly on the protocol loop without touching the worker thread.

## What the design does and why

### The resolver plugin contract

The heart of this round is a Python protocol (interface) called `Resolver`. A downstream language author implements this protocol to teach the server how to resolve cross-file references for their language.

The resolver receives one analyzed document at a time -- its URI, text, CST, and SymbolTable -- plus a "host" object that lets it request analyzed versions of other files. It returns a `CrossFileResolution` containing two mappings:

- `ref_targets`: for references that were unresolved within the current file, where do they actually point? Each entry maps a reference to an `ExternalTarget` -- a location (URI plus character offsets) in another file.
- `symbol_targets`: for symbols that are actually import bindings (a local name that is really just an alias for something defined elsewhere), where is the real definition? This is how "go to definition" on an imported name jumps to the source file, and how "find references" on a definition can discover uses in files that import it.

Several design choices here are deliberate:

**Batch, not per-reference.** The resolver is called once per document and answers everything at once. The alternative would be calling it once per reference, but that would force it to re-derive the import map every time. Since a document's imports are a property of the whole file (typically a few `use` statements at the top), a single pass is more natural and efficient.

**The resolver reads the target language's own CST, not `.fltklsp` constructs.** The `.fltklsp` spec language has no vocabulary for cross-file concepts -- no way to express "this import path maps to that directory structure" or "this alias binds to that remote symbol." Those project-model rules are inherently language-specific, which is precisely why this is a Python hook rather than a declarative spec extension.

**An ExternalTarget is a location, not an object graph.** The resolver returns raw character offsets in other files, not linked symbol objects. If a language has re-exports (A re-exports something from B that originally came from C), the resolver itself chases that chain using `host.document()`. The server never recurses -- it trusts whatever location the resolver hands back. This keeps the server simple and puts chain-following logic where the language-specific knowledge lives.

**Identity is the selection range only.** When the server needs to compare two targets to see if they refer to the same thing (for aggregating references, for the rename guard), it uses only the URI and the name offsets -- the character range covering the symbol's name itself. The broader "declaration range" (which might include the entire function or type block) is used only for the editor's peek window. This prevents a resolver whose declaration range is slightly different from silently breaking reference-matching or the rename guard.

**Resolutions are not cached.** The expensive part -- parsing and extracting symbols from each file -- is cached (by the project host, described next). But the resolver's own `resolve()` call is recomputed every time. Definition and references are user-action-rate operations (you press F12 occasionally), not keystroke-rate, so the cost is negligible at demo scale. Skipping a resolution cache entirely eliminates the thorny problem of figuring out when cached resolutions are stale (which files does a resolution depend on? what if an import target changed?). This is a documented limitation, to be revisited if a real-world consumer hits performance issues.

### The project host: giving the resolver access to the workspace

The `ProjectHost` is the server-side implementation of the services the resolver needs. It is a new concept -- the first time the server has any awareness of the workspace beyond the single file being edited. Without a resolver, the server behaves identically to today; the project host is only instantiated when `--resolver` is passed on the command line.

The project host does three things:

**It provides analyzed documents.** When the resolver asks for another file via `host.document(uri)`, the host returns a fully analyzed document -- parsed, with symbols extracted -- or `None` if the file is unreadable or failed to parse. For files the editor has open, it uses the editor's unsaved buffer (so your in-progress edits participate in cross-file resolution). For files not open in the editor, it reads from disk.

**It caches those analyses.** Each analyzed document is cached, keyed by a version identifier. For open files, the version is the LSP document version number (incremented on every edit). For disk files, the version is the file's modification time and size. On every access, the host checks whether the version has changed and re-analyzes if so. Only complete, successful analyses are cached -- a file with a syntax error returns `None` and is not cached, so it will be re-analyzed on the next request after the user fixes the error.

**It lists workspace files.** The host walks the workspace root directory (captured from the editor at startup), filtering by the resolver's declared file suffixes (e.g., `.gear`), and skipping dot-directories like `.git` and `.venv`. This listing is recomputed on every request rather than being watched for changes -- there is no file watcher this round. File content freshness comes from the per-access version check, so changes are picked up on the next request.

**Threading safety** is handled by a snapshot approach. The project host runs only on the single analysis worker thread. But it needs to know what files the editor has open and what their current contents are, which is information that changes on the main protocol thread whenever the user types. To avoid torn reads, the server snapshots the entire open-document map (URI to version and text) on the main thread at the moment it submits a job to the worker, and the host on the worker thread consults only that snapshot plus disk. It never touches the live editor state from the worker thread.

### Loading the resolver: the `--resolver` flag

The server gains a new command-line flag: `--resolver SPEC`. The spec is either a Python module path with an attribute (`my_package.resolver:create_resolver`) or a file path with an attribute (`path/to/resolver.py:create_resolver`). The file-path form is essential for the demo, where the resolver lives in the repo but is not an installed Python package.

The named attribute can be either a `Resolver` instance directly, or a zero-argument factory function that returns one. If it looks callable and does not have a `resolve` method, it is called as a factory.

Validation happens at startup, before the server processes any LSP messages. A broken resolver -- bad import, missing attribute, wrong type, empty file suffixes -- prints a clear error to stderr and exits immediately. This matches the existing fail-fast policy for invalid grammar or spec files: a misconfigured server is a startup error, never a half-working server that subtly misbehaves.

### Cross-file queries: definition and references with a resolver

A new `ProjectNavigator` layer sits between the server's LSP handlers and the resolver. It takes a project host and a resolver and provides two pure-Python query methods (no LSP types -- the server handles rendering to LSP locations).

The central concept is the **canonical target** of a symbol. For a locally-defined symbol with no imports involved, the canonical target is simply its own location. For an import binding (a local name that is really an alias for something in another file), the canonical target is wherever the resolver says the real definition lives. This is always exactly one hop -- the `ExternalTarget` is terminal by construction, so there is no recursive chasing.

**Definition** works like this: if the cursor is on a symbol or a same-file-resolved reference, look up that symbol's canonical target. If the cursor is on an unresolved reference, check the resolver's `ref_targets` for a cross-file location. If neither applies, return nothing.

**References** works like this: identify what the cursor is on and find its canonical target T. Then, for the file where T lives and for every file in the workspace, collect all occurrences that point to the same canonical target: same-file references, import bindings whose canonical target matches T, and unresolved references whose resolver-provided target matches T. Deduplicate by location. The cost is O(workspace files) resolver calls per request, which is fine for demo-scale and small-to-medium projects. This is a documented limitation; a persistent index would be the answer if a real consumer outgrows it.

Both definition and references move to the background worker thread when a resolver is active, because they may now involve reading and analyzing other files. Without a resolver, they keep their current shape (cheap, on the protocol loop).

### Error handling: degrade gracefully, except for rename

When the resolver throws an exception during a definition or references query, the server catches it, logs it, and falls back to the same-file answer. A buggy resolver degrades the experience but never crashes the server. Out-of-range offsets returned by the resolver are clamped to valid positions (this is existing behavior of the line-index infrastructure). Unknown keys in the resolver's mappings (objects not from the document's SymbolTable) simply never match anything and are harmless dead weight.

The one deliberate exception to the "degrade gracefully" rule is the rename guard, described next.

### The rename refusal guard: failing closed

Same-file rename already works (from round 3). But with cross-file resolution in play, a same-file rename becomes dangerous: if you rename a symbol that other files import, those other files now have a broken import. The server does not yet support cross-file rename (emitting edits across multiple files), and that is real design work deferred to a future round.

Instead, the server adds a safety guard. When a resolver is active and the user tries to rename a symbol, the server first checks whether that symbol has any cross-file references or is an import binding (a local alias for something defined elsewhere). If either is true, the rename is refused with a clear error message explaining why.

The critical design choice: this guard **fails closed**. If the resolver throws an exception or any workspace file fails to analyze during the guard check, the rename is refused with "cannot rename: could not verify cross-file references." The alternative -- degrading to same-file rename and hoping for the best -- would reopen exactly the hazard the guard exists to prevent. A transiently-failing resolver could silently let through a rename that corrupts other files. For read-only features like definition and references, graceful degradation is fine (you get a less complete answer). For a destructive edit like rename, the safe default is refusal.

Without a resolver, rename behavior is completely unchanged from round 3.

### The gear demo language

Gear is a toy language created to serve as both the reference implementation of the resolver API and the test fixture for cross-file navigation. Its syntax is inspired by the real downstream language (clockwork) but is deliberately not any real language:

```
use lib::shapes::{Circle, Square as Box};

shape Wheel {
    hub: Circle;
    frame: Box;
}

const SPOKES: Int = 36;

fn rim_area(w: Wheel) -> Float {
    let r = w.hub;
    return 3.14 * r * r;
}
```

The language has comments, strings, numbers, types, functions, constants, keywords, operators, and -- critically -- multi-file imports with `::` path separators and optional `as` aliases. This exercises every highlighting class the server supports and, via the imports, the entire resolver pipeline.

The gear grammar is loaded dynamically at server startup (the same way any FLTK grammar is loaded); there are no committed generated-code artifacts for gear.

The gear resolver maps import paths to files on disk (`lib::shapes` becomes `lib/shapes.gear` under the workspace root), reads the target file's SymbolTable, and redirects the local import binding to the target's definition. It uses `symbol_targets` (redirecting import bindings) rather than `ref_targets` (redirecting unresolved references), because gear's import syntax creates local symbol bindings. The `ref_targets` hook is exercised by a test-local fixture resolver instead, keeping both hooks covered.

A sample project ships under `examples/gear/sample/` with at least `main.gear` and `lib/shapes.gear`, containing working imports and aliases. The samples are kept error-free; the acceptance checklist has the tester introduce errors live to see diagnostics and degradation behavior.

### The VS Code extension

The extension is minimal, plain JavaScript (no TypeScript build step). Running `npm install` fetches its single dependency (`vscode-languageclient`). It declares `.gear` as a language, provides a `language-configuration.json` for comment toggling and bracket matching, and spawns the `fltk-lsp` server via `uv` from the local repository.

A few details worth noting:

- The launch command includes `--extra lsp` because pygls (the Python LSP framework the server is built on) is an optional dependency. Without this flag, a clean checkout would get an environment without pygls, and the server would exit immediately with an error about the missing dependency. Development machines that have already synced test dependencies would never hit this, making it an environment-dependent trap -- hence the explicit flag.
- The extension includes `semanticTokenScopes` mappings for four token types that are not predefined in the LSP specification (`constant`, `punctuation`, `label`, `text`). Without these mappings, tokens painted with those types would silently render uncolored in VS Code's default themes. This closes a caveat noted in round 1's design.
- The extension can be run via VS Code's Extension Development Host (F5) or via `code --extensionDevelopmentPath=...`. Both work against the in-repo defaults with zero configuration beyond `npm install`. Alternatively, it can be packaged as a `.vsix` and installed, but then the user must configure the server command manually since the extension is no longer in the repo.
- The README warns that Node/npm (for the extension), the Rust toolchain (required by the FLTK build system), and `uv` are prerequisites, and that the first launch pays a one-time maturin debug build cost.

### Where the new files live

The demo language and VS Code extension live under a new top-level `examples/` directory, not inside the `fltk` Python package. This is deliberate: they are consumer-style artifacts (the kind of thing a downstream language author would own), not library code, and must not ship in the Python wheel.

The resolver API itself (`resolver.py`) and the project host (`project.py`) live inside `fltk/lsp/`, as they are part of the library.

Tests for the demo language live in `fltk/lsp/` following the colocated-test convention. Because the wheel includes `fltk`'s tests but not `examples/`, the gear test suites skip at module level with an explanatory message when the `examples/gear` directory is absent, so an installed-distribution test run skips cleanly rather than failing on missing fixtures.

### The resolver API is labeled provisional

The resolver protocol ships with an explicit "provisional -- subject to change" label in its docstring and in the demo README. This is a deliberate hedge: the protocol currently has exactly one implementation (gear), and gear is an in-repo toy language. Freezing a plugin API based on a single in-repo consumer is how APIs calcify in the wrong shape. The intended trigger for removing the provisional label is writing a resolver for a real downstream language (clockwork) and validating that the protocol works well for a real-world case.

## What could go wrong and how it is handled

**No workspace root.** If the editor does not send a workspace root at startup, the workspace file listing is empty. Cross-file definition can still work if the resolver can construct file URIs from import paths and the host can read them, but find-references degrades to same-file only. This is logged once at startup.

**Import target is missing or broken.** If the file an import points to does not exist or fails to parse, `host.document()` returns `None`, the resolver emits no entry for that import, and navigation falls back to same-file. This is silent, matching the existing policy for unresolved references -- during live editing, neighboring files being transiently broken is the normal state.

**Import cycles.** If file A imports from file B which imports from file A, the host's per-document analysis cache prevents infinite loops (each file is analyzed independently, and the server never recurses into resolve calls). A resolver that chases re-export chains must bound its own depth; the gear resolver does one hop by construction. Guidance for resolver authors is included in the protocol's docstring.

**Resolver crashes or returns garbage.** Exceptions are caught and logged; definition and references fall back to same-file answers. Out-of-range offsets are clamped. Unknown mapping keys are ignored. But the rename guard fails closed -- any resolver error during the guard check means the rename is refused.

**Stale disk files.** Files not open in the editor are validated by modification time and size on every access. An external change (editing a file outside the editor) is picked up on the next request. The residual gap is the standard one: a same-size rewrite that completes within the filesystem's mtime granularity. Open files use LSP version numbers and are never stale.

**The requesting document is broken.** Definition and references serve from the last successful analysis (the existing "current or last good" policy). Rename continues to refuse on any parse error.

**Concurrent requests.** Everything resolver-related runs on the single worker thread, queued behind analyses and formats. A slow workspace scan delays later requests, but this is the same class of limitation as the existing single-worker design.

**Large workspaces.** A find-references query touches every workspace file. Each file's first access pays a parse cost, then stays cached. This is fine at demo scale and for projects of modest size. A persistent index and file-change watchers would be the answer for larger scale, but there is no concrete evidence yet that this is needed, so no work is planned for it.

**VS Code without Node/npm.** The extension cannot run, but the command-line tools and automated tests are unaffected. This is a documented prerequisite.

## What is still open

The design records no open questions requiring user judgment beyond the acceptance pass itself. However, it explicitly calls out several judgment calls that were made and are available for challenge during review:

- The provisional-API labeling -- is it the right hedge, or should the API be frozen now?
- The batch-per-document resolver shape and the decision not to cache resolutions -- is the simplicity worth the O(workspace files) cost per references query?
- Refusing rename rather than implementing cross-file rename -- is refusal an adequate floor?
- Withholding cross-file paint from the keystroke-rate highlighting path -- should resolved references influence syntax highlighting, even at the cost of coupling paint latency to workspace I/O?
- The "gear" name and `.gear` extension -- these are arbitrary and trivially renameable at implementation time if a different name is preferred.
- `examples/` as the demo's home directory -- is this the right location?

These are presented as decided-but-challengeable, not as open questions that block implementation. The design is ready to implement as written, and any of these could be revisited based on review feedback.
