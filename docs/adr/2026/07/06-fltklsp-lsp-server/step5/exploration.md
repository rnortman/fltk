# Step 5 exploration: resolver plugin API (M5), a multi-file demo language, and a VS Code-wired `fltk-lsp`

Context-only survey. No design proposed here.

**Verbatim instruction from the requester, to be carried forward to any agent that consumes
the ADR docs in `docs/adr/2026/07/06-fltklsp-lsp-server/`:**

> @docs/adr/2026/07/06-fltklsp-lsp-server/README.md and the docs it links to are the important
> context. These come from a brainstorm session. Despite the fact that this doc is written as if
> decisions were made, let me be clear: NO DECISIONS HAVE BEEN MADE. This was a brainstorming
> session. Everything is is malleable at this point.

Per the requester, `docs/adr/2026/07/06-fltklsp-lsp-server/step[1,2,3,4]/design.md` are
implemented and are authoritative over the brainstorm/spec/ADR — but "anything from existing
designs/code that does not make sense now that we're working through details can and should be
changed." Code at HEAD (`b1bd373`) is ground truth below; the step1–4 design docs are cited only
where they describe what the *current* code does.

## 1. Resolver-relevant code surface (M5 target)

### 1.1 Nothing resolver-shaped exists yet

`grep -rn "resolver" fltk/lsp/` returns zero hits. No plugin-loading mechanism, no cross-file
concept, no notion of "other files in this project" anywhere in `fltk/lsp/`. The ADR's D5
("a resolver plugin for cross-file... loaded by the server") and the spec's "per-language Python
resolver hook" are prose only; nothing has been built toward them in rounds 1–4.

### 1.2 The unit a resolver would consume: `SymbolTable` (`fltk/lsp/symbols.py`)

Everything is per-document. `extract(tree, tables, resolved_config, text) -> SymbolTable`
(`fltk/lsp/symbols.py:130-170`) walks one document's analysis CST and returns:

```python
@dataclasses.dataclass(frozen=True)
class Symbol:                                    # symbols.py:18-32
    name: str
    kind: tuple[str, ...]
    name_start: int; name_end: int                # selection range
    range_start: int; range_end: int               # declaration range

@dataclasses.dataclass(frozen=True)
class Reference:                                  # symbols.py:35-49
    name: str
    start: int; end: int
    depth: int
    kinds: tuple[tuple[str, ...], ...] | Literal["*"]
    tier: lsp_config.Tier
    symbol: Symbol | None                          # None = unresolved

@dataclasses.dataclass(frozen=True)
class SymbolTable:                                # symbols.py:63-100
    root: Scope
    symbols: tuple[Symbol, ...]
    references: tuple[Reference, ...]
    def symbol_at(self, offset) -> Symbol | None: ...
    def reference_at(self, offset) -> Reference | None: ...
    def occurrences(self, symbol) -> list[tuple[int, int]]: ...
```

`_resolve` (`symbols.py:262-274`) walks a reference's scope outward and stops at the first
same-name, kind-matching symbol; if nothing matches in any enclosing scope up to `root`,
`Reference.symbol` stays `None` — this is the exact seam step3/design.md §7 calls out: "the
resolver's job becomes precisely 'given this file's `SymbolTable` (its unresolved references and
its exported symbols) and other files, produce cross-file resolutions'" (`step3/design.md:541-545`).
Unresolved references are a first-class silent value already (§5 of that design), not an error
state — nothing needs to change in `symbols.py` to make a reference resolvable *later* by an
external mechanism; there is simply no such mechanism wired in today.

Qualified names (`ns::Type`, `a.b.c`) are unhandled at the text level: a `ref` anchored on such a
node compares its **whole span text** against symbol names (`_resolve`, `symbols.py:270-271`,
`symbol.name == ref.name`) and never matches unless the grammar labels the segments so the `ref`
anchors a single segment (step3/design.md §2.4, still true — no qualified-ref parsing exists).

### 1.3 `.fltklsp` has no import/use-related statement

