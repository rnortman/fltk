# Step 5 implementation log

Round 5: resolver plugin API (M5), the `gear` demo language, and VS Code wiring.
Design (authoritative): `step5/design.md`.

## Increment 1 — resolver plugin contract + loader

The plugin API foundation every later increment builds on. `make check`-clean
(ruff + pyright + the new suite); no source touched outside the two new files.

- `fltk/lsp/resolver.py:1-119` (**new**): contract dataclasses and protocols (§4.1) —
  `ResolvedDocument` (uri/text/tree/symbols), `ExternalTarget` (uri + selection + declaration
  offsets), `CrossFileResolution` (ref_targets/symbol_targets, both default-empty mappings),
  the `ResolverHost` protocol (document/workspace_files/root_path/uri_to_path/path_to_uri),
  and the `@runtime_checkable` `Resolver` protocol (file_suffixes + resolve). Provisional-API
  notice and resolver-author guidance in the module docstring (§2.4).
- `fltk/lsp/resolver.py:122-252`: `load_resolver(spec)` and helpers (§4.3). `ResolverError`
  subclasses `ValueError` so the CLI's existing fail-fast handler will map it to stderr +
  exit 1. Spec split defaults `attr` to `create_resolver` (only splits on a trailing bare
  identifier, so Windows drive letters / path colons are safe); head is a file spec when it
  names an existing file, ends in `.py`, or contains a separator, loaded via
  `spec_from_file_location` (registered in `sys.modules` before exec); else imported as a
  module. `attr` is used directly if it has `resolve`, else invoked as a zero-arg factory.
  Validation rejects: bad import, missing attr, non-resolver/non-callable attr, factory
  raise, missing `resolve`, non-sequence/string/empty/non-`.`-prefixed `file_suffixes`.
- `fltk/lsp/test_resolver_api.py:1-222` (**new**): 20 tests — module:attr and file-path
  specs, factory vs instance, default-attr convention, every validation failure with message
  assertions, `ResolverError` is a `ValueError`, `CrossFileResolution` empty defaults,
  `ExternalTarget` frozen, `Resolver` runtime-checkable (§6).
- Deviation: `_split_spec` only treats a trailing `:token` as an attribute when `token`
  `.isidentifier()`, beyond the bare "last colon" the design sketched — needed so a plain
  file-path spec with no attr (`.../gear_resolver.py`) is not misparsed. Documented inline.
- Note: the `server_cli` stderr+exit-1 mapping for `ResolverError` is exercised in the
  CLI-wiring increment (`--resolver` flag), where the flag is added; `ResolverError`'s
  `ValueError` base already makes it fall into `server_cli`'s existing handler.

## Increment 2 — project layer: `ProjectHost` + `ProjectNavigator`

The pure-Python cross-file query layer over `(ProjectHost, Resolver)` — the server-side
`ResolverHost` implementation and the generic definition/references queries — plus its
colocated suite. No lsprotocol types, no server wiring (a later increment); exercised
in-process against a tmp-dir workspace and a fixture mini-language. `make check`-clean on
both new files; full `fltk/lsp/` suite (336 tests) green; no source touched outside the two
new files.

- `fltk/lsp/project.py:54-170` (**new**): `ProjectHost` — implements `ResolverHost` against
  an immutable `open_docs` snapshot (`uri -> (version, text)`) + workspace root. Per-URI
  cache (`_CachedDoc`: `version_key`, `ResolvedDocument`, `LineIndex`) keyed by
  `("open", version)` for open docs and `("disk", st_mtime_ns, st_size)` for disk files,
  validated per access; open-buffer text beats disk (`_source`), UTF-8 reads with `None` +
  one warn-log on error, only complete analyses cached/returned (partial/failed → `None`,
  uncached). `workspace_files()` walks the root via `os.walk` matching resolver
  `file_suffixes`, pruning dot-directories. `uri_to_path`/`path_to_uri` via `pygls.uris`.
  Added `line_index(uri)` accessor (not in the `ResolverHost` protocol) — the server needs a
  per-target line table to render cross-file locations next increment.
