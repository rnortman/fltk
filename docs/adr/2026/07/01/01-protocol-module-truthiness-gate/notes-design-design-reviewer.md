# Design review findings: protocol-module-truthiness-gate

Verified at HEAD c03a801. The core of the design checks out against source: the gate is at
`fltk/fegen/gsm2tree.py:915` inside `_protocol_class_for_model`; the throwaway workaround is at
`fltk/fegen/gsm2tree_rs.py:445-449` with the docstring paragraph at 435-443; `self._py_gen` is
`Builtins`-backed (`gsm2tree_rs.py:177-181`); `pyreg.Builtins` has empty falsy `import_path`
(`fltk/iir/py/reg.py:16`); `NodeKind` is emitted unconditionally (`gsm2tree.py:747`); the two
non-test callers are `genparser.py:248` and `gsm2tree_rs.py:453`; the TODO.md entry is at lines
55-57 and does misname the containing method. The context-inertness argument in §2.2 also
verifies: `TypeKey` is structural (`fltk/iir/typemodel.py:28-33,72-79`), so every
`Type.make(cname="Span")` shares one key, and `iir_type_to_py_annotation`
(`fltk/iir/py/compiler.py:49-74`) resolves it through the `SpanProtocol` registration present in
every `create_default_context()` (`fltk/iir/context.py:113-126`); protocol emission performs no
registry writes. Findings below.

## design-1: Required-keyword change breaks an existing direct test caller the design says is untouched

- **Section**: §2.1 ("`_protocol_class_for_model(...)` — required keyword on the internal helpers
  (no default)") together with §4 ("Existing tests that must keep passing unchanged").
- **What's wrong**: `tests/test_gsm2tree_py.py:491-496` (`TestMutatorsEmittedPyProtocol` fixture)
  calls the internal helper directly: `gen._protocol_class_for_model("Bar", model, "bar")`. With
  `emit_kind_literal` as a required keyword-only parameter, this fixture raises `TypeError`,
  failing all ~8 tests in that class. The design's test plan enumerates test-file impact
  exhaustively (§2.3/§4) and lists only the `tests/test_gsm2tree_rs.py:1132-1135` docstring
  update; it never mentions this caller. §5 says "Open questions: None," yet the implementer must
  now make an undesigned choice for this call site (pass `emit_kind_literal=True`? `False`? note
  the fixture's generator is `Builtins`-backed via `tests/gsm2tree_helpers.py:69`, so `True`
  changes the fixture class's emitted `kind` line relative to today).
- **Why (source-backed)**: `tests/test_gsm2tree_py.py:496`; `tests/gsm2tree_helpers.py:67-69`.
  The exploration's caller sweep only covered `gen_protocol_module`/`gen_protocol_module_text`
  and `CstGenerator(...)` construction sites (exploration §"All callers..."), not direct callers
  of the private helpers — the design inherited that blind spot.
- **Consequence**: Implemented as written, the suite breaks in a class the design promised was
  untouched; the fix gets improvised outside the design (and the "no defaults on internal
  helpers" decision may get silently reversed to make the test pass).
- **Suggested fix**: Add this call site to §2.3 bookkeeping: update the fixture to
  `gen._protocol_class_for_model("Bar", model, "bar", emit_kind_literal=True)` (the tests assert
  only mutator stubs, so `True` keeps assertions valid), or state a deliberate decision to give
  the internal helpers the same `True` default.

## design-2: §4 mischaracterizes `tests/test_gsm2tree_py.py` protocol tests as "real-module"

- **Section**: §4, "`fltk/fegen/test_cst_protocol.py`, `tests/test_gsm2tree_py.py:234-240` —
  real-module protocol suites; unaffected by the defaulted keyword."
- **What's wrong**: `TestProtocolModuleAll` (`tests/test_gsm2tree_py.py:233-240`) builds its
  generator with `_make_generator`, which is `Builtins`-backed
  (`tests/gsm2tree_helpers.py:67-69`) — not real-module. This suite therefore currently exercises
  the degraded path (`kind: object`), and under the new `True` default its generated module
  content flips to the `Literal` form. Its assertions inspect only `__all__`, so it happens to
  keep passing, but the design's stated reason it is safe ("real-module ... unaffected") is
  factually wrong, and it contradicts the exploration's claim that every test-file `Builtins`
  `CstGenerator` "does not touch the protocol path" (exploration §"All callers...", which the
  design cites as exhaustive).
- **Consequence**: Low direct risk (assertions still pass), but the design's groundedness claim
  about the caller sweep is falsified at two points in the same file (this and design-1's line
  496) — the implementer cannot trust §4's "unaffected" list without re-checking, and a reviewer
  of the implementation may flag the unexplained behavior change in this suite's output.
- **Suggested fix**: Correct the §4 bullet: `test_cst_protocol.py` is real-module;
  `test_gsm2tree_py.py:234-240` is `Builtins`-backed and keeps passing only because it asserts
  `__all__` contents, which the parameter does not affect.

## design-3: The cited "repeat-call determinism" guardrail does not test repeat calls on a reused generator

- **Section**: §3 ("**Determinism**: reusing `self._py_gen` across `generate_protocol` calls is
  covered by the existing repeat-call determinism tests (`tests/test_gsm2tree_rs.py:1143-1147`)").
- **What's wrong**: The cited test is `test_deterministic_across_instances`
  (`tests/test_gsm2tree_rs.py:1144-1147`): it constructs **two fresh `RustCstGenerator`
  instances** and calls `generate_protocol()` once on each. It never calls `generate_protocol`
  twice on one instance, so it exercises exactly zero reuse of a single `_py_gen` across calls —
  the new state-sharing surface the change introduces (one `_py_gen` now serving `.rs`/`.pyi`
  emission *and* repeated protocol emission). Today that surface is provably inert
  (protocol emission does no registry writes), but the design explicitly leans on this test as
  the loud-failure guardrail for future regressions ("if a future change makes it write or read
  either ... fail loudly"), and for same-instance reuse it would not fail at all.
- **Consequence**: A future change that makes protocol emission mutate `_py_gen`/context state
  (e.g. memoizing via `iir_type_for_rule`) could produce order-dependent or second-call-divergent
  output while both cited guardrails stay green (the byte-identity CLI tests also construct fresh
  generators per invocation, `fltk/fegen/test_genparser.py:593-635`). The design's claimed safety
  net is thinner than stated.
- **Suggested fix**: Either soften the claim, or (one line) extend the determinism test / add to
  the §4 new-test list: `gen = RustCstGenerator(g); assert gen.generate_protocol() ==
  gen.generate_protocol()` — ideally after a `generate_pyi`/`generate_rs` call to pin
  cross-method inertness of the shared `_py_gen`.
