# Design — Round 5: resolver plugin API (M5), the `gear` demo language, and VS Code wiring

Status: draft for review (pre-freeze).

Provenance: the advisory docs (`README.md`, `brainstorm.md`, `fltklsp-spec.md`) remain
directional only. Verbatim from the requester, to be carried to any agent consuming them:
**"NO DECISIONS HAVE BEEN MADE. This was a brainstorming session. Everything is is malleable
at this point."** Code at HEAD (`b1bd373`) is ground truth; the step1–4 designs are
authoritative for what M0–M4 decided, and `step5/exploration.md` records the code facts this
design depends on. Per the requester, "anything from existing designs/code that does not make
sense now that we're working through details can and should be changed" — §2 calls out every
such change.

## 1. Round-5 scope: what and why

Three deliverables, one theme — cross-file navigation, end to end, demonstrable in a real
editor:

1. **The resolver plugin API** (the ADR's M5 core, D5's "per-language Python resolver hook"):
   a small Python protocol a downstream language implements, loaded by `fltk-lsp` via a new
   `--resolver` flag, that turns the same-file `SymbolTable` seam step3 built (unresolved
   `Reference`s as first-class silent values, `symbols.py:262-274`) into cross-file
   go-to-definition and find-references.
2. **A demo language, `gear`** (`.gear` files): an in-repo FLTK language with multi-file
   imports, a `.fltklsp`/`.fltkfmt` pair, and a resolver — the reference implementation of
   the plugin API and the fixture for its automated tests. Syntax is clockwork-*flavored*
   (repo-style `use a::b::{X as Y};` imports, per exploration §2) but deliberately not any
   real language, and `.gear` is not a real-world extension, so VS Code activation cannot be
   hijacked by an installed extension for a real language.
3. **VS Code wiring**: a minimal in-repo VS Code extension for `gear` that spawns `fltk-lsp`
   via `uv` from the local repo, demonstrating highlighting (comments, strings, types,
   statements, keywords, operators), formatting, and cross-file go-to-def/find-refs.
   Automated tests cover everything below the editor; final acceptance is the requester
   configuring their own VS Code against the repo and seeing it work.

Explicitly out of round 5, per the requester and by choice:

- **Rust/native acceleration** (the other half of the ADR's M5 line item) — punted by the
  requester. The step4 obligation stands: whatever round designs the native analysis path
  must expose the prefix surface and now also feed the same `SymbolTable` shape the resolver
  consumes.
- **Cross-file rename** — rename stays same-file, with a new refusal guard (§4.6) so it can
  never silently break other files.
- **`workspace/symbol`, call hierarchy, `didChangeWatchedFiles`** — future consumers of the
  same project index; nothing here needs reshaping for them.
- **A `qualified ref` `.fltklsp` language form** (spec OQ1) — this round *answers* OQ1 in the
  direction the spec floated: cross-file and qualified-name knowledge live in the resolver
  hook, not the spec language. `.fltklsp` syntax is untouched; no `.fltklsp` file changes
  meaning.
- **TextMate export** (spec OQ3) — the VS Code demo works on semantic tokens alone; a
  `language-configuration.json` (comments/brackets) is included, a TextMate grammar is not.

## 2. Deltas: corrections and decisions this round makes

### 2.1 The server learns about the workspace (first departure from per-URI-only state)

`server.py` today reads neither `root_uri` nor `workspace_folders` (exploration §1.5). This
round captures the workspace root at `initialize` and adds a project layer that can analyze
files the client never opened. This is deliberate new server scope, confined to the resolver
path: **without `--resolver`, server behavior is bit-identical to today** — no scanning, no
extra state, no new handlers' behavior change.

### 2.2 Definition/references become worker-thread operations

Today's definition/references handlers are cheap lookups into stored per-URI state
(`server.py:671-692`). With a resolver, a definition may require reading and analyzing other
files, and references may require scanning the workspace. Both handlers therefore move their
resolver-path work onto the existing single analysis worker (same executor as
parse/format), keeping the protocol loop non-blocking. The no-resolver path keeps its
current in-loop shape.

### 2.3 Rename gains a cross-file refusal guard

Step3's rename is same-file by design. With a resolver active, a same-file rename of a
symbol that other files reference (or that is an import binding) would silently corrupt the
project. New policy (§4.6): when a resolver is active, rename refuses — with an explanatory
error — any symbol that has cross-file inbound references or an external redirect target.
Without a resolver, rename behavior is unchanged.

### 2.4 The resolver API ships as **provisional** public surface

The ADR's Consequences make the server CLI and `.fltklsp` public API for out-of-tree
consumers. The resolver protocol will join them, but it has exactly one implementation
(gear) until a real downstream language (clockwork) writes one. The module docstring and the
demo README label the protocol **provisional — subject to change until validated against a
real downstream language**. This is a deliberate, called-out hedge: freezing a plugin API
against a single in-repo consumer is how APIs calcify wrong.

### 2.5 First multi-root packaging artifacts outside `fltk/`

The demo language and VS Code extension live under a new top-level `examples/` directory,
not inside the `fltk` package: they are consumer-style artifacts (a downstream language
would own these files), not library code, and must not ship in the wheel. Tests for them
live in `fltk/lsp/` per the colocated-test convention and locate `examples/` relative to the
repo root; because the wheel ships `fltk`'s colocated tests (`tool.maturin.python-packages`,
`pyproject.toml:34-36`) but not `examples/`, the two gear suites **skip at module level**
(with an explanatory reason) when the resolved `examples/gear` directory is absent, so an
installed-distribution test run skips cleanly instead of failing on missing fixtures. The
VS Code extension requires Node/npm to install its one dependency
(`vscode-languageclient`); that is a documented prerequisite for the manual acceptance pass
only — no Python test needs Node.

