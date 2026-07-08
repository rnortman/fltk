"""Dogfood: the committed `fltklsp.fltklsp` spec describes the `.fltklsp` language itself.

Loads that spec against its own grammar (`fltklsp.fltkg`) and highlights a sample `.fltklsp`
file, proving the addressing surface works end-to-end on a real, non-trivial spec.
"""

from __future__ import annotations

import pathlib

from fltk import plumbing
from fltk.lsp import lsp_config
from fltk.lsp.conftest import token_type_at as _token_type
from fltk.lsp.engine import AnalysisEngine
from fltk.lsp.lsp_config import load_lsp_config

_HERE = pathlib.Path(__file__).parent
_GRAMMAR_PATH = _HERE / "fltklsp.fltkg"
_SPEC_PATH = _HERE / "fltklsp.fltklsp"

# The committed `fltklsp.fltklsp` carries only `scope` statements; a good def/ref/namespace
# vocabulary for the `.fltklsp` language is its own design question, so semantics dogfooding uses
# this test-local spec instead: `rule` blocks define their rule name into a namespace scope, and an
# anchor identifier is a reference resolving to that name.
_SEMANTIC_SPEC = """
rule rule_config {
  def rule_name: type;
  namespace;
}
rule anchor {
  ref name: type;
}
"""


def test_dogfood_spec_loads_against_its_own_grammar() -> None:
    grammar = plumbing.parse_grammar_file(_GRAMMAR_PATH)
    resolved = load_lsp_config(_SPEC_PATH.read_text(), grammar)
    # The spec addresses these grammar rules with rule blocks.
    assert {"rule_config", "scope_stmt", "qualifier", "dotted_name", "literal"} <= set(resolved.child_matchers)
    # The two global literal anchors resolve to `;`/`:` matchers, each painting `punctuation`.
    assert {m.match for m in resolved.global_child_matchers} == {
        lsp_config.ByLiteralText(";"),
        lsp_config.ByLiteralText(":"),
    }
    assert all(m.paint.token == "punctuation" for m in resolved.global_child_matchers)


def test_dogfood_spec_highlights_a_sample() -> None:
    engine = AnalysisEngine.from_paths(_GRAMMAR_PATH, _SPEC_PATH)
    sample = 'rule def_stmt {\n  scope "name", label:comment: keyword.static;\n}\n'
    result = engine.highlight(sample)
    assert result.error is None
    assert result.tokens is not None

    # Statement keyword literals, painted by their rule blocks.
    assert _token_type(result.tokens, sample, "rule") == "keyword"
    assert _token_type(result.tokens, sample, "scope") == "keyword"
    # The rule name a `rule` block addresses -> `type` (rule_config block).
    assert _token_type(result.tokens, sample, "def_stmt") == "type"
    # A quoted anchor literal -> `string` (literal block on `value`).
    assert _token_type(result.tokens, sample, '"name"') == "string"
    # The `label:` qualifier is a contextual keyword (qualifier block).
    assert _token_type(result.tokens, sample, "label") == "keyword"
    # Dotted scope-token segments -> `property` (dotted_name block on `part`).
    assert _token_type(result.tokens, sample, "keyword") == "property"
    assert _token_type(result.tokens, sample, "static") == "property"
    # A bare identifier anchor falls through to the default `variable` paint.
    assert _token_type(result.tokens, sample, "comment") == "variable"


def test_dogfood_highlights_def_ref_namespace_and_qualifier() -> None:
    engine = AnalysisEngine.from_paths(_GRAMMAR_PATH, _SPEC_PATH)
    sample = "rule widget {\n  def alpha: kw.static;\n  ref rule:beta: keyword;\n  namespace;\n}\n"
    result = engine.highlight(sample)
    assert result.error is None
    assert result.tokens is not None

    # The three statement keywords each painted by their own rule block.
    assert _token_type(result.tokens, sample, "def") == "keyword"
    assert _token_type(result.tokens, sample, "ref") == "keyword"
    assert _token_type(result.tokens, sample, "namespace") == "keyword"
    # The addressed rule name -> `type` (rule_config block on `rule_name`).
    assert _token_type(result.tokens, sample, "widget") == "type"
    # The `rule:` qualifier keyword (the `rule` inside `rule:beta`, a later occurrence than the
    # `rule` that opens the block).
    q = sample.index("rule:beta")
    assert any(t.start == q and t.end == q + len("rule") and t.token_type == "keyword" for t in result.tokens)
    # A global literal anchor paints the statement `;` punctuation.
    assert _token_type(result.tokens, sample, ";") == "punctuation"


def test_dogfood_partial_paints_prefix_on_mid_document_error() -> None:
    engine = AnalysisEngine.from_paths(_GRAMMAR_PATH, _SPEC_PATH)
    # The first `rule` block is valid; the second (`rule 4 {`, a number where an identifier is
    # required) breaks the top-level `statement*` repetition, leaving a prefix.
    sample = 'rule good {\n  scope "n": keyword;\n}\nrule 4 {\n}\n'
    analysis = engine.analyze(sample)
    assert analysis.error is not None
    assert analysis.tree is not None
    assert analysis.tokens is not None
    assert analysis.prefix_end is not None
    # The prefix's opening `rule` keyword is painted, and every token stays within the prefix.
    first_rule = sample.index("rule")
    assert any(t.start == first_rule and t.token_type == "keyword" for t in analysis.tokens)
    assert all(t.end <= analysis.prefix_end for t in analysis.tokens)


def test_dogfood_semantics_extract_and_resolve_over_real_grammar() -> None:
    grammar = plumbing.parse_grammar_file(_GRAMMAR_PATH)
    resolved = load_lsp_config(_SEMANTIC_SPEC, grammar)
    engine = AnalysisEngine(grammar, resolved)
    # `rule widget { scope widget: keyword; }` -- the block defines `widget` (type), and the
    # `scope` anchor `widget` is a reference that resolves back to that definition.
    sample = "rule widget {\n  scope widget: keyword;\n}\n"
    analysis = engine.analyze(sample)
    assert analysis.error is None
    assert analysis.symbols is not None

    definitions = {(s.name, s.kind) for s in analysis.symbols.symbols}
    assert ("widget", ("type",)) in definitions

    resolved_refs = [r for r in analysis.symbols.references if r.symbol is not None]
    assert any(r.name == "widget" and r.symbol is not None and r.symbol.kind == ("type",) for r in resolved_refs)
