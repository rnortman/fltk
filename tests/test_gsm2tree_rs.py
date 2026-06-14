"""Generator unit tests for RustCstGenerator (gsm2tree_rs.py).

These tests validate the source text produced by the generator, not the compiled
Rust output. The compiled output is validated by test_rust_cst_poc.py (PoC grammar)
and test_fegen_rust_cst.py (fegen grammar).
"""

from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
from typing import Any

import pytest

from fltk.fegen import gsm
from fltk.fegen.gsm2tree_rs import RustCstGenerator
from tests.gsm2tree_helpers import make_generator as _make_generator
from tests.gsm2tree_helpers import make_zero_label_grammar as _make_zero_label_grammar
from tests.pyright_test_utils import _run_pyright_over_dir

# ---------------------------------------------------------------------------
# PoC grammar construction
# ---------------------------------------------------------------------------


def _make_poc_grammar() -> gsm.Grammar:
    """Construct the same 2-rule PoC grammar used to generate src/cst_generated.rs.

    identifier rule: one labeled regex item (label="name") with NO_WS separator.
    items rule: three labeled literal items + one labeled identifier ref with
    WS_ALLOWED and WS_REQUIRED separators (triggering trivia insertion).
    """
    identifier_rule = gsm.Rule(
        name="identifier",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="name",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[_a-z][_a-z0-9]*"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
        ],
    )

    items_rule = gsm.Rule(
        name="items",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="no_ws",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("."),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="ws_allowed",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal(","),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="ws_required",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal(":"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="item",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("identifier"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[
                    gsm.Separator.NO_WS,
                    gsm.Separator.WS_ALLOWED,
                    gsm.Separator.WS_REQUIRED,
                    gsm.Separator.NO_WS,
                ],
            ),
        ],
    )

    return gsm.Grammar(
        rules=(identifier_rule, items_rule),
        identifiers={"identifier": identifier_rule, "items": items_rule},
    )


# ---------------------------------------------------------------------------
# Minimal single-rule grammar
# ---------------------------------------------------------------------------


