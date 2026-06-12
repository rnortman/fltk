"""Module-split acceptance tests: §4.3-§4.6 of the rust-bindings-module-split design.

Verifies:
  §4.3 -- collision fixture: Parser/ApplyResult CST classes and parser machinery coexist.
  §4.4 -- import mechanics for fegen_rust_cst (sys.modules, from-import, importlib).
  §4.5 -- Span/SourceText absent from generated modules; present where required.
  §4.6 -- fltk._native.poc_cst: PoC classes reachable at new path, absent from top level.
"""

from __future__ import annotations

import importlib
import sys

import pytest

# ---------------------------------------------------------------------------
# Module imports (skip entire file sections if extensions not built)
# ---------------------------------------------------------------------------

fltk_native = pytest.importorskip(
    "fltk._native",
    reason="fltk._native not built; run 'uv run maturin develop' first",
)

rust_parser_fixture = pytest.importorskip(
    "rust_parser_fixture",
    reason="rust_parser_fixture not built; run 'make build-rust-parser-fixture' first",
)

fegen_rust_cst = pytest.importorskip(
    "fegen_rust_cst",
    reason="fegen_rust_cst not built; run 'make build-fegen-rust-cst' first",
)

phase4_roundtrip_cst = pytest.importorskip(
    "phase4_roundtrip_cst",
    reason="phase4_roundtrip_cst not built; run 'make build-test-user-ext' first",
)

# Top-level imports that are used inside tests (E402: after importorskip guards, F811:
# fegen_rust_cst.cst sub-import does not shadow the importorskip result).
import fegen_rust_cst.cst  # noqa: E402,F811
from fegen_rust_cst.parser import Parser as FegenParser  # noqa: E402

import fltk._native.fegen_cst  # noqa: E402
import fltk._native.poc_cst  # noqa: E402
from fltk._native import SourceText, Span  # noqa: E402
from fltk._native.poc_cst import Identifier as PocIdentifier  # noqa: E402
from fltk._native.poc_cst import Items as PocItems  # noqa: E402

# ===========================================================================
# §4.3 -- Collision fixture headline acceptance test
# ===========================================================================


class TestCollisionFixture:
    """rust_parser_fixture.collision_cst.Parser and .ApplyResult are CST node classes;
    rust_parser_fixture.collision_parser.Parser parses sample input; the two Parser
    attributes are distinct types.
    """

    def test_collision_cst_parser_is_cst_class(self):
        """collision_cst.Parser is a CST node class (not the parser machinery)."""
        cls = rust_parser_fixture.collision_cst.Parser
        assert isinstance(cls, type)
        # It has the CST node class interface (constructible, has .span).
        node = cls()
        assert hasattr(node, "span")

    def test_collision_cst_apply_result_is_cst_class(self):
        """collision_cst.ApplyResult is a CST node class (not the parser machinery)."""
        cls = rust_parser_fixture.collision_cst.ApplyResult
        assert isinstance(cls, type)
        node = cls()
        assert hasattr(node, "span")

    def test_collision_parser_parser_is_parser(self):
        """collision_parser.Parser parses sample input via apply__parse_root."""
        parser_cls = rust_parser_fixture.collision_parser.Parser
        # Single-token input: root = item+, item = parser|apply_result, each = /[a-z_]+/.
        p = parser_cls("foo")
        result = p.apply__parse_root(0)
        assert result is not None
        assert result.pos == len("foo")

    def test_collision_parser_apply_result_wraps_results(self):
        """collision_parser.ApplyResult is the parse result wrapper (has pos + result attrs)."""
        parser_cls = rust_parser_fixture.collision_parser.Parser
        p = parser_cls("foo")
        result = p.apply__parse_root(0)
        assert result is not None
        # ApplyResult must have pos (consumed position) and result (CST node).
        assert hasattr(result, "pos")
        assert hasattr(result, "result")

    def test_collision_cst_and_parser_parser_are_distinct_types(self):
        """collision_cst.Parser and collision_parser.Parser are distinct types -- the headline test."""
        cst_parser_cls = rust_parser_fixture.collision_cst.Parser
        machinery_parser_cls = rust_parser_fixture.collision_parser.Parser
        assert cst_parser_cls is not machinery_parser_cls

    def test_collision_cst_node_kind_has_parser_and_apply_result_variants(self):
        """collision_cst.NodeKind has PARSER and APPLYRESULT variants."""
        node_kind = rust_parser_fixture.collision_cst.NodeKind
        assert hasattr(node_kind, "PARSER")
        assert hasattr(node_kind, "APPLYRESULT")

    def test_collision_fixture_parse_and_access_cst_node(self):
        """Parsing produces collision_cst.Parser nodes reachable via the CST tree."""
        parser_cls = rust_parser_fixture.collision_parser.Parser
        cst_parser_cls = rust_parser_fixture.collision_cst.Parser
        p = parser_cls("foo")
        result = p.apply__parse_root(0)
        assert result is not None
        root_node = result.result
        # root.children should have at least one Item child; dig into it to find a parser node.
        assert len(root_node.children) > 0
        item_child = root_node.children[0][1]
        # item has either a 'p' (parser rule) or 'a' (apply_result rule) child.
        # Input "foo" matches the parser alternative ([a-z_]+ regex), so maybe_p() must return a node.
        parser_child = item_child.maybe_p()
        assert parser_child is not None, "expected maybe_p() to return a Parser node for input 'foo'"
        assert isinstance(parser_child, cst_parser_cls)


