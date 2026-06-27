# ELI5: Building a Standalone Rust Formatter for `.fltkg` Files

## What this is about

FLTK is a toolkit for building parsers and compilers. You describe a language's grammar in a `.fltkg` file, and FLTK generates a parser (code that reads that language) and a set of data structures called a Concrete Syntax Tree (CST) that represent parsed source code as a structured tree. FLTK can also generate an *unparser* -- code that takes a CST and turns it back into nicely formatted text -- using formatting rules you specify in a `.fltkfmt` file.

Until recently, all of FLTK's code generation produced Python. A recent line of work added the ability to generate Rust code instead: Rust parsers, Rust CST types, and -- most recently, in commit 6f975eb -- Rust unparsers. These generated Rust modules link against three small, pure-Rust runtime libraries that ship with FLTK (`fltk-cst-core` for CST data structures, `fltk-parser-core` for the parsing engine, and `fltk-unparser-core` for the formatting/rendering engine). None of these runtime libraries depend on Python.

The user wants "proof of life" for this new Rust unparser capability: a standalone binary, written entirely in Rust, that formats `.fltkg` files. The binary would parse a `.fltkg` file using a generated Rust parser, hand the resulting CST to a generated Rust unparser, and render the formatted output -- all without Python, PyO3, or the Python runtime being involved at any point. This would be the first binary target in the entire repository; everything else currently builds as a library.

There is a secondary goal: make the formatter easy to replicate for other FLTK-defined languages. Someone who defines their own language with FLTK should be able to produce a standalone Rust formatter binary for that language with minimal ceremony.

## The pieces that already exist

FLTK already uses itself to define its own grammar format. The grammar for `.fltkg` files lives at `fltk/fegen/fegen.fltkg`. Alongside it is `fltk/fegen/fegen.fltkfmt`, a format specification that describes how `.fltkg` files should be laid out -- things like "put a newline after every semicolon," "indent continuation lines inside a rule definition," and "keep comments attached to their surrounding code." A Python-based formatter already uses this spec today.

On the Rust side, a crate at `crates/fegen-rust/` already contains generated Rust code for two of the three stages: `cst.rs` (the CST data structures for the fegen grammar) and `parser.rs` (the parser). What is missing is `unparser.rs` -- no one has yet run the Rust unparser generator against `fegen.fltkg` with its `.fltkfmt` spec. The Makefile's code-generation target regenerates the CST and parser for this crate but has no step for the unparser.

The complete parse-unparse-render pipeline has already been proven in pure Rust in a test fixture elsewhere in the repo. The test demonstrates exactly the sequence the binary would use: create a parser, parse the input, read-lock the resulting CST node, create an unparser, unparse the CST into a document tree, resolve spacing specifications in that tree, and render it to a string. No Python is involved.

## The three pieces of new work

The design calls for three things, built in a specific order: first generate the missing unparser, then build a reusable CLI scaffolding library, then assemble the actual binary using that scaffolding.

### Generating the fegen Rust unparser

The first step is straightforward: run the existing `gen-rust-unparser` tool against `fegen.fltkg` with `fegen.fltkfmt` as the format configuration. This produces a new file, `crates/fegen-rust/src/unparser.rs`, containing a Rust `Unparser` struct with an `unparse_grammar` method. All the formatting rules from `fegen.fltkfmt` are baked directly into the generated code at generation time -- the `Unparser` is a unit struct (no fields, no runtime configuration) whose method bodies encode every spacing and layout decision statically. This is how FLTK's Rust unparser generation works for all grammars, not a special choice for this project.

The existing crate needs a few small wiring changes to accommodate the new module:

- The crate's `lib.rs` gets a `pub mod unparser;` declaration. The unparser module must be public because the binary (which lives in a separate crate) needs to name the `Unparser` type through it. The CST module (`mod cst;`) stays private -- the binary never needs to name CST types directly, because the macro (described below) works with them only through type inference. This is the same visibility arrangement the crate already uses: the parser module is public and exposes return types that reference private CST types, which works fine in Rust because the *types* are public even when the *module* is private.