The grammar `fltk/lsp/fltklsp.fltkg` (rules: `lsp_spec`, `statement`, `rule_config`,
`scope_stmt`, `def_stmt`, `ref_stmt`, `namespace_stmt`, `anchor`, `dotted_name`, `identifier`,
`literal`) has no construct for declaring what to import, alias, or how a `ref`'s unresolved
kind maps to another file's rule. `fltklsp-spec.md` §3's closing line stands unimplemented:
"Cross-file resolution is out of scope for this language. A per-language Python resolver hook
(loaded by the server) maps unresolved references + the file's import constructs to other files."
There is no `import`/`use` anchor concept in `.fltklsp` today — a resolver would have to be handed
the *target* grammar's own import/use nodes directly (via the CST or `SymbolTable`), since
`.fltklsp` itself carries no cross-file vocabulary.

### 1.4 `AnalysisEngine` and `DocumentAnalysis`: single-document, single-grammar, no injection point

`AnalysisEngine.__init__` (`fltk/lsp/engine.py:93-107`) takes one `gsm.Grammar` and one
`ResolvedLspConfig`; `analyze(text)` (`engine.py:149-217`) is a pure function of one document's
text — it has no parameter for "the rest of the project" and calls `symbols.extract` with only
that document's tree. `DocumentAnalysis` (`engine.py:55-81`) carries one `SymbolTable`. There is
no hook signature anywhere (`__init__`, `analyze`, or a class attribute) for a resolver
callback, and no place a resolver's output (cross-file symbol bindings) would be stored or
consumed downstream by `classify.py` (ref-site paint, `classify.py`'s `symbol_table` parameter
per step3/design.md §2.2) or by `features.py`'s definition/references handlers.

### 1.5 Server: per-URI state only, no project-wide index

`fltk/lsp/server.py`'s `FltkLanguageServer` keeps `self._docs: dict[str, _DocState]`
(`server.py:162`), populated lazily as documents are opened/analyzed (`did_open`, `did_change`
handlers, `server.py:597-608`) — there is no proactive workspace scan, no
`workspace/didChangeWatchedFiles` handler, no `workspace/symbol` handler, and `root_uri`/
`workspace_folders` from `InitializeParams` are read nowhere in `server.py` (only referenced, as
`root_uri=None`, in the test harness's own `_init_params`, `test_server.py:75-97`). A resolver
that needs to open and analyze *other* files (to resolve `use path::Type`) would have to drive
`AnalysisEngine.analyze` itself against file contents it reads — there is no existing
"analyze this other URI and cache it" utility; `_analyze_blocking`/`_analysis_for`/`_store`
(`server.py:194-297`) are all keyed to the single document a protocol request names, on one
worker thread shared by the whole server.

Definition/references/rename features (`features.py`'s `definition_location`,
`reference_locations`, etc., and their handlers in `server.py:671-713`) all operate on one
`good.symbols: SymbolTable` fetched via `_serveable_for` (`server.py:389-405`) for the single
requested URI — nothing merges symbol tables across documents, and `lsp.Location`/
`lsp.WorkspaceEdit` results are always scoped to the current document's own URI.

### 1.6 Native/Rust fast path: still absent, and specifically flagged for M5

`step1/design.md` §2.3 recorded that `generate_parser(rust_cst_module=...)` does not exist;
`step4/design.md` §2 (first bullet) reconfirms "There is no Rust runtime analysis path to
change" and explicitly defers to whichever round designs M5: "whatever round designs the M5
native analysis path must expose the same prefix surface from the native seam." Nothing in the
current tree changes this — `grep -rn "rust_cst_module"` across `fltk/` still returns nothing;
the only Rust-adjacent per-grammar artifact mechanism is the offline `genparser gen-rust-*` CLI
path used by consumers' own maturin builds. The requester's message for this round explicitly
punts Rust acceleration, so this is confirmed-inert background only.

## 2. Multi-file import precedent (clockwork)

The ADR (`README.md:88`) and spec (`fltklsp-spec.md` §3, §6 OQ1) both cite clockwork's
`use @repo::path::Type` as the motivating cross-file case. The actual clockwork grammar
(`/home/rnortman/tps/clockwork/clockwork/dsl/clockwork.fltkg`) defines:

```
module := (doc . '\n')? , ((clk_generate , clk_inner_attrs? , clk_use* , clk_entity+)
                             | (use* , entity+));
use := "use" : use_body . " "* . ";" . "\n"+ ;
use_alias := "as" : alias:identifier ;
use_body := (use_repo:repo_prefix . "::")? . use_path:namespace_path
            . (("::" . use_block) | (" "+ . use_alias))?;
use_block := "{" , use_type , ((";"|",") , use_type)* , (";"|",")? , "}" ;
use_type := typename:identifier , (use_alias)? ;
```

So the real-world shape is: an optional repo prefix, a dotted namespace path, then either a
single trailing alias (`use foo::bar as Baz;`) or a brace-delimited list of typenames each with
its own optional alias (`use foo::bar::{Type1, Type2 as T2};`). This is the shape the demo
language's import construct is expected to resemble in spirit (repo/path/alias, single or
grouped) without being clockwork itself or reusing its `.fltkg` file — the requester's brief
asks for a distinct, non-real-language syntax with a different file extension, specifically so
VS Code's file-extension-based activation cannot be confused with a real extension for an
existing language.

