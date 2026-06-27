# Implementation log: Standalone Rust formatter binary (`fltkfmt`)

Design: `docs/workflow/2026-06-27-rust-fltkfmt/design.md`
Requirements: `docs/workflow/2026-06-27-rust-fltkfmt/requirements.md`

## Increment 1 — Generate fegen Rust unparser and wire it into `fegen-rust` (§2.1)

Shipped:
- `Makefile:282-290`: added a `gen-rust-unparser` step for `fegen.fltkg` to the `gencode` target (modeled on the fixture step, after `build-fegen-rust-parser`), with `--format-config fltk/fegen/fegen.fltkfmt --protocol-module fltk.fegen.fltk_cst_protocol --pyi-output fltk/_stubs/fegen_rust_cst/unparser.pyi`.
- `crates/fegen-rust/src/unparser.rs`: NEW generated file (the fegen Rust unparser, fegen.fltkfmt baked in), produced by the new gencode step.
- `fltk/_stubs/fegen_rust_cst/unparser.pyi`: NEW generated type stub for the python-feature `unparser` submodule.
- `crates/fegen-rust/src/lib.rs:16`: added `pub mod unparser;`; `:25`: register the unparser submodule under `#[cfg(feature = "python")]`. `mod cst;` stays private (unparser reaches it via `use super::cst;`).
- `crates/fegen-rust/Cargo.toml:25` (+ `Cargo.lock`): added `fltk-unparser-core` path dependency.
- Verified: `cargo clippy --manifest-path crates/fegen-rust/Cargo.toml` clean under both `--no-default-features` and default (python-on) at `-D warnings`; `cargo test --no-default-features` passes (7 tests); pyright 0 errors; `make fix` clean.

Deviations / surprises:
- Generator clippy bug surfaced by fegen's comment trivia. `fltk/unparse/gsm2unparser_rs.py` (`_gen_has_preservable_trivia_method` ~:1446, `_gen_count_newlines_in_trivia_method` ~:1488) emitted `match { Variant => ..., _ => {} }` whenever the trivia child enum has >1 variant. The fixture grammar's `Trivia` is `Span`-only (no wildcard arm), so the design's assumption that the generated unparser is clippy-clean held there but FAILED for fegen (`LineComment`/`BlockComment` variants) under clippy `single_match`. Generated files can't be hand-edited (drift guard), so fixed the generator to emit the `if let` form clippy suggests in the wildcard cases; the `Span`-only path keeps its exhaustive single-arm `match`, so fixture-generated `unparser.rs`/`unparser_default.rs` are byte-identical (confirmed: not in `git diff`).
- `pyproject.toml:120-122`: added `"*.pyi" = ["E501"]` per-file-ignore. The design mandates `--pyi-output` but didn't anticipate that fegen's longer rule names push one-line `...`-bodied stub signatures past 120 chars; ruff's formatter keeps stub methods on one line (typeshed convention) and won't wrap them, so E501 fired on `make fix`/`make check`. The fixture stub passed only by short-name luck.

Out-of-scope observation (NOT fixed, NOT staged):
- `src/lib.rs` has pre-existing drift from generator output: `make gencode` (via `gen-rust-lib`) drops a `LineColPos` registration that the committed file still carries (likely from earlier span-line-col-api work). Reverted to committed state; outside §2.1 scope.

## Increment 2 — Create `fltk-fmt-cli` crate with `fully_consumed` helper (§2.2)

Shipped (smallest standalone piece of §2.2; the crate must exist before any of its other
items can land, so this increment creates the crate skeleton and the one pure,
dependency-free helper):
- `crates/fltk-fmt-cli/Cargo.toml`: NEW crate (rlib, `fltk_fmt_cli`, no deps, no pyo3,
  `license = "MIT"`).
- `crates/fltk-fmt-cli/src/lib.rs:18-23`: `pub fn fully_consumed(src: &str, pos: i64) -> bool`
  per §2.2 — char-index aware (`src.chars().skip(pos as usize).all(char::is_whitespace)`);
  true if `pos` reaches the char count or the unconsumed char suffix is all whitespace.
  Guards `pos < 0` (returns false) to avoid an `as usize` wraparound on a negative index.
- `crates/fltk-fmt-cli/src/lib.rs:25-89`: 5 unit tests per §4 — exact length, trailing
  whitespace suffix (accept), trailing non-whitespace (reject), char-vs-byte index
  correctness with multibyte input, multibyte whitespace suffix. All pass.
- `Cargo.toml:2` (+ `Cargo.lock`): added `crates/fltk-fmt-cli` to root workspace members,
  so root `cargo-check`/`cargo-test`/`cargo-clippy`/`cargo-deny` cover it automatically
  (§2.3).