def _make_minimal_grammar() -> gsm.Grammar:
    """Single-rule grammar: numbers := digits+ (one label, no whitespace separators)."""
    numbers_rule = gsm.Rule(
        name="numbers",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="digits",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[0-9]"),
                        quantifier=gsm.ONE_OR_MORE,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
        ],
    )
    return gsm.Grammar(
        rules=(numbers_rule,),
        identifiers={"numbers": numbers_rule},
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def poc_source() -> str:
    """Generated Rust source for the PoC 2-rule grammar."""
    gen = RustCstGenerator(_make_poc_grammar())
    return gen.generate()


@pytest.fixture(scope="module")
def fegen_generator() -> RustCstGenerator:
    """Module-scoped RustCstGenerator for the fegen.fltkg 14-rule grammar.

    Shared by fegen_source and fegen_pyi to avoid duplicating the parse pipeline.
    """
    from fltk.fegen import fltk2gsm, fltk_parser  # noqa: PLC0415
    from fltk.fegen.pyrt import terminalsrc  # noqa: PLC0415

    fegen_path = pathlib.Path(__file__).parent.parent / "fltk" / "fegen" / "fegen.fltkg"
    src = fegen_path.read_text()
    terminals = terminalsrc.TerminalSource(src)
    parser = fltk_parser.Parser(terminalsrc=terminals)
    result = parser.apply__parse_grammar(0)
    assert result is not None, "fegen.fltkg failed to parse"
    cst2gsm = fltk2gsm.Cst2Gsm(terminals.terminals)
    grammar = cst2gsm.visit_grammar(result.result)
    return RustCstGenerator(grammar)


@pytest.fixture(scope="module")
def fegen_source(fegen_generator: RustCstGenerator) -> str:
    """Generated Rust source for the fegen.fltkg 14-rule grammar."""
    return fegen_generator.generate()


# ---------------------------------------------------------------------------
# AC-10: Preamble correctness
# ---------------------------------------------------------------------------


class TestPreamble:
    def test_required_use_declarations(self, poc_source: str) -> None:
        """AC-10: Every generated .rs file includes the required use declarations."""
        # Unconditional: only Span (native, mode-independent)
        assert "use fltk_cst_core::Span;" in poc_source
        # Python-only imports are cfg-gated
        assert (
            '#[cfg(feature = "python")]\nuse fltk_cst_core::{extract_span, get_span_type, span_to_pyobject};'
            in poc_source
        )
        assert (
            '#[cfg(feature = "python")]\nuse pyo3::exceptions::{PyIndexError, PyTypeError, PyValueError};' in poc_source
        )
        # De-globbed explicit import: prelude is NOT a glob — explicit list replaces `use pyo3::prelude::*`.
        # Robustness requirement: the glob would import an unenumerable set of names, making it
        # impossible for the generator to guarantee all reserved-or-qualified checks are complete.
        assert '#[cfg(feature = "python")]\nuse pyo3::prelude::*;' not in poc_source
        explicit_prelude = (
            '#[cfg(feature = "python")]\n'
            "use pyo3::prelude::{Python, Py, Bound, IntoPyObject,\n"
            "    PyAnyMethods, PyListMethods, PyModuleMethods, PyStringMethods, PyTypeMethods,\n"
            "    pyclass, pymethods};"
        )
        assert explicit_prelude in poc_source
        # PyAny, PyResult, PyRef are NOT imported unqualified — all emission sites use
        # fully-qualified paths (pyo3::PyAny, pyo3::PyResult, pyo3::PyRef) so that grammar
        # rules named "any"/"result"/"ref" can generate `pub struct PyAny/PyResult/PyRef` handles.
        assert "use pyo3::PyAny" not in poc_source
        assert "use pyo3::PyResult" not in poc_source
        assert "use pyo3::PyRef" not in poc_source
        # PyList, PyTuple, PyType, PyModule are still fully-qualified at call sites.
        assert "use pyo3::types::{PyList, PyTuple, PyType};" not in poc_source
        # PyTypeInfo is NOT imported unqualified: a grammar rule `type_info` would derive handle
        # `PyTypeInfo` and collide with the import.  The single call site uses UFCS instead:
        #   <EnumName as pyo3::PyTypeInfo>::type_object(py)
        assert "use pyo3::PyTypeInfo;" not in poc_source
        # Combined cfg gate for test-introspection-only imports (pyfunction, wrap_pyfunction).
        # These must appear under the combined gate, not under the plain python gate.
        assert (
            '#[cfg(all(feature = "python", feature = "test-introspection"))]\n'
            "use pyo3::prelude::{pyfunction, wrap_pyfunction};"
        ) in poc_source
        # pyfunction and wrap_pyfunction must NOT appear inside the plain python-only gate.
        assert '#[cfg(feature = "python")]\nuse pyo3::prelude::{pyfunction' not in poc_source
        # These must NOT appear as unconditional imports
        assert "use pyo3::sync::GILOnceCell;" not in poc_source
        # get_source_text_type is no longer imported (span_to_pyobject handles the full path)
        assert "get_source_text_type" not in poc_source
        # Old form: unconditional pyo3 import is gone
        assert "use fltk_cst_core::{extract_span, get_span_type, span_to_pyobject, Span};" not in poc_source

    def test_preamble_at_start(self, poc_source: str) -> None:
        # Phase 2: CstError is the first unconditional import (before Span and Shared).
        assert poc_source.startswith("use fltk_cst_core::CstError;\n")
        assert "use fltk_cst_core::Span;\n" in poc_source

    def test_helpers_not_emitted(self, poc_source: str) -> None:
        """Helpers now live in fltk-cst-core; none of the five items are emitted in generated source."""
        assert "fn extract_span" not in poc_source
        assert "fn get_span_type" not in poc_source
        assert "fn get_source_text_type" not in poc_source
        assert "FLTK_NATIVE_SPAN_TYPE" not in poc_source
        assert "FLTK_NATIVE_SOURCE_TEXT_TYPE" not in poc_source
        # py.import("fltk._native") must not appear in generated code for preamble-helper purposes
        # (helpers moved to cst-core). Note: this assertion is scoped to the absence of the
        # preamble helpers only — if a future generator feature legitimately emits
        # py.import("fltk._native") for a different purpose, update this check accordingly.
        import_count = poc_source.count('py.import("fltk._native")')
        assert import_count == 0, (
            f'Expected 0 occurrences of py.import("fltk._native") in generated source, got {import_count}'
        )

    def test_no_crate_unknown_span_import(self, poc_source: str) -> None:
        """Standalone sentinel: no crate::UNKNOWN_SPAN linkage in generated source."""
        assert "use crate::UNKNOWN_SPAN;" not in poc_source

    def test_no_unknown_span_cache(self, poc_source: str) -> None:
        """Native span: no UNKNOWN_SPAN_CACHE for span sentinel (replaced by Span::unknown())."""
        assert "UNKNOWN_SPAN_CACHE" not in poc_source
        assert 'py.import("fltk._native")?.getattr("UnknownSpan")' not in poc_source


# ---------------------------------------------------------------------------
# AC-1 precondition: expected labels in generated source
# ---------------------------------------------------------------------------


class TestPocGrammarLabels:
    def test_identifier_label_enum_present(self, poc_source: str) -> None:
        # Phase 2: Rust name is IdentifierLabel (CamelCase); Python-visible name preserved via pyclass(name=...).
        assert "pub enum IdentifierLabel {" in poc_source
        # Python-on block has pyo3(name) directly on variants
        assert '#[pyo3(name = "NAME")]' in poc_source
        assert "    Name," in poc_source

    def test_identifier_label_pyclass_name(self, poc_source: str) -> None:
        # Dual-cfg: python-on block uses direct #[pyclass] with name = "Identifier_Label" for compatibility.
        assert '#[pyclass(frozen, from_py_object, name = "Identifier_Label")]' in poc_source
        # The python-on enum block is wrapped in #[cfg(feature = "python")]
        assert '#[cfg(feature = "python")]\n#[pyclass(frozen, from_py_object, name = "Identifier_Label")]' in poc_source

    def test_items_label_enum_present(self, poc_source: str) -> None:
        # Phase 2: Rust name is ItemsLabel (CamelCase).
        assert "pub enum ItemsLabel {" in poc_source
        assert '#[pyo3(name = "ITEM")]' in poc_source
        assert "    Item," in poc_source
        assert '#[pyo3(name = "NO_WS")]' in poc_source
        assert "    NoWs," in poc_source
        assert '#[pyo3(name = "WS_ALLOWED")]' in poc_source
        assert "    WsAllowed," in poc_source
        assert '#[pyo3(name = "WS_REQUIRED")]' in poc_source
        assert "    WsRequired," in poc_source

    def test_identifier_label_repr(self, poc_source: str) -> None:
        assert '"Identifier.Label.NAME"' in poc_source

    def test_items_label_repr(self, poc_source: str) -> None:
        assert '"Items.Label.ITEM"' in poc_source
        assert '"Items.Label.NO_WS"' in poc_source
        assert '"Items.Label.WS_ALLOWED"' in poc_source
        assert '"Items.Label.WS_REQUIRED"' in poc_source

    def test_label_pyclass_no_eq_hash_derive(self, poc_source: str) -> None:
        """eq, hash must NOT appear in #[pyclass] — hand-written __eq__/__hash__ are emitted instead."""
        assert "#[pyclass(eq, hash" not in poc_source

    def test_label_fltk_canonical_name_getter(self, poc_source: str) -> None:
        """_fltk_canonical_name getter must be emitted on label enums."""
        assert "fn _fltk_canonical_name(&self) -> &'static str {" in poc_source

    def test_label_eq_method(self, poc_source: str) -> None:
        """__eq__ method must be emitted on label enums."""
        eq_sig = "fn __eq__(&self, py: Python<'_>, other: &Bound<'_, pyo3::PyAny>) -> pyo3::PyResult<Py<pyo3::PyAny>> {"
        assert eq_sig in poc_source

    def test_label_hash_method(self, poc_source: str) -> None:
        """__hash__ method must be emitted on label enums."""
        # Check for hand-written __hash__ that routes through PyString
        assert "fn __hash__(&self, py: Python<'_>) -> pyo3::PyResult<isize> {" in poc_source
        assert "PyString::new(py, self.__repr__())" in poc_source

    def test_label_eq_uses_canonical_name_marker(self, poc_source: str) -> None:
        """__eq__ must read _fltk_canonical_name from the operand (duck-typed marker)."""
        assert '"_fltk_canonical_name"' in poc_source

    def test_allow_non_camel_case_types(self, poc_source: str) -> None:
        # Phase 2: label enums are now CamelCase (IdentifierLabel, etc.) — #[allow(non_camel_case_types)]
        # is no longer needed on label enums.  This attribute may still appear on other generated items
        # or be zero — we only assert it does NOT appear in excess (not a hard requirement).
        # The old check (>= 3) is now obsolete; the new check verifies the Rust names are idiomatic.
        assert "pub enum IdentifierLabel {" in poc_source
        assert "pub enum ItemsLabel {" in poc_source

    def test_derive_clone_partialeq_eq_hash(self, poc_source: str) -> None:
        # Phase 2: label enums now also derive Debug.
        # PoC grammar has 3 label-bearing rules: Identifier, Items, Trivia
        assert poc_source.count("#[derive(Clone, Debug, PartialEq, Eq, Hash)]") >= 3


# ---------------------------------------------------------------------------
# Node struct structure
# ---------------------------------------------------------------------------


class TestNodeStructure:
    def test_identifier_struct_present(self, poc_source: str) -> None:
        assert "pub struct Identifier {" in poc_source

    def test_items_struct_present(self, poc_source: str) -> None:
        assert "pub struct Items {" in poc_source

    def test_trivia_struct_present(self, poc_source: str) -> None:
        """Trivia class is emitted (trivia rule is auto-inserted by RustCstGenerator, not in the raw grammar)."""
        assert "pub struct Trivia {" in poc_source

    def test_span_field_native(self, poc_source: str) -> None:
        """§2.2: span field is native Span, not a Python-object type."""
        assert "span: Span," in poc_source
        assert "span: PyObject," not in poc_source
        assert "span: Py<PyAny>," not in poc_source

    def test_span_getter_emitted(self, poc_source: str) -> None:
        """§2.2: explicit span getter returning fltk._native.Span (cross-cdylib via Py<pyo3::PyAny>)."""
        assert "fn span(&self, py: Python<'_>) -> pyo3::PyResult<Py<pyo3::PyAny>> {" in poc_source

    def test_span_setter_emitted(self, poc_source: str) -> None:
        """§2.2: explicit span setter (cross-cdylib compatible via extract_span helper).
        Phase 1: handle is frozen, setter takes &self (mutation through RwLock).
        """
        set_span_sig = "fn set_span(&self, py: Python<'_>, value: &Bound<'_, pyo3::PyAny>) -> pyo3::PyResult<()> {"
        assert set_span_sig in poc_source

    def test_children_field_native_vec(self, poc_source: str) -> None:
        """§2.3: children field is a native Vec, not Py<PyList>."""
        # Phase 2: label enum is IdentifierLabel (CamelCase Rust name).
        assert "children: Vec<(Option<IdentifierLabel>, IdentifierChild)>," in poc_source
        assert "children: Py<PyList>," not in poc_source
        assert "#[pyo3(get)]\n    children:" not in poc_source

    def test_children_getter_emitted(self, poc_source: str) -> None:
        """§2.3: explicit children getter rebuilds PyList from Vec.

        The return type uses the fully-qualified pyo3::types::PyList path to avoid
        collision with grammar rules named 'list' generating `pub struct PyList`.
        """
        assert "fn children(&self, py: Python<'_>) -> pyo3::PyResult<Py<pyo3::types::PyList>> {" in poc_source

    def test_child_enum_emitted(self, poc_source: str) -> None:
        """§2.3: per-node child enum is emitted for each node class.
        Phase 1: node-typed variants use Shared<T> instead of Box<T>.
        """
        assert "pub enum IdentifierChild {" in poc_source
        assert "pub enum ItemsChild {" in poc_source
        # Identifier only has Span children (regex terminal)
        assert "IdentifierChild {\n    Span(Span)," in poc_source
        # Items has Span (literals) and Identifier (rule ref) children
        assert "Span(Span)," in poc_source
        # Phase 1: Shared<T> not Box<T>
        assert "Identifier(Shared<Identifier>)," in poc_source
        assert "Identifier(Box<Identifier>)," not in poc_source

    def test_label_classattr_present(self, poc_source: str) -> None:
        assert "#[classattr]" in poc_source
        assert "#[allow(non_snake_case)]" in poc_source
        assert "fn Label(py: Python<'_>) -> pyo3::PyResult<Py<pyo3::PyAny>> {" in poc_source

    def test_extend_children_emitted(self, poc_source: str) -> None:
        """§2.3/§2.5: extend_children method is emitted for each node class.
        Phase 1: handle is frozen (&self); takes handle ref, not PyRef.
        """
        assert "fn extend_children(" in poc_source
        # Phase 1: frozen handle uses &self; parameter is &PyHandle.
        assert "fn extend_children(&self, _py: Python<'_>, other: &PyIdentifier) -> pyo3::PyResult<()> {" in poc_source

    def test_get_span_type_helper_not_emitted(self, poc_source: str) -> None:
        """quality-1: helpers now in fltk-cst-core; no local helper or per-method init block."""
        # No local helper definitions (they're in fltk-cst-core).
        assert "fn get_span_type(py: Python<'_>) -> PyResult<Bound<'_, PyType>> {" not in poc_source
        # No per-method let span_type = FLTK_NATIVE_SPAN_TYPE.get_or_try_init block.
        assert "let span_type = FLTK_NATIVE_SPAN_TYPE.get_or_try_init" not in poc_source


# ---------------------------------------------------------------------------
# Node Debug and Drop generation
# ---------------------------------------------------------------------------


class TestNodeDebugDrop:
    """Generator-level tests for the iterative Debug/Drop emission."""

    def test_node_struct_derives_clone_only(self, poc_source: str) -> None:
        """Node structs use #[derive(Clone)] only — Debug is a manual impl."""
        assert "#[derive(Clone)]\npub struct Identifier {" in poc_source
        assert "#[derive(Clone, Debug)]\npub struct Identifier {" not in poc_source

    def test_manual_debug_impl_emitted(self, poc_source: str) -> None:
        """Manual impl fmt::Debug is emitted for every node struct."""
        assert "impl fmt::Debug for Identifier {" in poc_source
        assert "impl fmt::Debug for Items {" in poc_source
        assert 'f.debug_struct("Identifier")' in poc_source
        assert '"<{} child(ren)>"' in poc_source

    def test_drop_worklist_emitted_for_non_flat_grammar(self, poc_source: str) -> None:
        """DropWorklistItem enum is emitted when the grammar has node-typed children."""
        # PoC grammar: Items has an Identifier child, so child-class union is non-empty.
        assert "enum DropWorklistItem {" in poc_source

    def test_drop_impl_emitted_for_node_with_node_typed_children(self, poc_source: str) -> None:
        """impl Drop is emitted for Items (has Identifier node-typed child)."""
        assert "impl Drop for Items {" in poc_source

    def test_drop_impl_not_emitted_for_span_only_node(self, poc_source: str) -> None:
        """impl Drop is NOT emitted for Identifier (span-only children, no recursion risk)."""
        assert "impl Drop for Identifier {" not in poc_source


# ---------------------------------------------------------------------------
# AC-5: register_classes function
# ---------------------------------------------------------------------------


class TestRegisterClasses:
    def test_register_classes_function_present(self, poc_source: str) -> None:
        """AC-5: pub fn register_classes is present and gated with #[cfg(feature = "python")].

        The PyModule parameter uses the fully-qualified pyo3::types::PyModule path to avoid
        collision with grammar rules named "module" generating `pub struct PyModule`.
        """
        register_classes_sig = (
            '#[cfg(feature = "python")]\n'
            "pub fn register_classes(module: &Bound<'_, pyo3::types::PyModule>) -> pyo3::PyResult<()> {"
        )
        assert register_classes_sig in poc_source

    def test_register_classes_adds_identifier_label(self, poc_source: str) -> None:
        # Phase 2: Rust name is IdentifierLabel; Python class name "Identifier_Label" preserved via pyclass(name=...).
        assert "module.add_class::<IdentifierLabel>()?;" in poc_source

    def test_register_classes_adds_identifier(self, poc_source: str) -> None:
        # Phase 1: registers the handle pyclass PyIdentifier (Python name stays "Identifier")
        assert "module.add_class::<PyIdentifier>()?;" in poc_source

    def test_register_classes_adds_items_label(self, poc_source: str) -> None:
        # Phase 2: Rust name is ItemsLabel.
        assert "module.add_class::<ItemsLabel>()?;" in poc_source

    def test_register_classes_adds_items(self, poc_source: str) -> None:
        # Phase 1: registers the handle pyclass PyItems (Python name stays "Items")
        assert "module.add_class::<PyItems>()?;" in poc_source

    def test_register_classes_label_before_struct(self, poc_source: str) -> None:
        """Label enum must be registered before the node struct — PyO3 requires referenced types registered first."""
        # Phase 2: Rust name is IdentifierLabel.
        idx_label = poc_source.index("module.add_class::<IdentifierLabel>()?;")
        # Phase 1: handle is PyIdentifier
        idx_struct = poc_source.index("module.add_class::<PyIdentifier>()?;")
        assert idx_label < idx_struct

    def test_register_classes_returns_ok(self, poc_source: str) -> None:
        assert "    Ok(())\n}" in poc_source


# ---------------------------------------------------------------------------
# cfg feature gate coverage (§2.3 of design)
# ---------------------------------------------------------------------------


class TestCfgFeatureGate:
    """Verify cfg-gate placement per design §2.3.

    Enums (NodeKind, label enums) use dual-cfg blocks rather than cfg_attr on variant helper
    attributes.  pyo3 0.23 validates helper attributes before proc-macro expansion, so
    #[cfg_attr(feature = "python", pyo3(name = "..."))] on enum variants fails when pyclass
    is itself inside cfg_attr.  Dual-cfg blocks (one python-on with full pyo3 attrs, one
    python-off plain) are the correct pyo3-idiomatic approach.  Structs still use cfg_attr.
    """

    def test_pymethods_blocks_gated(self, poc_source: str) -> None:
        """Every #[pymethods] is immediately preceded by #[cfg(feature = "python")]."""
        lines = poc_source.splitlines()
        for i, line in enumerate(lines):
            if line.strip() == "#[pymethods]":
                # Walk backward over blank lines to find the preceding non-blank line
                j = i - 1
                while j >= 0 and lines[j].strip() == "":
                    j -= 1
                assert j >= 0, f"No line before #[pymethods] at line {i}"
                assert lines[j].strip() == '#[cfg(feature = "python")]', (
                    f"Expected '#[cfg(feature = \"python\")]' before #[pymethods] at line {i + 1}, found: {lines[j]!r}"
                )

    def test_node_struct_pyclass_gated(self, poc_source: str) -> None:
        """Phase 1: data struct has no pyclass; handle uses
        #[cfg(feature = "python")] + #[pyclass(frozen, weakref, name = "...")] .
        Phase 2: data struct derives Clone only; a manual impl fmt::Debug is emitted instead
        of derive(Debug) to keep Debug non-recursive (depth-bounded output).
        """
        # Node data struct derives Clone only (not Debug — Debug is a manual impl).
        assert "#[derive(Clone)]\npub struct Identifier {" in poc_source
        # Node data structs must NOT have derive(Debug).
        assert "#[derive(Clone, Debug)]\npub struct Identifier {" not in poc_source
        # Manual Debug impl must be present for each node struct.
        assert "impl fmt::Debug for Identifier {" in poc_source
        assert 'f.debug_struct("Identifier")' in poc_source
        assert '"<{} child(ren)>"' in poc_source
        # Handle pyclass gate
        assert '#[cfg(feature = "python")]' in poc_source
        # No raw bare #[pyclass] without attributes
        lines = poc_source.splitlines()
        for line in lines:
            assert line.strip() != "#[pyclass]", f"Found raw bare #[pyclass] line: {line!r}"
        # Handle uses frozen + weakref (Phase 1)
        assert '#[pyclass(frozen, weakref, name = "Identifier")]' in poc_source

    def test_child_enum_pyo3_impl_gated(self, poc_source: str) -> None:
        """The to_pyobject/extract_from_pyobject impl block on child enums is gated."""
        # The gated impl block starts with '#[cfg(feature = "python")]' then 'impl <Enum>Child {'
        assert '#[cfg(feature = "python")]\nimpl IdentifierChild {' in poc_source
        assert '#[cfg(feature = "python")]\nimpl ItemsChild {' in poc_source
        assert '#[cfg(feature = "python")]\nimpl TriviaChild {' in poc_source

    def test_unconditional_child_enum_partialeq(self, poc_source: str) -> None:
        """Child enum PartialEq impl is unconditional (no cfg gate)."""
        # PartialEq impl must not be directly preceded by a cfg line
        lines = poc_source.splitlines()
        for child_type in ("IdentifierChild", "TriviaChild"):
            for i, line in enumerate(lines):
                if f"impl PartialEq for {child_type}" in line:
                    j = i - 1
                    while j >= 0 and lines[j].strip() == "":
                        j -= 1
                    assert j >= 0
                    assert "#[cfg" not in lines[j], (
                        f"PartialEq impl for {child_type} should be unconditional, but preceded by: {lines[j]!r}"
                    )

    def test_enum_python_on_block_gated(self, poc_source: str) -> None:
        """Enum definitions with pyclass/pyo3 attrs are inside #[cfg(feature = \"python\")] blocks."""
        assert '#[cfg(feature = "python")]\n#[pyclass(frozen, from_py_object, name = "NodeKind")]' in poc_source
        # Phase 2: Rust name is IdentifierLabel; Python name "Identifier_Label" preserved via pyclass(name=...).
        assert '#[cfg(feature = "python")]\n#[pyclass(frozen, from_py_object, name = "Identifier_Label")]' in poc_source

    def test_enum_python_off_block_present(self, poc_source: str) -> None:
        """Enum definitions without pyo3 attrs present for python-off mode.
        Phase 2: derives now include Debug; Rust names are CamelCase (IdentifierLabel etc.).
        """
        assert (
            '#[cfg(not(feature = "python"))]\n#[derive(Clone, Debug, PartialEq, Eq, Hash)]\npub enum NodeKind {'
            in poc_source
        )
        # Phase 2: Rust enum names are CamelCase.
        assert (
            '#[cfg(not(feature = "python"))]\n#[derive(Clone, Debug, PartialEq, Eq, Hash)]\npub enum IdentifierLabel {'
            in poc_source
        )
        assert (
            '#[cfg(not(feature = "python"))]\n#[derive(Clone, Debug, PartialEq, Eq, Hash)]\npub enum ItemsLabel {'
            in poc_source
        )
        assert (
            '#[cfg(not(feature = "python"))]\n#[derive(Clone, Debug, PartialEq, Eq, Hash)]\npub enum TriviaLabel {'
            in poc_source
        )


# ---------------------------------------------------------------------------
# AC-7 precondition: fegen grammar class names
# ---------------------------------------------------------------------------

FEGEN_RULE_NAMES = [
    "grammar",
    "rule",
    "alternatives",
    "items",
    "item",
    "term",
    "disposition",
    "quantifier",
    "identifier",
    "raw_string",
    "literal",
    "_trivia",
    "line_comment",
    "block_comment",
]

FEGEN_CLASS_NAMES = [
    "Grammar",
    "Rule",
    "Alternatives",
    "Items",
    "Item",
    "Term",
    "Disposition",
    "Quantifier",
    "Identifier",
    "RawString",
    "Literal",
    "Trivia",
    "LineComment",
    "BlockComment",
]

# Each rule name must map to its expected class name via class_name_for_rule_node.
FEGEN_RULE_TO_CLASS = list(zip(FEGEN_RULE_NAMES, FEGEN_CLASS_NAMES, strict=False))


class TestFegenGrammar:
    def test_all_14_classes_present(self, fegen_source: str) -> None:
        """AC-7 precondition: all 14 expected class names appear in the generated source."""
        for class_name in FEGEN_CLASS_NAMES:
            assert f"pub struct {class_name} {{" in fegen_source, (
                f"Expected 'pub struct {class_name} {{' in fegen source"
            )

    def test_register_classes_present(self, fegen_source: str) -> None:
        register_classes_sig = (
            '#[cfg(feature = "python")]\n'
            "pub fn register_classes(module: &Bound<'_, pyo3::types::PyModule>) -> pyo3::PyResult<()> {"
        )
        assert register_classes_sig in fegen_source

    def test_all_14_classes_registered(self, fegen_source: str) -> None:
        """AC-7: all 14 classes have add_class calls in register_classes.

        Phase 1: handle structs are named Py<ClassName>; Python class name is
        preserved via #[pyclass(name = "ClassName")].
        """
        for class_name in FEGEN_CLASS_NAMES:
            py_handle = f"Py{class_name}"
            assert f"module.add_class::<{py_handle}>()?;" in fegen_source, (
                f"Expected 'module.add_class::<{py_handle}>()?;' in fegen source"
            )

    def test_preamble_in_fegen_source(self, fegen_source: str) -> None:
        """AC-10: fegen source also has the required preamble (cfg-gated)."""
        assert "use fltk_cst_core::Span;" in fegen_source
        assert (
            '#[cfg(feature = "python")]\nuse fltk_cst_core::{extract_span, get_span_type, span_to_pyobject};'
            in fegen_source
        )
        # De-globbed: explicit import list, not glob
        assert '#[cfg(feature = "python")]\nuse pyo3::prelude::*;' not in fegen_source
        explicit_prelude = (
            '#[cfg(feature = "python")]\n'
            "use pyo3::prelude::{Python, Py, Bound, IntoPyObject,\n"
            "    PyAnyMethods, PyListMethods, PyModuleMethods, PyStringMethods, PyTypeMethods,\n"
            "    pyclass, pymethods};"
        )
        assert explicit_prelude in fegen_source
        assert "use pyo3::sync::GILOnceCell;" not in fegen_source
        assert "use crate::UNKNOWN_SPAN;" not in fegen_source
        assert "UNKNOWN_SPAN_CACHE" not in fegen_source
        assert "FLTK_NATIVE_SPAN_TYPE" not in fegen_source
        assert "get_source_text_type" not in fegen_source

    def test_rule_name_to_class_name_mapping(self) -> None:
        """FEGEN_RULE_NAMES and FEGEN_CLASS_NAMES must agree with class_name_for_rule_node."""
        # Use the shared labeled grammar and _make_generator to access the name helper.
        from tests.gsm2tree_helpers import make_labeled_grammar  # noqa: PLC0415

        gen = _make_generator(make_labeled_grammar())
        for rule_name, expected_class in FEGEN_RULE_TO_CLASS:
            assert gen.class_name_for_rule_node(rule_name) == expected_class, (
                f"class_name_for_rule_node({rule_name!r}) should be {expected_class!r}"
            )


# ---------------------------------------------------------------------------
# AC-9: Minimal grammar (single-rule, no crash)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def minimal_source() -> str:
    """Generated Rust source for the minimal single-rule grammar."""
    gen = RustCstGenerator(_make_minimal_grammar())
    return gen.generate()


class TestMinimalGrammar:
    def test_minimal_grammar_produces_numbers_class(self, minimal_source: str) -> None:
        """AC-9: Generator does not crash on a single-rule grammar; Numbers struct is present."""
        assert "pub struct Numbers {" in minimal_source

    def test_minimal_grammar_produces_numbers_label(self, minimal_source: str) -> None:
        # Phase 2: Rust name is NumbersLabel (CamelCase); Python class name is "Numbers_Label".
        assert "pub enum NumbersLabel {" in minimal_source
        # Dual-cfg: python-on block has direct pyo3(name)
        assert '#[pyo3(name = "DIGITS")]' in minimal_source
        assert "    Digits," in minimal_source

    def test_minimal_grammar_has_preamble(self, minimal_source: str) -> None:
        """AC-10: Minimal grammar source also includes required use declarations (cfg-gated)."""
        assert "use fltk_cst_core::Span;" in minimal_source
        assert (
            '#[cfg(feature = "python")]\nuse fltk_cst_core::{extract_span, get_span_type, span_to_pyobject};'
            in minimal_source
        )
        # De-globbed: explicit import list, not glob
        assert '#[cfg(feature = "python")]\nuse pyo3::prelude::*;' not in minimal_source
        explicit_prelude = (
            '#[cfg(feature = "python")]\n'
            "use pyo3::prelude::{Python, Py, Bound, IntoPyObject,\n"
            "    PyAnyMethods, PyListMethods, PyModuleMethods, PyStringMethods, PyTypeMethods,\n"
            "    pyclass, pymethods};"
        )
        assert explicit_prelude in minimal_source
        assert "use pyo3::sync::GILOnceCell;" not in minimal_source
        assert "use crate::UNKNOWN_SPAN;" not in minimal_source
        assert "UNKNOWN_SPAN_CACHE" not in minimal_source
        assert "FLTK_NATIVE_SPAN_TYPE" not in minimal_source
        assert "get_source_text_type" not in minimal_source

    def test_flat_grammar_no_drop_worklist(self, minimal_source: str) -> None:
        """Flat grammar (no node-typed children anywhere) must not emit DropWorklistItem.

        An empty-union DropWorklistItem would cause dead_code warnings under -D warnings.
        """
        assert "DropWorklistItem" not in minimal_source, "flat grammar must not emit DropWorklistItem"
        assert "impl Drop" not in minimal_source, "flat grammar must not emit impl Drop"


# ---------------------------------------------------------------------------
# Determinism constraint
# ---------------------------------------------------------------------------


class TestDeterministicOutput:
    def test_two_calls_produce_identical_strings(self) -> None:
        gen = RustCstGenerator(_make_poc_grammar())
        s1 = gen.generate()
        s2 = gen.generate()
        assert s1 == s2

    def test_two_generator_instances_produce_identical_strings(self) -> None:
        grammar = _make_poc_grammar()
        s1 = RustCstGenerator(grammar).generate()
        s2 = RustCstGenerator(grammar).generate()
        assert s1 == s2

    def test_pyi_two_calls_produce_identical_strings(self) -> None:
        """generate_pyi is deterministic across two calls on the same instance."""
        gen = RustCstGenerator(_make_poc_grammar())
        s1 = gen.generate_pyi(_PROTO_MODULE)
        s2 = gen.generate_pyi(_PROTO_MODULE)
        assert s1 == s2

    def test_pyi_two_generator_instances_produce_identical_strings(self) -> None:
        """generate_pyi is deterministic across two separate generator instances."""
        grammar = _make_poc_grammar()
        s1 = RustCstGenerator(grammar).generate_pyi(_PROTO_MODULE)
        s2 = RustCstGenerator(grammar).generate_pyi(_PROTO_MODULE)
        assert s1 == s2

    def test_fegen_grammar_deterministic(self, fegen_source: str) -> None:
        """Fegen grammar (14 rules, many multi-label rules) produces identical output on two calls.

        Uses the fegen_source fixture (one generation) vs a fresh generator to catch
        any dict/set ordering bugs that the small PoC grammar cannot expose.
        """
        import pathlib  # noqa: PLC0415

        from fltk.fegen import fltk2gsm, fltk_parser  # noqa: PLC0415
        from fltk.fegen.pyrt import terminalsrc  # noqa: PLC0415

        fegen_path = pathlib.Path(__file__).parent.parent / "fltk" / "fegen" / "fegen.fltkg"
        src = fegen_path.read_text()
        terminals = terminalsrc.TerminalSource(src)
        parser = fltk_parser.Parser(terminalsrc=terminals)
        result = parser.apply__parse_grammar(0)
        assert result is not None
        cst2gsm = fltk2gsm.Cst2Gsm(terminals.terminals)
        grammar = cst2gsm.visit_grammar(result.result)

        s2 = RustCstGenerator(grammar).generate()
        assert fegen_source == s2


# ---------------------------------------------------------------------------
# OQ-empty-label-enum: zero-label rules omit the label enum
# ---------------------------------------------------------------------------


class TestEmptyLabelEnumOmitted:
    def test_zero_label_rule_omits_label_enum(self) -> None:
        """OQ-empty-label-enum: Rules with no labels omit the enum (Rust disallows zero-variant enums)."""
        gen = RustCstGenerator(_make_zero_label_grammar())
        source = gen.generate()
        assert "Foo_Label" not in source

    def test_zero_label_rule_still_emits_struct(self) -> None:
        gen = RustCstGenerator(_make_zero_label_grammar())
        source = gen.generate()
        assert "pub struct Foo {" in source

    def test_zero_label_rule_omits_label_classattr(self) -> None:
        """#[classattr] Label is not emitted in the Foo impl block (no label enum exists)."""
        gen = RustCstGenerator(_make_zero_label_grammar())
        source = gen.generate()
        # Extract the impl Foo { ... } block and verify Label classattr is absent from it.
        # (The _trivia rule added by the generator does have labels, so the file as a whole
        #  may contain 'fn Label' — but not inside the Foo impl block.)
        # Use regex to match the impl block up to the first `\n}` at column 0 (not indented).
        m = re.search(r"impl Foo \{(.+?)\n\}", source, re.DOTALL)
        assert m is not None, "impl Foo { ... } block not found in generated source"
        foo_impl = m.group(0)
        assert "fn Label(" not in foo_impl

    def test_zero_label_rule_register_classes_no_enum(self) -> None:
        gen = RustCstGenerator(_make_zero_label_grammar())
        source = gen.generate()
        assert "module.add_class::<Foo_Label>()?;" not in source
        # Phase 1: handle type is PyFoo; Python class name is "Foo" via name = "Foo"
        assert "module.add_class::<PyFoo>()?;" in source


# ---------------------------------------------------------------------------
# NodeKind enum generation
# ---------------------------------------------------------------------------


class TestNodeKindEnum:
    def test_node_kind_enum_present(self, poc_source: str) -> None:
        """NodeKind enum is emitted before all node structs."""
        assert "pub enum NodeKind {" in poc_source

    def test_node_kind_pyclass_no_eq_hash(self, poc_source: str) -> None:
        """NodeKind #[pyclass] must not have eq/hash (hand-written instead); dual-cfg form used."""
        # Dual-cfg: python-on block has direct #[pyclass]; must not have eq/hash
        assert '#[pyclass(frozen, from_py_object, name = "NodeKind")]' in poc_source
        assert '#[cfg(feature = "python")]\n#[pyclass(frozen, from_py_object, name = "NodeKind")]' in poc_source
        # eq/hash must not appear in the pyclass line
        lines = poc_source.splitlines()
        for line in lines:
            if '#[pyclass(frozen, from_py_object, name = "NodeKind")]' in line:
                assert "eq" not in line
                assert "hash" not in line

    def test_node_kind_has_identifier_and_items_variants(self, poc_source: str) -> None:
        """PoC grammar produces IDENTIFIER and ITEMS variants in NodeKind (direct pyo3 name in python-on block)."""
        assert '#[pyo3(name = "IDENTIFIER")]' in poc_source
        assert "    Identifier," in poc_source
        assert '#[pyo3(name = "ITEMS")]' in poc_source
        assert "    Items," in poc_source

    def test_node_kind_repr_canonical_form(self, poc_source: str) -> None:
        """NodeKind __repr__ emits 'NodeKind.<UPPER>' canonical strings."""
        assert '"NodeKind.IDENTIFIER"' in poc_source
        assert '"NodeKind.ITEMS"' in poc_source

    def test_node_kind_fltk_canonical_name_getter(self, poc_source: str) -> None:
        """NodeKind has _fltk_canonical_name getter."""
        # The NodeKind impl block must contain the getter
        assert "fn _fltk_canonical_name(&self) -> &'static str {" in poc_source

    def test_node_kind_eq_method(self, poc_source: str) -> None:
        """NodeKind has a hand-written __eq__ reading _fltk_canonical_name off the operand."""
        eq_sig = "fn __eq__(&self, py: Python<'_>, other: &Bound<'_, pyo3::PyAny>) -> pyo3::PyResult<Py<pyo3::PyAny>> {"
        assert eq_sig in poc_source

    def test_node_kind_hash_method(self, poc_source: str) -> None:
        """NodeKind has a hand-written __hash__ routing through PyString::hash."""
        assert "fn __hash__(&self, py: Python<'_>) -> pyo3::PyResult<isize> {" in poc_source

    def test_node_kind_registered_first(self, poc_source: str) -> None:
        """NodeKind must be registered before node structs in register_classes."""
        idx_node_kind = poc_source.index("module.add_class::<NodeKind>()?;")
        # Phase 1: handle type is PyIdentifier; Python class name is "Identifier"
        idx_identifier = poc_source.index("module.add_class::<PyIdentifier>()?;")
        assert idx_node_kind < idx_identifier

    def test_node_kind_before_label_enums(self, poc_source: str) -> None:
        """NodeKind enum block appears before the first Label enum block in the source.
        Phase 2: Rust label enum name is IdentifierLabel (CamelCase).
        """
        idx_node_kind_enum = poc_source.index("pub enum NodeKind {")
        idx_first_label_enum = poc_source.index("pub enum IdentifierLabel {")
        assert idx_node_kind_enum < idx_first_label_enum

    def test_fegen_grammar_node_kind_has_all_14(self, fegen_source: str) -> None:
        """Fegen grammar NodeKind has all 14 class-name-derived members (dual-cfg form)."""
        for class_name in FEGEN_CLASS_NAMES:
            python_name = class_name.upper()
            assert f'#[pyo3(name = "{python_name}")]' in fegen_source, (
                f"Expected NodeKind member {python_name!r} in fegen source"
            )
            assert f'"NodeKind.{python_name}"' in fegen_source, (
                f"Expected canonical string NodeKind.{python_name!r} in fegen source"
            )

    def test_fegen_grammar_node_kind_registered(self, fegen_source: str) -> None:
        """NodeKind is registered in register_classes for the fegen grammar."""
        assert "module.add_class::<NodeKind>()?;" in fegen_source


# ---------------------------------------------------------------------------
# kind getter on node structs
# ---------------------------------------------------------------------------


class TestKindGetter:
    def test_identifier_kind_getter(self, poc_source: str) -> None:
        """Identifier struct has a kind getter returning NodeKind::Identifier."""
        assert "fn kind(&self) -> NodeKind {" in poc_source
        assert "NodeKind::Identifier" in poc_source

    def test_items_kind_getter(self, poc_source: str) -> None:
        """Items struct has a kind getter returning NodeKind::Items."""
        assert "NodeKind::Items" in poc_source

    def test_kind_getter_is_getter_attr(self, poc_source: str) -> None:
        """The handle pymethod kind getter is annotated with #[getter].

        Phase 2: there are now TWO `kind` declarations per node type:
        1. `pub fn kind(&self) -> NodeKind` on the data struct (native API, no #[getter]).
        2. `fn kind(&self) -> NodeKind` on the handle pymethods block (has #[getter]).
        This test checks that at least one occurrence of the signature has #[getter] before it.
        """
        lines = poc_source.splitlines()
        # The pymethods version is not `pub fn`, so filter to those lines only.
        # We require that at least one kind fn has #[getter] immediately before it.
        found_getter = False
        kind_fn_sig = "fn kind(&self) -> NodeKind {"
        for i, line in enumerate(lines):
            if kind_fn_sig in line:
                # Walk backward over blank/doc-comment lines to find the preceding attribute line.
                j = i - 1
                while j >= 0 and (lines[j].strip() == "" or lines[j].strip().startswith("///")):
                    j -= 1
                if j >= 0 and "#[getter]" in lines[j]:
                    found_getter = True
                    break
        assert found_getter, (
            "Expected at least one 'fn kind(&self) -> NodeKind {' with '#[getter]' immediately before it"
        )

    def test_fegen_grammar_all_node_kinds_present(self, fegen_source: str) -> None:
        """All 14 node class names appear as NodeKind variants in fegen source."""
        for class_name in FEGEN_CLASS_NAMES:
            assert f"NodeKind::{class_name}" in fegen_source, f"Expected 'NodeKind::{class_name}' in fegen source"


# ---------------------------------------------------------------------------
# §4 item 2: No-PyObject audit (generator source level)
# ---------------------------------------------------------------------------


class TestNoPyObjectAudit:
    def test_no_pyobject_span_field(self, poc_source: str) -> None:
        """§4 item 2: No generated node struct has span stored as a Python-object type."""
        assert "span: PyObject," not in poc_source
        assert "span: Py<PyAny>," not in poc_source

    def test_no_py_pylist_children(self, poc_source: str) -> None:
        """§4 item 2 (§2.3): children field is now a native Vec, not Py<PyList>."""
        assert "children: Py<PyList>," not in poc_source
        # Native Vec storage for children
        assert "Vec<(Option<" in poc_source

    def test_no_unknown_span_cache_in_fegen(self, fegen_source: str) -> None:
        """§4 item 2: UNKNOWN_SPAN_CACHE not emitted for fegen grammar either."""
        assert "UNKNOWN_SPAN_CACHE" not in fegen_source

    def test_span_uses_native_sentinel(self, poc_source: str) -> None:
        """§2.2: new method uses Span::unknown() sentinel, not Python import."""
        assert "Span::unknown" in poc_source
        assert "UnknownSpan" not in poc_source


# ---------------------------------------------------------------------------
# §4 item 4: Native equality — generator source level
# ---------------------------------------------------------------------------


class TestNativeEqualityGenerated:
    def test_eq_uses_native_structural_equality(self, poc_source: str) -> None:
        """§2.4: __eq__ delegates to Shared<T>::PartialEq, not Python .eq().

        Phase 1: the handle's __eq__ delegates to Shared<T>::PartialEq (which applies the
        ptr_eq short-circuit then deep structural comparison) rather than inlining the logic.
        This keeps the short-circuit invariant in one place (shared.rs).
        """
        # Delegation to Shared<T>::PartialEq via `==` operator
        assert "let eq = self.inner == other_handle.inner;" in poc_source
        # Confirm the old inlined read-locks are gone (delegation, not duplication)
        assert "*self.inner.read() == *other_handle.inner.read()" not in poc_source

    def test_eq_no_python_span_eq(self, poc_source: str) -> None:
        """§2.4: Python .eq() on span must not appear in __eq__."""
        assert "self.span.bind(py).eq(" not in poc_source

    def test_eq_no_python_children_eq(self, poc_source: str) -> None:
        """§2.4: Python .eq() on children must not appear in __eq__."""
        assert "self.children.bind(py).eq(" not in poc_source

    def test_repr_uses_native_span_repr(self, poc_source: str) -> None:
        """§2.4: __repr__ uses native span start()/end() accessors, not Python .repr() on a bound obj.

        Phase 1: the handle's __repr__ acquires a read guard on the inner Shared and
        accesses span through it (guard.span.start(), guard.span.end()).
        """
        # Accesses span via the read guard on inner Shared
        assert "guard.span.start()" in poc_source
        assert "guard.span.end()" in poc_source
        assert "self.span.bind(py).repr()" not in poc_source


# ---------------------------------------------------------------------------
# Phase 1 structural invariants — generator source level (test-6/7/8)
# ---------------------------------------------------------------------------


class TestPhase1HandleStructure:
    """Verify the generator emits the handle struct, to_py_canonical, and py_new registration.

    These tests pin the core Phase 1 artifacts at the generator level so that a regression
    producing wrong field types or omitting registry calls fails the string-match gate before
    any compile or runtime test.
    """

    def test_handle_struct_emitted(self, poc_source: str) -> None:
        """Generator emits the PyX handle struct with a private Shared<X> inner field (test-6)."""
        # Handle struct for Identifier
        assert "pub struct PyIdentifier {" in poc_source
        # Field is private (no pub) and typed Shared<Identifier>
        assert "inner: Shared<Identifier>," in poc_source
        # Confirm the old pub form is absent
        assert "pub inner: Shared<Identifier>," not in poc_source

    def test_to_py_canonical_uses_registry(self, poc_source: str) -> None:
        """Generator emits to_py_canonical and routes wrap-out through registry (test-7)."""
        assert "pub fn to_py_canonical(" in poc_source
        assert "registry::get_or_insert_with(" in poc_source

    def test_py_new_uses_force_register(self, poc_source: str) -> None:
        """Generator emits force_register in the #[new] constructor (test-8)."""
        assert "registry::force_register(" in poc_source


# ---------------------------------------------------------------------------
# generate_pyi: .pyi stub emission (§2.1 of design)
# ---------------------------------------------------------------------------

_PROTO_MODULE = "fltk.fegen.fltk_cst_protocol"


@pytest.fixture(scope="module")
def poc_pyi() -> str:
    """Generated .pyi stub for the PoC 2-rule grammar."""
    gen = RustCstGenerator(_make_poc_grammar())
    return gen.generate_pyi(_PROTO_MODULE)


@pytest.fixture(scope="module")
def minimal_pyi() -> str:
    """Generated .pyi stub for the minimal single-rule grammar (one label)."""
    gen = RustCstGenerator(_make_minimal_grammar())
    return gen.generate_pyi(_PROTO_MODULE)


@pytest.fixture(scope="module")
def zero_label_pyi() -> str:
    """Generated .pyi stub for the zero-label grammar."""
    from tests.gsm2tree_helpers import make_zero_label_grammar  # noqa: PLC0415

    gen = RustCstGenerator(make_zero_label_grammar())
    return gen.generate_pyi(_PROTO_MODULE)


@pytest.fixture(scope="module")
def fegen_pyi(fegen_generator: RustCstGenerator) -> str:
    """Generated .pyi stub for the fegen grammar (14 rules).

    Derived from the shared fegen_generator fixture (no duplicate parse pipeline).
    """
    return fegen_generator.generate_pyi(_PROTO_MODULE)


class TestGeneratePyiHeader:
    def test_future_annotations(self, poc_pyi: str) -> None:
        assert "from __future__ import annotations" in poc_pyi

    def test_imports_typing(self, poc_pyi: str) -> None:
        assert "import typing" in poc_pyi

    def test_imports_terminalsrc(self, poc_pyi: str) -> None:
        assert "import fltk.fegen.pyrt.terminalsrc" in poc_pyi

    def test_imports_span_module(self, poc_pyi: str) -> None:
        assert "import fltk.fegen.pyrt.span" in poc_pyi

    def test_imports_fltk_native(self, poc_pyi: str) -> None:
        assert "import fltk._native" in poc_pyi

    def test_imports_protocol_module_as_proto(self, poc_pyi: str) -> None:
        assert f"import {_PROTO_MODULE} as _proto" in poc_pyi

    def test_ruff_noqa_header(self, poc_pyi: str) -> None:
        assert poc_pyi.startswith("# ruff: noqa: N802")

    def test_node_kind_alias(self, poc_pyi: str) -> None:
        assert "NodeKind = _proto.NodeKind" in poc_pyi

    def test_no_module_level_span(self, poc_pyi: str) -> None:
        """No module-level Span: neither backend's generated module exports one (§2.1a)."""
        lines = poc_pyi.splitlines()
        for line in lines:
            stripped = line.strip()
            # No top-level 'Span = ...' or 'Span: ...' at module level (class Span inside is fine)
            if re.match(r"^Span\s*[:=]", stripped):
                pytest.fail(f"Found module-level Span binding: {line!r}")


class TestGeneratePyiClasses:
    def test_one_class_per_rule(self, poc_pyi: str) -> None:
        """Every rule in the PoC grammar produces exactly one class in the stub."""
        # PoC grammar has identifier + items; trivia is auto-added
        for class_name in ("Identifier", "Items", "Trivia"):
            assert f"class {class_name}:" in poc_pyi

    def test_labelled_rule_has_label_alias(self, poc_pyi: str) -> None:
        """Labelled rules have 'Label = _proto.<Class>.Label' (type alias, not ClassVar).

        ClassVar annotation causes pyright reportRedeclaration when checking structural
        compatibility with the protocol's nested Label class (§3 — self-check must pass).
        """
        assert "Label = _proto.Identifier.Label" in poc_pyi
        assert "Label = _proto.Items.Label" in poc_pyi

    def test_zero_label_rule_has_no_label(self, zero_label_pyi: str) -> None:
        """Label-free rules omit the Label alias (mirroring .rs conditional emission).

        The zero-label grammar has a Foo rule with no labels; _trivia is auto-added and
        does have labels, so we check specifically that Foo's class body lacks Label.
        """
        # Extract the Foo class body: lines between 'class Foo:' and the next 'class ' or EOF.
        lines = zero_label_pyi.splitlines()
        in_foo = False
        foo_lines: list[str] = []
        for line in lines:
            if line.startswith("class Foo:"):
                in_foo = True
                continue
            if in_foo:
                if line.startswith("class "):
                    break
                foo_lines.append(line)
        assert foo_lines, "Foo class not found in zero_label_pyi"
        foo_body = "\n".join(foo_lines)
        assert "Label" not in foo_body, f"Foo (label-free) should not have Label member; Foo body:\n{foo_body}"

    def test_kind_discriminant_uses_proto_nodekind(self, poc_pyi: str) -> None:
        """kind: Literal[_proto.NodeKind.<MEMBER>] — references protocol module's NodeKind."""
        assert "kind: typing.Literal[_proto.NodeKind.IDENTIFIER]" in poc_pyi
        assert "kind: typing.Literal[_proto.NodeKind.ITEMS]" in poc_pyi

    def test_span_annotation_exact_protocol_union(self, poc_pyi: str) -> None:
        """span annotation is the exact protocol union (invariant attribute)."""
        assert "span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span" in poc_pyi

    def test_children_annotation_labelled(self, poc_pyi: str) -> None:
        """Labelled node children: list[tuple[Optional[_proto.<Class>.Label], <child_ann>]]."""
        # Identifier has one label; children annotation must use proto Label
        assert "list[tuple[typing.Optional[_proto.Identifier.Label]" in poc_pyi

    def test_children_annotation_label_free(self, zero_label_pyi: str) -> None:
        """Label-free node children: list[tuple[None, <child_ann>]]."""
        assert "list[tuple[None," in zero_label_pyi

    def test_no_stub_local_class_names_in_annotations(self, poc_pyi: str) -> None:
        """No quoted rule-ref annotations ('"ClassName"') — all replaced with _proto.ClassName."""
        import re  # noqa: PLC0415

        assert not re.search(r'"[A-Z][A-Za-z0-9_]*"', poc_pyi), (
            "Found quoted class name in .pyi; should be _proto-qualified"
        )
        # This check catches the quoted-string form produced under `from __future__ import
        # annotations`; a hypothetical bare (unquoted) uppercase name in an annotation context
        # would not be caught here but would be flagged by the pyright conformance tests.
        # The pyright conformance tests are the authoritative guard; this is a fast pre-pyright lint only.

    def test_extend_children_present(self, poc_pyi: str) -> None:
        """extend_children uses _proto.ClassName (not stub-local) to avoid contravariance errors."""
        assert "def extend_children(self, other: _proto.Identifier) -> None: ..." in poc_pyi
        assert "def extend_children(self, other: _proto.Items) -> None: ..." in poc_pyi

    def test_generic_append_present(self, poc_pyi: str) -> None:
        assert "def append(self," in poc_pyi

    def test_generic_extend_present(self, poc_pyi: str) -> None:
        assert "def extend(self," in poc_pyi

    def test_generic_child_present(self, poc_pyi: str) -> None:
        assert "def child(self)" in poc_pyi


class TestGeneratePyiPerLabelAccessors:
    def test_append_label_method_present(self, poc_pyi: str) -> None:
        assert "def append_name(self, child:" in poc_pyi

    def test_extend_label_method_present(self, poc_pyi: str) -> None:
        assert "def extend_name(self, children:" in poc_pyi

    def test_children_label_typed_iterator(self, poc_pyi: str) -> None:
        """children_<label> must be Iterator[T], NOT list[T] (§3 of design)."""
        assert "def children_name(self) -> typing.Iterator[" in poc_pyi
        # Must not be list
        assert "def children_name(self) -> list[" not in poc_pyi

    def test_child_label_method_present(self, poc_pyi: str) -> None:
        assert "def child_name(self)" in poc_pyi

    def test_maybe_label_method_present(self, poc_pyi: str) -> None:
        assert "def maybe_name(self)" in poc_pyi

    def test_multi_label_rule_all_five_per_label(self, poc_pyi: str) -> None:
        """Items rule (4 labels) has all 5 accessors per label."""
        for label in ("no_ws", "ws_allowed", "ws_required", "item"):
            for prefix in ("append_", "extend_", "children_", "child_", "maybe_"):
                method = f"def {prefix}{label}("
                assert method in poc_pyi, f"Missing {method!r} in poc_pyi"


class TestMutatorsEmittedRsPymethods:
    """§4.1: Generated Rust source contains all four pymethod mutators with expected signatures."""

    def test_insert_pymethod_present(self, poc_source: str) -> None:
        """fn insert pymethod is emitted on each node."""
        assert "fn insert(" in poc_source

    def test_remove_at_pymethod_present(self, poc_source: str) -> None:
        """fn remove_at pymethod is emitted on each node."""
        assert "fn remove_at(" in poc_source

    def test_replace_at_pymethod_present(self, poc_source: str) -> None:
        """fn replace_at pymethod is emitted on each node."""
        assert "fn replace_at(" in poc_source

    def test_clear_pymethod_present(self, poc_source: str) -> None:
        """fn clear pymethod is emitted on each node."""
        assert "fn clear(" in poc_source

    def test_insert_takes_pyany_index(self, poc_source: str) -> None:
        """insert takes index as &Bound<'_, pyo3::PyAny> (not i64), for __index__ semantics."""
        insert_sig_start = (
            "fn insert(\n        &self,\n        py: Python<'_>,\n        index: &Bound<'_, pyo3::PyAny>,"
        )
        assert insert_sig_start in poc_source

    def test_insert_pyo3_signature(self, poc_source: str) -> None:
        """insert has #[pyo3(signature = (index, child, label = None))]."""
        assert "#[pyo3(signature = (index, child, label = None))]\n    fn insert(" in poc_source

    def test_replace_at_pyo3_signature(self, poc_source: str) -> None:
        """replace_at has #[pyo3(signature = (index, child, label = None))]."""
        assert "#[pyo3(signature = (index, child, label = None))]\n    fn replace_at(" in poc_source

    def test_remove_at_returns_pyresult_pyobject(self, poc_source: str) -> None:
        """remove_at returns pyo3::PyResult<Py<pyo3::PyAny>> (tuple of label + child)."""
        remove_at_sig = (
            "fn remove_at(&self, py: Python<'_>, index: &Bound<'_, pyo3::PyAny>) -> pyo3::PyResult<Py<pyo3::PyAny>>"
        )
        assert remove_at_sig in poc_source

    def test_clear_returns_pyresult_unit(self, poc_source: str) -> None:
        """clear returns pyo3::PyResult<()>."""
        assert "fn clear(&self, _py: Python<'_>) -> pyo3::PyResult<()>" in poc_source

    def test_insert_index_normalization_present(self, poc_source: str) -> None:
        """insert normalizes index via operator.index (TypeError for non-indexable, not AttributeError)."""
        # operator.index is called via Python's operator module, not __index__ directly.
        assert 'import(pyo3::intern!(py, "operator"))' in poc_source
        assert 'getattr(pyo3::intern!(py, "index"))' in poc_source

    def test_insert_clamp_logic_present(self, poc_source: str) -> None:
        """insert contains clamp logic (both directions): positive clamps to n, negative to 0."""
        assert "if u > n { n } else { u }" in poc_source
        assert "if normalized < 0 { 0 } else { normalized as usize }" in poc_source

    def test_remove_at_index_error_message(self, poc_source: str) -> None:
        """remove_at emits the pinned IndexError message format with positional {} placeholders."""
        # Format: "{ClassName}.remove_at: index {} out of range ({} children)"
        # Uses positional {} because orig_str and n are separate variables.
        assert "out of range ({} children)" in poc_source

    def test_mutators_in_pymethods_block(self, poc_source: str) -> None:
        """All four mutators appear inside a #[cfg(feature = \"python\")] #[pymethods] block."""
        # The fn insert/remove_at/replace_at/clear appear inside the pymethods impl blocks.
        # We verify they are not bare pub fns (which would be native methods, not pymethods).
        # Native method signatures differ: they use &mut self and usize.
        assert "fn insert(\n        &self," in poc_source  # pymethod: &self
        assert "fn remove_at(&self," in poc_source  # pymethod: &self
        assert "fn clear(&self," in poc_source  # pymethod: &self

    def test_fegen_source_has_all_mutators(self, fegen_source: str) -> None:
        """Fegen grammar (14 rules) also emits all four mutators."""
        assert "fn insert(" in fegen_source
        assert "fn remove_at(" in fegen_source
        assert "fn replace_at(" in fegen_source
        assert "fn clear(" in fegen_source


class TestNativeMutatorsEmittedRs:
    """§4.1: Native (non-pymethod) mutators insert_child/remove_child/replace_child/clear_children are emitted."""

    def test_insert_child_native(self, poc_source: str) -> None:
        """pub fn insert_child is emitted on each node struct."""
        assert "pub fn insert_child(" in poc_source

    def test_remove_child_native(self, poc_source: str) -> None:
        """pub fn remove_child is emitted on each node struct."""
        assert "pub fn remove_child(" in poc_source

    def test_replace_child_native(self, poc_source: str) -> None:
        """pub fn replace_child is emitted on each node struct."""
        assert "pub fn replace_child(" in poc_source

    def test_clear_children_native(self, poc_source: str) -> None:
        """pub fn clear_children is emitted on each node struct."""
        assert "pub fn clear_children(" in poc_source

    def test_insert_child_signature(self, poc_source: str) -> None:
        """insert_child takes (index: usize, label: Option<...Label>, child: ...Child)."""
        assert (
            "pub fn insert_child(&mut self, index: usize, label: Option<IdentifierLabel>, child: IdentifierChild)"
            in poc_source
        )

    def test_remove_child_signature(self, poc_source: str) -> None:
        """remove_child takes (index: usize) and returns (Option<...Label>, ...Child)."""
        assert (
            "pub fn remove_child(&mut self, index: usize) -> (Option<IdentifierLabel>, IdentifierChild)" in poc_source
        )

    def test_replace_child_signature(self, poc_source: str) -> None:
        """replace_child takes (index: usize, label, child) and returns (label, child) old entry."""
        assert "pub fn replace_child(" in poc_source
        # Verify at minimum the return type is present (replaces and returns old entry)
        assert "-> (Option<IdentifierLabel>, IdentifierChild)" in poc_source

    def test_clear_children_signature(self, poc_source: str) -> None:
        """clear_children takes only &mut self."""
        assert "pub fn clear_children(&mut self)" in poc_source

    def test_native_mutators_use_mut_self(self, poc_source: str) -> None:
        """Native mutators take &mut self (not &self like pymethods)."""
        assert "pub fn insert_child(&mut self," in poc_source
        assert "pub fn remove_child(&mut self," in poc_source
        assert "pub fn clear_children(&mut self)" in poc_source

    def test_fegen_source_has_native_mutators(self, fegen_source: str) -> None:
        """Fegen grammar also emits all four native mutators."""
        assert "pub fn insert_child(" in fegen_source
        assert "pub fn remove_child(" in fegen_source
        assert "pub fn replace_child(" in fegen_source
        assert "pub fn clear_children(" in fegen_source


class TestMutatorsEmittedPyi:
    """§4.1: .pyi stubs contain all four mutator method signatures."""

    def test_insert_present_pyi(self, poc_pyi: str) -> None:
        """insert stub is present in the .pyi."""
        assert "def insert(self," in poc_pyi

    def test_remove_at_present_pyi(self, poc_pyi: str) -> None:
        """remove_at stub is present in the .pyi."""
        assert "def remove_at(self," in poc_pyi

    def test_replace_at_present_pyi(self, poc_pyi: str) -> None:
        """replace_at stub is present in the .pyi."""
        assert "def replace_at(self," in poc_pyi

    def test_clear_present_pyi(self, poc_pyi: str) -> None:
        """clear stub is present in the .pyi."""
        assert "def clear(self) -> None: ..." in poc_pyi

    def test_insert_signature_labeled(self, poc_pyi: str) -> None:
        """insert stub has index: int, child, and label params for a labeled node."""
        # Extract Identifier class section
        lines = poc_pyi.splitlines()
        in_identifier = False
        identifier_lines: list[str] = []
        for line in lines:
            if line.startswith("class Identifier:"):
                in_identifier = True
                continue
            if in_identifier:
                if line.startswith("class "):
                    break
                identifier_lines.append(line)
        identifier_body = "\n".join(identifier_lines)
        assert "def insert(self, index: int," in identifier_body, (
            f"Expected 'def insert(self, index: int,' in Identifier class body; got:\n{identifier_body}"
        )
        assert "label:" in identifier_body, "Expected 'label:' in Identifier.insert stub"

    def test_remove_at_returns_tuple_labeled(self, poc_pyi: str) -> None:
        """remove_at stub returns a tuple for labeled nodes."""
        assert "def remove_at(self, index: int) -> tuple[" in poc_pyi

    def test_replace_at_returns_none(self, poc_pyi: str) -> None:
        """replace_at stub returns None."""
        assert "def replace_at(self, index: int," in poc_pyi
        # Verify it ends with -> None: ...
        for line in poc_pyi.splitlines():
            if "def replace_at" in line and "-> None:" in line:
                break
        else:
            # May span multiple lines; check that replace_at appears with -> None somewhere
            import re  # noqa: PLC0415

            match = re.search(r"def replace_at\([^)]+\)\s*->\s*None:", poc_pyi, re.DOTALL)
            assert match is not None, "replace_at must return None in .pyi"

    def test_mutators_after_generic_child(self, poc_pyi: str) -> None:
        """Mutators appear after def child(self) in the stub (§2.3 ordering)."""
        idx_child = poc_pyi.find("def child(self)")
        idx_insert = poc_pyi.find("def insert(self,")
        assert idx_child != -1, "def child not found in poc_pyi"
        assert idx_insert != -1, "def insert not found in poc_pyi"
        assert idx_child < idx_insert, "insert must appear after child in .pyi"

    def test_fegen_pyi_has_all_mutators(self, fegen_pyi: str) -> None:
        """Fegen grammar .pyi also contains all four mutator stubs."""
        assert "def insert(self," in fegen_pyi
        assert "def remove_at(self," in fegen_pyi
        assert "def replace_at(self," in fegen_pyi
        assert "def clear(self) -> None: ..." in fegen_pyi


class TestRegistrySnapshotEmittedRs:
    """§4.1 / §2.3: _registry_snapshot pyfunction is emitted per module (test-introspection feature)."""

    def test_registry_snapshot_pyfunction_present(self, poc_source: str) -> None:
        """_registry_snapshot is emitted as a #[pyfunction] in register_classes."""
        assert "_registry_snapshot" in poc_source

    def test_registry_snapshot_cfg_gated(self, poc_source: str) -> None:
        """_registry_snapshot is gated on feature = \"test-introspection\"."""
        assert 'feature = "test-introspection"' in poc_source

    def test_registry_snapshot_added_in_register_classes(self, poc_source: str) -> None:
        """register_classes adds _registry_snapshot as a function."""
        assert "add_function" in poc_source


class TestMutatorNoCollisionRs:
    """§2.1: no per-label generated name can equal any fixed mutator name."""

    def test_fixed_mutator_names_not_reachable_from_per_label_prefixes(self) -> None:
        """Per-label prefix families (append_/extend_/children_/child_/maybe_) never produce a fixed mutator name."""
        fixed_names = {"insert", "remove_at", "replace_at", "clear"}
        per_label_prefixes = ("append_", "extend_", "children_", "child_", "maybe_")
        for label in fixed_names:
            for prefix in per_label_prefixes:
                generated = f"{prefix}{label}"
                assert generated not in fixed_names, f"Per-label method '{generated}' collides with fixed mutator name"

    def test_no_insert_remove_replace_clear_in_reserved_labels(self) -> None:
        """_RESERVED_LABELS does not contain insert/remove_at/replace_at/clear (not needed)."""
        from fltk.fegen.gsm2tree_rs import _RESERVED_LABELS  # noqa: PLC0415

        fixed_names = {"insert", "remove_at", "replace_at", "clear"}
        for label in fixed_names:
            assert label not in _RESERVED_LABELS, (
                f"'{label}' should not be in _RESERVED_LABELS; per-label methods never produce bare fixed mutator names"
            )


class TestGeneratePyiModuleLevelClassAttrs:
    def test_no_redundant_module_level_attrs(self, poc_pyi: str) -> None:
        """No 'ClassName: type[ClassName]' module-level attrs (would cause reportRedeclaration).

        The class definition itself serves as the module-level binding; separate variable
        annotations of the same name trigger pyright reportRedeclaration in stub self-check.
        CstModule conformance works from the class definitions alone.
        """
        import re  # noqa: PLC0415

        for line in poc_pyi.splitlines():
            # Top-level (unindented) '<ClassName>: type[<ClassName>]' should NOT be present.
            if re.match(r"^[A-Z]\w+: type\[\w+\]", line):
                pytest.fail(f"Redundant module-level class attr found: {line!r}")

    def test_fegen_grammar_class_definitions_all_present(self, fegen_pyi: str) -> None:
        """Fegen grammar: all 14 expected classes are defined in the stub."""
        for class_name in FEGEN_CLASS_NAMES:
            assert f"class {class_name}:" in fegen_pyi, f"Missing class definition for '{class_name}'"


class TestGeneratePyiClassLabelSetMatchesRs:
    """Class/label set of the .pyi must equal that of the .rs (drift guard).

    Phase 1: the .rs contains both the data struct (e.g. ``pub struct Identifier``)
    and the Python handle (e.g. ``pub struct PyIdentifier``).  The .pyi only exposes
    the Python-facing class name (``Identifier``), so we extract *data-struct* names
    only from the .rs — filtering out the ``Py``-prefixed handle structs.
    """

    def _extract_rs_data_struct_classes(self, rs_source: str) -> set[str]:
        """Return pub struct names that are NOT Py-prefixed (i.e. data structs)."""
        import re  # noqa: PLC0415

        all_structs = set(re.findall(r"pub struct (\w+) \{", rs_source))
        # Filter out Py-prefixed handle structs introduced by Phase 1.
        return {name for name in all_structs if not name.startswith("Py")}

    def _extract_pyi_classes(self, pyi_source: str) -> set[str]:
        import re  # noqa: PLC0415

        return set(re.findall(r"^class (\w+):", pyi_source, re.MULTILINE))

    def test_poc_class_set_matches(self, poc_source: str, poc_pyi: str) -> None:
        """PoC grammar: data-struct class names in .rs equal class names in .pyi."""
        rs_classes = self._extract_rs_data_struct_classes(poc_source)
        pyi_classes = self._extract_pyi_classes(poc_pyi)
        assert rs_classes == pyi_classes

    def test_fegen_class_set_matches(self, fegen_source: str, fegen_pyi: str) -> None:
        """Fegen grammar: data-struct class names in .rs equal class names in .pyi."""
        rs_classes = self._extract_rs_data_struct_classes(fegen_source)
        pyi_classes = self._extract_pyi_classes(fegen_pyi)
        assert rs_classes == pyi_classes


# ---------------------------------------------------------------------------
# Reserved label rejection (§4.2 of design ADR 2026/06/10-rust-idiomatic-cst-api)
# ---------------------------------------------------------------------------


class TestReservedLabelRejection:
    """Generator must reject labels whose per-label methods collide with fixed method names."""

    def _make_reserved_label_grammar(self, label: str) -> gsm.Grammar:
        """Single-rule grammar with one item whose label is the given reserved name."""
        rule = gsm.Rule(
            name="node",
            alternatives=[
                gsm.Items(
                    items=[
                        gsm.Item(
                            label=label,
                            disposition=gsm.Disposition.INCLUDE,
                            term=gsm.Regex(r"[a-z]+"),
                            quantifier=gsm.REQUIRED,
                        ),
                    ],
                    sep_after=[gsm.Separator.NO_WS],
                ),
            ],
        )
        return gsm.Grammar(rules=(rule,), identifiers={"node": rule})

    def test_children_label_rejected(self) -> None:
        """Label 'children' is reserved: extend_children would collide with the fixed method."""
        grammar = self._make_reserved_label_grammar("children")
        with pytest.raises(ValueError, match="children") as exc_info:
            RustCstGenerator(grammar)
        # Error message must name both the label and the colliding method.
        assert "extend_children" in str(exc_info.value)

    def test_non_reserved_label_accepted(self) -> None:
        """A non-reserved label does not raise."""
        grammar = self._make_reserved_label_grammar("name")
        gen = RustCstGenerator(grammar)
        assert gen is not None


# ---------------------------------------------------------------------------
# Reserved class name rejection (§2.6 of design ADR 2026/06/11-rust-bindings-module-split)
# ---------------------------------------------------------------------------


def _make_single_rule_grammar(rule_name: str, *, labeled: bool = True) -> gsm.Grammar:
    """Minimal single-rule grammar with one regex item; used to test per-rule validation."""
    rule = gsm.Rule(
        name=rule_name,
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="value" if labeled else None,
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[a-z]+"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
        ],
    )
    return gsm.Grammar(rules=(rule,), identifiers={rule_name: rule})


