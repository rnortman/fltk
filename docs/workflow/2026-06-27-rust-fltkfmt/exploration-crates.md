# Crate Layout & Generated-Rust Placement — exploration-crates

## Cargo workspace layout

**Root workspace** (`/home/rnortman/src/fltk/Cargo.toml`, lines 1–2):
```
[workspace]
members = [".", "crates/fltk-cst-core", "crates/fltk-parser-core", "crates/fltk-unparser-core"]
```
The root package `fltk-native` (lib name `fltk_native`, `crate-type = ["cdylib"]`) is the maturin
extension that ships to PyPI.  It is **the only cdylib in the workspace**; the three `crates/`
members are all `rlib`.

**Standalone crates** (each has its own `[workspace]` declaration, deliberately excluded from the
root workspace, and its own `Cargo.lock`):

| Path | Package | crate-type | Purpose |
|------|---------|------------|---------|
| `crates/fegen-rust/` | `fegen-rust-cst` | `cdylib` + `rlib` | Rust CST + parser for `fegen.fltkg`; maturin-built as `fegen_rust_cst` |
| `tests/rust_cst_fixture/` | `phase4-roundtrip-cst` | `cdylib` | Phase-4 roundtrip test extension |
| `tests/rust_parser_fixture/` | `rust-parser-fixture` | `rlib` + `cdylib` | Fixture CST + parser + unparser; maturin-built as `rust_parser_fixture` |
| `tests/rust_poc_cst/` | `poc-cst` | `cdylib` + `rlib` | PoC CST fixture |

`tests/rust_cst_fegen/` exists on disk but currently contains only a `target/` directory — no `src/`
or `Cargo.toml` in the main branch.

## Runtime crates the generated code links against

All three are `rlib`; none link pyo3 unconditionally:

### `fltk-cst-core` (`crates/fltk-cst-core/Cargo.toml`)
- `crate-type = ["rlib"]`
- pyo3 optional behind `python` feature (default-on; downstream pure-Rust consumers use
  `default-features = false`)
- Exports: `Span`, `SourceText`, `LineColPos`, `Shared`, `CstError`, `resolve_line_col`
  (`src/lib.rs` lines 4–18)

### `fltk-parser-core` (`crates/fltk-parser-core/Cargo.toml`)
- `crate-type = ["rlib"]`; **never links pyo3** (structural absence, not a disabled feature)
- Depends on `fltk-cst-core` (no-default-features) and `regex-automata 0.4`
- Re-exports `regex_automata` so generated parsers can use
  `fltk_parser_core::regex_automata::meta::Regex` without a separate dep (`src/lib.rs` line 23)
- Exports: `errors`, `memo`, `terminalsrc` modules; `escape_control_chars`, `ErrorTracker`,
  `ParseContext`, `TokenType`, `Cache`, `apply`, `ApplyResult`, `PackratState`, etc.
  (`src/lib.rs` lines 17–27)

### `fltk-unparser-core` (`crates/fltk-unparser-core/Cargo.toml`)
- `crate-type = ["rlib"]`; **never links pyo3**, **no `fltk-cst-core` dep**
- Operates on `Doc`, not CST spans. Terminal text is extracted in generated code and handed
  in as `Doc::Text(String)`.
- Exports: `DocAccumulator`, `Doc` and all combinator functions (`text`, `group`, `nest`, …),
  `Renderer`, `RendererConfig`, `resolve_spacing_specs`, `UnparseResult`
  (`src/lib.rs` lines 15–28)
- No dependencies at all (empty `[dependencies]` in `Cargo.toml`)

## How generated Rust code is placed into crates

**No `build.rs`, no OUT_DIR pattern.** Generated `.rs` files are produced by Python CLI commands
and **committed to the repository**. The workflow:

1. Run `make gen-rust-cst GRAMMAR=… RS_OUT=…` →
   `uv run python -m fltk.fegen.genparser gen-rust-cst …` (Makefile lines 215–216)
2. Run `make gen-rust-parser GRAMMAR=… RS_OUT=…` → calls `gsm2parser_rs.RustParserGenerator`
   (Makefile lines 219–221)
3. Run `make gen-rust-unparser GRAMMAR=… RS_OUT=…` → calls `gsm2unparser_rs.RustUnparserGenerator`
   (Makefile lines 223–226)
4. Run `make fix` to normalize formatting (ruff check --fix + ruff format)
5. Commit the result

The Python generators live at:
- `fltk/fegen/gsm2tree_rs.py` — CST generator (`RustCstGenerator`)
- `fltk/fegen/gsm2parser_rs.py` — parser generator (`RustParserGenerator`)
- `fltk/unparse/gsm2unparser_rs.py` — unparser generator (`RustUnparserGenerator`)

**CLI entry point**: `fltk/fegen/genparser.py` (typer app). The `gen-rust-unparser` subcommand
is at line 470. Key parameter: `--format-config PATH` accepts a `.fltkfmt` file whose spacing/
anchor/disposition decisions are **baked into the generated unparser at generation time**
(`genparser.py` lines 481–490, `gsm2unparser_rs.py` line 44–52).