- Verified: `cargo test -p fltk-fmt-cli` (5 pass), `cargo clippy -p fltk-fmt-cli -- -D warnings`
  clean, `cargo fmt -p fltk-fmt-cli -- --check` clean.

## Increment 3 — `FmtArgs` clap-derive CLI struct (§2.2)

Shipped (smallest standalone piece of remaining §2.2; `run_main` and the
`fltk_formatter_main!` macro both build on this struct, so the arg surface lands first):
- `crates/fltk-fmt-cli/Cargo.toml:15`: added `clap = { version = "4", features = ["derive"] }`
  to `[dependencies]` (+ `Cargo.lock`).
- `crates/fltk-fmt-cli/src/lib.rs:9-49`: added `pub struct FmtArgs` (clap
  `#[derive(Parser)]`, `#[command(version, about)]`) with the full §2.2 CLI surface:
  positional `files: Vec<PathBuf>`, `--check`, `--in-place`, `--width`/`-w` (default 80),
  `--indent`/`-i` (default 2), `--output`/`-o: Option<PathBuf>`. clap supplies
  `--help`/`--version`. `i64`-typed `fully_consumed` left as-is; widths are `usize`.
- `crates/fltk-fmt-cli/src/lib.rs:148-209`: 5 new unit tests (defaults; positional files;
  combined flags+dimensions; long `--width`/`--indent`; unknown-flag rejection). All pass
  (10 total in crate).
- Verified: `cargo test -p fltk-fmt-cli` (10 pass), `cargo clippy -p fltk-fmt-cli
  --all-targets -- -D warnings` clean, `cargo fmt -p fltk-fmt-cli -- --check` clean.
