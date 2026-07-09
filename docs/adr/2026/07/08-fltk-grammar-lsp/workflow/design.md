# Design: Dogfood LSP for fltk's own grammar DSLs

Requirements: the verbatim user request (see task). Exploration: `exploration.md` alongside this file.

## Context and motivation

The M0–M5 work (`a17ba80`..`2e40bfa`) produced a generic, grammar-agnostic LSP server
(`fltk-lsp`, `fltk/lsp/server_cli.py`) plus the gear demo proving it end to end in VS Code
(`examples/gear/`). fltk itself has three DSLs, each with a grammar in-tree:

| Language | Grammar | `.fltklsp` today | `.fltkfmt` today |
|---|---|---|---|
| `.fltkg` (grammars) | `fltk/fegen/fegen.fltkg` | none | `fltk/fegen/fegen.fltkfmt` |
| `.fltkfmt` (format specs) | `fltk/unparse/unparsefmt.fltkg` | none | none |
| `.fltklsp` (editor specs) | `fltk/lsp/fltklsp.fltkg` | `fltk/lsp/fltklsp.fltklsp` (scope-only) | none |

No triple is complete, and none is reachable without a four-flag `fltk-lsp` invocation whose
paths point inside the installed package. The request: complete the triples, expose one
friendly entry point, integrate with VS Code, and (stretch) make the server launchable from a
Bazel `@fltk//` submodule.

Note there is nothing fltk-repo-specific about these servers: the `.fltkg` server serves *any*
grammar file, including downstream consumers' grammars. This is the real payoff — every
`@fltk//` consumer editing their own `lang.fltkg`/`lang.fltkfmt`/`lang.fltklsp` gets
highlighting, diagnostics, and formatting for free.

## Proposed approach

Four pieces, each independently landable in this order.

### 1. Complete the spec triples (new sidecar files)

All files live next to their grammars, inside the `fltk` package, so they ship in the wheel
and resolve via `importlib.resources` (see Packaging below).

**New: `fltk/fegen/fegen.fltklsp`** — highlighting *and* def/ref for the `.fltkg` language.
This is the flagship dogfood: `fegen.fltkg` has exactly the def/ref shape the M4 machinery
wants:

- `rule := name:identifier , ":=" ...` (`fegen.fltkg:3`) → `rule rule { def name: type; }`
  gives document symbols, go-to-definition targets, and same-file rename for grammar rules.
- `term := identifier | literal | ...` (`fegen.fltkg:12-13`) → `rule term { ref
  rule:identifier: type; }` (the `rule:` anchor qualifier addresses the unlabeled
  `identifier` child by referenced-rule-name, per `fltklsp.fltkg:15-16`) makes every rule
  reference navigable: F12 from a use to its definition, Shift+F12 on a definition.
- Kind choice: def/ref kinds are open vocabulary, but declaration-site and resolved-reference
  paints are emitted only when the kind's first segment is in the token legend
  (`lsp_config.py:691-694`, `classify.py:287-292`) — a kind like `rule` would leave rule
  names and references at the default `variable` paint. `type` is in the legend and matches
  both in-tree precedents (`fltklsp.fltklsp:11` `scope rule_name: type;`,
  `test_dogfood.py:27` `def rule_name: type;`), so all def/ref kinds in these specs use
  `type`.
