# Refined Request: Standalone Rust Formatter Binary for `.fltkg` Files

## Original request

> "We've just finished Rust unparser generation. I want proof of life in the form of a standalone formatter binary for .fltkg files. We already have an fegen.fltkfmt I think, and we're using it from python. I'd like a pure-Rust formatter with zero python deps: It uses pure-rust parser and hands that CST off to a pure-rust unparser. Give it all the typical CLI flags you'd want for a code formatter. Bonus points: Turn this into an easy way to create a code formatter for *any* fltk grammar, given the grammar file and the fltkfmt file. Maybe as a Rust macro or generic."

## What the user is asking for

The primary ask is a standalone Rust binary that formats `.fltkg` grammar files — a "proof of life" for the recently completed Rust unparser generation feature. This binary must have zero Python dependencies: it parses `.fltkg` input using a pure-Rust generated parser, passes the resulting CST to a pure-Rust generated unparser, and renders the formatted output. The entire pipeline runs without Python, PyO3, or the GIL.

The secondary ask (the "bonus") is to make this approach reusable, so that anyone who defines a language with FLTK can easily produce a standalone Rust formatter binary for that language, given its grammar file and its `.fltkfmt` format specification.

## What matters in the codebase

### The three Rust runtime crates

FLTK's Rust side is built on three `rlib` crates that provide the runtime machinery generated code links against:

- **`fltk-cst-core`** (at `crates/fltk-cst-core/`) — provides `Span`, `SourceText`, `Shared`, and related CST infrastructure. PyO3 support is behind an optional `python` feature; pure-Rust consumers use `default-features = false`.
- **`fltk-parser-core`** (at `crates/fltk-parser-core/`) — provides the parsing engine (`TerminalSource`, `PackratState`, `ErrorTracker`, regex support). Never links PyO3.
- **`fltk-unparser-core`** (at `crates/fltk-unparser-core/`) — provides the `Doc` IR, `DocAccumulator`, `Renderer`, `RendererConfig`, and `resolve_spacing_specs`. No dependencies at all — no PyO3, no `fltk-cst-core`.

All three are members of the root Cargo workspace.

### How Rust code is generated

FLTK generates Rust source files from grammars using Python CLI commands (via `fltk/fegen/genparser.py`). The generated `.rs` files are committed to the repository. Three generators exist:

- **CST generator** (`gen-rust-cst`) — takes a `.fltkg` grammar and produces a `cst.rs` with CST node structs, child enums, label enums, and accessors.
- **Parser generator** (`gen-rust-parser`) — takes a `.fltkg` grammar and produces a `parser.rs` with a `Parser` struct and per-rule `apply__parse_{rule}` methods.
- **Unparser generator** (`gen-rust-unparser`) — takes a `.fltkg` grammar and optionally a `.fltkfmt` format specification, and produces an `unparser.rs` with an `Unparser` unit struct and per-rule `unparse_{rule}` methods. The format specification is **baked into the generated code at generation time** — the `Unparser` struct carries no runtime configuration for formatting rules.

### The `fegen-rust` crate: most of the way there

A crate at `crates/fegen-rust/` already contains generated Rust CST (`cst.rs`) and parser (`parser.rs`) for FLTK's own grammar (`fegen.fltkg`). It builds as `fegen-rust-cst` and is a standalone crate (separate `[workspace]`, excluded from the root workspace). It currently depends on `fltk-cst-core` and `fltk-parser-core`.

What is **missing**: there is no `unparser.rs` in this crate. The Rust unparser for the fegen grammar has never been generated. The Makefile's `gencode` target regenerates `cst.rs` and `parser.rs` for this crate but has no `gen-rust-unparser` step for `fegen.fltkg`.

### The format specification exists

A `.fltkfmt` file at `fltk/fegen/fegen.fltkfmt` defines the formatting rules for `.fltkg` files — trivia preservation (line comments, block comments), blank-line handling, separator spacing, and rule-level group/nest/anchor directives. This is the same spec the Python formatter uses today.

### The proven pure-Rust pipeline

