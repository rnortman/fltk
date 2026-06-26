# Delta design review — notes

Reviewed: `design-delta-python-rust-isolation.md` (amends `design.md`).
Method: verified the central claims with live pyright probes against the real modules
(`fltk._native` is built; `pyright` available), and grounded every file:line reference.

## Verified TRUE (no finding)

- **D0** is correct and reproduced. With the `_native` stub present, `span.Span` resolves to
  `fltk._native.Span` and `ApplyResult[int, span.Span]` from a `terminalsrc.Span` raises the
  invariant error. With the stub removed, `reveal_type(span.Span)` = `Unknown` (pyright does NOT
  follow the `except` branch to `terminalsrc.Span`) and the error disappears — i.e. pyright's
  diagnostics/types depend on stub presence. Confirmed against `span.py:8-14`, `memo.py:22,69`.
- **D3.2/D3.3 registry mechanism** is sound. `TypeKey` is keyed by `cname` (typemodel.py:28-34),
  so all `iir.Type.make(cname="Span")` share one entry; repointing `context.py:113-123` flips
  parser/CST/protocol/unparser span annotations, and span-typed children flow through
  `model_for_item` → `self.Span.key` → `iir_type_to_py_annotation(...self.context)`
  (gsm2tree.py:619, 679-680). The hardcoded `span` *field* (gsm2tree.py:269, :900,
  gsm2tree_rs.py:358) is correctly identified as a manual edit.
- **D3.3 parser honesty** verified: `ApplyResult(0, terminalsrc.Span(...))` infers
  `ApplyResult[int, terminalsrc.Span]`; an exact `terminalsrc.Span` annotation is cast-free (0
  errors). The D4 variance argument (parser return is invariant, so `SpanProtocol` there fails
  identically to the native case) is correct.
- **D3.1 `terminalsrc.Span` side** verified: with `merge`/`intersect` retyped to `Self` and `kind`
  added, `terminalsrc.Span` (and `= terminalsrc.UnknownSpan` defaults, and
  `-> SpanProtocol: return terminalsrc.Span(...)`) ARE assignable to the refined `SpanProtocol`.

---

## design-1 — D3.1 contradicts D5.2: native Span is NOT statically assignable to `SpanProtocol`

- Section: D3.1 ("Verified by pyright: with this, `terminalsrc.Span` *and* `fltk._native.Span`
  values are assignable to a `SpanProtocol`-typed variable / parameter / return / dataclass
  field.") vs D5.2 ("Native `fltk._native.Span` is not *statically* a `SpanProtocol` …
  `line_col()` returns the native `LineColPos`, which is not assignable to `SpanProtocol`'s
  `terminalsrc.LineColPos` return").
- What's wrong: the D3.1 claim is false, and it directly contradicts D5.2 (and D4's "both runtime
  backends satisfy [SpanProtocol]"). I built the exact D3.1 refinement (`Self` merge/intersect +
  `kind: Literal[SpanKind.SPAN]`) and probed with pyright: `x: SpanProtocol = terminalsrc.Span(0,1)`
  is clean, but `x: SpanProtocol = fltk._native.Span(0,1)` fails —
  `"line_col" is an incompatible type: () -> (fltk._native.LineColPos | None) is not assignable to
  () -> (fltk.fegen.pyrt.terminalsrc.LineColPos | None)` (also `line_col_or_raise`). The `Self`/`kind`
  refinement does nothing to close the `LineColPos` nominal gap, so native is non-conformant with
  or without it. D5.2 is the correct statement; D3.1 over-generalizes runtime `isinstance`
  conformance (which only checks attribute presence) into a static-assignability claim.
- Why: `span_protocol.py:6,67-79` types `line_col`/`line_col_or_raise` with the concrete
  `terminalsrc.LineColPos`; `_native/__init__.pyi:67-68` returns the native `LineColPos`; the two
  are distinct nominal classes (cross-backend `LineColPos` is un-unified — the open
  `TODO(spanprotocol-native-linecol)`).