class TestReservedClassNameRejection:
    """RustCstGenerator must reject rule names that derive a class name colliding with fixed cst-module names."""

    @pytest.mark.parametrize(
        ("rule_name", "expected_class", "collision_substring"),
        [
            ("node_kind", "NodeKind", "NodeKind"),
            ("span", "Span", "Span"),
            ("shared", "Shared", "Shared"),
            ("cst_error", "CstError", "CstError"),
            ("drop_worklist_item", "DropWorklistItem", "DropWorklistItem"),
            ("eq_worklist_item", "EqWorklistItem", "EqWorklistItem"),
            # PyO3 name guards — Half 1 (Py-prefixed): grammar rules whose class name derives a
            # `Py{CN}` handle colliding with a pyo3 name imported UNQUALIFIED.
            # Not reserved: "list"/"tuple"/"type"/"module"/"any"/"result"/"ref" — those pyo3 names
            # are fully-qualified at all emission sites, so their Py{CN} handles are safe.
            ("index_error", "IndexError", "pyo3"),
            ("type_error", "TypeError", "pyo3"),
            ("value_error", "ValueError", "pyo3"),
            # PyO3 name guards — Half 2 (non-Py-prefixed): grammar rules whose bare `{CN}` data
            # struct collides with a name in the explicit `use pyo3::prelude::{...}` import list.
            # `bound` → CN=Bound, collides with pyo3::Bound imported unqualified.
            ("bound", "Bound", "pyo3"),
            # `py` → CN=Py, collides with pyo3::Py imported unqualified.
            ("py", "Py", "pyo3"),
            # `python` → CN=Python, collides with pyo3::Python imported unqualified.
            ("python", "Python", "pyo3"),
            # `into_py_object` → CN=IntoPyObject, collides with pyo3::IntoPyObject imported unqualified.
            ("into_py_object", "IntoPyObject", "pyo3"),
            # Note: `from_py_object` → CN=FromPyObject is NOT reserved: FromPyObject is not imported
            # unqualified in the generated cst.rs preamble (the from_py_object pyclass param is handled
            # internally by the pyo3 macro and does not require FromPyObject in scope).
        ],
    )
    def test_reserved_class_name_rejected(self, rule_name: str, expected_class: str, collision_substring: str) -> None:
        """Rules whose derived class name collides with fixed cst module names are rejected at generation time."""
        grammar = _make_single_rule_grammar(rule_name)
        with pytest.raises(ValueError, match=rule_name) as exc_info:
            RustCstGenerator(grammar)
        error_text = str(exc_info.value)
        assert expected_class in error_text, f"Error should name the derived class {expected_class!r}: {error_text}"
        assert collision_substring in error_text, f"Error should name collision target: {error_text}"

    def test_source_text_rule_accepted(self) -> None:
        """Rule named 'source_text' is NOT reserved: SourceText is not in the cst.rs preamble."""
        grammar = _make_single_rule_grammar("source_text")
        gen = RustCstGenerator(grammar)
        assert gen is not None

    @pytest.mark.parametrize(
        ("rule_name", "expected_handle", "collision_substring"),
        [
            # Direct check (per-rule): CN = PyAnyMethods falls into _RESERVED_CLASS_NAMES_SEEDED.
            ("py_any_methods", "PyAnyMethods", "pyo3"),
            ("py_list_methods", "PyListMethods", "pyo3"),
            ("py_module_methods", "PyModuleMethods", "pyo3"),
            ("py_string_methods", "PyStringMethods", "pyo3"),
            ("py_type_methods", "PyTypeMethods", "pyo3"),
        ],
    )
    def test_seeded_reserved_cn_rejected_directly(
        self, rule_name: str, expected_handle: str, collision_substring: str
    ) -> None:
        """Rules whose CN is in _RESERVED_CLASS_NAMES_SEEDED are rejected by the per-rule check."""
        grammar = _make_single_rule_grammar(rule_name)
        with pytest.raises(ValueError, match=rule_name) as exc_info:
            RustCstGenerator(grammar)
        error_text = str(exc_info.value)
        assert expected_handle in error_text, f"Error should name the reserved handle {expected_handle!r}: {error_text}"
        assert collision_substring in error_text, f"Error should name collision target: {error_text}"

    def test_seeded_reserved_handle_rejected_cross_rule(self) -> None:
        """Rule 'any_methods' (handle=PyAnyMethods) is rejected because PyAnyMethods is seeded in claims."""
        # any_methods → CN=AnyMethods, handle=PyAnyMethods.
        # _RESERVED_CLASS_NAMES_SEEDED seeds PyAnyMethods into claims, so the cross-rule check fires.
        grammar = _make_single_rule_grammar("any_methods")
        with pytest.raises(ValueError) as exc_info:
            RustCstGenerator(grammar)
        error_text = str(exc_info.value)
        assert "PyAnyMethods" in error_text, f"Error must name PyAnyMethods: {error_text}"
        assert "pyo3" in error_text, f"Error must mention pyo3 import: {error_text}"

    def test_type_info_rule_accepted(self) -> None:
        """Rule 'type_info' is NOT reserved: PyTypeInfo is no longer imported unqualified."""
        # The _label_classattr emission uses UFCS (<EnumName as pyo3::PyTypeInfo>::type_object)
        # so `use pyo3::PyTypeInfo;` was removed, making type_info a legal rule name.
        grammar = _make_single_rule_grammar("type_info")
        gen = RustCstGenerator(grammar)
        assert gen is not None

    @pytest.mark.parametrize(
        ("rule_name", "expected_class_name"),
        [
            ("parser", "Parser"),
            ("apply_result", "ApplyResult"),
            # "list"/"tuple"/"type" are NOT reserved: the generated preamble uses fully-qualified
            # pyo3::types::PyList/PyTuple/PyType paths, so `pub struct PyList` etc. are safe.
            ("list", "List"),
            ("tuple", "Tuple"),
            ("type", "Type"),
            # "module" is NOT reserved: register_classes uses pyo3::types::PyModule qualified.
            ("module", "Module"),
            # "any" is NOT reserved: PyAny is now fully-qualified at all emission sites
            # (pyo3::PyAny), so `pub struct PyAny` from rule "any" does not collide.
            ("any", "Any"),
            # "err"/"result" are NOT reserved: PyErr/PyResult are now fully-qualified at
            # all emission sites, so `pub struct PyErr/PyResult` from these rules are safe.
            ("err", "Err"),
            ("result", "Result"),
            # "from_py_object" is NOT reserved: FromPyObject is not imported unqualified
            # (from_py_object in #[pyclass(...)] is a macro param, not a use-site type).
            ("from_py_object", "FromPyObject"),
        ],
    )
    def test_rules_not_reserved_are_accepted(self, rule_name: str, expected_class_name: str) -> None:
        """Rules whose class name does NOT collide with reserved names are accepted and emitted correctly."""
        grammar = _make_single_rule_grammar(rule_name)
        gen = RustCstGenerator(grammar)
        src = gen.generate()
        # The generated cst source must contain the rule's pyclass name handle.
        assert f'name = "{expected_class_name}"' in src, (
            f"Expected pyclass name = {expected_class_name!r} in generated cst source"
        )

    def test_source_text_rule_cst_class_name_in_source(self) -> None:
        """source_text rule is not reserved; generated cst source contains name = \"SourceText\" (positive case)."""
        grammar = _make_single_rule_grammar("source_text")
        gen = RustCstGenerator(grammar)
        src = gen.generate()
        assert 'name = "SourceText"' in src, 'Expected pyclass name = "SourceText" in generated cst source'