A test fixture at `tests/rust_parser_fixture/` demonstrates the complete pure-Rust format pipeline (parse → unparse → resolve spacing → render), with no Python involvement. The steps are: construct a `Parser` from source text, call `apply__parse_{rule}`, read-lock the resulting `Shared<Node>`, call `Unparser::new().unparse_{rule}`, resolve spacing specs, then render to a `String` via `Renderer`. This is exactly the pipeline the standalone binary would use.

### The existing Python formatter CLI

The Python formatter (`fltk/unparse_cli.py`) accepts a grammar file, a format spec file, and an input file, plus flags for `--width`, `--indent`, `--output`, `--rule` (start rule), and stdin/stdout support. This provides a reference for what the Rust binary should cover, though the Rust binary can be simpler since the grammar and format spec are baked in at generation time.

### No existing binary targets

No crate in the repository currently defines a `[[bin]]` target. All Rust artifacts are libraries (`rlib` or `cdylib`). This binary would be the first.

## The primary deliverable

Generate a Rust unparser for `fegen.fltkg` using the existing `fegen.fltkfmt` format specification, wire it into the `fegen-rust` crate (or a new crate/binary target alongside it), and produce a standalone binary that formats `.fltkg` files.

The binary should default to writing formatted output to stdout — the safer default, and consistent with the existing Python formatter. In-place and check modes are opt-in via explicit flags. The full CLI surface:

- Accept one or more input files as positional arguments, and/or read from stdin when no file is given (or `-` is passed).
- **Default behavior**: write formatted output to stdout.
- **Check mode** (`--check`): report whether the input is already correctly formatted without writing output; exit non-zero if it is not. This is what CI pipelines and pre-commit hooks use.
- **In-place mode** (`--in-place`): write formatted output back to each input file rather than stdout. Requires at least one file argument (incompatible with stdin).
- **Width** (`--width` / `-w`): maximum line width for the formatter, defaulting to the project's convention (80).
- **Indent** (`--indent` / `-i`): indentation width, defaulting to the project's convention.
- **Output file** (`--output` / `-o`): write to a specific file instead of stdout (when not using in-place mode).
- Appropriate exit codes: 0 for success (or "already formatted" in check mode), non-zero for formatting needed (check mode) or errors.
- Error messages to stderr when files cannot be read or parsed.

## The bonus deliverable: reusable formatter scaffolding

The user would like this to be easily reusable — given any FLTK grammar and its `.fltkfmt` file, someone should be able to produce a standalone Rust formatter binary for that language without much ceremony. Ideally, the automation itself is the proof of life: rather than first hand-building a formatter for `fegen.fltkg` and then later automating the process, the preferred approach is to build the automation first and then use it to produce the fegen formatter as its first consumer. That said, building it manually first is acceptable as long as there is a clear path toward automation — the user does not want to stop at a one-off binary with no reuse story.

### Where this is in tension with the codebase

The user suggested "maybe as a Rust macro or generic" for the reuse mechanism, but the architecture makes this more nuanced than it might sound. The format specification is baked into the generated `Unparser` at code-generation time — there is no runtime `FormatterConfig` object in the Rust layer. The `Unparser` is always a unit struct with formatting decisions embedded in its method bodies. Similarly, the `Parser` struct is grammar-specific generated code. There is nothing to be generic *over* at the Rust type level: each grammar produces its own concrete parser and unparser types with different methods.

What *can* be shared across grammars is the `main()` scaffolding: argument parsing, file I/O, the parse-unparse-resolve-render pipeline, check mode logic, in-place write logic, exit codes. The grammar-specific parts are: which `apply__parse_{rule}` to call, which `unparse_{rule}` to call, and the crate dependencies.

The right reuse mechanism is a design decision, not a requirements question. The key constraint any approach must respect is the "format spec baked at generation time" architecture: each grammar yields its own concrete parser and unparser types with grammar-specific methods, so the reuse boundary falls between the grammar-independent CLI scaffolding and the grammar-specific parse/unparse calls.
