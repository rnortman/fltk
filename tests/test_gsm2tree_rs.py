"""Generator unit tests for RustCstGenerator (gsm2tree_rs.py).

These tests validate the source text produced by the generator, not the compiled
Rust output. The compiled output is validated by test_rust_cst_poc.py (PoC grammar)
and test_fegen_rust_cst.py (fegen grammar).
"""

from __future__ import annotations

import pathlib
import re

import pytest

from fltk.fegen import gsm
from fltk.fegen.gsm2tree_rs import RustCstGenerator

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
# Zero-label grammar (unlabeled INCLUDE items)
# ---------------------------------------------------------------------------

def _make_zero_label_grammar() -> gsm.Grammar:
    """Rule with no labeled items — label enum must be omitted."""
    unlabeled_rule = gsm.Rule(
        name="token",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[a-z]+"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
        ],
    )
    return gsm.Grammar(
        rules=(unlabeled_rule,),
        identifiers={"token": unlabeled_rule},
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
def fegen_source() -> str:
    """Generated Rust source for the fegen.fltkg 14-rule grammar."""
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

    gen = RustCstGenerator(grammar)
    return gen.generate()


# ---------------------------------------------------------------------------
# AC-10: Preamble correctness
# ---------------------------------------------------------------------------

class TestPreamble:
    def test_required_use_declarations(self, poc_source: str) -> None:
        """AC-10: Every generated .rs file includes the required use declarations."""
        assert "use pyo3::exceptions::{PyTypeError, PyValueError};" in poc_source
        assert "use pyo3::prelude::*;" in poc_source
        assert "use pyo3::types::{PyList, PyTuple};" in poc_source
        assert "use pyo3::PyTypeInfo;" in poc_source
        assert "use crate::UNKNOWN_SPAN;" in poc_source

    def test_preamble_at_start(self, poc_source: str) -> None:
        assert poc_source.startswith("use pyo3::")


# ---------------------------------------------------------------------------
# AC-1 precondition: expected labels in generated source
# ---------------------------------------------------------------------------

class TestPocGrammarLabels:
    def test_identifier_label_enum_present(self, poc_source: str) -> None:
        assert "pub enum Identifier_Label {" in poc_source
        assert '#[pyo3(name = "NAME")]' in poc_source
        assert "    Name," in poc_source

    def test_identifier_label_pyclass_name(self, poc_source: str) -> None:
        assert '#[pyclass(eq, hash, frozen, name = "Identifier_Label")]' in poc_source

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

    def test_span_field(self, poc_source: str) -> None:
        assert "#[pyo3(get, set)]" in poc_source
        assert "span: PyObject," in poc_source

    def test_children_field(self, poc_source: str) -> None:
        assert "#[pyo3(get)]" in poc_source
        assert "children: Py<PyList>," in poc_source

    def test_label_classattr_present(self, poc_source: str) -> None:
        assert "#[classattr]" in poc_source
        assert "#[allow(non_snake_case)]" in poc_source
        assert "fn Label(py: Python<'_>) -> PyResult<PyObject> {" in poc_source


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
    "grammar", "rule", "alternatives", "items", "item", "term",
    "disposition", "quantifier", "identifier", "raw_string", "literal",
    "_trivia", "line_comment", "block_comment",
]

FEGEN_CLASS_NAMES = [
    "Grammar", "Rule", "Alternatives", "Items", "Item", "Term",
    "Disposition", "Quantifier", "Identifier", "RawString", "Literal",
    "Trivia", "LineComment", "BlockComment",
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
        assert "use pyo3::prelude::*;" in fegen_source
        assert "use crate::UNKNOWN_SPAN;" in fegen_source

    def test_rule_name_to_class_name_mapping(self) -> None:
        """FEGEN_RULE_NAMES and FEGEN_CLASS_NAMES must agree with class_name_for_rule_node."""
        from fltk.fegen import gsm  # noqa: PLC0415
        from fltk.fegen.gsm2tree import CstGenerator  # noqa: PLC0415
        from fltk.iir.context import create_default_context  # noqa: PLC0415
        from fltk.iir.py import reg as pyreg  # noqa: PLC0415

        # Build a minimal CstGenerator with a dummy grammar to access the name helper.
        dummy_rule = gsm.Rule(
            name="dummy",
            alternatives=[gsm.Items(items=[gsm.Item(
                label="x",
                disposition=gsm.Disposition.INCLUDE,
                term=gsm.Regex(r"x"),
                quantifier=gsm.REQUIRED,
            )], sep_after=[gsm.Separator.NO_WS])],
        )
        dummy_grammar = gsm.Grammar(rules=(dummy_rule,), identifiers={"dummy": dummy_rule})
        gen = CstGenerator(grammar=dummy_grammar, py_module=pyreg.Builtins, context=create_default_context())
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
        assert "use pyo3::prelude::*;" in minimal_source
        assert "use crate::UNKNOWN_SPAN;" in minimal_source


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
        assert "Token_Label" not in source

    def test_zero_label_rule_still_emits_struct(self) -> None:
        gen = RustCstGenerator(_make_zero_label_grammar())
        source = gen.generate()
        assert "pub struct Token {" in source

    def test_zero_label_rule_omits_label_classattr(self) -> None:
        """#[classattr] Label is not emitted in the Token impl block (no label enum exists)."""
        gen = RustCstGenerator(_make_zero_label_grammar())
        source = gen.generate()
        # Extract the impl Token { ... } block and verify Label classattr is absent from it.
        # (The _trivia rule added by the generator does have labels, so the file as a whole
        #  may contain 'fn Label' — but not inside the Token impl block.)
        # Use regex to match the impl block up to the first `\n}` at column 0 (not indented).
        m = re.search(r"impl Token \{(.+?)\n\}", source, re.DOTALL)
        assert m is not None, "impl Token { ... } block not found in generated source"
        token_impl = m.group(0)
        assert "fn Label(" not in token_impl

    def test_zero_label_rule_register_classes_no_enum(self) -> None:
        gen = RustCstGenerator(_make_zero_label_grammar())
        source = gen.generate()
        assert "module.add_class::<Token_Label>()?;" not in source
        assert "module.add_class::<Token>()?;" in source
