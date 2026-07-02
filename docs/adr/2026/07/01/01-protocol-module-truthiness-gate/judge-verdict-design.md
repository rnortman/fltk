# Judge verdict — design review

Phase: design. Doc: `docs/adr/2026/07/01/01-protocol-module-truthiness-gate/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 3 findings, all dispositioned Fixed.

## Findings walk

### design-1 — Fixed
Claim: required keyword-only `emit_kind_literal` on the internal helpers breaks the direct caller
`tests/test_gsm2tree_py.py:496` (`TestMutatorsEmittedPyProtocol` fixture), which the design's §4
listed as untouched; consequence is ~8-10 tests failing plus an improvised, undesigned fix during
implementation.
Verification against revised design:
- §2.3 now carries the bookkeeping bullet: the fixture passes `emit_kind_literal=True`, identified
  as "the only direct caller of either private helper outside `gsm2tree.py`."
- §4 adds the matching guardrail bullet (`tests/test_gsm2tree_py.py:488-547` — fixture updated per
  §2.3, assertions unchanged).
- §5 records the fixture keyword as a resolved judgment call (no longer claims zero judgment calls).
- §2.1's no-default-on-internal-helpers decision is intact — not silently reversed.
Verification against source: fixture at `tests/test_gsm2tree_py.py:496` confirmed calling
`gen._protocol_class_for_model("Bar", model, "bar")` with no keyword; every assertion in the class
inspects mutator `FunctionDef`s (presence, signature text, ordering) — none touches the `kind`
line, so the design's "assertions are unaffected" claim holds even though the `Builtins`-backed
fixture's emitted `kind` line flips to the `Literal` form.
Assessment: fix addresses the finding at the exact sites named; the responder took the reviewer's
first suggested option and documented the choice. Accept.

### design-2 — Fixed
Claim: §4 mischaracterized `TestProtocolModuleAll` (`tests/test_gsm2tree_py.py:233-240`) as
"real-module; unaffected" when it is `Builtins`-backed; consequence is a falsified groundedness
claim in the §4 unaffected list and an unexplained output change for implementation reviewers.
Verification against revised design: §4 now splits the bullet exactly as the reviewer suggested —
`fltk/fegen/test_cst_protocol.py` (real-module, unaffected); `tests/test_gsm2tree_py.py:233-337`
(`Builtins`-backed via `tests/gsm2tree_helpers.py:69`; content flips to `Literal` form but every
assertion inspects only `__all__` and module structure); and the design-1 fixture bullet.
Verification against source: `TestProtocolModuleAll` builds via `_make_generator`
(`Builtins`-backed per `tests/gsm2tree_helpers.py` `make_generator`, `py_module=pyreg.Builtins`);
its assertions cover `__all__` presence/contents/sorting/position and `_ProtocolLabelMember`
ClassDef presence — no `kind` assertions. The corrected §4 rationale is accurate.
Assessment: fix matches the suggested correction and is source-accurate. Accept.

### design-3 — Fixed
Claim: the cited determinism guardrail (`tests/test_gsm2tree_rs.py:1144-1147`,
`test_deterministic_across_instances`) builds two fresh generators and never reuses one instance,
so it cannot catch a future protocol emission that mutates shared `_py_gen`/context state;
consequence is a claimed loud-failure safety net that is silent for the exact new state-sharing
surface (fresh-generator byte-identity tests also stay green on writes).
Verification against revised design: the responder took the stronger of the reviewer's two
options —
- §4 test 4 added: same-instance `RustCstGenerator`, `generate_protocol()` twice interleaved with
  a `generate_pyi`/`generate_rs` call, byte-identical outputs.
- §3 Determinism bullet rewritten to state accurately that the existing test is cross-instance
  only and does not exercise same-instance reuse; test 4 pins it.
- §3 context-coupling bullet corrected: read-regressions attributed to the byte-identity and
  py_module-independence tests, write-regressions to the new same-instance test, with the explicit
  note that fresh-generator tests alone would stay green on a write.
Residual note: §2.2's closing line ("the existing cross-path byte-identity test ... is the
guardrail for all of the above") remains slightly loose read in isolation, but §3 now carries the
precise attribution and §4 test 4 closes the actual gap; the reviewer's consequence is fully
addressed. Not disputed.
Assessment: fix exceeds the suggested remedy (test added, claims corrected). Accept.

## Disputed items

None.

## Approved

3 findings: 3 Fixed verified.

---

## Verdict: APPROVED

All three dispositions are Fixed, each verified against the revised design doc and spot-checked
against test source. No disposition wrong; no residual gap rising above a nit.
