# Deep correctness review — clean-protocol-consumer-api

Reviewed: 1e78b73..bc42280. Authoring note: concise, precise, complete, unambiguous.

Scope: logic / control flow / data flow of the diff. Files: `terminalsrc.py`, `src/span.rs`,
`gsm2tree.py`, generated `fltk_cst_protocol.py`, `fltk2gsm.py`, `pyproject.toml`, tests.

## No findings.

Verified the load-bearing correctness claims empirically (uv run, debug Rust build, full suite):

- `SpanKind` enum has exactly one member `SPAN`; the `_fltk_canonical_name: str` body line is an
  annotation, not a member. `==`/`hash` cross-backend bridge correct in both operand orders;
  `NotImplemented` returned for foreign operands (`SpanKind.SPAN == 5` → False, `!= 5` → True).
- `Span.kind` field added after defaulted `_source` (no default-ordering TypeError); `compare=False,
  hash=False` preserved — `Span(1,5) == Span(1,5,'x')` and equal hashes hold; `kind` excluded from repr.
- Protocol `_ProtocolLabelMember` and concrete `enum.Enum` Label emit IDENTICAL canonical strings
  (`"<Class>.Label.<UPPER>"`); cross-type `==` resolves both orders, equal members hash equal, foreign
  operand `!=` correct. Label member declaration (nested `Label` body) and post-class sentinel
  assignment both iterate `sorted(model.labels.keys())` + `.upper()` — in lockstep, no drift.
- Protocol-local `NodeKind` reuses the same generator helpers as concrete `NodeKind`; canonical strings
  identical, so `item.kind == cst.Item.kind` narrows (pyright 0 errors on `fltk2gsm.py`) AND evaluates
  True at runtime via the concrete-side bridge `__eq__` (concrete instance is LEFT/subject operand).
- Protocol import isolation holds: after `import fltk_cst_protocol`, neither `fltk.fegen.fltk_cst` nor
  `fltk._native` is in `sys.modules`. Acyclicity invariant (`terminalsrc` imports no native) intact.
- Rust `Span.kind` getter (GILOnceCell) returns the *shared* Python `SpanKind.SPAN` object: `is` and
  `==` against `SpanKind.SPAN`/`cst.Span.kind` both True for a `fltk._native.Span` instance.

Control/data-flow note (not a defect): replacing `typing.cast("cst.Item", item)` with
`assert item.kind == cst.Item.kind` adds a runtime check the cast lacked. In the interleaved walk the
preceding `assert item_label == cst.Items.Label.ITEM` already guarantees the arm is an `Item`, so the
new assert is always satisfied on valid data and only converts a previously-silent invariant violation
into an AssertionError — a strict improvement, not a regression.

Full suite: 899 passed. `fltk2gsm.py`: pyright 0 errors, ruff clean.