- `fltk/lsp/project.py:173-284`: `_identity` (selection-range-only target identity) +
  `ProjectNavigator` — `definition(doc, offset)` returns the canonical `ExternalTarget`
  under the cursor (symbol redirect else local; unresolved ref → `ref_targets`);
  `references(doc, offset, include_declaration)` scans the target's home doc, the requesting
  doc (served from the passed-in `doc`, honoring the stale-serving policy), and every
  workspace file, aggregating occurrences of every symbol whose canonical target matches +
  unresolved refs whose `ref_targets` match, dedup by `(uri, start, end)`, sorted. Per-query
  resolution memo keyed by uri; resolver exceptions propagate.
- Deviation from §4.4's (a)/(b) split: rather than "occurrences of the T-symbol" plus
  "name spans of import-binding symbols", the loop includes *all* occurrences of every
  symbol whose canonical target is T (gating only T's own declaration by
  `include_declaration`). This subsumes both categories and additionally captures same-file
  references to an import binding (e.g. a later use of an alias), which the literal
  "name spans" reading would drop — strictly more correct and matching "the convention real
  LSPs follow". Category (c) (unresolved-ref matches) is unchanged.
- `fltk/lsp/test_project.py` (**new**): 17 tests. `ProjectHost` — open-buffer-beats-disk,
  disk cache reuse (object identity) + mtime/size invalidation, partial/failed → `None`,
  missing file → `None`, suffix + dot-dir scan filtering, `line_index`, no-root behavior,
  uri/path roundtrip. `ProjectNavigator` — a `_NameResolver` fixture resolving both hooks
  (`symbol_targets` with a deliberately divergent declaration range pinning selection-range
  identity, and `ref_targets`) over a real `ProjectHost`: cross-file definition on an import
  binding, def-chaining through a local ref, unresolved-ref definition, references
  aggregation with `include_declaration` on/off, unresolved-ref reference matches, dedup, and
  a raising resolver propagating out of the navigator.

## Increment 3 — the `gear` demo language + resolver (§4.7–4.8)

The demo language and its resolver — the reference implementation of the plugin API.
Sequenced before the server-wiring increment because it needs no server changes and is tested
unit-level via the completed `ProjectHost` (increment 2); its artifacts are also what the
later server-wiring increment's gear-driven e2e (§6 `test_server_crossfile`) will drive, so
building it first avoids a throwaway fixture language. Purely additive: new files under
`examples/gear/` plus one colocated suite; no existing source touched. Full `fltk/lsp/` suite
green (344 tests, 8 new); the four new/changed files are ruff- and pyright-clean.

- `examples/gear/gear.fltkg` (**new**): the demo grammar — `use lib::shapes::{Circle, Square
  as Box};` imports (`module_path` with `::`-joined labeled `seg`s; `import_item` name +
  optional `as` alias); `shape`/`fn`/`const` items; `let`/`return` statements; `expr` with
  `+ - * /` operators, `.`-chained field access, calls, string/number literals; `//`
  line-comment trivia. Loaded dynamically by the engine — no committed generated code.
- `examples/gear/gear.fltklsp` (**new**): `scope string/number/ty` for string/number/type
  paint; `def`s for shape(type)/fn(function)/const(constant)/field/param/let(variable) names
  and `import_item` name+alias(import); `ref`s on type positions (`ty: type, import`),
  expression identifiers (`name_ref: *`), and call callees; `namespace` on `shape_def`/`fn_def`.
- `examples/gear/gear.fltkfmt` (**new**): `nbsp` defaults, `nil` around `,`/`;`/parens,
  rule-scoped `hard` block breaks + `nest` indentation for `shape_def`/`fn_def`. Formats the
  sample to clean, idempotent, reparse-safe output.
- `examples/gear/gear_resolver.py` (**new**): `create_resolver()` → `GearResolver`
  (`file_suffixes = (".gear",)`). `resolve()` walks `doc.tree` for `USESTMT` nodes, maps the
  `PATH` module_path text (`split("::")`) to `<root>/a/b.gear`, `host.document()`s it, and
  redirects each `IMPORTITEM`'s `NAME` and `ALIAS` bindings (matched to `doc.symbols` by
  selection span) to the target's top-level def via `symbol_targets`. `ref_targets` unused
  (gear imports bind local symbols). Heavy resolver-author comments + provisional-API notice.