- Scope statements for the rest: literals → `string`, `raw_string.value` (regex bodies) →
  a distinct paint from the fixed legend (`features.SEMANTIC_TOKEN_TYPES` has no `regexp`
  type, so e.g. `macro`), item labels (`item`'s `label:identifier`, `fegen.fltkg:11`) → `label`,
  operator/punctuation literals (`":="`, `";"`, `"|"`, separators, dispositions,
  quantifiers). Exact anchor and token-type choices are implementation detail validated by
  `load_lsp_config`'s fail-fast anchor checking and pinned by tests.

**New: `fltk/unparse/unparsefmt.fltklsp`** — highlighting for the `.fltkfmt` language.
Keywords (`rule`, `group`, `nest`, `join`, `after`, `before`, `from`, `to`, `omit`,
`render`, `as`, `trivia_preserve`, `preserve_blanks`, `ws_allowed`, `ws_required`), spacing
words (`nil`/`nbsp`/`bsp`/`soft`/`hard`/`blank`), `rule_config.rule_name` → `type`,
literals → `string`, integers → `number`. Plus `rule rule_config { def rule_name: type; }`
for outline/document-symbols. No in-file refs: `.fltkfmt` anchors refer to labels/literals
of the *target* grammar, which is a different file in a different language (see Open
questions).

**New: `fltk/unparse/unparsefmt.fltkfmt`** and **`fltk/lsp/fltklsp.fltkfmt`** — formatting
for `.fltkfmt` and `.fltklsp` files. Both languages share `fegen`-family conventions, so
both specs follow the shape of `examples/gear/gear.fltkfmt` and `fltk/fegen/fegen.fltkfmt`:
`trivia_preserve: LineComment;`, `preserve_blanks: 1;`, statements end with `after ";" {
hard; }`, `rule ... { ... }` blocks break and indent via `nest from after "{" to before
"}"`. (New files follow the existing `trivia_preserve` node-class-name convention
(`LineComment`); the D2 canonicalization cleanup in the prior ADR is out of scope here.)

**Extend: `fltk/lsp/fltklsp.fltklsp`** — add `def rule_name: type;` inside the existing
`rule rule_config` block so `.fltklsp` files get document symbols and find-references on
rule-block names. Anchor identifiers are *not* made refs: they name rules/labels of the
target grammar (cross-file), and resolving them to same-file `rule_config` blocks — as
`test_dogfood.py`'s test-local `_SEMANTIC_SPEC` does for test purposes — would be
semantically wrong as a shipped spec (mostly-dangling refs, misleading rename).
`test_dogfood.py` keeps its `_SEMANTIC_SPEC` tests but its committed-spec tests extend to
cover the new `def`.

### 2. One friendly entry point: `fltk-grammar-lsp`

**New console script** in `pyproject.toml` `[project.scripts]`:
`fltk-grammar-lsp = "fltk.lsp.grammar_cli:app"`.

Why a new script rather than extending `fltk-lsp`: `server_cli.app` is a single-command
Typer app, so `fltk-lsp --grammar ...` works with no subcommand. Adding a second command
would force `fltk-lsp main --grammar ...` — a breaking CLI change for existing consumers.
The generic CLI and the built-in-language CLI stay separate scripts sharing one
implementation.

**New module `fltk/lsp/grammar_cli.py`**:

```python
@dataclasses.dataclass(frozen=True)
class BuiltinLanguage:
    package: str        # importlib.resources anchor, e.g. "fltk.fegen"
    grammar: str        # "fegen.fltkg"
    lsp: str | None     # "fegen.fltklsp"
    fmt: str | None     # "fegen.fltkfmt"

BUILTIN_LANGUAGES: dict[str, BuiltinLanguage] = {
    "fltkg":   BuiltinLanguage("fltk.fegen",   "fegen.fltkg",      "fegen.fltklsp",      "fegen.fltkfmt"),
    "fltkfmt": BuiltinLanguage("fltk.unparse", "unparsefmt.fltkg", "unparsefmt.fltklsp", "unparsefmt.fltkfmt"),
    "fltklsp": BuiltinLanguage("fltk.lsp",     "fltklsp.fltkg",    "fltklsp.fltklsp",    "fltklsp.fltkfmt"),
}
```

CLI shape: `fltk-grammar-lsp LANGUAGE [--width N] [--indent N]` where `LANGUAGE` is one of
the three keys (Typer positional enum argument; an unknown value exits non-zero listing the
valid ids, which Typer gives for free). No `--grammar/--lsp/--fmt/--rule/--resolver`: the
registry supplies paths; each grammar's first rule (`grammar`, `formatter`, `lsp_spec`) is
already the correct start rule, matching `AnalysisEngine.from_paths`'s default.

Resource paths are materialized with `importlib.resources.files(pkg) / name` +
`importlib.resources.as_file(...)` (held open for the server's lifetime via an
`ExitStack`), so the same code works for editable installs, wheels, and Bazel runfiles.

`grammar_cli.py` ends with the same `if __name__ == "__main__": app()` guard as
`server_cli.py:79-80` — required both by the `python -m fltk.lsp.grammar_cli` invocation
the e2e test uses (test plan item 6) and by the Bazel `py_binary` (stretch section).

**Refactor `fltk/lsp/server_cli.py`**: extract the body of `main()` (lines 49–76 — the lazy
pygls import with its actionable install hint, engine/config/resolver construction, the
`ValueError`/`OSError` fail-fast handling, and `server.start_io()`) into a shared helper
`serve(grammar, lsp, fmt, rule, width, indent, resolver_spec)` that both `server_cli.main`
and `grammar_cli.main` call. Behavior of `fltk-lsp` is unchanged.

### 3. VS Code extension: `editors/vscode/`

A single extension (`name: "fltk-grammars"`) covering all three languages, closely modeled
on `examples/gear/vscode/` (which stays as-is — it demos the *resolver*, which this
extension does not use):

- `package.json`: `contributes.languages` registers ids `fltkg`, `fltkfmt`, `fltklsp` with
  their extensions; `activationEvents: ["onLanguage:fltkg", "onLanguage:fltkfmt",
  "onLanguage:fltklsp"]`; the same `semanticTokenScopes` fallback mapping as gear
  (`constant`, `punctuation`, `label`); `untrustedWorkspaces.supported: false`.
- Per-language `language-configuration.json`: `//` line comments everywhere; `/* */` block
  comments for `fltkg` only (only `fegen.fltkg` has `block_comment` trivia); brackets and
  auto-close pairs per language.
- `extension.js`: one `LanguageClient` per language id, started **lazily** — at activation,
  scan `workspace.textDocuments` and subscribe to `onDidOpenTextDocument`; start the client
  for a language the first time a document of that language appears. This avoids spawning
  three server processes when the user only ever opens `.fltkg` files.
- Server command: a machine-scoped array setting `fltk.grammars.server.command` holding the
  **argv prefix**; the extension appends the language id as the final positional argument.
  Default (empty setting) is the in-repo command computed from the extension's own location
  (`path.resolve(__dirname, "..", "..")` → repo root):
  `["uv", "--project", <root>, "run", "--extra", "lsp", "fltk-grammar-lsp"]`.
  Machine scope for the same reason as gear (`examples/gear/vscode/package.json:44-45`): a
  cloned repo's workspace settings must not be able to redirect the launched executable.
  Same no-`transport`-field stdio wiring as gear (`extension.js:51-55` — pygls rejects
  `--stdio`).
- `README.md`: prerequisites (Node, Rust toolchain, slow first launch — same as gear's),
  Extension-Development-Host and `.vsix` instructions, a manual acceptance checklist per
  language, and the Bazel section below.

### 4. Stretch: launch from a Bazel `@fltk//` submodule

Three small changes make `bazel run @fltk//:grammar_lsp -- <language>` work from any
consumer workspace (e.g. clockwork's `local_path_override` setup):

1. **Get pygls into the Bazel pip graph.** Two regeneration paths for
   `requirements_lock.txt` exist today and must be kept from diverging. The committed file's
   own header records its provenance: `uv export --format requirements-txt --no-editable
   --output-file requirements_lock.txt` (`requirements_lock.txt:1-2`). That command is
   **canonical**: regenerate the committed file with `uv export --format requirements-txt
   --no-editable --extra lsp --output-file requirements_lock.txt`, preserving the existing
   format and provenance. The Bazel `lock` target (`BUILD.bazel:7-11`) is a *different*
   tool — the rules_python 1.5.0 `lock` rule runs `uv pip compile` and appends its `args`
   attr verbatim (verified in `rules_python/python/uv/private/lock.bzl`,
   `args.add_all(ctx.attr.args)`), with a different output format. So that anyone who does
   run `bazel run //:requirements` doesn't silently drop pygls, also add
   `args = ["--extra", "lsp"]` to the `lock` target — but its output is not what gets
   committed; the `uv export` command above is. This grows the `@pypi` hub by pygls +
   transitive deps (lsprotocol, cattrs, attrs); under bzlmod these repos are fetched
   lazily, so consumers that never reference them pay nothing.
2. **Ship the spec files as Bazel data.** `py_library(":fltk")` globs only `**/*.py` plus
   `fltk/py.typed` (`BUILD.bazel:24-30`); add
   `glob(["fltk/**/*.fltkg", "fltk/**/*.fltklsp", "fltk/**/*.fltkfmt"])` to its `data` so
   `importlib.resources` finds them in runfiles.
3. **New `py_binary`**: `py_binary(name = "grammar_lsp", srcs =
   ["fltk/lsp/grammar_cli.py"], main = "fltk/lsp/grammar_cli.py", visibility = public,
   deps = [":fltk", "@pypi//astor", "@pypi//typer", "@pypi//pygls"])` — same shape as
   `:genparser` (`BUILD.bazel:13-22`), which also proves the LSP's pure-Python path needs
   no `:native_py`.

VS Code integration is then a documented setting, not code:
`"fltk.grammars.server.command": ["bazel", "run", "@fltk//:grammar_lsp", "--"]` (the
extension appends the language id). The README documents this as **experimental** with its
real caveats: LSP traffic is on stdout and Bazel's build chatter on stderr, so the protocol
survives, but (a) concurrent `bazel run`s contend for the workspace lock — and this is the
*expected* case, not a corner: VS Code session restore reopens all previously open editors
at activation, so a workspace with a `.fltkg` and its sibling `.fltkfmt`/`.fltklsp` open
starts multiple clients in the same tick; Bazel's client queues on the lock, so the symptom
is slow or timed-out client startups, not corruption — and (b) a cold cache means a visible
build before the server answers. The README therefore presents the `bazel run --script_path`
pattern (generate a launcher script once, point the setting at it) as the primary
recommendation whenever more than one fltk language is in use, not as an escape hatch.

## Packaging

The three grammars and six sidecar specs (four new in section 1 + two existing) live under
`fltk/`'s package tree, and
`[tool.maturin] python-packages = ["fltk"]` copies the package directory into the wheel, so
they ship without config changes. Verified during design by building a wheel with
`maturin build`: `fegen.fltkg`, `fegen.fltkfmt`, `fltklsp.fltkg`, `fltklsp.fltklsp`, and
`unparsefmt.fltkg` are all present — the five data files that exist today; the four new
sidecars land in the same globbed tree, and test plan item 1 guards that every registry
entry loads (note `maturin develop`'s editable wheel contains only a `.pth` file — only a
real `maturin build` wheel demonstrates this). `pygls` stays an
optional extra; `fltk-grammar-lsp` without it prints the same actionable hint as `fltk-lsp`
(shared `serve` helper).

## Edge cases / failure modes

- **Missing pygls**: identical fail-fast behavior to `fltk-lsp` (`server_cli.py:50-53`) via
  the shared helper — message names the `lsp` extra, exit 1 before protocol I/O.
- **Broken shipped specs**: `load_lsp_config` / `parse_format_config_file` validate at
  startup, but a shipped-broken spec would be a release bug — the test plan loads every
  registry entry in CI so this cannot regress silently.
- **Any-user's-files semantics**: the `fltkg` server serves *all* `.fltkg` files, including
  downstream grammars. Anchors in a user's `.fltkfmt`/`.fltklsp` that don't exist in *their*
  grammar are not diagnosable by these servers (they only see the sidecar file's own
  syntax); that cross-file validation is resolver territory (Open questions).
- **Formatting at default width**: `--width` defaults to 80 (`server_cli.py:41`); the repo's
  own line convention is 120. `--width`/`--indent` pass through `fltk-grammar-lsp`, and the
  VS Code setting overrides the full argv prefix, so users can tune it; the shipped default
  stays 80 for consistency with `fltk-lsp`.
- **Parse errors while editing**: already handled by the engine — M3 prefix highlighting,
  stale-token serving, `ErrorTracker` diagnostics. Nothing new needed.
- **Three servers, one editor**: lazy client start keeps process count equal to the number
  of distinct fltk languages actually open.
- **Bazel lock contention / cold-build latency**: documented, experimental path; lock
  contention is expected whenever more than one fltk language is open, with `--script_path`
  as the primary recommendation (see stretch section).
- **`rule` as both keyword and rule name**: `fegen.fltklsp` addresses a grammar rule
  literally named `rule` (`rule rule { ... }`); this parses fine (`rule_name:identifier`
  accepts it, proven by the analogous `rule rule` block already in
  `fltk/fegen/fegen.fltkfmt:17`).

## Test plan

After implementation the following exist (new `fltk/lsp/test_grammar_lsp.py` unless noted):

1. **Registry integrity** — for each `BUILTIN_LANGUAGES` entry: all named resources exist,
   `AnalysisEngine.from_paths(grammar, lsp)` succeeds, and
   `plumbing.parse_format_config_file(fmt)` succeeds. This is the CI guard that shipped
   specs load.
2. **Highlight smoke per language** — a small sample of each language asserting key token
   types via the existing `token_type_at` conftest helper (pattern:
   `test_dogfood.py:49-70`): e.g. for `.fltkg`, a rule-name def paint (`type` with the
   `declaration` modifier), a literal → `string`,
   a label → `label`; analogous assertions for `.fltkfmt` keywords/spacings and the extended
   `.fltklsp` spec.
3. **fegen def/ref semantics** — analyze a sample grammar; assert a rule definition symbol
   exists and an identifier-term reference resolves to it (pattern:
   `test_dogfood.py:109-124`), covering go-to-def/find-refs for `.fltkg`.
4. **Formatting round-trip on real files** — for each language, format its own committed
   in-tree files (e.g. `fegen.fltkg` via `fegen.fltkfmt`; the new specs via theirs): output
   reparses under the same grammar and formatting is idempotent (format∘format =
   format). Does not require committed files to already be format-clean.
5. **CLI behavior** — `fltk-grammar-lsp` with an unknown language exits non-zero and names
   the valid ids; `--help` works; the path-resolution helper returns existing paths for all
   three languages without starting I/O (factor `grammar_cli` so resolution is testable
   separately from `serve`).
6. **One end-to-end LSP session** — a pytest-lsp test (same harness as the existing server
   e2e tests, e.g. `test_server_crossfile.py`) spawning
   `[sys.executable, "-m", "fltk.lsp.grammar_cli", "fltkg"]` — the same `python -m` pattern
   the cited harness uses (`test_server_crossfile.py:62-66`), which works regardless of
   whether the venv's console script has been refreshed by a `maturin develop` re-run —
   initializing, and fetching semantic tokens + a diagnostic for a sample grammar. One
   language suffices; the per-language differences are covered by 1–4. (The console-script
   name itself is covered by item 5's CLI tests via the Typer app object.)
7. **`test_dogfood.py` update** — committed-spec tests extended for the new
   `def rule_name: type;`; `_SEMANTIC_SPEC` tests unchanged.
8. **VS Code** — manual acceptance checklist in `editors/vscode/README.md` (gear precedent,
   `examples/gear/README.md:88-109`): highlighting, Format Document, F12/Shift+F12 on rule
   names in a `.fltkg`, live degradation. Not automated (same stance as gear).
9. **Bazel** — CI does not currently exercise any Bazel target (`.github/workflows/ci.yml`
   has a single uv/Rust check job), so `bazel build //:grammar_lsp` and the
   `bazel run @fltk//:grammar_lsp -- fltkg` smoke are documented manual verification steps —
   the same status as the existing `bootstrap_*` Bazel smoke targets.

## Open questions

1. **Cross-file navigation from sidecars into the grammar** — F12 from a `rule foo {` block
   in a `.fltkfmt`/`.fltklsp` (or from an anchor) to the rule definition in the sibling
   `.fltkg` would be the first real-world validation of the provisional resolver API — which
   its own docstring says it needs. But the current resolver contract is same-language
   (`ResolverHost.document()` analyzes with the host server's single engine), so this needs
   a cross-language API extension. Proposed: **out of scope here**; land this design's
   declarative-only servers, file a TODO slug for the resolver extension. Confirm.
2. **VS Code distribution** — in-repo Extension-Development-Host + manual `.vsix` (the gear
   stance), or should CI package/publish the extension? Proposed default: in-repo only for
   now; publication is a separate decision with marketplace-account implications.
