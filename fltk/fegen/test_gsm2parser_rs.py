"""Tests for the Rust parser generator (gsm2parser_rs.py)."""

from __future__ import annotations

import pytest

from fltk.fegen import gsm
from fltk.fegen.gsm2parser_rs import RustParserGenerator, _rust_str_lit

# ---------------------------------------------------------------------------
# Helper: build minimal test grammars
# ---------------------------------------------------------------------------


def _make_simple_grammar() -> gsm.Grammar:
    """A minimal grammar: one rule matching a regex."""
    rule = gsm.Rule(
        name="word",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="value",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[a-z]+"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    return gsm.Grammar(rules=[rule], identifiers={"word": rule})


def _make_two_rule_grammar() -> gsm.Grammar:
    """Grammar with two rules: items := item+ and item := /[a-z]+/."""
    item_rule = gsm.Rule(
        name="item",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="value",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[a-z]+"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    items_rule = gsm.Rule(
        name="items",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="item",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("item"),
                        quantifier=gsm.ONE_OR_MORE,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    return gsm.Grammar(
        rules=[items_rule, item_rule],
        identifiers={"items": items_rule, "item": item_rule},
    )


def _make_literal_grammar() -> gsm.Grammar:
    """Grammar with a literal term."""
    rule = gsm.Rule(
        name="kw",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.SUPPRESS,
                        term=gsm.Literal("keyword"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    return gsm.Grammar(rules=[rule], identifiers={"kw": rule})


def _make_ws_grammar() -> gsm.Grammar:
    """Grammar with WS_ALLOWED separator to test trivia capture code."""
    # expr := left:word , right:word
    word_rule = gsm.Rule(
        name="word",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="value",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[a-z]+"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    expr_rule = gsm.Rule(
        name="expr",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="left",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("word"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="right",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("word"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.WS_ALLOWED, gsm.Separator.NO_WS],
            )
        ],
    )
    return gsm.Grammar(
        rules=[expr_rule, word_rule],
        identifiers={"expr": expr_rule, "word": word_rule},
    )


# ---------------------------------------------------------------------------
# _rust_str_lit tests
# ---------------------------------------------------------------------------


def test_rust_str_lit_plain() -> None:
    assert _rust_str_lit("hello") == "hello"


def test_rust_str_lit_backslash() -> None:
    assert _rust_str_lit("a\\b") == "a\\\\b"


def test_rust_str_lit_double_quote() -> None:
    assert _rust_str_lit('say "hi"') == 'say \\"hi\\"'


def test_rust_str_lit_control_chars() -> None:
    # Null byte (0x00)
    assert _rust_str_lit("\x00") == "\\u{00}"
    # Tab (0x09)
    assert _rust_str_lit("\t") == "\\u{09}"
    # Newline (0x0a)
    assert _rust_str_lit("\n") == "\\u{0a}"
    # DEL (0x7f)
    assert _rust_str_lit("\x7f") == "\\u{7f}"


def test_rust_str_lit_multibyte() -> None:
    # Non-ASCII chars pass through verbatim
    assert _rust_str_lit("café") == "café"
    assert _rust_str_lit("αβγ") == "αβγ"


# ---------------------------------------------------------------------------
# Basic generation tests
# ---------------------------------------------------------------------------


def test_generate_returns_string() -> None:
    grammar = _make_simple_grammar()
    gen = RustParserGenerator(grammar)
    src = gen.generate()
    assert isinstance(src, str)
    assert len(src) > 0


def test_generate_has_apply_wrappers_per_rule() -> None:
    """Each rule (including _trivia) must have a pub apply__ wrapper."""
    grammar = _make_simple_grammar()
    gen = RustParserGenerator(grammar)
    src = gen.generate()

    # word rule
    assert "pub fn apply__parse_word(" in src
    # trivia rule
    assert "pub fn apply__parse__trivia(" in src


def test_generate_two_rules_apply_wrappers() -> None:
    grammar = _make_two_rule_grammar()
    gen = RustParserGenerator(grammar)
    src = gen.generate()

    assert "pub fn apply__parse_items(" in src
    assert "pub fn apply__parse_item(" in src
    assert "pub fn apply__parse__trivia(" in src


_EXPECTED_NON_APPLY_PUB_FNS = {
    "new",
    "from_source_text",
    "terminals",
    "capture_trivia",
    "rule_names",
    "error_message",
    "error_position",
}


def test_private_rule_bodies_not_pub() -> None:
    """parse_X body functions must be private (not pub).

    The only pub fn names that are not apply__ wrappers must be the fixed
    set of Parser struct accessors/constructors listed in _EXPECTED_NON_APPLY_PUB_FNS.
    """
    grammar = _make_simple_grammar()
    gen = RustParserGenerator(grammar)
    src = gen.generate()

    for line in src.splitlines():
        stripped = line.strip()
        if not stripped.startswith("pub fn "):
            continue
        fn_name = stripped.split("(")[0].removeprefix("pub fn ")
        if fn_name.startswith("apply__"):
            continue
        assert fn_name in _EXPECTED_NON_APPLY_PUB_FNS, f"Unexpected pub fn: {fn_name}"


def test_rule_names_constant() -> None:
    grammar = _make_simple_grammar()
    gen = RustParserGenerator(grammar)
    src = gen.generate()
    # Should have RULE_NAMES with word and _trivia
    assert "pub const RULE_NAMES:" in src
    assert '"word"' in src
    assert '"_trivia"' in src


def test_rule_names_order_matches_grammar() -> None:
    """RULE_NAMES order must match grammar.rules order (user rules first, trivia last)."""
    grammar = _make_two_rule_grammar()
    gen = RustParserGenerator(grammar)
    src = gen.generate()
    # items first, then item, then _trivia (added internally)
    rule_names_line = next(line for line in src.splitlines() if "RULE_NAMES" in line and "pub const" in line)
    items_pos = rule_names_line.find('"items"')
    item_pos = rule_names_line.find('"item"')
    trivia_pos = rule_names_line.find('"_trivia"')
    assert items_pos < item_pos < trivia_pos


def test_capture_trivia_field_in_struct() -> None:
    """Parser struct must have capture_trivia field."""
    grammar = _make_simple_grammar()
    gen = RustParserGenerator(grammar)
    src = gen.generate()
    assert "capture_trivia: bool," in src


def test_capture_trivia_check_in_separator() -> None:
    """WS_ALLOWED separator should emit 'if self.capture_trivia' check."""
    grammar = _make_ws_grammar()
    gen = RustParserGenerator(grammar)
    src = gen.generate()
    assert "self.capture_trivia" in src


def test_regex_table_emitted() -> None:
    """Regex table must be emitted when regexes are used."""
    grammar = _make_simple_grammar()
    gen = RustParserGenerator(grammar)
    src = gen.generate()
    assert "REGEX_PATTERNS" in src
    assert "REGEX_CELLS" in src
    assert "regex_at" in src
    # The pattern from the grammar
    assert "[a-z]+" in src


def test_regex_table_dedup() -> None:
    """Same regex pattern used twice must appear only once in the table."""
    # Create a grammar where the same pattern appears in two rules
    rule1 = gsm.Rule(
        name="a",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="v",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[a-z]+"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    rule2 = gsm.Rule(
        name="b",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="v",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[a-z]+"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    grammar = gsm.Grammar(rules=[rule1, rule2], identifiers={"a": rule1, "b": rule2})
    gen = RustParserGenerator(grammar)
    src = gen.generate()

    # Count how many times [a-z]+ appears in the REGEX_PATTERNS line
    regex_line = next(line for line in src.splitlines() if "REGEX_PATTERNS" in line and "const" in line)
    count = regex_line.count("[a-z]+")
    assert count == 1, f"Expected dedup, got {count} occurrences in: {regex_line}"


def test_literal_generates_consume_literal() -> None:
    """Grammar with literals must emit consume_literal helper."""
    grammar = _make_literal_grammar()
    gen = RustParserGenerator(grammar)
    src = gen.generate()
    assert "consume_literal" in src
    assert '"keyword"' in src


def test_regex_table_present_for_trivia_even_without_user_regexes() -> None:
    """REGEX_PATTERNS is emitted even when the grammar has no user regexes.

    The internal _trivia rule always uses a regex separator (\\s+), so the regex
    table is always present. A grammar with only literals still gets REGEX_PATTERNS
    for the trivia whitespace pattern.
    """
    rule = gsm.Rule(
        name="kw",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.SUPPRESS,
                        term=gsm.Literal("hello"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    grammar = gsm.Grammar(rules=[rule], identifiers={"kw": rule})
    gen = RustParserGenerator(grammar)
    src = gen.generate()
    assert "REGEX_PATTERNS" in src
    # The default _trivia rule uses [\s]+ as its content regex.
    regex_line = next(line for line in src.splitlines() if "REGEX_PATTERNS" in line and "const" in line)
    assert "[\\\\s]+" in regex_line


def test_deterministic_output() -> None:
    """Same grammar must produce identical output on repeated calls."""
    grammar = _make_two_rule_grammar()
    gen1 = RustParserGenerator(grammar)
    src1 = gen1.generate()
    gen2 = RustParserGenerator(grammar)
    src2 = gen2.generate()
    assert src1 == src2


def test_invocation_raises_not_implemented() -> None:
    """Invocation terms must raise NotImplementedError (either at construction or generate time)."""
    rule = gsm.Rule(
        name="inv",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Invocation(method_name="some_method", expression=None),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    grammar = gsm.Grammar(rules=[rule], identifiers={"inv": rule})
    with pytest.raises(NotImplementedError):
        gen = RustParserGenerator(grammar)
        gen.generate()


def test_inline_disposition_raises_at_some_point() -> None:
    """INLINE disposition on a non-Identifier term must raise an error.

    CstGenerator rejects INLINE on non-Identifier terms with an AssertionError.
    RustParserGenerator raises NotImplementedError for INLINE on Identifiers (see
    test_inline_disposition_identifier_raises_not_implemented). The exact exception
    type here depends on which layer rejects it first; both are correct rejections,
    so both are accepted. The Identifier-INLINE case is tested separately with a
    pinned exception type.
    """
    rule = gsm.Rule(
        name="inl",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INLINE,
                        term=gsm.Regex(r"[a-z]+"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    grammar = gsm.Grammar(rules=[rule], identifiers={"inl": rule})
    with pytest.raises((NotImplementedError, AssertionError)):
        gen = RustParserGenerator(grammar)
        gen.generate()


def test_inline_disposition_identifier_raises_not_implemented() -> None:
    """INLINE disposition on an Identifier term must raise NotImplementedError at generate time.

    CstGenerator supports INLINE on Identifiers (for inlining child rule's children),
    but the Rust parser generator does not.
    """
    child_rule = gsm.Rule(
        name="child",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="v",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[a-z]+"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    parent_rule = gsm.Rule(
        name="parent",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INLINE,
                        term=gsm.Identifier("child"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    grammar = gsm.Grammar(
        rules=[parent_rule, child_rule],
        identifiers={"parent": parent_rule, "child": child_rule},
    )
    with pytest.raises(NotImplementedError, match="INLINE"):
        gen = RustParserGenerator(grammar)
        gen.generate()


def test_parser_struct_has_cache_fields() -> None:
    """Parser struct must have cache fields for all rules."""
    grammar = _make_two_rule_grammar()
    gen = RustParserGenerator(grammar)
    src = gen.generate()

    assert "cache__parse_items:" in src
    assert "cache__parse_item:" in src
    assert "cache__parse__trivia:" in src


def test_apply_uses_rule_id_u32() -> None:
    """apply() calls must use u32-typed rule IDs."""
    grammar = _make_simple_grammar()
    gen = RustParserGenerator(grammar)
    src = gen.generate()
    # Should have something like "apply(self, 0u32, pos,"
    assert "u32" in src


def test_cst_mod_path_custom() -> None:
    """Custom cst_mod_path should appear in use statement."""
    grammar = _make_simple_grammar()
    gen = RustParserGenerator(grammar, cst_mod_path="my::module::cst")
    src = gen.generate()
    assert "use my::module::cst;" in src


def test_cst_mod_path_non_cst_suffix() -> None:
    """Non-cst-suffix path should emit 'use X as cst;'."""
    grammar = _make_simple_grammar()
    gen = RustParserGenerator(grammar, cst_mod_path="my::module::nodes")
    src = gen.generate()
    assert "use my::module::nodes as cst;" in src


def test_source_name_in_header() -> None:
    """Source name should appear in the generated header comment."""
    grammar = _make_simple_grammar()
    gen = RustParserGenerator(grammar, source_name="test.fltkg")
    src = gen.generate()
    assert "test.fltkg" in src


def test_optional_item_no_return_none() -> None:
    """Optional items (?) must not emit 'else { return None; }' in the item branch."""
    rule = gsm.Rule(
        name="opt",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="v",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[a-z]+"),
                        quantifier=gsm.NOT_REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    grammar = gsm.Grammar(rules=[rule], identifiers={"opt": rule})
    gen = RustParserGenerator(grammar)
    src = gen.generate()
    assert "pub fn apply__parse_opt(" in src
    # Locate the opt__alt0 body and verify it has no required-item else branch.
    # Split on the item parser fn boundary to isolate the alt body.
    # The alt body is between "fn parse_opt__alt0(" and the next "fn ".
    after_alt0 = src.split("fn parse_opt__alt0(", 1)[1]
    alt0_body = after_alt0.split("\n    fn ", 1)[0]
    # Optional item: no 'else {' in the item's if-let block.
    assert "} else {" not in alt0_body, "Optional item must not emit 'else { return None; }' in the alt body"


def test_zero_or_more_quantifier() -> None:
    """* quantifier: no required-match check (no 'if pos == span_start { return None; }')."""
    rule = gsm.Rule(
        name="zom",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="v",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[a-z]+"),
                        quantifier=gsm.ZERO_OR_MORE,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    grammar = gsm.Grammar(rules=[rule], identifiers={"zom": rule})
    gen = RustParserGenerator(grammar)
    src = gen.generate()
    assert "pub fn apply__parse_zom(" in src
    # Locate the zom item parser body and verify it has no +guard.
    after_item = src.split("fn parse_zom__alt0__item0(", 1)[1]
    item_body = after_item.split("\n    fn ", 1)[0]
    assert "if pos == span_start" not in item_body, "* quantifier must not emit the one-or-more progress guard"


def test_one_or_more_quantifier() -> None:
    """+ quantifier: must emit 'if pos == span_start { return None; }' check."""
    grammar = _make_two_rule_grammar()
    gen = RustParserGenerator(grammar)
    src = gen.generate()
    # The items rule has item+ — item parser must check for at least one match
    assert "if pos == span_start" in src
    assert "return None;" in src


def test_suppress_disposition_no_append() -> None:
    """SUPPRESS disposition must not generate append code."""
    grammar = _make_literal_grammar()
    gen = RustParserGenerator(grammar)
    src = gen.generate()
    assert "pub fn apply__parse_kw(" in src
    # Isolate the kw alternative body and verify no push_child or append_ is present
    # (SUPPRESS means: advance pos, do not record the child).
    after_alt0 = src.split("fn parse_kw__alt0(", 1)[1]
    alt0_body = after_alt0.split("\n    fn ", 1)[0]
    assert "push_child" not in alt0_body, "SUPPRESS must not emit push_child in the alt body"
    assert "append_" not in alt0_body, "SUPPRESS must not emit append_ in the alt body"


def test_ws_required_separator_has_else_return_none() -> None:
    """WS_REQUIRED separator must emit else { return None; } in the separator block."""
    rule1 = gsm.Rule(
        name="word",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="value",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[a-z]+"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    rule2 = gsm.Rule(
        name="pair",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="left",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("word"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="right",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("word"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.WS_REQUIRED, gsm.Separator.NO_WS],
            )
        ],
    )
    grammar = gsm.Grammar(
        rules=[rule2, rule1],
        identifiers={"pair": rule2, "word": rule1},
    )
    gen = RustParserGenerator(grammar)
    src = gen.generate()
    # Isolate the pair__alt0 body to verify the separator-specific else-branch,
    # rather than relying on any else-return that could come from required items.
    after_alt0 = src.split("fn parse_pair__alt0(", 1)[1]
    alt0_body = after_alt0.split("\n    fn ", 1)[0]
    # The WS_REQUIRED separator calls apply__parse__trivia with an else { return None; }.
    assert "apply__parse__trivia" in alt0_body, "WS_REQUIRED separator must call apply__parse__trivia"
    # The trivia if-let block must have an else-return for the WS_REQUIRED case.
    # The search is bounded: we require the else-return to appear BEFORE the next required-item
    # check ('if let Some(item1)'), so a WS_ALLOWED downgrade (which removes the trivia else-branch
    # but keeps the item1 else-return) cannot satisfy this test.
    item1_idx = alt0_body.find("if let Some(item1)")
    assert item1_idx != -1, "pair__alt0 must have 'if let Some(item1)' for the second item"
    trivia_idx = alt0_body.find("apply__parse__trivia")
    assert trivia_idx != -1, "WS_REQUIRED separator must call apply__parse__trivia"
    # The separator-specific else-return must appear between the trivia call and item1.
    trivia_else_idx = alt0_body.find("} else {", trivia_idx)
    assert trivia_else_idx != -1, "WS_REQUIRED separator block must have '} else {' after the trivia call"
    assert trivia_else_idx < item1_idx, (
        "Trivia else-branch must precede 'if let Some(item1)' — "
        "if it follows, it belongs to item1's required-item check, not the WS_REQUIRED separator"
    )
    return_idx = alt0_body.find("return None;", trivia_else_idx)
    assert return_idx != -1, "WS_REQUIRED separator block must have 'return None;' in the else branch"
    assert return_idx < item1_idx, "return None; in separator else-block must precede 'if let Some(item1)'"


# ---------------------------------------------------------------------------
# Union-label append path (scope coverage)
# ---------------------------------------------------------------------------


def test_union_label_append_uses_child_enum() -> None:
    """Union-typed label (same label, two node types) must wrap in child enum variant.

    When a label maps to two different node types (a union), the append statement
    must emit 'result.append_<lbl>(cst::<X>Child::<ClassName>(itemN.result))'
    rather than a bare 'result.append_<lbl>(itemN.result)'.
    """
    # Grammar: val := item:num | item:word
    # Both alternatives carry label "item"; CST sees two different node types under
    # the same label → union label → append uses child enum.
    num_rule = gsm.Rule(
        name="num",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="v",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[0-9]+"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    word_rule = gsm.Rule(
        name="word",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="v",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[a-z]+"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    val_rule = gsm.Rule(
        name="val",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="item",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("num"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
            gsm.Items(
                items=[
                    gsm.Item(
                        label="item",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("word"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
        ],
    )
    grammar = gsm.Grammar(
        rules=[val_rule, num_rule, word_rule],
        identifiers={"val": val_rule, "num": num_rule, "word": word_rule},
    )
    gen = RustParserGenerator(grammar)
    src = gen.generate()

    # Union-label append must wrap in child enum: cst::ValChild::Num(...) or cst::ValChild::Word(...)
    assert "cst::ValChild::Num(" in src or "cst::ValChild::Word(" in src, (
        "Union-label append must wrap the result in the child enum variant"
    )
    # Must NOT emit a bare append_item call (which would be the single-type path)
    # Specifically, append_item must take a ValChild enum value, not the node directly.
    # The child-enum form always has '::' after 'append_item(' in the form 'cst::ValChild::'.
    assert "result.append_item(cst::ValChild::" in src, (
        "Union-label append must use cst::<X>Child::<ClassName>(...) form"
    )


def test_source_name_none_omits_from_clause() -> None:
    """When source_name=None, the generated header must not contain 'from `<unknown>`'."""
    grammar = _make_simple_grammar()
    gen = RustParserGenerator(grammar)  # no source_name
    src = gen.generate()
    # Must not mention <unknown> — the clause is omitted entirely.
    assert "<unknown>" not in src, "source_name=None must not emit '<unknown>' in the header"
    # The generated header comment must still be present.
    assert "//! Generated by fltk gen-rust-parser." in src


def test_no_consume_literal_in_regex_only_grammar() -> None:
    """A grammar with no literal terms must not emit consume_literal (dead_code clippy)."""
    grammar = _make_simple_grammar()  # regex-only (no literals)
    gen = RustParserGenerator(grammar)
    src = gen.generate()
    assert "consume_literal" not in src, (
        "regex-only grammar must not emit consume_literal (would trigger dead_code clippy)"
    )


def test_generate_idempotent() -> None:
    """generate() must return the same result on a second call without re-emitting bodies."""
    grammar = _make_two_rule_grammar()
    gen = RustParserGenerator(grammar)
    src1 = gen.generate()
    src2 = gen.generate()
    assert src1 == src2, "generate() must be idempotent (second call must not re-emit fn bodies)"
    # Verify there is exactly one definition of each rule body (no duplication).
    assert src1.count("fn parse_items(") == 1, "parse_items must appear exactly once"


def test_multi_alternative_rule_emits_multiple_if_let_branches() -> None:
    """A rule with two alternatives must emit two 'if let Some(altN)' branches in order."""
    # val grammar has alt0 (num) and alt1 (word)
    num_rule = gsm.Rule(
        name="num",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="v",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[0-9]+"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    word_rule = gsm.Rule(
        name="word",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="v",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[a-z]+"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    val_rule = gsm.Rule(
        name="val",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="v",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("num"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
            gsm.Items(
                items=[
                    gsm.Item(
                        label="v",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("word"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
        ],
    )
    grammar = gsm.Grammar(
        rules=[val_rule, num_rule, word_rule],
        identifiers={"val": val_rule, "num": num_rule, "word": word_rule},
    )
    gen = RustParserGenerator(grammar)
    src = gen.generate()
    # Isolate parse_val body (not the apply__ wrapper)
    after_parse_val = src.split("fn parse_val(", 1)[1]
    parse_val_body = after_parse_val.split("\n    fn ", 1)[0]
    # Must contain both alt0 and alt1 branches in order.
    alt0_idx = parse_val_body.find("if let Some(alt0)")
    alt1_idx = parse_val_body.find("if let Some(alt1)")
    assert alt0_idx != -1, "parse_val must contain 'if let Some(alt0)'"
    assert alt1_idx != -1, "parse_val must contain 'if let Some(alt1)'"
    assert alt0_idx < alt1_idx, "alt0 branch must appear before alt1 branch"


# ---------------------------------------------------------------------------
# Identifier validation (errhandling-1)
# ---------------------------------------------------------------------------


def test_dangling_identifier_at_top_level_raises() -> None:
    """A top-level Identifier term referencing an unknown rule raises ValueError at construction."""
    rule = gsm.Rule(
        name="broken",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.SUPPRESS,
                        term=gsm.Identifier("nosuchrule"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    grammar = gsm.Grammar(rules=[rule], identifiers={"broken": rule})
    with pytest.raises(ValueError, match="nosuchrule"):
        RustParserGenerator(grammar)


def test_dangling_identifier_in_subexpression_raises() -> None:
    """An Identifier nested inside a sub-expression (list/tuple term) must also be caught.

    The validation walk must recurse into sub-expression alternatives, not just
    the top-level item terms.  Prior to the errhandling-1 fix, a dangling identifier
    inside a sub-expression was missed and would raise a raw KeyError at generate() time.
    """
    # Grammar: broken := (nosuchrule | /[a-z]+/)
    # The outer item's term is a sub-expression; inside, one alternative references
    # an unknown rule.  The identifier has INCLUDE disposition so it doesn't hit the
    # gsm2tree SUPPRESS-on-Sequence guard.
    sub_expr: list[gsm.Items] = [
        gsm.Items(
            items=[
                gsm.Item(
                    label="inner",
                    disposition=gsm.Disposition.INCLUDE,
                    term=gsm.Identifier("nosuchrule"),
                    quantifier=gsm.REQUIRED,
                )
            ],
            sep_after=[gsm.Separator.NO_WS],
        ),
        gsm.Items(
            items=[
                gsm.Item(
                    label="value",
                    disposition=gsm.Disposition.INCLUDE,
                    term=gsm.Regex(r"[a-z]+"),
                    quantifier=gsm.REQUIRED,
                )
            ],
            sep_after=[gsm.Separator.NO_WS],
        ),
    ]
    rule = gsm.Rule(
        name="broken",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="x",
                        disposition=gsm.Disposition.INCLUDE,
                        term=sub_expr,
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    grammar = gsm.Grammar(rules=[rule], identifiers={"broken": rule})
    with pytest.raises(ValueError, match="nosuchrule"):
        RustParserGenerator(grammar)
