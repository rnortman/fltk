"""Tests for the explicit painter layer and the combined `classify` token stream."""

from __future__ import annotations

import itertools

from fltk import plumbing
from fltk.lsp import classify as classify_module
from fltk.lsp import lsp_config, symbols
from fltk.lsp.analysis import prepare_analysis_grammar
from fltk.lsp.classify import Token, classify
from fltk.lsp.conftest import token_for as _token_for

# A small target grammar. `hello` is a word literal (default -> keyword), `word` is an identifier
# regex (default -> variable), `!` is a word-free non-punctuation literal (default -> operator).
# `greeting` is invoked by `top`, so a global `rule:greeting` anchor produces a whole-node paint.
_GRAMMAR = r"""
top := , greeting* ;
greeting := kw:"hello" , name:word , punct:"!" , ;
word := /[a-z]+/ ;
_trivia := ( line_comment | line_comment? : )+ ;
line_comment := prefix:"//" . content:/[^\n]*/ . newline:"\n" ;
"""


def _classify(config_text: str, text: str) -> list[Token]:
    grammar = plumbing.parse_grammar(_GRAMMAR)
    resolved = lsp_config.load_lsp_config(config_text, grammar)

    parser = plumbing.generate_parser(prepare_analysis_grammar(grammar))
    parsed = plumbing.parse_text(parser, text, "top")
    assert parsed.success, parsed.error_message
    return classify(parsed.cst, parser.grammar, resolved, text)


def _covering(tokens: list[Token], text: str, substr: str) -> list[Token]:
    start = text.index(substr)
    return [t for t in tokens if t.start <= start < t.end]


def test_explicit_scope_overrides_default() -> None:
    # Default would paint `world` (a `word` regex) as variable; an explicit scope makes it type.
    text = "hello world !"
    tokens = _classify("rule greeting {\n  scope name: type;\n}\n", text)
    assert _token_for(tokens, text, "world").token_type == "type"
    # Untouched terminals keep their defaults (`!` is a word-free non-punctuation literal -> operator).
    assert _token_for(tokens, text, "hello").token_type == "keyword"
    assert _token_for(tokens, text, "!").token_type == "operator"


def test_none_occludes_default_and_emits_no_token() -> None:
    text = "hello world !"
    tokens = _classify("rule greeting {\n  scope kw: none;\n}\n", text)
    # `hello` default keyword is suppressed by the `none` paint; no token covers it.
    assert _covering(tokens, text, "hello") == []
    assert _token_for(tokens, text, "world").token_type == "variable"


def test_innermost_explicit_wins_over_outer_node_paint() -> None:
    # Whole-greeting node paint (keyword) plus an inner scope on `name` (type). The inner, deeper
    # match wins over its sub-span; the outer paint still covers the rest.
    text = "hello world !"
    config = "scope rule:greeting: keyword;\nrule greeting {\n  scope name: type;\n}\n"
    tokens = _classify(config, text)
    # The whole-node keyword paint covers inter-item whitespace, so `hello`/`!` are not standalone
    # tokens; the covering token is what matters.
    assert _token_for(tokens, text, "world").token_type == "type"
    (hello_cover,) = _covering(tokens, text, "hello")
    assert hello_cover.token_type == "keyword"
    (bang_cover,) = _covering(tokens, text, "!")
    assert bang_cover.token_type == "keyword"


def test_rule_block_outranks_global() -> None:
    text = "hello world !"
    config = "scope label:name: type;\nrule greeting {\n  scope name: string;\n}\n"
    tokens = _classify(config, text)
    assert _token_for(tokens, text, "world").token_type == "string"


def test_label_anchor_outranks_rule_name_anchor() -> None:
    # Both match the `name:word` child. The label anchor comes first (smaller stmt_index); it must
    # still win over the later rule-name anchor, proving anchor_rank dominates stmt_index.
    text = "hello world !"
    config = "rule greeting {\n  scope name: type;\n  scope rule:word: string;\n}\n"
    tokens = _classify(config, text)
    assert _token_for(tokens, text, "world").token_type == "type"


def test_later_statement_wins_tie() -> None:
    text = "hello world !"
    config = "scope label:name: type;\nscope label:name: string;\n"
    tokens = _classify(config, text)
    assert _token_for(tokens, text, "world").token_type == "string"


def test_def_paints_declaration_and_explicit_scope_beats_def_at_same_node() -> None:
    text = "hello world !"
    # def alone: declaration-site paint with the `declaration` modifier.
    def_tokens = _classify("rule greeting {\n  def name: type;\n}\n", text)
    name_token = _token_for(def_tokens, text, "world")
    assert name_token.token_type == "type"
    assert name_token.modifiers == ("declaration",)
    # def + explicit scope on the same anchor: the scope wins (no declaration modifier).
    both = _classify("rule greeting {\n  def name: type;\n  scope name: variable;\n}\n", text)
    scoped = _token_for(both, text, "world")
    assert scoped.token_type == "variable"
    assert scoped.modifiers == ()


