# Implementation Log: Clean Protocol-Only Consumer API

## Increment 2 — Rust `Span.kind` getter returning shared Python `SpanKind.SPAN` (§2.2) (commit 16f9582)

- `src/span.rs:1-11`: Added `use pyo3::sync::GILOnceCell` and `SPAN_KIND_SPAN_CACHE: GILOnceCell<PyObject>` static with acyclicity comment.
- `src/span.rs:251-266`: Added `#[getter] fn kind` to `#[pymethods] impl Span`; uses `SPAN_KIND_SPAN_CACHE.get_or_try_init` to import and cache `fltk.fegen.pyrt.terminalsrc.SpanKind.SPAN`. Returns `clone_ref` of cached object — same Python object as `terminalsrc.Span.kind`, so identity holds and equality is trivially satisfied.
- All 463 tests pass; Rust extension builds cleanly.

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
