# Design review — Clean Protocol-Only Consumer API

Reviewer notes. Adversarial fact-check of `design.md` against source (base f1d9745) + probe.
Authoring: concise, source-backed, consequence-first. Each finding has ID / quote / defect / evidence /
consequence / fix.

## Verification summary (claims that CHECK OUT — recorded so they are not re-litigated)

- **Core mechanism empirically reproduced on real Protocol classes** (not just dataclasses as probe D4
  did). Ran pyright 1.1.402 / py3.10 against `typing.Protocol` classes with
  `kind: Literal[NodeKind.X] = NodeKind.X` and a separate `SpanKind.SPAN` on a `Span` Protocol:
  - Runtime read `Item.kind` → `NodeKind.ITEM` on the class object. PASS (Protocol class attr is a real
    runtime value, so `cst.<Node>.kind` evaluates at runtime).
  - Shape 2 `match child.kind: case Item.kind / Trivia.kind / Span.kind:` narrows to Item/Trivia/Span,
    **0 errors**. PASS.
  - Shape 1 `assert item.kind == Item.kind` narrows `Item|Trivia|Span → Item`, **0 errors**. PASS
    (probe only tested the `if` form D2; the `assert` form Shape 1 actually uses is confirmed here).
  This closes the one untested gap (Protocol vs dataclass) in `narrowing-mechanism-probe.md`. The design's
  central runtime+static claim (§0, §2.3b, §2.6) holds.
- **Span is a real distinct Rust pyclass, not opaque.** `src/span.rs:56` `#[pyclass(frozen,eq,hash)]
  Span`; `eq`/`hash` use only `(start,end)` (`span.rs:64-77`). The probe's C1 statement "Rust Span is
  opaque (`span: PyObject`)" is STALE; the design correctly overrides it (§1.4, §2.2 "OPEN DETAIL —
  RESOLVED") and treats Rust `Span` as `fltk._native.Span`, a class distinct from `terminalsrc.Span`.
  Good — design did not blindly trust the probe here.
- **Backend separator-child types confirmed.** Python concrete: `terminalsrc.Span`
  (`fltk_parser.py:342` appends `item0.result`, a `terminalsrc.Span`). Rust: `fltk._native.Span`
  (node `span`/separator slots are `PyObject`, `cst_fegen.rs:144,153-163`; tests build them via
  `_span(...)`=`fltk._native.Span`, `tests/test_rust_cst_poc.py:310,385`). The Python-concrete `Span` IS
  the shared `terminalsrc.Span` (no separate concrete `Span` class), so `cst.Span.kind` and a
  Python-produced separator resolve to the SAME `SpanKind.SPAN` — design §1.4 is correct.
- **Canonical-name bridge reuse is real.** `_emit_cross_backend_eq_hash` (gsm2tree.py:100-132),
  `_node_kind_enum`/`_emit_node_kind_canonical_name_assignments` (134-156),
  `_emit_label_canonical_name_assignments` (158-169), Rust `_emit_rust_cross_backend_eq_hash`
  (gsm2tree_rs.py:150-179), `_kind_getter` (349-358). All cited locations exist and match the design's
  description. AC 7/AC 12 bridge extension to `SpanKind` is consistent with the existing pattern.
- **Existing violations confirmed** at the cited lines: dual import `fltk2gsm.py:8` + TYPE_CHECKING
  shadow `:11-12`; `typing.cast` `:63,:75`; `# noqa: S101` `:62,70,74,78`; protocol `Label` members are
  bare `ClassVar[object]` (`fltk_cst_protocol.py:14,39`...); `kind` annotation-only (gsm2tree.py:489);
  TYPE_CHECKING-only `NodeKind` import (gsm2tree.py:451-454, emitted fltk_cst_protocol.py:8-9).
  Root-cause §1 is accurate.

## Findings

### design-1 — Protocol `Label` sentinel: design under-specifies its `__eq__`/`__hash__`; if not an exact copy of the bridge (incl. `NotImplemented` + canonical-name `__hash__`), AC 6/7/10 symmetry breaks

- **Quote** (§2.3c): "a tiny runtime sentinel carrying `_fltk_canonical_name = "<ClassName>.Label.<UPPER>"`
  and the bridge `__eq__`/`__hash__`. ... A value typed `object` round-trips (the bridge never inspects
  the static type)."
