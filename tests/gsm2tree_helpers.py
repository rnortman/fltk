"""Shared grammar construction helpers for gsm2tree generator tests.

Used by test_gsm2tree_py.py and test_gsm2tree_rs.py so both files exercise
the same boundary conditions and generator-construction changes propagate to both.
"""

from __future__ import annotations

from fltk.fegen import gsm
from fltk.fegen.gsm2tree import CstGenerator
from fltk.iir.context import create_default_context
from fltk.iir.py import reg as pyreg


def make_zero_label_grammar() -> gsm.Grammar:
    """Grammar with a single rule whose only included items have no label.

    foo := $"x"."y";  -- $-disposition, no label, NO_WS separators throughout
    so labels={} after model_for_rule and no trivia injection.
    """
    rule = gsm.Rule(
        name="foo",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("x"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("y"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS, gsm.Separator.NO_WS],
            ),
        ],
    )
    return gsm.Grammar(rules=(rule,), identifiers={"foo": rule})


def make_labeled_grammar() -> gsm.Grammar:
    """Grammar with a single rule whose item has a label."""
    rule = gsm.Rule(
        name="bar",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="name",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[a-z]+"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
        ],
    )
    return gsm.Grammar(rules=(rule,), identifiers={"bar": rule})


def make_multi_label_grammar() -> gsm.Grammar:
    """Grammar with a single rule carrying three distinct labels.

    A one-label rule cannot distinguish a correct canonical-name → member pairing from one that
    collapses every name onto the first member, so generator shape pins on the label mapping need
    a rule with several labels.
    """
    rule = gsm.Rule(
        name="bar",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=label,
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[a-z]+"),
                        quantifier=gsm.REQUIRED,
                    )
                    for label in ("name", "value", "tail")
                ],
                sep_after=[gsm.Separator.NO_WS] * 3,
            ),
        ],
    )
    return gsm.Grammar(rules=(rule,), identifiers={"bar": rule})


def make_rule_ref_grammar(*, labeled: bool) -> gsm.Grammar:
    """``foo := $"x"."y";`` plus a rule referencing it, with or without a label."""
    foo = make_zero_label_grammar().rules[0]
    ref = gsm.Rule(
        name="baz",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="inner" if labeled else None,
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier("foo"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
        ],
    )
    return gsm.Grammar(rules=(foo, ref), identifiers={"foo": foo, "baz": ref})


def make_generator(grammar: gsm.Grammar) -> CstGenerator:
    """Construct a CstGenerator with default context and Python builtins module."""
    return CstGenerator(grammar=grammar, py_module=pyreg.Builtins, context=create_default_context())
