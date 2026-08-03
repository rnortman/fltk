"""Tests for `AnalysisEngine` -- the grammar+specs -> tokens seam."""

from __future__ import annotations

import pytest

from fltk import plumbing
from fltk.fegen import gsm
from fltk.lsp.conftest import HELLO_GRAMMAR as _GRAMMAR
from fltk.lsp.conftest import HELLO_LSP as _LSP
from fltk.lsp.conftest import build_hello_engine
from fltk.lsp.conftest import token_type_at as _type_of
from fltk.lsp.engine import AnalysisEngine
from fltk.lsp.lsp_config import load_lsp_config


def _engine(config_text: str = "", *, start_rule: str | None = "top") -> AnalysisEngine:
    return build_hello_engine(config_text, start_rule=start_rule)[0]


def test_highlight_defaults_only() -> None:
    engine = _engine()
    text = "hello world !"
    result = engine.highlight(text)
    assert result.error is None
    assert result.tokens is not None
    assert _type_of(result.tokens, text, "hello") == "keyword"
    assert _type_of(result.tokens, text, "world") == "variable"


def test_highlight_applies_explicit_config() -> None:
    engine = _engine(_LSP)
    text = "hello world !"
    result = engine.highlight(text)
    assert result.error is None
    assert result.tokens is not None
    # The explicit scope repaints the `name` child from the default `variable` to `type`.
    assert _type_of(result.tokens, text, "world") == "type"


def test_highlight_parse_failure_reports_error() -> None:
    engine = _engine()
    result = engine.highlight("hello world")  # missing the required `!`
    assert result.tokens is None
    assert result.error is not None
    assert result.error != ""


def test_from_paths_with_lsp_file(tmp_path) -> None:
    grammar_path = tmp_path / "lang.fltkg"
    grammar_path.write_text(_GRAMMAR)
    lsp_path = tmp_path / "lang.fltklsp"
    lsp_path.write_text(_LSP)

    engine = AnalysisEngine.from_paths(grammar_path, lsp_path, start_rule="top")
    text = "hello world !"
    result = engine.highlight(text)
    assert result.error is None
    assert result.tokens is not None
    assert _type_of(result.tokens, text, "world") == "type"


def test_from_paths_without_lsp_uses_defaults(tmp_path) -> None:
    grammar_path = tmp_path / "lang.fltkg"
    grammar_path.write_text(_GRAMMAR)

    engine = AnalysisEngine.from_paths(grammar_path, start_rule="top")
    text = "hello world !"
    result = engine.highlight(text)
    assert result.error is None
    assert result.tokens is not None
    # No config -> the default `variable` paint stands.
    assert _type_of(result.tokens, text, "world") == "variable"


def test_start_rule_none_uses_first_rule() -> None:
    # start_rule=None -> plumbing.parse_text falls back to the grammar's first rule (`top`).
    engine = _engine(start_rule=None)
    text = "hello world !"
    result = engine.highlight(text)
    assert result.error is None
    assert result.tokens is not None
    assert _type_of(result.tokens, text, "hello") == "keyword"


def test_highlight_reused_across_calls() -> None:
    # The engine's raison d'etre is reuse: one construction, many `highlight` calls. A prior
    # parse failure must not corrupt a later success, nor vice versa.
    engine = _engine(_LSP)

    ok = engine.highlight("hello world !")
    assert ok.error is None
    assert ok.tokens is not None
    assert _type_of(ok.tokens, "hello world !", "world") == "type"

    bad = engine.highlight("hello world")  # missing the required `!`
    assert bad.tokens is None
    assert bad.error

    ok2 = engine.highlight("hello there !")
    assert ok2.error is None
    assert ok2.tokens is not None
    assert _type_of(ok2.tokens, "hello there !", "there") == "type"


def _grammar_with_unexpanded_inline() -> gsm.Grammar:
    """A grammar retaining an INLINE item, as only a programmatic caller can produce.

    `plumbing.parse_grammar` expands `!` away, so the engine's INLINE rejection is
    reachable only by bypassing that boundary.
    """
    word = gsm.Rule(
        name="word",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="name",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[a-z]+"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    tail = gsm.Rule(
        name="tail",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="mark",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("word"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    top = gsm.Rule(
        name="top",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INLINE,
                        term=gsm.Identifier("tail"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    rules = [top, tail, word]
    return gsm.Grammar(rules=rules, identifiers={rule.name: rule for rule in rules})


def test_inline_grammar_rejected_at_construction() -> None:
    grammar = _grammar_with_unexpanded_inline()
    resolved = load_lsp_config("", grammar)
    with pytest.raises(ValueError, match="inline"):
        AnalysisEngine(grammar, resolved, start_rule="top")


def test_inline_grammar_accepted_after_expansion() -> None:
    """An inline-using grammar reaches the engine already expanded and highlights normally."""
    grammar = plumbing.parse_grammar(r"""
top := a:num . !tail ;
tail := op:"+" . mark:num ;
num := name:/[0-9]+/ ;
""")
    resolved = load_lsp_config("", grammar)
    engine = AnalysisEngine(grammar, resolved, start_rule="top")

    text = "1+2"
    result = engine.highlight(text)
    assert result.error is None
    assert result.tokens is not None
    # The spliced literal is a child of the `top` node and is classified against `top`'s
    # terminal table, which carries it only because expansion moved `tail`'s items there.
    assert _type_of(result.tokens, text, "+") == "operator"
    # The spliced `mark:num` is tokenized exactly like the caller's own `a:num`.
    assert _type_of(result.tokens, text, "2") == _type_of(result.tokens, text, "1") == "number"
