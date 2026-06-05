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

## Increment 5 — `self.cst` removal from `fltk2gsm.py` (AC9, AC10) (commit aea3936)

- `fltk/fegen/fltk2gsm.py`: dropped `cst=` constructor parameter and `self.cst` entirely; replaced all `self.cst.X.Label.Y` references with `_cst_const.X.Label.Y` from top-level `from fltk.fegen import fltk_cst as _cst_const`; deleted `isinstance(item, self.cst.Item)` conjuncts (lines 69, 80) and replaced with `typing.cast("cst.Item", item)`; removed `_DEFAULT_CST`/`_default_cst` sentinel scaffolding; kept `if TYPE_CHECKING: from fltk.fegen import fltk_cst_protocol as cst` for annotations.
- `fltk/plumbing.py:174-176`: removed `cst=cast("cst.CstModule", pr.cst_module)` injection on Rust path; Rust path now calls `fltk2gsm.Cst2Gsm(terminals.terminals)` identically to Python path.
- `tests/test_phase4_fegen_rust_backend.py`: updated `test_rust_backend_uses_real_cst2gsm` to not check `cst=` kwarg (parameter removed); replaced `TestCst2GsmInjection` with `TestAC9LabelBackendIndependence` (3 tests: cross-backend `==`, cross-backend `in`, `no self.cst` assert).
- `fltk/test_plumbing.py`: renamed `TestCst2GsmDefaultNamespace` → `TestCst2GsmNoSelfCst`; replaced `test_default_cst_is_fltk_cst` (tested `self.cst`) with `test_no_cst_attribute` (asserts absence); removed unused `_fltk_cst` import.
- 805 tests pass; pyright 0 errors; ruff clean.

## Increment 4 — `NodeKind` enum + `kind` discriminant: Rust generator, regenerated Rust CST outputs (commit 3ea8225)

- `fltk/fegen/gsm2tree_rs.py:138-148`: added `_node_kind_variant_name`, `_node_kind_python_name`, `_node_kind_canonical_name` helpers.
- `fltk/fegen/gsm2tree_rs.py:150-222`: added `_node_kind_block()` emitting the module-level `NodeKind` enum with `#[pyclass(frozen)]`, `#[derive(Clone, PartialEq, Eq, Hash)]`, and `#[pymethods]` block containing `__repr__`, `_fltk_canonical_name` getter, `__eq__` (own-type fast path + canonical-name cross-type + `py.NotImplemented()`), and `__hash__` (CPython `PyString::hash`).
- `fltk/fegen/gsm2tree_rs.py:97-112`: `generate()` now calls `_node_kind_block()` before label/node blocks.
- `fltk/fegen/gsm2tree_rs.py:290-298`: added `_kind_getter()` emitting `#[getter] fn kind(&self) -> NodeKind` returning the node's variant.
- `fltk/fegen/gsm2tree_rs.py:248`: `_node_block()` now calls `_kind_getter()` after `_new_method()`.
- `fltk/fegen/gsm2tree_rs.py:558-562`: `_register_classes_fn()` registers `NodeKind` first, before label enums and node structs.
- `tests/test_gsm2tree_rs.py`: added `TestNodeKindEnum` (11 tests) and `TestKindGetter` (4 tests) covering enum structure, canonical strings, eq/hash methods, registration order, fegen-grammar completeness, and per-node `kind` getter emission. All 60 generator tests pass.
- Regenerated: `src/cst_fegen.rs`, `src/cst_generated.rs`, `tests/rust_cst_fegen/src/cst.rs`, `tests/rust_cst_fixture/src/cst.rs`. All four Rust extension crates compiled clean; 803 tests pass; pyright 0 errors; ruff clean.

## Increment 3 — `NodeKind` enum + `kind` discriminant: Python generator, fltk_cst, fltk_cst_protocol (commit a538305)

