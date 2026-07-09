# Implementation log: Dogfood LSP for fltk's own grammar DSLs

## Increment 1 — spec triples + `fltk-grammar-lsp` entry point + tests

Core dogfood slice (design §§1–2, test plan 1–7): all three fltk DSLs served by the generic LSP
through one friendly entry point, with the sidecar specs driving highlighting/def-ref/formatting,
pinned by tests. VS Code extension (§3) and Bazel stretch (§4) remain for later increments.

Shipped:

- `fltk/fegen/fegen.fltklsp` (new): highlighting + def/ref for `.fltkg`. `rule rule { def name:
  type; }` (rule defs → outline/go-to-def/rename), `rule term { ref rule:identifier: type; }`
  (every rule-invocation term is a navigable reference), scopes for literals (`string`), regex
  bodies (`macro`), item labels (`label`), and global literal scopes for operators/punctuation.
- `fltk/unparse/unparsefmt.fltklsp` (new): `.fltkfmt` highlighting. `rule rule_config { def
  rule_name: type; }` for the outline; explicit `string`/`number` scopes for literal/integer
  values. Keywords/spacing words fall out of the default classifier (word-shaped literals → keyword).
- `fltk/unparse/unparsefmt.fltkfmt`, `fltk/lsp/fltklsp.fltkfmt` (new): formatting for `.fltkfmt`
  and `.fltklsp`, modeled on the proven `gear.fltkfmt` structure (nbsp spacing, statement-per-line,
  `rule { ... }` bodies nest/break). Both verified reparse-clean and idempotent on all in-tree files.
- `fltk/lsp/fltklsp.fltklsp:9-13`: replaced `scope rule_name: type;` with `def rule_name: type;`
  in the `rule_config` block (the `def` still paints `type` at the declaration site and adds the
  outline symbol / find-refs).
- `fltk/lsp/grammar_cli.py` (new): `BuiltinLanguage` dataclass + `BUILTIN_LANGUAGES` registry,
  `Language` str-enum (Typer positional argument), `resolve_paths(language, ExitStack)`
  (`importlib.resources.files`/`as_file`), Typer `main` taking the language id + `--width`/
  `--indent`, `if __name__ == "__main__"` guard for `python -m` and the Bazel `py_binary`.
- `fltk/lsp/server_cli.py:35-73`: extracted shared `serve(grammar, lsp, fmt, rule, width, indent,
  resolver_spec)`; `main()` now delegates to it. `fltk-lsp` behavior unchanged.
- `pyproject.toml:33`: added `fltk-grammar-lsp = "fltk.lsp.grammar_cli:app"` console script.
- `fltk/lsp/test_grammar_lsp.py` (new): registry integrity (parametrized), per-language highlight
  smoke, `.fltkg` def/ref resolution, formatting round-trip (reparse + idempotent) over real files,
  CLI unknown-language/`--help`/`resolve_paths`, and one pytest-lsp end-to-end session (`python -m
  fltk.lsp.grammar_cli fltkg`) checking tokens + a diagnostic. `fltk/lsp/test_dogfood.py`: added a
  committed-spec test for the new `def rule_name: type;`.
- Deviation: the `label` item anchor in `fegen.fltklsp` is written `label:label` (qualifier form),
  not the bare `label` the design sketched — an unqualified `label` anchor parses as the `label:`
  qualifier keyword in the `.fltklsp` grammar. Same semantics (the item child captured under label
  `label`); noted at `fegen.fltklsp:38-41`.
- Deviation: `unparsefmt.fltklsp` keyword/spacing highlighting relies on the default classifier
  rather than explicit `scope` statements (word-shaped literals already default to `keyword`), so the
  spec only declares the non-default paints; matches design intent (exact token choices are
  implementation detail).
- All 29 tests pass (`test_grammar_lsp`, `test_dogfood`, `test_server_cli`); ruff + pyright clean on
  changed modules.

## Increment 2 — VS Code extension + Bazel submodule launch

Editor + build-system integration for the grammar LSP (design §§3–4, test plan 8–9). Completes the
remaining design items. The resolver cross-file navigation (open question 1) and marketplace
distribution (open question 2) stay deferred per the task; no TODO slug filed since both remain
unconfirmed open questions rather than settled design.

Shipped:

- `editors/vscode/package.json` (new): single `fltk-grammars` extension registering languages
  `fltkg`/`fltkfmt`/`fltklsp` with their `.fltkg`/`.fltkfmt`/`.fltklsp` extensions,
  `activationEvents` per language, the gear `semanticTokenScopes` fallback mapping
  (`constant`/`punctuation`/`label`), `untrustedWorkspaces.supported: false`, and the
  machine-scoped `fltk.grammars.server.command` argv-prefix setting.
- `editors/vscode/language-configuration-{fltkg,fltkfmt,fltklsp}.json` (new): `//` line comments
  everywhere; `/* */` block comments for `fltkg` only (only `fegen.fltkg` has block-comment
  trivia); brackets + auto-close/surrounding pairs.
- `editors/vscode/extension.js` (new): `LANGUAGES` list + `clients` map; one `LanguageClient` per
  language id, started lazily via `maybeStart` on `activate` (scan `workspace.textDocuments`) and
  `onDidOpenTextDocument`. `commandPrefix()` returns the setting override or the in-repo default
  `["uv","--project",<repoRoot>,"run","--extra","lsp","fltk-grammar-lsp"]` (repo root =
  `path.resolve(__dirname, "..", "..")`); the language id is appended as the final arg. No
  `transport` field (pygls stdio), matching gear.
- `editors/vscode/README.md` (new): CLI usage, prerequisites, Extension-Development-Host + `.vsix`
  instructions, per-language manual acceptance checklist (test plan 8), and the experimental Bazel
  `@fltk//` section with lock-contention/cold-build caveats and the `--script_path` recommendation.
- `editors/vscode/.gitignore` (new): `node_modules/`, `*.vsix`, `package-lock.json` (gear parity).
- `BUILD.bazel`: `args = ["--extra", "lsp"]` on the `lock` target; spec sidecars
  (`fltk/**/*.fltkg`, `*.fltklsp`, `*.fltkfmt`) added to `py_library(":fltk")` `data`; new
  `py_binary(name = "grammar_lsp", srcs/main = fltk/lsp/grammar_cli.py, deps = :fltk + astor +
  pygls + typer)`.
- `requirements_lock.txt`: regenerated via the canonical `uv export --format requirements-txt
  --no-editable --extra lsp --output-file requirements_lock.txt`; adds pygls 2.1.1 + transitive
  deps (lsprotocol, cattrs, attrs) to the Bazel pip graph; provenance header updated to match.
- Test plan 8–9 are documented manual verification (VS Code acceptance checklist, Bazel smoke); no
  new automated tests — CI exercises neither VS Code nor Bazel. `node --check` on `extension.js`
  and `JSON.parse` on all four JSON files pass.