## 3. Demo-language requirements as stated by the requester, mapped to existing pieces

The requester's brief: a demo FLTK language with multi-file imports, exercised by automated
tests and manually via VS Code; it must demonstrate **highlighting** (comments/trivia, strings,
types, statements, keywords, operators), **formatting**, and **go-to-def/find-refs**; a
different, non-real file extension; automated tests plus a manual VS Code acceptance pass.

Existing precedent inside `fltk/lsp/test_data/` is the `greet` fixture language
(`greet.fltkg`/`greet.fltkfmt`/`greet.fltklsp`, read above), used by `conftest.py`'s
`HELLO_GRAMMAR`/`HELLO_LSP` and by `test_server.py`'s `_SERVER_COMMAND` — but `greet` is
single-file only (`document := , item*`; no `use`/import rule at all) and its highlighting
coverage is thin: `greeting`/`note`/`definition`/`usage`/`module` items, a `name` regex, a
quoted `string`, `block_comment`/`line_comment` trivia, no operators, no distinct "type" vs
"variable" contextual pair beyond `scope name: type;` on one rule. It demonstrates the
`def`/`ref`/`namespace` machinery (`module` opens a namespace whose `name` is a `def`,
`definition` defines, `usage` references) but not cross-file resolution, and not formatting
richness beyond a few `after` spacing rules (`greet.fltkfmt`, 6 lines).

Every one of the requested demo-language features maps onto a milestone that already has
end-to-end machinery *within one file*: `.fltklsp` `scope` statements drive highlighting
(`lsp_config.py`, `classify.py`); `.fltkfmt` + `plumbing.generate_unparser`/`render_doc` drive
formatting (used by `server._ensure_format_pipeline`/`_format_blocking`, `server.py:488-558`);
`def`/`ref`/`namespace` drive same-file go-to-def/find-refs (`symbols.py`, `features.py`'s
`definition_location`/`reference_locations`, `server.py:671-692`). The only genuinely new
surface the demo requires is the cross-file half of go-to-def/find-refs — i.e., exactly the M5
resolver gap in §1.

## 4. VS Code wiring: current packaging and what's absent

### 4.1 Server launch surface today

`pyproject.toml`:
- `[project.scripts]` (`pyproject.toml:30-32`): `fltk-highlight = "fltk.lsp.highlight_cli:app"`,
  `fltk-lsp = "fltk.lsp.server_cli:app"`.
- `[project.optional-dependencies] lsp = ["pygls>=2,<3"]` (`pyproject.toml:27-28`) — core
  `dependencies = ["astor", "typer"]` (`pyproject.toml:25`) stay pygls-free.
- `fltk-lsp`'s CLI (`server_cli.py:34-67`) takes `--grammar`, `--lsp`, `--fmt`, `--rule`,
  `--width`, `--indent`, and lazily imports `fltk.lsp.server` so a missing `pygls` prints
  "fltk-lsp requires the 'lsp' extra: pip install 'fltk[lsp]'" instead of crashing
  (`server_cli.py:44-48`). It calls `server.start_io()` (`server_cli.py:67`) — stdio transport
  only; no TCP/socket option exists.

