No findings.

The change is a pure deletion of dead code plus two reference-text fixups. There are no new code paths to cover and no behavior changes. Key observations:

- `tests/rust_cst_fegen/src/native_parser_tests.rs` (deleted) is byte-for-byte identical to `crates/fegen-rust/src/native_parser_tests.rs` (surviving). The diff between them is empty. No test coverage is lost.
- The surviving `crates/fegen-rust/src/native_parser_tests.rs` has meaningful assertions: it parses `fegen.fltkg` end-to-end (`r.pos == parser.terminals().len()`), verifies error-position is populated on failure, checks `rule_names()` content, and tests `capture_trivia=true` produces strictly more children than `capture_trivia=false`. These are behavioral, not vacuous.
- The `build-fegen-rust-cst` Makefile target already pointed to `crates/fegen-rust` at the base commit — the deleted directory was not wired into any build or test lane, confirming the spec claim.
- The CHANGELOG and extension-guide text changes are documentation-only; no behavior to test.