- The crate's `Cargo.toml` gains a dependency on `fltk-unparser-core`, which the generated unparser code references.

- Under a `#[cfg(feature = "python")]` gate, the new unparser module's PyO3 classes get registered as a submodule, mirroring how the parser module is already registered. This keeps the Python extension build warning-clean (without it, the PyO3 registration function in the generated code would be dead code in Python builds).

- The Makefile's code-generation target gets a new step to regenerate the unparser. Because the format spec is baked at generation time, the committed `unparser.rs` must be regenerated whenever `fegen.fltkfmt` changes. The existing workflow of running `make gencode` and checking `git diff` for unexpected changes serves as a drift guard.

### Reusable CLI scaffolding: the `fltk-fmt-cli` crate

This is where the "bonus" reuse goal lives. Rather than hard-coding argument parsing and file I/O into the fegen formatter and then later extracting it, the design builds the reusable scaffolding first and makes the fegen formatter its first consumer.

The new crate, `fltk-fmt-cli`, is a regular Rust library (no Python involvement). It lives in the root Cargo workspace alongside the other runtime crates, because it is shared infrastructure that any downstream formatter crate can depend on.

It provides three things:

**A CLI argument struct (`FmtArgs`).** This is a `clap`-based struct that defines the full command-line interface a formatter binary should have:

- Positional file arguments (zero or more paths; no files or `-` means read from stdin).
- `--check`: a "dry run" mode that reports whether the input is already correctly formatted, without writing anything. If any input would change, the binary exits with code 1. This is what CI pipelines and pre-commit hooks use.
- `--in-place`: rewrite each file in place with its formatted version. Requires at least one file argument (you cannot rewrite stdin in place).
- `--width` / `-w`: maximum line width, defaulting to 80.
- `--indent` / `-i`: indentation width, defaulting to 2. This default matches the `.fltkg` source convention (continuation lines in grammar files are 2-space indented) and the existing Python formatter's default. The rendering engine's own default is 4, but the CLI overrides it to 2 because 2 is what `.fltkg` files actually use.
- `--output` / `-o`: write to a specific file instead of stdout.
- `--help` and `--version` come from `clap` automatically.

**A `run_main` function.** This is the workhorse. It takes a single argument: a closure (a function value) that does the grammar-specific work of formatting. The closure receives source text, an optional filename, and a renderer configuration, and returns either the formatted string or an error message. `run_main` handles everything else: parsing CLI arguments, validating flag combinations, reading input files, calling the closure for each one, dispatching the output to the right place based on mode, and choosing the right exit code. When the closure returns an error, `run_main` prepends the file path to the error message before printing it, because the parser's own error output contains line/column/caret information but never the filename.

**A `fltk_formatter_main!` macro.** This is the "easy button." A consumer writes a single macro invocation naming their grammar crate's parser type, unparser type, parse method, and unparse method:

```
fltk_fmt_cli::fltk_formatter_main! {
    parser:   my_crate::parser::Parser,
    unparser: my_crate::unparser::Unparser,
    parse:    apply__parse_my_start_rule,
    unparse:  unparse_my_start_rule,
}
```

The macro expands into a complete `fn main()` that constructs the closure `run_main` needs, wiring together the proven parse-unparse-resolve-render pipeline for the named start rule. The macro takes method *identifiers* (bare names), not strings, so it does not need any helper crates for identifier manipulation.

Why a macro and not a trait or generic function? Because FLTK's generated parsers and unparsers do not implement any shared trait. Each grammar produces its own concrete types with grammar-specific method names (the parse method for a grammar whose start rule is `grammar` is `apply__parse_grammar`; for one whose start rule is `program` it would be `apply__parse_program`). There is nothing to be generic *over* at the Rust type level. A trait-based approach would require every grammar consumer to write a hand-implemented trait impl that would be strictly more boilerplate than the macro call. The macro is the minimal-ceremony way to bind grammar-specific names.

The macro is sugar over `run_main`, not a replacement for it. Consumers who want to customize the pipeline (for example, adding a post-processing pass) can call `run_main` directly with a hand-written closure.

