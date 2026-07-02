# Deep correctness review — protocol-module-truthiness-gate (cc1e869)

No findings.

Verification performed:
- `emit_kind_literal` threading is consistent: default `True` at both public entry points
  (`gen_protocol_module`, `gen_protocol_module_text`), required keyword on both private helpers;
  gate `if rule_name and emit_kind_literal:` preserves empty-`rule_name` short-circuit.
- `RustCstGenerator.generate_protocol` reuse of the Builtins-backed `self._py_gen` is safe:
  traced the protocol-emission path — it never reads `py_module` and touches the context only
  via read-only `pycompiler.iir_type_to_py_annotation` (registry lookups, no writes). The
  registry-writing paths (`iir_type_for_rule`, `py_annotation_for_model_types`) are unreachable
  from `gen_protocol_module`.
- Imports in `gsm2tree_rs.py` (`CstGenerator`, `pyreg`, `create_default_context`) remain used
  by `_py_gen` construction.
- Ran at HEAD cc1e869 in a clean worktree: the 3 new `test_cst_protocol.py` tests,
  `TestGenerateProtocol` (incl. new same-instance reuse test), `TestMutatorsEmittedPyProtocol`
  (15 passed), and all of `fltk/fegen/test_genparser.py` incl. the cross-path byte-identity
  guardrail (65 passed).
- Note (environment, not a diff defect): the live working tree contains unresolved merge-conflict
  markers in `fltk/fegen/gsm2tree.py` (~line 297) from work outside this commit range; tests
  cannot run against the dirty tree.
