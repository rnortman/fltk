# Implementation Log: Phase 2 — Rust Parser Generator

## Increment 3 — scope-3+4: fixture grammar + tests (design §2.6 B, §4 item 3) (commit e4019b5)

- fltk/fegen/test_data/rust_parser_fixture.fltkg: added `expr` (direct left recursion), `lval`/`rval` (indirect left recursion via mutual reference), `arrow` (multibyte literal `→`), `latin_word` (multibyte regex `[À-ÿ]+`).
- tests/rust_parser_fixture/src/cst.rs: regenerated from updated grammar.
- tests/rust_parser_fixture/src/parser.rs: regenerated from updated grammar.
- tests/rust_parser_fixture/src/native_tests.rs: added 13 new tests covering `error_position()`, negative/beyond-end `pos` for non-nullable and nullable rules, `Shared::ptr_eq` memo sharing, direct left recursion (expr associativity + termination), indirect left recursion (lval/rval base cases), multibyte literal codepoint offsets (arrow), multibyte regex codepoint offsets (latin_word partial and pure).
- 34 Rust tests total; `make check` green.

## Increment 2 — scope-2: Makefile wiring for fixture crates (design §2.7) (commit b86e0ef)

- Makefile:40-41: `cargo-check` extended with `cargo check -q --manifest-path tests/rust_cst_fegen/Cargo.toml` (default features = python-on gate).
- Makefile:51-56: `cargo-test-no-python` extended with `cargo test -q --manifest-path tests/rust_parser_fixture/Cargo.toml` and `cargo test -q --manifest-path tests/rust_cst_fegen/Cargo.toml --no-default-features`.
- Makefile:58-63: `cargo-clippy-no-python` extended with corresponding clippy invocations for both fixture crates.
- `make check` green with all new lanes.

## Increment 1 — scope-1: generator emits `generated_regex_tests` block (design §2.4) (commit f3ea889)

- gsm2parser_rs.py: added `_gen_regex_compile_test` method; `generate()` calls it after closing `}` when `self._regex_patterns` is non-empty.
- fltk/fegen/fegen.fltkg:21: fixed `block_comment` rule to remove lookahead (`(?!\/)`) unsupported by `regex` crate. Changed `content` regex to `(?:[^*]|\*+[^\/\*])*` and changed `end` from literal `"*/"` to regex `/\*+\//`. Labels `start`/`content`/`end` and their `Span` types are unchanged; the `end` span now captures trailing stars (e.g., `**/` for `/***/`-style comments).
- Regenerated: `fltk_parser.py`, `fltk_trivia_parser.py`, `tests/rust_cst_fegen/src/parser.rs`, `tests/rust_parser_fixture/src/parser.rs`.
- Both `parser::generated_regex_tests::all_regex_patterns_compile` tests pass under `cargo test`.
- `make check` green.
- Out-of-scope observation: `fltk/fegen/bootstrap.fltkg:21` has the same lookahead in `block_comment` but no Rust parser is generated from it, so no immediate failure. TODO(bootstrap-block-comment-lookahead): fix for consistency when bootstrap grammar gets a Rust parser.


