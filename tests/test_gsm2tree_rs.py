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
        assert "use fltk_cst_core::{extract_span, get_span_type, span_to_pyobject, Span};" in poc_source
        assert "use pyo3::exceptions::{PyTypeError, PyValueError};" in poc_source
        assert "use pyo3::prelude::*;" in poc_source
        assert "use pyo3::sync::GILOnceCell;" not in poc_source
        assert "use pyo3::types::{PyList, PyTuple, PyType};" in poc_source
        assert "use pyo3::PyTypeInfo;" in poc_source
        # get_source_text_type is no longer imported (span_to_pyobject handles the full path)
        assert "get_source_text_type" not in poc_source

    def test_preamble_at_start(self, poc_source: str) -> None:
        assert poc_source.startswith("use fltk_cst_core::{extract_span, get_span_type, span_to_pyobject, Span};\n")

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
        assert "pub enum Identifier_Label {" in poc_source
        assert '#[pyo3(name = "NAME")]' in poc_source
        assert "    Name," in poc_source

    def test_identifier_label_pyclass_name(self, poc_source: str) -> None:
        assert '#[pyclass(frozen, name = "Identifier_Label")]' in poc_source

    def test_items_label_enum_present(self, poc_source: str) -> None:
        assert "pub enum Items_Label {" in poc_source
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
        assert "fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {" in poc_source

    def test_label_hash_method(self, poc_source: str) -> None:
        """__hash__ method must be emitted on label enums."""
        # Check for hand-written __hash__ that routes through PyString
        assert "fn __hash__(&self, py: Python<'_>) -> PyResult<isize> {" in poc_source
        assert "PyString::new(py, self.__repr__())" in poc_source

    def test_label_eq_uses_canonical_name_marker(self, poc_source: str) -> None:
        """__eq__ must read _fltk_canonical_name from the operand (duck-typed marker)."""
        assert '"_fltk_canonical_name"' in poc_source

    def test_allow_non_camel_case_types(self, poc_source: str) -> None:
        # PoC grammar has 3 label-bearing rules: Identifier, Items, Trivia
        assert poc_source.count("#[allow(non_camel_case_types)]") >= 3  # one per label enum

    def test_derive_clone_partialeq_eq_hash(self, poc_source: str) -> None:
        # PoC grammar has 3 label-bearing rules: Identifier, Items, Trivia
        assert poc_source.count("#[derive(Clone, PartialEq, Eq, Hash)]") >= 3


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
        """§2.2: span field is native Span, not PyObject."""
        assert "span: Span," in poc_source
        assert "span: PyObject," not in poc_source

    def test_span_getter_emitted(self, poc_source: str) -> None:
        """§2.2: explicit span getter returning fltk._native.Span (cross-cdylib via PyObject)."""
        assert "fn span(&self, py: Python<'_>) -> PyResult<PyObject> {" in poc_source

    def test_span_setter_emitted(self, poc_source: str) -> None:
        """§2.2: explicit span setter (cross-cdylib compatible via extract_span helper)."""
        assert "fn set_span(&mut self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {" in poc_source

    def test_children_field_native_vec(self, poc_source: str) -> None:
        """§2.3: children field is a native Vec, not Py<PyList>."""
        # IdentifierChild is the per-node child enum for Identifier
        assert "children: Vec<(Option<Identifier_Label>, IdentifierChild)>," in poc_source
        assert "children: Py<PyList>," not in poc_source
        assert "#[pyo3(get)]\n    children:" not in poc_source

    def test_children_getter_emitted(self, poc_source: str) -> None:
        """§2.3: explicit children getter rebuilds PyList from Vec."""
        assert "fn children(&self, py: Python<'_>) -> PyResult<Py<PyList>> {" in poc_source

    def test_child_enum_emitted(self, poc_source: str) -> None:
        """§2.3: per-node child enum is emitted for each node class."""
        assert "pub enum IdentifierChild {" in poc_source
        assert "pub enum ItemsChild {" in poc_source
        # Identifier only has Span children (regex terminal)
        assert "IdentifierChild {\n    Span(Span)," in poc_source
        # Items has Span (literals) and Identifier (rule ref) children
        assert "Span(Span)," in poc_source
        assert "Identifier(Box<Identifier>)," in poc_source

    def test_label_classattr_present(self, poc_source: str) -> None:
        assert "#[classattr]" in poc_source
        assert "#[allow(non_snake_case)]" in poc_source
        assert "fn Label(py: Python<'_>) -> PyResult<PyObject> {" in poc_source

    def test_extend_children_emitted(self, poc_source: str) -> None:
        """§2.3/§2.5: extend_children method is emitted for each node class."""
        assert "fn extend_children(" in poc_source
        assert "fn extend_children(&mut self, other: PyRef<'_, Identifier>) -> PyResult<()> {" in poc_source

    def test_get_span_type_helper_not_emitted(self, poc_source: str) -> None:
        """quality-1: helpers now in fltk-cst-core; no local helper or per-method init block."""
        # No local helper definitions (they're in fltk-cst-core).
        assert "fn get_span_type(py: Python<'_>) -> PyResult<Bound<'_, PyType>> {" not in poc_source
        # No per-method let span_type = FLTK_NATIVE_SPAN_TYPE.get_or_try_init block.
        assert "let span_type = FLTK_NATIVE_SPAN_TYPE.get_or_try_init" not in poc_source


