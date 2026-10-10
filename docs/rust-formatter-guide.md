# Building a Standalone Formatter Binary for Your Grammar

This guide shows how to turn any FLTK grammar into a standalone, pure-Rust formatter CLI using
the `fltk_formatter_main!` macro from the `fltk-fmt-cli` crate. The macro generates a complete
`fn main()` — argument parsing, file/stdin I/O, in-place/check modes, exit codes, error
reporting — so a formatter binary is a single macro invocation naming your grammar's generated
parser and unparser types.

`crates/fltkfmt/` (the `.fltkg` formatter, built from `fegen.fltkg`) is the canonical worked
example; this guide mirrors it.

---

## Overview

`fltk-fmt-cli` provides the grammar-independent CLI scaffolding. The grammar-specific pieces —
the concrete `Parser` / `Unparser` types and the start-rule parse/unparse methods — are bound
at your call site by the macro. The expansion runs the pure-Rust pipeline:

```
Parser::new(src, filename, true) → parser.apply__parse_<rule>(0) → fully-consumed check
  → Unparser::new().unparse_<rule>(&cst) → resolve_spacing_specs → Renderer::render
```

No Python, PyO3, or GIL is involved at any stage.

---

## The crate it formats

The binary needs your grammar's pure-Rust parser and unparser. They come from the pure-Rust
`generate_rust_parser` target of [`docs/bazel-consumer-guide.md`](bazel-consumer-guide.md) §5,
with `unparser = True` (§5.2), and the binary itself is the `rust_binary` of §5.3. That guide
owns the module pin, the codegen target, the runtime deps (`fltk-parser-core:no_python`,
`fltk-unparser-core`, …) and the binary's `version` attribute; nothing here repeats them.

The crate root declares its `parser` and `unparser` modules `pub` (the consumer guide's recipe
prints them that way) because the binary names `my_grammar_cst::parser::Parser` and
`my_grammar_cst::unparser::Unparser` from outside the crate: with private `mod` declarations those
paths fail to resolve. `cst` may stay private — the generated parser and unparser reach it as
`super::cst`.

Your start rule determines the method names the macro references: `apply__parse_<rule>` and
`unparse_<rule>`. For `fegen.fltkg` the start rule is `grammar`, giving `apply__parse_grammar` and
`unparse_grammar`.

---

## The macro invocation

The entire `src/main.rs` is one invocation:

```rust
fltk_fmt_cli::fltk_formatter_main! {
    about: "Format MyGrammar files.",
    parser: my_grammar_cst::parser::Parser,
    unparser: my_grammar_cst::unparser::Unparser,
    parse: apply__parse_<start_rule>,
    unparse: unparse_<start_rule>,
}
```

Parameters:

| Parameter  | What it is | Value |
|------------|------------|-------|
| `about`    | Required. The one-line description `-h`/`--help` show (`expr`). | `"Format MyGrammar files."` |
| `name`     | Optional. The name `--version` prints (`expr`). | Default `env!("CARGO_PKG_NAME")` of *your* crate |
| `version`  | Optional. The version `--version` prints (`expr`). | Default `env!("CARGO_PKG_VERSION")` of *your* crate |
| `parser`   | Path to your grammar's generated parser type (`path`). | `my_grammar_cst::parser::Parser` |
| `unparser` | Path to your grammar's generated unparser type (`path`). | `my_grammar_cst::unparser::Unparser` |
| `parse`    | The start-rule parse method name (a bare `ident`, not a path). | `apply__parse_<start_rule>` |
| `unparse`  | The start-rule unparse method name (a bare `ident`). | `unparse_<start_rule>` |

`<start_rule>` is the grammar rule you want to format whole documents against. The method names
are taken as identifiers (no `paste`/`concat_idents` needed), so substitute your rule name
directly: e.g. start rule `document` → `parse: apply__parse_document`, `unparse:
unparse_document`.

The keys must appear in exactly this order — `about`, `name`, `version`, `parser`, `unparser`,
`parse`, `unparse` — with `name` and `version` omittable. Despite the keyword labels they are
positional (the macro has a single fixed-order arm), so reordering them produces a macro-match
error rather than working.

The `name` and `version` defaults are evaluated in your crate, so `--version` prints your
binary's identity, never `fltk-fmt-cli`'s. Under Bazel, `CARGO_PKG_NAME` is the `rust_binary`
target name and `CARGO_PKG_VERSION` is its `version` attribute — `0.0.0` when the attribute is
unset. So set `version` on your `rust_binary`, and pass `name:` if the target name is not what
users should see.

The expansion is pure sugar over `fltk_fmt_cli::run_main`. If you need to customize the
pipeline (e.g. a different consumed-input policy), call
`run_main(FormatterInfo { about, name, version }, closure)` directly, with your own
`Fn(&str, Option<&str>, RendererConfig) -> Result<String, String>` closure, instead of using the
macro. All three `FormatterInfo` fields are required.

---

## The CLI surface you get for free

Every generated binary exposes the same flags (from `FmtArgs` / clap):

| Flag | Meaning |
|------|---------|
| `[FILES]...` | Input files to format. None (or `-`) reads from stdin. |
| `--check` | Report whether inputs are already formatted without writing; exit non-zero if not. |
| `--in-place` | Rewrite each input file in place (atomic temp+rename). Requires at least one file. |
| `-w, --width <N>` | Maximum line width. Default `80`. |
| `-i, --indent <N>` | Indentation width. Default `2`. |
| `-o, --output <PATH>` | Write output to this file instead of stdout (single input only). |
| `-h`, `--help` | Your `about` text. |
| `-V`, `--version` | `<name> <version>` — your binary's, never `fltk-fmt-cli`'s. An unversioned Bazel target prints `0.0.0`. |

Behavior baked into the scaffolding:

- **Default**: format each input to stdout (multiple inputs concatenate in order).
- **Exit codes**: `0` success; `1` when `--check` finds an input that would change; `2` for any
  error (usage, read/write failure, parse/unparse failure). Processing continues across all
  inputs; the returned code is the worst outcome seen.
- **Rejected combinations** (exit `2` with a usage message): `--in-place` with `--output`,
  `--check`, no file, or `-`; `--check` with `--output`; `--output` with more than one input.
- **Errors** are prefixed with the input's filename (`<stdin>` for stdin); a partial parse
  (non-whitespace left unconsumed) and a depth-limit overflow are both reported as errors.

---

## Worked example

For a grammar whose start rule is `grammar` (this is exactly `crates/fltkfmt/src/main.rs`):

```rust
fltk_fmt_cli::fltk_formatter_main! {
    about: "Format FLTK grammar (.fltkg) files.",
    parser: fegen_rust_cst::parser::Parser,
    unparser: fegen_rust_cst::unparser::Unparser,
    parse: apply__parse_grammar,
    unparse: unparse_grammar,
}
```

Build it, then run the built binary (`//:mylang_fmt` is the consumer guide's §5.3 target):

```bash
bazel build //:mylang_fmt
BIN=bazel-bin/mylang_fmt

"$BIN" input.mygrammar                       # format to stdout
"$BIN" --in-place -w 100 -i 4 src/*.mygrammar
"$BIN" --check src/*.mygrammar               # CI gate
cat input.mygrammar | "$BIN"                 # stdin → stdout
```

`bazel run //:mylang_fmt -- …` works too, but only with `--run_under="cd $PWD &&"`: `bazel run`
executes in the runfiles tree, so without it every relative file path above names a different
file or none.

That is the whole recipe: the §5.2 codegen target, the two `pub mod` lines, and one
`fltk_formatter_main!` invocation.
