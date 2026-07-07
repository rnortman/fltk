"""Tests for symbol extraction, scope construction, and reference resolution."""

from __future__ import annotations

from fltk import plumbing
from fltk.lsp import classify, lsp_config, symbols
from fltk.lsp.analysis import prepare_analysis_grammar

# Trivia block shared by every grammar so inter-token whitespace and `//` comments parse.
_TRIVIA = r"""
_trivia := ( line_comment | line_comment? : )+ ;
line_comment := prefix:"//" . content:/[^\n]*/ . newline:"\n" ;
"""

# Flat language: `let NAME ;` declares, `use NAME ;` references. No scopes.
_FLAT_GRAMMAR = (
    r"""
program := , stmt* ;
stmt := decl | use ;
decl := kw:"let" , name:word , semi:";" , ;
use := kw:"use" , target:word , semi:";" , ;
word := /[a-z]+/ ;
"""
    + _TRIVIA
)
_FLAT_CONFIG = "rule decl {\n  def name: variable;\n}\nrule use {\n  ref target: variable;\n}\n"

# Nested language: `mod NAME { ... }` opens a namespace, `let NAME ;` declares in the current
# scope, `use NAME ;` references. `block` is a namespace rule whose own name hoists outward.
_MOD_GRAMMAR = (
    r"""
program := , item* ;
item := block | use | decl ;
block := kw:"mod" , name:word , open:"{" , item* , close:"}" , ;
use := kw:"use" , target:word , semi:";" , ;
decl := kw:"let" , name:word , semi:";" , ;
word := /[a-z]+/ ;
"""
    + _TRIVIA
)
_MOD_CONFIG = (
    "rule block {\n  def name: namespace;\n  namespace;\n}\n"
    "rule decl {\n  def name: variable;\n}\n"
    "rule use {\n  ref target: *;\n}\n"
)


def _extract(grammar_text: str, config_text: str, text: str, start_rule: str) -> symbols.SymbolTable:
    grammar = plumbing.parse_grammar(grammar_text)
    resolved = lsp_config.load_lsp_config(config_text, grammar)
    parser = plumbing.generate_parser(prepare_analysis_grammar(grammar))
    parsed = plumbing.parse_text(parser, text, start_rule)
    assert parsed.success, parsed.error_message
    tables = classify.build_grammar_tables(parser.grammar)
    return symbols.extract(parsed.cst, tables, resolved, text)


def _sym(table: symbols.SymbolTable, name: str) -> symbols.Symbol:
    matches = [s for s in table.symbols if s.name == name]
    assert len(matches) == 1, f"expected one symbol named {name!r}, got {matches}"
    return matches[0]


def _ref(table: symbols.SymbolTable, text: str, substr: str) -> symbols.Reference:
    """Find the reference whose span is the trailing identifier of ``substr`` (e.g. ``use x``)."""
    token = substr.split()[-1]
    start = text.index(substr) + substr.rindex(token)
    end = start + len(token)
    matches = [r for r in table.references if r.start == start and r.end == end]
    assert len(matches) == 1, f"expected one reference for {substr!r}, got {matches}"
    return matches[0]


# --- Symbol fields and matching -------------------------------------------------------------------


def test_label_anchored_def_records_name_and_ranges() -> None:
    text = "let alpha ;\n"
    table = _extract(_FLAT_GRAMMAR, _FLAT_CONFIG, text, "program")
    (symbol,) = table.symbols
    assert symbol.name == "alpha"
    assert symbol.kind == ("variable",)
    # Selection range is the name child's span.
    assert text[symbol.name_start : symbol.name_end] == "alpha"
    # Declaration range is the producing `decl` node's span, wider than the name.
    assert symbol.range_start <= symbol.name_start
    assert symbol.range_end >= symbol.name_end
    assert text[symbol.range_start : symbol.range_end].startswith("let")


def test_rule_anchored_def_uses_node_span() -> None:
    grammar = "program := , ( word , )* ;\nword := /[a-z]+/ ;\n" + _TRIVIA
    config = "rule program {\n  def rule:word: variable;\n}\n"
    text = "aa bb\n"
    table = _extract(grammar, config, text, "program")
    assert {s.name for s in table.symbols} == {"aa", "bb"}


def test_literal_anchored_def_names_by_literal_text() -> None:
    grammar = 'program := , ( kw:"go" , )* ;\n' + _TRIVIA
    config = 'rule program {\n  def "go": variable;\n}\n'
    text = "go go\n"
    table = _extract(grammar, config, text, "program")
    assert [s.name for s in table.symbols] == ["go", "go"]


def test_union_anchor_defines_one_symbol_per_child() -> None:
    # `word` is both the implicit label of the unlabeled invocation and the invoked rule name,
    # so the def unions into two matchers; extraction must still create one symbol per child.
    grammar = "program := , ( word , )* ;\nword := /[a-z]+/ ;\n" + _TRIVIA
    config = "rule program {\n  def word: variable;\n}\n"
    text = "aa bb\n"
    table = _extract(grammar, config, text, "program")
    assert [s.name for s in table.symbols] == ["aa", "bb"]


