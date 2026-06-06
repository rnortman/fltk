# Efficiency review — CST type annotations regression

Commit reviewed: 0903a36 (base a2822d5).

Scope: restoring `visit_*`/`__init__` type annotations on `fltk2gsm.py`, boundary `cast`s,
and a new `gen_protocol_module()` generator on `CstGenerator` (gsm2tree.py) plus one extra
file write in `genparser.generate`.

No findings.

Rationale (not findings, context for why):
- All `fltk2gsm.py` changes are annotation-only. `from __future__ import annotations` makes
  the `cstp.*` names strings, never evaluated at runtime; `cast(...)` is erased at runtime
  (returns its arg). Zero added runtime work in the CST→GSM visit path.
- The new generator code (`gen_protocol_module`, `_protocol_class_for_model`,
  `_cst_module_protocol`, `protocol_annotation_for_model_types`) runs once at codegen time
  (`genparser generate`), a batch dev tool — not a hot/startup/per-request path. Loops are
  bounded by rule/label count. No redundant recomputation introduced.
- One extra file write (`{base}_cst_protocol.py`) per `generate` invocation: codegen-time,
  intended deliverable, not on any hot path.
- No new data structures retained at runtime; no listeners/intervals; no existence pre-checks;
  no broadened reads.
