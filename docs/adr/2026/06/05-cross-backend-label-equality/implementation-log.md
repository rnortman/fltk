# Cross-Backend Label Equality — Implementation Log

## Increment 1 — Python `Label` `__eq__`/`__hash__`/`_fltk_canonical_name` in `gsm2tree.py` (commit 600bfc6)

- `fltk/fegen/gsm2tree.py:112-141`: in `py_class_for_model`, after emitting `enum.auto()` members, now emits on each `Label(enum.Enum)`:
  - `_fltk_canonical_name` property (instance-resolved, returns `f"<ClassName>.Label.{self.name}"`)
  - `__eq__` with `other is self` fast path, same-type `self.name == other.name` fast path, canonical-name cross-type path via `getattr(other, "_fltk_canonical_name", None)`, and `NotImplemented` for foreign operands
  - `__hash__` returning `hash(self._fltk_canonical_name)`
- `fltk/fegen/fltk_cst.py`: regenerated; all Label enums now carry the three methods (verified at lines 13-27, 74-88, 157-171, 220-234, 352-366, etc.)
- `fltk/fegen/fltk_cst_protocol.py`: regenerated (no semantic change to protocol; protocol Label uses `ClassVar[object]`)
- 783 tests pass; pyright 0 errors; ruff clean on modified files.
- `fltk_parser.py` was NOT regenerated (parser doesn't depend on Label eq/hash; pre-existing committed file retained).

