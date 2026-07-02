# Deep error-handling review: unparser-none-path-diagnostics

Commit reviewed: 462cf1c920351b1f83dc20f178001076cc196a9a (base 1d277ce8).

## Verdict

No findings.

## What was checked

The change converts the two documented silent-`None` paths in the generated
unparsers into loud halts, matching the design's "halt with a diagnostic" policy.
Reviewed both the generators (`gsm2unparser_rs.py`, `gsm2unparser.py`,
`pyrt.py`) and the regenerated output (`crates/fegen-rust/src/unparser.rs`,
fixtures), plus the runtime tests.

- Site 2 (regex text extraction): `span.text()?` -> `let Some(text) = ... else
  { panic!(...) }`. Message names rule, item (`label \`x\`` / `(unlabeled)`),
  child position `pos`, and span `Debug` (start/end/has_source). `pos` is in
  scope at every emission site; the two `None` causes (sourceless vs bad offset)
  are distinguishable from the message. Reported and responded to.
- Site 1 (dropped comment): added `else { panic!(...) }` on
  `if let Some(trivia_result)`; Python mirror raises `ValueError` via new
  `raise_preserved_trivia_failure(rule_name, pos)` (`-> NoReturn`). Guarded by
  `_has_preservable_trivia`, so it fires only when a confirmed-preservable
  comment fails to unparse — a genuine invariant violation, correctly halted
  rather than silently dropped.

- Expected-bad-input vs invariant-violation distinction is correct: the
  "not this alternative" `None` signal is preserved on the ordinary
  backtracking paths; only the CST-child-property failures (unreadable span,
  unparseable confirmed-preservable comment) are promoted to halt. The
  backtracking-abort interaction is analyzed and defended in the design's
  edge-cases section (a broken child cannot yield a correct result via another
  alternative), and the sourceless-span Python/Rust asymmetry is an explicitly
  accepted consequence of the Rust CST lacking `terminals`.
- No `span.text()?` remain in generated Rust; the `text_str().map(...).unwrap_or(0)`
  newline-count paths are deliberately out of scope (blank-line fidelity, not
  data fidelity), per design.
- Format-string safety: `rust_str_lit` escapes `"`/`\`; rule names and labels
  are grammar identifiers, so no brace/quote injection into the panic format.

## Verification performed

- `pytest tests/test_rust_unparser_generator.py
  tests/test_rust_unparser_none_path_diagnostics.py fltk/unparse/test_pyrt.py
  fltk/unparse/test_unparser.py` — 195 passed (includes the site-2 PanicException
  runtime test and the Python site-1 ValueError test).
- `cargo test test_preservable_trivia_unparse_none_panics` (crate
  `fegen-rust-cst`) — passes; generated panic arms compile and fire as expected.
