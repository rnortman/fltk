"""Tier-2 Phase 4 tests: the Rust fegen CST backend.

These tests require the fegen_rust_cst extension to be built.
They are skipped automatically when the module is not importable (run
`make build-fegen-rust-cst` first, or use CI which builds it before pytest).
A CI lane where every test here is skipped is a failure signal — the artifact
is not being built.

Test coverage:
  AC6 (partial) — make build-fegen-rust-cst produces an importable fegen_rust_cst module
  AC9 — label comparisons are backend-independent
  Self-hosting — Rust parser → Rust CST → real Cst2Gsm equals the Python path
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

from fltk._native import SourceText, Span  # noqa: E402
from fltk.fegen import fltk2gsm  # noqa: E402
from fltk.fegen import fltk_cst as py_cst  # noqa: E402
from fltk.fegen.pyrt import terminalsrc as tsrc  # noqa: E402
from fltk.plumbing import parse_grammar  # noqa: E402

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


# ── Child accessor contract: span roundtrip and type pins ─────────────────


_CHILD_SPAN_PARAMS = pytest.mark.parametrize(
    "node_class,append_method,child_method",
    [
        (fegen_rust_cst.cst.Identifier, "append_name", "child_name"),
        (fegen_rust_cst.cst.Literal, "append_value", "child_value"),
        (fegen_rust_cst.cst.RawString, "append_value", "child_value"),
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
        """fegen_rust_cst.cst exposes each expected grammar node class."""
        assert hasattr(fegen_rust_cst.cst, class_name), f"Missing class: {class_name}"
        assert isinstance(getattr(fegen_rust_cst.cst, class_name), type)

    def test_module_is_standalone(self):
        """The fegen_rust_cst module is importable as a standalone extension."""
        mod = importlib.import_module("fegen_rust_cst")
        assert mod is not None
        # Verify the cst submodule is accessible
        assert hasattr(mod, "cst")


# ── AC9: label-compare backend independence ────────────────────────────────


class TestAC9LabelBackendIndependence:
    """AC9: label comparisons in Cst2Gsm succeed regardless of which backend produced the label.

    A label held from the Rust fegen_rust_cst backend compares equal (and is
    in-found) against the corresponding constant from the fixed Python fltk_cst module.
    """

    def test_rust_label_equals_python_constant(self):
        """A Rust-backend label compares == to the Python fltk_cst constant."""
        rust_label = fegen_rust_cst.cst.Items.Label.NO_WS
        py_label = py_cst.Items.Label.NO_WS
        assert rust_label == py_label, f"Rust label {rust_label!r} != Python label {py_label!r}"

    def test_rust_label_in_python_tuple(self):
        """A Rust-backend label is found in a tuple of Python constants."""
        rust_label = fegen_rust_cst.cst.Items.Label.ITEM
        assert rust_label in (py_cst.Items.Label.ITEM, py_cst.Items.Label.NO_WS)

    def test_cst2gsm_no_cst_parameter(self):
        """Cst2Gsm takes only terminals — no cst= parameter after self.cst removal."""
        terminals_obj = tsrc.TerminalSource(_SIMPLE_GRAMMAR)
        cst2gsm_instance = fltk2gsm.Cst2Gsm(terminals_obj.terminals)
        assert not hasattr(cst2gsm_instance, "cst"), "self.cst should be absent from Cst2Gsm"


# ── Self-hosting: Rust parser → Rust CST → real Cst2Gsm ──────────────────


class TestRustParserSelfHosting:
    """Self-hosting: Rust-generated parser → Rust CST → real Cst2Gsm equals Python path.

    Exercises fegen_rust_cst.parser.Parser directly (not via plumbing.parse_grammar):
      1. Instantiate fegen_rust_cst.parser.Parser(text, capture_trivia=False)
      2. Call parser.apply__parse_grammar(0)
      3. Assert result is not None and result.pos == len(text)
      4. Run fltk2gsm.Cst2Gsm(text).visit_grammar(result.result)
      5. Compare to plumbing.parse_grammar(text) (pure-Python reference path)

    Satisfies §5 item 4 of the controlling design: Rust-parser → Rust-CST → real Cst2Gsm
    over fegen.fltkg, equal to the Python path's GSM.
    """

    def _assert_rust_parser_equals_python(self, text: str) -> None:
        """Parse text with the Rust parser and compare the resulting GSM to the Python path."""
        parser = fegen_rust_cst.parser.Parser(text, capture_trivia=False)
        result = parser.apply__parse_grammar(0)
        assert result is not None, parser.error_message()
        assert result.pos == len(text), (
            f"Partial parse: consumed {result.pos}/{len(text)} chars. Error tracker: {parser.error_message()}"
        )
        assert isinstance(result.result, fegen_rust_cst.cst.Grammar), type(result.result)
        gsm_rust = fltk2gsm.Cst2Gsm(text).visit_grammar(result.result)
        gsm_python = parse_grammar(text)
        assert gsm_rust == gsm_python

    def test_simple_grammar(self):
        """Minimal grammar: Rust parser → Rust CST → Cst2Gsm equals Python path."""
        self._assert_rust_parser_equals_python(_SIMPLE_GRAMMAR)

    def test_multi_rule_grammar(self):
        """Multi-rule grammar with alternatives: Rust parser path equals Python path."""
        self._assert_rust_parser_equals_python(_MULTI_RULE_GRAMMAR)

    def test_fegen_grammar_self_hosted(self):
        """fegen.fltkg self-hosted through the Rust parser; GSM must equal Python path.

        This is the §5 item 4 requirement: the grammar that parses all user grammars,
        parsed by the Rust parser it generated, producing a GSM equal to the Python path.
        """
        assert _FEGEN_FLTKG_PATH.exists(), f"fegen.fltkg not found at {_FEGEN_FLTKG_PATH}"
        text = _FEGEN_FLTKG_PATH.read_text(encoding="utf-8")
        self._assert_rust_parser_equals_python(text)