The scaffolding crate also provides a `fully_consumed` helper function. After parsing, the binary needs to check whether the parser consumed the entire input. A naive check (`position == length`) would reject normal files that end with a trailing newline or extra whitespace, because the grammar's rules might not consume trailing whitespace. `fully_consumed` accepts a parse whose unconsumed suffix is entirely whitespace, treating only a non-whitespace remainder as a genuine partial parse. It works with character indices (not byte indices), because FLTK's span positions are character-based.

### The fegen formatter binary: `fltkfmt`

The final piece is a new crate at `crates/fltkfmt/` that produces the actual binary. It is a standalone crate with its own workspace (separate from the root workspace), following the same pattern as the `fegen-rust` crate and the test fixtures. This isolation keeps the `fegen-rust-cst` crate's default PyO3 features from being pulled into the root workspace's dependency resolution.

The binary crate depends on `fegen-rust-cst` with default features disabled (pure Rust, no PyO3), `fltk-unparser-core`, and `fltk-fmt-cli`. The CST and parser runtime crates come in transitively through `fegen-rust-cst`.

The entire `src/main.rs` is the single macro invocation from the scaffolding crate, naming the fegen grammar's parser and unparser types and methods. This proves the scaffolding works: a complete, fully-featured formatter binary with near-zero per-grammar code.

Because the crate is standalone (outside the root workspace), the root `cargo test` and `cargo clippy` will not see it. The Makefile's check targets must be extended to cover it explicitly, using `--manifest-path` to point at its `Cargo.toml`. The design calls for adding it to four existing check steps: the no-Python cargo test step, the no-Python clippy step, the check that proves no PyO3 is linked (which is what backs the "zero Python" claim), and the supply-chain audit step (`cargo deny`). A convenience target for building a release binary may be added but is not a check step.

The scaffolding crate `fltk-fmt-cli`, by contrast, is a root workspace member and is automatically covered by the root workspace's check commands -- no per-crate target is needed. Adding it does pull `clap` (the argument-parsing library) and its transitive dependencies into the root workspace's supply-chain audit. The design notes that clap's dependency tree uses MIT/Apache-2.0 licenses (with some Unicode-3.0), all within the project's existing allow-list, and that the project's `cargo deny` configuration warns on (rather than denying) duplicate dependency versions. The implementer is directed to run the audit after adding clap to confirm nothing breaks.

## How the CLI behaves

The CLI behavior is specified in detail:

