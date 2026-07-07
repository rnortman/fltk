"""Analysis-grammar transform for the classification engine.

The runtime parser omits ``SUPPRESS``-disposition items from the CST, so terminals
that default to suppression (unlabeled literals and regexes) never reach the tree and
their spans become gaps in the parent node's span.  ``prepare_analysis_grammar`` returns
a structurally identical grammar in which every ``SUPPRESS`` item is promoted to
``INCLUDE``: it parses exactly the same language with exactly the same spans, but its CST
carries a child for every terminal the parser touched.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence

from fltk.fegen import gsm


def prepare_analysis_grammar(grammar: gsm.Grammar) -> gsm.Grammar:
    """Return ``grammar`` with every ``SUPPRESS`` disposition promoted to ``INCLUDE``.

    Recurses through ``Sequence[Items]`` sub-expressions and across all rules.  The
    resulting grammar matches the identical language with identical spans, but its CST
    contains a child for every terminal and subtree the parser consumed.

    Raises ``ValueError`` if any item uses the ``INLINE`` (``!``) disposition, which no
    ``plumbing.generate_parser``-based engine supports.
    """
    inline_rules = _find_inline_rules(grammar)
    if inline_rules:
        rule_list = ", ".join(sorted(inline_rules))
        msg = f"grammar uses `!` (inline), not supported by the analysis engine (rules: {rule_list})"
        raise ValueError(msg)

    new_rules = [_transform_rule(rule) for rule in grammar.rules]
    return dataclasses.replace(
        grammar,
        rules=new_rules,
        identifiers={rule.name: rule for rule in new_rules},
    )


def _find_inline_rules(grammar: gsm.Grammar) -> set[str]:
    """Collect the names of rules containing an ``INLINE``-disposition item."""
    return {rule.name for rule in grammar.rules if _rule_uses_inline(rule)}


def _rule_uses_inline(rule: gsm.Rule) -> bool:
    found = False

    def visit(_idx: int, item: gsm.Item) -> None:
        nonlocal found
        if item.disposition == gsm.Disposition.INLINE:
            found = True

    for alt in rule.alternatives:
        gsm.for_each_item(alt, visit)

    return found


def _transform_rule(rule: gsm.Rule) -> gsm.Rule:
    new_alternatives = [_transform_items(alt) for alt in rule.alternatives]
    return dataclasses.replace(rule, alternatives=new_alternatives)


def _transform_items(items: gsm.Items) -> gsm.Items:
    new_items = [_transform_item(item) for item in items.items]
    return dataclasses.replace(items, items=new_items)


def _transform_item(item: gsm.Item) -> gsm.Item:
    term = item.term
    if isinstance(term, Sequence):
        term = [_transform_items(alt) for alt in term]

    disposition = item.disposition
    if disposition == gsm.Disposition.SUPPRESS:
        disposition = gsm.Disposition.INCLUDE

    return dataclasses.replace(item, disposition=disposition, term=term)