- **Defect / why.** Shape 1 (LOCKED model, `fltk2gsm.py:45-51,62,65,67,70,74`) writes comparisons with
  the **concrete** label as the LEFT operand: `item_label == cst.Items.Label.ITEM`,
  `labeled_children[0][0] in (cst.Items.Label.NO_WS, ...)`. Python evaluates `concrete.__eq__(sentinel)`
  first; the concrete enum `__eq__` (gsm2tree.py:120-124) resolves via `getattr(other,
  '_fltk_canonical_name', None)` and returns a result — so the concrete side wins and the sentinel's own
  `__eq__` is never reached in these sites. That part works. BUT AC 7 requires **both operand orders**
  (symmetry) and AC 6 requires `==`/`!=` usability generally, where the sentinel IS the left/subject
  operand. The design says "give the sentinel a bridge `__eq__`/`__hash__`" but does not pin the shape.
  The existing bridge returns `NotImplemented` for foreign operands (gsm2tree.py:124) precisely so the
  other operand gets a reflected turn, and `__hash__` = `hash(self._fltk_canonical_name)`
  (gsm2tree.py:131). A naive sentinel `__eq__` that returns `True/False` for all foreign operands, or an
  identity/`object`-default `__hash__`, would: (a) make `sentinel == non_matching_concrete` wrong or block
  reflected resolution, (b) make equal members hash UNEQUAL → AC 7 hash clause fails, set/dict use breaks.
- **Consequence.** Silent AC 6/7/10 failures on the Label axis: symmetric equality and hash-consistency
  not guaranteed; this is the same "canonical-string is the load-bearing invariant" trap (§3) but on the
  Label sentinel, which the design does not bind tightly.
