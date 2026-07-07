"""Tests for the GSM anchor-matching index (`build_grammar_index`)."""

from fltk.lsp import lsp_config
from fltk.plumbing import parse_grammar

# `top` mixes an explicit label (`a:`), an unlabeled rule invocation (implicit label
# `word` == invoked rule name), an unlabeled literal, and a labeled invocation
# (`k:word`, whose label differs from its invoked rule name).
_GRAMMAR = """
top := a:word . word . ":" . k:word ;
word := name:/[a-z]+/ ;
"""


def _index(text: str) -> lsp_config.GrammarIndex:
    return lsp_config.build_grammar_index(parse_grammar(text))


def test_explicit_and_implicit_labels_collected() -> None:
    idx = _index(_GRAMMAR)
    top = idx.rules["top"]
    # Explicit labels `a`, `k`; the implicit label `word` from the unlabeled invocation.
    assert top.labels == frozenset({"a", "word", "k"})


def test_literals_collected() -> None:
    idx = _index(_GRAMMAR)
    assert idx.rules["top"].literals == frozenset({":"})
    assert idx.rules["word"].literals == frozenset()


def test_invoked_rules_distinct_from_labels() -> None:
    idx = _index(_GRAMMAR)
    top = idx.rules["top"]
    # Every `word` invocation contributes the invoked rule name, regardless of its label.
    assert top.invoked_rules == frozenset({"word"})


def test_grammar_wide_unions() -> None:
    idx = _index(_GRAMMAR)
    assert idx.rule_names == frozenset({"top", "word"})
    assert idx.all_labels == frozenset({"a", "word", "k", "name"})
    assert idx.all_literals == frozenset({":"})


def test_subexpression_recursion() -> None:
    # Labels, literals, and invocations nested in a sub-expression are all collected.
    idx = _index(
        """
        top := a:word . ( ";" . b:word . tail )? ;
        word := name:/[a-z]+/ ;
        tail := mark:word ;
        """
    )
    top = idx.rules["top"]
    assert top.labels == frozenset({"a", "b", "tail"})
    assert top.literals == frozenset({";"})
    assert top.invoked_rules == frozenset({"word", "tail"})


def test_alternatives_merged() -> None:
    # Both alternatives of a rule contribute to its index.
    idx = _index(
        """
        top := a:word | "x" . b:word ;
        word := name:/[a-z]+/ ;
        """
    )
    top = idx.rules["top"]
    assert top.labels == frozenset({"a", "b"})
    assert top.literals == frozenset({"x"})
