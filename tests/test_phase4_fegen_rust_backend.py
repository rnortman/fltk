"""Tier-2 Phase 4 tests: AC8 — real Cst2Gsm on the Rust fegen backend.

These tests require the fegen_rust_cst extension to be built.
They are skipped automatically when the module is not importable (run
`make build-fegen-rust-cst` first, or use CI which builds it before pytest).
A CI lane where every test here is skipped is a failure signal — the artifact
is not being built.

Test coverage:
  AC6 (partial) — make build-fegen-rust-cst produces an importable fegen_rust_cst module
  AC8 — the *real* fltk2gsm.Cst2Gsm runs against the Rust fegen backend via
         parse_grammar(rust_fegen_cst_module="fegen_rust_cst"); the resulting
         gsm.Grammar is equal to the Python-backend result on the same input.
         No hand-written substitute for Cst2Gsm.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import ClassVar

import pytest

# ---------------------------------------------------------------------------
# Module-level skip when fegen Rust CST extension not available
# ---------------------------------------------------------------------------

fegen_rust_cst = pytest.importorskip(
    "fegen_rust_cst",
    reason="fegen_rust_cst not built; run 'make build-fegen-rust-cst' first",
)

import fltk.fegen.fltk2gsm as fltk2gsm_mod  # noqa: E402
from fltk._native import SourceText, Span  # noqa: E402
from fltk._native import fegen_cst as embedded_fegen_cst  # noqa: E402
from fltk.fegen import fltk2gsm  # noqa: E402
from fltk.fegen import fltk_cst as py_cst  # noqa: E402
from fltk.fegen.pyrt import terminalsrc as tsrc  # noqa: E402
from fltk.plumbing import parse_grammar, parse_grammar_file  # noqa: E402

# ── Shared test inputs ─────────────────────────────────────────────────────

_SIMPLE_GRAMMAR = 'test := "hello";'

_MULTI_RULE_GRAMMAR = """
thing := left , op , right ;
left := id ;
right := id ;
op := "+" | "-" ;
id := /[a-z]+/ ;
"""

_FEGEN_FLTKG_PATH = Path(__file__).parent.parent / "fltk" / "fegen" / "fegen.fltkg"


# ── AC8: real Cst2Gsm on Rust fegen backend ───────────────────────────────


class TestAC8RealCst2GsmRustBackend:
    """AC8 (binding): real fltk2gsm.Cst2Gsm runs against Rust fegen CST.

    parse_grammar(text, rust_fegen_cst_module="fegen_rust_cst") must produce
    a gsm.Grammar equal to parse_grammar(text) (Python backend) on the same input.
    No hand-written Cst2Gsm substitute.
    """

    def test_simple_grammar_rust_equals_python(self):
        """Simple single-rule grammar: Rust backend produces the same gsm.Grammar as Python."""
        python_result = parse_grammar(_SIMPLE_GRAMMAR)
        rust_result = parse_grammar(_SIMPLE_GRAMMAR, rust_fegen_cst_module="fegen_rust_cst")
        assert python_result == rust_result

    def test_multi_rule_grammar_rust_equals_python(self):
        """Multi-rule grammar with alternatives: Rust == Python backend."""
        python_result = parse_grammar(_MULTI_RULE_GRAMMAR)
        rust_result = parse_grammar(_MULTI_RULE_GRAMMAR, rust_fegen_cst_module="fegen_rust_cst")
        assert python_result == rust_result

    def test_fegen_grammar_itself_rust_equals_python(self):
        """Parse fegen.fltkg itself with both backends; results must be equal.

        This is the strongest AC8 check: the actual fegen grammar (used to parse
        all user grammars) produces the same gsm.Grammar regardless of CST backend.
        """
        python_result = parse_grammar_file(_FEGEN_FLTKG_PATH)
        rust_result = parse_grammar_file(_FEGEN_FLTKG_PATH, rust_fegen_cst_module="fegen_rust_cst")
        assert python_result == rust_result

    def test_rust_backend_uses_real_cst2gsm(self):
        """Verify the Rust path calls Cst2Gsm (not a hand-written substitute).

        Monkeypatches Cst2Gsm.__init__ to confirm it is called exactly once
        by parse_grammar with the Rust backend.
        """
        captured: list[object] = []
        original_init = fltk2gsm_mod.Cst2Gsm.__init__

        def recording_init(self, terminals):
            captured.append(terminals)
            return original_init(self, terminals)

        fltk2gsm_mod.Cst2Gsm.__init__ = recording_init
        try:
            parse_grammar(_SIMPLE_GRAMMAR, rust_fegen_cst_module="fegen_rust_cst")
        finally:
            fltk2gsm_mod.Cst2Gsm.__init__ = original_init

        assert len(captured) == 1, "Cst2Gsm.__init__ not called exactly once"


# ── Child accessor contract: span roundtrip and type pins ─────────────────


# TODO(child-span-params-dedup): These three triples duplicate the _span-factory rows of
# CLASS_LABEL_INFO in tests/test_fegen_rust_cst.py:55-57. A label rename in the generated
# CST requires updating both lists; they could be unified via a shared conftest fixture.
_CHILD_SPAN_PARAMS = pytest.mark.parametrize(
    "node_class,append_method,child_method",
    [
        (fegen_rust_cst.Identifier, "append_name", "child_name"),
        (fegen_rust_cst.Literal, "append_value", "child_value"),
        (fegen_rust_cst.RawString, "append_value", "child_value"),
    ],
    ids=["Identifier.child_name", "Literal.child_value", "RawString.child_value"],
)


class TestChildSpanAccessorContract:
    """Focused regression tests for Rust-backed fegen node child span accessors.

    Pins the contracts required by fltk2gsm._span_text (used by visit_identifier,
    visit_literal, visit_regex) on objects returned by child_name()/child_value().
    The AC8 equality tests cover this indirectly; these tests give a localized failure
    signal if an accessor's return type or source-preservation regresses.
    """

    @_CHILD_SPAN_PARAMS
    def test_sourceless_span_start_end(self, node_class, append_method, child_method):
        """Sourceless roundtrip: return type is fltk._native.Span; .start/.end are accessible."""
        span = Span(3, 9)
        node = node_class()
        getattr(node, append_method)(span)
        result = getattr(node, child_method)()
        assert isinstance(result, Span)
        assert result.start == 3
        assert result.end == 9
        assert result.text() is None
        assert result.has_source() is False

    @_CHILD_SPAN_PARAMS
    def test_source_bearing_span_text(self, node_class, append_method, child_method):
        """Source-bearing roundtrip: source survives native storage; .text() returns correct slice."""
        src = SourceText("hello world!")
        span = Span.with_source(3, 9, src)
        node = node_class()
        getattr(node, append_method)(span)
        result = getattr(node, child_method)()
        assert isinstance(result, Span)
        assert result.start == 3
        assert result.end == 9
        assert result.has_source() is True
        assert result.text() == "lo wor"

    @_CHILD_SPAN_PARAMS
    def test_append_rejects_terminalsrc_span(self, node_class, append_method, child_method):  # noqa: ARG002
        """append_<label> rejects terminalsrc.Span; only fltk._native.Span is accepted."""
        bad = tsrc.Span(3, 9)
        node = node_class()
        with pytest.raises(TypeError, match="unsupported child type"):
            getattr(node, append_method)(bad)


# ── AC6 (partial): fegen_rust_cst is importable and has expected classes ──


class TestAC6FegenRustCstModule:
    """AC6 (partial): the fegen Rust CST module exposes the expected 14 grammar node classes."""

    _EXPECTED_CLASSES: ClassVar[list[str]] = [
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

    @pytest.mark.parametrize("class_name", _EXPECTED_CLASSES)
    def test_class_exposed(self, class_name: str):
        """fegen_rust_cst exposes each expected grammar node class."""
        assert hasattr(fegen_rust_cst, class_name), f"Missing class: {class_name}"
        assert isinstance(getattr(fegen_rust_cst, class_name), type)

    def test_module_is_standalone(self):
        """The fegen_rust_cst module is importable separately from fltk._native.fegen_cst."""
        mod = importlib.import_module("fegen_rust_cst")
        assert mod is not None
        # Verify it's distinct from the embedded fltk._native.fegen_cst submodule
        assert mod is not embedded_fegen_cst


# ── AC9: label-compare backend independence ────────────────────────────────


class TestAC9LabelBackendIndependence:
    """AC9: label comparisons in Cst2Gsm succeed regardless of which backend produced the label.

    A label held from the Rust fegen_rust_cst backend compares equal (and is
    in-found) against the corresponding constant from the fixed Python fltk_cst module.
    """

    def test_rust_label_equals_python_constant(self):
        """A Rust-backend label compares == to the Python fltk_cst constant."""
        rust_label = fegen_rust_cst.Items.Label.NO_WS
        py_label = py_cst.Items.Label.NO_WS
        assert rust_label == py_label, f"Rust label {rust_label!r} != Python label {py_label!r}"

    def test_rust_label_in_python_tuple(self):
        """A Rust-backend label is found in a tuple of Python constants."""
        rust_label = fegen_rust_cst.Items.Label.ITEM
        assert rust_label in (py_cst.Items.Label.ITEM, py_cst.Items.Label.NO_WS)

    def test_cst2gsm_no_cst_parameter(self):
        """Cst2Gsm takes only terminals — no cst= parameter after self.cst removal."""
        terminals_obj = tsrc.TerminalSource(_SIMPLE_GRAMMAR)
        cst2gsm_instance = fltk2gsm.Cst2Gsm(terminals_obj.terminals)
        assert not hasattr(cst2gsm_instance, "cst"), "self.cst should be absent from Cst2Gsm"