## 3. Deliverables and file layout

| File | Contents |
|---|---|
| `fltk/lsp/resolver.py` | **New**: `Resolver` protocol, `ResolvedDocument`, `ExternalTarget`, `CrossFileResolution`, `ResolverHost` protocol, `load_resolver(spec)` (§4.1, §4.3) |
| `fltk/lsp/project.py` | **New**: `ProjectHost` (workspace scan, per-file analysis cache, open-buffer-over-disk reads) and `ProjectNavigator` (cross-file definition/references queries) (§4.2, §4.4) |
| `fltk/lsp/server.py` | Capture workspace root; optional resolver wiring; definition/references resolver paths on the worker; rename refusal guard (§4.5–4.6) |
| `fltk/lsp/server_cli.py` | `--resolver SPEC` flag; startup load + validation, fail-fast (§4.3) |
| `fltk/lsp/features.py` | Small helper to render `(uri, start, end)` triples to `lsp.Location` via a per-target `LineIndex` (§4.5) |
| `examples/gear/gear.fltkg`, `gear.fltklsp`, `gear.fltkfmt` | The demo language (§4.7) |
| `examples/gear/gear_resolver.py` | The gear resolver — reference implementation of the plugin API (§4.8) |
| `examples/gear/sample/` | Multi-file sample project (`main.gear`, `lib/shapes.gear`, …) (§4.7) |
| `examples/gear/vscode/` | VS Code extension: `package.json`, `extension.js`, `language-configuration.json`, `.gitignore` (node_modules) (§4.9) |
| `examples/gear/README.md` | Setup walkthrough: uv command line, VS Code steps, acceptance checklist (§4.9–4.10) |
| `fltk/lsp/test_resolver_api.py`, `test_project.py`, `test_server_crossfile.py`, `test_gear_demo.py` | Tests (§6) |

No changes to: `symbols.py`, `classify.py`, `engine.py`, `lsp_config.py`, the `.fltklsp`
grammar, plumbing, generated artifacts, Rust, Bazel, or any existing test's expectations.
`pyproject.toml` is untouched (no new Python dependencies; `examples/` is outside the
package).

## 4. Proposed approach

### 4.1 The resolver plugin contract (`fltk/lsp/resolver.py`)

The step3 seam is the contract's foundation: per document, `symbols.extract` yields a
`SymbolTable` whose `Reference.symbol is None` entries are exactly the same-file-unresolvable
references, and whose `Symbol`s are the file's definable surface. The resolver's job: given
one analyzed document and the ability to obtain other analyzed documents, say where things
*really* live.

