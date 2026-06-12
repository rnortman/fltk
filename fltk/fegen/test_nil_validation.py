"""Test for repeated potentially-nil items validation."""

import pytest

from fltk.fegen import gsm


def test_repeated_nil_validation_catches_trivia_issue():
    """Test that the validation catches the problematic trivia pattern."""
    # Create a grammar with the problematic pattern: (line_comment? ,)+
    line_comment_rule = gsm.Rule(
        name="line_comment",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="prefix",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("//"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="content",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[^\n]*"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="newline",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("\n"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS, gsm.Separator.NO_WS, gsm.Separator.NO_WS],
            )
        ],
    )

    # Create trivia rule with problematic pattern: (line_comment? ,)+
    trivia_rule = gsm.Rule(
        name="_trivia",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INCLUDE,
                        term=[  # Parentheses - list of alternatives
                            gsm.Items(
                                items=[
                                    gsm.Item(
                                        label=None,
                                        disposition=gsm.Disposition.INCLUDE,
                                        term=gsm.Identifier("line_comment"),
                                        quantifier=gsm.NOT_REQUIRED,  # ? makes it optional
                                    ),
                                ],
                                sep_after=[gsm.Separator.WS_ALLOWED],  # , separator
                            )
                        ],
                        quantifier=gsm.ONE_OR_MORE,  # + makes it repeated
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )

    grammar = gsm.Grammar(
        rules=[line_comment_rule, trivia_rule], identifiers={"line_comment": line_comment_rule, "_trivia": trivia_rule}
    )

    # This should raise a ValueError
    with pytest.raises(ValueError, match="Repeated potentially-nil items found"):
        gsm.validate_no_repeated_nil_items(grammar)