### 4.2 No VS Code extension scaffold exists

`find . -iname "*vscode*"` (excluding `.git`) returns nothing in the repo. There is no
`package.json`, no `client/` TypeScript LSP-client bootstrap, no `.vscode/launch.json`, no
`language-configuration.json`, no bundled `.vsix`. Everything needed to make VS Code spawn
`fltk-lsp` for a given file extension — an extension manifest declaring a `languages`
contribution (file extension → language id) and an activation event, plus a minimal
`vscode-languageclient` bootstrap that shells out to the `fltk-lsp` command — is greenfield.

### 4.3 Client-capability surface the server already reacts to

Because these are the capabilities a hand-built VS Code client (or its extension manifest) would
need to be able to negotiate correctly, not just present:

- Position encoding: `general.positionEncodings`; server picks `utf-32` if offered, else the
  mandatory `utf-16` (`server.py:65-90`, `_encoding`, `server.py:177-190`). VS Code's built-in
  `vscode-languageclient` defaults to advertising only `utf-16` (LSP-mandatory default) unless
  the extension explicitly requests `utf-32` — this is extension-manifest/client-code territory,
  not server territory.
- Hierarchical document symbols: `text_document.document_symbol.hierarchical_document_symbol_support`
  (`server.py:409-419`, `_hierarchical_symbols`) — toggles `document_symbols` vs
  `document_symbols_flat` (`server.py:658-669`).
- Versioned workspace edits: `workspace.workspace_edit.document_changes`
  (`server.py:421-423`, `_document_changes`) — toggles whether `rename` returns
  `documentChanges` (versioned) or plain `changes` (`server.py:466-484`, per step3/design.md §2.6).
- `RenameOptions(prepare_provider=True)` is registered (`server.py:711`), so a client is
  expected to call `textDocument/prepareRename` before `rename` — standard VS Code behavior,
  needs no special client code.

None of this requires anything beyond what `vscode-languageclient`'s standard
`LanguageClient` constructor already negotiates by default, **except** the utf-32 opt-in, which
is a documented but optional `positionEncodings` client capability override.

### 4.4 Formatting geometry is a server-launch flag, not client-negotiated

