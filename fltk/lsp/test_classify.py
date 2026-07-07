"""Tests for the default classification layer (`classify.default_tokens`)."""

from __future__ import annotations

import itertools

from fltk.lsp.analysis import prepare_analysis_grammar
from fltk.lsp.classify import Token, default_tokens
from fltk.lsp.conftest import token_for as _token_for
from fltk.plumbing import generate_parser, parse_grammar, parse_text

# One rule exercises every default-table row. `k`/`p`/`o` are labeled literals (word / punctuation
# / operator); `s`/`n`/`v`/`x` are labeled regexes (quote / digit / identifier / other text); the
# trailing unlabeled `";"` is suppressed by default and only surfaces in the analysis grammar,
# exercising the unlabeled literal-first provenance path. A real `_trivia`/`line_comment` pair lets
# the trivia (comment, non-descent, whitespace-only) rows be tested.
_GRAMMAR = r"""
top := , row* ;
row := k:"let" , p:"(" , o:"=>" , s:/"[a-z]*"/ , n:/[0-9]+/ , v:/[a-z_]+/ , x:/@[a-z]+/ , ";" , ;
_trivia := ( line_comment | line_comment? : )+ ;
line_comment := prefix:"//" . content:/[^\n]*/ . newline:"\n" ;
"""


def _tokens(text: str) -> list[Token]:
    grammar = parse_grammar(_GRAMMAR)
    parser = generate_parser(prepare_analysis_grammar(grammar))
    result = parse_text(parser, text, "top")
    assert result.success, result.error_message
    return default_tokens(result.cst, parser.grammar, text)


def test_default_table_rows():
    text = 'let ( => "ab" 12 foo @bar ;'
    tokens = _tokens(text)

    assert _token_for(tokens, text, "let").token_type == "keyword"
    assert _token_for(tokens, text, "(").token_type == "punctuation"
    assert _token_for(tokens, text, "=>").token_type == "operator"
    assert _token_for(tokens, text, '"ab"').token_type == "string"
    assert _token_for(tokens, text, "12").token_type == "number"
    assert _token_for(tokens, text, "foo").token_type == "variable"
    assert _token_for(tokens, text, "@bar").token_type == "text"


def test_suppressed_literal_classifies_via_unlabeled_provenance():
    # The trailing `;` is suppressed by default and only present in the analysis tree; it has no
    # label, so it resolves literal-first against the rule's literal union -> punctuation.
    text = 'let ( => "ab" 12 foo @bar ;'
    tokens = _tokens(text)
    assert _token_for(tokens, text, ";").token_type == "punctuation"


def test_contextual_keyword_boundary():
    # The `v` regex position holds the spelling "let" -- textually identical to the `k` literal
    # keyword, but classified by provenance: literal -> keyword, regex -> variable.
    text = 'let ( => "ab" 12 let @bar ;'
    tokens = _tokens(text)
    kw = _token_for(tokens, text, "let")  # first occurrence: the k literal
    assert kw.token_type == "keyword"
    variable = [t for t in tokens if text[t.start : t.end] == "let" and t.token_type == "variable"]
    assert len(variable) == 1, tokens
    assert variable[0].start > kw.start


def test_lookahead_regex_span_classifies_by_positional_provenance():
    # `v` is a regex whose match depends on a following `;` via lookahead. The parser consumes only
    # `foo`, so `fullmatch("foo")` on the isolated slice would fail; provenance must instead be
    # tested positionally (match at the span start, ending at the span end) as the parser did.
    grammar = parse_grammar(r"""
top := , item* ;
item := v:/[a-z]+(?=;)/ . ";" , ;
""")
    parser = generate_parser(prepare_analysis_grammar(grammar))
    text = "foo;"
    result = parse_text(parser, text, "top")
    assert result.success, result.error_message
    tokens = default_tokens(result.cst, parser.grammar, text)
    assert _token_for(tokens, text, "foo").token_type == "variable"


def test_whitespace_only_trivia_emits_nothing():
    # The spaces between tokens are whitespace-only trivia; no token should cover them.
    text = 'let ( => "ab" 12 foo @bar ;'
    tokens = _tokens(text)
    comment_tokens = [t for t in tokens if t.token_type == "comment"]
    assert comment_tokens == []
    # No token covers a pure-space position.
    for i, ch in enumerate(text):
        if ch == " ":
            assert not any(t.start <= i < t.end for t in tokens)


def test_structured_comment_is_single_comment_and_not_descended():
    text = '//hi there\nlet ( => "ab" 12 foo @bar ;'
    tokens = _tokens(text)
    comment_tokens = [t for t in tokens if t.token_type == "comment"]
    assert len(comment_tokens) == 1
    comment = comment_tokens[0]
    # The comment interval spans the whole trivia node, including the trailing newline.
    assert comment.start == 0
    assert text[comment.start : comment.end] == "//hi there\n"
    # Non-descent: the `//` prefix inside the comment never repaints as operator/punctuation.
    inside = [t for t in tokens if t.start >= comment.start and t.end <= comment.end and t is not comment]
    assert inside == []


def test_token_stream_invariants():
    text = '//c\nlet ( => "ab" 12 foo @bar ;\nlet ( => "z" 7 bar @q ;'
    tokens = _tokens(text)

    # Sorted by start.
    assert tokens == sorted(tokens, key=lambda t: (t.start, t.end))
    # Non-overlapping.
    for prev, nxt in itertools.pairwise(tokens):
        assert prev.end <= nxt.start
    # In-bounds.
    for t in tokens:
        assert 0 <= t.start < t.end <= len(text)
    # No two adjacent tokens of the same type left unmerged.
    for prev, nxt in itertools.pairwise(tokens):
        assert not (prev.end == nxt.start and prev.token_type == nxt.token_type)