```python
@dataclasses.dataclass(frozen=True)
class ResolvedDocument:
    """One analyzed document as the resolver sees it."""
    uri: str
    text: str
    tree: Any                      # analysis-grammar CST root
    symbols: symbols.SymbolTable

@dataclasses.dataclass(frozen=True)
class ExternalTarget:
    """A definition site in another (or the same) file, in codepoint offsets."""
    uri: str
    name_start: int; name_end: int          # selection range
    range_start: int; range_end: int        # declaration range

@dataclasses.dataclass(frozen=True)
class CrossFileResolution:
    """The resolver's answers for one document.

    ref_targets: cross-file targets for references unresolved same-file.
    symbol_targets: redirects for symbols that are import bindings — 'this local
    symbol is really declared over there' (drives definition-chaining and the
    global-references match).
    """
    ref_targets: Mapping[symbols.Reference, ExternalTarget] = ...
    symbol_targets: Mapping[symbols.Symbol, ExternalTarget] = ...

class ResolverHost(Protocol):
    """Server-provided services; all methods are cheap-or-cached."""
    def document(self, uri: str) -> ResolvedDocument | None: ...
        # Analyze (open-buffer text if the client has the file open, else disk) and
        # cache; None if unreadable/nonexistent. Failed/partial parses return None —
        # resolvers only ever see complete analyses.
    def workspace_files(self) -> Sequence[str]: ...
        # URIs of workspace files matching the resolver's suffixes; empty when the
        # client provided no workspace root.
    def root_path(self) -> pathlib.Path | None: ...
    def uri_to_path(self, uri: str) -> pathlib.Path | None: ...
    def path_to_uri(self, path: pathlib.Path) -> str: ...

@runtime_checkable
class Resolver(Protocol):
    file_suffixes: Sequence[str]            # e.g. (".gear",); drives workspace scan
    def resolve(self, doc: ResolvedDocument, host: ResolverHost) -> CrossFileResolution: ...
```

Design points, each deliberate:

- **Batch, not per-reference.** One `resolve()` call per document lets the resolver walk the
  document's import constructs once and answer everything, instead of re-deriving the import
  map per reference. `Reference` and `Symbol` are frozen (hashable) dataclasses; the mappings
  are keyed by the exact objects from `doc.symbols`, which the server holds.
- **The resolver reads import constructs from the target grammar's own CST** (`doc.tree`)
  or from `doc.symbols` — `.fltklsp` carries no cross-file vocabulary (exploration §1.3),
  and this round keeps it that way. The project model (what `a::b` means on disk, what an
  alias binds) is unrepresentable in a selector language; that is the whole reason D5 made
  this a Python hook.
- **`ExternalTarget` is a location, not a symbol.** No cross-document object graph: the
  resolver chases chains itself (via `host.document`) if its language has re-exports; the
  server never recurses.
- **Canonical identity is the selection range.** Everywhere the server compares targets
  (§4.4's aggregation, §4.6's guard), identity is `(uri, name_start, name_end)` only;
  `range_start/range_end` are presentation (the peek window), never identity. The protocol
  docstring still tells resolver authors to copy all four offsets verbatim from the target
  document's `SymbolTable` — but a resolver whose declaration range disagrees (trivia
  inclusion, say) can no longer silently empty find-references or defang the rename guard.
  The §6 fixture resolver pins this rule with a deliberately divergent declaration range.
- **Resolutions are not cached by the server.** `host.document()` caches the expensive part
  (parse + extract, keyed by content version, §4.2); `resolve()` itself is a cheap walk and
  is recomputed per request. Definition/references are user-action-rate, not
  keystroke-rate; skipping a resolution cache eliminates the entire invalidation problem
  (which files does a resolution depend on?) at demo-appropriate cost. Documented
  limitation, revisit on evidence — the ProjectHost cache is where an index would grow.
- **No `.fltklsp` involvement.** Kind filtering, path mapping, alias semantics: all
  resolver-internal.

### 4.2 `ProjectHost` (`fltk/lsp/project.py`)

The server-side implementation of `ResolverHost`:

- **Text source**: for a requested URI, the open-editor buffer (pygls workspace text
  document) wins over disk; disk reads are UTF-8 with errors surfaced as `None` (plus one
  `window/logMessage`). Unsaved edits therefore participate in cross-file resolution.
- **Cache**: `dict[uri, _CachedDoc]` holding `(version_key, ResolvedDocument, LineIndex)`.
  `version_key` is the LSP document version for open docs and `(st_mtime_ns, st_size)` for
  disk files; validated on every access, re-analyzed on mismatch. Analysis reuses the one
  `AnalysisEngine` — same grammar, same config, same `analyze()`; only complete analyses
  are cached and returned (partial/failed → `None`, not cached, so a later fix re-analyzes).