`server.py`'s `_format_blocking` builds `RendererConfig(max_width=width, indent_width=indent)`
from the CLI's `--width`/`--indent` (defaults 80/2, matching `fltk-unparse`, per
step2/design.md §2.7) and **ignores** the client's `FormattingOptions` (`tab_size` etc.) by
design. A VS Code launch config for the demo language would fix these via the server's command
-line args (in the extension's `serverOptions`), not via VS Code's own "Editor: Tab Size"
setting.

## 5. Test harness conventions for the LSP suite

### 5.1 Fixture-language layout

`fltk/lsp/test_data/` holds a `<name>.fltkg` / `<name>.fltkfmt` / `<name>.fltklsp` triple (only
`greet.*` exists today). `conftest.py` additionally defines two inline fixture grammars as
Python string constants (`HELLO_GRAMMAR`, `HELLO_LSP`, `conftest.py:20-29`) for tests that don't
need the on-disk file path plumbing, with `build_hello_engine(config_text, start_rule="top")`
(`conftest.py:32-40`) as the shared constructor and `token_for`/`token_type_at`
(`conftest.py:43-58`) as shared token-lookup helpers.

### 5.2 End-to-end protocol tests: `pytest-lsp` over a real subprocess

`test_server.py` is the only suite that drives the *actual* `fltk-lsp` binary rather than
calling `create_server` in-process: `_SERVER_COMMAND = [sys.executable, "-m",
"fltk.lsp.server_cli", "--grammar", ..., "--lsp", ..., "--fmt", ..., "--width", "80", "--indent",
"2"]` (`test_server.py:35-49`), spawned by `pytest_lsp.ClientServerConfig`/`LanguageClient`
(imported at `test_server.py:19-22`; `pytest-lsp` is in the `test` dependency group,
`pyproject.toml:46-50`, alongside `coverage[toml]` and `pytest`). Helpers
`_init_params`/`_open`/`_change`/`_tokens`/`_range_tokens`/`_decode`/`_line_col`
(`test_server.py:75-153`) build `InitializeParams` with capability toggles, drive
`didOpen`/`didChange`, and decode the delta-encoded semantic-token wire format for assertions.
This is the pattern an automated multi-file-import test (open file A, open file B, go-to-def in
A landing in B) would need to extend — today every `test_server.py` scenario is single-URI
(`_URI = "file:///doc.greet"`, one document open at a time); there is no existing test that opens
two URIs in the same server session and asserts a cross-document result.

### 5.3 In-process server construction (no subprocess)

Other than `test_server.py`, nothing else in the LSP suite spawns a subprocess:
`test_engine.py`, `test_engine_analyze.py`, `test_classify*.py`, `test_symbols.py`,
`test_lsp_resolve.py`, `test_features.py`, `test_positions.py`, etc. all call
`AnalysisEngine`/`load_lsp_config`/`classify.classify`/`symbols.extract` directly in-process.
`test_server_cli.py` (75 lines) tests only the CLI's fail-fast startup-validation paths
(missing/invalid `--grammar`/`--lsp`/`--fmt`, unknown `--rule`) via direct `typer` invocation,
not a live server.

### 5.4 Dogfood pattern

`test_dogfood.py` loads the real `fltklsp.fltkg`/`fltklsp.fltklsp` (the `.fltklsp` language's
own spec, `fltk/lsp/fltklsp.fltklsp`, read above — highlighting-only, no `def`/`ref`) and
asserts the shipped spec highlights a sample `.fltklsp` document, established as the
"self-hosting smoke test" pattern (step3/design.md's test plan explicitly keeps this file
`def`/`ref`-free and pushes any def/ref dogfooding into a test-local spec instead, `step3/design.md`
"Test plan" bullet on `test_dogfood.py`).

## 6. Build/codegen wiring for a new grammar

`Makefile`'s `gencode` target (`Makefile:253-278` and onward) is the precedent for how a new
`.fltkg` grammar gets committed generated CST/parser code: one `uv run python -m
fltk.fegen.genparser generate --protocol <grammar> <name> <python.module.path> --output-dir
<dir>` invocation per grammar, listed explicitly (fegen, bootstrap, toy, unparsefmt, regex,
fltklsp are the current six). A demo language's own grammar would either (a) be loaded
dynamically at runtime the way `AnalysisEngine`/`fltk-lsp`/`fltk-highlight` already load *any*
`.fltkg` (`plumbing.parse_grammar_file` + `plumbing.generate_parser`, no codegen step required
for LSP serving) or (b) additionally get a committed generated-code step if the demo also wants
to exercise the compiled-artifact path — nothing in the current LSP stack requires the latter;
`AnalysisEngine.from_paths` (`engine.py:109-125`) only needs a `.fltkg` file path plus an
optional `.fltklsp` path, both read and compiled in-memory at server startup
(`plumbing.generate_parser(prepare_analysis_grammar(grammar))`, `engine.py:101`, one-time cost
per server process).

## 7. Open factual questions

- Whether `vscode-languageclient`'s default `LanguageClient` bootstrap (minimal `client/`
  TypeScript + `package.json` `activationEvents`/`languages` contribution) is sufic ient on its
  own, or whether some VS Code-side syntax contribution (a `TextMate` grammar or
  `language-configuration.json` for bracket-matching/auto-closing) is also expected — the ADR's
  OQ3 (`fltklsp-spec.md` §6) floats a `.tmLanguage.json` exporter as a *possible* future round
  but nothing about it has been decided or built.
- Whether pygls's `LanguageServer` base class (from `pygls.lsp.server`) exposes ready-made
  workspace-folder/file-enumeration helpers that a resolver could reuse, versus needing to do
  its own filesystem walking — the installed `pygls` package lives at
  `.venv/lib64/python3.10/site-packages/pygls`, but no code in `fltk/lsp/` currently reads
  `workspace_folders`/`root_uri`, so there is no precedent in this codebase either way.
