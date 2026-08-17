# fltk grammars — VS Code client

A single VS Code extension that gives fltk's own three DSLs — `.fltkg` grammars, `.fltkfmt`
format specs, and `.fltklsp` editor specs — syntax highlighting, formatting, document
outline, and (for `.fltkg`) go-to-definition / find-references. It does this by spawning
`fltk-grammar-lsp`, the friendly one-argument entry point that resolves each language's
packaged grammar and sidecar specs for you.

There is nothing fltk-repo-specific about the servers: the `.fltkg` server highlights and
formats *any* grammar file, so every project that edits its own `lang.fltkg` /
`lang.fltkfmt` / `lang.fltklsp` gets the same tooling.

Unlike the gear demo (`examples/gear/vscode/`), this extension uses no resolver plugin —
navigation is same-file only — so it wires no `--resolver` argument.

## The server, from the command line

```bash
bazel run //:grammar_lsp -- {fltkg,fltkfmt,fltklsp} [--width N] [--indent N]
```

That builds the server and runs it in one step; `pygls` and every other dependency comes from
the Bazel-managed pip hub, so there is nothing to install first.

For editor use, prefer the checked-in launcher `editors/vscode/run-grammar-lsp`, which builds
the target and then execs the built server. A server started directly by `bazel run` holds the
Bazel workspace lock for its whole lifetime and blocks every other Bazel command in the
checkout — including the next language client this extension starts.

## VS Code

### Prerequisites

- **Node / npm** — only to install the extension's one dependency
  (`vscode-languageclient`). No Python test needs Node.
- **Bazel** (via `bazelisk`, honoring `.bazelversion`) — it builds and launches the server.
- No Rust toolchain of your own — `fltk` is a mixed Python/Rust package, and Bazel fetches
  the hermetic Rust toolchain it compiles with.
- The **first launch is slow**: it pays a one-time Bazel build of the Rust extension and the
  generated parsers. This is a visibly slow first start, not a hang; later launches hit the
  Bazel cache and are fast.

### Run it (Extension Development Host)

```bash
cd editors/vscode
npm install
```

Then either:

- Open `editors/vscode` in VS Code and press **F5** (launches an Extension Development
  Host), **or**
- `code --extensionDevelopmentPath=<repo>/editors/vscode`

Both work against the in-repo defaults with zero configuration beyond `npm install`: the
extension computes the repo root from its own location and launches
`editors/vscode/run-grammar-lsp <language>`. A separate server
process is started lazily per language — the first time a `.fltkg`, `.fltkfmt`, or
`.fltklsp` document is opened this session — so opening only `.fltkg` files spawns only the
`fltkg` server. Open `fltk/fegen/fegen.fltkg` (or any grammar) to see it work.

### Packaged `.vsix` (optional)

```bash
cd editors/vscode
npx @vscode/vsce package
```

Install the resulting `.vsix`. Because the packaged extension no longer lives in the repo,
the relative-root default is wrong — you **must** set `fltk.grammars.server.command` (a
string array, the argv prefix; the extension appends the language id) to point at your
checkout, e.g.:

```json
"fltk.grammars.server.command": ["/path/to/fltk/editors/vscode/run-grammar-lsp"]
```

`--width` / `--indent` can be appended to that prefix to tune formatting (the shipped
default width is 80, matching `fltk-lsp`).

## Acceptance checklist

Run through these in the Extension Development Host with the fltk repo open as the workspace
folder. Because a client starts per language, do each language's steps with a file of that
language open.

1. **Setup**: `npm install` in `editors/vscode`; F5 (or `--extensionDevelopmentPath`); open
   the fltk repo as the workspace folder.
2. **`.fltkg` highlighting**: open `fltk/fegen/fegen.fltkg` — comments, rule-name
   definitions, string literals, regex bodies, item labels, and operators/punctuation are
   visibly distinct.
3. **`.fltkg` formatting**: mangle the whitespace in a `.fltkg` file, then **Format
   Document** — it restores clean layout.
4. **`.fltkg` go-to-definition / find-references**: **F12** on a rule name used in a term
   lands on that rule's definition; **Shift+F12** on a rule definition lists its uses.
5. **`.fltkfmt` highlighting + outline**: open `fltk/fegen/fegen.fltkfmt` — keywords,
   spacing words, string/number literals are distinct; the Outline view lists `rule` blocks.
6. **`.fltklsp` highlighting + outline**: open `fltk/lsp/fltklsp.fltklsp` — the Outline view
   lists `rule` blocks; **Format Document** works.
7. **Live degradation**: introduce a syntax error → a diagnostic appears and highlighting
   stays fresh on the still-valid prefix.

## From a consumer workspace (`@fltk//`)

fltk is often vendored as a Bazel submodule (`@fltk//…`). The server target is public, so a
consumer workspace launches it without any separate fltk install:

```bash
bazel run @fltk//:grammar_lsp -- fltkg
```

Point the VS Code setting at a launcher generated once from that target (the extension appends
the language id):

```bash
bazel run --script_path=/path/to/grammar_lsp.sh @fltk//:grammar_lsp
```

```json
"fltk.grammars.server.command": ["/path/to/grammar_lsp.sh"]
```

Do **not** point the setting at `bazel run` itself. Each `bazel run` grabs the workspace lock
and holds it for the server's lifetime, and VS Code session restore starts one client per open
fltk language in the same tick, so the extra clients queue on the lock — slow or timed-out
startup. That is exactly why the in-repo default is `run-grammar-lsp` rather than a `bazel run`
argv. A cold Bazel cache also means a visible build before the first response.

`bazel build //:grammar_lsp` is covered by `bazel build //...`; the end-to-end launch
(`bazel run @fltk//:grammar_lsp -- fltkg`) remains a manual verification step.
