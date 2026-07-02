# Deep error-handling review notes

Commit reviewed: cc1e869c09866461a967f1b39e3e187c87400baf (base 5ce1fd8f936240169be9dafafa4bc63e46274a9d)

No findings.

Scope: replacement of the `py_module.import_path` truthiness sentinel with an explicit
`emit_kind_literal` keyword parameter threaded through the protocol-emission chain in
`gsm2tree.py`, deletion of the throwaway-`CstGenerator` workaround in `gsm2tree_rs.py`, and test
updates.

Error-path review:
- The gated conditional `if rule_name and emit_kind_literal:` retains its `else` arm; both branches
  are handled exhaustively (Literal discriminant vs `kind: object`). No new unreachable branch, no
  missing default.
- No error swallowing introduced: no bare/broad excepts, no `let _ =`-equivalent, no default-on-error
  fallback. The `emit_kind_literal=False` arm is an intentional, documented opt-out, not a silent
  degradation — this change actually removes the prior silent-failure trap (Builtins-backed generator
  silently emitting degraded output).
- No error propagation altered; no transient-vs-logic error handling in the diff.
- `create_default_context` and `pyreg` imports in `gsm2tree_rs.py` remain used (lines 175, 179).