- `make cargo-deny`: root manifest (now pulling clap's transitive tree) passes
  advisories/bans/licenses/sources; clap tree is MIT/Apache-2.0 within `deny.toml`'s
  allow-list, no new violations.

## Increment 4 — `run_main` CLI driver in `fltk-fmt-cli` (§2.2)

Shipped (smallest standalone remaining piece of §2.2; the `fltk_formatter_main!` macro is
sugar over `run_main`, so the driver lands before the macro):
- `crates/fltk-fmt-cli/Cargo.toml:16` (+ `Cargo.lock`): added `fltk-unparser-core` path dep
  (needed for `RendererConfig` in the `run_main`/`format_fn` signature).
- `crates/fltk-fmt-cli/src/lib.rs:162-172`: `pub fn run_main<F>(format_fn: F) -> ExitCode`
  where `F: Fn(&str, Option<&str>, RendererConfig) -> Result<String, String>` — parses
  `FmtArgs`, locks real stdin/stdout/stderr, delegates to `run_inner`, maps the `u8` to
  `ExitCode`.
- `crates/fltk-fmt-cli/src/lib.rs:181-...`: `fn run_inner` — the testable core with injected
  I/O streams. Validates flag combos, builds the ordered source list (no files / `-` ⇒
  stdin), reads each input, calls `format_fn` (filename `None` for stdin), and dispatches on
  mode: default→stdout (multi-file concatenates in order), `--check`→compare + report path to
  stderr (writes nothing), `--in-place`→atomic write, `--output`→write file. Prepends the
  input display path to `Err`/read/write messages. Continues across inputs; returns worst-of
  exit code (2 error > 1 check-diff > 0).
- `crates/fltk-fmt-cli/src/lib.rs:87-113`: `fn validate` — rejects `--in-place`+`--output`,
  `--in-place`+`--check`, `--in-place`+no-file (and `--in-place`+`-`), `--output`+multi-input
  (exit 2, usage message to stderr).
- `crates/fltk-fmt-cli/src/lib.rs:118-148`: `fn write_atomic` — sibling temp file
  (`.<name>.fltkfmt.tmp.<pid>`) + rename over target; removes temp on failure (design §3).
  No `tempfile` crate dep introduced.
- `crates/fltk-fmt-cli/src/lib.rs` test module: 13 new `run_inner` integration tests driven
  by stub `format_fn`s (uppercase / identity / fail) per §4 — default-stdout, multi-file
  concatenation, `--check` exit 1 vs 0 (writes nothing, file untouched), `--in-place` rewrite
  + no-leftover-temp, all four flag-conflict rejections + stdin-`-` rejection, `--output` to
  file, missing-file read error (exit 2, other input still processed), format-error path
  (exit 2, filename-prefixed message). 25 tests pass.
- Verified: `cargo test -p fltk-fmt-cli` (25 pass), `cargo clippy -p fltk-fmt-cli
  --all-targets -- -D warnings` clean, `cargo fmt -p fltk-fmt-cli -- --check` clean.

Deviation: design says tests "drive `run_main`", but `run_main` reads real env argv and
locks the real stdio streams, so it is not in-process testable. Added a private `run_inner`
seam carrying identical logic with injected `&mut dyn Read`/`Write` streams and a `u8`
return (`ExitCode` is not comparable); `run_main` is the thin env+stdio wrapper. Tests
target `run_inner`. Behavior is unchanged; this is a standard testability seam.

## Increment 5 — `fltk_formatter_main!` macro in `fltk-fmt-cli` (§2.2)

Shipped (smallest standalone remaining piece of §2.2; the macro is the last §2.2 item and is
pure sugar over the already-landed `run_main`):
- `crates/fltk-fmt-cli/src/lib.rs:16-20`: changed the `fltk_unparser_core` import from a plain
  `use RendererConfig` to `pub use {resolve_spacing_specs, Renderer, RendererConfig}` so the
  macro can name the render API through `$crate` (a consumer then needn't name the
  `fltk-unparser-core` crate itself). `RendererConfig` is still used unqualified by
  `run_inner`; the other two re-exports are used only by the macro expansion (`pub use` is not
  flagged unused).
- `crates/fltk-fmt-cli/src/lib.rs:175-241`: added `#[macro_export] macro_rules! fltk_formatter_main`
  with the `parser:`/`unparser:` `:path` and `parse:`/`unparse:` `:ident` matcher (trailing
  comma allowed). Expands to `fn main() -> ExitCode` calling `$crate::run_main` with a closure
  running the proven pipeline (§1/§2.2): `<$parser>::new(src, filename, true)` →
  `parser.$parse(0)` (`None` ⇒ `Err(parser.error_message())`); `$crate::fully_consumed(src,
  parsed.pos)` check (partial parse ⇒ `Err(error_message())`); `parsed.result.read()` →
  `<$unparser>::new().$unparse(&*guard)` (`None` ⇒ `Err` internal-error string) →
  `$crate::resolve_spacing_specs(unparsed.doc())` → `$crate::Renderer::new(cfg).render(&resolved)`.
  Fully path-qualified (`::core`/`::std`/`$crate`) for hygiene.
- Verified: `cargo build/clippy --all-targets -D warnings/fmt --check` all clean for
  `fltk-fmt-cli`; `cargo test -p fltk-fmt-cli` 25 pass (the rustdoc example is `ignore`d). The
  macro body is only type-checked when expanded in a consumer; the `fltkfmt` binary crate that
  invokes it (and exercises end-to-end) lands in a later increment per §2.3.

Deviation: design §2.2 says the macro "names `fegen_rust_cst::unparser::Unparser`" etc. and
references `resolve_spacing_specs`/`Renderer` (from `fltk-unparser-core`). To avoid forcing
each consumer to also name `fltk-unparser-core` directly, the macro reaches those render-API
items via `$crate::` re-exports rather than a bare `fltk_unparser_core::` path. Behavior is
identical; this only narrows the consumer's required dependency surface.

## Increment 6 — Create the `fltkfmt` standalone binary crate (§2.3)

Shipped (smallest standalone piece of §2.3; the binary must exist before its integration
tests or check-gating can land):
- `crates/fltkfmt/Cargo.toml`: NEW standalone crate with its own `[workspace]` (excluded from
  the root workspace, like `fegen-rust`/fixtures, because `fegen-rust-cst`'s default features
  pull pyo3). Declares `[[bin]] name = "fltkfmt"` and the three §2.3 path deps:
  `fegen-rust-cst { default-features = false }` (pure-Rust, no pyo3), `fltk-unparser-core`,
  `fltk-fmt-cli`. `fltk-cst-core`/`fltk-parser-core` arrive transitively.
- `crates/fltkfmt/src/main.rs`: the single `fltk_fmt_cli::fltk_formatter_main!` invocation
  naming `fegen_rust_cst::parser::Parser` / `fegen_rust_cst::unparser::Unparser` and the
  start-rule (`grammar`) methods `apply__parse_grammar` / `unparse_grammar` — proving the
  scaffolding yields a working formatter with near-zero per-grammar code.
- `crates/fltkfmt/Cargo.lock`: NEW (committed; standalone-crate lockfiles are tracked in this
  repo, e.g. `crates/fegen-rust/Cargo.lock`).
- Verified: `cargo build --release` succeeds; `cargo clippy --all-targets -- -D warnings`
  clean; `cargo fmt -- --check` clean. End-to-end smoke test: `fltkfmt fltk/fegen/fegen.fltkg`
  formats to stdout, exit 0 (pure-Rust parse → unparse → resolve → render, zero Python).

Note: §2.3's Makefile check-gating (`--manifest-path` lines into `check-common`), the
`crates/fltkfmt/tests/` integration tests, and the cross-backend parity pytest are not in this
increment.

## Increment 7 — Wire `crates/fltkfmt` into `make check` gating (§2.3)

Shipped (one semantic change: gate the standalone `fltkfmt` binary crate into the precommit
`check-common` pipeline, via explicit `--manifest-path` lines mirroring the other standalone
crates — §2.3):
- `Makefile:141` (`cargo-test-no-python`): added `cargo test -q --manifest-path
  crates/fltkfmt/Cargo.toml` (binary crate has no tests yet — integration tests deferred under
  TODO(fltkfmt-integration-tests) — so this compiles the crate and runs 0 tests; it still gates
  build breakage).
- `Makefile:149` (`cargo-clippy-no-python`): added `cargo clippy -q --manifest-path
  crates/fltkfmt/Cargo.toml --all-targets -- -D warnings`.
- `Makefile:170-172` (`check-no-pyo3`): added the fltkfmt graph assertion — positive control
  `fltk-parser-core` (arrives transitively via `fegen-rust-cst { default-features = false }`)
  then the pyo3-absence check, backing the "zero Python" claim for the binary. fltkfmt's own
  `[workspace]` means default-features (no python feature on the binary itself); no
  `--no-default-features` flag needed (unlike the fegen line, whose own defaults are python-on).
- `Makefile:184` (`cargo-deny`): added `cargo deny --manifest-path crates/fltkfmt/Cargo.toml
  check --config deny.toml`.
- Verified: all four lanes pass — `make cargo-test-no-python` (fltkfmt: 0 tests, ok),
  `make cargo-clippy-no-python` (clean, `-D warnings`), `make check-no-pyo3` ("pyo3 absent from
  python-off graphs"), `make cargo-deny` (fltkfmt manifest: advisories/bans/licenses/sources ok;
  only benign "license-not-encountered" allowance warnings, no violations).
- Per §2.3 the optional `build-fltkfmt` convenience target is "not a check step"; not added
  (manual release builds use `cd crates/fltkfmt && cargo build --release`).

## Increment 8 — Cross-backend parity pytest (§4)

Shipped (single semantic change: the last §4 test-plan item that was neither implemented
nor deferred under TODO(fltkfmt-integration-tests)):
- `tests/test_fltkfmt_parity.py`: NEW pytest mirroring `tests/test_rust_unparser_parity_fixture.py`.
  For a pinned corpus of all 8 real `.fltkg` files (the canonical `fegen`/`bootstrap`/`fltk`/`regex`
  grammars + the 4 `test_data` grammars) × 2 render configs (`w80i2` flat default, `w40i4`
  breaking), it compares the `fltkfmt` binary's stdout (subprocess) to the in-process Python
  reference and asserts byte equality. 16 tests, all pass.
- Python reference (`_py_format`): runs the exact `fltk/unparse_cli.py` pipeline on
  `fegen.fltkg` + `fegen.fltkfmt` (`parse_text` → `unparse_cst` → `render_doc` at matching
  `RendererConfig`); grammar/parser/unparser generation is `functools.cache`d (expensive).
- Binary (`fltkfmt_binary` session fixture): builds via `cargo build --manifest-path
  crates/fltkfmt/Cargo.toml` and returns `target/debug/fltkfmt`; `pytest.skip` if `cargo` is
  absent, hard-fail on a build error.
- `# noqa: S603`/`S607` on the two `subprocess.run` call sites, per the existing tests/ convention
  (e.g. `tests/pyright_test_utils.py`, `tests/test_nullable_loop_guard.py`).
- Verified: `pytest tests/test_fltkfmt_parity.py` (16 pass), ruff check + ruff format --check +
  pyright all clean on the new file.

Deviation: design §4 says the parity pytest "mirrors `test_rust_unparser_parity_fixture.py`",
which uses `pytest.importorskip` on a make-built extension module. `fltkfmt` is a standalone
binary with no `make` build wiring (design §2.3 kept `build-fltkfmt` optional / not a check step),
so a plain importorskip-equivalent would never run in CI. Instead the session fixture builds the
binary with `cargo` (skip only when `cargo` is unavailable), making the test self-sufficient and
actually runnable wherever the Rust toolchain is present (required per CLAUDE.md). The Python
reference is computed in-process via the same plumbing `unparse_cli.py` wraps (byte-identical to,
and faster than, subprocessing the CLI), matching how the mirrored test runs its Python side
in-process.