def test_literal_anchor_paints_span() -> None:
    text = "hello world !"
    tokens = _classify('scope "!": operator;\n', text)
    assert _token_for(tokens, text, "!").token_type == "operator"


def test_explicit_paint_descends_into_trivia_subtree() -> None:
    # An explicit scope inside the trivia rule paints one inner label; the surrounding `//` and
    # newline keep the default `comment`. This exercises explicit-layer descent into trivia (which
    # the default layer never does) plus the split-default subtraction around the painted span.
    text = "//hi there\nhello world !"
    tokens = _classify("rule line_comment {\n  scope content: string;\n}\n", text)
    assert _token_for(tokens, text, "hi there").token_type == "string"
    # The `//` prefix and trailing newline are the leftover fragments of the whole-comment default,
    # proving both that the explicit layer descended and that the default interval was split.
    (prefix_cover,) = _covering(tokens, text, "//")
    assert prefix_cover.token_type == "comment"
    newline_at = text.index("\n")
    newline_covers = [t for t in tokens if t.start <= newline_at < t.end]
    assert len(newline_covers) == 1
    assert newline_covers[0].token_type == "comment"


def test_token_stream_invariants() -> None:
    text = "//c\nhello world !\nhello there !"
    config = "scope rule:greeting: keyword;\nrule greeting {\n  scope name: type;\n  scope kw: none;\n}\n"
    tokens = _classify(config, text)

    # Sorted by start.
    assert tokens == sorted(tokens, key=lambda t: (t.start, t.end))
    # Non-overlapping.
    for prev, nxt in itertools.pairwise(tokens):
        assert prev.end <= nxt.start
    # In-bounds.
    for t in tokens:
        assert 0 <= t.start < t.end <= len(text)
    # No two adjacent tokens sharing type and modifiers left unmerged.
    for prev, nxt in itertools.pairwise(tokens):
        assert not (prev.end == nxt.start and prev.token_type == nxt.token_type and prev.modifiers == nxt.modifiers)
    # The `none`-scoped `hello` keyword emits no token.
    assert all(text[t.start : t.end] != "hello" for t in tokens)


# --- Ref-site paint (§4.4) ------------------------------------------------------------------------

# A def/ref language: `let NAME ;` declares, `use NAME ;` references. Default paint for the `word`
# regex is `variable`; a resolved ref inherits its defining kind's token.
_REF_GRAMMAR = r"""
program := , stmt* ;
stmt := decl | use ;
decl := kw:"let" , name:word , semi:";" , ;
use := kw:"use" , target:word , semi:";" , ;
word := /[a-z]+/ ;
_trivia := ( line_comment | line_comment? : )+ ;
line_comment := prefix:"//" . content:/[^\n]*/ . newline:"\n" ;
"""

# A nesting variant so ref depth and explicit-paint depth can be crossed: `use` wraps its target in
# an `inner` node, so a ref anchored on the `inner` node child is shallower than a scope on the
# `target` span inside `inner` (and vice versa).
_NEST_GRAMMAR = r"""
program := , stmt* ;
stmt := decl | use ;
decl := kw:"let" , name:word , semi:";" , ;
use := kw:"use" , inner , semi:";" , ;
inner := target:word ;
word := /[a-z]+/ ;
_trivia := ( line_comment | line_comment? : )+ ;
line_comment := prefix:"//" . content:/[^\n]*/ . newline:"\n" ;
"""


def _classify_syms(grammar_text: str, config_text: str, text: str) -> list[Token]:
    """Classify with a symbol table so resolved references paint their defining kind."""
    grammar = plumbing.parse_grammar(grammar_text)
    resolved = lsp_config.load_lsp_config(config_text, grammar)
    parser = plumbing.generate_parser(prepare_analysis_grammar(grammar))
    parsed = plumbing.parse_text(parser, text, "program")
    assert parsed.success, parsed.error_message
    tables = classify_module.build_grammar_tables(parser.grammar)
    table = symbols.extract(parsed.cst, tables, resolved, text)
    return classify(parsed.cst, parser.grammar, resolved, text, tables=tables, symbol_table=table)


def test_resolved_ref_paints_defining_kind() -> None:
    text = "let x ;\nuse x ;\n"
    config = "rule decl {\n  def name: type;\n}\nrule use {\n  ref target: type;\n}\n"
    tokens = _classify_syms(_REF_GRAMMAR, config, text)
    # The `x` in `use x` inherits the defining kind's token; the default would be `variable`.
    ref_x = text.index("use x") + 4
    (cover,) = [t for t in tokens if t.start == ref_x and t.token_type]
    assert cover.token_type == "type"
    assert cover.modifiers == ()  # ref paint carries no declaration modifier
    # The declaration site keeps its def-paint (declaration modifier).
    decl_x = text.index("let x") + 4
    (decl,) = [t for t in tokens if t.start == decl_x]
    assert decl.token_type == "type"
    assert decl.modifiers == ("declaration",)


