# Deep security review — rust-unparser-backend batch 8

Commit reviewed: 69fa04efa8bdb0524c0b3f9c4a4026da66d0c941 (base 7723f7ec12ca1fa450e925fac4333a00af1f0230)

Scope: CLI subcommand (`gen-rust-unparser`), `gen-rust-lib --unparser` flag, `LibSpec.standard` change, unparser-generator header/param tweaks, fixture build wiring (Cargo, lib.rs), tests, Makefile target.

No findings.

Notes on what was checked (developer-facing codegen CLI; no network/auth/secret/deserialization surface):

- CLI/build trust boundaries: `grammar_file`, `output_file`, `format_config` are all operator-supplied CLI path arguments; none is derived from untrusted file content, so `output_file.write_text(src)` overwriting an operator-named path is expected behavior, not traversal. The Makefile target only forwards `GRAMMAR`/`RS_OUT` make vars to the same command.
- Codegen injection sinks all escaped/validated:
  - `--cst-mod-path` validated against `_CST_MOD_PATH_RE` before being interpolated into the `use`/`mod` lines (same guard as `gen-rust-parser`).
  - `source_name=str(grammar_file)` is routed through `rust_str_lit` (escapes `\\`, `"`, control chars incl. newline → `\u{0a}`, DEL) before going into the `//!` doc-comment line — no comment break-out.
  - Format-config values reach generated Rust only via `_doc_to_rust_expr`, whose `Text` arm escapes content through `rust_str_lit` and which rejects unsupported Doc types; literal-term text uses the same escaping (`gsm2unparser_rs.py:917,1070,1593`).
- `_node_param` `\bnode\b` heuristic only chooses `node` vs `_node` parameter naming; a wrong choice yields a Rust compile error or an unused-variable warning, not a security consequence.
- `LibSpec.standard(with_unparser=...)` / `--unparser` only append a fixed `Submodule("unparser","unparser")` registration; no rule-derived or operator-derived content is interpolated.
