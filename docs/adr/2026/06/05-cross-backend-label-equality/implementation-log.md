# Cross-Backend Label Equality — Implementation Log

## Increment 2 — Rust `Label` `__eq__`/`__hash__`/`_fltk_canonical_name` in `gsm2tree_rs.py` (commit 0d8c815)

- `fltk/fegen/gsm2tree_rs.py:152`: dropped `eq, hash` from `#[pyclass(frozen, name = ...)]` on all label enums; `#[derive(Clone, PartialEq, Eq, Hash)]` retained for Rust-internal use.
- `fltk/fegen/gsm2tree_rs.py:175-208`: new `#[pymethods]` entries on each label enum:
  - `_fltk_canonical_name` `#[getter]` returning `self.__repr__()` (same canonical string).
  - `__eq__` with own-type fast path (`extract::<EnumName>()` + Rust `PartialEq`); cross-type path reads `_fltk_canonical_name` off operand via `getattr` and string-compares; marker absent → `py.NotImplemented()`.
  - `__hash__` building `PyString::new(py, self.__repr__())` and returning its CPython hash via `PyAnyMethods::hash`, ensuring in-process hash agreement with Python.
- `tests/test_gsm2tree_rs.py:228-252`: added 5 new generator assertions: `eq, hash` absent from `#[pyclass]`; `_fltk_canonical_name` getter present; `__eq__` present; `__hash__` with `PyString::new` present; `"_fltk_canonical_name"` string present in `__eq__` body. Updated `test_identifier_label_pyclass_name` to expect `frozen` without `eq, hash`.
- Regenerated: `src/cst_fegen.rs`, `src/cst_generated.rs`, `tests/rust_cst_fegen/src/cst.rs`, `tests/rust_cst_fixture/src/cst.rs`. All four Rust crates compiled (`maturin develop` clean on all three extension crates).
- 788 tests pass; pyright 0 errors; ruff clean.

## Increment 3 — `NodeKind` enum + `kind` discriminant: Python generator, fltk_cst, fltk_cst_protocol (commit TBD)

Draft scope: emit `NodeKind` enum (with cross-backend eq/hash) and `kind` instance attribute on every node in `gsm2tree.py`; regenerate `fltk_cst.py` and `fltk_cst_protocol.py`.

## Increment 1 — Python `Label` `__eq__`/`__hash__`/`_fltk_canonical_name` in `gsm2tree.py` (commit 600bfc6)

- `fltk/fegen/gsm2tree.py:112-141`: in `py_class_for_model`, after emitting `enum.auto()` members, now emits on each `Label(enum.Enum)`:
  - `_fltk_canonical_name` property (instance-resolved, returns `f"<ClassName>.Label.{self.name}"`)
  - `__eq__` with `other is self` fast path, same-type `self.name == other.name` fast path, canonical-name cross-type path via `getattr(other, "_fltk_canonical_name", None)`, and `NotImplemented` for foreign operands
  - `__hash__` returning `hash(self._fltk_canonical_name)`
- `fltk/fegen/fltk_cst.py`: regenerated; all Label enums now carry the three methods (verified at lines 13-27, 74-88, 157-171, 220-234, 352-366, etc.)
- `fltk/fegen/fltk_cst_protocol.py`: regenerated (no semantic change to protocol; protocol Label uses `ClassVar[object]`)
- 783 tests pass; pyright 0 errors; ruff clean on modified files.
- `fltk_parser.py` was NOT regenerated (parser doesn't depend on Label eq/hash; pre-existing committed file retained).