def test_explicit_scope_beats_ref_paint_at_same_node() -> None:
    text = "let x ;\nuse x ;\n"
    config = "rule decl {\n  def name: type;\n}\nrule use {\n  ref target: type;\n  scope target: string;\n}\n"
    tokens = _classify_syms(_REF_GRAMMAR, config, text)
    ref_x = text.index("use x") + 4
    (cover,) = [t for t in tokens if t.start == ref_x]
    assert cover.token_type == "string"  # explicit scope (rank 2) beats ref paint (rank 1)


def test_deeper_explicit_beats_shallower_ref() -> None:
    # Ref anchored on the `inner` node child of `use` (shallow); a scope on the `target` span inside
    # `inner` is deeper and wins over their shared span.
    text = "let x ;\nuse x ;\n"
    config = (
        "rule decl {\n  def name: type;\n}\n"
        "rule use {\n  ref rule:inner: type;\n}\n"
        "rule inner {\n  scope target: string;\n}\n"
    )
    tokens = _classify_syms(_NEST_GRAMMAR, config, text)
    ref_x = text.index("use x") + 4
    (cover,) = [t for t in tokens if t.start == ref_x]
    assert cover.token_type == "string"


def test_deeper_ref_beats_shallower_explicit() -> None:
    # A whole-node scope on `inner` (shallow) vs a ref on the `target` span inside it (deeper).
    text = "let x ;\nuse x ;\n"
    config = "rule decl {\n  def name: type;\n}\nscope rule:inner: string;\nrule inner {\n  ref target: type;\n}\n"
    tokens = _classify_syms(_NEST_GRAMMAR, config, text)
    ref_x = text.index("use x") + 4
    (cover,) = [t for t in tokens if t.start == ref_x]
    assert cover.token_type == "type"


def test_unresolved_ref_falls_through_to_default() -> None:
    text = "use y ;\n"  # no `let y`, so the reference does not resolve
    config = "rule decl {\n  def name: type;\n}\nrule use {\n  ref target: type;\n}\n"
    tokens = _classify_syms(_REF_GRAMMAR, config, text)
    ref_y = text.index("use y") + 4
    (cover,) = [t for t in tokens if t.start == ref_y]
    assert cover.token_type == "variable"  # the built-in default for a `word` regex


def test_out_of_legend_kind_ref_gets_no_paint() -> None:
    text = "let x ;\nuse x ;\n"
    # `widget` is not a legend token, so the resolved ref contributes no paint.
    config = "rule decl {\n  def name: widget.thing;\n}\nrule use {\n  ref target: *;\n}\n"
    tokens = _classify_syms(_REF_GRAMMAR, config, text)
    ref_x = text.index("use x") + 4
    (cover,) = [t for t in tokens if t.start == ref_x]
    assert cover.token_type == "variable"  # default, not repainted


def test_none_scope_occludes_ref_paint() -> None:
    text = "let x ;\nuse x ;\n"
    config = "rule decl {\n  def name: type;\n}\nrule use {\n  ref target: type;\n  scope target: none;\n}\n"
    tokens = _classify_syms(_REF_GRAMMAR, config, text)
    ref_x = text.index("use x") + 4
    assert [t for t in tokens if t.start <= ref_x < t.end] == []  # none suppresses the ref paint


def test_classify_without_symbol_table_leaves_ref_as_default() -> None:
    # Regression pin: omitting the symbol table reproduces the reference-free (round-2) output.
    text = "let x ;\nuse x ;\n"
    config = "rule decl {\n  def name: type;\n}\nrule use {\n  ref target: type;\n}\n"
    grammar = plumbing.parse_grammar(_REF_GRAMMAR)
    resolved = lsp_config.load_lsp_config(config, grammar)
    parser = plumbing.generate_parser(prepare_analysis_grammar(grammar))
    parsed = plumbing.parse_text(parser, text, "program")
    assert parsed.success, parsed.error_message
    without = classify(parsed.cst, parser.grammar, resolved, text)
    ref_x = text.index("use x") + 4
    (cover,) = [t for t in without if t.start == ref_x]
    assert cover.token_type == "variable"


def test_ref_paint_preserves_token_stream_invariants() -> None:
    text = "let x ;\nuse x ;\nuse x ;\n"
    config = "rule decl {\n  def name: type;\n}\nrule use {\n  ref target: type;\n}\n"
    tokens = _classify_syms(_REF_GRAMMAR, config, text)
    assert tokens == sorted(tokens, key=lambda t: (t.start, t.end))
    for prev, nxt in itertools.pairwise(tokens):
        assert prev.end <= nxt.start
    for t in tokens:
        assert 0 <= t.start < t.end <= len(text)
