# Guide review: docs/rust-formatter-guide.md

Fact-checked against crates/fltk-fmt-cli/src/lib.rs, crates/fltkfmt/ (Cargo.toml +
src/main.rs), crates/fegen-rust/ (Cargo.toml, lib.rs, generated src/*.rs), and
fltk/fegen/genparser.py + Makefile.

Verified accurate: macro name `fltk_formatter_main!`; parameter set/types
(`parser`/`unparser` = `:path`, `parse`/`unparse` = bare `:ident`); pipeline
(`Parser::new(src, filename, true)` -> `$parse(0)` -> depth/fully-consumed check ->
`Unparser::new().$unparse` -> `resolve_spacing_specs` -> `Renderer::render`); the
`run_main` signature `Fn(&str, Option<&str>, RendererConfig) -> Result<String,String>`;
`fltk_fmt_cli::RendererConfig` re-export; the full CLI flag table (`--check`,
`--in-place`, `-w/--width` default 80, `-i/--indent` default 2, `-o/--output`,
`--help`/`--version`); exit codes (0/1/2, worst-of accumulation); the rejected flag
combinations; the two-dependency `Cargo.toml` shape; the worked example in
crates/fltkfmt/src/main.rs (start rule `grammar` -> `apply__parse_grammar` /
`unparse_grammar`); and the Step 1 genparser subcommand names/args including the
`--format-config` flag (default `--cst-mod-path super::cst` makes the bare commands work
for the `src/cst.rs` + `src/parser.rs` + `src/unparser.rs` layout shown).

---

## code-1

File: docs/rust-formatter-guide.md:46-55 (Step 1, the cross-reference to
docs/rust-cst-extension-guide.md).

What's wrong: The doc tells the consumer to build the CST crate "exactly as the Rust CST
extension does" and to "See docs/rust-cst-extension-guide.md for the crate skeleton (lib.rs
module wiring via gen-rust-lib, the extension-module/python feature split, and how to pin
the non-published fltk-cst-core / fltk-*-core crates)." The linked guide's skeleton is
neither sufficient nor accurately described for a formatter dependency:

- crates/fltk-fmt-cli + the generated sources require the CST crate to be consumable as an
  `rlib`, but rust-cst-extension-guide.md:50 shows `crate-type = ["cdylib"]` only (no
  `rlib`). A cdylib-only crate cannot be used as a normal Cargo library dependency.
- The generated parser.rs `use fltk_parser_core::...` and unparser.rs
  `use fltk_unparser_core::...` (confirmed in crates/fegen-rust/src/parser.rs:16-19 and
  src/unparser.rs:4-7), so the CST crate must declare BOTH `fltk-parser-core` and
  `fltk-unparser-core` as dependencies. rust-cst-extension-guide.md:57-72 declares only
  `fltk-cst-core`.
- The macro names `my_grammar_cst::parser::Parser` and `..::unparser::Unparser`, so lib.rs
  must declare `pub mod parser;` and `pub mod unparser;` (as crates/fegen-rust/src/lib.rs
  does). rust-cst-extension-guide.md:76-86 shows only `mod cst;` (not even `pub`, no
  parser/unparser modules).
- The cross-reference attributes "lib.rs module wiring via gen-rust-lib" to the linked
  guide, but rust-cst-extension-guide.md never mentions `gen-rust-lib`; it hand-writes
  lib.rs.
- "how to pin the non-published fltk-cst-core / fltk-*-core crates" is also unsupported:
  the linked guide only pins fltk-cst-core, never the parser/unparser core crates.

Consequence: A downstream consumer who follows the linked guide's skeleton verbatim
produces a crate that does not compile (unresolved `fltk_parser_core` /
`fltk_unparser_core` in parser.rs/unparser.rs) and whose `parser::Parser` /
`unparser::Unparser` paths do not resolve (missing/non-pub modules), and cannot be used as
an rlib dependency at all. The only correct template is crates/fegen-rust/ (which the doc
names but does not reproduce), so the actionable instructions are wrong/incomplete for the
formatter case.

Fix: Give the formatter's CST crate its own complete, correct `Cargo.toml` + `lib.rs` in
this guide (mirroring crates/fegen-rust): `crate-type = ["cdylib", "rlib"]`; deps on
`fltk-cst-core`, `fltk-parser-core`, `fltk-unparser-core` (with the pyo3-optional feature
split); and `mod cst; pub mod parser; pub mod unparser;`. If `gen-rust-lib` is the intended
lib.rs generator, show the actual invocation (e.g. `gen-rust-lib ... --unparser`) and
confirm it emits the `pub mod parser/unparser` the macro needs; do not defer these to a
guide that lacks them.

---

## code-2

File: docs/rust-formatter-guide.md:165-177 (Minimal end-to-end example, build vs run).

What's wrong: Build uses `cargo build --release --manifest-path
crates/my-grammar-fmt/Cargo.toml`, but every run command invokes
`./target/release/my-grammar-fmt`. The guide says it mirrors crates/fltkfmt, which carries
its own `[workspace]` (crates/fltkfmt/Cargo.toml:5) — i.e. a standalone workspace whose
build artifacts land in `crates/my-grammar-fmt/target/release/`, not the repo-root
`./target/release/`.

Consequence: For the standalone-workspace layout the guide says it mirrors, the
copy-pasted run/CI commands look in the wrong directory and fail with "no such file"; the
built binary is at `crates/my-grammar-fmt/target/release/my-grammar-fmt`.

Fix: Use the manifest-relative path (`crates/my-grammar-fmt/target/release/my-grammar-fmt`)
or `cargo run --release --manifest-path crates/my-grammar-fmt/Cargo.toml -- ...`, and/or
state explicitly whether the consumer crate is its own workspace (artifacts local) or a
member of a parent workspace (artifacts at the workspace root).

---

## code-3 (minor)

File: docs/rust-formatter-guide.md:92-99, 153-159 (macro invocation examples).

What's wrong: `fltk_formatter_main!` is `macro_rules!` with a fixed-order arm
(`parser`, `unparser`, `parse`, `unparse` — crates/fltk-fmt-cli/src/lib.rs:284-289), so the
keys are positional despite the keyword labels; reordering them fails to match. The guide
always shows the correct order but never states the order is mandatory.

Consequence: A consumer who reorders the keys (reasonably assuming they are named/optional)
gets a confusing macro-match error rather than a clear "wrong order" signal.

Fix: One line noting the four keys must appear in the order shown.