- Consequence: an internal contradiction in the load-bearing justification. The delta's D4 rests on
  "the only native-free type both runtime backends satisfy"; that holds at runtime but not
  statically for native. The design still *builds* (the Rust `.pyi` only *declares* `span:
  SpanProtocol`, never assigns a native value into a `SpanProtocol` slot inside pyright scope, per
  D5.2's containment — which is correct), and D6's assignability test correctly pins only the
  `terminalsrc` side. So the practical blast radius is limited, but the D3.1 prose is a false
  "verified by pyright" claim that, taken at face value, would mislead the implementer (e.g. into
  writing a native-side assignability assertion that cannot pass). Fix: delete/retract the
  "`fltk._native.Span` values are assignable" half of D3.1; state plainly that only `terminalsrc.Span`
  is statically assignable and native conforms by `.pyi` declaration + runtime `isinstance`, per D5.2.

## design-2 — D3.2's `SourceText` repoint omits the conflicting second registration → codegen crash

- Section: D3.2 ("`SourceText` registration (`context.py:125-132`): change module from … `span` to …
  `terminalsrc`."). No mention of the second registration site.
- What's wrong: `SourceText` (cname="SourceText") is registered TWICE against the same compiler
  context: once in `context.py:126-132` and again in `gsm2parser.py:78-84` (`name="SourceText"`,
  `module=("fltk","fegen","pyrt","span")`). Both use `iir.Type.make(cname="SourceText")` → identical
  `TypeKey`. `TypeRegistry.register_type` raises `ValueError("Conflicting type registration")` when
  the same key is re-registered with a *different* `TypeInfo` (context.py:21-25). Today both point at
  `span`, so it is a benign idempotent re-registration. If D3.2 repoints only `context.py` to
  `terminalsrc` and leaves `gsm2parser.py:82` at `span`, the two `TypeInfo`s differ →
  `ParserGenerator.__init__` raises at construction time.
- Why: verified registration order — `create_default_context` → `_register_builtin_types`
  (registers `SourceText`→`terminalsrc` after D3.2) runs first; `ParserGenerator.__init__`
  (gsm2parser.py:78-84, registers `SourceText`→`span`) runs second on the same registry → conflict.
  The delta's "what must change" list (D3.2/D3.3) never names `gsm2parser.py:78-84`; D3.3 only points
  at the `:55-85` range as *where to add* the new parser-local Span type.
- Consequence: a faithful, literal implementation of the delta crashes ALL Python-parser generation
  with `ValueError`, so the D6 regen (`make gencode`) cannot even run. This is a hard blocker hidden
  by an incomplete amendment. Fix: D3.2 must also change (or delete, since context now supplies it)
  the `gsm2parser.py:78-84` `SourceText`→`span` re-registration so the `_source_text` field
  annotation becomes the honest `terminalsrc.SourceText` without a key conflict.

## design-3 — Test plan (D6) does not account for in-tree, in-pyright-scope tests that pin the OLD union surface

- Section: D6 ("Original §4 tests stand except where they assert the old surface."), D3.4/D3.5
  (span field/children → `SpanProtocol`).
- What's wrong: the delta changes the protocol and Rust-`.pyi` span surface but its test plan only
  gestures at "tests that assert the old surface" without identifying the concrete, pre-existing
  suites that exist *specifically* to pin the union `terminalsrc.Span | fltk._native.Span`. These
  break and several are pyright-checked inside `make check` scope (`include=["fltk","*.py"]`):
  - `tests/test_gsm2tree_rs.py:1153` (`"import fltk.fegen.pyrt.span" in poc_pyi`), `:1156`
    (`"import fltk._native" in poc_pyi`), `:1222`
    (`"span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span" in poc_pyi`) — all contradicted
    by D3.5 (drops both imports; field → `SpanProtocol`).
  - `fltk/fegen/test_cst_protocol.py:497-561` — a dedicated suite asserting the protocol `span`
    field IS the widened union and that a `fltk._native.Span` value satisfies it (e.g. `:536`
    `def get_native_span(node) -> fltk._native.Span: return typing.cast(fltk._native.Span, node.span)`).
    This lives in `fltk/`, so it is pyright-gated by `make check`, and its premise (union widening)
    is removed by D3.4.
- Why: grep-confirmed the assertions above; `make check` pyright scope is `["fltk","*.py"]`
  (pyproject.toml). These are not "original §4 tests of this design" — they are prior-work tests the
  delta's D6 catch-all does not enumerate or give a retarget/delete contract for.
- Consequence: after implementing the delta, `make check` and the suite fail on pre-existing tests
  the design never mentions, with no guidance on what the new SpanProtocol contract should assert
  (or whether the native-pinning consumer test is deleted vs. retargeted). Risk of the implementer
  either getting stuck or silently dropping coverage. Fix: D6 should name these and state the
  intended disposition (update `test_gsm2tree_rs` `.pyi` assertions to `SpanProtocol` + dropped
  imports; rework/retire the `test_cst_protocol.py` union-widening suite into a `SpanProtocol`
  conformance assertion).

## design-4 — R2 "pyright identical with/without `_native`" is met for the pipeline but NOT repo-wide under the D8.1 keep-default (input to D8.1, not a defect)

- Section: D5.1 (pyright stability over the generated pipeline), D3.7/D8.1 (keep `span.py` selector
  and `span_protocol.AnySpan` native probe).
- What's wrong / context: D5.1's claim is verified TRUE for the *generated* parser/CST/protocol/
  unparser modules (they will name neither `span` nor `_native`; `SpanProtocol` resolves through
  `terminalsrc` only). But `span.py:8-14` (`span.Span` flips `fltk._native.Span` ↔ `Unknown`) and
  `span_protocol.py:89-94` (`AnySpan` flips `Span | _RustSpan` ↔ `Span`) remain in `make check`
  pyright scope and remain stub-sensitive. The user's R2 (authoritative) says "Pyright should
  produce the same results when analyzing Python code whether the Rust backend is importable or
  not." Under the delta's stated D8.1 *default* ("keep both"), that whole-repo property is not fully
  satisfied; it is only satisfied if D8.1 is resolved toward purge.
- Why: confirmed by the D0 probe (`span.Span` Unknown↔native) and `span_protocol.py:89-94`.
- Consequence: the load-bearing R2 acceptance criterion's full (repo-wide) satisfaction hinges on
  the D8.1 decision; this is the substance of that open question. Flagged only so the user's D8.1
  judgment is made with the repo-wide-vs-pipeline scope of R2 explicit — not as a defect in the
  delta's reasoning (the delta surfaces exactly this tradeoff in D8.1, which is a deliberate
  user-judgment item).

---

## Groundedness spot-checks (all confirmed)

- D3.1 `kind` already on both backends: terminalsrc.py:58, `_native/__init__.pyi:74-75` ✓.
- D3.1 contravariance claim (`merge`/`intersect` declare `other: SpanProtocol`): span_protocol.py:52,59 ✓.
- D3.4 `_protocol_span_class` kind-marker (gsm2tree.py:975-988) and span children via registry ✓.
- D3.5 Rust `.pyi`: span field hardcoded union at gsm2tree_rs.py:358; imports gsm2tree_rs.py:329-331;
  no other `fltk._native`/`span` reference in the stub body ✓ (so the "drop if unused" is feasible).
- D3.6 unparser: span_type `cname="Span"` (gsm2unparser.py:87), `is_span` guard helper
  (gsm2unparser.py:380-394), TYPE_CHECKING span import (gsm2unparser.py:1862-1872) ✓.
- D3.3 construction unchanged: `_make_span_expr` emits `terminalsrc.Span.with_source`
  (gsm2parser.py:284-294); `_source_text` emits `terminalsrc.SourceText` (gsm2parser.py:120-137) ✓.
- Implementation-log "what stands" claims (increments 1,3,4,5,6,7-10 committed; §2.5/increment-11
  blocked) match HEAD source ✓.