def test_repeated_labeled_items_each_define_a_symbol() -> None:
    grammar = 'decl := kw:"let" , ( n:word , )+ , semi:";" , ;\nword := /[a-z]+/ ;\n' + _TRIVIA
    config = "rule decl {\n  def n: variable;\n}\n"
    text = "let a b c ;\n"
    table = _extract(grammar, config, text, "decl")
    assert [s.name for s in table.symbols] == ["a", "b", "c"]


def test_def_beats_ref_on_the_same_child() -> None:
    config = "rule decl {\n  def name: variable;\n  ref name: *;\n}\nrule use {\n  ref target: variable;\n}\n"
    text = "let x ;\n"
    table = _extract(_FLAT_GRAMMAR, config, text, "program")
    assert [s.name for s in table.symbols] == ["x"]
    # The def'd occurrence is a declaration only -- not additionally a reference.
    assert table.references == ()


# --- Scope tree -----------------------------------------------------------------------------------


def test_root_scope_spans_whole_text() -> None:
    text = "  let x ;\n"
    table = _extract(_FLAT_GRAMMAR, _FLAT_CONFIG, text, "program")
    assert table.root.start == 0
    assert table.root.end == len(text)


def test_namespace_opens_a_nested_scope() -> None:
    text = "mod m { let a ; }\n"
    table = _extract(_MOD_GRAMMAR, _MOD_CONFIG, text, "program")
    (inner,) = table.root.children
    assert inner.parent is table.root
    assert text[inner.start : inner.end].startswith("mod m")


# --- Namespace hoist (§2.1) -----------------------------------------------------------------------


def test_namespace_name_hoists_and_members_stay_inside() -> None:
    text = "mod outer { let a ; }\nuse outer ;\nuse a ;\n"
    table = _extract(_MOD_GRAMMAR, _MOD_CONFIG, text, "program")
    # `outer` (the namespace's own name) lives in the root scope.
    assert _sym(table, "outer") in table.root.symbols
    # `a` (a member) lives in the namespace scope, not the root.
    (inner,) = table.root.children
    assert _sym(table, "a") in inner.symbols
    assert _sym(table, "a") not in table.root.symbols
    # A reference to the namespace name from outside resolves.
    assert _ref(table, text, "use outer").symbol == _sym(table, "outer")
    # A reference to a member from outside the namespace does not.
    outside_a = next(r for r in table.references if r.start == text.index("use a") + 4)
    assert outside_a.symbol is None


def test_self_reference_resolves_through_hoisted_name() -> None:
    # A `use` of the namespace's own name from *inside* the namespace resolves to the hoisted name.
    text = "mod outer { use outer ; }\n"
    table = _extract(_MOD_GRAMMAR, _MOD_CONFIG, text, "program")
    assert _ref(table, text, "use outer").symbol == _sym(table, "outer")


def test_member_reference_resolves_within_namespace() -> None:
    text = "mod m { let a ; use a ; }\n"
    table = _extract(_MOD_GRAMMAR, _MOD_CONFIG, text, "program")
    assert _ref(table, text, "use a").symbol == _sym(table, "a")


def test_identical_span_nested_namespaces_nest_and_resolve_outward() -> None:
    # `outer := inner ;` with both namespace rules: `outer` and `inner` nodes share a span, so two
    # scopes with identical bounds nest inner-inside-outer. A reference inside `inner` must resolve
    # through both scopes outward to a symbol defined further out.
    grammar = (
        "program := , decl , wrap , ;\n"
        'decl := kw:"let" , name:word , semi:";" , ;\n'
        'wrap := kw:"w" , outer , ;\n'
        "outer := inner ;\n"
        'inner := kw:"use" , target:word , semi:";" , ;\n'
        "word := /[a-z]+/ ;\n"
    ) + _TRIVIA
    config = (
        "rule decl {\n  def name: variable;\n}\n"
        "rule outer {\n  namespace;\n}\n"
        "rule inner {\n  namespace;\n  ref target: variable;\n}\n"
    )
    text = "let a ;\nw use a ;\n"
    table = _extract(grammar, config, text, "program")
    (outer_scope,) = table.root.children
    (inner_scope,) = outer_scope.children
    # Two distinct scopes are created even though their spans coincide.
    assert (outer_scope.start, outer_scope.end) == (inner_scope.start, inner_scope.end)
    assert inner_scope.parent is outer_scope
    # The reference inside `inner` resolves outward through both scopes to the root-level symbol.
    assert _ref(table, text, "use a").symbol == _sym(table, "a")


# --- Resolution semantics -------------------------------------------------------------------------