- **Workspace scan**: `workspace_files()` walks the root captured at `initialize`
  (first workspace folder, else `root_uri`, else none), matching the resolver's
  `file_suffixes`, skipping dot-directories (`.git`, `.venv`, …). The listing is recomputed
  per request (no watcher this round); file *content* freshness comes from the per-access
  `version_key` check. Editors don't notify servers of unopened-file disk changes without
  `didChangeWatchedFiles`, which is out of scope — mtime validation on access is the
  degraded-but-correct substitute.
- **Threading**: `ProjectHost` is only ever touched from the single analysis worker (§2.2),
  so it needs no locking. Which URIs a `resolve()` will request is unknowable at submit, so
  the handler snapshots the **entire open-document map** — `uri -> (version, text)` — plus
  the workspace root on the loop thread at submit time and hands it to the host;
  `document()` consults only that snapshot and disk, never the live pygls workspace (which
  `didChange` mutates on the loop thread concurrently — the torn-read hazard the
  `rename_document` snapshot comment guards against, `server.py:437-439`). The snapshot is
  O(open documents) reference copies, extending the step4 `_analyze_blocking` submit-time
  pattern to a whole map because the needed subset is worker-side knowledge.

### 4.3 Loading a resolver (`--resolver`, `load_resolver`)

```
fltk-lsp --grammar lang.fltkg [--lsp ...] [--fmt ...] [--resolver SPEC] ...
```

`SPEC` is `module.path:attr` or `path/to/file.py:attr` (a path is recognized by an existing
file or a `.py`/`/` in the head; file specs load via `importlib.util.spec_from_file_location`
— essential for the uv-run-from-repo demo, where the resolver is not an installed package).
`attr` names either a `Resolver` instance or a zero-argument factory returning one; if the
named object has no `resolve` attribute and is callable, it is invoked. Convention (and the
gear demo's shape): a factory named `create_resolver`.

Startup validation, fail-fast before any protocol I/O (extending the step2 §4.1 sequence):
import errors, a missing/wrong-typed `attr`, empty or non-`.`-prefixed `file_suffixes`, or a
missing `resolve` method each print a formatted message to stderr and exit 1 — a broken
resolver is a startup error, never a half-working server, matching the `.fltklsp`/`.fltkfmt`
policy.

### 4.4 `ProjectNavigator`: the generic cross-file queries (`fltk/lsp/project.py`)

Pure-Python query layer over `(ProjectHost, Resolver)`; no lsprotocol types (the server
renders). The key notion is a symbol's **canonical target**, a `(uri, name_start, name_end,
range_start, range_end)` tuple whose identity is its `(uri, name_start, name_end)` prefix
(§4.1 — declaration ranges never participate in matching):

```
canonical(doc, symbol) = resolver.resolve(doc, host).symbol_targets.get(symbol)
                         or local_target(doc.uri, symbol)
