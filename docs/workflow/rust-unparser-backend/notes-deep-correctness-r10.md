# Deep correctness review — batch 10 (§4 cross-backend parity tests + native test)

Commit reviewed: fa22e182702d3ea1c1ec5e464345ab006941c9e9 (base 028583414d5943b6e134a78c922868f45cb59361)

Scope: `tests/test_rust_unparser_parity_fixture.py`, `tests/unparser_parity.py`,
`tests/rust_parser_fixture/src/native_tests.rs` (native unparser block),
`tests/rust_parser_fixture/src/lib.rs`, `Makefile`, generated `unparser_default.rs`
(PyUnparser None-handling only, as it backs the parity test).

## Verdict on the core question (do the parity tests genuinely compare Rust vs Python?)

The parity harness is sound. Verified end to end:

- `_py_cst` drives Python parser + Python unparser; `_rust_node` + `rust_parser_fixture.unparser*.Unparser()`
  drive Rust parser + Rust unparser. `assert_unparse_parity` runs both full pipelines and asserts
  byte-equal. No backend is compared to itself.
- `unparse_python` faithfully mirrors `plumbing.unparse_cst` (construct with `text`, call
  `unparse_{rule}(cst)`, None-guard, `resolve_spacing_specs(result.accumulator.doc)`, `render_doc`).
  `unparse_rust` calls the Rust PyUnparser full-pipeline method. Both use identical `(max_width, indent_width)`.
- Corpus is non-empty (38 pairs) × 2 baked configs (`.fltkfmt` vs default) × 2 render widths
  `[(80,4),(8,2)]` = 152 cases. Parametrize ids are unique (enumerate index suffix), so no cases are
  silently dropped.
- The two baked Rust modules genuinely differ (`unparser.rs` vs `unparser_default.rs` differ at byte 6028;
  143-line diff), and the Python side is generated with the matching config in each function — the two
  test functions exercise distinct configs, not duplicates.
- Both sides require full input consumption (Python `parse_text` checks `pos == len`; `_rust_node` asserts
  `result.pos == len(text)`), so CSTs are comparable; codepoint lengths line up for the multibyte cases.
- Failure-agreement is asserted (`(py_str is None) == (rust_str is None)`), and a real divergence (e.g. the
  union-span `val "!@#"` arm, narrow-width group breaks shown by the (8,2) config, trivia-preserving
  `"( hello )"`) would surface as a mismatch, not a silent pass. The narrow (8,2) config provably triggers
  break-vs-flat differences (confirmed against native expected strings), so Wadler-Lindig decisions are
  compared cross-backend. No vacuous all-None corpus path.

## correctness-1

File: `tests/rust_parser_fixture/src/native_tests.rs:1011` (macro `render_native!` uses
`Parser::new(src, None, false)`), against the comment at lines 996–999.

What: The native unparser tests parse with `capture_trivia=false`, but the block comment claims the
expected literals are "the parity-validated Python-backend reference ... which asserts the two backends
render byte-equal at these exact configs." The cited parity corpus
(`test_rust_unparser_parity_fixture.py`) parses with `capture_trivia=true` (line 62 / line 94). For an
input that carries preservable internal trivia, `capture_trivia=true` routes the unparser through its
trivia-preservation path (`SeparatorSpec` wrapping a captured `Trivia` child) while `capture_trivia=false`
routes it through the no-trivia spacing-default path. These are different generated code paths, so the
parity test's byte-equal guarantee (Python-true == Rust-true) does not, in general, transfer to the
native test's value (Rust-false).

Why: The only native input with internal trivia is `stmt "x = y"`. The `.fltkfmt` config sets
`ws_required: nbsp` (single space) and the source uses single spaces, so the trivia-preservation path and
the spacing-default path coincide at `"x = y"`. The cross-reference therefore happens to hold for the
chosen inputs, but by coincidence of input/config, not by the cited parity assertion.

Consequence: No current test failure or false pass — the native test independently asserts its own
pipeline output, and it is Rust-only (it cannot mask a Python/Rust divergence). The defect is only that
the "parity-validated reference" justification is not airtight: if a future native input gains internal
whitespace that differs from the config default (e.g. `"x  =  y"` with `ws_required: nbsp`), the native
expected literal (default-spacing path, `"x = y"`) would no longer equal the value the parity test
validates (trivia-preserving path, `"x  =  y"`), despite the comment asserting they are the same reference.

Suggested fix: Parse with `capture_trivia=true` in the `render_native!` macro to make the native path match
the parity corpus exactly, or soften the comment to state the native test asserts its own
(`capture_trivia=false`) pipeline output rather than implying path-identical parity validation.
