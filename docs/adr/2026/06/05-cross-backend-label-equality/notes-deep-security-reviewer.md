# Security review — cross-backend label equality + NodeKind

Reviewed: 854e1ad..c57f888. Notes: this file.

No findings.

Scope reviewed: `gsm2tree.py`, `gsm2tree_rs.py`, `fltk2gsm.py`, `plumbing.py`,
and generated outputs (`fltk_cst.py`, `*.rs`). Change adds canonical-name-keyed
`__eq__`/`__hash__` to generated `Label`/`NodeKind` enums and a `kind` discriminant.

No injection, auth, secret, path, SSRF, deserialization, or crypto surface
introduced. Grammar rule names flow into emitted format strings (canonical
names, Rust variants) but are validated as identifiers before codegen and the
output is build-time generated code under the trusted regen workflow — no
untrusted-runtime-input-to-sink flow.

The one new duck-typed surface, `getattr(other, "_fltk_canonical_name", None)`
in both backends' `__eq__`, is benign: an arbitrary operand exposing that
attribute yields at worst a `False`/string mismatch; Rust guards with
`if let Ok(...)`, Python falls back to `NotImplemented`. No raise propagation,
DoS, or type confusion of security consequence. Accepted in design §3.3.
