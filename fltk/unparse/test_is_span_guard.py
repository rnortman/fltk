"""Tests for the dual-backend span guard in generated unparsers (design §2.6a).

The generated unparser is a backend-agnostic CST consumer: it must recognize a
span child structurally — ``terminalsrc.Span`` from a Python parser or
``fltk._native.Span`` from a Rust CST — via ``fltk.unparse.pyrt.is_span`` rather
than through ``span.py``'s process-wide backend probe.
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

import pytest

from fltk.fegen.pyrt import terminalsrc
from fltk.plumbing import generate_parser, generate_unparser_source, parse_grammar_file
from fltk.unparse import pyrt

TOY_GRAMMAR = Path(__file__).parent / "toy.fltkg"


class TestIsSpanHelper:
    """Unit coverage for fltk.unparse.pyrt.is_span (dual-backend, probe-free)."""

    def test_accepts_terminalsrc_span(self):
        span = terminalsrc.Span.with_source(0, 2, "ab")
        assert pyrt.is_span(span) is True

    def test_accepts_native_span(self):
        try:
            native = importlib.import_module("fltk._native")
        except ImportError:
            pytest.skip("fltk._native not built in this environment")
        assert pyrt.is_span(native.Span(0, 2)) is True

    def test_rejects_non_span(self):
        assert pyrt.is_span(object()) is False
        assert pyrt.is_span("not a span") is False
        assert pyrt.is_span(None) is False

    def test_native_branch_is_lazy_when_native_absent(self, monkeypatch):
        # Simulate a pure-Python install: fltk._native not loaded. The native
        # branch must resolve to False via sys.modules.get without importing.
        monkeypatch.setitem(sys.modules, "fltk._native", None)
        assert pyrt.is_span(terminalsrc.Span.with_source(0, 1, "a")) is True
        assert pyrt.is_span(object()) is False


def _generate_unparser_source(grammar_path: Path) -> str:
    """Generate the in-memory unparser module source for a grammar file.

    Wraps plumbing.generate_unparser_source for a grammar file path so the emitted
    span guards can be inspected.
    """
    grammar = parse_grammar_file(grammar_path)
    parser_result = generate_parser(grammar, capture_trivia=True)
    try:
        return generate_unparser_source(parser_result.grammar, parser_result.cst_module_name)
    finally:
        sys.modules.pop(parser_result.cst_module_name, None)


class TestGeneratedGuard:
    """The generated unparser emits the dual-backend helper, not a probe guard."""

    def test_uses_is_span_helper(self):
        src = _generate_unparser_source(TOY_GRAMMAR)
        assert "fltk.unparse.pyrt.is_span(" in src

    def test_no_probe_bound_span_isinstance(self):
        src = _generate_unparser_source(TOY_GRAMMAR)
        # No remaining isinstance guard resolves through the span.py probe
        # (the only fltk.fegen.pyrt.span.Span reference left is the lazy
        # annotation surface, which is not an isinstance call).
        isinstance_lines = [line for line in src.splitlines() if "isinstance(" in line]
        offending = [line for line in isinstance_lines if "fltk.fegen.pyrt.span.Span" in line]
        assert not offending, f"probe-bound span isinstance guard still present: {offending}"


class TestLazySpanAnnotations:
    """The generated unparser's span annotations are lazy; span_protocol is TYPE_CHECKING-only (D3.6).

    The annotation surface is the agnostic ``fltk.fegen.pyrt.span_protocol.SpanProtocol`` — the
    unparser names neither ``fltk._native`` nor the ``fltk.fegen.pyrt.span`` selector.
    """

    def _module(self) -> ast.Module:
        return ast.parse(_generate_unparser_source(TOY_GRAMMAR))

    def test_future_annotations_is_first_statement(self):
        mod = self._module()
        first = mod.body[0]
        assert isinstance(first, ast.ImportFrom)
        assert first.module == "__future__"
        assert [alias.name for alias in first.names] == ["annotations"]

    def test_no_module_top_level_span_protocol_import(self):
        mod = self._module()
        top_level_imports = [stmt for stmt in mod.body if isinstance(stmt, ast.Import)]
        offending = [
            alias.name
            for stmt in top_level_imports
            for alias in stmt.names
            if alias.name == "fltk.fegen.pyrt.span_protocol"
        ]
        assert not offending, f"runtime top-level span_protocol import present: {offending}"

    def test_no_span_selector_import_anywhere(self):
        src = _generate_unparser_source(TOY_GRAMMAR)
        # The selector module must appear nowhere — not at top level, not under TYPE_CHECKING.
        # `span_protocol` shares the `fltk.fegen.pyrt.span` prefix, so match the exact import line.
        offending = [line for line in src.splitlines() if line.strip() == "import fltk.fegen.pyrt.span"]
        assert not offending, f"span selector import present: {offending}"

    def test_span_protocol_import_under_type_checking(self):
        mod = self._module()
        guarded: list[str] = []
        for stmt in mod.body:
            if (
                isinstance(stmt, ast.If)
                and isinstance(stmt.test, ast.Attribute)
                and isinstance(stmt.test.value, ast.Name)
                and stmt.test.value.id == "typing"
                and stmt.test.attr == "TYPE_CHECKING"
            ):
                for inner in stmt.body:
                    if isinstance(inner, ast.Import):
                        guarded.extend(alias.name for alias in inner.names)
        assert "fltk.fegen.pyrt.span_protocol" in guarded, (
            "span_protocol import not found under `if typing.TYPE_CHECKING:`"
        )
