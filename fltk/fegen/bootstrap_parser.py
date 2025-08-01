import collections.abc
import typing

import fltk.fegen.pyrt.errors
import fltk.fegen.pyrt.memo
import fltk.fegen.pyrt.terminalsrc
from fltk.fegen import bootstrap_cst


class Parser:
    """Parser"""

    def __init__(self, terminalsrc: fltk.fegen.pyrt.terminalsrc.TerminalSource) -> None:
        self.terminalsrc = terminalsrc
        self.packrat: fltk.fegen.pyrt.memo.Packrat = fltk.fegen.pyrt.memo.Packrat()
        self.error_tracker: fltk.fegen.pyrt.errors.ErrorTracker[int] = fltk.fegen.pyrt.errors.ErrorTracker()
        self.rule_names: typing.Sequence[str] = [
            "grammar",
            "rule",
            "alternatives",
            "items",
            "item",
            "term",
            "disposition",
            "quantifier",
            "identifier",
            "raw_string",
            "literal",
        ]
        self._cache__parse_grammar: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, bootstrap_cst.Grammar]
        ] = {}
        self._cache__parse_rule: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, bootstrap_cst.Rule]
        ] = {}
        self._cache__parse_alternatives: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, bootstrap_cst.Alternatives]
        ] = {}
        self._cache__parse_items: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, bootstrap_cst.Items]
        ] = {}
        self._cache__parse_item: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, bootstrap_cst.Item]
        ] = {}
        self._cache__parse_term: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, bootstrap_cst.Term]
        ] = {}
        self._cache__parse_disposition: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, bootstrap_cst.Disposition]
        ] = {}
        self._cache__parse_quantifier: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, bootstrap_cst.Quantifier]
        ] = {}
        self._cache__parse_identifier: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, bootstrap_cst.Identifier]
        ] = {}
        self._cache__parse_raw_string: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, bootstrap_cst.RawString]
        ] = {}
        self._cache__parse_literal: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, bootstrap_cst.Literal]
        ] = {}

    def consume_literal(
        self, pos: int, literal: str
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        if span := self.terminalsrc.consume_literal(pos=pos, literal=literal):
            return fltk.fegen.pyrt.memo.ApplyResult(pos=span.end, result=span)
        self.error_tracker.fail_literal(pos=pos, rule_id=self.packrat.invocation_stack[-1], literal=literal)
        return None

    def consume_regex(
        self, pos: int, regex: str
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        if span := self.terminalsrc.consume_regex(pos=pos, regex=regex):
            return fltk.fegen.pyrt.memo.ApplyResult(pos=span.end, result=span)
        self.error_tracker.fail_regex(pos=pos, rule_id=self.packrat.invocation_stack[-1], regex=regex)
        return None

    def parse_grammar(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Grammar] | None:
        if alt0 := self.parse_grammar__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_grammar(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Grammar] | None:
        return self.packrat.apply(
            rule_callable=self.parse_grammar, rule_id=0, rule_cache=self._cache__parse_grammar, pos=pos
        )

    def parse_grammar__alt0(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Grammar] | None:
        result: bootstrap_cst.Grammar = bootstrap_cst.Grammar(span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1))
        if item0 := self.parse_grammar__alt0__item0(pos=pos):
            pos = item0.pos
            result.children.extend(item0.result.children)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_grammar__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Grammar] | None:
        result: bootstrap_cst.Grammar = bootstrap_cst.Grammar(span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1))
        while one_result := self.apply__parse_rule(pos=pos):
            pos = one_result.pos
            result.append_rule(child=one_result.result)
            if len(result.children) == 0:
                return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Rule] | None:
        if alt0 := self.parse_rule__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_rule(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Rule] | None:
        return self.packrat.apply(rule_callable=self.parse_rule, rule_id=1, rule_cache=self._cache__parse_rule, pos=pos)

    def parse_rule__alt0(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Rule] | None:
        result: bootstrap_cst.Rule = bootstrap_cst.Rule(span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1))
        if item0 := self.parse_rule__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_name(child=item0.result)
        else:
            return None
        if ws_after__item0 := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__item0.pos
        if item1 := self.parse_rule__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if ws_after__item1 := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__item1.pos
        if item2 := self.parse_rule__alt0__item2(pos=pos):
            pos = item2.pos
            result.append_alternatives(child=item2.result)
        else:
            return None
        if ws_after__item2 := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__item2.pos
        if item3 := self.parse_rule__alt0__item3(pos=pos):
            pos = item3.pos
        else:
            return None
        if ws_after__item3 := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__item3.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Identifier] | None:
        return self.apply__parse_identifier(pos=pos)

    def parse_rule__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=":=")

    def parse_rule__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Alternatives] | None:
        return self.apply__parse_alternatives(pos=pos)

    def parse_rule__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_alternatives(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Alternatives] | None:
        if alt0 := self.parse_alternatives__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_alternatives(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Alternatives] | None:
        return self.packrat.apply(
            rule_callable=self.parse_alternatives, rule_id=2, rule_cache=self._cache__parse_alternatives, pos=pos
        )

    def parse_alternatives__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Alternatives] | None:
        result: bootstrap_cst.Alternatives = bootstrap_cst.Alternatives(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_alternatives__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_items(child=item0.result)
        else:
            return None
        if ws_after__item0 := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__item0.pos
        if item1 := self.parse_alternatives__alt0__item1(pos=pos):
            pos = item1.pos
            result.children.extend(item1.result.children)
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_alternatives__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items] | None:
        return self.apply__parse_items(pos=pos)

    def parse_alternatives__alt0__item1__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Alternatives] | None:
        if alt0 := self.parse_alternatives__alt0__item1__alts__alt0(pos=pos):
            return alt0
        return None

    def parse_alternatives__alt0__item1__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Alternatives] | None:
        result: bootstrap_cst.Alternatives = bootstrap_cst.Alternatives(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_alternatives__alt0__item1__alts__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__item0.pos
        if item1 := self.parse_alternatives__alt0__item1__alts__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_items(child=item1.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_alternatives__alt0__item1__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="|")

    def parse_alternatives__alt0__item1__alts__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items] | None:
        return self.apply__parse_items(pos=pos)

    def parse_alternatives__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Alternatives] | None:
        result: bootstrap_cst.Alternatives = bootstrap_cst.Alternatives(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        while one_result := self.parse_alternatives__alt0__item1__alts(pos=pos):
            pos = one_result.pos
            result.children.extend(one_result.result.children)
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_items(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items] | None:
        if alt0 := self.parse_items__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_items(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items] | None:
        return self.packrat.apply(
            rule_callable=self.parse_items, rule_id=3, rule_cache=self._cache__parse_items, pos=pos
        )

    def parse_items__alt0(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items] | None:
        result: bootstrap_cst.Items = bootstrap_cst.Items(span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1))
        if item0 := self.parse_items__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_item(child=item0.result)
        else:
            return None
        if ws_after__item0 := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__item0.pos
        if item1 := self.parse_items__alt0__item1(pos=pos):
            pos = item1.pos
            result.children.extend(item1.result.children)
        if ws_after__item1 := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__item1.pos
        if item2 := self.parse_items__alt0__item2(pos=pos):
            pos = item2.pos
            result.children.extend(item2.result.children)
        if ws_after__item2 := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__item2.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_items__alt0__item0(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Item] | None:
        return self.apply__parse_item(pos=pos)

    def parse_items__alt0__item1__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items] | None:
        if alt0 := self.parse_items__alt0__item1__alts__alt0(pos=pos):
            return alt0
        return None

    def parse_items__alt0__item1__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items] | None:
        result: bootstrap_cst.Items = bootstrap_cst.Items(span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1))
        if item0 := self.parse_items__alt0__item1__alts__alt0__item0(pos=pos):
            pos = item0.pos
            result.children.extend(item0.result.children)
        else:
            return None
        if ws_after__item0 := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__item0.pos
        if item1 := self.parse_items__alt0__item1__alts__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_item(child=item1.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_items__alt0__item1__alts__alt0__item0__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items] | None:
        if alt0 := self.parse_items__alt0__item1__alts__alt0__item0__alts__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_items__alt0__item1__alts__alt0__item0__alts__alt1(pos=pos):
            return alt1
        return None

    def parse_items__alt0__item1__alts__alt0__item0__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items] | None:
        result: bootstrap_cst.Items = bootstrap_cst.Items(span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1))
        if item0 := self.parse_items__alt0__item1__alts__alt0__item0__alts__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_no_ws(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_items__alt0__item1__alts__alt0__item0__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=".")

    def parse_items__alt0__item1__alts__alt0__item0__alts__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items] | None:
        result: bootstrap_cst.Items = bootstrap_cst.Items(span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1))
        if item0 := self.parse_items__alt0__item1__alts__alt0__item0__alts__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_ws(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_items__alt0__item1__alts__alt0__item0__alts__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=",")

    def parse_items__alt0__item1__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items] | None:
        return self.parse_items__alt0__item1__alts__alt0__item0__alts(pos=pos)

    def parse_items__alt0__item1__alts__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Item] | None:
        return self.apply__parse_item(pos=pos)

    def parse_items__alt0__item1(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items] | None:
        result: bootstrap_cst.Items = bootstrap_cst.Items(span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1))
        while one_result := self.parse_items__alt0__item1__alts(pos=pos):
            pos = one_result.pos
            result.children.extend(one_result.result.children)
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_items__alt0__item2__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items] | None:
        if alt0 := self.parse_items__alt0__item2__alts__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_items__alt0__item2__alts__alt1(pos=pos):
            return alt1
        return None

    def parse_items__alt0__item2__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items] | None:
        result: bootstrap_cst.Items = bootstrap_cst.Items(span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1))
        if item0 := self.parse_items__alt0__item2__alts__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_no_ws(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_items__alt0__item2__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=".")

    def parse_items__alt0__item2__alts__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items] | None:
        result: bootstrap_cst.Items = bootstrap_cst.Items(span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1))
        if item0 := self.parse_items__alt0__item2__alts__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_ws(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_items__alt0__item2__alts__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=",")

    def parse_items__alt0__item2(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items] | None:
        return self.parse_items__alt0__item2__alts(pos=pos)

    def parse_item(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Item] | None:
        if alt0 := self.parse_item__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_item(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Item] | None:
        return self.packrat.apply(rule_callable=self.parse_item, rule_id=4, rule_cache=self._cache__parse_item, pos=pos)

    def parse_item__alt0(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Item] | None:
        result: bootstrap_cst.Item = bootstrap_cst.Item(span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1))
        if item0 := self.parse_item__alt0__item0(pos=pos):
            pos = item0.pos
            result.children.extend(item0.result.children)
        if item1 := self.parse_item__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_disposition(child=item1.result)
        if item2 := self.parse_item__alt0__item2(pos=pos):
            pos = item2.pos
            result.append_term(child=item2.result)
        else:
            return None
        if item3 := self.parse_item__alt0__item3(pos=pos):
            pos = item3.pos
            result.append_quantifier(child=item3.result)
        if ws_after__item3 := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__item3.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_item__alt0__item0__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Item] | None:
        if alt0 := self.parse_item__alt0__item0__alts__alt0(pos=pos):
            return alt0
        return None

    def parse_item__alt0__item0__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Item] | None:
        result: bootstrap_cst.Item = bootstrap_cst.Item(span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1))
        if item0 := self.parse_item__alt0__item0__alts__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_label(child=item0.result)
        else:
            return None
        if item1 := self.parse_item__alt0__item0__alts__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_item__alt0__item0__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Identifier] | None:
        return self.apply__parse_identifier(pos=pos)

    def parse_item__alt0__item0__alts__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=":")

    def parse_item__alt0__item0(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Item] | None:
        return self.parse_item__alt0__item0__alts(pos=pos)

    def parse_item__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Disposition] | None:
        return self.apply__parse_disposition(pos=pos)

    def parse_item__alt0__item2(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Term] | None:
        return self.apply__parse_term(pos=pos)

    def parse_item__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Quantifier] | None:
        return self.apply__parse_quantifier(pos=pos)

    def parse_term(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Term] | None:
        if alt0 := self.parse_term__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_term__alt1(pos=pos):
            return alt1
        if alt2 := self.parse_term__alt2(pos=pos):
            return alt2
        if alt3 := self.parse_term__alt3(pos=pos):
            return alt3
        return None

    def apply__parse_term(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Term] | None:
        return self.packrat.apply(rule_callable=self.parse_term, rule_id=5, rule_cache=self._cache__parse_term, pos=pos)

    def parse_term__alt0(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Term] | None:
        result: bootstrap_cst.Term = bootstrap_cst.Term(span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1))
        if item0 := self.parse_term__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_identifier(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_term__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Identifier] | None:
        return self.apply__parse_identifier(pos=pos)

    def parse_term__alt1(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Term] | None:
        result: bootstrap_cst.Term = bootstrap_cst.Term(span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1))
        if item0 := self.parse_term__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_literal(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_term__alt1__item0(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Literal] | None:
        return self.apply__parse_literal(pos=pos)

    def parse_term__alt2(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Term] | None:
        result: bootstrap_cst.Term = bootstrap_cst.Term(span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1))
        if item0 := self.parse_term__alt2__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if item1 := self.parse_term__alt2__item1(pos=pos):
            pos = item1.pos
            result.append_regex(child=item1.result)
        else:
            return None
        if item2 := self.parse_term__alt2__item2(pos=pos):
            pos = item2.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_term__alt2__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="/")

    def parse_term__alt2__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.RawString] | None:
        return self.apply__parse_raw_string(pos=pos)

    def parse_term__alt2__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="/")

    def parse_term__alt3(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Term] | None:
        result: bootstrap_cst.Term = bootstrap_cst.Term(span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1))
        if item0 := self.parse_term__alt3__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__item0.pos
        if item1 := self.parse_term__alt3__item1(pos=pos):
            pos = item1.pos
            result.append_alternatives(child=item1.result)
        else:
            return None
        if ws_after__item1 := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__item1.pos
        if item2 := self.parse_term__alt3__item2(pos=pos):
            pos = item2.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_term__alt3__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="(")

    def parse_term__alt3__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Alternatives] | None:
        return self.apply__parse_alternatives(pos=pos)

    def parse_term__alt3__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=")")

    def parse_disposition(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Disposition] | None:
        if alt0 := self.parse_disposition__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_disposition__alt1(pos=pos):
            return alt1
        if alt2 := self.parse_disposition__alt2(pos=pos):
            return alt2
        return None

    def apply__parse_disposition(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Disposition] | None:
        return self.packrat.apply(
            rule_callable=self.parse_disposition, rule_id=6, rule_cache=self._cache__parse_disposition, pos=pos
        )

    def parse_disposition__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Disposition] | None:
        result: bootstrap_cst.Disposition = bootstrap_cst.Disposition(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_disposition__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_suppress(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_disposition__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="%")

    def parse_disposition__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Disposition] | None:
        result: bootstrap_cst.Disposition = bootstrap_cst.Disposition(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_disposition__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_include(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_disposition__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="$")

    def parse_disposition__alt2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Disposition] | None:
        result: bootstrap_cst.Disposition = bootstrap_cst.Disposition(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_disposition__alt2__item0(pos=pos):
            pos = item0.pos
            result.append_inline(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_disposition__alt2__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="!")

    def parse_quantifier(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Quantifier] | None:
        if alt0 := self.parse_quantifier__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_quantifier__alt1(pos=pos):
            return alt1
        if alt2 := self.parse_quantifier__alt2(pos=pos):
            return alt2
        return None

    def apply__parse_quantifier(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Quantifier] | None:
        return self.packrat.apply(
            rule_callable=self.parse_quantifier, rule_id=7, rule_cache=self._cache__parse_quantifier, pos=pos
        )

    def parse_quantifier__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Quantifier] | None:
        result: bootstrap_cst.Quantifier = bootstrap_cst.Quantifier(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_quantifier__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_optional(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_quantifier__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="?")

    def parse_quantifier__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Quantifier] | None:
        result: bootstrap_cst.Quantifier = bootstrap_cst.Quantifier(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_quantifier__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_one_or_more(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_quantifier__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="+")

    def parse_quantifier__alt2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Quantifier] | None:
        result: bootstrap_cst.Quantifier = bootstrap_cst.Quantifier(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_quantifier__alt2__item0(pos=pos):
            pos = item0.pos
            result.append_zero_or_more(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_quantifier__alt2__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="*")

    def parse_identifier(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Identifier] | None:
        if alt0 := self.parse_identifier__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_identifier(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Identifier] | None:
        return self.packrat.apply(
            rule_callable=self.parse_identifier, rule_id=8, rule_cache=self._cache__parse_identifier, pos=pos
        )

    def parse_identifier__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Identifier] | None:
        result: bootstrap_cst.Identifier = bootstrap_cst.Identifier(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_identifier__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_name(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_identifier__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_regex(pos=pos, regex="[_a-z][_a-z0-9]*")

    def parse_raw_string(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.RawString] | None:
        if alt0 := self.parse_raw_string__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_raw_string(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.RawString] | None:
        return self.packrat.apply(
            rule_callable=self.parse_raw_string, rule_id=9, rule_cache=self._cache__parse_raw_string, pos=pos
        )

    def parse_raw_string__alt0(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.RawString] | None:
        result: bootstrap_cst.RawString = bootstrap_cst.RawString(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_raw_string__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_value(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_raw_string__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_regex(pos=pos, regex="([^\\/\\n\\\\]|\\\\.)+")

    def parse_literal(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Literal] | None:
        if alt0 := self.parse_literal__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_literal(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Literal] | None:
        return self.packrat.apply(
            rule_callable=self.parse_literal, rule_id=10, rule_cache=self._cache__parse_literal, pos=pos
        )

    def parse_literal__alt0(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Literal] | None:
        result: bootstrap_cst.Literal = bootstrap_cst.Literal(span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1))
        if item0 := self.parse_literal__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_value(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_literal__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_regex(pos=pos, regex="(\"([^\"\\n\\\\]|\\\\.)+\"|'([^'\\n\\\\]|\\\\.)+')")
