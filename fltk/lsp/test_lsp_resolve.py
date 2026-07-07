"""Tests for anchor resolution: a validated LspConfig into the classifier's matcher tables."""

from fltk import plumbing
from fltk.lsp import lsp_config

# A small target grammar exercising labels, invoked rules, and literals.
#   greeting: labels {kw, name}, literals {"hello", "!"}, invoked rules {word}
#   word:     no labels/literals/invoked rules
_GRAMMAR = """
greeting := kw:"hello" , name:word , "!" ;
word := /[a-z]+/ ;
"""


def _resolve(config_text: str) -> lsp_config.ResolvedLspConfig:
    return lsp_config.load_lsp_config(config_text, plumbing.parse_grammar(_GRAMMAR))


def test_empty_config_resolves_to_empty_tables() -> None:
    resolved = _resolve("")
    assert resolved.node_paints == {}
    assert resolved.child_matchers == {}
    assert resolved.global_child_matchers == ()


def test_global_rule_name_anchor_becomes_node_paint() -> None:
    resolved = _resolve("scope rule:greeting: keyword;\n")
    assert set(resolved.node_paints) == {"greeting"}
    (node_paint,) = resolved.node_paints["greeting"]
    assert node_paint.paint == lsp_config.Paint("keyword", ())
    assert node_paint.tier.anchor_rank == lsp_config.ANCHOR_RANK_RULE_NAME
    assert node_paint.tier.block_rank == lsp_config.BLOCK_RANK_GLOBAL
    assert resolved.global_child_matchers == ()


def test_global_label_anchor_becomes_global_matcher() -> None:
    resolved = _resolve("scope label:kw: keyword;\n")
    assert resolved.node_paints == {}
    (matcher,) = resolved.global_child_matchers
    assert matcher.match == lsp_config.ByLabel("kw")
    assert matcher.paint == lsp_config.Paint("keyword", ())
    assert matcher.tier.anchor_rank == lsp_config.ANCHOR_RANK_LABEL_LITERAL


def test_global_literal_anchor_becomes_global_matcher() -> None:
    resolved = _resolve('scope "!": punctuation;\n')
    assert resolved.node_paints == {}
    (matcher,) = resolved.global_child_matchers
    assert matcher.match == lsp_config.ByLiteralText("!")
    assert matcher.paint == lsp_config.Paint("punctuation", ())


def test_unqualified_global_rule_and_label_union() -> None:
    # `salutation := kw:"hi" word` invokes `word` unlabeled, so fltk2gsm gives it the implicit
    # label `word`: `word` is now both a rule name and an item label => both readings emitted.
    grammar_text = 'salutation := kw:"hi" , word ;\nword := /[a-z]+/ ;\n'
    config_text = "scope word: variable;\n"
    resolved = lsp_config.load_lsp_config(config_text, plumbing.parse_grammar(grammar_text))
    # rule-name reading => node paint on `word`.
    assert set(resolved.node_paints) == {"word"}
    # label reading => global by-label matcher.
    labels = {m.match for m in resolved.global_child_matchers if isinstance(m.match, lsp_config.ByLabel)}
    assert lsp_config.ByLabel("word") in labels


def test_local_scope_anchors() -> None:
    resolved = _resolve(
        "rule greeting {\n"
        "  scope kw: keyword;\n"
        "  scope name: variable;\n"
        '  scope "!": punctuation;\n'
        "  scope rule:word: type;\n"
        "}\n"
    )
    matchers = resolved.child_matchers["greeting"]
    by_match = {m.match: m for m in matchers}
    # `name` is a label (it labels the `word` invocation) but not an invoked rule name;
    # `word` is the invoked rule name.
    assert lsp_config.ByLabel("kw") in by_match
    assert lsp_config.ByLabel("name") in by_match
    assert lsp_config.ByLiteralText("!") in by_match
    assert lsp_config.ByChildRule("word") in by_match
    assert by_match[lsp_config.ByLabel("kw")].paint == lsp_config.Paint("keyword", ())
    assert by_match[lsp_config.ByChildRule("word")].tier.anchor_rank == lsp_config.ANCHOR_RANK_RULE_NAME
    # All rule-block scope matchers carry rule block rank and explicit-scope source rank.
    for m in matchers:
        assert m.tier.block_rank == lsp_config.BLOCK_RANK_RULE
        assert m.tier.source_rank == lsp_config.SOURCE_RANK_SCOPE


