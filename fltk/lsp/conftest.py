"""Shared pytest helpers for the ``fltk.lsp`` test suite."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

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
