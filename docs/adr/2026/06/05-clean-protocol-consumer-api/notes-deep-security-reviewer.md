# Security review — clean-protocol-consumer-api

Commit reviewed: bc42280 (base 1e78b73).
Note: Concise. Precise. Complete. Unambiguous. No padding.

No findings.

Scope reviewed: protocol-local `NodeKind`/`SpanKind` runtime enums + `_fltk_canonical_name`
cross-backend `__eq__`/`__hash__` bridge (`fltk_cst_protocol.py`, `terminalsrc.py`), generator
emission (`gsm2tree.py`), Rust `Span.kind` getter (`src/span.rs`), consumer rewrite
(`fltk2gsm.py`), global `S101` ruff disable (`pyproject.toml`).

Considered and dismissed (not vulnerabilities):
- Duck-typed `__eq__` matching any object exposing `_fltk_canonical_name` is by-design
  cross-backend equality. The compared strings are hardcoded discriminant constants, never
  derived from untrusted grammar input, and the result feeds only type-narrowing/dispatch — no
  injection sink (SQL/cmd/path/HTML). No trust boundary crossed.
- Rust `Span.kind` getter imports a fixed module path (`fltk.fegen.pyrt.terminalsrc`); no
  user-controlled import target. `GILOnceCell` init is benign.
- Global `S101` disable + asserts replacing `typing.cast` in `fltk2gsm.py:57-73`: asserts guard
  parser structural invariants, stripped under `python -O`. This is a correctness/robustness
  concern, not a security boundary — out of lane (correctness-reviewer).
- No secrets, no network/SSRF, no filesystem path handling, no auth surface, no deserialization
  in the diff.
