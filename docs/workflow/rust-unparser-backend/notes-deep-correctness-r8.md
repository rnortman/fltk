# Deep correctness review — batch 8 (CLI / LibSpec / Makefile / fixture)

Commit reviewed: 69fa04efa8bdb0524c0b3f9c4a4026da66d0c941 (base 7723f7ec…).
Scope: CLI `gen-rust-unparser`, `gen-rust-lib --unparser`, `LibSpec.standard`,
Makefile wiring, fixture compilation, and the `gsm2unparser_rs` import-split /
`_node_param` / single-variant-let changes carried in this diff.

---

## correctness-1 — `_node_param`'s `\bnode\b` text scan false-matches literal text, emitting an unused `node` parameter

File: `fltk/unparse/gsm2unparser_rs.py:154-166` (`_node_param`), reached from
`:619-625` (`_gen_item_method`) and `:743-749` (`_gen_inner_methods`).

What's wrong: `_node_param` decides whether to name the CST parameter `node` or
`_node` by scanning the *rendered* body text for `re.search(r"\bnode\b", line)`.
But a body that never reads the parameter can still legitimately contain the
substring "node" inside an emitted **string literal**. The required-suppressed
literal path (`_gen_suppressed_item_body`, `:1069-1074`) and the INLINE-literal
path (`_gen_literal_term_body` else-branch, `:923-925`) emit
`acc.add_non_trivia(fltk_unparser_core::text("<literal>"))` and nothing else —
they do not touch the node. When `<literal>` is the word "node" (or contains it
as a whole word, e.g. `"node "`, `"end node"`), `\bnode\b` matches the quoted
text and `_node_param` returns `"node"`, naming a parameter that the body never
uses.

Why: confirmed empirically against the real generator. A grammar with a required
suppressed literal `%"node"` produces:

```rust
fn unparse_kw__alt0__item0(&self, node: &cst::Kw, pos: usize, acc: DocAccumulator) -> Option<UnparseResult> {
    let acc = acc.add_non_trivia(fltk_unparser_core::text("node"));
    Some(UnparseResult::new(acc, pos))
}
```

`node` is unused. The same `_node_param` correctly yields `_node` for `"("`,
`")"`, `"hello"`, `"render"` — only the literal "node" trips it. Required
suppressed literals are an explicitly supported construct (design §3: "Required
suppressed literals are reconstructed from the literal text").

Consequence: the generated unparser fails to compile under the project's
`cargo clippy … -D warnings` lanes (Makefile `cargo-clippy` :128/:131 and
`cargo-clippy-no-python` :143/:145) via `unused_variables`, for any grammar that
has a required-suppressed (or, under `python -O`, INLINE) literal whose text
contains "node" as a whole word. This directly defeats the stated purpose of
`_node_param` ("keeps the generated unparser warning-clean under `-D warnings`").
The fixture grammar happens to contain no such literal, so `make check` passes
and masks the defect; a downstream grammar (e.g. a graph/AST DSL that suppresses
a `node` keyword) breaks.

Suggested fix: decide the parameter name structurally rather than by text scan —
the call sites already know whether the body reads the node (e.g. thread a
`reads_node: bool` out of `_gen_item_body`/`_gen_term_body`/
`_gen_suppressed_item_body`, set False only for the suppressed-optional /
required-suppressed-literal / INLINE-literal bodies). Failing that, restrict the
scan to non-string-literal tokens.

---

## correctness-2 — `Doc` is imported unconditionally but is unused for grammars that emit no `Doc::` expression

File: `fltk/unparse/gsm2unparser_rs.py:108` (`_gen_header`):
`use fltk_unparser_core::{DocAccumulator, Doc, UnparseResult};`

What's wrong: `Doc` (the bare type) is referenced only by `_doc_to_rust_expr`
output (`Doc::Nil`/`Doc::Line`/`Doc::Nbsp`/`Doc::SoftLine`/`Doc::HardLine{…}`,
`:1582-1591`), which is emitted only when a separator/spacing actually produces a
spacing `Doc`. A grammar with no whitespace separators (all `.`/`NO_WS`) and the
default `FormatterConfig` emits zero `Doc::` references, so `Doc` is imported but
never used. `DocAccumulator`/`UnparseResult` are always used; `Doc` is not.

Why: confirmed empirically — generating the unparser for `r := a:/x/ . b:/y/ ;`
(NO_WS separators, default config) yields a file with no `Doc::` and no bare
`Doc` reference outside the import line. This diverges from the parser backend,
which conditionally emits its potentially-unused imports precisely to stay
`-D warnings`-clean (`gsm2parser_rs.py:309-313`: `OnceLock`/`Regex` imported only
`if self._regex_patterns`). The diff reworked this exact import line to gate the
pipeline types behind `python`, but left `Doc` exposed to the same unused-import
failure mode.

Consequence: generated unparser fails `cargo clippy … -D warnings`
(`unused_imports`) for any separator-less / spacing-less grammar. This batch is
what first subjects generated unparsers to a `-D warnings` compile (new Makefile
`gen-rust-unparser` target + fixture compilation), so the latent issue becomes a
real build break for such downstream grammars. The fixture grammar has WS
separators (emits `Doc::Nil`/`Doc::Line`), so it compiles and masks the defect.

Suggested fix: emit `Doc` in the import only when `_doc_to_rust_expr` was
actually used (track a "doc expr emitted" flag during body generation, as the
parser backend tracks `_regex_patterns`), or add `#[allow(unused_imports)]` to
the `Doc` import line.

---

## Wiring checked, no findings

- `gen-rust-unparser` CLI (`genparser.py:407-475`) mirrors `gen-rust-parser`:
  `_CST_MOD_PATH_RE` validation, `_parse_grammar_raw`, optional
  `parse_format_config_file` (exists, raises `ValueError`/`FileNotFoundError`,
  both caught), `RustUnparserGenerator(...).generate()`, atomic-ish write (no
  partial file on generation error). Catch set `(ValueError, RuntimeError)` is
  sufficient — the unparser generator raises only those.
- `gen-rust-lib --unparser` (`:491-550`): `with_unparser` threads into
  `LibSpec.standard`, appends `Submodule("unparser","unparser")` with the
  shared `register_classes` entry point; correctly ignored under `--no-cst`
  (runtime_only branch). Consistent with cst/parser convention.
- Fixture wiring (`lib.rs`, `Cargo.toml`, `Cargo.lock`) and Makefile `gencode` /
  `gen-rust-unparser` target follow the parser pattern; `unparser::register_classes`
  is `pub use`'d under `#[cfg(feature="python")]` and the registrar call sits in
  the python-gated `#[pymodule]` fn.
- Single-variant irrefutable-let change (`:889-893`, `:987-990`): valid Rust;
  the plain `let Enum::OnlyVariant(x) = …;` is irrefutable for a one-variant enum
  and is the form `clippy::infallible_destructuring_match` recommends. `child_tuple`
  remains bound (`need_tuple=True`) and used. Present and correct in committed fixture.
- Import split (`:108-110`) is correct for the python-on build: root gated
  `use fltk_unparser_core::{Renderer,…}` is referenced via `super::` from
  `python_bindings`, so the root binding is "used"; python-off build drops both
  the gated import and the consuming module.