```

One redirect hop, by construction (`ExternalTarget` is terminal, §4.1).

- **`definition(doc, offset)`**: run step3's `symbol_target` query head. Cursor on a symbol
  or same-file-resolved reference → that symbol's canonical target. Cursor on an unresolved
  reference → `resolve(doc).ref_targets.get(ref)`, else `None`. Same-file behavior when no
  resolver: unchanged (this layer isn't invoked).
- **`references(doc, offset, include_declaration)`**: identify the queried thing's canonical
  target `T` (via the same head; for an unresolved ref, its `ref_targets` entry). Then for
  the home document of `T` **and every `host.workspace_files()` document** (analyzed via the
  cache): collect (a) same-file occurrences of the symbol whose canonical target is `T`
  (step3's `occurrences`, minus the declaration unless `include_declaration`), (b) name
  spans of symbols whose canonical target is `T` but which are not `T` itself (import
  bindings *are* references to the definition — the convention real LSPs follow), and (c)
  unresolved references whose `ref_targets` entry is `T`. Deduplicate by `(uri, start, end)`.
  Cost is O(workspace files) resolver calls per request against cached analyses —
  demo-scale by design, documented limitation (§5).

### 4.5 Server wiring (`server.py`, `features.py`)

- `initialize` captures the workspace root (alongside the existing capability captures,
  `server.py:409-423` pattern). `create_server(...)` gains a keyword-only
  `resolver: Resolver | None = None` (additive; existing callers unchanged).
- With a resolver: the `definition` and `references` handlers submit a job to the analysis
  executor that (1) ensures the requesting document's current analysis (the existing
  `_analysis_for` path), (2) runs the `ProjectNavigator` query, (3) returns neutral
  `(uri, start, end)` triples plus each target's `LineIndex`. The handler renders them via a
  new `features.location(uri, start, end, line_index, enc)` helper — positions in *other*
  files must be computed against *those files'* line tables, in the session's negotiated
  encoding. Read-only stale-serving policy is per-document and unchanged: the requesting
  document serves from current-or-last-good exactly as today; other documents come from the
  ProjectHost cache (complete analyses only). To make the last-good path constructible,
  `_GoodAnalysis` gains a `text: str` field (module-private; one string per open document —
  today the last-good text survives only as the private `LineIndex._text`,
  `positions.py:37`), and the requesting-side `ResolvedDocument` is built **wholesale from
  that snapshot** — text, tree, symbols, line index all from one version, never pairing
  live buffer text with a last-good tree (exactly the version-mixing `_GoodAnalysis`'s
  docstring rules out).
- `documentHighlight` stays same-file (it is a same-document feature by definition).
  Semantic tokens, folding, selection, outline, diagnostics, formatting: untouched —
  cross-file resolution does **not** feed highlighting this round (ref-site paint stays
  same-file). Pulling the resolver into the per-keystroke `analyze()` path would couple
  paint latency to workspace I/O; deferred until evidence demands it, and recorded as the
  natural follow-up once resolutions are cached.
- Resolver exceptions in the definition/references paths: caught (`Exception`), logged via
  `window/logMessage`, degraded to the same-file answer — a buggy resolver downgrades the
  experience, never breaks the server. The one deliberate exception is the rename guard,
  which fails **closed** (§4.6). Bogus `ExternalTarget` offsets are clamped by the
  target's `LineIndex` (clamping is its designed behavior, step2 §4.5).

### 4.6 Rename refusal guard (§2.3)

In the rename handler, after step3's existing current-version and occurrence steps and
before the verify-reparse: if a resolver is active, run the global-references query for the
target symbol; if any occurrence lies outside the requesting document, or the symbol has a
`symbol_targets` redirect (it is an import binding — renaming it locally would detach it
from what it imports), fail the request with "cannot rename: symbol is referenced in other
files" (respectively "…is an import binding"). The guard fails **closed**: any exception
during its global query — from the resolver or from analyzing a workspace file — refuses
the rename with "cannot rename: could not verify cross-file references". Degrading to the
same-file answer here (the §4.5 disposition for read-only features) would let a buggy or
transiently-failing resolver silently reopen the exact hazard §2.3 exists to close.
Same worker job, so no new race shape; the step3 versioned-`documentChanges` policy is
unchanged for renames that pass. Cross-file
rename — emitting a multi-file `WorkspaceEdit` with per-file verify-reparse — is real
design work deferred to a future round; refusal is the safe floor.

### 4.7 The `gear` demo language (`examples/gear/`)

Requirements it must exhibit (requester's brief): comments/trivia, strings, types,
statements, keywords, operators; multi-file imports; formatting; def/ref. Shape (sketch —
the implementer owns the exact grammar, these constructs are the contract):

```
// gear — a demo language for fltk-lsp. Not a real language.
use lib::shapes::{Circle, Square as Box};

shape Wheel {
    hub: Circle;
    frame: Box;
}

const SPOKES: Int = 36;
const LABEL: Text = "front wheel";

fn rim_area(w: Wheel) -> Float {
    let r = w.hub;
    return 3.14 * r * r;      // operators: * + - / -> =
}
```

- **Grammar** (`gear.fltkg`): `file := , use_stmt* , item+ ;` with `use_stmt` carrying a
  `::`-separated module path (each segment individually labeled — the step3 §2.4 guidance)
  and a braced import list with optional `as` aliases (the clockwork-precedent shape,
  exploration §2); items are `shape_def | fn_def | const_def`; statements `let`/`return`;
  expressions with arithmetic operators, field access, calls, string/number literals;
  line-comment trivia (`//`). Loaded dynamically by the server (no committed generated
  code, no `gencode` step — exploration §6 confirms the LSP stack needs none).