# ===========================================================================
# §4.4 -- Import mechanics for fegen_rust_cst
# ===========================================================================


class TestImportMechanics:
    """Various import forms for fegen_rust_cst.cst and .parser must succeed."""

    def test_import_fegen_rust_cst_cst_attribute(self):
        """fegen_rust_cst.cst is accessible as an attribute."""
        assert hasattr(fegen_rust_cst, "cst")

    def test_from_import_parser_works(self):
        """Parser imported from fegen_rust_cst.parser is the same as via attribute."""
        assert FegenParser is fegen_rust_cst.parser.Parser

    def test_importlib_import_cst_submodule(self):
        """importlib.import_module('fegen_rust_cst.cst') succeeds."""
        mod = importlib.import_module("fegen_rust_cst.cst")
        assert mod is not None
        assert hasattr(mod, "NodeKind")

    def test_sys_modules_cst_is_attribute(self):
        """sys.modules['fegen_rust_cst.cst'] is fegen_rust_cst.cst."""
        # importlib.import_module to ensure it's registered (it should be already).
        importlib.import_module("fegen_rust_cst.cst")
        assert "fegen_rust_cst.cst" in sys.modules
        assert sys.modules["fegen_rust_cst.cst"] is fegen_rust_cst.cst

    def test_sys_modules_parser(self):
        """sys.modules['fegen_rust_cst.parser'] is fegen_rust_cst.parser."""
        assert "fegen_rust_cst.parser" in sys.modules
        assert sys.modules["fegen_rust_cst.parser"] is fegen_rust_cst.parser

    def test_cst_has_node_kind(self):
        """fegen_rust_cst.cst.NodeKind is present."""
        assert hasattr(fegen_rust_cst.cst, "NodeKind")
        assert isinstance(fegen_rust_cst.cst.NodeKind, type)

    def test_parser_has_parser_class(self):
        """fegen_rust_cst.parser.Parser is present."""
        assert hasattr(fegen_rust_cst.parser, "Parser")
        assert isinstance(fegen_rust_cst.parser.Parser, type)

    def test_parser_has_apply_result_class(self):
        """fegen_rust_cst.parser.ApplyResult is present."""
        assert hasattr(fegen_rust_cst.parser, "ApplyResult")
        assert isinstance(fegen_rust_cst.parser.ApplyResult, type)


# ===========================================================================
# §4.5 -- Span/SourceText drop from generated modules
# ===========================================================================


