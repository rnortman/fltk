"""Test grammar-based trivia rule discovery and classification."""

from fltk.fegen import gsm


def test_trivia_rule_discovery():
    """Test that rules reachable from '_TRIVIA' rule are correctly classified."""
    # Create grammar with trivia rule
    ws_rule = gsm.Rule(
        name="ws",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None, disposition=gsm.Disposition.INCLUDE, term=gsm.Regex(r"\s+"), quantifier=gsm.REQUIRED
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )

    line_comment_rule = gsm.Rule(
        name="line_comment",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None, disposition=gsm.Disposition.INCLUDE, term=gsm.Literal("//"), quantifier=gsm.REQUIRED
                    ),
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[^\n]*"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label=None, disposition=gsm.Disposition.INCLUDE, term=gsm.Literal("\n"), quantifier=gsm.REQUIRED
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS, gsm.Separator.NO_WS, gsm.Separator.NO_WS],
            )
        ],
    )

    trivia_rule = gsm.Rule(
        name="_TRIVIA",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("ws"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("line_comment"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
        ],
    )

    # Non-trivia rule
    function_rule = gsm.Rule(
        name="function",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("function"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="name",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("identifier"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.WS_REQUIRED, gsm.Separator.NO_WS],
            )
        ],
    )

    identifier_rule = gsm.Rule(
        name="identifier",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[a-zA-Z_][a-zA-Z0-9_]*"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )

    rules = [ws_rule, line_comment_rule, trivia_rule, function_rule, identifier_rule]
    identifiers = {rule.name: rule for rule in rules}
    grammar = gsm.Grammar(rules=rules, identifiers=identifiers)

    # Classify trivia rules
    classified_grammar = gsm.classify_trivia_rules(grammar)

    # Check classification results
    classified_rules = {rule.name: rule for rule in classified_grammar.rules}

    # Rules reachable from trivia should be marked as trivia rules
    assert classified_rules["_TRIVIA"].is_trivia_rule is True
    assert classified_rules["ws"].is_trivia_rule is True
    assert classified_rules["line_comment"].is_trivia_rule is True

    # Non-trivia rules should not be marked
    assert classified_rules["function"].is_trivia_rule is False
    assert classified_rules["identifier"].is_trivia_rule is False


def test_no_trivia_rule():
    """Test that grammars without trivia rule are unchanged."""
    # Create grammar without trivia rule
    identifier_rule = gsm.Rule(
        name="identifier",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[a-zA-Z_][a-zA-Z0-9_]*"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )

    rules = [identifier_rule]
    identifiers = {rule.name: rule for rule in rules}
    grammar = gsm.Grammar(rules=rules, identifiers=identifiers)

    # Classify trivia rules
    classified_grammar = gsm.classify_trivia_rules(grammar)

    # Should be unchanged
    assert classified_grammar == grammar
    assert classified_grammar.rules[0].is_trivia_rule is False


def test_trivia_separation_validation():
    """Test that mixed trivia/non-trivia usage is detected."""
    # Create grammar where non-trivia rule references trivia rule
    line_comment_rule = gsm.Rule(
        name="line_comment",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None, disposition=gsm.Disposition.INCLUDE, term=gsm.Literal("//"), quantifier=gsm.REQUIRED
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )

    trivia_rule = gsm.Rule(
        name="_TRIVIA",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("line_comment"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )

    # Invalid: non-trivia rule referencing trivia rule
    invalid_rule = gsm.Rule(
        name="invalid",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("line_comment"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )

    rules = [line_comment_rule, trivia_rule, invalid_rule]
    identifiers = {rule.name: rule for rule in rules}
    grammar = gsm.Grammar(rules=rules, identifiers=identifiers)

    # Should raise validation error
    try:
        gsm.classify_trivia_rules(grammar)
        msg = "Expected ValueError for trivia separation violation"
        raise AssertionError(msg)
    except ValueError as e:
        assert "trivia separation violations" in str(e).lower()
        assert "invalid" in str(e)
        assert "line_comment" in str(e)


if __name__ == "__main__":
    test_trivia_rule_discovery()
    test_no_trivia_rule()
    test_trivia_separation_validation()