- **`gear.fltklsp`**: `scope` statements covering every requested highlight class
  (structural comments if any, strings, numbers, `type_ref: type` for contextual type
  paint, `enumMember`/`constant` for consts); `def`s for shape/fn/const/field/param/let
  names and for `use` item names and aliases; `ref`s for type positions and expression
  identifiers; `namespace` on `shape_def` and `fn_def` (exercising the step3 hoist).
- **`gear.fltkfmt`**: enough structure to make Format Document visibly do something —
  block indentation, spacing around operators and `:`/`->`.
- **Sample project** (`examples/gear/sample/`): at least `main.gear` and `lib/shapes.gear`
  (module path `lib::shapes` ⇒ `<root>/lib/shapes.gear`), with at least one aliased
  import in active use. The samples are kept healthy (no deliberate errors or unresolved
  references); the README's acceptance checklist has the tester introduce errors live
  (§4.10 item 6).

### 4.8 The gear resolver (`examples/gear/gear_resolver.py`)

`create_resolver()` returns a `Resolver` with `file_suffixes = (".gear",)`. `resolve()`:
walk `doc.tree`'s `use_stmt` nodes; map each module path to a workspace-relative file
(`a::b` → `a/b.gear` under `host.root_path()`); `host.document()` it; find the named
top-level symbol in that document's `SymbolTable` root scope; emit a `symbol_targets` entry
redirecting the local import-binding symbol (the alias when present, else the name — and
the pre-alias name's binding too, so both identifiers navigate). Unmatched names or missing
files yield no entry — silent degradation, same philosophy as same-file unresolved
references. `ref_targets` stays empty for gear (its imports bind local symbols, so nothing
is unresolved-but-resolvable); the `ref_targets` path is exercised by a test-local fixture
resolver instead (§6) — both hooks stay covered.

The file doubles as the *documented example* for downstream resolver authors: heavily
commented, provisional-API notice at top (§2.4).

### 4.9 VS Code extension (`examples/gear/vscode/`)

Minimal, plain-JavaScript (no TypeScript build step; `npm install` fetches the single
dependency `vscode-languageclient`):

- `package.json`: language contribution (`id: gear`, `extensions: [".gear"]`,
  `language-configuration.json` for `//` comments, brackets, auto-closing pairs);
  activation on `onLanguage:gear`; a `gear.server.command` setting (string array) to
  override the launch command; and `semanticTokenScopes` mappings for the four
  non-LSP-predefined legend members (step1 §4.5) so they actually color in default themes —
  `constant` → `constant.language`, `punctuation` → `punctuation`, `label` →
  `entity.name.label`, `text` unmapped. Without these, gear's `constant`-painted tokens
  would silently render uncolored — the "clients that don't theme them simply won't color
  them" caveat step1 §4.5 recorded, closed here on the client side.
- `extension.js`: computes the repo root from its own location
  (`<repo>/examples/gear/vscode` → three `..`), builds the default command
  `uv --project <repo> run --extra lsp fltk-lsp --grammar <repo>/examples/gear/gear.fltkg
  --lsp … --fmt … --resolver <repo>/examples/gear/gear_resolver.py:create_resolver`,
  honors the `gear.server.command` override, and starts a stdio `LanguageClient`.
  `--extra lsp` is load-bearing: pygls lives only in the `lsp` optional extra
  (`pyproject.toml:27-28`), and plain `uv run` syncs default groups only (`dev` = maturin),
  so without it a clean checkout gets a pygls-less environment and `server_cli.py:44-48`
  exits 1 before any protocol I/O — an environment-dependent trap that dev machines
  (whose venvs have pygls via test-group syncs) would never surface. Default
  client capabilities are sufficient (utf-16; the server negotiates it — step2 §2.4); no
  utf-32 opt-in is attempted.
- Run modes, documented in the README: primary — open `examples/gear/vscode` in VS Code and
  F5 (Extension Development Host), or `code --extensionDevelopmentPath=...`; both work
  against the in-repo defaults with zero configuration beyond `npm install`. The README's
  prerequisites name Node/npm (extension install only) **and the Rust toolchain** — per
  CLAUDE.md, without rustup/cargo `uv run` cannot build the package at all — and warn that
  the first launch pays the one-time maturin debug build (a visibly slow first start, not a
  hang). Optional —
  `npx @vscode/vsce package` + install the `.vsix`, in which case `gear.server.command`
  must be set (the packaged extension no longer lives in the repo, so the relative-root
  default is wrong there; the README says so explicitly).

### 4.10 Acceptance

Automated (§6) plus the requester's manual pass, scripted as a checklist in
`examples/gear/README.md`:

1. `npm install` in `examples/gear/vscode`; F5 (or `--extensionDevelopmentPath`); open
   `examples/gear/sample/` as the workspace folder.
2. Highlighting: comments, strings, numbers, keywords (`shape`/`fn`/`let`/`return`/`use`),
   operators, types, constants all visibly distinct in `main.gear`.
3. Formatting: mangle whitespace, Format Document restores it.
4. Go-to-def: F12 on an imported name (and on a local use of an alias) lands in
   `lib/shapes.gear`.
5. Find-refs: Shift+F12 on a shape definition in `lib/shapes.gear` lists locations in
   `main.gear` — including with `main.gear` never having been opened in the session.
6. Live degradation: introduce a syntax error → diagnostic + prefix-fresh highlighting
   (M3); rename an exported shape → refusal message (§4.6); rename a local `let` → works.

## 5. Edge cases and failure modes

- **No workspace root** (client sends none): `workspace_files()` is empty; `document()`
  still serves open buffers and absolute-path URIs, so definition through an import can
  still work if the resolver can construct the URI; find-refs degrades to same-file.
  Logged once at initialize.
- **Import target missing/unparsable**: `host.document()` → `None`; resolver emits no
  entry; navigation degrades to same-file. Silent (same policy as unresolved references,
  step3 §5) — with live editing, transiently-broken neighbors are the normal state.
- **Import cycles** (`a` uses `b` uses `a`): the host caches per-document analyses and the
  server never recurses (§4.1); a resolver that chases chains must bound itself — the gear
  resolver does one hop by construction. Resolver-author guidance in `resolver.py`'s
  docstring.
- **Resolver raises / returns garbage**: exception → catch, log, same-file answer for
  definition/references (§4.5) but fail-closed refusal in the rename guard (§4.6);
  out-of-range offsets → clamped by the target's `LineIndex`; unknown mapping keys (objects
  not from `doc.symbols`) simply never match and are dead weight.
