# Design: Standalone Rust formatter binary for `.fltkg` files (`fltkfmt`)

Requirements: `docs/workflow/2026-06-27-rust-fltkfmt/requirements.md`
Exploration: `exploration-fmt.md`, `exploration-codegen.md`, `exploration-crates.md` (same dir)

## 1. Root cause / context

The Rust unparser generator landed in commit 6f975eb. The "proof of life" the user
wants is a pure-Rust binary that formats `.fltkg` files end to end — parse with a
generated Rust parser, hand the CST to a generated Rust unparser, render — with zero
Python, PyO3, or GIL involvement.

Everything needed already exists except three things:

1. **No Rust unparser for the fegen grammar.** `crates/fegen-rust/src/` has `cst.rs`
   and `parser.rs` (generated from `fltk/fegen/fegen.fltkg`) but **no `unparser.rs`**.
   `crates/fegen-rust/src/lib.rs:14-15` declares `mod cst;` / `pub mod parser;` only,
   and the `gencode` Makefile target (`Makefile:247-311`) has no `gen-rust-unparser`
   step for `fegen.fltkg`. The format spec the Python formatter already uses lives at
   `fltk/fegen/fegen.fltkfmt`.

2. **No binary target anywhere.** Every Rust artifact in the repo is an `rlib` or
   `cdylib`; no crate defines `[[bin]]` (`exploration-crates.md` §"Summary").

3. **No reuse scaffolding.** There is no macro/generic/library that turns
   `(grammar crate, fltkfmt)` into a formatter binary. The only parameterization point
   today is the Python `gen-rust-unparser` CLI, which bakes the `FormatterConfig` into
   the generated `Unparser` at generation time (`fltk/fegen/genparser.py:470-580`).
   There is therefore nothing to be *runtime-generic over* at the Rust type level: each
   grammar yields its own concrete `Parser`/`Unparser` with grammar-specific inherent
   methods (`requirements.md` §"Where this is in tension").

The exact pure-Rust pipeline the binary needs is already proven in
`tests/rust_parser_fixture/src/native_tests.rs:1001-1037`:

```rust
let mut parser = Parser::new(src, None, true);          // capture_trivia = true
let parsed = parser.apply__parse_<rule>(0).unwrap();
let guard = parsed.result.read();                       // RwLockReadGuard<Node>
let unparsed = Unparser::new().unparse_<rule>(&*guard).unwrap();
let resolved = resolve_spacing_specs(unparsed.doc());
Renderer::new(RendererConfig { indent_width, max_width }).render(&resolved)
```

The runtime crates the generated code links against are pure Rust: `fltk-cst-core`
(used `default-features = false`, no pyo3), `fltk-parser-core` (never links pyo3),
`fltk-unparser-core` (no deps at all) — see `exploration-crates.md` §"Runtime crates".

The reuse boundary is fixed by the architecture: **grammar-independent CLI scaffolding**
(arg parsing, file/stdin I/O, check/in-place modes, exit codes, error reporting) on one
side; **grammar-specific calls** (`Parser::new`, `apply__parse_<rule>`, `unparse_<rule>`,
the crate deps) on the other.

## 2. Proposed approach

Build the reuse scaffolding **first**, then use it to produce the fegen formatter as its
first consumer — the path the user explicitly prefers (`requirements.md`
§"bonus deliverable"). Three pieces of work:

### 2.1 Generate the fegen Rust unparser and wire it in

- **New generated file** `crates/fegen-rust/src/unparser.rs`, produced by
  `gen-rust-unparser` from `fltk/fegen/fegen.fltkg` with
  `--format-config fltk/fegen/fegen.fltkfmt`. The fegen format spec is thereby baked in
  at generation time; the start rule is `grammar` (`fegen.fltkg:2`), so the entry method
  is `unparse_grammar(&cst::Grammar) -> Option<UnparseResult>`.