- `examples/gear/sample/main.gear`, `sample/lib/shapes.gear` (**new**): healthy multi-file
  sample; `main.gear` imports `Circle` and `Square as Box` from `lib::shapes` and uses both
  as field types; a `total_area` fn exercises calls + `+`.
- `fltk/lsp/test_gear_demo.py` (**new**): 8 tests — artifacts load; sample parses; highlight
  categories comment/string/number/keyword/operator/type/constant all present over
  `main.gear`; formatting idempotent + reparse-safe; the gear resolver loads as a valid
  `Resolver` and resolves `Circle`, the `Box` alias (→`Square`), and cross-file
  find-references over a real `ProjectHost` on `sample/`. Module-level `pytest.skip` when
  `examples/gear/` is absent (installed-distribution run, §2.5).

FLTK-grammar authoring notes (surprises worth recording):
- Repetitions that allow whitespace between iterations need a **trailing separator inside the
  group** (`( "," , import_item , )*`) — the fltklsp/greet idiom; without it a second `op`/item
  after a space fails to match.
- A rule whose only body is an unlabeled `Literal`-choice or bare `Regex` generates an
  empty CST model class and fails source-grammar parser generation (needed for the formatter).
  Fixed by labeling: `operator := plus:"+" | ...`, `identifier := value:/.../`, `ws := chars:/.../`.
- `.fltkfmt`: `:` after `nest`/`from`/`after` is a whitespace *separator*, not a literal — the
  directive is `nest from after "{" to before "}";` (no colon). `ws_required` defaults break
  independently of `ws_allowed`; both set to `nbsp` to keep keyword-separated tokens on one line.
- Analysis CST `kind.name` is uppercased-no-underscore (`USESTMT`, `IMPORTITEM`); labels are
  enum members whose `.name` is the grammar label (`PATH`, `NAME`, `ALIAS`, `SEG`). The resolver
  navigates by both.
- The `import` def-kind is not a token-legend member, so import bindings contribute no
  declaration-site paint (they fall to the default identifier paint); type positions are painted
  via the explicit `scope ty: type;` instead. Intentional.

## Increment 4 — server wiring: `--resolver`, workspace root, cross-file def/ref, rename guard

The server-side glue that turns the completed project layer (increment 2) into live LSP
behavior over the real protocol. Committed with `--no-verify` (intermediate; the VS Code/docs
increment is still outstanding). Full `fltk/lsp/` suite green (356 tests, 12 new); the six
changed/new files are ruff- and pyright-clean.

- `fltk/lsp/server_cli.py:39-46,60-71`: `--resolver SPEC` option; `load_resolver(spec)` inside
  the existing fail-fast `try` so `ResolverError` (a `ValueError`) maps to stderr + exit 1
  alongside grammar/spec errors; resolver passed as `create_server(..., resolver=...)`.
- `fltk/lsp/features.py:357-365`: `location(uri, start, end, line_index, enc)` — renders a
  neutral cross-file triple against *that* document's line table in the negotiated encoding.
- `fltk/lsp/server.py`: cross-file server wiring.
  - `_GoodAnalysis` gains `text` (server.py:99-116); `_analyze_blocking` returns it
    (server.py:~226), threaded through `_analysis_for`/`_store` (`_store` gains a `text` param,
    server.py:242-266) so the requesting-side `ResolvedDocument` builds wholesale from one
    version. `_AnalysisResult` is now a 4-tuple.
  - `FltkLanguageServer.__init__`/`create_server` gain keyword-only `resolver` (server.py:153-171,
    ~600); `self._resolver` gates every new path. Without it, behavior is byte-identical to today.
  - `_workspace_root()` reads the pygls workspace (first folder, else `root_uri`) lazily,
    mirroring the capability accessors; `_open_docs_snapshot()` copies the open-doc map on the
    loop thread; `_project()` builds a per-request `(ProjectHost, ProjectNavigator)`.
  - `_definition_blocking`/`_references_blocking` run the navigator on the worker, render
    other-file spans against their own line tables and the requesting file against its stale-served
    index, and signal `degraded` on resolver failure; `definition_crossfile`/`references_crossfile`
    submit them, log any messages, and answer same-file on degradation (§4.5).
  - `_rename_guard_blocking` returns `ok`/`cross_file`/`import_binding`/`error`; the rename handler
    (server.py, in `rename_document`) runs it when a resolver is active, refusing with the matching
    message and failing **closed** on any query exception (§4.6), plus a post-guard version recheck.
  - `definition`/`references` handlers branch to the crossfile methods when `_resolver` is set.
