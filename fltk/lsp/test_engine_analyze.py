"""Tests for ``AnalysisEngine.analyze`` and the two read-only properties.

``highlight`` is pinned to remain byte-for-byte identical to its original output (it now delegates
to ``analyze``); the richer ``analyze`` result carries the CST and a structured error.
"""

from __future__ import annotations

from fltk import plumbing
from fltk.lsp import engine as engine_module
from fltk.lsp.conftest import HELLO_LSP as _LSP
from fltk.lsp.conftest import build_hello_engine
from fltk.lsp.engine import AnalysisEngine
from fltk.lsp.lsp_config import load_lsp_config

# A def/ref language so `analyze` produces a non-empty symbol table.
_REF_GRAMMAR = r"""
program := , stmt* ;
stmt := decl | use ;
decl := kw:"let" , name:word , semi:";" , ;
use := kw:"use" , target:word , semi:";" , ;
word := /[a-z]+/ ;
_trivia := ( line_comment | line_comment? : )+ ;
line_comment := prefix:"//" . content:/[^\n]*/ . newline:"\n" ;
"""
_REF_CONFIG = "rule decl {\n  def name: variable;\n}\nrule use {\n  ref target: variable;\n}\n"


def _engine(config_text: str = "") -> tuple[AnalysisEngine, object]:
    return build_hello_engine(config_text, start_rule="top")


def test_analyze_success_carries_tree_and_tokens() -> None:
    engine, _ = _engine(_LSP)
    text = "hello world !"
    analysis = engine.analyze(text)
    assert analysis.error is None
    assert analysis.tokens is not None
    assert analysis.tree is not None
    # The CST is a structural node with the usual walk surface.
    assert hasattr(analysis.tree, "children")


def test_analyze_failure_has_structured_error_with_offset() -> None:
    engine, _ = _engine()
    text = "hello world"  # missing the required "!"
    analysis = engine.analyze(text)
    assert analysis.tree is None
    assert analysis.tokens is None
    assert analysis.error is not None
    assert analysis.error.message != ""
    assert analysis.error.offset is not None
    assert 0 <= analysis.error.offset <= len(text)


def test_analyze_recursion_error_reports_offset_none(monkeypatch) -> None:
    engine, _ = _engine()

    def _raise(*_args, **_kwargs):
        raise RecursionError

    monkeypatch.setattr(engine_module.plumbing, "parse_text", _raise)
    analysis = engine.analyze("anything")
    assert analysis.tree is None
    assert analysis.tokens is None
    assert analysis.error is not None
    assert analysis.error.offset is None
    assert "nesting depth" in analysis.error.message


def test_highlight_delegates_to_analyze_on_success() -> None:
    engine, _ = _engine(_LSP)
    text = "hello world !"
    analysis = engine.analyze(text)
    result = engine.highlight(text)
    assert result.error is None
    assert result.tokens == analysis.tokens


def test_highlight_delegates_to_analyze_on_failure() -> None:
    engine, _ = _engine()
    text = "hello world"
    analysis = engine.analyze(text)
    result = engine.highlight(text)
    assert result.tokens is None
    assert analysis.error is not None
    assert result.error == analysis.error.message


def _ref_engine() -> AnalysisEngine:
    grammar = plumbing.parse_grammar(_REF_GRAMMAR)
    return AnalysisEngine(grammar, load_lsp_config(_REF_CONFIG, grammar), start_rule="program")


def test_analyze_carries_populated_symbol_table_on_success() -> None:
    engine = _ref_engine()
    analysis = engine.analyze("let x ;\nuse x ;\n")
    assert analysis.error is None
    assert analysis.symbols is not None
    assert [s.name for s in analysis.symbols.symbols] == ["x"]
    # The reference resolves to the declaration.
    (reference,) = analysis.symbols.references
    assert reference.symbol is not None
    assert reference.symbol.name == "x"


def test_analyze_empty_config_has_empty_symbol_table() -> None:
    engine, _ = _engine()  # HELLO grammar, empty config -> no defs/refs
    analysis = engine.analyze("hello world !")
    assert analysis.symbols is not None
    assert analysis.symbols.symbols == ()
    assert analysis.symbols.references == ()


def test_analyze_failure_has_no_symbol_table() -> None:
    engine = _ref_engine()
    analysis = engine.analyze("let x")  # missing the `;`
    assert analysis.error is not None
    assert analysis.symbols is None


def test_analyze_extraction_recursion_error_reports_offset_none(monkeypatch) -> None:
    # A RecursionError raised by symbol extraction (not just parsing) is caught by the same guard
    # and degrades to the structured offset-None failure with tree/tokens/symbols all None.
    engine = _ref_engine()

    def _raise(*_args, **_kwargs):
        raise RecursionError

    monkeypatch.setattr(engine_module.symbols, "extract", _raise)
    analysis = engine.analyze("let x ;\nuse x ;\n")  # parses cleanly, so extraction is reached
    assert analysis.tree is None
    assert analysis.tokens is None
    assert analysis.symbols is None
    assert analysis.error is not None
    assert analysis.error.offset is None
    assert "nesting depth" in analysis.error.message


def test_source_grammar_is_the_original_pre_transform_grammar() -> None:
    engine, grammar = _engine()
    # The analysis transform builds a new grammar internally; source_grammar returns the
    # exact object passed to __init__, never that variant.
    assert engine.source_grammar is grammar


def test_trivia_kind_names_covers_the_comment_rule() -> None:
    engine, _ = _engine()
    names = engine.trivia_kind_names
    assert isinstance(names, frozenset)
    # `line_comment` is reachable from the grammar's `_trivia` rule, so its CST kind name
    # (uppercased UpperCamel) is a trivia kind.
    assert "LINECOMMENT" in names
