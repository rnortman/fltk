# Dispositions — deep review round 9

Commit reviewed: bb96d0e78ae563c4cbad898225c16be02b4baba5 (base 90ffae8c)

No-finding reviewers: correctness, security, efficiency reported "No findings".

---

errhandling-1:
- Disposition: Fixed
- Action: Added `_PROTOCOL_MODULE_RE` + `_validate_protocol_module(...)` helper
  (`fltk/fegen/genparser.py:398-415`) and call it before any file is written in both
  `gen_rust_unparser` (`:516-517`) and `gen_rust_cst` (`:357-358`). A malformed
  `--protocol-module` (empty, spaces, leading/trailing dot) now exits 1 with
  `Error: --protocol-module '...' is not a valid Python module path` and writes no artifacts,
  rather than emitting a syntactically invalid `.pyi` with exit 0. Tests:
  `test_gen_rust_unparser_invalid_protocol_module`, `test_gen_rust_cst_invalid_protocol_module`
  (`fltk/fegen/test_genparser.py`). Applied to the `gen_rust_cst` sibling too via the shared
  helper, since both interpolate the value verbatim and the helper is the single maintenance
  point the finding recommended.
- Severity assessment: Real diagnosability gap — a typo'd flag produces a green build with a
  broken committed stub that only fails much later in a downstream type checker, with no pointer
  back to the offending argument.

test-1:
- Disposition: Fixed
- Action: Added `test_gen_rust_unparser_pyi_write_failure_exits_cleanly`
  (`fltk/fegen/test_genparser.py`): points `--pyi-output` at an existing directory so the stub
  write raises, then asserts exit != 0, `isinstance(result.exception, SystemExit)`, `"Error:"`
  and `".pyi stub"` in output, and documents the partial-artifact state (the `.rs`, written
  first, remains on disk).
- Severity assessment: Untested error path; low runtime risk but the partial-artifact behavior
  was undocumented. The test now pins the exit contract and the documented behavior.

reuse-1:
- Disposition: Fixed
- Action: Extended `_write_output_file(output_file, src, artifact_label="output file")`
  (`fltk/fegen/genparser.py:272-285`) and replaced both inline `.pyi` try/except blocks
  (`gen_rust_cst` and `gen_rust_unparser`) with `_write_output_file(stub_path, pyi_text, ".pyi stub")`.
  The error message/exit-code contract for stub writes now lives in the one shared helper.
- Severity assessment: Maintainability — duplicated error contract across two (soon three) call
  sites; consolidating removes the divergence risk the helper was introduced to prevent.

quality-1:
- Disposition: Fixed
- Action: Added `$(EXTRA_ARGS)` to the `gen-rust-unparser` Makefile target (`Makefile:225-226`)
  and routed the `gencode` fixture-unparser regeneration through
  `$(MAKE) gen-rust-unparser ... EXTRA_ARGS="--format-config ..."` instead of an inline
  invocation (`Makefile`). Verified the rerouted target produces byte-identical fixture
  `unparser.rs` (no drift).
- Severity assessment: Quality — the target was a dead letter for `--format-config` callers and
  could silently diverge from the inline `gencode` call; closing it matches the `gen-rust-cst`
  pattern.

quality-2:
- Disposition: Fixed
- Action: Same fix as reuse-1 — `_write_output_file` gained the optional `artifact_label`
  parameter and both stub writes now call it. (reuse-1 and quality-2 are the same duplication.)
- Severity assessment: Maintainability; see reuse-1.