# ---------------------------------------------------------------------------
# Cross-rule identifier collision check
# ---------------------------------------------------------------------------


def _make_two_rule_grammar(
    rule_name_a: str, rule_name_b: str, *, labeled_a: bool = True, labeled_b: bool = True
) -> gsm.Grammar:
    """Two-rule grammar; each rule has a single regex item with/without a label."""
    g_a = _make_single_rule_grammar(rule_name_a, labeled=labeled_a)
    g_b = _make_single_rule_grammar(rule_name_b, labeled=labeled_b)
    return gsm.Grammar(
        rules=g_a.rules + g_b.rules,
        identifiers={**g_a.identifiers, **g_b.identifiers},
    )


class TestCrossRuleIdentifierCollisions:
    """RustCstGenerator must detect cross-rule Rust identifier collisions before emission."""

    def test_foo_and_foo_child_collide_on_foo_child(self) -> None:
        """Rule 'foo_child' derives struct FooChild, colliding with rule 'foo's child enum FooChild."""
        grammar = _make_two_rule_grammar("foo", "foo_child")
        with pytest.raises(ValueError) as exc_info:
            RustCstGenerator(grammar)
        error_text = str(exc_info.value)
        assert "FooChild" in error_text, f"Error must name the colliding identifier FooChild: {error_text}"
        assert "foo" in error_text, f"Error must name rule 'foo': {error_text}"
        assert "foo_child" in error_text, f"Error must name rule 'foo_child': {error_text}"
        assert "child value enum" in error_text, f"Error must name the 'child value enum' family: {error_text}"
        assert "node struct" in error_text, f"Error must name the 'node struct' family: {error_text}"
        assert "rename" in error_text, f"Error must include the 'rename' action hint: {error_text}"

    def test_foo_with_label_and_foo_label_collide_on_foo_label(self) -> None:
        """Rule 'foo_label' derives struct FooLabel, colliding with rule 'foo's label enum FooLabel."""
        grammar = _make_two_rule_grammar("foo", "foo_label", labeled_a=True, labeled_b=True)
        with pytest.raises(ValueError) as exc_info:
            RustCstGenerator(grammar)
        error_text = str(exc_info.value)
        assert "FooLabel" in error_text, f"Error must name the colliding identifier FooLabel: {error_text}"
        assert "foo" in error_text, f"Error must name rule 'foo': {error_text}"
        assert "foo_label" in error_text, f"Error must name rule 'foo_label': {error_text}"
        assert "label enum" in error_text, f"Error must name the 'label enum' family: {error_text}"

    def test_foo_and_py_foo_collide_on_py_foo(self) -> None:
        """Rule 'py_foo' derives struct PyFoo, colliding with rule 'foo's handle struct PyFoo."""
        grammar = _make_two_rule_grammar("foo", "py_foo")
        with pytest.raises(ValueError) as exc_info:
            RustCstGenerator(grammar)
        error_text = str(exc_info.value)
        assert "PyFoo" in error_text, f"Error must name the colliding identifier PyFoo: {error_text}"
        assert "foo" in error_text, f"Error must name rule 'foo': {error_text}"
        assert "py_foo" in error_text, f"Error must name rule 'py_foo': {error_text}"
        assert "Python handle struct" in error_text, f"Error must name the 'Python handle struct' family: {error_text}"

    def test_non_injective_cn_collision(self) -> None:
        """Rules 'foo_bar' and 'foo__bar' both derive CN 'FooBar'; all families collide."""
        grammar = _make_two_rule_grammar("foo_bar", "foo__bar")
        with pytest.raises(ValueError) as exc_info:
            RustCstGenerator(grammar)
        error_text = str(exc_info.value)
        assert "FooBar" in error_text, f"Error must name the colliding identifier FooBar: {error_text}"
        assert "foo_bar" in error_text, f"Error must name rule 'foo_bar': {error_text}"
        assert "foo__bar" in error_text, f"Error must name rule 'foo__bar': {error_text}"

    def test_foo_without_label_and_foo_label_accepted(self) -> None:
        """Emitted-only semantics: 'foo' with no label + 'foo_label' does not collide (FooLabel not claimed for foo)."""
        # foo has no labels so no FooLabel is emitted; foo_label's struct FooLabel is uncontested.
        grammar = _make_two_rule_grammar("foo", "foo_label", labeled_a=False, labeled_b=True)
        gen = RustCstGenerator(grammar)
        source = gen.generate()
        # foo_label's node struct must be emitted as pub struct FooLabel
        assert "pub struct FooLabel {" in source
        # The label enum for foo_label (which has labels) would be FooLabelLabel — verify no spurious FooLabel enum
        assert "pub enum FooLabel {" not in source

    def test_trivia_collision_annotates_auto_generated(self) -> None:
        """User rule 'trivia' collides with auto-added '_trivia'; message annotates '_trivia' as auto-generated."""
        grammar = _make_single_rule_grammar("trivia")
        with pytest.raises(ValueError) as exc_info:
            RustCstGenerator(grammar)
        error_text = str(exc_info.value)
        assert "trivia" in error_text, f"Error must name 'trivia': {error_text}"
        # The auto-generated annotation must appear in the message
        assert "auto" in error_text.lower(), f"Error must mention auto-generated trivia rule: {error_text}"

    def test_user_defined_trivia_no_auto_annotation(self) -> None:
        """User-defined '_trivia' + user rule 'trivia': both reported as ordinary rules (no auto annotation)."""
        # Build a grammar that includes _trivia explicitly so add_trivia_rule_to_grammar is a no-op
        trivia_rule = gsm.Rule(
            name="_trivia",
            alternatives=[
                gsm.Items(
                    items=[
                        gsm.Item(
                            label="ws",
                            disposition=gsm.Disposition.INCLUDE,
                            term=gsm.Regex(r"\s+"),
                            quantifier=gsm.REQUIRED,
                        ),
                    ],
                    sep_after=[gsm.Separator.NO_WS],
                ),
            ],
        )
        user_trivia_rule = gsm.Rule(
            name="trivia",
            alternatives=[
                gsm.Items(
                    items=[
                        gsm.Item(
                            label="value",
                            disposition=gsm.Disposition.INCLUDE,
                            term=gsm.Regex(r"[a-z]+"),
                            quantifier=gsm.REQUIRED,
                        ),
                    ],
                    sep_after=[gsm.Separator.NO_WS],
                ),
            ],
        )
        grammar = gsm.Grammar(
            rules=(user_trivia_rule, trivia_rule),
            identifiers={"trivia": user_trivia_rule, "_trivia": trivia_rule},
        )
        with pytest.raises(ValueError) as exc_info:
            RustCstGenerator(grammar)
        error_text = str(exc_info.value)
        assert "trivia" in error_text, f"Error must name 'trivia': {error_text}"
        # No auto-generated annotation: user supplied _trivia explicitly
        assert "auto" not in error_text.lower(), (
            f"Error must NOT mention auto-generated when user defined _trivia: {error_text}"
        )

    def test_three_way_collision_all_claimants_reported(self) -> None:
        """Three rules sharing CN FooBar all appear in the collision message (no truncation to first two)."""
        # foo_bar, foo__bar, foo___bar all derive CN FooBar via non-injective snake_to_upper_camel
        g1 = _make_single_rule_grammar("foo_bar")
        g2 = _make_single_rule_grammar("foo__bar")
        g3 = _make_single_rule_grammar("foo___bar")
        grammar = gsm.Grammar(
            rules=g1.rules + g2.rules + g3.rules,
            identifiers={**g1.identifiers, **g2.identifiers, **g3.identifiers},
        )
        with pytest.raises(ValueError) as exc_info:
            RustCstGenerator(grammar)
        error_text = str(exc_info.value)
        assert "FooBar" in error_text, f"Error must name the colliding identifier FooBar: {error_text}"
        assert "foo_bar" in error_text, f"Error must name rule 'foo_bar': {error_text}"
        assert "foo__bar" in error_text, f"Error must name rule 'foo__bar': {error_text}"
        assert "foo___bar" in error_text, f"Error must name rule 'foo___bar': {error_text}"

    def test_trivia_child_rule_collides_with_auto_trivia_child_enum(self) -> None:
        """User rule 'trivia_child' collides with auto-added _trivia's child enum TriviaChild; annotation present."""
        grammar = _make_single_rule_grammar("trivia_child")
        with pytest.raises(ValueError) as exc_info:
            RustCstGenerator(grammar)
        error_text = str(exc_info.value)
        assert "TriviaChild" in error_text, f"Error must name TriviaChild: {error_text}"
        assert "trivia_child" in error_text, f"Error must name rule 'trivia_child': {error_text}"
        # The auto-generated annotation must appear (TriviaChild is claimed by the auto-added _trivia rule)
        assert "auto" in error_text.lower(), f"Error must mention auto-generated trivia rule: {error_text}"

    def test_multiple_collisions_reported_at_once(self) -> None:
        """Grammar with foo+foo_child and bar+bar_child reports both FooChild and BarChild in one ValueError."""
        # Merge two two-rule grammars (foo/foo_child, bar/bar_child) into one four-rule grammar.
        g1 = _make_two_rule_grammar("foo", "foo_child")
        g2 = _make_two_rule_grammar("bar", "bar_child")
        grammar = gsm.Grammar(
            rules=g1.rules + g2.rules,
            identifiers={**g1.identifiers, **g2.identifiers},
        )
        with pytest.raises(ValueError) as exc_info:
            RustCstGenerator(grammar)
        error_text = str(exc_info.value)
        assert "FooChild" in error_text, f"Error must name FooChild collision: {error_text}"
        assert "BarChild" in error_text, f"Error must name BarChild collision: {error_text}"

    def test_non_colliding_multi_rule_grammar_accepted(self) -> None:
        """Multi-rule grammar with no collisions constructs and generates successfully."""
        grammar = _make_two_rule_grammar("alpha", "beta")
        gen = RustCstGenerator(grammar)
        source = gen.generate()
        assert "pub struct Alpha {" in source
        assert "pub struct Beta {" in source

    def test_prediction_vs_output_consistency(self) -> None:
        """Drift guard: each predicted identifier appears in generate() output as a definition."""
        grammar = _make_two_rule_grammar("alpha", "beta", labeled_a=True, labeled_b=True)
        gen = RustCstGenerator(grammar)
        source = gen.generate()

        # Collect the augmented grammar's rules (includes _trivia)
        for rule in gen.grammar.rules:
            cn = gen.class_name_for_rule(rule.name)

            # Node struct: pub struct CN {
            assert f"pub struct {cn} {{" in source, f"Expected 'pub struct {cn} {{' for rule {rule.name!r}"
            # Handle: pub struct Py{CN} {  — use py_handle_name so a rename propagates here
            py_handle = RustCstGenerator.py_handle_name(cn)
            assert f"pub struct {py_handle} {{" in source, (
                f"Expected 'pub struct {py_handle} {{' for rule {rule.name!r}"
            )
            # Child enum: pub enum {CN}Child {
            child_enum = RustCstGenerator.child_enum_name(cn)
            assert f"pub enum {child_enum} {{" in source, f"Expected 'pub enum {child_enum} {{' for rule {rule.name!r}"
            # Label enum: only for rules that have labels — use label_enum_name so a rename propagates here
            if gen.rule_has_labels(rule.name):
                label_enum = RustCstGenerator.label_enum_name(cn)
                assert f"pub enum {label_enum} {{" in source, (
                    f"Expected 'pub enum {label_enum} {{' for labeled rule {rule.name!r}"
                )


