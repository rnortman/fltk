# Deep security review — rust-unparser-backend batch 4 (generator term-handling)

Commit reviewed: 66657a3e192b152178fb179099987c9942de2285 (base 014bbda93908b3d0d59062efe0e85a1c1580d992)

Scope: generator term-handling code in `fltk/unparse/gsm2unparser_rs.py`,
`fltk/fegen/gsm2tree_rs.py` (`num_child_variants`), a comment typo fix in
`fltk/unparse/gsm2unparser.py`, and tests.

No findings.

Code-generation/injection analysis (the flagged concern):

- Grammar literal text (`item.term.value`, `doc.content`, `op.separator` Text
  content) is the only arbitrary-character data interpolated into emitted Rust,
  and every site routes through `rust_str_lit` before being placed inside a Rust
  `"..."` literal. `rust_str_lit` escapes the only two breakout characters for a
  Rust double-quoted string (`"` and `\`, with `\` doubled first so no spurious
  escape can form) and `\u{..}`-escapes control chars + DEL; non-ASCII passes
  through as valid UTF-8 source. No string-literal breakout is possible.
  Confirmed by `test_include_literal_text_is_escaped` /
  `test_suppressed_literal_text_is_escaped`.
- Identifiers emitted raw into Rust identifier positions (rule names, ref-rule
  names → `unparse_*`, derived class/child-enum/label names, labels via
  `snake_to_upper_camel`) all originate from grammar identifiers, which the
  grammar parser constrains to `/[_a-z][_a-z0-9]*/` (`fegen.fltkg` `identifier`
  rule). That character set cannot break out of an identifier/path context, so
  no identifier-injection vector exists. Same pattern as the already-committed
  sibling generators (`gsm2parser_rs.py`, `gsm2tree_rs.py`).
- Numeric interpolations (`op.indent or 1`, `HardLine.blank_lines`) are ints.
- `source_name` in the header doc-comment is `rust_str_lit`-escaped (newlines →
  `\u{0a}` text), so it cannot terminate the line comment.

Trust boundary: inputs (grammar `.fltkg`, `.fltkfmt`) are developer-controlled
build-time source artifacts, not runtime untrusted input. No runtime untrusted
data reaches emitted strings in this batch — regex term handling (the path that
would read parsed-input span text) is still a pass-through here. The runtime
crate `fltk-unparser-core` and its deep-tree/stack-safety concerns are not part
of this diff.