# ---------------------------------------------------------------------------
# AC-5: register_classes function
# ---------------------------------------------------------------------------


class TestRegisterClasses:
    def test_register_classes_function_present(self, poc_source: str) -> None:
        """AC-5: pub fn register_classes is present."""
        assert "pub fn register_classes(module: &Bound<'_, PyModule>) -> PyResult<()> {" in poc_source

    def test_register_classes_adds_identifier_label(self, poc_source: str) -> None:
        assert "module.add_class::<Identifier_Label>()?;" in poc_source

    def test_register_classes_adds_identifier(self, poc_source: str) -> None:
        assert "module.add_class::<Identifier>()?;" in poc_source

    def test_register_classes_adds_items_label(self, poc_source: str) -> None:
        assert "module.add_class::<Items_Label>()?;" in poc_source

    def test_register_classes_adds_items(self, poc_source: str) -> None:
        assert "module.add_class::<Items>()?;" in poc_source

    def test_register_classes_label_before_struct(self, poc_source: str) -> None:
        """Label enum must be registered before the node struct — PyO3 requires referenced types registered first."""
        idx_label = poc_source.index("module.add_class::<Identifier_Label>()?;")
        idx_struct = poc_source.index("module.add_class::<Identifier>()?;")
        assert idx_label < idx_struct

    def test_register_classes_returns_ok(self, poc_source: str) -> None:
        assert "    Ok(())\n}" in poc_source


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
        assert "pub fn register_classes(module: &Bound<'_, PyModule>) -> PyResult<()> {" in fegen_source

    def test_all_14_classes_registered(self, fegen_source: str) -> None:
        """AC-7: all 14 classes have add_class calls in register_classes."""
        for class_name in FEGEN_CLASS_NAMES:
            assert f"module.add_class::<{class_name}>()?;" in fegen_source, (
                f"Expected 'module.add_class::<{class_name}>()?;' in fegen source"
            )

    def test_preamble_in_fegen_source(self, fegen_source: str) -> None:
        """AC-10: fegen source also has the required preamble."""
        assert "use fltk_cst_core::{extract_span, get_span_type, span_to_pyobject, Span};" in fegen_source
        assert "use pyo3::prelude::*;" in fegen_source
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
        assert "pub enum Numbers_Label {" in minimal_source
        assert '#[pyo3(name = "DIGITS")]' in minimal_source
        assert "    Digits," in minimal_source

    def test_minimal_grammar_has_preamble(self, minimal_source: str) -> None:
        """AC-10: Minimal grammar source also includes required use declarations."""
        assert "use fltk_cst_core::{extract_span, get_span_type, span_to_pyobject, Span};" in minimal_source
        assert "use pyo3::prelude::*;" in minimal_source
        assert "use pyo3::sync::GILOnceCell;" not in minimal_source
        assert "use crate::UNKNOWN_SPAN;" not in minimal_source
        assert "UNKNOWN_SPAN_CACHE" not in minimal_source
        assert "FLTK_NATIVE_SPAN_TYPE" not in minimal_source
        assert "get_source_text_type" not in minimal_source


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
        assert "module.add_class::<Foo>()?;" in source


