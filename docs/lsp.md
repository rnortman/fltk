# Grammar LSP: editor support for fltk's DSLs

fltk ships three small domain-specific languages that work together to define parsers and their tooling:

- `.fltkg` files define grammars (the parsing rules for a language).
- `.fltkfmt` files define formatting specs (how to pretty-print code parsed by a grammar).
- `.fltklsp` files define editor specs (highlighting, go-to-definition, and other editor features for code parsed by a grammar).

The grammar LSP gives you syntax highlighting, document formatting, document outline, diagnostics, and (for `.fltkg`) go-to-definition and find-references in any editor that speaks the Language Server Protocol. It serves all three of fltk's own DSLs, and because the servers are grammar-generic, they also serve your own `.fltkg`/`.fltkfmt`/`.fltklsp` files if you are writing a grammar on top of fltk.

## Running the server

```bash
fltk-grammar-lsp {fltkg,fltkfmt,fltklsp}
```

The single positional argument is the language to serve. That is the only required argument. The server resolves its grammar and sidecar spec files from the installed fltk package automatically; there are no `--grammar`, `--lsp`, or `--fmt` flags to set.

Two optional flags tune document formatting:

- `--width N` (default 80) -- line width target.
- `--indent N` (default 2) -- indentation width.

The server speaks LSP over stdio. Editors start it as a subprocess and communicate over its stdin/stdout.

### Prerequisites

`pygls` must be installed. It lives in the `lsp` optional extra, not in fltk's base dependencies. If it is missing, the server prints an actionable message (`pip install 'fltk[lsp]'`) and exits.

When running from a source checkout with `uv`, pass `--extra lsp` so `uv` syncs the extra:

```bash
uv --project /path/to/fltk run --extra lsp fltk-grammar-lsp fltkg
```

`--extra lsp` is load-bearing: without it, a clean checkout has no `pygls` and the server exits before doing anything.

fltk is a mixed Python/Rust package, so a Rust toolchain (`rustup` + `cargo`, from <https://rustup.rs/>) must also be available for the build step. The first launch from a clean checkout is slow because it pays for a one-time debug build of the Rust extension; subsequent launches are fast.

## What each language gets

All three languages get highlighting, formatting, diagnostics, and document outline (the Outline panel in VS Code).

`.fltkg` files additionally get go-to-definition and find-references for grammar rule names: F12 on a rule name used inside another rule jumps to that rule's definition; Shift+F12 on a rule's definition lists every place it is referenced.

`.fltkfmt` and `.fltklsp` do not have cross-reference navigation. Their rule-block names refer to rules in a sibling `.fltkg` file (a different language in a different file), and cross-file/cross-language navigation is not yet implemented.

## VS Code

A VS Code extension lives at `editors/vscode/` in the fltk repository. It registers all three languages and starts one `fltk-grammar-lsp` server process per language, lazily -- only when you first open a file of that language.

### Setup (Extension Development Host)

```bash
cd editors/vscode
npm install
```

Then either press F5 from the `editors/vscode` folder in VS Code (this launches an Extension Development Host window), or run:

```bash
code --extensionDevelopmentPath=/path/to/fltk/editors/vscode
```

No configuration is needed beyond `npm install`. The extension computes the fltk repo root from its own file location and builds the `uv ... --extra lsp fltk-grammar-lsp <language>` command automatically.

Open any `.fltkg` file (for example, `fltk/fegen/fegen.fltkg`) to see it working.

### Setup (packaged `.vsix`)

```bash
cd editors/vscode
npx @vscode/vsce package
```

Install the resulting `.vsix` file. Because the packaged extension no longer lives inside the repo tree, the auto-detected repo root is wrong. You must set the `fltk.grammars.server.command` setting (a string array) to tell the extension how to launch the server:

```json
"fltk.grammars.server.command": [
  "uv", "--project", "/path/to/fltk", "run", "--extra", "lsp", "fltk-grammar-lsp"
]
```

The extension appends the language id (`fltkg`, `fltkfmt`, or `fltklsp`) as the final argument. You can append `--width` and `--indent` to the array to tune formatting.

This setting is machine-scoped: it can only be set in user or machine settings, not in workspace `.vscode/settings.json`. This is deliberate -- it prevents a cloned repository from silently redirecting which executable gets launched.

The extension is not published to the VS Code marketplace. Installation is from source or from a locally built `.vsix`.

## Bazel (`@fltk//`) -- experimental

If your project vendors fltk as a Bazel submodule (`@fltk//...`), you can launch the server directly from that submodule without a separate fltk install:

```bash
bazel run @fltk//:grammar_lsp -- fltkg
```

To use this from VS Code, set the command prefix:

```json
"fltk.grammars.server.command": ["bazel", "run", "@fltk//:grammar_lsp", "--"]
```

This path is experimental. Two caveats:

**Lock contention.** Every `bazel run` grabs the Bazel workspace lock. If VS Code restores a session with `.fltkg`, `.fltkfmt`, and `.fltklsp` files all open, it tries to start three server processes at once; the extra Bazel invocations queue on the lock. The result is slow or timed-out client startup (not data corruption -- LSP traffic uses stdout while Bazel's build output goes to stderr).

**Cold-cache latency.** With an empty Bazel cache, there is a visible build before the server begins responding.

When you use more than one fltk language, the recommended workaround is to generate a launcher script once and point the setting at that script, which avoids the per-launch lock contention:

```bash
bazel run --script_path=/path/to/grammar_lsp.sh @fltk//:grammar_lsp
```

```json
"fltk.grammars.server.command": ["/path/to/grammar_lsp.sh"]
```

## The generic `fltk-lsp` server

`fltk-grammar-lsp` is a convenience wrapper. Under the hood it calls the same generic `fltk-lsp` server that powers any fltk-based language (including the gear demo in `examples/gear/`). If you are building your own language on fltk, you use `fltk-lsp` directly with explicit `--grammar`, `--lsp`, `--fmt`, and optionally `--resolver` flags pointing at your own spec files. See `examples/gear/` for a complete example including a VS Code extension and a cross-file resolver plugin.
