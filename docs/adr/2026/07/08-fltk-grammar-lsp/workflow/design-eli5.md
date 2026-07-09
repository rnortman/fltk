# ELI5: Dogfood LSP for fltk's own grammar DSLs

## What this is about

FLTK (Formal Language ToolKit) is a Python library for building parsers and compilers. If you want to invent a new language -- or a configuration format, or any structured text -- you describe its syntax in a grammar file, and FLTK generates a parser and typed data structures for you.

FLTK uses its own custom file formats to do this work. There are three of them, each a small domain-specific language (DSL):

- **`.fltkg` files** define the grammar itself -- the rules that say what valid syntax looks like in the language you are creating.
- **`.fltkfmt` files** describe how to pretty-print (auto-format) code written in the language the grammar defines.
- **`.fltklsp` files** describe how an editor should highlight the language -- which tokens are strings, which are keywords, which are type names -- and how to wire up "go to definition" and "find all references" for identifiers.

A Language Server Protocol (LSP) server is a background process that gives code editors (like VS Code) smart features: syntax highlighting, error diagnostics, auto-formatting, "go to definition," "find all references," and so on. Instead of each editor re-implementing these features, editors talk to an LSP server over a standard protocol, and the server does the analysis.

Recent work (milestones M0 through M5) built a generic, grammar-agnostic LSP server called `fltk-lsp`. You point it at a `.fltkg` grammar and optionally a `.fltklsp` and `.fltkfmt`, and it serves editor features for any language those files describe. A demo was built around a made-up language called "gear," proving the whole pipeline end-to-end in VS Code: highlighting, formatting, cross-file navigation, all working.

**The problem:** FLTK's own three DSLs (`.fltkg`, `.fltkfmt`, `.fltklsp`) do not get any of these editor features. Each DSL has a grammar file that describes its syntax, but the companion `.fltkfmt` and `.fltklsp` specs that would power formatting and highlighting are either missing or incomplete. No complete "triple" (grammar + format spec + LSP spec) exists for any of the three. Worse, the only way to launch the server today is a long command with four separate flags pointing at file paths deep inside the installed package -- not something a casual user would figure out.

**What we want:** Complete the spec triples for all three DSLs, wrap them behind a single friendly command, integrate with VS Code, and -- as a stretch goal -- make it all work when FLTK is pulled in as a Bazel submodule by another project.

This is "dogfooding": using our own tools on ourselves. But the payoff is broader than internal polish. The `.fltkg` server, for instance, does not just serve FLTK's own grammar files -- it serves any `.fltkg` file. Every downstream consumer editing their own grammar gets highlighting, diagnostics, and formatting for free.

## The relevant parts of the system

### The three DSLs and what they have today

Each DSL is defined by a grammar file that lives inside the `fltk` package:

| DSL | Grammar file | Has `.fltklsp`? | Has `.fltkfmt`? |
|---|---|---|---|
| `.fltkg` (grammars) | `fltk/fegen/fegen.fltkg` | No | Yes |
| `.fltkfmt` (format specs) | `fltk/unparse/unparsefmt.fltkg` | No | No |
| `.fltklsp` (editor specs) | `fltk/lsp/fltklsp.fltkg` | Yes (highlighting only) | No |

None has a complete triple. The `.fltklsp` language's own `.fltklsp` spec handles highlighting but has no definition/reference navigation. The `.fltkfmt` language has nothing beyond its grammar.

### How the existing LSP server works

`fltk-lsp` is a command-line tool that starts a single-language LSP server. You give it `--grammar` (required), plus optionally `--lsp` (for highlighting and navigation) and `--fmt` (for formatting). It loads those files, builds an analysis engine, and speaks the LSP protocol over standard I/O. Editors spawn one server process per language.

The server depends on a Python library called `pygls` (Python Generic Language Server), which is an optional install extra -- you get it with `pip install fltk[lsp]`. If pygls is missing, the server prints a helpful message and exits rather than crashing with an import error.

### The gear demo as a model

