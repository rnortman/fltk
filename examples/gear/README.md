# gear — a demo language for `fltk-lsp`

`gear` is a small, deliberately unreal language used to demonstrate `fltk-lsp` end to end:
syntax highlighting, formatting, and cross-file go-to-definition / find-references over a
multi-file project with `use a::b::{X as Y};` imports. `.gear` is not a real-world file
extension, so VS Code activation can never be hijacked by an installed extension for a real
language.

The demo has two halves:

- **The language** (`gear.fltkg` + `gear.fltklsp` + `gear.fltkfmt`) and its **cross-file
  resolver** (`gear_resolver.py`) — the reference implementation of the `fltk-lsp` resolver
  plugin API. This half runs with nothing but the Python toolchain and is covered by the
  automated suite (`fltk/lsp/test_gear_demo.py`, `fltk/lsp/test_server_crossfile.py`).
- **The VS Code client** (`vscode/`) — a minimal extension that spawns `fltk-lsp` from this
  checkout so you can see the whole thing work in a real editor.

> The resolver plugin API is **provisional** — subject to change until validated against a
> real downstream language. See the notice at the top of `gear_resolver.py`.

## The server, from the command line

The resolver-enabled server is launched like this (the same argv the VS Code client builds
and the automated e2e tests drive):

```bash
uv --project <repo> run --extra lsp fltk-lsp \
  --grammar examples/gear/gear.fltkg \
  --lsp     examples/gear/gear.fltklsp \
  --fmt     examples/gear/gear.fltkfmt \
  --resolver examples/gear/gear_resolver.py:create_resolver
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
cd examples/gear/vscode
npm install
```

Then either:

- Open `examples/gear/vscode` in VS Code and press **F5** (launches an Extension Development
  Host), **or**
- `code --extensionDevelopmentPath=<repo>/examples/gear/vscode`

Both work against the in-repo defaults with zero configuration beyond `npm install`: the
extension computes the repo root from its own location and builds the `uv … --extra lsp
fltk-lsp …` command shown above. In the Development Host, open `examples/gear/sample/` as
the workspace folder and open `main.gear`.

### Packaged `.vsix` (optional)

```bash
cd examples/gear/vscode
npx @vscode/vsce package
```

Install the resulting `.vsix`. Because the packaged extension no longer lives in the repo,
the relative-root default is wrong — you **must** set `gear.server.command` (a string array,
the full argv) to point at your checkout, e.g.:

```json
"gear.server.command": [
  "uv", "--project", "/path/to/fltk", "run", "--extra", "lsp", "fltk-lsp",
  "--grammar", "/path/to/fltk/examples/gear/gear.fltkg",
  "--lsp", "/path/to/fltk/examples/gear/gear.fltklsp",
  "--fmt", "/path/to/fltk/examples/gear/gear.fltkfmt",
  "--resolver", "/path/to/fltk/examples/gear/gear_resolver.py:create_resolver"
]
```

## Acceptance checklist

Run through these in the Extension Development Host with `examples/gear/sample/` open as the
workspace folder:

1. **Setup**: `npm install` in `examples/gear/vscode`; F5 (or
   `--extensionDevelopmentPath`); open `examples/gear/sample/` as the workspace folder.
2. **Highlighting**: in `main.gear`, comments, strings, numbers, keywords
   (`shape` / `fn` / `let` / `return` / `use`), operators, types, and constants are all
   visibly distinct.
3. **Formatting**: mangle the whitespace in `main.gear`, then **Format Document** — it
   restores clean layout.
4. **Go-to-definition**: **F12** on an imported name (and on a local use of the `Box` alias)
   lands in `lib/shapes.gear`.
5. **Find-references**: **Shift+F12** on a shape definition in `lib/shapes.gear` lists
   locations in `main.gear` — including when `main.gear` was never opened this session.
6. **Live degradation**: introduce a syntax error → a diagnostic appears and highlighting
   stays fresh on the still-valid prefix; **rename** an exported shape → a refusal message
   (cross-file rename is not supported); rename a local `let` binding → succeeds.

The samples ship healthy (no deliberate errors or unresolved references); step 6 has you
introduce breakage live.