class TestSpanDrop:
    """Span and SourceText are absent from generated cst/parser submodules
    and from the top-level fegen_rust_cst module.
    """

    def test_fegen_rust_cst_top_level_no_span(self):
        """fegen_rust_cst top level has no Span attribute."""
        assert not hasattr(fegen_rust_cst, "Span")

    def test_fegen_rust_cst_top_level_no_source_text(self):
        """fegen_rust_cst top level has no SourceText attribute."""
        assert not hasattr(fegen_rust_cst, "SourceText")

    def test_fegen_rust_cst_cst_no_span(self):
        """fegen_rust_cst.cst has no Span attribute."""
        assert not hasattr(fegen_rust_cst.cst, "Span")

    def test_fegen_rust_cst_cst_no_source_text(self):
        """fegen_rust_cst.cst has no SourceText attribute."""
        assert not hasattr(fegen_rust_cst.cst, "SourceText")

    def test_fegen_rust_cst_parser_no_span(self):
        """fegen_rust_cst.parser has no Span attribute."""
        assert not hasattr(fegen_rust_cst.parser, "Span")

    def test_fegen_rust_cst_parser_no_source_text(self):
        """fegen_rust_cst.parser has no SourceText attribute."""
        assert not hasattr(fegen_rust_cst.parser, "SourceText")

    def test_rust_parser_fixture_top_level_no_span(self):
        """rust_parser_fixture top level has no Span attribute (§2.4 scoped drop)."""
        assert not hasattr(rust_parser_fixture, "Span")

    def test_rust_parser_fixture_top_level_no_source_text(self):
        """rust_parser_fixture top level has no SourceText attribute."""
        assert not hasattr(rust_parser_fixture, "SourceText")

    def test_phase4_roundtrip_cst_top_level_has_span(self):
        """phase4_roundtrip_cst (rust_cst_fixture) keeps Span at top level (§2.4 exception)."""
        assert hasattr(phase4_roundtrip_cst, "Span")
        assert isinstance(phase4_roundtrip_cst.Span, type)

    def test_phase4_roundtrip_cst_top_level_has_source_text(self):
        """phase4_roundtrip_cst keeps SourceText at top level (§2.4 exception)."""
        assert hasattr(phase4_roundtrip_cst, "SourceText")
        assert isinstance(phase4_roundtrip_cst.SourceText, type)

    def test_fltk_native_has_span(self):
        """fltk._native still has Span (canonical home)."""
        assert isinstance(Span, type)

    def test_fltk_native_has_source_text(self):
        """fltk._native still has SourceText (canonical home)."""
        assert isinstance(SourceText, type)


# ===========================================================================
# §4.6 -- fltk._native.poc_cst
# ===========================================================================


class TestPocCstSubmodule:
    """PoC classes are in fltk._native.poc_cst; absent from fltk._native top level."""

    def test_poc_cst_identifier_reachable(self):
        """fltk._native.poc_cst.Identifier is a type."""
        assert isinstance(PocIdentifier, type)

    def test_poc_cst_items_reachable(self):
        """fltk._native.poc_cst.Items is a type."""
        assert isinstance(PocItems, type)

    def test_poc_cst_absent_from_native_top_level(self):
        """fltk._native top level does not expose Identifier (moved to poc_cst)."""
        assert not hasattr(fltk_native, "Identifier")

    def test_poc_cst_items_absent_from_native_top_level(self):
        """fltk._native top level does not expose Items (moved to poc_cst)."""
        assert not hasattr(fltk_native, "Items")

    def test_native_still_has_span(self):
        """fltk._native still exposes Span at top level (canonical home)."""
        assert hasattr(fltk_native, "Span")

    def test_native_still_has_source_text(self):
        """fltk._native still exposes SourceText at top level."""
        assert hasattr(fltk_native, "SourceText")

    def test_native_still_has_unknown_span(self):
        """fltk._native still exposes UnknownSpan at top level."""
        assert hasattr(fltk_native, "UnknownSpan")

    def test_fegen_cst_still_accessible(self):
        """fltk._native.fegen_cst is still accessible (unchanged)."""
        assert hasattr(fltk_native, "fegen_cst")
        assert fltk._native.fegen_cst is fltk_native.fegen_cst

    def test_sys_modules_poc_cst(self):
        """sys.modules['fltk._native.poc_cst'] is fltk._native.poc_cst."""
        assert "fltk._native.poc_cst" in sys.modules
        assert sys.modules["fltk._native.poc_cst"] is fltk._native.poc_cst

    def test_sys_modules_fegen_cst(self):
        """sys.modules['fltk._native.fegen_cst'] is fltk._native.fegen_cst."""
        assert "fltk._native.fegen_cst" in sys.modules
        assert sys.modules["fltk._native.fegen_cst"] is fltk._native.fegen_cst

    def test_poc_cst_has_node_kind(self):
        """fltk._native.poc_cst.NodeKind is present."""
        assert hasattr(fltk._native.poc_cst, "NodeKind")
