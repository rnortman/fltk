# Security review — rust-unparser-backend batch 5 (generator term-handling)

Commit reviewed: 5f7b5cb1d33150b1125daf6e0f19c4051ab28c30 (base f9ed9363427731cad797682ba6e5beed10d77393)

Scope: `fltk/unparse/gsm2unparser_rs.py` (regex/sub-expression/before-after-spacing
term handling), `crates/fltk-unparser-core/src/doc.rs` + `lib.rs` (`before_spec`/`after_spec`
constructors), tests.

## Findings

No findings.

## Code-generation / injection analysis (the called-out concern)

This is a build-time Rust code generator. Trust boundary: `.fltkg` grammar and
`.fltkfmt` format files are developer-authored build inputs, not runtime untrusted
data. Even so, every grammar/config-derived string interpolated into emitted Rust was
checked:

- Literal text (`_gen_literal_term_body:579`, `_gen_suppressed_item_body:715`,
  `_doc_to_rust_expr:772`) is emitted as `fltk_unparser_core::text("{rust_str_lit(...)}")`.
  `rust_str_lit` (gsm2parser_rs.py:59) escapes `\` → `\\`, `"` → `\"`, and all code points
  < 0x20 plus DEL → `\u{XX}`. The only two characters that can terminate/escape a Rust
  `"..."` literal (`"`, `\`) are both escaped, and newline/CR/tab/NUL are escaped, so no
  literal value can break out of the string and inject Rust. No breakout possible.
- Regex terms (`_gen_regex_term_body`): the regex *pattern* is never interpolated into
  generated code. Only the runtime-captured `span.text()` value is used, and it is bound
  to a Rust variable (`let text = span.text()?;`) then passed as data to
  `fltk_unparser_core::text(text)`. No string interpolation of attacker-influenced runtime
  text into source; it flows into a `String` field and is rendered as data, never as code.
- Source-name header (`_gen_header:91`) is `rust_str_lit`-escaped inside a `//!` line
  comment; escaped newlines cannot break out of the line comment.
- Spacing Docs from the FormatterConfig (`_item_spacing_lines` → `_doc_to_rust_expr`)
  route Text content through `rust_str_lit` as well, and Group/Nest/Join are rejected
  (parity with the Python backend).
- Identifiers/labels/class names (`ref_rule_name`, `item.label`, child/label enum names)
  go through the shared naming helpers (`snake_to_upper_camel`, `child_enum_name`,
  `label_enum_name`, `class_name_for_rule`) — identical to the CST/parser backends, so no
  new attack surface is introduced here and the emitted symbols match the CST module.

## Other classes

No auth, network, filesystem-from-runtime-data, secrets, crypto, deserialization, or
timing surfaces in the diff. Deep-tree recursion (resolve/render stack exhaustion) is a
pre-existing, explicitly deferred item (design §3 / open question 1); `Doc::drop` is
iterative and the new `before_spec`/`after_spec` constructors are trivial wrappers that
add no recursion or unsafe code.
