# ADR: Rust Parser Codegen

**Status**: Accepted
**Date**: 2026-06-10

---

## Context

Phases 1–3 of this ADR delivered Rust CST codegen (`gsm2tree_rs.py`), a runtime crate
(`fltk-parser-core`), a Rust parser generator (`gsm2parser_rs.py`), and Python bindings
for generated Rust parsers. The goal: FLTK generates both Python parsers (unchanged) and
Rust parsers from the same `.fltkg` grammar. Pure-Rust consumers pay no cost for Python;
Python bindings are gated behind a `python` feature flag. The CST crosses the
boundary; the parser does not.

Full requirements: `request.md` in this directory.
Full design: `exploration.md` (survey) and `design.md` (binding decisions).

---

## Decision

**Direct Rust emission via `gsm2parser_rs.py`** — a dedicated Python module that walks
`gsm.Grammar` and emits `.rs` source directly, mirroring `gsm2parser.py` for Python but
producing Rust output. The IIR→Rust compiler backend path was rejected.

Four load-bearing reasons (design.md §2):

1. **IIR encodes the Python CST API.** `RefType`, `NodeRef`, and `Optional[NodeRef]` map
   to Python dataclass field types; they have no direct Rust equivalents.
2. **Python-shaped ownership structure.** The IIR assumes garbage-collected, shared-mutable
   nodes. Rust's ownership model and the `Shared<T>` / `Arc<T>` pattern require different
   structural choices throughout code generation.
3. **RefType annotations wrong for Rust.** Label type info and child-enum variants are
   derived from `RefType`; generating correct Rust enum variants and append methods requires
   different logic than the IIR provides.
4. **Constructs the IIR cannot represent.** Generated items such as regex OnceLock tables,
   memoization cache fields, and the pyo3 bindings block have no IIR counterparts.

**Future parsers** (e.g. an unparser for a new target language) use the same
direct-emission path: one dedicated `gsm2<target>_<artifact>.py` module per target/artifact
pair. This avoids the IIR-adaptation cost while keeping generated artifacts independently
auditable (design.md §2.6).

---

## Regex subset

Grammar regexes must use the common subset of Python `re` and the Rust `regex` crate.
Lookahead, lookbehind, and backreferences are **not supported** — the Rust `regex` crate
rejects them at compile time with a clear error message.

Enforcement: the generated parser includes a `#[cfg(test)] fn all_regex_patterns_compile`
that calls `Regex::new(pattern)` for each pattern. `cargo test` names any unsupported
pattern in the failure message, so grammar authors learn of a violation immediately.

The subset-only constraint is the accepted permanent default. The `fancy_regex` crate
(which supports lookaround/backreferences) is added only if a concrete need arises
(user answer A1, exploration.md §1).

---

## Consequences

- **Two generators that can drift**: `gsm2parser.py` (Python) and `gsm2parser_rs.py`
  (Rust) implement the same grammar semantics independently. Parity tests
  (`tests/test_rust_parser_parity_fegen.py`, `tests/test_rust_parser_parity_fixture.py`)
  are the contract: any semantic divergence surfaces as a test failure.
- **One codegen idiom**: direct emission — no IR abstraction layer between grammar model
  and output text. The generator is longer but every output line is traceable to a single
  grammar construct.
- **Parser API freedom**: parsers never cross the Python/Rust boundary, so the Rust parser
  API can diverge from the Python API where Rust idioms demand it. Deliberate divergences:
  - Constructor is `Parser::new(text, capture_trivia)` / `Parser::from_source_text(...)`;
    Python uses `Parser(terminalsrc=...)`.
  - `error_message()` / `error_position()` methods instead of a public `error_tracker`
    field.
- **No annotation churn for downstream consumers**: the generated CST API (the thing that
  crosses boundaries) is unchanged. Downstream code that typed against Python-backend CST
  nodes does not need to update call sites or type annotations to use the Rust backend
  (CLAUDE.md §CRITICAL).

---

## Phases

| Phase | Design doc | Summary |
|---|---|---|
| 1 — runtime crate | `../10-rust-parser-runtime-crate/design.md` | `fltk-parser-core`: `TerminalSource`, `PackratState`, `Cache`, `ErrorTracker`, `apply()` |
| 2 — generator | `../10-rust-parser-generator/design.md` | `gsm2parser_rs.py`: direct Rust emission from `gsm.Grammar` |
| 3 — Python bindings | `../10-rust-parser-python-bindings/design.md` | `#[cfg(feature = "python")]` pyo3 block generated into each parser |
| 4 — integration | `../10-rust-parser-integration/design.md` | `check-no-pyo3` fixture assertions, self-hosting test, this README |
