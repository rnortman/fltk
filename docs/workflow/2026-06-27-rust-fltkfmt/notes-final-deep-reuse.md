reuse-1

File: fltk/_stubs/fegen_rust_cst/unparser.pyi:5-7 (new in diff); fltk/_stubs/rust_parser_fixture/unparser.pyi:5-7 (pre-existing); fltk/unparse/gsm2unparser_rs.py:133-135 (generate_pyi emission)

What's duplicated: The `class Doc` stub block — three lines declaring `render(max_width, indent_width) -> str` and `__repr__() -> str` — is copy-pasted verbatim into every per-grammar unparser `.pyi` file. The `generate_pyi()` method in `gsm2unparser_rs.py` emits this block inline for each grammar it processes. The two committed stubs (`fegen_rust_cst/unparser.pyi` and `rust_parser_fixture/unparser.pyi`) are already identical in their `Doc` definition.

Existing function/utility: The `Doc` class is grammar-independent — its surface (`render` + `__repr__`) does not vary by grammar. The CST side has `CstModule` as a shared protocol; no equivalent `DocModule` or shared stub exists for the unparser's `Doc` class. The `generate_pyi` docstring acknowledges this: "there is no `UnparserModule` analog of `CstModule`."

Consequence: Every new grammar that grows a Rust unparser extension will receive a fresh verbatim copy of the `Doc` stub emitted by `generate_pyi`. If `Doc.render`'s signature changes (e.g., a new parameter, a different return type) all committed stubs must be found and updated individually. The duplication is currently two copies; it will grow linearly with grammar count. A shared stub (e.g., `fltk/_stubs/fltk_unparser_doc.pyi` imported by each per-grammar stub, and referenced from `generate_pyi`) would centralize the definition.
