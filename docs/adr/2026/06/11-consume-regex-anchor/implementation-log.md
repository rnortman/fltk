# Implementation Log: anchored regex matching in consume_regex

## Increment 1 — switch fltk-parser-core from regex to regex-automata (commit TBD)

- `crates/fltk-parser-core/Cargo.toml`: replaced `regex = "1"` with `regex-automata = "0.4"`.
- `crates/fltk-parser-core/src/lib.rs`: replaced `pub use regex` with `pub use regex_automata`; updated doc comment.
- `crates/fltk-parser-core/src/terminalsrc.rs:8-9`: replaced `use regex::Regex` with `use regex_automata::meta::Regex` and `use regex_automata::{Anchored, Input}`.
- `crates/fltk-parser-core/src/terminalsrc.rs:127-175`: replaced `find_at`+start-check body with `Input::new(text).anchored(Anchored::Yes).span(byte_pos..text.len())` + `regex.search(&input)?`; removed TODO(consume-regex-anchor) and updated doc comment.
- `crates/fltk-parser-core/src/terminalsrc.rs` tests: ported all `regex::Regex::new(...)` to `Regex::new(...)` (meta::Regex); added new `consume_regex_context_before_pos` test (text `"hello"`, pattern `\Bello`, pos=1 → span 1..5).
- `fltk/fegen/gsm2parser_rs.py:275`: header now emits `use fltk_parser_core::regex_automata::meta::Regex;`.
- `fltk/fegen/gsm2parser_rs.py:988`: compile test now uses `fltk_parser_core::regex_automata::meta::Regex::new(pat)`.
- `fltk/fegen/gsm2parser_rs.py` docstring: updated compile-test sentence.
- `fltk/fegen/test_gsm2parser_rs.py:test_regex_table_emitted`: added assertion that generated source contains `use fltk_parser_core::regex_automata::meta::Regex;`.
- `make gencode && make fix`: regenerated `tests/rust_cst_fegen/src/parser.rs` and `tests/rust_parser_fixture/src/parser.rs`.
- `TODO.md`: removed `consume-regex-anchor` entry.
- `make check` passed (lint, format, typecheck, 1309 pytest, cargo test workspace + fixture crates including `all_regex_patterns_compile`).