- **Fix.** State explicitly that the sentinel reuses the EXACT `_emit_cross_backend_eq_hash` shape
  (identity fast-path; `getattr(other,'_fltk_canonical_name',None)`; `NotImplemented` for foreign;
  `__hash__ = hash(self._fltk_canonical_name)`). Add a test (extend plan #5/#7) asserting BOTH operand
  orders + hash equality for a matching AND a non-matching protocol Label member vs a concrete one.

### design-2 — Rust `Span.kind` getter imports pure-Python `terminalsrc` from inside `_native`; "exactly like UNKNOWN_SPAN_CACHE" is the WRONG direction and the acyclicity invariant is unstated

- **Quote** (§2.2): "import and return the shared Python `SpanKind.SPAN` directly
  (`py.import("fltk.fegen.pyrt.terminalsrc")?...`), cached in a `GILOnceCell` exactly like
  `UNKNOWN_SPAN_CACHE`."
- **Defect / why.** `UNKNOWN_SPAN_CACHE` goes generated-Python → `fltk._native` (cst_fegen.rs:158). The
  proposed getter inverts it: `_native` → pure-Python `fltk.fegen.pyrt.terminalsrc`. `terminalsrc.py`
  (read in full) imports only `bisect, re, dataclasses, typing` — NO `fltk._native` — so no cycle TODAY.
  But the design frames it as identical to UNKNOWN_SPAN_CACHE (it is the opposite direction) and never
  records the load-bearing invariant that `terminalsrc` must stay free of any `fltk._native` import.
- **Consequence.** Low now, latent later: if a future change makes `terminalsrc` import the native ext,
  the cached cross-direction import becomes a cycle (import deadlock / init failure) at first
  `Span.kind` access — a non-obvious cross-language breakage. The §2.2 Rust-`#[pyclass] SpanKind`
  fallback is correctly retained as the escape hatch.
- **Fix.** Reframe as "same `GILOnceCell` pattern, opposite import direction"; add invariant
  "`terminalsrc` must not import `fltk._native`"; keep the Rust-`SpanKind` fallback.

### design-3 — `Span.kind` `compare=False, hash=False`: correct and should be stated as REQUIRED, not merely "defensive"

- **Quote** (§2.1): "`compare=False, hash=False` ... the constant would not change `==`, but excluding it
  is defensive and documents intent."
- **Defect / why.** `terminalsrc.Span` is a `@dataclass(frozen,eq,slots)` whose `__eq__` is generated
  from compared fields; `_source` is already `compare=False, hash=False` (terminalsrc.py:13) to preserve
  the documented "sourceless sentinel `==` source-bearing span at same position" invariant
  (span.rs:51-53 mirrors it). Adding a third compared field, even a constant, is the kind of change the
  invariant guards; excluding it is mandatory to keep that contract robust, not optional polish. (Because
  `kind` is constant the `==` result is unchanged either way, so the design's literal claim is true — the
  wording just understates necessity.)
- **Consequence.** Negligible runtime effect (constant). Flagged so a future edit doesn't "tidy" the field
  back into compare/hash. Keep as written.

### design-4 (verification note, non-blocking) — Option-A structural-mismatch claim confirmed against source

- **Quote** (§2.3c / test #9): protocol `Label` "stays a **plain class** (not `enum.Enum`)", so
  `test_boundary_probe_documents_label_mismatch` still passes.
- **Verified.** That test (`test_cst_protocol.py:298-376`, `_CASTLESS_PROBE_FIXTURE` :348-356) asserts
  `fltk_cst` (nested `Label(enum.Enum)`) is NOT assignable to `cstp.CstModule` (nested plain `class
  Label`). Adding a runtime value to a plain-class attribute does not make it an enum → nominal mismatch
  preserved. Also confirmed: `cst.X.Label.Y` is only used in `==`/`in` (never `match` value-pattern) in
  the model consumer, so static type `object` is fine for those sites. No defect; Option A sound on the
  Label axis. (Recorded so it is not re-questioned.)

### design-5 (verification note, non-blocking) — "no eager concrete-backend import" test must whitelist `terminalsrc`

- **Quote** (test #4 / §3): assert `"fltk.fegen.fltk_cst" not in sys.modules`, "no `fltk._native` eager
  import", protocol "imports only `enum`, `typing`, `terminalsrc`."
- **Verified / caveat.** The protocol module already imports `fltk.fegen.pyrt.terminalsrc`
  (fltk_cst_protocol.py:6) and §2.1 adds `SpanKind` there — so importing the protocol module imports
  `terminalsrc`, which is EXPECTED and allowed (it is the shared runtime, not a concrete backend, and
  carries no `fltk._native`/`fltk_cst` import). Test #4 must assert absence of `fltk_cst` AND
  `fltk._native` specifically, not an over-strict "enum+typing only" allowlist (which would FALSE-FAIL on
  `terminalsrc`). §3 already lists `terminalsrc` as allowed, so the design is internally consistent;
  flagged to prevent a test author mis-implementing #4.

## Coverage / scope check

- Shapes 1 & 2 (LOCKED anchor): reproduced; both empirically pyright-clean here. AC 8/8a/11 covered by
  test #1 (two structurally different traversals). PASS.
- AC 12 (cross-backend dual-shape, three enum classes incl. Span axis): §2.2/§2.6/§1.4 + test #6 cover
  it; canonical-name bridge + concrete-instance-as-subject (probe E3) correctly applied; Span axis
  collapses to a shared `SpanKind.SPAN`. PASS, subject to design-2 import-invariant note.
- AC 6/7/10 (runtime values, cross-backend eq/hash, additive Label): covered; **design-1** is the place to
  tighten (sentinel `__eq__`/`__hash__` must mirror the bridge incl. `NotImplemented` + symmetric hash).
- AC 1-5/9 (`fltk2gsm.py` clean + behavior-equiv): §2.4/§2.5 covered; S101 drop via `ignore` list is the
  right realization.
- Rejected approaches (accessor / runtime_checkable / TypeIs-primary): §0 honors all three; none
  reintroduced. The design explicitly overrides notes-design-user.md's stale "COMMITTED MECHANISM: TypeIs"
  in favor of native `.kind` per the LOCKED requirements + probe — correct resolution of that
  contradiction, not a finding.
- Scope: five production changes map 1:1 to requirements; no bonus features, no premature abstraction.

## Bottom line

Sound and grounded; the core mechanism is empirically reproduced on real Protocol classes (closing the
probe's dataclass-only gap), Shape 1 + Shape 2 are clean (single protocol import, native `.kind`, no
cast/predicate/accessor/runtime_checkable/suppression), the `SpanKind` addition to frozen+slots
`terminalsrc.Span` is sound, the Python-shared-Span vs distinct-Rust-Span claim is correct, and AC 12 is
correctly designed. One real correctness gap to close — **design-1** (pin the protocol `Label` sentinel's
`__eq__`/`__hash__` to the exact bridge contract). **design-2** (Rust Span.kind import-direction
invariant) should be tightened. design-3/4/5 are wording/verification notes.