**`RustUnparserGenerator.__init__`** signature (`gsm2unparser_rs.py` lines 41–52):
```python
def __init__(
    self,
    grammar: gsm.Grammar,
    formatter_config: FormatterConfig | None = None,
    ...
):
    self._formatter_config = formatter_config or FormatterConfig()
```

A downstream consumer compiles a generated parser+unparser by:
- Creating a new crate (standalone `[workspace]` to avoid the root workspace)
- Depending on `fltk-cst-core` (no-default-features for pure Rust), `fltk-parser-core`,
  `fltk-unparser-core` via path or crates.io
- Including the generated `cst.rs`, `parser.rs`, `unparser.rs` as `mod` declarations in `lib.rs`
- Building with `cargo build` or `maturin develop --features extension-module` for the Python
  extension variant

See `tests/rust_parser_fixture/Cargo.toml` for the canonical template:
```toml
[dependencies]
fltk-cst-core = { path = "../../crates/fltk-cst-core", default-features = false }
fltk-parser-core = { path = "../../crates/fltk-parser-core" }
fltk-unparser-core = { path = "../../crates/fltk-unparser-core" }
pyo3 = { version = "0.29", features = ["abi3-py310"], optional = true }
```
and `tests/rust_parser_fixture/src/lib.rs` for the module wiring pattern.

## Self-hosting bootstrap for `fegen.fltkg`

**What exists in `crates/fegen-rust/src/`**:
- `cst.rs` — generated Rust CST for `fegen.fltkg`
  (regenerated via `make gen-rust-cst GRAMMAR=fltk/fegen/fegen.fltkg RS_OUT=crates/fegen-rust/src/cst.rs`;
  Makefile line 278)
- `parser.rs` — generated Rust parser for `fegen.fltkg`
  (regenerated via `make build-fegen-rust-parser`; Makefile lines 229–231)
- `lib.rs`, `native_parser_tests.rs`

**What does NOT exist in `crates/fegen-rust/src/`**:
- **No `unparser.rs`** — the Rust unparser for `fegen.fltkg` has not been generated yet.

**`fegen.fltkfmt` exists** at `fltk/fegen/fegen.fltkfmt` (non-empty; defines trivia preservation,
blank-line handling, separator spacing, and rule-level group/nest/anchor directives). It is NOT yet
wired into any `make gencode` step for generating a Rust unparser.

The Makefile `gencode` target (lines 247–311) regenerates `cst.rs` and `parser.rs` for
`crates/fegen-rust` but has no `gen-rust-unparser` invocation for `fegen.fltkg`.

**Native parser tests** for the fegen grammar exist at
`crates/fegen-rust/src/native_parser_tests.rs` and run via `make test-native-parser`
(Makefile line 235: `cd crates/fegen-rust && cargo test --no-default-features`).

## Pure-Rust parse+unparse+render pipeline (no GIL)

The fixture at `tests/rust_parser_fixture/src/native_tests.rs` lines 987–1038 demonstrates
the full pure-Rust pipeline:

```rust
use crate::unparser::Unparser;
use fltk_unparser_core::{resolve_spacing_specs, Renderer, RendererConfig};

// 1. Parse
let mut parser = Parser::new(src, None, true);
let parsed = parser.apply__parse_num(0).unwrap();
// 2. Unparse → Doc tree
let guard = parsed.result.read();
let unparsed = Unparser::new().unparse_num(&*guard).unwrap();
// 3. Resolve spacing specs
let resolved = resolve_spacing_specs(unparsed.doc());
// 4. Render to String
Renderer::new(RendererConfig { indent_width: 4, max_width: 80 }).render(&resolved)
```

This is the exact pipeline a standalone `[[bin]]` formatter would use.

## Existing patterns for parameterized codegen

**No macros, no generics, no `build.rs` patterns exist** in the current codebase for turning
`(grammar_file, fltkfmt_file)` into a formatter. The only existing pattern is the Python CLI
(`genparser.py gen-rust-unparser --format-config grammar.fltkfmt`) that produces a committed `.rs`
file. That `.rs` file's `Unparser` struct has the `FormatterConfig` **baked in** at generation time
— there is no runtime `FormatterConfig` argument.

The `fltk-native` root crate has no `[[bin]]` target; no existing crate in the repo defines a
`[[bin]]` section. All Rust artifacts are `rlib` or `cdylib`.

## Summary of what would be needed for a standalone Rust formatter binary for `fegen.fltkg`

1. Generate `crates/fegen-rust/src/unparser.rs` from `fegen.fltkg` + `fegen.fltkfmt` (one
   `gen-rust-unparser` invocation; not yet wired into `gencode`)
2. Add a new crate (or a `[[bin]]` target in an existing crate) that depends on
   `fltk-cst-core`, `fltk-parser-core`, `fltk-unparser-core`, and the `fegen-rust` crate's
   `cst`/`parser`/`unparser` modules
3. The binary's `main` would: read stdin/file → `Parser::new` → `apply__parse_*` →
   `Unparser::new().unparse_*` → `resolve_spacing_specs` → `Renderer::new(…).render(…)` → stdout

For a **generic** formatter (any grammar), the `.rs` codegen step must be run per grammar at
build-prep time; there is no runtime-generic path. The `Unparser` struct is always a unit struct
with formatting baked in.