- **Default mode** (no `--check`, no `--in-place`): format each input and write to stdout. When multiple files are given, their outputs are concatenated in order (following `gofmt`'s convention). The `--output` flag therefore requires exactly one input source.

- **Check mode** (`--check`): format in memory, compare byte-for-byte to the original, write nothing. Print the path of each file that would change to stderr. Exit 1 if any differ, 0 if all match.

- **In-place mode** (`--in-place`): write each formatted result back to its file. Requires at least one file argument; rejects stdin or `-`.

- **Errors** (parse failure, unreadable file, non-UTF-8 input) go to stderr with context. Processing continues across remaining inputs so one bad file does not mask the rest. The final exit code reflects the worst outcome: 2 (error) beats 1 (check-diff) beats 0 (success).

- **Conflicting flags** (`--in-place` with `--output`, `--in-place` with `--check`, `--output` with multiple inputs, `--in-place` with no file) are rejected with a usage error to stderr and exit 2.

## What could go wrong and how it is handled

**Trailing whitespace at the end of a file.** Real `.fltkg` files end with a newline. Whether the parser consumes a trailing newline depends on the grammar's trailing whitespace rules, and it is not guaranteed to consume all forms of trailing whitespace (extra blank lines, for instance). Requiring the parser position to exactly equal the input length would spuriously reject normal files. The `fully_consumed` helper solves this by accepting any parse whose unconsumed suffix is pure whitespace, treating only non-whitespace remainders as errors. The test plan includes assertions that files with and without trailing newlines format successfully to the same result.

**Parse failure.** When the parser cannot parse the input, it returns `None`. The macro closure converts this to an error carrying the parser's error message, which includes line, column, and a caret pointing at the problem. The CLI scaffolding prepends the filename when printing the error. The parser's `error_message()` function does not include the filename on its own -- the filename passed to `Parser::new` goes into span bookkeeping but never appears in the error output. The CLI, which owns the file path, is what associates an error with its file. Exit code 2.

**Unparser returns `None`.** This would indicate a mismatch between the CST shape and the unparser's expectations -- something that should not happen for a successfully parsed tree. Rather than panicking, the macro maps this to an explicit internal error message. Exit code 2.

**Empty input.** The fegen grammar requires at least one rule (`grammar := , rule+`), so an empty file is an invalid `.fltkg` and surfaces as a parse error. This is not special-cased.

**Non-UTF-8 input.** Rust strings are UTF-8, so reading a non-UTF-8 file fails at the read stage. Reported as a read error, exit code 2.

**In-place write atomicity.** A formatter that truncates a file and then fails mid-write would corrupt the source. The design specifies writing to a temporary file in the same directory and then renaming it over the original, so a crash leaves the original intact.

**In-place write on an unchanged file.** Still safe to rewrite identical bytes, and the rename-based approach avoids needless filesystem churn. Skipping the write when output equals input is mentioned as a minor optional optimization.

**Idempotency.** Formatting already-formatted output must produce identical output (`format(format(x)) == format(x)`). This is the core correctness invariant and is explicitly tested.

**Threading.** The unparser core's `Doc` type uses `Rc` (a single-threaded reference count) internally, so the render stage cannot be shared across threads. The CLI processes files sequentially, so this is not a constraint. No threading is introduced.

## How it is tested

**Scaffolding crate tests (`fltk-fmt-cli`).** These are pure Rust tests that use a stub formatting function (not a real parser) to verify the CLI scaffolding in isolation:

- Default mode writes to stdout; multiple files concatenate in order.
- Check mode exits 1 when the stub would change input, 0 when it would not, and writes nothing to stdout.
- In-place mode rewrites files, rejects stdin, and uses atomic temp-file-plus-rename.
- Conflicting flag combinations exit 2 with a usage message.
- A missing file produces exit 2 but other inputs are still processed.
- The `fully_consumed` helper is unit-tested: exact length (accept), trailing whitespace (accept), trailing non-whitespace (reject), and correct behavior with multibyte characters (ensuring it uses character indices, not byte indices).

**Formatter binary integration tests (`crates/fltkfmt/tests/`).** These are pure Rust tests that exercise the real formatter end-to-end:

- Idempotency: format a corpus of `.fltkg` files (including `fegen.fltkg` itself and test-data grammars), then format the result again; assert the second pass is byte-identical to the first.
- Golden output: assert that formatting the canonical `fegen.fltkg` at width 80 / indent 2 produces a stable expected output.
- Trailing-newline robustness: the same input with and without a trailing newline, and with trailing blank lines, formats successfully to the same result.
- Parse-error path: malformed input yields a non-zero result and a message mentioning the synthetic filename and a line/column.

**Cross-backend parity (recommended).** A pytest that compares the Rust binary's output to the Python formatter's output for a corpus of `.fltkg` files at matching width and indent settings, asserting byte equality. This is the strongest guarantee that the pure-Rust formatter matches the established Python formatter and guards against future drift.

**Drift guard.** Running `make gencode` followed by `git diff` must show no changes to the committed `unparser.rs` or its `.pyi` stub, following the existing convention for detecting uncommitted regeneration.

## What is still open

The design identifies no open questions that require user input. Two deliberate defaults are flagged for visibility, both changeable:

- The default `--indent` is 2, matching the `.fltkg` source convention and the Python formatter's default, even though the rendering engine's own default is 4. The CLI overrides the engine default.
- When multiple files are given in default (stdout) mode, their formatted outputs are concatenated in order, following `gofmt`'s convention. The `--output` flag is therefore restricted to a single input source.
