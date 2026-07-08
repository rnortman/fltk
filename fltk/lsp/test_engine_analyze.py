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

# A single sequence with no top-level repetition: an error yields a hard failure (the start rule
# returns no result), so ``analyze`` produces the *failed* outcome with no prefix.
_HARD_GRAMMAR = 'pair := a:"a" , b:"b" ;'


def _engine(config_text: str = "") -> tuple[AnalysisEngine, object]:
    return build_hello_engine(config_text, start_rule="top")


def _hard_engine() -> AnalysisEngine:
    grammar = plumbing.parse_grammar(_HARD_GRAMMAR)
    return AnalysisEngine(grammar, load_lsp_config("", grammar), start_rule="pair")


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
    engine = _hard_engine()
    text = "a x"  # `b` expects "b"; no top-level repetition, so this is a hard failure.
    analysis = engine.analyze(text)
    assert analysis.tree is None
    assert analysis.tokens is None
    assert analysis.prefix_end is None
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
    engine = _hard_engine()
    analysis = engine.analyze("a x")  # hard failure: no prefix, so no symbol table
    assert analysis.error is not None
    assert analysis.symbols is None
    assert analysis.prefix_end is None


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


def test_analyze_classification_recursion_error_on_complete_parse_degrades(monkeypatch) -> None:
    # The outer try guards classify.classify on the *complete* (non-prefix) path too: a RecursionError
    # there still degrades to the failed outcome with the nesting-depth message rather than escaping
    # analyze(). Sibling to the extraction test, but hitting the classify call on a fully-parsed text.
    engine = _ref_engine()

    def _raise(*_args, **_kwargs):
        raise RecursionError

    monkeypatch.setattr(engine_module.classify, "classify", _raise)
    analysis = engine.analyze("let x ;\nuse x ;\n")  # parses cleanly, so classify is reached
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


def test_start_rule_property_round_trips() -> None:
    engine, _ = _engine()  # constructed with start_rule="top"
    assert engine.start_rule == "top"
    grammar = plumbing.parse_grammar(_REF_GRAMMAR)
    default = AnalysisEngine(grammar, load_lsp_config("", grammar))
    assert default.start_rule is None


def test_analyze_complete_has_no_prefix_end() -> None:
    engine, _ = _engine(_LSP)
    analysis = engine.analyze("hello world !")
    assert analysis.error is None
    assert analysis.prefix_end is None


def test_analyze_partial_outcome_shape() -> None:
    engine = _ref_engine()
    # First stmt parses; the second (`let ;`, no name) breaks the repetition.
    text = "let a ;\nlet ;\n"
    analysis = engine.analyze(text)
    assert analysis.error is not None
    assert analysis.tree is not None
    assert analysis.tokens is not None
    assert analysis.symbols is not None
    assert analysis.prefix_end is not None
    # The prefix ends before the broken region, and the error is at/after the boundary.
    assert analysis.prefix_end <= (analysis.error.offset or 0)
    assert analysis.prefix_end < len(text)
    # Every fresh token is confined to the prefix.
    assert all(token.end <= analysis.prefix_end for token in analysis.tokens)


def test_analyze_partial_symbols_are_prefix_only() -> None:
    engine = _ref_engine()
    # `a` is defined in the prefix; the repetition breaks on `let ;`, so `b` past it is never seen.
    analysis = engine.analyze("let a ;\nlet ;\nlet b ;\n")
    assert analysis.error is not None
    assert analysis.symbols is not None
    names = [s.name for s in analysis.symbols.symbols]
    assert "a" in names
    assert "b" not in names


def test_analyze_partial_ref_to_def_past_error_is_unresolved() -> None:
    engine = _ref_engine()
    # The ref `use x` is in the prefix; the only `let x` is past the error, so it stays unresolved
    # (paints default) rather than crashing.
    analysis = engine.analyze("use x ;\nQ\nlet x ;\n")
    assert analysis.error is not None
    assert analysis.symbols is not None
    assert analysis.tokens is not None
    (reference,) = analysis.symbols.references
    assert reference.symbol is None


def test_highlight_on_partial_reports_none_tokens() -> None:
    engine = _ref_engine()
    analysis = engine.analyze("let a ;\nlet ;\n")
    assert analysis.error is not None
    assert analysis.tokens is not None  # analyze exposes the prefix tokens...
    result = engine.highlight("let a ;\nlet ;\n")
    assert result.tokens is None  # ...but highlight's one-of contract still reports failure only.
    assert result.error == analysis.error.message


def test_analyze_prefix_classification_recursion_degrades_to_parse_error(monkeypatch) -> None:
    # A RecursionError raised while classifying the prefix (parse itself succeeded to a prefix)
    # degrades to the failed outcome carrying the parse error, not the nesting-depth message.
    engine = _ref_engine()

    def _raise(*_args, **_kwargs):
        raise RecursionError

    monkeypatch.setattr(engine_module.classify, "classify", _raise)
    analysis = engine.analyze("let a ;\nlet ;\n")
    assert analysis.tree is None
    assert analysis.tokens is None
    assert analysis.error is not None
    # The parse error has a source offset; the nesting-depth degrade would have offset None.
    assert analysis.error.offset is not None
    assert "nesting depth" not in analysis.error.message