- `fltk/fegen/gsm2tree.py`: added `node_kind_member_name()` helper and `_node_kind_enum()` which emits a module-level `NodeKind(enum.Enum)` with one member per rule (uppercased class name), plus `_fltk_canonical_name` property (`"NodeKind.<NAME>"`), cross-backend `__eq__`, and `__hash__`; `gen_py_module()` now prepends this enum before node classes.
- `fltk/fegen/gsm2tree.py:py_class_for_model`: added `kind: typing.Literal[NodeKind.<UPPER>] = NodeKind.<UPPER>` instance-attr dataclass field on every node class (before `span`).
- `fltk/fegen/gsm2tree.py:gen_protocol_module`: adds `from <concrete_module> import NodeKind` when `py_module.import_path` is non-empty; passes `rule_name` to `_protocol_class_for_model`.
- `fltk/fegen/gsm2tree.py:_protocol_class_for_model`: accepts optional `rule_name`; emits `kind: typing.Literal[NodeKind.<MEMBER>]` when module path known, else `kind: object`.
- `fltk/fegen/fltk_cst.py`: regenerated — `NodeKind` enum at top (14 members), `kind` field on all 14 node dataclasses.
- `fltk/fegen/fltk_cst_protocol.py`: regenerated — imports `NodeKind` from `fltk.fegen.fltk_cst`; each Protocol class has `kind: typing.Literal[NodeKind.<MEMBER>]`.
- 788 tests pass; pyright 0 errors; ruff clean.

## Increment 6 — Cross-backend label/NodeKind equality test module (AC1-AC8, §4) (commit 35d8081)

- `tests/test_cross_backend_label_equality.py`: new test module, 42 tests.
- `TestLabelCrossBackend` (21 tests): parametrized over 3 backend pairs (py/ext, py/emb, emb/ext); covers AC1 (eq both directions), AC2 (ineq), AC3 (same-backend unchanged), AC4 (hash consistent), AC5 (set/dict collapse), AC6 (membership in tuple), AC7 (no raise on None/int/str/object/foreign label — both directions).
- `TestAC8TwoRustCrates` (3 tests): explicit targeted check that the two distinct Rust cdylib crates have distinct Python types yet compare equal and hash-agree (AC8).
- `TestNodeKindCrossBackend` (18 tests): same eq/hash/set/membership/no-raise matrix for NodeKind members; additionally asserts canonical-string family disjointness (NodeKind strings never match Label strings).
- `_narrowing_fixture` (TYPE_CHECKING block): pyright-checked fixture confirming `node.kind == NodeKind.ITEMS` narrows correctly over `Items | Grammar` (homogeneous node union); zero pyright errors.
- 847 tests pass; pyright 0 errors; ruff clean.

## Increment 1 — Python `Label` `__eq__`/`__hash__`/`_fltk_canonical_name` in `gsm2tree.py` (commit 600bfc6)

- `fltk/fegen/gsm2tree.py:112-141`: in `py_class_for_model`, after emitting `enum.auto()` members, now emits on each `Label(enum.Enum)`:
  - `_fltk_canonical_name` property (instance-resolved, returns `f"<ClassName>.Label.{self.name}"`)
  - `__eq__` with `other is self` fast path, same-type `self.name == other.name` fast path, canonical-name cross-type path via `getattr(other, "_fltk_canonical_name", None)`, and `NotImplemented` for foreign operands
  - `__hash__` returning `hash(self._fltk_canonical_name)`
- `fltk/fegen/fltk_cst.py`: regenerated; all Label enums now carry the three methods (verified at lines 13-27, 74-88, 157-171, 220-234, 352-366, etc.)
- `fltk/fegen/fltk_cst_protocol.py`: regenerated (no semantic change to protocol; protocol Label uses `ClassVar[object]`)
- 783 tests pass; pyright 0 errors; ruff clean on modified files.
- `fltk_parser.py` was NOT regenerated (parser doesn't depend on Label eq/hash; pre-existing committed file retained).