def test_repeated_nil_validation_rejects_nested_subexpr():
    """validate_no_repeated_nil_items rejects +/* item nested inside a sub-expression.

    Grammar: rule := outer:( (x:r"a*")+ )
    The outer item is REQUIRED over a sub-expression; the inner item is ONE_OR_MORE
    over Regex(r"a*").  Previously the validator only inspected top-level items and
    missed the nested ONE_OR_MORE, so such grammars passed validation and reached
    codegen.  With the recursive walk, the inner item is found and rejected.
    """
    inner_items = gsm.Items(
        items=[
            gsm.Item(
                label="x",
                disposition=gsm.Disposition.INCLUDE,
                term=gsm.Regex(r"a*"),  # nullable
                quantifier=gsm.ONE_OR_MORE,  # nested +
            )
        ],
        sep_after=[gsm.Separator.NO_WS],
    )
    rule = gsm.Rule(
        name="rule",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="outer",
                        disposition=gsm.Disposition.INCLUDE,
                        term=[inner_items],  # sub-expression wrapping the + item
                        quantifier=gsm.REQUIRED,  # REQUIRED outer — top-level walk missed this
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    grammar = gsm.Grammar(rules=[rule], identifiers={"rule": rule})

    with pytest.raises(ValueError, match="Repeated potentially-nil items found"):
        gsm.validate_no_repeated_nil_items(grammar)


def test_repeated_nil_validation_rejects_deeply_nested_subexpr():
    """validate_no_repeated_nil_items rejects +/* item two sub-expression levels deep.

    Grammar: rule := outer:( wrapper:( (x:r"a*")* ) )
    The ZERO_OR_MORE item lives two sub-expression levels below the rule alternative.
    """
    innermost_items = gsm.Items(
        items=[
            gsm.Item(
                label="x",
                disposition=gsm.Disposition.INCLUDE,
                term=gsm.Regex(r"a*"),  # nullable
                quantifier=gsm.ZERO_OR_MORE,  # *
            )
        ],
        sep_after=[gsm.Separator.NO_WS],
    )
    wrapper_items = gsm.Items(
        items=[
            gsm.Item(
                label="wrapper",
                disposition=gsm.Disposition.INCLUDE,
                term=[innermost_items],
                quantifier=gsm.REQUIRED,
            )
        ],
        sep_after=[gsm.Separator.NO_WS],
    )
    rule = gsm.Rule(
        name="rule",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="outer",
                        disposition=gsm.Disposition.INCLUDE,
                        term=[wrapper_items],
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    grammar = gsm.Grammar(rules=[rule], identifiers={"rule": rule})

    with pytest.raises(ValueError, match="Repeated potentially-nil items found"):
        gsm.validate_no_repeated_nil_items(grammar)


def test_repeated_nil_validation_allows_safe_patterns():
    """Test that the validation allows safe patterns."""
    # Create a rule with required items (safe to repeat)
    safe_rule = gsm.Rule(
        name="safe_rule",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("required"),
                        quantifier=gsm.ONE_OR_MORE,  # + but item is required
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )

    grammar = gsm.Grammar(rules=[safe_rule], identifiers={"safe_rule": safe_rule})

    # This should not raise an error
    gsm.validate_no_repeated_nil_items(grammar)


def test_trivia_rule_not_nil_validation():
    """Test that trivia rules cannot be nil (optional-quantifier path, pre-existing)."""
    # Create a trivia rule that can be nil via NOT_REQUIRED quantifier
    nil_trivia_rule = gsm.Rule(
        name="_trivia",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"\s*"),  # Can match empty string
                        quantifier=gsm.NOT_REQUIRED,  # ? makes it optional
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )

    grammar = gsm.Grammar(rules=[nil_trivia_rule], identifiers={"_trivia": nil_trivia_rule})

    # This should raise a ValueError
    with pytest.raises(ValueError, match="Trivia rule '_trivia' cannot match empty string"):
        gsm.validate_trivia_rule_not_nil(grammar)


def test_trivia_rule_not_nil_required_nullable_term():
    """validate_trivia_rule_not_nil rejects REQUIRED quantifier + nullable regex term.

    Pre-fix: the quantifier-only check (is_optional()) returned False for REQUIRED,
    so this trivia rule was accepted even though it can produce empty matches.
    Post-fix: Item.can_be_nil is term-aware; REQUIRED + Regex(r"\\s*") → True → rejected.
    """
    nil_trivia_rule = gsm.Rule(
        name="_trivia",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="content",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"\s*"),  # nullable — can match empty string
                        quantifier=gsm.REQUIRED,  # REQUIRED quantifier, not optional
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    grammar = gsm.Grammar(rules=[nil_trivia_rule], identifiers={"_trivia": nil_trivia_rule})

    with pytest.raises(ValueError, match="Trivia rule '_trivia' cannot match empty string"):
        gsm.validate_trivia_rule_not_nil(grammar)


def test_regex_nil_detection():
    """Test that regex nil detection works correctly."""
    grammar = gsm.Grammar(rules=[], identifiers={})

    # Test regexes that can match empty
    assert gsm.Regex(r"a*").can_be_nil(grammar) is True
    assert gsm.Regex(r"a?").can_be_nil(grammar) is True
    assert gsm.Regex(r"(a|)").can_be_nil(grammar) is True
    assert gsm.Regex(r"").can_be_nil(grammar) is True

    # Test regexes that cannot match empty
    assert gsm.Regex(r"a+").can_be_nil(grammar) is False
    assert gsm.Regex(r"a").can_be_nil(grammar) is False
    assert gsm.Regex(r"[a-z]+").can_be_nil(grammar) is False


def test_literal_nil_detection():
    """Test that literal nil detection works correctly."""
    grammar = gsm.Grammar(rules=[], identifiers={})

    # Empty string literal can be nil
    assert gsm.Literal("").can_be_nil(grammar) is True

    # Non-empty literals cannot be nil
    assert gsm.Literal("hello").can_be_nil(grammar) is False
    assert gsm.Literal(" ").can_be_nil(grammar) is False


def test_separator_nil_detection():
    """Test that separator nil detection works correctly."""
    # Test all separator types
    assert gsm.Separator.NO_WS.can_be_nil() is True  # . (dot)
    assert gsm.Separator.WS_ALLOWED.can_be_nil() is True  # , (comma)
    assert gsm.Separator.WS_REQUIRED.can_be_nil() is False  # : (colon)


def test_item_nil_detection_with_quantifiers():
    """Test item nil detection with different quantifiers."""
    grammar = gsm.Grammar(rules=[], identifiers={})

    # Required item with empty literal: nil because the term is nullable
    required_item = gsm.Item(
        label=None,
        disposition=gsm.Disposition.INCLUDE,
        term=gsm.Literal(""),  # Empty literal — term is nullable
        quantifier=gsm.REQUIRED,
    )
    assert required_item.can_be_nil(grammar) is True

    # Optional item (always nil regardless of term)
    optional_item = gsm.Item(
        label=None,
        disposition=gsm.Disposition.INCLUDE,
        term=gsm.Literal("required"),  # Even required literal
        quantifier=gsm.NOT_REQUIRED,
    )
    assert optional_item.can_be_nil(grammar) is True

    # Zero-or-more item (always nil regardless of term)
    zero_or_more_item = gsm.Item(
        label=None,
        disposition=gsm.Disposition.INCLUDE,
        term=gsm.Literal("required"),
        quantifier=gsm.ZERO_OR_MORE,
    )
    assert zero_or_more_item.can_be_nil(grammar) is True

    # One-or-more item with empty literal: nil because the term is nullable (empty match on first iteration)
    one_or_more_item = gsm.Item(
        label=None,
        disposition=gsm.Disposition.INCLUDE,
        term=gsm.Literal(""),  # Empty literal — term is nullable
        quantifier=gsm.ONE_OR_MORE,
    )
    assert one_or_more_item.can_be_nil(grammar) is True


def test_memoization():
    """Test that nil detection results are memoized."""
    grammar = gsm.Grammar(rules=[], identifiers={})

    regex = gsm.Regex(r"a*")

    # First call should compute and cache
    result1 = regex.can_be_nil(grammar)

    # Second call should use cached result
    result2 = regex.can_be_nil(grammar)

    assert result1 == result2 is True

    # Check that result is cached on the object itself
    assert regex._can_be_nil is True

    # Test with a different regex that should not be nil
    regex2 = gsm.Regex(r"a+")
    result3 = regex2.can_be_nil(grammar)
    assert result3 is False
    assert regex2._can_be_nil is False
