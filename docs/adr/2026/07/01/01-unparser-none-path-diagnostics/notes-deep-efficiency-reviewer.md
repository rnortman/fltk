# Efficiency review — unparser-none-path-diagnostics

Commit reviewed: 462cf1c920351b1f83dc20f178001076cc196a9a (base 1d277ce8)

No findings.

Scope: the diff converts two silent-`None` unparser paths into loud halts
(`panic!` in generated Rust, `raise ValueError` via `raise_preserved_trivia_failure`
in generated Python). All new code sits on failure/invariant-violation branches:

- Rust site 1: added `else { panic!(...) }` arms on the trivia `if let Some(...)`
  blocks — only reached when `unparse__trivia` returns None after preservable
  comments were confirmed. Happy path untouched.
- Rust site 2: `let text = span.text()?;` -> `let Some(text) = span.text() else { panic!(...) };`.
  Happy-path cost is identical to the prior `?`; the panic message (incl. `{:?}`
  span Debug formatting) is built only when the panic fires.
- Python site 1: new `orelse` block calling a runtime helper that raises — only
  executed on the same invariant violation.
- Generator changes (gsm2unparser.py, gsm2unparser_rs.py) build the panic/raise
  strings at code-generation time, not at unparse runtime; negligible one-time cost.

No new per-render/per-request/startup work, no redundant computation, no repeated
reads, no concurrency opportunities missed, no unbounded structures or leaks.
