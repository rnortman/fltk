# Security review — rust-unparser-backend, batch 2

Commit reviewed: e65e4f66bf2d466637df6f94744fa85abc7d239c (base d5914359bd41d526caacc18db82ef0f4c0d5c4b8)

Scope: `crates/fltk-unparser-core/src/{render.rs,result.rs,lib.rs}`, `fltk/unparse/gsm2unparser_rs.py`, `tests/test_rust_unparser_generator.py`, plus design/log docs.

No findings.

Notes (no action needed):
- `render.rs` is a faithful queue-based (iterative) port of `renderer.py`; no recursion, so the attacker-controlled-CST-depth -> stack-overflow concern from design §3 does not arise in this stage. The renderer's only output is formatted source text (its purpose); no injection sink.
- `panic!` on unresolved spec/join nodes is a pipeline-bug path, deterministic on Doc structure, not driven per-input by untrusted CST content; parity with the Python `ValueError`.
- Generator stub emits only a header + unit struct. `source_name` is escaped via `_rust_str_lit` (escapes `\`, `"`, and control chars incl. newline -> `\u{0a}`) and placed inside a `//!` line comment wrapped in backticks; cannot break out of the comment or inject Rust. `source_name` is build-time/CLI input, not a runtime trust boundary.
- No secrets, auth/authz, deserialization, path, SSRF, or crypto surface in this batch.