The gear demo (`examples/gear/`) is a working end-to-end example: a made-up language with a complete grammar, format spec, LSP spec, and a cross-file resolver plugin, plus a VS Code extension. It is the template for the new work. Its VS Code extension launches the server, wires up highlighting and formatting, and is configured via a machine-scoped setting (so that a cloned repo's workspace settings cannot redirect which executable gets launched -- a deliberate security choice).

### Bazel consumption

FLTK can be used as a Bazel dependency. Other projects pull it in as `@fltk//...` and use its code-generation macros. Today, the Bazel build knows nothing about the LSP server: there is no Bazel target for it, and the pip dependency lock file used by Bazel does not include `pygls`.

## What we are going to do and why

The design calls for four independently landable pieces, in order.

### Piece 1: Complete the spec triples (new sidecar files)

Six new or modified files, each living next to its grammar inside the `fltk` package so it ships automatically in the wheel (the Python distribution format).

**New `fegen.fltklsp`** -- the flagship spec. This gives `.fltkg` files full highlighting and definition/reference navigation. Rule names get "go to definition" (click a rule name where it is defined, find where it is used) and "find all references" (click a definition, see every use). This works because fltkg grammars have a natural def/ref structure: a rule definition (`rule := ...`) defines a name, and other rules reference that name when they use it as a sub-rule.

One nuance worth explaining: the def/ref system uses a "kind" label to classify what kind of thing is being defined or referenced. The design chooses `type` as the kind for rule names. This is not because grammar rules are types in the programming-language sense; rather, the highlighting system only paints tokens with special colors when the kind's name matches an entry in a fixed "token legend" built into the server. The kind `type` is in that legend and already matches the conventions used by the existing in-tree specs, so rule names get visually distinct highlighting. A kind like `rule` (which might seem more natural) is not in the legend and would leave rule names painted with the generic default color.

Other tokens get straightforward highlighting: string literals become `string`, regex bodies get a distinct paint, item labels become `label`, and punctuation/operators are painted as punctuation.

**New `unparsefmt.fltklsp`** -- highlighting for `.fltkfmt` files. Keywords (`rule`, `group`, `nest`, `join`, etc.) and spacing words (`nil`, `nbsp`, `soft`, `hard`, etc.) get their appropriate token types; rule names get `type` paint; literals become `string`; integers become `number`. Rule config blocks get definition navigation (outline/document-symbols) so you can jump between sections. However, there is no in-file reference navigation: when a `.fltkfmt` file refers to labels or literals, it is referring to things defined in a different file (the target grammar), which is a fundamentally cross-file problem beyond the scope of this work.

**New `unparsefmt.fltkfmt` and `fltklsp.fltkfmt`** -- formatting specs for `.fltkfmt` and `.fltklsp` files respectively. Both follow the same structural conventions as the existing `fegen.fltkfmt`: preserve line comments, preserve up to one blank line between blocks, put line breaks after semicolons, and indent the contents of `rule ... { ... }` blocks.

**Extended `fltklsp.fltklsp`** -- the self-hosting spec for `.fltklsp` files. Currently it only has highlighting. The design adds definition navigation for rule-block names so you get document-symbol outlines and can find references to a rule config block. Importantly, the design does *not* make anchor identifiers (which name rules or labels from the target grammar) into references -- that would be semantically wrong because those names refer to things in a different language's file, and resolving them within the same file would produce mostly-dangling, misleading results. An existing test file (`test_dogfood.py`) has a test-local spec that does wire up these anchors for test purposes; that stays as-is for testing, while the shipped spec deliberately omits it.

### Piece 2: One friendly entry point (`fltk-grammar-lsp`)

**The problem with the current CLI:** Today, launching a server for one of FLTK's own languages requires a command like `fltk-lsp --grammar fltk/fegen/fegen.fltkg --lsp fltk/fegen/fegen.fltklsp --fmt fltk/fegen/fegen.fltkfmt` -- you need to know where the files are inside the installed package. This is unfriendly.

**Why not extend `fltk-lsp`?** The existing `fltk-lsp` is a single-command CLI app (using a library called Typer). Adding a second command would change it from `fltk-lsp --grammar ...` to `fltk-lsp main --grammar ...`, breaking existing users. Rather than impose that breaking change, the design keeps the two scripts separate.

**The new script: `fltk-grammar-lsp LANGUAGE`.** You just say `fltk-grammar-lsp fltkg` (or `fltkfmt` or `fltklsp`) and the server starts. No path flags needed. The three languages and their file locations are hardcoded in a registry inside the new module. If you pass an unknown language name, the CLI exits with an error listing the valid options (Typer provides this for free).

**How it finds the files:** The files live inside the installed Python package. The new CLI locates them using `importlib.resources`, Python's standard mechanism for finding data files shipped inside packages. This works whether FLTK is installed as an editable development install, a regular wheel, or running under Bazel.

**Shared implementation:** Rather than duplicating the server-startup logic, the design extracts the core of `fltk-lsp`'s `main()` function into a shared helper called `serve()`. Both `fltk-lsp` (the generic, bring-your-own-files CLI) and `fltk-grammar-lsp` (the built-in-languages CLI) call this helper. The behavior of `fltk-lsp` is unchanged.

### Piece 3: VS Code extension

A single VS Code extension called `fltk-grammars` covers all three languages, modeled closely on the existing gear demo extension.

**One extension, three languages:** The extension registers the three file extensions (`.fltkg`, `.fltkfmt`, `.fltklsp`) and their language IDs. Rather than spawning three server processes at startup, it starts each server lazily -- only when you actually open a file of that language. This avoids wasting resources if you only ever edit `.fltkg` files.

**Server command configuration:** The extension has a machine-scoped setting (`fltk.grammars.server.command`) that holds the command used to launch the server. Machine scope is deliberate and matches the gear demo's approach: it prevents a cloned repository's workspace settings from redirecting the launched executable (a security concern -- you do not want a malicious repo to run arbitrary code when you open it). The extension appends the language ID as the final argument to whatever command is configured.

The default command (when the setting is empty) is computed from the extension's own location within the repository, using `uv` to run the server from the project.

**Language-specific configuration files:** Each language gets a `language-configuration.json` defining comment syntax, bracket pairs, and auto-close behavior. All three use `//` line comments. Only `.fltkg` also has `/* */` block comments (because only the grammar language has a block-comment construct).

### Piece 4 (stretch): Launch from a Bazel submodule

This makes `bazel run @fltk//:grammar_lsp -- fltkg` work from any project that depends on FLTK through Bazel (such as the `clockwork` project that currently uses a `local_path_override`).

Three changes are needed:

**Get pygls into the Bazel dependency graph.** Today, the lock file that Bazel reads (`requirements_lock.txt`) is generated from FLTK's base dependencies only, which do not include pygls. The design regenerates this file to include the `lsp` extra. Two regeneration paths exist (a `uv export` command for the committed file, and a separate Bazel `lock` target) and both must be updated to avoid divergence. The extra dependencies (pygls and its transitive needs: lsprotocol, cattrs, attrs) are fetched lazily under Bazel's module system, so projects that never use the LSP pay no cost.

**Ship the spec files as Bazel data.** The existing Bazel `py_library` target for `fltk` only globs `.py` files. The design adds globs for `.fltkg`, `.fltklsp`, and `.fltkfmt` files so that `importlib.resources` can find them when the server runs under Bazel.

**Add a `py_binary` target.** A new `py_binary` named `grammar_lsp` makes the server launchable via `bazel run`. It follows the same pattern as the existing `genparser` target.

**VS Code integration for the Bazel path** is just documentation, not code: set `fltk.grammars.server.command` to `["bazel", "run", "@fltk//:grammar_lsp", "--"]` and the extension handles the rest.

**Important caveats (documented as experimental):** Bazel's `run` command has a workspace lock, meaning only one `bazel run` can execute at a time. This is not a corner case -- it is the expected situation when VS Code reopens multiple files at startup, because the extension starts a server per language. The servers will start, but slowly, as each queues behind the lock. A cold Bazel cache also means a visible build delay before the server responds. For these reasons, the design recommends a `bazel run --script_path` pattern as the primary approach: generate a launcher script once, then point the VS Code setting at that script. This avoids re-entering Bazel on every server start.

## What could go wrong and how it is handled

**pygls not installed.** The shared `serve()` helper inherits the existing behavior: it tries to import pygls lazily, and if the import fails, it prints a message telling you to install `fltk[lsp]` and exits cleanly. No protocol gibberish on stdout, no stack trace.

**A shipped spec file has a bug.** The analysis engine validates specs at startup (anchors must reference real grammar constructs, token types must be from the known legend). A broken spec would cause the server to fail on launch. The test plan guards against this in CI by loading every registry entry and verifying it parses successfully, so a broken spec cannot ship silently.

**A user's own files reference things that do not exist.** When someone writes a `.fltkfmt` or `.fltklsp` for their own language, they might reference labels or rules that do not actually exist in their grammar. These servers cannot catch that: they only parse the sidecar file's own syntax and have no access to the target grammar. Cross-file validation like this would require the resolver plugin system, which is out of scope for this work.

**Formatting width.** The default formatting width is 80 columns (matching the existing `fltk-lsp` default), even though the FLTK repository itself uses 120. Users can override this via `--width` and `--indent` flags, or by customizing the VS Code setting to include these flags.

**Parse errors while editing.** Already handled by the existing engine from the M3 milestone: partial parses produce degraded highlighting rather than no highlighting, and diagnostics are reported for the broken portions.

**Three servers when you only need one.** The lazy-start design in the VS Code extension means a server process is only spawned for a language when you actually open a file in that language. If you only edit `.fltkg` files, only one server runs.

**The word `rule` is both a keyword and a rule name.** In the `.fltkg` grammar, there is a grammar rule literally called `rule`. The `.fltklsp` spec must say `rule rule { ... }` to describe it, which looks like it might confuse the parser. It does not: the parser distinguishes between the keyword and the identifier based on position, and this pattern is already proven by the existing `fegen.fltkfmt` which contains an analogous `rule rule { ... }` block.

## What is still open

### 1. Cross-file navigation from sidecar files into the grammar

When you are editing a `.fltkfmt` or `.fltklsp` file and you see a rule name (like `rule foo { ... }`), it would be natural to press F12 and jump to the definition of `foo` in the corresponding `.fltkg` grammar file. This does not work today and is not part of this design.

The reason it is hard: the existing resolver plugin system (the mechanism that enables cross-file navigation, proven by the gear demo) operates within a single language. A resolver's host provides documents analyzed by one engine against one grammar. But this cross-file jump would go from a `.fltkfmt` file (analyzed by the `.fltkfmt` engine) to a `.fltkg` file (which would need to be analyzed by the `.fltkg` engine). That is a cross-language operation that the resolver API does not currently support.

This matters because it would be the first real-world validation of the resolver plugin API, which is explicitly marked as provisional. Its own documentation says it needs real downstream use to prove out the design.

The design proposes deferring this: land the current declarative-only servers (which handle everything except cross-file navigation), file a TODO for the resolver API extension, and revisit later. This is a question of whether that deferral is acceptable, or whether cross-file navigation should be tackled now as part of this work.

### 2. VS Code extension distribution

Should the VS Code extension be published to the VS Code Marketplace, or should it remain an in-repo development artifact?

Right now, the gear demo extension is not published -- you install it by opening the repo in VS Code's Extension Development Host or by manually packaging a `.vsix` file. The design proposes the same approach for the `fltk-grammars` extension: in-repo only, no marketplace publication.

The trade-off: marketplace publication would make the extension easy to install (just search for it in VS Code), but it requires a marketplace account, a publication pipeline in CI, and ongoing maintenance of the listing. The design treats that as a separate decision with its own implications, not something to bundle into this work.