# ---------------------------------------------------------------------------
# Union-label native accessor generation (quality-2 fix)
# ---------------------------------------------------------------------------


def _make_union_label_grammar() -> gsm.Grammar:
    """Grammar with a union-labeled rule: value_node := operand:identifier | operand:literal.

    The label `operand` maps to {identifier, literal}, triggering the union branch in
    _native_per_label_methods.  The `identifier` rule has a regex child and `literal`
    also has a regex child so neither needs trivia rules.
    """
    identifier_rule = gsm.Rule(
        name="identifier",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="name",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[_a-z][_a-z0-9]*"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
        ],
    )
    literal_rule = gsm.Rule(
        name="literal",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="val",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[0-9]+"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
        ],
    )
    # value_node has two alternatives sharing the label `operand` with different types.
    value_node_rule = gsm.Rule(
        name="value_node",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="operand",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("identifier"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
            gsm.Items(
                items=[
                    gsm.Item(
                        label="operand",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("literal"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
        ],
    )
    return gsm.Grammar(
        rules=(identifier_rule, literal_rule, value_node_rule),
        identifiers={
            "identifier": identifier_rule,
            "literal": literal_rule,
            "value_node": value_node_rule,
        },
    )


@pytest.fixture(scope="module")
def union_label_source() -> str:
    """Generated Rust source for the union-label grammar."""
    gen = RustCstGenerator(_make_union_label_grammar())
    return gen.generate()


class TestUnionLabelNativeAccessors:
    """Generator-level checks for the union-label branch of _native_per_label_methods.

    quality-2 fix: exercises child_<lbl>, maybe_<lbl>, children_<lbl>,
    append_<lbl>, and extend_<lbl> when the label maps to multiple node types
    (i.e. ref_type == "&{ClassName}Child", single_node_cls is None).
    """

    def test_child_union_lbl_returns_child_enum_ref(self, union_label_source: str) -> None:
        """child_operand returns &ValueNodeChild (the whole child enum), not a typed Shared<T>."""
        assert "pub fn child_operand(&self) -> Result<&ValueNodeChild, CstError>" in union_label_source

    def test_child_union_lbl_no_unexpected_child_type_arm(self, union_label_source: str) -> None:
        """Union branch has no UnexpectedChildType arm — no type check is needed."""
        # The child_operand body must not contain UnexpectedChildType.
        # We look for the function body between child_operand and the next pub fn.
        import re  # noqa: PLC0415

        match = re.search(
            r"pub fn child_operand\(&self\).*?(?=\n    pub fn )",
            union_label_source,
            re.DOTALL,
        )
        assert match is not None, "child_operand function not found"
        body = match.group(0)
        assert "UnexpectedChildType" not in body, "union branch must not emit UnexpectedChildType"

    def test_maybe_union_lbl_signature(self, union_label_source: str) -> None:
        """maybe_operand returns Result<Option<&ValueNodeChild>, CstError>."""
        assert "pub fn maybe_operand(&self) -> Result<Option<&ValueNodeChild>, CstError>" in union_label_source

    def test_children_union_lbl_signature(self, union_label_source: str) -> None:
        """children_operand yields &ValueNodeChild items (no type filter on union label)."""
        assert "pub fn children_operand(&self) -> impl Iterator<Item = &ValueNodeChild>" in union_label_source

    def test_children_union_lbl_uses_map_not_filter_map(self, union_label_source: str) -> None:
        """children_operand uses .map() directly — no filter_map because no type guard needed."""
        import re  # noqa: PLC0415

        match = re.search(
            r"pub fn children_operand\(&self\).*?(?=\n    pub fn )",
            union_label_source,
            re.DOTALL,
        )
        assert match is not None, "children_operand function not found"
        body = match.group(0)
        assert ".map(" in body, "should use .map() for lossless iteration"
        assert "filter_map" not in body, "union children should not filter_map"

    def test_append_union_lbl_accepts_child_enum(self, union_label_source: str) -> None:
        """append_operand accepts a ValueNodeChild value (not impl Into<Shared<T>>)."""
        assert "pub fn append_operand(&mut self, child: ValueNodeChild)" in union_label_source

    def test_extend_union_lbl_accepts_child_enum_iter(self, union_label_source: str) -> None:
        """extend_operand accepts impl IntoIterator<Item = ValueNodeChild>."""
        assert (
            "pub fn extend_operand(&mut self, children: impl IntoIterator<Item = ValueNodeChild>)" in union_label_source
        )


# ---------------------------------------------------------------------------
# Pyright harness for .pyi self-check and conformance tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def pyright_available() -> bool:
    """Return True when uv + pyright are runnable in this environment."""
    if shutil.which("uv") is None:
        return False
    result = subprocess.run(
        ["uv", "run", "pyright", "--version"],  # noqa: S607
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return result.returncode == 0


def _run_pyright_in_tmpdir(
    file_path: pathlib.Path,
    *,
    pyright_available: bool,
    cwd: pathlib.Path | None = None,
) -> list[dict[str, Any]]:
    """Run pyright --outputjson on file_path, return list of error diagnostics.

    Raises pytest.skip if pyright unavailable.
    cwd: directory to run pyright from (defaults to file_path.parent).
    """
    if not pyright_available:
        pytest.skip("pyright not available in this environment")
    run_cwd = cwd if cwd is not None else file_path.parent
    result = subprocess.run(  # noqa: S603
        ["uv", "run", "pyright", "--outputjson", str(file_path)],  # noqa: S607
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        cwd=str(run_cwd),
    )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail(f"pyright produced non-JSON output: {result.stdout[:500]}")
    return [d for d in data.get("generalDiagnostics", []) if d.get("severity") == "error"]


_REPO_ROOT = pathlib.Path(__file__).parent.parent


def _write_pyi_tmpdir(tmp_path: pathlib.Path, pyi_text: str, mod_name: str = "fegen_cst") -> pathlib.Path:
    """Write the stub to tmp_path/<mod_name>.pyi plus an empty <mod_name>.py and pyrightconfig.json.

    The pyrightconfig.json points to the repo venv so fltk imports resolve.
    Returns the path to the .pyi file.
    """
    pyi_path = tmp_path / f"{mod_name}.pyi"
    pyi_path.write_text(pyi_text)
    (tmp_path / f"{mod_name}.py").write_text("")
    (tmp_path / "pyrightconfig.json").write_text(
        json.dumps({"pythonVersion": "3.10", "venvPath": str(_REPO_ROOT), "venv": ".venv"})
    )
    return pyi_path


# ---------------------------------------------------------------------------
# .pyi pyright self-check (§4 item 3 — zero errors on the stub in isolation)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def fegen_pyright_diagnostics(
    fegen_pyi: str,
    poc_pyi: str,
    pyright_available: bool,  # noqa: FBT001
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, list[dict[str, Any]]]:
    """Run pyright once over a shared tmpdir holding all .pyi check fixtures.

    Writes: fegen_cst.pyi (stub), fegen_cst.py (empty), pyrightconfig.json,
    conformance_fixture.py (whole-module), per_class_fixture.py (per-class),
    poc_cst.pyi (PoC stub), poc_cst.py (empty).
    Runs a single `uv run pyright --outputjson <dir>` invocation and returns
    diagnostics partitioned by absolute file path.

    Batching all four pyright tests (fegen self-check, whole-module, per-class,
    and PoC self-check) into one subprocess avoids 4x cold pyright startup cost.
    """
    tmpdir = tmp_path_factory.mktemp("fegen_pyright")
    _write_pyi_tmpdir(tmpdir, fegen_pyi)
    _write_pyi_tmpdir(tmpdir, poc_pyi, mod_name="poc_cst")
    _write_module_conformance_fixture(tmpdir)
    _write_per_class_conformance_fixture(tmpdir, FEGEN_CLASS_NAMES)
    return _run_pyright_over_dir(tmpdir, pyright_available=pyright_available)


class TestGeneratePyiSelfCheck:
    """Pyright self-check: the emitted .pyi produces zero errors in isolation."""

    def test_fegen_pyi_self_check_zero_errors(
        self,
        fegen_pyright_diagnostics: dict[str, list[dict[str, Any]]],
    ) -> None:
        """The fegen grammar .pyi stub produces zero pyright errors when checked in isolation.

        This verifies internal well-typedness (all referenced names resolve, no illegal type
        forms) but does NOT compare against the protocol — that is the conformance tests' job.
        Uses the shared fegen_pyright_diagnostics fixture (one pyright run for all fegen tests).
        """
        # Filter diagnostics to those originating from the fegen_cst.pyi file.
        pyi_errors = [d for path, errs in fegen_pyright_diagnostics.items() if "fegen_cst.pyi" in path for d in errs]
        assert pyi_errors == [], f"Unexpected pyright errors in fegen .pyi self-check:\n{pyi_errors}"

    def test_poc_pyi_self_check_zero_errors(
        self,
        fegen_pyright_diagnostics: dict[str, list[dict[str, Any]]],
    ) -> None:
        """The PoC grammar .pyi stub produces zero pyright errors when checked in isolation.

        Uses the shared fegen_pyright_diagnostics fixture (one pyright run for all .pyi tests).
        """
        pyi_errors = [d for path, errs in fegen_pyright_diagnostics.items() if "poc_cst.pyi" in path for d in errs]
        assert pyi_errors == [], f"Unexpected pyright errors in PoC .pyi self-check:\n{pyi_errors}"


# ---------------------------------------------------------------------------
# Stub-vs-protocol conformance tests (§2.2, §4 item 4)
# ---------------------------------------------------------------------------


def _write_module_conformance_fixture(tmp_path: pathlib.Path, mod_name: str = "fegen_cst") -> pathlib.Path:
    """Write a fixture that imports mod_name and assigns it to cstp.CstModule without a cast."""
    fixture = tmp_path / "conformance_fixture.py"
    fixture.write_text(
        f"# ruff: noqa\n"
        f"from __future__ import annotations\n"
        f"import fltk.fegen.fltk_cst_protocol as cstp\n"
        f"import {mod_name}\n"
        f"\n"
        f"_m: cstp.CstModule = {mod_name}\n"
    )
    return fixture


def _write_per_class_conformance_fixture(
    tmp_path: pathlib.Path, class_names: list[str], mod_name: str = "fegen_cst"
) -> pathlib.Path:
    """Write per-class no-cast fixtures: def f(x: mod.Foo) -> None: _x: cstp.Foo = x."""
    lines = [
        "# ruff: noqa",
        "from __future__ import annotations",
        "import fltk.fegen.fltk_cst_protocol as cstp",
        f"import {mod_name}",
        "",
    ]
    for name in class_names:
        lines.append(f"def _check_{name.lower()}(x: {mod_name}.{name}) -> None:")
        lines.append(f"    _x: cstp.{name} = x")
        lines.append("")
    fixture = tmp_path / "per_class_fixture.py"
    fixture.write_text("\n".join(lines))
    return fixture


# ---------------------------------------------------------------------------
# Drift guard: poc_grammar.fltkg must describe the same GSM as _make_poc_grammar()
# ---------------------------------------------------------------------------


class TestPocGrammarFltkg:
    """Assert the declarative .fltkg source for the PoC grammar equals _make_poc_grammar().

    Prevents the hand-built Python fixture and the .fltkg file from silently diverging.
    Both are sources of truth for src/cst_generated.rs; this test ties them together.
    """

    @pytest.fixture(scope="class")
    def fltkg_grammar(self) -> gsm.Grammar:
        """Parse fltk/fegen/test_data/poc_grammar.fltkg via the same raw pipeline used by gen-rust-cst."""
        from fltk.fegen.genparser import _parse_grammar_raw  # noqa: PLC0415

        fltkg_path = pathlib.Path(__file__).parent.parent / "fltk" / "fegen" / "test_data" / "poc_grammar.fltkg"
        return _parse_grammar_raw(fltkg_path)

    def test_rule_names_match(self, fltkg_grammar: gsm.Grammar) -> None:
        """The .fltkg grammar has the same rule names in the same order as _make_poc_grammar()."""
        expected = _make_poc_grammar()
        assert [r.name for r in fltkg_grammar.rules] == [r.name for r in expected.rules]

    @pytest.mark.parametrize("rule_name", ["identifier", "items"])
    def test_rule_items(self, fltkg_grammar: gsm.Grammar, rule_name: str) -> None:
        """Each rule: alternatives, items, and all item fields (incl. initial_sep) match _make_poc_grammar()."""
        expected = _make_poc_grammar()
        fltkg_rule = fltkg_grammar.identifiers[rule_name]
        expected_rule = expected.identifiers[rule_name]
        assert len(fltkg_rule.alternatives) == len(expected_rule.alternatives)
        for fltkg_alt, expected_alt in zip(fltkg_rule.alternatives, expected_rule.alternatives, strict=True):
            assert fltkg_alt.initial_sep == expected_alt.initial_sep
            assert fltkg_alt.sep_after == expected_alt.sep_after
            assert len(fltkg_alt.items) == len(expected_alt.items)
            for fltkg_item, expected_item in zip(fltkg_alt.items, expected_alt.items, strict=True):
                assert fltkg_item.label == expected_item.label
                assert fltkg_item.disposition == expected_item.disposition
                assert fltkg_item.term == expected_item.term
                assert fltkg_item.quantifier == expected_item.quantifier


class TestGeneratePyiConformance:
    """Stub-vs-protocol conformance: the emitted .pyi satisfies CstModule without a cast."""

    def test_fegen_whole_module_no_cast_zero_errors(
        self,
        fegen_pyright_diagnostics: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Whole-module no-cast: assign fegen_cst module to cstp.CstModule → zero pyright errors.

        This is the primary load-bearing test: verifies the .pyi's structural conformance to
        the CstModule protocol without any cast. Post-§2.1a (Span property removal), zero errors
        is the expected and achievable outcome (design §2.2, §4 item 4).
        Uses the shared fegen_pyright_diagnostics fixture (one pyright run for all fegen tests).
        """
        errors = [d for path, errs in fegen_pyright_diagnostics.items() if "conformance_fixture" in path for d in errs]
        assert errors == [], (
            f"Expected zero pyright errors for fegen_cst -> CstModule (no cast).\n"
            f"Errors indicate a stub annotation diverges from the protocol (design §1 blockers).\n"
            f"Errors: {errors}"
        )

    def test_fegen_per_class_no_cast_zero_errors(
        self,
        fegen_pyright_diagnostics: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Per-class no-cast: each stub class is assignable to its protocol counterpart.

        Each function 'def f(x: fegen_cst.Grammar) -> None: _x: cstp.Grammar = x' must
        produce zero pyright errors — verifying that individual node-class structural
        compatibility holds, not just the module-level assignment.
        Uses the shared fegen_pyright_diagnostics fixture (one pyright run for all fegen tests).
        """
        errors = [d for path, errs in fegen_pyright_diagnostics.items() if "per_class_fixture" in path for d in errs]
        assert errors == [], (
            f"Per-class conformance failed: at least one stub class does not satisfy its "
            f"protocol counterpart without a cast.\nErrors: {errors}"
        )


# ---------------------------------------------------------------------------
# RustParserGenerator: register_classes signature
# ---------------------------------------------------------------------------


class TestRustParserRegisterClasses:
    """register_classes in parser.rs must use fully-qualified pyo3::types::PyModule.

    The parser generator uses `use pyo3::prelude::*` inside the python_bindings mod (safe
    because the parser emits only fixed names PyParser/PyApplyResult, never rule-derived PyX).
    But register_classes' parameter type must still be pyo3::types::PyModule (qualified) to
    match fltk-cst-core's register_submodule signature.
    """

    def test_register_classes_signature_uses_qualified_pymodule(self) -> None:
        """register_classes uses pyo3::types::PyModule (qualified), not bare PyModule."""
        from fltk.fegen.gsm2parser_rs import RustParserGenerator  # noqa: PLC0415

        grammar = _make_single_rule_grammar("my_rule")
        gen = RustParserGenerator(grammar)
        src = gen.generate()
        expected_sig = "pub fn register_classes(module: &Bound<'_, pyo3::types::PyModule>) -> PyResult<()> {"
        if expected_sig not in src:
            idx = src.find("register_classes")
            snippet = src[idx : idx + 120] if idx >= 0 else "(not found)"
            msg = f"parser.rs register_classes must use qualified pyo3::types::PyModule. Found: {snippet}"
            raise AssertionError(msg)
