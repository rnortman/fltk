# Deep Correctness Review — rust-native-lib-shape

Commits reviewed: fltk 7200d9c..7a7ca4d, clockwork 6ede250..ea34388

## Scope

Almost the entire diff is mechanical and out of scope for new-logic review:
- `crates/fegen-rust/src/parser.rs`, `cst.rs`, `native_parser_tests.rs`, `lib.rs`,
  `tests/rust_poc_cst/*` — verbatim moves/promotions from `tests/rust_cst_fegen/`
  and `tests/rust_poc_cst/`. Confirmed `parser.rs` byte-identical to base
  `tests/rust_cst_fegen/src/parser.rs` (diff -q: IDENTICAL). No logic change.
- Makefile / BUILD.bazel / test-file retargeting — wiring, not logic.
- `src/lib.rs`, clockwork `clockwork_native_lib.rs` deletion — removing hand-authored
  files now produced by the generator.

Genuinely new executable logic:
- `fltk/fegen/gsm2lib_rs.py` (LibSpec / Submodule / RustLibGenerator)
- `gen_rust_lib` CLI command in `fltk/fegen/genparser.py`
- the no-`lib_rs` branch in `rust.bzl` `fltk_pyo3_cdylib`

## Logic traced

- `_validate_rust_ident` regex `^[A-Za-z_][A-Za-z0-9_]*$` is anchored; correctly
  rejects "", "1bad", "has space", "a-b". `_native` (underscore-prefixed) accepted.
- `LibSpec.validate()` invariants both hold and are consistently enforced:
  - empty submodules + no span/UNKNOWN_SPAN -> ValueError (caught + reported by CLI,
    no crash on `--no-cst` with no span flags).
  - `unknown_span_static` without `register_span_types` -> ValueError. This guard is
    correct: the emitted UNKNOWN_SPAN init calls `Span::unknown()` and references
    `Span`, which is only imported (`use span::{SourceText, Span}`) when
    register_span_types is True. Without the guard the generated Rust would not compile.
- `generate()` control flow: conditional `register_submodule` import emitted only when
  `submodules` non-empty — matches span-only path (zero submodules) emitting no dead
  import; verified by test_span_only_zero_register_submodule_calls.
- `gen_rust_lib` branch logic: `no_cst` -> direct empty-submodule LibSpec; else
  `LibSpec.standard(..., with_parser=not no_parser)` with a rebuild when span flags
  are also passed on the standard path. `no_parser` correctly ignored under `no_cst`
  (submodules already empty). No path produces an unvalidated spec — `RustLibGenerator.__init__`
  calls `spec.validate()` and the CLI try/except maps ValueError to exit 1.

## Behavioral-equivalence checks (downstream-facing, per CLAUDE.md)

- Generated `_native` lib.rs (`--no-cst --register-span-types --unknown-span-static`)
  matches committed `src/lib.rs` exactly except for a hand-stripped comment (cosmetic).
- Generated `clockwork_native` / `bootstrap_native` lib.rs (default standard path)
  reproduces the deleted hand-authored `clockwork_native_lib.rs` content: same imports,
  `mod cst;`/`mod parser;`, `#[pymodule] fn <name>`, both register_submodule calls,
  `Ok(())`. Only the dropped TODO comment differs (cosmetic).
- Bazel no-lib_rs branch: genrule passes target `name` as `--module-name`; assembly
  genrule prepends `#![recursion_limit]` and the generator deliberately omits it
  (test_standard_output_no_recursion_limit) — no duplicate attribute. `$(location :name_gen_lib)`
  resolves to the single genrule out; correct.

## Findings

No findings.
