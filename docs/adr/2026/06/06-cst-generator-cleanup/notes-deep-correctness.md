# Deep correctness review — cst-generator-cleanup (2dd27f0..b72aea6)

No findings.

Verified (not just read):
- Quintet extraction (C) is byte-identical: regenerated fegen + toy artifacts via genparser, applied `make fix` order (ruff check --fix, then format) — zero diff vs committed `fltk_cst.py`, `fltk_cst_protocol.py`, `toy_cst*.py`. (Note: format-before-check order does NOT converge; the committed flow's order is load-bearing.)
- Label-free path (B) exec'd end-to-end: generated concrete module compiles/imports, `append`/`extend`/`child()` behave correctly at runtime, no `Foo.Label` attribute on either backend's surface, `tuple[None, T]` annotations are runtime-safe without `from __future__ import annotations` (concrete module lacks it; `tuple.__class_getitem__` accepts `None`).
- `__all__` (A): insertion-point scan correctly matches the `if typing.TYPE_CHECKING:` block (`ast.Attribute` test shape confirmed against `pygen.if_(pygen.expr("typing.TYPE_CHECKING"), ...)`); `default=-1` fallback is unreachable while any import exists, and reachable only when no `__future__` import exists, so it cannot displace one. `__all__` contents derive from the same `rule_models` iteration as class emission — no drift path. Set-union dedup is sound for current names.
- No generic runtime access to `<NodeClass>.Label` anywhere in fltk/unparse, gsm2parser, or pyrt — removing the empty enum cannot break in-tree runtime paths; parser emission references `Label.X` only for labeled items, which label-free nodes have none of.
- `concrete_body_for` unknown-method `ValueError` is unreachable from `_emit_label_quintet` (fixed five method names); `body_for` returns fresh non-empty lists, so no AST-node aliasing or empty-FunctionDef hazard.
- New tests + `fltk/fegen/test_cst_protocol.py`: 29 passed.

Pre-existing (not introduced by this diff, noted for completeness): a grammar rule named `span`, `node_kind`, or `cst_module` would collide with the fixed `Span`/`NodeKind`/`CstModule` protocol classes (duplicate ClassDefs); `__all__`'s set-union silently dedupes the name but the collision predates this change.
