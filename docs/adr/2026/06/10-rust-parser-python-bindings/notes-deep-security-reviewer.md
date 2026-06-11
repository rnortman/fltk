# Security review — Phase 3 Python bindings + parity (b668897..b107645)

Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Scope reviewed: `fltk/fegen/gsm2parser_rs.py` `_gen_python_bindings`, generated bindings in `tests/rust_parser_fixture/src/parser.rs` and `tests/rust_cst_fegen/src/parser.rs`, extension wiring (`tests/rust_parser_fixture/src/lib.rs`, `Cargo.toml`, `tests/rust_cst_fegen/src/lib.rs`), Makefile lanes, `tests/parser_parity.py`, new test modules.

Checked and clean:
- **Code injection into generated Rust**: interpolated names (`apply_name`, `Py{class_name}`) derive from grammar rule names validated at generator construction (`gsm2parser_rs.py:101-127` identifier validation; `gsm2tree_rs.py` class-name validation). Grammar files are build-time developer inputs, not a runtime trust boundary.
- **`check_pos` bounds**: `TerminalSource::len()` returns `i64` codepoint count (`crates/fltk-parser-core/src/terminalsrc.rs:88-91`), so the `pos < 0 || pos > len` comparison is type- and unit-correct; all native `consume_*` paths independently reject out-of-range `pos` before indexing `cp_to_byte`. No panic/OOB path from Python-supplied `pos`. Python ints outside `i64` fail in pyo3 extraction (`OverflowError`) before any use.
- **Non-frozen `PyParser` aliasing**: pyo3 runtime borrow checking turns reentrant/concurrent `&mut self` access into a Python exception, not UB.
- **No secrets, no filesystem/network/deserialization surface** in the diff. Test modules' `getattr(p, f"apply__parse_{rule}")` uses corpus-literal rule names only.

## security-1

- **File**: tests/rust_parser_fixture/src/parser.rs:1125ff and tests/rust_cst_fegen/src/parser.rs (generated `python_bindings` blocks); generator `fltk/fegen/gsm2parser_rs.py:_gen_python_bindings`.
- **Issue**: This diff is the first point where the depth-unbounded recursive-descent Rust parser becomes callable from Python on arbitrary `text`. Rust stack exhaustion on deeply nested input aborts the whole Python process (guard-page SIGSEGV/abort; not catchable), whereas the Python backend raises a recoverable `RecursionError`. The existing mitigation guidance lives only in a Rust doc comment ("run the parser on a thread with a known stack size", parser.rs:1-7) — invisible to Python consumers, and the binding runs on whatever thread Python calls from, where stack size is not under the parser's control.
- **Trust boundary / data flow**: untrusted text → `Parser(text)` pyclass constructor → `apply__parse_<rule>` → native recursive descent; recursion depth proportional to input nesting.
- **Consequence**: an attacker who can supply input to any downstream application using these bindings (the primary out-of-tree use case per CLAUDE.md) can crash the entire host Python process with a short deeply-nested input — process-abort DoS, strictly worse than the Python backend's catchable failure mode.
- **Existing disposition**: tracked as `TODO(parser-depth-limit)` (TODO.md:76) with the abort behavior documented in the Rust header. The residual gap introduced by this phase: no Python-visible warning and no depth limit at the boundary that real untrusted input crosses.
- **Suggested fix**: when `TODO(parser-depth-limit)` lands, enforce the depth counter by default (or with a sane default cap) in the generated `PyParser` path and surface it as a Python exception; meanwhile, mirror the stack-depth warning somewhere Python consumers see it (binding class docstring / phase docs).

No other findings.

Commit reviewed: b107645.
