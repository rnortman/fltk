# Correctness review — Phase 4 integration (8b3e92b..f1423a2)

Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Reviewed: Makefile `check-no-pyo3` stanzas, `TestRustParserSelfHosting`, ADR README, `gsm2parser_rs.py` docstring.

## Verified clean

- **Makefile stanzas**: `tests/rust_parser_fixture/Cargo.toml` has no `default` feature and depends on `fltk-parser-core` (positive control valid); `fegen-rust-cst` declares `default = ["extension-module"]` with `pyo3` optional and `fltk-parser-core` unconditional, so `--no-default-features` is the correct python-off lane and the control crate is guaranteed present. `! ... || FAIL` under `set -e` matches the existing stanzas' semantics. Both crates are standalone `[workspace]`s, so `--manifest-path` resolution is isolated as the design claims. Updated comment is accurate.
- **Test signature surface**: generated bindings (`tests/rust_cst_fegen/src/parser.rs:1369-1380`) define `#[pyo3(signature = (text, capture_trivia = false))]`, `error_message() -> String`, and `PyApplyResult` getters `pos`/`result` — all four usages in `_assert_rust_parser_equals_python` match.
- **`result.pos == len(text)` codepoint semantics**: `fltk-parser-core/src/terminalsrc.rs` builds a codepoint→byte table; all external positions including `ApplyResult.pos` are codepoint indices, matching Python `len(str)`.
- **`Cst2Gsm(text)` vs Python path**: `TerminalSource.__init__` stores the input string verbatim as `.terminals` (terminalsrc.py:163-164), so passing raw `text` is identical to the reference path's `Cst2Gsm(terminals.terminals)` (plumbing.py:146).
- **Reference path purity**: `parse_grammar(text)` with no `rust_fegen_cst_module` takes the committed-Python-parser branch unconditionally (plumbing.py:132-148); no env/cache leakage from the Rust branch.
- **Assert-message failure path**: `format_error_message` (errors.rs) handles `longest_parse_len == -1` and out-of-range gracefully (no panic), so `parser.error_message()` in the assert message cannot turn a clean assertion failure into a pyo3 panic. Python `assert cond, msg` evaluates `msg` only on failure — no cost or side effect on the pass path.

## Findings

### correctness-1

- **File**: `docs/adr/2026/06/10-rust-parser-codegen/README.md:67` (Consequences, first bullet)
- **What's wrong**: cites parity tests as `tests/test_rust_parser_parity.py`. No such file exists.
- **Why**: the actual parity suite is `tests/test_rust_parser_parity_fegen.py` and `tests/test_rust_parser_parity_fixture.py` (shared harness `tests/parser_parity.py`). `ls tests/ | grep parity` confirms; `test_rust_parser_parity.py` matches nothing.
- **Consequence**: the ADR — treated as immutable once accepted per CLAUDE.md convention — permanently records a dangling reference for the load-bearing "parity tests are the contract" mitigation. A future reader following the pointer finds no file and may conclude the contract was removed.
- **Suggested fix**: change the citation to `tests/test_rust_parser_parity_{fegen,fixture}.py` (or name both files) before the ADR is committed as accepted.

No other findings. Test logic, Makefile logic, and docstring factual claims (`#[test] fn all_regex_patterns_compile` exists in generated output, parser.rs:1313-1321) all check out.
