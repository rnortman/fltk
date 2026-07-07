"""Shared pytest helpers for the ``fltk.lsp`` test suite."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fltk import plumbing
from fltk.lsp.engine import AnalysisEngine
from fltk.lsp.lsp_config import load_lsp_config

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fltk.fegen import gsm
    from fltk.lsp.classify import Token

# A small shared target grammar: `hello` is a word literal (default -> keyword), `word` an
# identifier regex (default -> variable), `!` a word-free non-punctuation literal (default ->
# operator). Used by the engine and CLI tests, which need the same simple language.
HELLO_GRAMMAR = r"""
top := , greeting* ;
greeting := kw:"hello" , name:word , punct:"!" , ;
word := /[a-z]+/ ;
_trivia := ( line_comment | line_comment? : )+ ;
line_comment := prefix:"//" . content:/[^\n]*/ . newline:"\n" ;
"""

# A spec that repaints the `name` child of `greeting` from the default `variable` to `type`.
HELLO_LSP = "rule greeting {\n  scope name: type;\n}\n"


def build_hello_engine(config_text: str = "", *, start_rule: str | None = "top") -> tuple[AnalysisEngine, gsm.Grammar]:
    """Construct an ``AnalysisEngine`` over ``HELLO_GRAMMAR`` with the given ``.fltklsp`` config text.

    Returns the engine and the parsed grammar (the pre-transform object the engine stores as
    ``source_grammar``). Shared by the engine tests, which need the same construction sequence.
    """
    grammar = plumbing.parse_grammar(HELLO_GRAMMAR)
    resolved = load_lsp_config(config_text, grammar)
    return AnalysisEngine(grammar, resolved, start_rule=start_rule), grammar


def token_for(tokens: Sequence[Token], text: str, substr: str) -> Token:
    """Return the single token whose span exactly covers ``substr`` in ``text``.

    ``substr`` must occur in ``text``; the token stream must contain exactly one token whose
    ``[start, end)`` matches that occurrence's bounds.
    """
    start = text.index(substr)
    end = start + len(substr)
    matches = [t for t in tokens if t.start == start and t.end == end]
    assert len(matches) == 1, f"expected exactly one token spanning {substr!r}, got {matches}"
    return matches[0]


def token_type_at(tokens: Sequence[Token], text: str, substr: str) -> str:
    """Return the ``token_type`` of the single token exactly covering ``substr`` in ``text``."""
    return token_for(tokens, text, substr).token_type
