"""Regression test for separators in sub-expressions bug

This test verifies that rule_has_whitespace_separators correctly detects
separators inside sub-expressions (parentheses), not just at the top level.

The bug occurs in gsm2tree.py lines 49-59 where rule_has_whitespace_separators
only checks separators at the top level of rule alternatives. For rules like:
    _trivia := (line_comment? ,)+;

The comma separator is inside the parenthesized sub-expression, so the method
returns False. This causes _trivia to not be added to its own model types,
resulting in Trivia.append() only accepting LineComment objects instead of
also accepting Trivia objects.

This leads to a runtime error in the generated parser when trying to append
a Trivia result to another Trivia node.
"""

import logging
from typing import Final

from fltk.fegen import gsm, gsm2tree
from fltk.iir.context import create_default_context
from fltk.iir.py import reg as pyreg

LOG: Final = logging.getLogger(__name__)


def test_rule_has_whitespace_separators_with_subexpr():
    """Test that rule_has_whitespace_separators detects separators in sub-expressions.

    This is a direct unit test of the method that has the bug.
    """
    context = create_default_context(capture_trivia=True)

    # Create the problematic _trivia rule: (line_comment? ,)+
    # The comma is inside the sub-expression, not at top level
    trivia_rule = gsm.Rule(
        name="_trivia",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INCLUDE,
                        term=[  # Sub-expression as list of Items
                            gsm.Items(
                                items=[
                                    gsm.Item(
                                        label="line_comment",
                                        disposition=gsm.Disposition.INCLUDE,
                                        term=gsm.Identifier("line_comment"),
                                        quantifier=gsm.NOT_REQUIRED,
                                    ),
                                ],
                                sep_after=[gsm.Separator.WS_ALLOWED],  # Comma separator INSIDE sub-expression
                            ),
                        ],
                        quantifier=gsm.ONE_OR_MORE,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
        ],
    )

    # Create a simple grammar with this rule
    line_comment_rule = gsm.Rule(
        name="line_comment",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="content",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex("//.*"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
        ],
    )

    grammar = gsm.Grammar(
        rules=(trivia_rule, line_comment_rule), identifiers={"_trivia": trivia_rule, "line_comment": line_comment_rule}
    )

    # Create CstGenerator and test the method
    cstgen = gsm2tree.CstGenerator(grammar=grammar, py_module=pyreg.Builtins, context=context)

    # The bug: this returns False because comma is inside sub-expression
    has_ws = cstgen.rule_has_whitespace_separators(trivia_rule)

    # This assertion will FAIL with the current buggy code
    assert has_ws, (
        "rule_has_whitespace_separators should return True for _trivia rule "
        "because it contains a WS_ALLOWED separator (comma) inside the sub-expression"
    )


def test_control_cases():
    """Test control cases to ensure our detection works correctly."""
    context = create_default_context(capture_trivia=True)

    # Test 1: Rule with top-level separator (should return True)
    rule_with_toplevel_sep = gsm.Rule(
        name="test1",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="a",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("a"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="b",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("b"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.WS_ALLOWED, gsm.Separator.NO_WS],  # Comma at top level
            ),
        ],
    )

    # Test 2: Rule with no separators anywhere (should return False)
    rule_no_sep = gsm.Rule(
        name="test2",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INCLUDE,
                        term=[  # Sub-expression without separators
                            gsm.Items(
                                items=[
                                    gsm.Item(
                                        label="a",
                                        disposition=gsm.Disposition.INCLUDE,
                                        term=gsm.Identifier("a"),
                                        quantifier=gsm.REQUIRED,
                                    ),
                                    gsm.Item(
                                        label="b",
                                        disposition=gsm.Disposition.INCLUDE,
                                        term=gsm.Identifier("b"),
                                        quantifier=gsm.REQUIRED,
                                    ),
                                ],
                                sep_after=[gsm.Separator.NO_WS, gsm.Separator.NO_WS],  # No WS
                            ),
                        ],
                        quantifier=gsm.ONE_OR_MORE,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
        ],
    )

    # Test 3: Rule with initial_sep at top level (should return True)
    rule_with_initial_sep = gsm.Rule(
        name="test3",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="a",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("a"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
                initial_sep=gsm.Separator.WS_REQUIRED,  # Initial sep with WS
            ),
        ],
    )

    dummy_grammar = gsm.Grammar(rules=[], identifiers={})
    cstgen = gsm2tree.CstGenerator(grammar=dummy_grammar, py_module=pyreg.Builtins, context=context)

    # Test the control cases
    assert cstgen.rule_has_whitespace_separators(rule_with_toplevel_sep), (
        "Should return True for rule with top-level WS_ALLOWED separator"
    )

    assert not cstgen.rule_has_whitespace_separators(rule_no_sep), (
        "Should return False for rule with no whitespace separators"
    )

    assert cstgen.rule_has_whitespace_separators(rule_with_initial_sep), (
        "Should return True for rule with WS_REQUIRED initial_sep"
    )
