from collections.abc import Sequence

import bootstrap_cst as cst
from fltk.fegen import gsm


class Cst2Gsm:
    def __init__(self, terminals):
        self.terminals = terminals

    def visit_grammar(self, grammar: cst.Grammar) -> gsm.Grammar:
        rules = [self.visit_rule(rule) for rule in grammar.children_rule()]
        return gsm.Grammar(
            rules=rules, vars=[], identifiers={rule.name: rule for rule in rules}
        )

    def visit_rule(self, rule: cst.Rule) -> gsm.Rule:
        return gsm.Rule(
            name=self.visit_identifier(rule.child_name()).value,
            alternatives=self.visit_alternatives(rule.child_alternatives()),
        )

    def visit_identifier(self, identifier: cst.Identifier) -> gsm.Identifier:
        span = identifier.child_name()
        return gsm.Identifier(self.terminals[span.start : span.end])

    def visit_alternatives(self, alternatives: cst.Alternatives) -> list[gsm.Items]:
        return list(self.visit_items(items) for items in alternatives.children_items())

    def visit_items(self, items: cst.Items) -> gsm.Items:
        gsm_items = []
        ws_after = []
        for (item_label, item), (ws_label, ws) in zip(
            items.children[::2], items.children[1::2]
        ):
            assert item_label == cst.Items.Label.item and isinstance(item, cst.Item)
            gsm_items.append(self.visit_item(item))
            if ws_label == cst.Items.Label.ws:
                ws_after.append(True)
            else:
                assert ws_label == cst.Items.Label.no_ws
                ws_after.append(False)
        if (len(items.children) % 2) != 0:
            item_label, item = items.children[-1]
            assert item_label == cst.Items.Label.item and isinstance(item, cst.Item)
            gsm_items.append(self.visit_item(item))
            ws_after.append(False)
        assert len(gsm_items) == len(ws_after)
        return gsm.Items(items=gsm_items, ws_after=ws_after)

    def visit_item(self, item: cst.Item) -> gsm.Item:
        term = self.visit_term(item.child_term())

        label = (
            self.visit_identifier(cst_label).value
            if (cst_label := item.maybe_label())
            else None
        )
        if label is None and isinstance(term, gsm.Identifier):
            label = term.value

        disposition = (
            self.visit_disposition(cst_disposition)
            if (cst_disposition := item.maybe_disposition())
            else None
        )
        if disposition is None:
            if label or isinstance(term, Sequence):
                disposition = gsm.Disposition.INCLUDE
            else:
                disposition = gsm.Disposition.SUPPRESS

        quantifier = (
            self.visit_quantifier(cst_quantifier)
            if (cst_quantifier := item.maybe_quantifier())
            else gsm.REQUIRED
        )

        return gsm.Item(
            label=label, disposition=disposition, term=term, quantifier=quantifier
        )

    def visit_term(self, term: cst.Term) -> gsm.Term:
        if alternatives := term.maybe_alternatives():
            return self.visit_alternatives(alternatives)
        if identifier := term.maybe_identifier():
            return self.visit_identifier(identifier)
        if literal := term.maybe_literal():
            return self.visit_literal(literal)
        if regex := term.maybe_regex():
            return self.visit_regex(regex)
        raise NotImplementedError(f"Unsupported term type: {term}")

    def visit_disposition(self, disposition: cst.Disposition) -> gsm.Disposition:
        label, _ = disposition.child()
        if label == cst.Disposition.Label.include:
            return gsm.Disposition.INCLUDE
        if label == cst.Disposition.Label.suppress:
            return gsm.Disposition.SUPPRESS
        if label == cst.Disposition.Label.inline:
            return gsm.Disposition.INLINE
        raise NotImplementedError(f"Unsupported disposition: {disposition}")

    def visit_quantifier(self, quantifier: cst.Quantifier) -> gsm.Quantifier:
        label, _ = quantifier.child()
        if label == cst.Quantifier.Label.one_or_more:
            return gsm.ONE_OR_MORE
        if label == cst.Quantifier.Label.optional:
            return gsm.NOT_REQUIRED
        if label == cst.Quantifier.Label.zero_or_more:
            return gsm.ZERO_OR_MORE
        raise NotImplementedError(f"Unsupported quantifier: {quantifier}")

    def visit_literal(self, literal: cst.Literal) -> gsm.Literal:
        span = literal.child_value()
        return gsm.Literal(eval(self.terminals[span.start : span.end]))

    def visit_regex(self, regex: cst.RawString) -> gsm.Regex:
        span = regex.child_value()
        return gsm.Regex(self.terminals[span.start : span.end])
