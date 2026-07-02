# Security review — unparser-none-path-diagnostics

Reviewed: `1d277ce8..462cf1c9` (12 files: generator changes in `fltk/unparse/gsm2unparser.py`,
`fltk/unparse/gsm2unparser_rs.py`, new `pyrt.raise_preserved_trivia_failure`, regenerated
committed Rust unparsers, tests).

No findings.

Checked and cleared:

- **Injection into generated source.** Rule names and labels are interpolated into emitted
  Rust `panic!` strings and Python calls. Rust side goes through `rust_str_lit`
  (`fltk/fegen/gsm2parser_rs.py:59`), which escapes `\`, `"`, and control chars, so string
  literal escape-out is not possible. Python side passes the rule name as
  `iir.LiteralString`, emitted via `repr()` (`fltk/iir/py/compiler.py:321`) — safe.
  `rust_str_lit` does not escape `{`/`}` for `panic!` format-string purposes, but rule
  names/labels are grammar identifiers (they also become method names and enum variants, so
  a brace-bearing name cannot produce compilable output today), and the grammar author
  already controls the entire generated source — no trust boundary is crossed; at worst a
  hostile grammar breaks its own build. Noted as a latent robustness nit, not a vuln.
- **Information disclosure in diagnostics.** Panic/ValueError messages carry rule name,
  child position, and the span's `Debug` form (start/end/`has_source` only — source text is
  deliberately elided per the design). No file contents, secrets, or paths leak into error
  messages.
- **DoS via new panic paths.** The change converts two silent-`None` invariant-violation
  paths into `panic!`/`ValueError`. Both are unreachable from parser-produced CSTs (spans
  always carry source); only hand-constructed/mutated CSTs hit them. Through PyO3 a panic
  surfaces as a catchable `PanicException`, so a Python service cannot be crashed outright.
  Net effect is a security *improvement*: a formatter silently deleting comments or nulling
  output is an integrity failure (silently altered output) that this change eliminates.
- No secrets, auth surfaces, filesystem/network/deserialization paths, or dependency
  changes in the diff.
