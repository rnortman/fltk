# Security review — rust-unparser-backend batch 3 (generator code)

Commit reviewed: e6a682cb883db43d6df2cc7215cb982121934254 (base d622ff7905362ebc71b3f232cae8b801db9bdd0f)

Scope: `fltk/unparse/gsm2unparser_rs.py` (generator), `tests/test_rust_unparser_generator.py`,
`implementation-log.md`. Focus: code-generation / injection into emitted Rust.

## Findings

No findings.

## Notes (reviewed, not issues)

Trust boundary for this code generator: `.fltkg` grammars and `.fltkfmt` format
configs are build-time inputs; the generator emits Rust source that is later
compiled. The injection-relevant question is whether attacker-influenced strings
can break out of the literal/identifier contexts they are emitted into. Both new
sinks are handled:

- `_doc_to_rust_expr` Text → `Doc::text("{rust_str_lit(doc.content)}")`.
  `doc.content` originates from FormatterConfig spacing/separator Docs (user
  `.fltkfmt`). `rust_str_lit` escapes `"`, `\`, and all control chars `< 0x20`
  plus DEL, so the string literal cannot be broken out of; backslash escaping
  means content like `\u{...}` becomes inert literal text. Unicode > 0x7F passes
  through, which is valid in Rust UTF-8 source. Group/Nest/Join/Comment are
  rejected with `ValueError`, matching the Python backend (no silent divergence).

- Rule names interpolated into Rust identifiers (`unparse_{rule_name}`,
  `cst::{class_name}`, `__alt{N}__item{M}`) are not escaped, but the grammar
  constrains identifiers to `/[_a-z][_a-z0-9]*/` (fegen.fltkg:16), so they are
  always valid, injection-free Rust identifiers. `class_name_for_rule_node`
  derives CamelCase from that same constrained input. This matches existing
  `gsm2parser_rs.py` precedent.

- Header comment (`//! ... from `{escaped}``) wraps `source_name` via
  `rust_str_lit`. The only comment-escape vector is a newline; `rust_str_lit`
  escapes `\n`/`\r` (cp < 0x20) to `\u{0a}`/`\u{0d}` literal text, so the line
  comment cannot be terminated early. Safe.

- Integer interpolations (`op.indent or 1`, `doc.blank_lines`) are typed ints;
  no string injection surface.