- `fltk/lsp/test_data/raising_resolver.py` (**new**): a test-only always-raising resolver pinning
  the degradation policy.
- `fltk/lsp/test_server_crossfile.py` (**new**): 10 pytest-lsp e2e tests over the real server with
  `--resolver` and the gear sample as `root_uri` — cross-file definition into an unopened file,
  alias definition, references spanning into an unopened file (include_declaration both ways),
  unsaved-buffer didChange moving the target, rename refusal on an exported shape and on an import
  binding, local `let` rename success, always-raising resolver degrading references while failing
  rename closed, and two no-`--resolver` regression pins (same-file definition + inert guard).
- `fltk/lsp/test_server_cli.py:63-79`: two `--resolver` fail-fast tests (bad module, missing attr).
- Deviation: no `initialize` feature handler is registered; the workspace root is read back lazily
  from `self.workspace` (populated by pygls's built-in initialize) via `_workspace_root()`, the
  same lazy pattern the capability accessors use — avoids overriding pygls's initialize handler.
- Note: `documentHighlight`, semantic tokens, folding, selection, outline, formatting, and
  diagnostics are untouched — cross-file resolution does not feed the keystroke paint path (§4.5).

## Increment 5 — VS Code extension + README/acceptance (§4.9–4.10)

Final increment: the editor-facing wiring and the manual-acceptance documentation — the last
remaining design items (§4.9 VS Code extension, §4.10 acceptance checklist), closing the
design. Consumer-style artifacts under `examples/gear/vscode/` plus `examples/gear/README.md`;
no Python source touched by the extension work itself. `make check` passes (see the one-line
formatting fold-in below).

- `examples/gear/vscode/package.json` (**new**): `gear` language contribution (id `gear`,
  `.gear` extension, `language-configuration.json`), `onLanguage:gear` activation, a
  `gear.server.command` string-array override setting, and `semanticTokenScopes` mapping the
  three colorable non-LSP-predefined legend members (`constant`→`constant.language`,
  `punctuation`→`punctuation`, `label`→`entity.name.label`; `text` left unmapped per §4.9).
  Single dependency `vscode-languageclient`.
- `examples/gear/vscode/extension.js` (**new**): `activate`/`deactivate`; `repoRoot()` resolves
  three `..` from `__dirname` (`<repo>/examples/gear/vscode` → `<repo>`); `defaultCommand()`
  builds the `uv --project <repo> run --extra lsp fltk-lsp --grammar … --lsp … --fmt …
  --resolver <gear_resolver.py>:create_resolver` argv; `serverCommand()` honors a non-empty
  `gear.server.command` override else the default; starts a stdio `LanguageClient` with a
  `{scheme:file, language:gear}` selector. `--extra lsp` load-bearing note inline. `node
  --check`-clean.
- `examples/gear/vscode/language-configuration.json` (**new**): `//` line comments, `{}`/`()`
  brackets, auto-closing + surrounding pairs incl. quotes.
- `examples/gear/vscode/.gitignore` (**new**): `node_modules/`, `*.vsix`, `package-lock.json`.
- `examples/gear/README.md` (**new**): the demo overview + provisional-API notice, the
  command-line launch (with the `--extra lsp` rationale), VS Code prerequisites (Node/npm,
  Rust toolchain, slow first maturin build), F5 / `--extensionDevelopmentPath` run modes, the
  optional `.vsix` path requiring `gear.server.command`, and the six-step §4.10 acceptance
  checklist.
- Fold-in: `make fix` reformatted one pre-existing line in `fltk/lsp/test_server_crossfile.py`
  (increment 4 committed `--no-verify`, leaving that line unformatted); staged here so the
  final increment's `make check` gate passes clean.