- **Stale disk cache**: unopened files re-validate by `(mtime_ns, size)` on every access;
  an editor-external change is picked up on the next request. Open files use LSP versions —
  never stale. Sub-mtime-granularity same-size rewrites are the residual (standard) hole.
- **Requesting document currently broken**: definition/references serve from
  current-or-last-good as today (partial analyses have symbols too, but the step4 policy —
  completeness beats freshness for navigation — carries over unchanged); rename keeps
  refusing on any parse error.
- **Concurrent requests**: everything resolver-touching runs on the single worker, FIFO
  behind analyses/formats; a slow workspace scan delays later requests, same class as the
  existing `TODO(lsp-analysis-watchdog)` limitation. Not made worse structurally — one
  scan is O(files) stat calls plus first-touch parses that then stay cached.
- **Large workspaces**: O(files) resolver calls per references request, first-touch parse
  cost per file. Fine for the demo and for clockwork-scale projects; documented limitation,
  revisit with a persistent index + `didChangeWatchedFiles` if a real consumer hits it (no
  `TODO(slug)` — no concrete evidence yet, per the step4 §3.2 convention).
- **Files outside the workspace root**: served by `document()` if the resolver asks by URI;
  never in `workspace_files()`. Symlinked duplicates may index twice; harmless
  (deduplication is by URI) and documented.
- **VS Code without Node/npm**: the extension cannot run; the CLI + automated tests are
  unaffected. Prerequisite stated in the README.

## 6. Test plan (TDD; colocated in `fltk/lsp/`)