- **`crates/fegen-rust/src/lib.rs`**: add `pub mod unparser;` (the binary's macro names
  `fegen_rust_cst::unparser::Unparser`, so the module must be public), and — under
  `#[cfg(feature = "python")]` — register the unparser submodule
  (`register_submodule(m, "unparser", unparser::register_classes)?;`), mirroring
  `tests/rust_parser_fixture/src/lib.rs:19`. Registering it keeps the existing Python
  extension build (`make build-fegen-rust-cst`, default features) warning-clean, since
  the python-gated `register_classes` in the new file would otherwise be dead code.
  `mod cst;` **stays private**: the generated `unparser.rs` reaches the CST via
  `use super::cst;` (within-crate; a private `mod cst` is visible to sibling modules — see
  `tests/rust_parser_fixture/src/unparser.rs:9`), and the binary's macro names no `cst::`
  path — it holds CST values only through type inference (`let parsed =
  parser.apply__parse_grammar(0); … &*guard`). This mirrors the crate today, which already
  compiles clean under `cargo clippy --manifest-path crates/fegen-rust/Cargo.toml
  --no-default-features -- -D warnings` with `mod cst;` private while `pub mod parser;`
  exposes `apply__parse_grammar -> …Shared<cst::Grammar>` (verified; no
  `private_interfaces` allow is needed). Widening `cst` to `pub` is unnecessary and would
  expand `fegen-rust-cst`'s public Rust surface for no reason.

- **`crates/fegen-rust/Cargo.toml`**: add
  `fltk-unparser-core = { path = "../fltk-unparser-core" }` to `[dependencies]`
  (unparser.rs references `fltk_unparser_core::*`; current deps at lines 21-24 lack it).

- **`Makefile` `gencode`**: add a `gen-rust-unparser` step modeled on the fixture step
  (`Makefile:293-296`):
  ```
  $(MAKE) gen-rust-unparser GRAMMAR=fltk/fegen/fegen.fltkg \
      RS_OUT=crates/fegen-rust/src/unparser.rs \
      EXTRA_ARGS="--format-config fltk/fegen/fegen.fltkfmt \
                  --protocol-module fltk.fegen.fltk_cst_protocol \
                  --pyi-output fltk/_stubs/fegen_rust_cst/unparser.pyi"
  ```
  `fltk.fegen.fltk_cst_protocol` is the same protocol module the fegen `cst.rs`
  generation already uses (`Makefile:279`), so the emitted `.pyi` type-checks under the
  existing `fltk/_stubs` pyright setup. Because the spec is baked at generation time, the
  committed `unparser.rs` must be regenerated whenever `fegen.fltkfmt` changes; `make
  gencode` + `git diff` is the existing drift guard.

### 2.2 Reusable CLI scaffolding crate: `fltk-fmt-cli`

New crate `crates/fltk-fmt-cli/` (`rlib`, no pyo3), added as a member of the **root**
Cargo workspace alongside the other runtime/scaffolding crates — it is shared,
publishable infrastructure that downstream formatter crates depend on, unlike the
standalone concrete grammar/fixture crates. Dependencies: `fltk-unparser-core` (for
`RendererConfig`) and `clap` (derive feature) for argument parsing.

It owns everything grammar-independent:

- **`FmtArgs`** — a `clap`-derive struct exposing the full CLI surface from
  `requirements.md` §"primary deliverable":
  - positional `files: Vec<PathBuf>` (zero or more; `-` or empty ⇒ stdin)
  - `--check` (report-only; never writes; non-zero exit if any input would change)
  - `--in-place` (rewrite each file in place; requires ≥1 file arg)
  - `--width WIDTH` / `-w` (default **80**)
  - `--indent N` / `-i` (default **2** — the `.fltkg` convention used in `fegen.fltkg`
    and the Python `unparse_cli.py:38` default; note this differs from
    `RendererConfig`'s own default of 4)
  - `--output PATH` / `-o` (write to a file instead of stdout; single input only)
  - clap supplies `--help`/`--version`.

- **`pub fn run_main<F>(format_fn: F) -> std::process::ExitCode`** where
  `F: Fn(&str, Option<&str>, RendererConfig) -> Result<String, String>`. It parses
  `FmtArgs`, validates flag combinations, reads each input, calls `format_fn(source,
  filename, cfg)` (`filename` is `None` for stdin), then dispatches on mode. The closure
  returns the formatted string or an error message. When the closure returns `Err`,
  `run_main` prepends the input path to the message before writing it to stderr — the
  parser's `error_message()` carries only line/col/caret, never the filename (§3), so the
  CLI scaffolding, which owns the path, is what associates an error with its file. All
  I/O, mode logic, error-path filename prefixing, and exit codes live in the library.

- **`pub fn fully_consumed(src: &str, pos: i64) -> bool`** — shared helper deciding
  whether a parse covered the input: `true` if `pos` reaches the char count, or the
  unconsumed char suffix is entirely whitespace (see §3). Char-index aware
  (`src.chars().skip(pos as usize).all(char::is_whitespace)`), because
  `TerminalSource`/`Span` positions are char indices, not byte indices.

- **`#[macro_export] macro_rules! fltk_formatter_main`** — the "easy reuse" surface the
  user asked for. A consumer writes one invocation naming the concrete types and methods:
  ```rust
  fltk_fmt_cli::fltk_formatter_main! {
      parser:  fegen_rust_cst::parser::Parser,
      unparser: fegen_rust_cst::unparser::Unparser,
      parse:   apply__parse_grammar,
      unparse: unparse_grammar,
  }
  ```
  It expands to a `fn main()` that calls `run_main` with a closure performing the proven
  pipeline (§1) for the named start rule: `Parser::new(src, filename, true)` →
  `parser.$parse(0)`; if `None`, `Err(parser.error_message())`; else check
  `fltk_fmt_cli::fully_consumed`; `parsed.result.read()` →
  `Unparser::new().$unparse(&*guard)` (`None` ⇒ `Err` internal error) →
  `resolve_spacing_specs(unparsed.doc())` → `Renderer::new(cfg).render(&resolved)`. The
  macro takes method *identifiers* (not a rule string), so no `paste`/`concat_idents`
  dependency is needed. The macro is sugar over `run_main`; `run_main` is independently
  usable for consumers who want to hand-write the closure.

  Why a macro and not a trait or pure generic: the generated `Parser`/`Unparser` expose
  grammar-specific *inherent* methods and implement no shared trait, and the start-rule
  method name varies per grammar; a macro is the minimal-ceremony way to bind those names
  at the call site (`requirements.md` §"Where this is in tension"). A trait-based
  alternative would require a hand-written per-grammar impl that is strictly more
  boilerplate than the macro invocation.

### 2.3 The fegen formatter binary: `fltkfmt`

New **standalone** crate `crates/fltkfmt/` (its own `[workspace]`, like `fegen-rust` and
the fixtures, so the pyo3-defaulting `fegen-rust-cst` crate stays out of the root
workspace). It defines `[[bin]] name = "fltkfmt"`. Dependencies (path):
`fegen-rust-cst { default-features = false }` (pure-Rust rlib, no pyo3),
`fltk-unparser-core`, `fltk-fmt-cli`. `fltk-cst-core`/`fltk-parser-core` come in
transitively via `fegen-rust-cst`; add them explicitly only if a named type requires it
(the macro names neither).

`src/main.rs` is the single `fltk_formatter_main!` invocation from §2.2 — proving the
scaffolding produces a working formatter with near-zero per-grammar code.

- **Makefile / `make check` gating.** `crates/fltkfmt/` is a standalone crate with its own
  `[workspace]`/`Cargo.lock`, so the root `cargo test`/`clippy`/`deny` will not see it; it
  must be gated the way the other standalone crates are — via explicit `--manifest-path`
  lines added to the existing `check-common` steps. The MANDATORY anti-drift rule
  (`Makefile:27-32`) forbids bespoke check steps outside `check-common`, and
  `test-native-parser`/`test-rust-parser-fixture` exist but are **not** run by any check
  target, so they are not a wiring point. Add `--manifest-path crates/fltkfmt/Cargo.toml`
  to: `cargo-test-no-python` (`Makefile:135-140`), `cargo-clippy-no-python` (`-D warnings`,
  `Makefile:142-147`), `check-no-pyo3` (the pyo3-absence proof — required to back the "zero
  Python" claim for the binary, `Makefile:153-170`), and `cargo-deny` (the local-only
  supply-chain lane, `Makefile:176-181`). A convenience `build-fltkfmt`
  (`cd crates/fltkfmt && cargo build --release`) target may be added for manual release
  builds but is **not** a check step.

  `fltk-fmt-cli` is a **root**-workspace member (§2.2), so root
  `cargo-check`/`cargo-test`/`cargo-clippy`/`cargo-deny` already cover it automatically —
  no per-crate target is needed, and a separate `test-fltk-fmt-cli` target would only
  duplicate `cargo-test`. Adding `fltk-fmt-cli` pulls `clap`'s transitive tree into the
  root `cargo deny` check; clap and its tree are MIT/Apache-2.0 (with some Unicode-3.0),
  all within `deny.toml`'s allow-list (`deny.toml:13-18`), and `multiple-versions = "warn"`
  (not `deny`) means version duplication will not fail — but the implementer must run
  `make cargo-deny` after adding clap to confirm no new advisory/license/source violation.

### CLI behavior summary

- Default (no `--check`/`--in-place`): format each input, write to stdout. Multiple files
  ⇒ outputs concatenated in order (gofmt-style); `--output` therefore requires exactly
  one input source.
- `--check`: format in memory, compare byte-for-byte to the original; write nothing.
  Print the path of each file that would change to stderr. Exit `1` if any differ, `0` if
  all match.
- `--in-place`: write each formatted result back to its file; requires ≥1 file argument
  (rejects stdin / `-`).
- Errors (parse failure, unreadable file, non-UTF-8) go to stderr with context; exit
  code `2`. Processing continues across remaining inputs so one bad file does not mask the
  rest; the final exit code reflects the worst outcome (`2` error > `1` check-diff > `0`).
- Conflicting flags (`--in-place` with `--output`, `--in-place` with `--check`,
  `--output` with multiple inputs, `--in-place` with no file) are rejected by `run_main`
  with a usage error to stderr, exit `2`.

## 3. Edge cases / failure modes

- **Trailing whitespace / newline at EOF.** Real `.fltkg` files end in `\n`. Whether
  `apply__parse_grammar` consumes a trailing newline depends on the grammar's trailing
  `,` (ws-allowed) plus trivia capture; it is not guaranteed for all trailing-whitespace
  shapes (extra blank lines, etc.). Requiring `pos == len` would spuriously reject normal
  files. Mitigation: `fully_consumed` (§2.2) accepts a parse whose unconsumed suffix is
  pure whitespace. A non-whitespace remainder is a genuine partial parse ⇒ error. Parity
  with the Python formatter's trailing-whitespace handling is asserted by the test plan.

- **Parse failure.** `parser.apply__parse_<rule>(0)` returns `None`. The macro closure
  returns `Err(parser.error_message())`, which routes through the shared
  `fltk_parser_core::format_error_message` (`crates/fltk-parser-core/src/errors.rs:123-158`)
  to produce a line/col message with a caret. `format_error_message` does **not** read
  `SourceText.filename` — the filename passed to `Parser::new` lands in the span's source
  bookkeeping but never appears in `error_message()` output. `run_main` owns the input path
  and is what surfaces it: when it writes an `Err` to stderr it prepends the file path (e.g.
  `"<path>: "`), so the CLI's error output names the file plus the line/col/caret. Exit `2`.

- **Unparser returns `None`.** Indicates a CST/unparser shape mismatch — should not
  happen for a successfully parsed tree, but the macro maps it to an explicit internal
  error message rather than a panic. Exit `2`.

- **Empty input.** `grammar := , rule+` requires ≥1 rule; an empty file is an invalid
  `.fltkg` and surfaces as a parse error. Documented, not special-cased.

- **Non-UTF-8 input.** Read fails (Rust strings are UTF-8); reported as a read error,
  exit `2`. Char-indexed positions assume UTF-8 throughout.

- **`--in-place` write atomicity.** A formatter that truncates then fails mid-write
  corrupts the source. Write to a temp file in the same directory and rename over the
  original, so a crash leaves the original intact.

- **`--in-place` on an unchanged file.** Still safe to rewrite identical bytes; no
  special handling required, but the rename-based write avoids needless churn only if we
  skip writing when output == input (minor optimization, optional).

- **Idempotency.** Formatting already-formatted output must be a no-op (`format(format(x))
  == format(x)`); this is the core correctness invariant and a test (§4).

- **Concurrency / `Send`.** `fltk_unparser_core::Doc` uses `Rc` internally
  (`exploration-codegen.md` §8), so the render stage is single-threaded. The CLI is
  sequential per file; this is not a constraint for the binary. No threading is
  introduced.

## 4. Test plan

After this change the following tests exist:

- **`fltk-fmt-cli` unit/integration tests** (pure Rust, no grammar): drive `run_main`
  with a stub `format_fn` (e.g. identity, or one that uppercases) to verify, without any
  parser:
  - default mode writes to stdout; multiple files concatenate in order;
  - `--check` exits `1` when the stub would change input, `0` when identity, and writes
    nothing;
  - `--in-place` rewrites files, rejects stdin, and is atomic (temp+rename);
  - flag-conflict rejections (`--in-place`+`--output`, `--output`+multi-input,
    `--in-place`+no-file, `--in-place`+`--check`) exit `2` with a usage message;
  - read error on a missing file ⇒ exit `2`, other inputs still processed.
  - `fully_consumed` unit tests: exact length, trailing-whitespace suffix (accept),
    trailing non-whitespace (reject), char-vs-byte index correctness with multibyte input.

- **`fltkfmt` integration tests** (`crates/fltkfmt/tests/`, pure Rust):
  - **Idempotency**: format a corpus of `.fltkg` snippets (including `fegen.fltkg`
    itself and the test-data grammars), then format the result again; assert the second
    pass is byte-identical to the first.
  - **Golden / canonical**: assert formatting the canonical `fltk/fegen/fegen.fltkg`
    produces a stable expected output at width 80 / indent 2 (regenerate-able golden).
  - **Trailing-newline robustness**: same input with and without a trailing newline (and
    with trailing blank lines) formats successfully to the same result.
  - **Parse-error path**: malformed input yields a non-zero result and a message
    mentioning the (synthetic) filename and a line/col.

- **Cross-backend parity** (recommended, ties into existing infra): a pytest mirroring
  `tests/test_rust_unparser_parity_fixture.py` that, for a `.fltkg` corpus, compares the
  `fltkfmt` binary's output to the Python `fltk.unparse_cli fegen.fltkg fegen.fltkfmt`
  output at matching `--width`/`--indent`, asserting byte equality. This is the strongest
  guarantee that the pure-Rust formatter matches the established Python formatter,
  including trailing-whitespace handling, and guards against future drift.

- **Drift guard**: `make gencode` followed by `git diff --stat` must show no changes to
  the committed `crates/fegen-rust/src/unparser.rs` / `unparser.pyi` (the existing
  cheat-detection convention, `Makefile:244-246`).

## 5. Open questions

None require user input. Two deliberate defaults are flagged for visibility (both
changeable):

- Default `--indent` is **2** — the `.fltkg` source convention (continuation lines in
  `fegen.fltkg` are 2-space indented) and the Python `unparse_cli.py:38` reference
  default. `RendererConfig`'s own default is 4; the CLI overrides it to 2.
- Multiple files in default (stdout) mode concatenate their formatted outputs in order
  (gofmt convention); `--output` is therefore restricted to a single input source.