def test_def_paint_in_legend_adds_declaration_modifier() -> None:
    resolved = _resolve("rule greeting {\n  def name: type.something;\n}\n")
    (matcher,) = resolved.child_matchers["greeting"]
    assert matcher.match == lsp_config.ByLabel("name")
    assert matcher.paint == lsp_config.Paint("type", ("declaration",))
    assert matcher.tier.source_rank == lsp_config.SOURCE_RANK_DEF


def test_def_paint_kind_not_in_legend_emits_nothing() -> None:
    # `symbol` is not a legend token, so the def contributes no paint (but still validates).
    resolved = _resolve("rule greeting {\n  def name: symbol.function;\n}\n")
    assert resolved.child_matchers == {}


def test_def_emits_def_matcher_with_kind_and_tier() -> None:
    # A def whose kind is out of the legend still contributes a semantic matcher (no paint).
    resolved = _resolve("rule greeting {\n  def name: symbol.function;\n}\n")
    assert resolved.child_matchers == {}  # out-of-legend -> no paint
    (dm,) = resolved.def_matchers["greeting"]
    assert dm.match == lsp_config.ByLabel("name")
    assert dm.kind == ("symbol", "function")
    assert dm.tier.source_rank == lsp_config.SOURCE_RANK_DEF


def test_ref_emits_ref_matcher_with_kinds_and_tier() -> None:
    resolved = _resolve("rule greeting {\n  ref name: type.cog, function;\n}\n")
    (rm,) = resolved.ref_matchers["greeting"]
    assert rm.match == lsp_config.ByLabel("name")
    assert rm.kinds == (("type", "cog"), ("function",))
    assert rm.tier.source_rank == lsp_config.SOURCE_RANK_REF


def test_ref_wildcard_kinds_preserved() -> None:
    resolved = _resolve("rule greeting {\n  ref name: *;\n}\n")
    (rm,) = resolved.ref_matchers["greeting"]
    assert rm.kinds == "*"


def test_unqualified_def_anchor_unions_label_and_rule() -> None:
    # `name` labels the `word` invocation; `word` is the invoked rule name. An unqualified def
    # on `word` would union, but here we anchor on the rule name to exercise both readings.
    grammar_text = 'greeting := kw:"hi" , word ;\nword := /[a-z]+/ ;\n'
    resolved = lsp_config.load_lsp_config(
        "rule greeting {\n  def word: type;\n}\n", plumbing.parse_grammar(grammar_text)
    )
    matches = {dm.match for dm in resolved.def_matchers["greeting"]}
    assert lsp_config.ByLabel("word") in matches
    assert lsp_config.ByChildRule("word") in matches


def test_namespace_flag_accumulates_across_blocks() -> None:
    resolved = _resolve("rule greeting {\n  ref name: *;\n}\nrule greeting {\n  namespace;\n}\n")
    assert resolved.namespace_rules == frozenset({"greeting"})
    # The ref from the first block survives even though neither block produced a paint matcher.
    assert "greeting" in resolved.ref_matchers
    assert "greeting" not in resolved.child_matchers


def test_no_semantic_statements_leaves_tables_empty() -> None:
    resolved = _resolve("rule greeting {\n  scope name: type;\n}\n")
    assert resolved.def_matchers == {}
    assert resolved.ref_matchers == {}
    assert resolved.namespace_rules == frozenset()


def test_none_token_paint_preserved() -> None:
    resolved = _resolve("rule greeting {\n  scope name: none;\n}\n")
    (matcher,) = resolved.child_matchers["greeting"]
    assert matcher.paint == lsp_config.Paint("none", ())


def test_explicit_scope_outranks_def_and_later_wins() -> None:
    # A scope and a def on the same anchor: scope's source_rank is higher; and stmt_index
    # increases in file order so later statements carry larger keys.
    resolved = _resolve(
        "rule greeting {\n"
        "  def name: type;\n"  # index 1, source_rank DEF
        "  scope name: variable;\n"  # index 2, source_rank SCOPE
        "}\n"
    )
    matchers = resolved.child_matchers["greeting"]
    scope_m = next(m for m in matchers if m.paint == lsp_config.Paint("variable", ()))
    def_m = next(m for m in matchers if m.paint == lsp_config.Paint("type", ("declaration",)))
    assert scope_m.tier.source_rank > def_m.tier.source_rank
    assert scope_m.tier.stmt_index > def_m.tier.stmt_index


def test_multiple_rule_blocks_accumulate() -> None:
    resolved = _resolve("rule greeting {\n  scope kw: keyword;\n}\nrule greeting {\n  scope name: variable;\n}\n")
    matchers = resolved.child_matchers["greeting"]
    matches = {m.match for m in matchers}
    assert lsp_config.ByLabel("kw") in matches
    assert lsp_config.ByLabel("name") in matches