# ---------------------------------------------------------------------------
# NodeKind enum generation
# ---------------------------------------------------------------------------


class TestNodeKindEnum:
    def test_node_kind_enum_present(self, poc_source: str) -> None:
        """NodeKind enum is emitted before all node structs."""
        assert "pub enum NodeKind {" in poc_source

    def test_node_kind_pyclass_no_eq_hash(self, poc_source: str) -> None:
        """NodeKind #[pyclass] must not have eq/hash (hand-written instead)."""
        # Confirm the NodeKind pyclass line exists and lacks eq/hash
        assert '#[pyclass(frozen, name = "NodeKind")]' in poc_source
        # eq/hash must not appear in combination with the NodeKind class line
        lines = poc_source.splitlines()
        for line in lines:
            if '#[pyclass(frozen, name = "NodeKind")]' in line:
                assert "eq" not in line
                assert "hash" not in line

    def test_node_kind_has_identifier_and_items_variants(self, poc_source: str) -> None:
        """PoC grammar produces IDENTIFIER and ITEMS variants in NodeKind."""
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
        assert "fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {" in poc_source

    def test_node_kind_hash_method(self, poc_source: str) -> None:
        """NodeKind has a hand-written __hash__ routing through PyString::hash."""
        assert "fn __hash__(&self, py: Python<'_>) -> PyResult<isize> {" in poc_source

    def test_node_kind_registered_first(self, poc_source: str) -> None:
        """NodeKind must be registered before node structs in register_classes."""
        idx_node_kind = poc_source.index("module.add_class::<NodeKind>()?;")
        idx_identifier = poc_source.index("module.add_class::<Identifier>()?;")
        assert idx_node_kind < idx_identifier

    def test_node_kind_before_label_enums(self, poc_source: str) -> None:
        """NodeKind enum block appears before the first Label enum block in the source."""
        idx_node_kind_enum = poc_source.index("pub enum NodeKind {")
        idx_first_label_enum = poc_source.index("pub enum Identifier_Label {")
        assert idx_node_kind_enum < idx_first_label_enum

    def test_fegen_grammar_node_kind_has_all_14(self, fegen_source: str) -> None:
        """Fegen grammar NodeKind has all 14 class-name-derived members."""
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
        """The kind getter is annotated with #[getter] immediately before its fn declaration."""
        # Verify that "#[getter]" appears as the immediately preceding non-blank, non-comment line
        # before "fn kind(&self) -> NodeKind {" — this ensures the attribute is actually on the
        # kind function, not just that #[getter] appears somewhere in the file.
        lines = poc_source.splitlines()
        kind_fn_sig = "fn kind(&self) -> NodeKind {"
        for i, line in enumerate(lines):
            if kind_fn_sig in line:
                # Walk backward over blank lines to find the preceding non-blank line
                j = i - 1
                while j >= 0 and lines[j].strip() == "":
                    j -= 1
                assert j >= 0, "No non-blank line found before fn kind"
                assert "#[getter]" in lines[j], (
                    f"Expected '#[getter]' immediately before 'fn kind', found: {lines[j]!r}"
                )
                break
        else:
            pytest.fail("'fn kind(&self) -> NodeKind {' not found in poc_source")

    def test_fegen_grammar_all_node_kinds_present(self, fegen_source: str) -> None:
        """All 14 node class names appear as NodeKind variants in fegen source."""
        for class_name in FEGEN_CLASS_NAMES:
            assert f"NodeKind::{class_name}" in fegen_source, f"Expected 'NodeKind::{class_name}' in fegen source"


# ---------------------------------------------------------------------------
# §4 item 2: No-PyObject audit (generator source level)
# ---------------------------------------------------------------------------


