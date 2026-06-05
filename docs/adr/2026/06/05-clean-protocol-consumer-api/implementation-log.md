# Implementation Log: Clean Protocol-Only Consumer API

## Increment 2 — Rust `Span.kind` getter returning shared Python `SpanKind.SPAN` (§2.2) (commit 16f9582)

- `src/span.rs:1-11`: Added `use pyo3::sync::GILOnceCell` and `SPAN_KIND_SPAN_CACHE: GILOnceCell<PyObject>` static with acyclicity comment.
- `src/span.rs:251-266`: Added `#[getter] fn kind` to `#[pymethods] impl Span`; uses `SPAN_KIND_SPAN_CACHE.get_or_try_init` to import and cache `fltk.fegen.pyrt.terminalsrc.SpanKind.SPAN`. Returns `clone_ref` of cached object — same Python object as `terminalsrc.Span.kind`, so identity holds and equality is trivially satisfied.
- All 463 tests pass; Rust extension builds cleanly.

## Increment 3 — Protocol module: runtime `NodeKind`/`kind`/`Label` + `Span` class + `S101` drop + `fltk2gsm` rewrite (§2.3, §2.4, §2.5) (commit d373749)

- `fltk/fegen/gsm2tree.py`: `gen_protocol_module` rewritten to emit protocol-local runtime `NodeKind` (via existing `_node_kind_enum()` + canonical-name assignments; replaces `TYPE_CHECKING`-guarded concrete import), `import enum` added; `_protocol_class_for_model` updated to emit `kind: Literal[NodeKind.X] = NodeKind.X` (runtime default) instead of annotation-only; new `_ProtocolLabelMember` sentinel class emitted into protocol module (cross-backend `__eq__`/`__hash__`; `NotImplemented` for foreign operands; canonical-name `__hash__`); `_protocol_class_for_model_with_assignments` wrapper emits post-class `Label.MEMBER = _ProtocolLabelMember(...)` assignments; new `_protocol_span_class` emits `class Span(typing.Protocol)` with `kind: Literal[SpanKind.SPAN] = SpanKind.SPAN`; `_cst_module_protocol` gains `Span` property; `_emit_protocol_label_member_class` emits the sentinel class body.
- `fltk/fegen/fltk_cst_protocol.py`: Regenerated — now has protocol-local `NodeKind` enum with runtime members + canonical strings, `_ProtocolLabelMember` class, `kind = NodeKind.X` defaults on all Protocol nodes, `Label.MEMBER = _ProtocolLabelMember(...)` post-class assignments, `class Span(typing.Protocol)` with `SpanKind.SPAN` kind, `Span` property on `CstModule`. No `TYPE_CHECKING` block. Ruff-clean after `make fix`.
- `fltk/fegen/fltk2gsm.py`: Rewritten as clean protocol-only consumer — single `from fltk.fegen import fltk_cst_protocol as cst` import; `typing.cast` at former `:63`/`:75` replaced with `assert item.kind == cst.Item.kind` (bare, no noqa); all `# noqa: S101` removed; `import typing` and `TYPE_CHECKING` block deleted.
- `pyproject.toml`: Added `"S101"` to `ignore` list (§2.5) so Shape-1 narrowing asserts are bare project-wide. Removed 57 now-unused `# noqa: S101` directives across the codebase via `ruff check --fix`.
- `fltk/fegen/test_cst_protocol.py`: Updated `test_protocol_module_has_one_class_per_rule` (adds `NodeKind`, `_ProtocolLabelMember`, `Span` to expected set); updated `test_cst_module_protocol_has_property_per_rule` (adds `Span`); renamed `test_fltk2gsm_does_not_import_protocol_at_runtime` → `test_fltk2gsm_imports_protocol_not_concrete_at_runtime` (inverted: protocol IS imported at runtime, concrete `fltk_cst` is NOT).
- All 852 tests pass; ruff clean; pyright 0 errors.
- Deviation: bootstrap regeneration was needed — `fltk2gsm.py` now requires the new protocol module to run, but the generator uses `fltk2gsm.py` to parse. Resolved via an inline `_DirectCst2Gsm` that uses `fltk_cst` (concrete) directly for the one-time regeneration. After regeneration, the loop is broken: `fltk2gsm.py` → protocol module (which is now correct) → works.

## Increment 1 — `terminalsrc.SpanKind` + `Span.kind` field (§2.1) (commit 16c43da)

- `fltk/fegen/pyrt/terminalsrc.py:9-29`: Added `SpanKind(enum.Enum)` with `SPAN = enum.auto()`,
  bare `_fltk_canonical_name: str` annotation (pyright-visible), and cross-backend `__eq__`/`__hash__`.
- `fltk/fegen/pyrt/terminalsrc.py:30`: Post-class assignment `SpanKind.SPAN._fltk_canonical_name = "SpanKind.SPAN"`.
- `fltk/fegen/pyrt/terminalsrc.py:47`: Added `kind: Literal[SpanKind.SPAN]` field with
  `repr=False, compare=False, hash=False` — preserves existing repr/equality/hash contracts.
- Added `import enum` and `from typing import ..., Literal` to imports.
- All 463 existing tests pass; ruff and pyright clean on changed file.
- Deviation: design did not mention `repr=False`; added because without it the existing
  `test_repr` test (which asserts `"Span(start=1, end=5)"`) would fail. `repr=False` is
  consistent with `_source` which also uses `repr=False`.
