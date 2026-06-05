from __future__ import annotations

import ast
from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from fltk.fegen import fltk_cst as _default_cst
from fltk.fegen import gsm

if TYPE_CHECKING:
    from fltk.fegen import fltk_cst_protocol as cst

# Module-level sentinel: cast _default_cst to the Protocol type so the __init__
# default does not trigger B008 (no function call in default argument position).
# The cast is needed because fltk_cst.Grammar.Label (and other nested Labels) are
# concrete enum subclasses, not assignable to the Protocol's nested Label class
# (pyright treats nested classes nominally, not structurally).
_DEFAULT_CST: cst.CstModule = cast("cst.CstModule", _default_cst)


class Cst2Gsm:
    def __init__(self, terminals, cst: cst.CstModule = _DEFAULT_CST):
        self.terminals = terminals
        self.cst = cst

    def visit_grammar(self, grammar: cst.Grammar) -> gsm.Grammar:
        rules = [self.visit_rule(rule) for rule in grammar.children_rule()]
        return gsm.Grammar(rules=rules, identifiers={rule.name: rule for rule in rules})

    def visit_rule(self, rule: cst.Rule) -> gsm.Rule:
        return gsm.Rule(
            name=self.visit_identifier(rule.child_name()).value,
            alternatives=self.visit_alternatives(rule.child_alternatives()),
        )

    def visit_identifier(self, identifier: cst.Identifier) -> gsm.Identifier:
        span = identifier.child_name()
        return gsm.Identifier(self.terminals[span.start : span.end])

    def visit_alternatives(self, alternatives: cst.Alternatives) -> list[gsm.Items]:
        return [self.visit_items(items) for items in alternatives.children_items()]

    def visit_items(self, items: cst.Items) -> gsm.Items:
        gsm_items = []
        sep_after = []
        initial_sep = gsm.Separator.NO_WS

        labeled_children = items.children

        # Check if there's a leading separator
        start_idx = 0
        if labeled_children and labeled_children[0][0] in (
            self.cst.Items.Label.NO_WS,
            self.cst.Items.Label.WS_ALLOWED,
            self.cst.Items.Label.WS_REQUIRED,
        ):
            sep_label, _ = labeled_children[0]
            if sep_label == self.cst.Items.Label.WS_REQUIRED:
                initial_sep = gsm.Separator.WS_REQUIRED
            elif sep_label == self.cst.Items.Label.WS_ALLOWED:
                initial_sep = gsm.Separator.WS_ALLOWED
            else:
                initial_sep = gsm.Separator.NO_WS
            start_idx = 1

        # Process items and separators (interleaved ITEM / separator pairs)
        children = labeled_children[start_idx:]
        for (item_label, item), (sep_label, _) in zip(children[::2], children[1::2], strict=False):
            assert item_label == self.cst.Items.Label.ITEM and isinstance(item, self.cst.Item)  # noqa: S101
            gsm_items.append(self.visit_item(item))
            if sep_label == self.cst.Items.Label.WS_REQUIRED:
                sep_after.append(gsm.Separator.WS_REQUIRED)
            elif sep_label == self.cst.Items.Label.WS_ALLOWED:
                sep_after.append(gsm.Separator.WS_ALLOWED)
            else:
                assert sep_label == self.cst.Items.Label.NO_WS  # noqa: S101
                sep_after.append(gsm.Separator.NO_WS)
        if (len(children) % 2) != 0:
            item_label, item = children[-1]
            assert item_label == self.cst.Items.Label.ITEM and isinstance(item, self.cst.Item)  # noqa: S101
            gsm_items.append(self.visit_item(item))
            sep_after.append(gsm.Separator.NO_WS)
        assert len(gsm_items) == len(sep_after)  # noqa: S101
        return gsm.Items(items=gsm_items, sep_after=sep_after, initial_sep=initial_sep)

    def visit_item(self, item: cst.Item) -> gsm.Item:
        term = self.visit_term(item.child_term())

        # cst_label is a raw CST node; visit_identifier reads only span offsets off it,
        # so no self.cst isinstance dispatch is needed here.
        label = self.visit_identifier(cst_label).value if (cst_label := item.maybe_label()) else None
        if label is None and isinstance(term, gsm.Identifier):
            label = term.value

        disposition = self.visit_disposition(cst_disposition) if (cst_disposition := item.maybe_disposition()) else None
        if disposition is None:
            if label or isinstance(term, Sequence):
                disposition = gsm.Disposition.INCLUDE
            else:
                disposition = gsm.Disposition.SUPPRESS

        quantifier = (
            self.visit_quantifier(cst_quantifier) if (cst_quantifier := item.maybe_quantifier()) else gsm.REQUIRED
        )

        return gsm.Item(label=label, disposition=disposition, term=term, quantifier=quantifier)

    def visit_term(self, term: cst.Term) -> gsm.Term:
        if alternatives := term.maybe_alternatives():
            return self.visit_alternatives(alternatives)
        if identifier := term.maybe_identifier():
            return self.visit_identifier(identifier)
        if literal := term.maybe_literal():
            return self.visit_literal(literal)
        if regex := term.maybe_regex():
            return self.visit_regex(regex)
        msg = f"Unsupported term type: {term}"
        raise NotImplementedError(msg)

    def visit_disposition(self, disposition: cst.Disposition) -> gsm.Disposition:
        label, _ = disposition.child()
        if label == self.cst.Disposition.Label.INCLUDE:
            return gsm.Disposition.INCLUDE
        if label == self.cst.Disposition.Label.SUPPRESS:
            return gsm.Disposition.SUPPRESS
        if label == self.cst.Disposition.Label.INLINE:
            return gsm.Disposition.INLINE
        msg = f"Unsupported disposition: {disposition}"
        raise NotImplementedError(msg)

    def visit_quantifier(self, quantifier: cst.Quantifier) -> gsm.Quantifier:
        label, _ = quantifier.child()
        if label == self.cst.Quantifier.Label.ONE_OR_MORE:
            return gsm.ONE_OR_MORE
        if label == self.cst.Quantifier.Label.OPTIONAL:
            return gsm.NOT_REQUIRED
        if label == self.cst.Quantifier.Label.ZERO_OR_MORE:
            return gsm.ZERO_OR_MORE
        msg = f"Unsupported quantifier: {quantifier}"
        raise NotImplementedError(msg)

    def visit_literal(self, literal: cst.Literal) -> gsm.Literal:
        span = literal.child_value()
        return gsm.Literal(ast.literal_eval(self.terminals[span.start : span.end]))

    def visit_regex(self, regex: cst.RawString) -> gsm.Regex:
        span = regex.child_value()
        return gsm.Regex(self.terminals[span.start : span.end])