class TestNoPyObjectAudit:
    def test_no_pyobject_span_field(self, poc_source: str) -> None:
        """§4 item 2: No generated node struct has span: PyObject."""
        assert "span: PyObject," not in poc_source

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
        """§2.4: __eq__ uses native Rust PartialEq (self == &*other_node), not Python .eq()."""
        assert "self == &*other_node" in poc_source
        assert "// Native structural equality: no Python .eq() on stored state" in poc_source

    def test_eq_no_python_span_eq(self, poc_source: str) -> None:
        """§2.4: Python .eq() on span must not appear in __eq__."""
        assert "self.span.bind(py).eq(" not in poc_source

    def test_eq_no_python_children_eq(self, poc_source: str) -> None:
        """§2.4: Python .eq() on children must not appear in __eq__."""
        assert "self.children.bind(py).eq(" not in poc_source

    def test_repr_uses_native_span_repr(self, poc_source: str) -> None:
        """§2.4: __repr__ uses native span start()/end() accessors, not Python .repr() on a bound obj."""
        assert "self.span.start()" in poc_source
        assert "self.span.end()" in poc_source
        assert "self.span.bind(py).repr()" not in poc_source


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
    """Class/label set of the .pyi must equal that of the .rs (drift guard)."""

    def _extract_rs_classes(self, rs_source: str) -> set[str]:
        import re  # noqa: PLC0415

        return set(re.findall(r"pub struct (\w+) \{", rs_source))

    def _extract_pyi_classes(self, pyi_source: str) -> set[str]:
        import re  # noqa: PLC0415

        return set(re.findall(r"^class (\w+):", pyi_source, re.MULTILINE))

    def test_poc_class_set_matches(self, poc_source: str, poc_pyi: str) -> None:
        """PoC grammar: class names in .pyi equal class names in .rs."""
        rs_classes = self._extract_rs_classes(poc_source)
        pyi_classes = self._extract_pyi_classes(poc_pyi)
        assert rs_classes == pyi_classes

    def test_fegen_class_set_matches(self, fegen_source: str, fegen_pyi: str) -> None:
        """Fegen grammar: class names in .pyi equal class names in .rs."""
        rs_classes = self._extract_rs_classes(fegen_source)
        pyi_classes = self._extract_pyi_classes(fegen_pyi)
        assert rs_classes == pyi_classes


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


def _run_pyright_over_dir(
    tmpdir: pathlib.Path,
    *,
    pyright_available: bool,
) -> dict[str, list[dict[str, Any]]]:
    """Run pyright --outputjson over a directory; return errors partitioned by file path.

    Returns a dict mapping each file's absolute path string to its list of error diagnostics.
    Raises pytest.skip if pyright unavailable.
    """
    if not pyright_available:
        pytest.skip("pyright not available in this environment")
    result = subprocess.run(  # noqa: S603
        ["uv", "run", "pyright", "--outputjson", str(tmpdir)],  # noqa: S607
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        cwd=str(tmpdir),
    )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail(f"pyright produced non-JSON output: {result.stdout[:500]}")
    partitioned: dict[str, list[dict[str, Any]]] = {}
    for diag in data.get("generalDiagnostics", []):
        if diag.get("severity") != "error":
            continue
        file_key = diag.get("file", "")
        partitioned.setdefault(file_key, []).append(diag)
    return partitioned


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
    pyright_available: bool,  # noqa: FBT001
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, list[dict[str, Any]]]:
    """Run pyright once over a shared tmpdir holding all fegen .pyi check fixtures.

    Writes: fegen_cst.pyi (stub), fegen_cst.py (empty), pyrightconfig.json,
    conformance_fixture.py (whole-module), per_class_fixture.py (per-class).
    Runs a single `uv run pyright --outputjson <dir>` invocation and returns
    diagnostics partitioned by absolute file path.

    Batching the three fegen pyright tests (self-check, whole-module, per-class)
    into one subprocess avoids 3x cold pyright startup cost.
    """
    tmpdir = tmp_path_factory.mktemp("fegen_pyright")
    _write_pyi_tmpdir(tmpdir, fegen_pyi)
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
        tmp_path: pathlib.Path,
        poc_pyi: str,
        pyright_available: bool,  # noqa: FBT001
    ) -> None:
        """The PoC grammar .pyi stub produces zero pyright errors when checked in isolation."""
        pyi_path = _write_pyi_tmpdir(tmp_path, poc_pyi, mod_name="poc_cst")
        errors = _run_pyright_in_tmpdir(pyi_path, pyright_available=pyright_available)
        assert errors == [], f"Unexpected pyright errors in PoC .pyi self-check:\n{errors}"


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
