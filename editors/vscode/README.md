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
uv --project <repo> run --extra lsp fltk-grammar-lsp {fltkg,fltkfmt,fltklsp} [--width N] [--indent N]
```

`--extra lsp` is load-bearing: `pygls` lives only in the `lsp` optional extra, and a plain
`uv run` syncs default groups only, so without it a clean checkout gets a `pygls`-less
environment and the server exits 1 before any protocol I/O.

## VS Code

### Prerequisites

- **Node / npm** — only to install the extension's one dependency
  (`vscode-languageclient`). No Python test needs Node.
- **The Rust toolchain** (`rustup` + `cargo`) — `fltk` is a mixed Python/Rust package, so
  `uv run` cannot build it without Rust. Install via <https://rustup.rs/>.
- The **first launch is slow**: it pays the one-time maturin debug build of the Rust
  extension. This is a visibly slow first start, not a hang; subsequent launches are fast.

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
extension computes the repo root from its own location and builds the
`uv … --extra lsp fltk-grammar-lsp <language>` command shown above. A separate server
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
"fltk.grammars.server.command": [
  "uv", "--project", "/path/to/fltk", "run", "--extra", "lsp", "fltk-grammar-lsp"
]
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

## Bazel (`@fltk//`) — experimental

fltk is often vendored as a Bazel submodule (`@fltk//…`). You can launch the server straight
from that submodule so a consumer workspace needs no separate fltk install:

```bash
bazel run @fltk//:grammar_lsp -- fltkg
```

Point the VS Code setting at it (the extension appends the language id):

```json
"fltk.grammars.server.command": ["bazel", "run", "@fltk//:grammar_lsp", "--"]
```

This is **experimental**. Two real caveats:

- **Lock contention.** Each `bazel run` grabs the workspace lock. VS Code session restore
  reopens all previously open editors at activation, so a workspace with a `.fltkg` and its
  sibling `.fltkfmt` / `.fltklsp` open starts multiple clients in the same tick; the extra
  Bazel clients queue on the lock. The symptom is slow or timed-out client startup, not
  corruption. LSP traffic is on stdout and Bazel's build chatter on stderr, so the protocol
  itself survives.
- **Cold-cache build.** A cold cache means a visible Bazel build before the server answers.

Whenever more than one fltk language is in use, prefer generating a launcher script once and
pointing the setting at it, which sidesteps the per-launch lock:

```bash
bazel run --script_path=/path/to/grammar_lsp.sh @fltk//:grammar_lsp
```

```json
"fltk.grammars.server.command": ["/path/to/grammar_lsp.sh"]
```

Bazel CI does not currently exercise any target, so `bazel build //:grammar_lsp` and
`bazel run @fltk//:grammar_lsp -- fltkg` are documented manual verification steps, the same
status as the existing `bootstrap_*` Bazel smoke targets.