- **`test_resolver_api.py`** — `load_resolver`: module:attr spec, file-path spec, factory
  vs instance, default-attr convention; each validation failure (bad import, missing attr,
  no `resolve`, bad `file_suffixes`) raises with a useful message; `server_cli` maps these
  to stderr + exit 1 (extending `test_server_cli.py`'s fail-fast pattern).
- **`test_project.py`** — `ProjectHost` against a tmp-dir workspace and a fixture
  mini-language: open-buffer text beats disk; disk cache invalidates on mtime/size change;
  version-keyed reuse (analysis object identity across unchanged accesses); partial/failed
  analyses return `None` and are not cached; workspace scan filters suffixes and skips
  dot-dirs; no-root behavior. `ProjectNavigator` with a **test-local fixture resolver**
  exercising both hooks: `ref_targets` (unresolved ref → cross-file target — the hook gear
  doesn't use) and `symbol_targets` (redirect chaining, canonical-target identity —
  including the §4.1 selection-range-only matching rule, pinned by a fixture target whose
  declaration range deliberately diverges from the target `SymbolTable`'s yet still
  matches); references aggregation (occurrences + import bindings + unresolved-ref matches,
  include_declaration on/off, dedup); a resolver exception propagates out of the navigator
  (the catch lives in the server layer, §4.5).
- **`test_gear_demo.py`** — the committed gear artifacts are loadable and correct:
  grammar + `.fltklsp` + `.fltkfmt` load cleanly; the sample project parses; highlight
  classes cover every requested category (assert tokens of type comment, string, number,
  keyword, operator, type, constant exist over `main.gear`); formatting is idempotent on
  the formatted sample; the gear resolver resolves `Circle` and the `Box` alias to
  `lib/shapes.gear` (unit-level, via a real `ProjectHost` over `examples/gear/sample/`).
- **`test_server_crossfile.py`** — pytest-lsp end-to-end over the real server via the
  harness convention (`[sys.executable, "-m", "fltk.lsp.server_cli", ...]`, exploration
  §5.2) with `--resolver`, `root_uri` pointing at the sample project — the suite's first
  multi-URI scenarios (exploration §5.2): definition on an imported name in `main.gear` →
  `Location` in `lib/shapes.gear` (file never opened via didOpen — disk path); references
  on the shape def in `lib/shapes.gear` → locations in `main.gear`, include_declaration
  both ways; edit-the-unsaved-buffer case (didChange to `lib/shapes.gear`, definition
  target moves accordingly); rename of the exported shape → refusal error; rename of a
  local binding → succeeds as before; a server run with a test-local always-raising
  resolver → references degrade to same-file while rename fails closed (§4.5–4.6); a
  no-`--resolver` server run of the same requests → step3 behavior byte-identical
  (regression pin for §2.1's "bit-identical without a resolver").
- Existing suites stay green: `uv run pytest`, `uv run ruff check . && uv run pyright` —
  in particular all step3/step4 server tests, unchanged, pin the no-resolver paths.
- Not automated: the VS Code extension itself (JavaScript, editor-hosted). Its contract is
  pinned indirectly — the **argument vector** it launches (`--grammar/--lsp/--fmt/--resolver`
  values) is the one `test_server_crossfile` drives; the `uv ... run --extra lsp` launcher
  layer itself is exercised only by the manual acceptance checklist (§4.10), which is why
  §4.9 spells out why `--extra lsp` is load-bearing rather than leaving it implicit.

## 7. Roadmap notes

- **Native/Rust acceleration** (punted): the future native analysis path must feed the same
  `SymbolTable`/`ResolvedDocument` shapes; the resolver API is parser-backend-agnostic by
  construction (it sees extracted tables and structural CSTs only).
- **Cross-file rename**: the refusal guard (§4.6) marks exactly the spot; the
  references-aggregation query already computes the edit set a future round would render
  into a multi-file `WorkspaceEdit`.
- **Resolution caching / workspace index / `didChangeWatchedFiles`**: `ProjectHost` is the
  seam; grow it when a real consumer's scale demands (§5).
- **Ref-site paint for cross-resolved references**: natural once resolutions are cached;
  deliberately withheld from the keystroke path now (§4.5).
- **Spec OQ1 (qualified names)**: answered as resolver-territory; a `qualified ref`
  language form remains possible later but nothing here depends on it.
- **Clockwork adoption**: the real validation of the provisional API (§2.4) — writing
  clockwork's resolver against this protocol is the natural next round after this one, and
  the intended trigger for de-provisionalizing.

## 8. Open questions

None requiring user judgment beyond the acceptance pass itself. Judgment calls decided and
recorded for review to challenge: the provisional-API labeling (§2.4), batch-per-document
resolver shape and no-resolution-cache policy (§4.1), rename refusal rather than cross-file
rename (§4.6), cross-file paint withheld from the keystroke path (§4.5), the `gear` name
and `.gear` extension (arbitrary; trivially renameable at implementation time if the
requester prefers another), and `examples/` as the demo's home (§2.5).
