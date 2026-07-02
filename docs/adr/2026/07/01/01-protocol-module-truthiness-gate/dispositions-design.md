# Dispositions: design review round 1 — protocol-module-truthiness-gate

Findings from `notes-design-design-reviewer.md`. Each fact-checked against source at HEAD
c03a801 before disposition.

design-1:
- Disposition: Fixed
- Action: Verified: `tests/test_gsm2tree_py.py:496` (`TestMutatorsEmittedPyProtocol` fixture)
  calls `gen._protocol_class_for_model("Bar", model, "bar")` directly and would raise `TypeError`
  under the required keyword-only parameter. Added a §2.3 bookkeeping bullet designating the fix:
  the fixture passes `emit_kind_literal=True` (matches the new public default; the class asserts
  only mutator stubs and method ordering, never the `kind` line, so assertions are unaffected
  even though the `Builtins`-backed fixture's emitted `kind` line changes from `object` to the
  `Literal` form). Added a matching §4 guardrail bullet (`tests/test_gsm2tree_py.py:488-547`) and
  updated §5 to record the fixture keyword as a resolved judgment call. Kept the
  no-default-on-internal-helpers decision (§2.1) intact rather than silently reversing it.
- Severity assessment: Implemented as written, the suite would break in a test class the design
  claimed was untouched (~10 tests), forcing an undesigned improvised fix during implementation.
  Correctly caught; the exploration's caller sweep genuinely missed direct private-helper callers.

design-2:
- Disposition: Fixed
- Action: Verified: `TestProtocolModuleAll` (`tests/test_gsm2tree_py.py:233`) builds its
  generator via `_make_generator`, which is `Builtins`-backed (`tests/gsm2tree_helpers.py:69`) —
  not real-module as §4 claimed. Split the inaccurate §4 bullet into three:
  `fltk/fegen/test_cst_protocol.py` (genuinely real-module, unaffected);
  `tests/test_gsm2tree_py.py:233-337` (`Builtins`-backed; module content flips to the `Literal`
  form under the new default, but every assertion inspects only `__all__` and module structure,
  so it passes unchanged); and the design-1 fixture bullet.
- Severity assessment: No test would have failed, but the design's stated safety rationale
  ("real-module ... unaffected") was factually wrong, undermining trust in the §4 unaffected
  list and leaving the suite's output change unexplained for implementation reviewers.

design-3:
- Disposition: Fixed
- Action: Verified: `test_deterministic_across_instances`
  (`tests/test_gsm2tree_rs.py:1144-1147`) constructs two fresh `RustCstGenerator` instances and
  calls `generate_protocol()` once each — zero same-instance reuse, so it cannot guard the new
  state-sharing surface. Took the reviewer's stronger option: added new test 4 to §4
  (same-instance `RustCstGenerator`, `generate_protocol()` twice interleaved with a
  `generate_pyi`/`generate_rs` call, outputs byte-identical), rewrote the §3 Determinism bullet
  to state accurately what the existing test does and does not cover, and corrected the §3
  context-coupling bullet to attribute read-regressions to the byte-identity/independence tests
  and write-regressions to the new same-instance test (the fresh-generator tests alone would
  stay green on a write).
- Severity assessment: The design's claimed loud-failure guardrail was silent for the exact
  failure mode the change introduces (future protocol emission mutating shared `_py_gen`/context
  state, producing second-call-divergent output). A one-test addition closes the gap.
