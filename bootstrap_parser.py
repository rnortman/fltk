import collections.abc
import typing
import fltk.fegen.pyrt.errors
import fltk.fegen.pyrt.memo
import bootstrap_cst


class Parser:
    """Parser"""

    def __init__(self, terminalsrc: fltk.fegen.pyrt.terminalsrc.TerminalSource) -> None:
        self.terminalsrc = terminalsrc
        self.packrat: fltk.fegen.pyrt.memo.Packrat = fltk.fegen.pyrt.memo.Packrat()
        self.error_tracker: fltk.fegen.pyrt.errors.ErrorTracker[
            int
        ] = fltk.fegen.pyrt.errors.ErrorTracker()
        self._cache__parse_grammar: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, bootstrap_cst.Grammar]
        ] = dict()
        self._cache__parse_rule: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, bootstrap_cst.Rule]
        ] = dict()
        self._cache__parse_alternatives: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, bootstrap_cst.Alternatives]
        ] = dict()
        self._cache__parse_items: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, bootstrap_cst.Items]
        ] = dict()
        self._cache__parse_item: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, bootstrap_cst.Item]
        ] = dict()
        self._cache__parse_term: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, bootstrap_cst.Term]
        ] = dict()
        self._cache__parse_disposition: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, bootstrap_cst.Disposition]
        ] = dict()
        self._cache__parse_quantifier: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, bootstrap_cst.Quantifier]
        ] = dict()
        self._cache__parse_identifier: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, bootstrap_cst.Identifier]
        ] = dict()
        self._cache__parse_raw_string: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, bootstrap_cst.RawString]
        ] = dict()
        self._cache__parse_literal: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, bootstrap_cst.Literal]
        ] = dict()

    def consume_literal(
        self, pos: int, literal: str
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]
    ]:
        if span := self.terminalsrc.consume_literal(pos=pos, literal=literal):
            return fltk.fegen.pyrt.memo.ApplyResult(pos=span.end, result=span)
        self.error_tracker.fail_literal(
            pos=pos, rule_id=self.packrat.invocation_stack[-1], literal=literal
        )
        return None

    def consume_regex(
        self, pos: int, regex: str
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]
    ]:
        if span := self.terminalsrc.consume_regex(pos=pos, regex=regex):
            return fltk.fegen.pyrt.memo.ApplyResult(pos=span.end, result=span)
        self.error_tracker.fail_regex(
            pos=pos, rule_id=self.packrat.invocation_stack[-1], regex=regex
        )
        return None

    def parse_grammar(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Grammar]]:
        if alt0 := self.parse_grammar__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_grammar(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Grammar]]:
        return self.packrat.apply(
            rule_callable=self.parse_grammar,
            rule_id=0,
            rule_cache=self._cache__parse_grammar,
            pos=pos,
        )

    def parse_grammar__alt0(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Grammar]]:
        result: bootstrap_cst.Grammar = bootstrap_cst.Grammar(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if rule := self.parse_grammar__alt0__rule(pos=pos):
            pos = rule.pos
            result.children.extend(rule.result.children)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_grammar__alt0__rule(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Grammar]]:
        result: bootstrap_cst.Grammar = bootstrap_cst.Grammar(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        while one_result := self.apply__parse_rule(pos=pos):
            pos = one_result.pos
            result.append_rule(child=one_result.result)
            if len(result.children) == 0:
                return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Rule]]:
        if alt0 := self.parse_rule__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_rule(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Rule]]:
        return self.packrat.apply(
            rule_callable=self.parse_rule,
            rule_id=1,
            rule_cache=self._cache__parse_rule,
            pos=pos,
        )

    def parse_rule__alt0(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Rule]]:
        result: bootstrap_cst.Rule = bootstrap_cst.Rule(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if name := self.parse_rule__alt0__name(pos=pos):
            pos = name.pos
            result.append_name(child=name.result)
        else:
            return None
        if ws_after__name := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__name.pos
        if item1 := self.parse_rule__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if ws_after__item1 := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__item1.pos
        if alternatives := self.parse_rule__alt0__alternatives(pos=pos):
            pos = alternatives.pos
            result.append_alternatives(child=alternatives.result)
        else:
            return None
        if ws_after__alternatives := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__alternatives.pos
        if item3 := self.parse_rule__alt0__item3(pos=pos):
            pos = item3.pos
        else:
            return None
        if ws_after__item3 := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__item3.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule__alt0__name(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Identifier]
    ]:
        return self.apply__parse_identifier(pos=pos)

    def parse_rule__alt0__item1(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]
    ]:
        return self.consume_literal(pos=pos, literal=":=")

    def parse_rule__alt0__alternatives(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Alternatives]
    ]:
        return self.apply__parse_alternatives(pos=pos)

    def parse_rule__alt0__item3(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]
    ]:
        return self.consume_literal(pos=pos, literal=";")

    def parse_alternatives(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Alternatives]
    ]:
        if alt0 := self.parse_alternatives__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_alternatives(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Alternatives]
    ]:
        return self.packrat.apply(
            rule_callable=self.parse_alternatives,
            rule_id=2,
            rule_cache=self._cache__parse_alternatives,
            pos=pos,
        )

    def parse_alternatives__alt0(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Alternatives]
    ]:
        result: bootstrap_cst.Alternatives = bootstrap_cst.Alternatives(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if items := self.parse_alternatives__alt0__items(pos=pos):
            pos = items.pos
            result.append_items(child=items.result)
        else:
            return None
        if ws_after__items := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__items.pos
        if item1 := self.parse_alternatives__alt0__item1(pos=pos):
            pos = item1.pos
            result.children.extend(item1.result.children)
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_alternatives__alt0__items(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items]]:
        return self.apply__parse_items(pos=pos)

    def parse_alternatives__alt0__item1__alts(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Alternatives]
    ]:
        if alt0 := self.parse_alternatives__alt0__item1__alts__alt0(pos=pos):
            return alt0
        return None

    def parse_alternatives__alt0__item1__alts__alt0(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Alternatives]
    ]:
        result: bootstrap_cst.Alternatives = bootstrap_cst.Alternatives(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_alternatives__alt0__item1__alts__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__item0.pos
        if items := self.parse_alternatives__alt0__item1__alts__alt0__items(pos=pos):
            pos = items.pos
            result.append_items(child=items.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_alternatives__alt0__item1__alts__alt0__item0(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]
    ]:
        return self.consume_literal(pos=pos, literal="|")

    def parse_alternatives__alt0__item1__alts__alt0__items(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items]]:
        return self.apply__parse_items(pos=pos)

    def parse_alternatives__alt0__item1(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Alternatives]
    ]:
        result: bootstrap_cst.Alternatives = bootstrap_cst.Alternatives(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        while one_result := self.parse_alternatives__alt0__item1__alts(pos=pos):
            pos = one_result.pos
            result.children.extend(one_result.result.children)
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_items(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items]]:
        if alt0 := self.parse_items__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_items(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items]]:
        return self.packrat.apply(
            rule_callable=self.parse_items,
            rule_id=3,
            rule_cache=self._cache__parse_items,
            pos=pos,
        )

    def parse_items__alt0(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items]]:
        result: bootstrap_cst.Items = bootstrap_cst.Items(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item := self.parse_items__alt0__item(pos=pos):
            pos = item.pos
            result.append_item(child=item.result)
        else:
            return None
        if ws_after__item := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__item.pos
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

    def parse_items__alt0__item(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Item]]:
        return self.apply__parse_item(pos=pos)

    def parse_items__alt0__item1__alts(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items]]:
        if alt0 := self.parse_items__alt0__item1__alts__alt0(pos=pos):
            return alt0
        return None

    def parse_items__alt0__item1__alts__alt0(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items]]:
        result: bootstrap_cst.Items = bootstrap_cst.Items(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_items__alt0__item1__alts__alt0__item0(pos=pos):
            pos = item0.pos
            result.children.extend(item0.result.children)
        else:
            return None
        if ws_after__item0 := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__item0.pos
        if item := self.parse_items__alt0__item1__alts__alt0__item(pos=pos):
            pos = item.pos
            result.append_item(child=item.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_items__alt0__item1__alts__alt0__item0__alts(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items]]:
        if alt0 := self.parse_items__alt0__item1__alts__alt0__item0__alts__alt0(
            pos=pos
        ):
            return alt0
        if alt1 := self.parse_items__alt0__item1__alts__alt0__item0__alts__alt1(
            pos=pos
        ):
            return alt1
        return None

    def parse_items__alt0__item1__alts__alt0__item0__alts__alt0(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items]]:
        result: bootstrap_cst.Items = bootstrap_cst.Items(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if no_ws := self.parse_items__alt0__item1__alts__alt0__item0__alts__alt0__no_ws(
            pos=pos
        ):
            pos = no_ws.pos
            result.append_no_ws(child=no_ws.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_items__alt0__item1__alts__alt0__item0__alts__alt0__no_ws(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]
    ]:
        return self.consume_literal(pos=pos, literal=".")

    def parse_items__alt0__item1__alts__alt0__item0__alts__alt1(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items]]:
        result: bootstrap_cst.Items = bootstrap_cst.Items(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if ws := self.parse_items__alt0__item1__alts__alt0__item0__alts__alt1__ws(
            pos=pos
        ):
            pos = ws.pos
            result.append_ws(child=ws.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_items__alt0__item1__alts__alt0__item0__alts__alt1__ws(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]
    ]:
        return self.consume_literal(pos=pos, literal=",")

    def parse_items__alt0__item1__alts__alt0__item0(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items]]:
        return self.parse_items__alt0__item1__alts__alt0__item0__alts(pos=pos)

    def parse_items__alt0__item1__alts__alt0__item(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Item]]:
        return self.apply__parse_item(pos=pos)

    def parse_items__alt0__item1(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items]]:
        result: bootstrap_cst.Items = bootstrap_cst.Items(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        while one_result := self.parse_items__alt0__item1__alts(pos=pos):
            pos = one_result.pos
            result.children.extend(one_result.result.children)
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_items__alt0__item2__alts(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items]]:
        if alt0 := self.parse_items__alt0__item2__alts__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_items__alt0__item2__alts__alt1(pos=pos):
            return alt1
        return None

    def parse_items__alt0__item2__alts__alt0(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items]]:
        result: bootstrap_cst.Items = bootstrap_cst.Items(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if no_ws := self.parse_items__alt0__item2__alts__alt0__no_ws(pos=pos):
            pos = no_ws.pos
            result.append_no_ws(child=no_ws.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_items__alt0__item2__alts__alt0__no_ws(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]
    ]:
        return self.consume_literal(pos=pos, literal=".")

    def parse_items__alt0__item2__alts__alt1(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items]]:
        result: bootstrap_cst.Items = bootstrap_cst.Items(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if ws := self.parse_items__alt0__item2__alts__alt1__ws(pos=pos):
            pos = ws.pos
            result.append_ws(child=ws.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_items__alt0__item2__alts__alt1__ws(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]
    ]:
        return self.consume_literal(pos=pos, literal=",")

    def parse_items__alt0__item2(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Items]]:
        return self.parse_items__alt0__item2__alts(pos=pos)

    def parse_item(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Item]]:
        if alt0 := self.parse_item__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_item(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Item]]:
        return self.packrat.apply(
            rule_callable=self.parse_item,
            rule_id=4,
            rule_cache=self._cache__parse_item,
            pos=pos,
        )

    def parse_item__alt0(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Item]]:
        result: bootstrap_cst.Item = bootstrap_cst.Item(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_item__alt0__item0(pos=pos):
            pos = item0.pos
            result.children.extend(item0.result.children)
        if disposition := self.parse_item__alt0__disposition(pos=pos):
            pos = disposition.pos
            result.append_disposition(child=disposition.result)
        if term := self.parse_item__alt0__term(pos=pos):
            pos = term.pos
            result.append_term(child=term.result)
        else:
            return None
        if quantifier := self.parse_item__alt0__quantifier(pos=pos):
            pos = quantifier.pos
            result.append_quantifier(child=quantifier.result)
        if ws_after__quantifier := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__quantifier.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_item__alt0__item0__alts(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Item]]:
        if alt0 := self.parse_item__alt0__item0__alts__alt0(pos=pos):
            return alt0
        return None

    def parse_item__alt0__item0__alts__alt0(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Item]]:
        result: bootstrap_cst.Item = bootstrap_cst.Item(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if label := self.parse_item__alt0__item0__alts__alt0__label(pos=pos):
            pos = label.pos
            result.append_label(child=label.result)
        else:
            return None
        if item1 := self.parse_item__alt0__item0__alts__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_item__alt0__item0__alts__alt0__label(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Identifier]
    ]:
        return self.apply__parse_identifier(pos=pos)

    def parse_item__alt0__item0__alts__alt0__item1(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]
    ]:
        return self.consume_literal(pos=pos, literal=":")

    def parse_item__alt0__item0(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Item]]:
        return self.parse_item__alt0__item0__alts(pos=pos)

    def parse_item__alt0__disposition(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Disposition]
    ]:
        return self.apply__parse_disposition(pos=pos)

    def parse_item__alt0__term(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Term]]:
        return self.apply__parse_term(pos=pos)

    def parse_item__alt0__quantifier(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Quantifier]
    ]:
        return self.apply__parse_quantifier(pos=pos)

    def parse_term(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Term]]:
        if alt0 := self.parse_term__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_term__alt1(pos=pos):
            return alt1
        if alt2 := self.parse_term__alt2(pos=pos):
            return alt2
        if alt3 := self.parse_term__alt3(pos=pos):
            return alt3
        return None

    def apply__parse_term(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Term]]:
        return self.packrat.apply(
            rule_callable=self.parse_term,
            rule_id=5,
            rule_cache=self._cache__parse_term,
            pos=pos,
        )

    def parse_term__alt0(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Term]]:
        result: bootstrap_cst.Term = bootstrap_cst.Term(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if identifier := self.parse_term__alt0__identifier(pos=pos):
            pos = identifier.pos
            result.append_identifier(child=identifier.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_term__alt0__identifier(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Identifier]
    ]:
        return self.apply__parse_identifier(pos=pos)

    def parse_term__alt1(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Term]]:
        result: bootstrap_cst.Term = bootstrap_cst.Term(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if literal := self.parse_term__alt1__literal(pos=pos):
            pos = literal.pos
            result.append_literal(child=literal.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_term__alt1__literal(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Literal]]:
        return self.apply__parse_literal(pos=pos)

    def parse_term__alt2(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Term]]:
        result: bootstrap_cst.Term = bootstrap_cst.Term(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_term__alt2__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if regex := self.parse_term__alt2__regex(pos=pos):
            pos = regex.pos
            result.append_regex(child=regex.result)
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
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]
    ]:
        return self.consume_literal(pos=pos, literal="/")

    def parse_term__alt2__regex(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.RawString]
    ]:
        return self.apply__parse_raw_string(pos=pos)

    def parse_term__alt2__item2(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]
    ]:
        return self.consume_literal(pos=pos, literal="/")

    def parse_term__alt3(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Term]]:
        result: bootstrap_cst.Term = bootstrap_cst.Term(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_term__alt3__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__item0.pos
        if alternatives := self.parse_term__alt3__alternatives(pos=pos):
            pos = alternatives.pos
            result.append_alternatives(child=alternatives.result)
        else:
            return None
        if ws_after__alternatives := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__alternatives.pos
        if item2 := self.parse_term__alt3__item2(pos=pos):
            pos = item2.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_term__alt3__item0(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]
    ]:
        return self.consume_literal(pos=pos, literal="(")

    def parse_term__alt3__alternatives(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Alternatives]
    ]:
        return self.apply__parse_alternatives(pos=pos)

    def parse_term__alt3__item2(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]
    ]:
        return self.consume_literal(pos=pos, literal=")")

    def parse_disposition(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Disposition]
    ]:
        if alt0 := self.parse_disposition__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_disposition__alt1(pos=pos):
            return alt1
        if alt2 := self.parse_disposition__alt2(pos=pos):
            return alt2
        return None

    def apply__parse_disposition(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Disposition]
    ]:
        return self.packrat.apply(
            rule_callable=self.parse_disposition,
            rule_id=6,
            rule_cache=self._cache__parse_disposition,
            pos=pos,
        )

    def parse_disposition__alt0(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Disposition]
    ]:
        result: bootstrap_cst.Disposition = bootstrap_cst.Disposition(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if suppress := self.parse_disposition__alt0__suppress(pos=pos):
            pos = suppress.pos
            result.append_suppress(child=suppress.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_disposition__alt0__suppress(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]
    ]:
        return self.consume_literal(pos=pos, literal="%")

    def parse_disposition__alt1(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Disposition]
    ]:
        result: bootstrap_cst.Disposition = bootstrap_cst.Disposition(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if include := self.parse_disposition__alt1__include(pos=pos):
            pos = include.pos
            result.append_include(child=include.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_disposition__alt1__include(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]
    ]:
        return self.consume_literal(pos=pos, literal="$")

    def parse_disposition__alt2(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Disposition]
    ]:
        result: bootstrap_cst.Disposition = bootstrap_cst.Disposition(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if inline := self.parse_disposition__alt2__inline(pos=pos):
            pos = inline.pos
            result.append_inline(child=inline.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_disposition__alt2__inline(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]
    ]:
        return self.consume_literal(pos=pos, literal="!")

    def parse_quantifier(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Quantifier]
    ]:
        if alt0 := self.parse_quantifier__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_quantifier__alt1(pos=pos):
            return alt1
        if alt2 := self.parse_quantifier__alt2(pos=pos):
            return alt2
        return None

    def apply__parse_quantifier(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Quantifier]
    ]:
        return self.packrat.apply(
            rule_callable=self.parse_quantifier,
            rule_id=7,
            rule_cache=self._cache__parse_quantifier,
            pos=pos,
        )

    def parse_quantifier__alt0(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Quantifier]
    ]:
        result: bootstrap_cst.Quantifier = bootstrap_cst.Quantifier(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if optional := self.parse_quantifier__alt0__optional(pos=pos):
            pos = optional.pos
            result.append_optional(child=optional.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_quantifier__alt0__optional(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]
    ]:
        return self.consume_literal(pos=pos, literal="?")

    def parse_quantifier__alt1(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Quantifier]
    ]:
        result: bootstrap_cst.Quantifier = bootstrap_cst.Quantifier(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if one_or_more := self.parse_quantifier__alt1__one_or_more(pos=pos):
            pos = one_or_more.pos
            result.append_one_or_more(child=one_or_more.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_quantifier__alt1__one_or_more(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]
    ]:
        return self.consume_literal(pos=pos, literal="+")

    def parse_quantifier__alt2(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Quantifier]
    ]:
        result: bootstrap_cst.Quantifier = bootstrap_cst.Quantifier(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if zero_or_more := self.parse_quantifier__alt2__zero_or_more(pos=pos):
            pos = zero_or_more.pos
            result.append_zero_or_more(child=zero_or_more.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_quantifier__alt2__zero_or_more(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]
    ]:
        return self.consume_literal(pos=pos, literal="*")

    def parse_identifier(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Identifier]
    ]:
        if alt0 := self.parse_identifier__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_identifier(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Identifier]
    ]:
        return self.packrat.apply(
            rule_callable=self.parse_identifier,
            rule_id=8,
            rule_cache=self._cache__parse_identifier,
            pos=pos,
        )

    def parse_identifier__alt0(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Identifier]
    ]:
        result: bootstrap_cst.Identifier = bootstrap_cst.Identifier(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if name := self.parse_identifier__alt0__name(pos=pos):
            pos = name.pos
            result.append_name(child=name.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_identifier__alt0__name(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]
    ]:
        return self.consume_regex(pos=pos, regex="[_a-z][_a-z0-9]*")

    def parse_raw_string(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.RawString]
    ]:
        if alt0 := self.parse_raw_string__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_raw_string(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.RawString]
    ]:
        return self.packrat.apply(
            rule_callable=self.parse_raw_string,
            rule_id=9,
            rule_cache=self._cache__parse_raw_string,
            pos=pos,
        )

    def parse_raw_string__alt0(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.RawString]
    ]:
        result: bootstrap_cst.RawString = bootstrap_cst.RawString(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if value := self.parse_raw_string__alt0__value(pos=pos):
            pos = value.pos
            result.append_value(child=value.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_raw_string__alt0__value(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]
    ]:
        return self.consume_regex(pos=pos, regex="([^\\/\\n\\\\]|\\\\.)+")

    def parse_literal(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Literal]]:
        if alt0 := self.parse_literal__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_literal(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Literal]]:
        return self.packrat.apply(
            rule_callable=self.parse_literal,
            rule_id=10,
            rule_cache=self._cache__parse_literal,
            pos=pos,
        )

    def parse_literal__alt0(
        self, pos: int
    ) -> typing.Optional[fltk.fegen.pyrt.memo.ApplyResult[int, bootstrap_cst.Literal]]:
        result: bootstrap_cst.Literal = bootstrap_cst.Literal(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if value := self.parse_literal__alt0__value(pos=pos):
            pos = value.pos
            result.append_value(child=value.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_literal__alt0__value(
        self, pos: int
    ) -> typing.Optional[
        fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]
    ]:
        return self.consume_regex(
            pos=pos, regex="(\"([^\"\\n\\\\]|\\\\.)+\"|'([^'\\n\\\\]|\\\\.)+')"
        )