def test_forward_reference_resolves() -> None:
    text = "use x ;\nlet x ;\n"
    table = _extract(_FLAT_GRAMMAR, _FLAT_CONFIG, text, "program")
    assert _ref(table, text, "use x").symbol == _sym(table, "x")


def test_inner_definition_shadows_outer() -> None:
    text = "let a ;\nmod m { let a ; use a ; }\n"
    table = _extract(_MOD_GRAMMAR, _MOD_CONFIG, text, "program")
    inner_a_start = text.index("let a ;", text.index("mod")) + 4
    resolved = _ref(table, text, "use a").symbol
    assert resolved is not None
    assert resolved.name_start == inner_a_start  # the inner `a`, not the root one


def test_unresolved_reference_stays_none() -> None:
    text = "use missing ;\n"
    table = _extract(_FLAT_GRAMMAR, _FLAT_CONFIG, text, "program")
    assert _ref(table, text, "use missing").symbol is None


def test_duplicate_defs_resolve_to_document_first() -> None:
    text = "let a ;\nlet a ;\nuse a ;\n"
    table = _extract(_FLAT_GRAMMAR, _FLAT_CONFIG, text, "program")
    assert len([s for s in table.symbols if s.name == "a"]) == 2
    resolved = _ref(table, text, "use a").symbol
    assert resolved is not None
    assert resolved.name_start == text.index("let a ;") + 4  # the first declaration


def test_kind_prefix_matching_on_segment_boundary() -> None:
    # `ref target: type` sees a `type.cog` symbol (prefix on a segment boundary)...
    seeing = _extract(
        _FLAT_GRAMMAR,
        "rule decl {\n  def name: type.cog;\n}\nrule use {\n  ref target: type;\n}\n",
        "let x ;\nuse x ;\n",
        "program",
    )
    assert _ref(seeing, "let x ;\nuse x ;\n", "use x").symbol is not None
    # ...but `ref target: type.cog` does not see a bare `type` symbol.
    not_seeing = _extract(
        _FLAT_GRAMMAR,
        "rule decl {\n  def name: type;\n}\nrule use {\n  ref target: type.cog;\n}\n",
        "let x ;\nuse x ;\n",
        "program",
    )
    assert _ref(not_seeing, "let x ;\nuse x ;\n", "use x").symbol is None


def test_wildcard_ref_matches_any_kind() -> None:
    table = _extract(
        _FLAT_GRAMMAR,
        "rule decl {\n  def name: widget.thing;\n}\nrule use {\n  ref target: *;\n}\n",
        "let x ;\nuse x ;\n",
        "program",
    )
    assert _ref(table, "let x ;\nuse x ;\n", "use x").symbol is not None


def test_kind_list_matches_any_listed() -> None:
    table = _extract(
        _FLAT_GRAMMAR,
        "rule decl {\n  def name: function;\n}\nrule use {\n  ref target: type, function;\n}\n",
        "let x ;\nuse x ;\n",
        "program",
    )
    assert _ref(table, "let x ;\nuse x ;\n", "use x").symbol is not None


# --- Lookups and occurrences ----------------------------------------------------------------------


def test_symbol_at_and_reference_at_select_innermost() -> None:
    text = "let alpha ;\nuse alpha ;\n"
    table = _extract(_FLAT_GRAMMAR, _FLAT_CONFIG, text, "program")
    def_off = text.index("alpha") + 2
    assert table.symbol_at(def_off) is _sym(table, "alpha")
    assert table.reference_at(def_off) is None  # the def name is not a reference span
    ref_off = text.index("use alpha") + 6
    assert table.reference_at(ref_off) is _ref(table, text, "use alpha")
    assert table.symbol_at(ref_off) is None


def test_occurrences_dedupes_overlapping_spans() -> None:
    # A single-child chain: a ref anchored on the node child (`inner`) and a ref anchored on the
    # span child (`name`) name the identical range; occurrences must list it once.
    grammar = (
        "program := , item* ;\n"
        "item := decl | wrap ;\n"
        'decl := kw:"let" , name:word , semi:";" , ;\n'
        'wrap := kw:"r" , inner , wsemi:";" , ;\n'
        "inner := name:word ;\n"
        "word := /[a-z]+/ ;\n"
    ) + _TRIVIA
    config = (
        "rule decl {\n  def name: variable;\n}\nrule wrap {\n  ref rule:inner: *;\n}\nrule inner {\n  ref name: *;\n}\n"
    )
    text = "let a ;\nr a ;\n"
    table = _extract(grammar, config, text, "program")
    symbol = _sym(table, "a")
    occ = table.occurrences(symbol)
    # The two references over `a` in `r a ;` share a span; it appears once alongside the decl.
    assert len(occ) == len(set(occ))
    r_a = text.index("r a") + 2
    assert (r_a, r_a + 1) in occ
    assert (symbol.name_start, symbol.name_end) in occ
