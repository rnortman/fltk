import collections.abc
import typing

import fltk.fegen.pyrt.errors
import fltk.fegen.pyrt.memo
import fltk.fegen.pyrt.span
import fltk.fegen.pyrt.terminalsrc
import fltk.unparse.toy_cst


class Parser:
    """Parser"""

    def __init__(self, terminalsrc: fltk.fegen.pyrt.terminalsrc.TerminalSource) -> None:
        self.terminalsrc = terminalsrc
        self._source_text = fltk.fegen.pyrt.span.SourceText(text=terminalsrc.terminals, filename=terminalsrc.filename)
        self.packrat: fltk.fegen.pyrt.memo.Packrat[int, int] = fltk.fegen.pyrt.memo.Packrat()
        self.error_tracker: fltk.fegen.pyrt.errors.ErrorTracker[int] = fltk.fegen.pyrt.errors.ErrorTracker()
        self.rule_names: typing.Sequence[str] = ["expr", "term", "factor", "number", "_trivia"]
        self._cache__parse_expr: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.toy_cst.Expr]
        ] = {}
        self._cache__parse_term: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.toy_cst.Term]
        ] = {}
        self._cache__parse_factor: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.toy_cst.Factor]
        ] = {}
        self._cache__parse_number: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.toy_cst.Number]
        ] = {}
        self._cache__parse__trivia: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.toy_cst.Trivia]
        ] = {}

    def consume_literal(
        self, pos: int, literal: str
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        if span := self.terminalsrc.consume_literal(pos=pos, literal=literal):
            return fltk.fegen.pyrt.memo.ApplyResult(
                pos=span.end, result=fltk.fegen.pyrt.span.Span.with_source(span.start, span.end, self._source_text)
            )
        self.error_tracker.fail_literal(pos=pos, rule_id=self.packrat.invocation_stack[-1], literal=literal)
        return None

    def consume_regex(
        self, pos: int, regex: str
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        if span := self.terminalsrc.consume_regex(pos=pos, regex=regex):
            return fltk.fegen.pyrt.memo.ApplyResult(
                pos=span.end, result=fltk.fegen.pyrt.span.Span.with_source(span.start, span.end, self._source_text)
            )
        self.error_tracker.fail_regex(pos=pos, rule_id=self.packrat.invocation_stack[-1], regex=regex)
        return None

    def parse_expr(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Expr] | None:
        if alt0 := self.parse_expr__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_expr(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Expr] | None:
        return self.packrat.apply(rule_callable=self.parse_expr, rule_id=0, rule_cache=self._cache__parse_expr, pos=pos)

    def parse_expr__alt0(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Expr] | None:
        _span_start: int = pos
        result: fltk.unparse.toy_cst.Expr = fltk.unparse.toy_cst.Expr(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_expr__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_term(child=item0.result)
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
            result.append(child=ws_after__item0.result, label=None)
        if item1 := self.parse_expr__alt0__item1(pos=pos):
            pos = item1.pos
            result.extend_children(other=item1.result)
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_expr__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Term] | None:
        return self.apply__parse_term(pos=pos)

    def parse_expr__alt0__item1__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Expr] | None:
        if alt0 := self.parse_expr__alt0__item1__alts__alt0(pos=pos):
            return alt0
        return None

    def parse_expr__alt0__item1__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Expr] | None:
        _span_start: int = pos
        result: fltk.unparse.toy_cst.Expr = fltk.unparse.toy_cst.Expr(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_expr__alt0__item1__alts__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_plus(child=item0.result)
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
            result.append(child=ws_after__item0.result, label=None)
        if item1 := self.parse_expr__alt0__item1__alts__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_term(child=item1.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_expr__alt0__item1__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="+")

    def parse_expr__alt0__item1__alts__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Term] | None:
        return self.apply__parse_term(pos=pos)

    def parse_expr__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Expr] | None:
        _span_start: int = pos
        result: fltk.unparse.toy_cst.Expr = fltk.unparse.toy_cst.Expr(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        while one_result := self.parse_expr__alt0__item1__alts(pos=pos):
            if not one_result.pos > pos:
                break
            pos = one_result.pos
            result.extend_children(other=one_result.result)
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_term(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Term] | None:
        if alt0 := self.parse_term__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_term(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Term] | None:
        return self.packrat.apply(rule_callable=self.parse_term, rule_id=1, rule_cache=self._cache__parse_term, pos=pos)

    def parse_term__alt0(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Term] | None:
        _span_start: int = pos
        result: fltk.unparse.toy_cst.Term = fltk.unparse.toy_cst.Term(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_term__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_factor(child=item0.result)
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
            result.append(child=ws_after__item0.result, label=None)
        if item1 := self.parse_term__alt0__item1(pos=pos):
            pos = item1.pos
            result.extend_children(other=item1.result)
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_term__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Factor] | None:
        return self.apply__parse_factor(pos=pos)

    def parse_term__alt0__item1__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Term] | None:
        if alt0 := self.parse_term__alt0__item1__alts__alt0(pos=pos):
            return alt0
        return None

    def parse_term__alt0__item1__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Term] | None:
        _span_start: int = pos
        result: fltk.unparse.toy_cst.Term = fltk.unparse.toy_cst.Term(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_term__alt0__item1__alts__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_mult(child=item0.result)
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
            result.append(child=ws_after__item0.result, label=None)
        if item1 := self.parse_term__alt0__item1__alts__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_factor(child=item1.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_term__alt0__item1__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="*")

    def parse_term__alt0__item1__alts__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Factor] | None:
        return self.apply__parse_factor(pos=pos)

    def parse_term__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Term] | None:
        _span_start: int = pos
        result: fltk.unparse.toy_cst.Term = fltk.unparse.toy_cst.Term(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        while one_result := self.parse_term__alt0__item1__alts(pos=pos):
            if not one_result.pos > pos:
                break
            pos = one_result.pos
            result.extend_children(other=one_result.result)
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_factor(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Factor] | None:
        if alt0 := self.parse_factor__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_factor__alt1(pos=pos):
            return alt1
        return None

    def apply__parse_factor(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Factor] | None:
        return self.packrat.apply(
            rule_callable=self.parse_factor, rule_id=2, rule_cache=self._cache__parse_factor, pos=pos
        )

    def parse_factor__alt0(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Factor] | None:
        _span_start: int = pos
        result: fltk.unparse.toy_cst.Factor = fltk.unparse.toy_cst.Factor(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_factor__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_number(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_factor__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Number] | None:
        return self.apply__parse_number(pos=pos)

    def parse_factor__alt1(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Factor] | None:
        _span_start: int = pos
        result: fltk.unparse.toy_cst.Factor = fltk.unparse.toy_cst.Factor(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_factor__alt1__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
            result.append(child=ws_after__item0.result, label=None)
        if item1 := self.parse_factor__alt1__item1(pos=pos):
            pos = item1.pos
            result.append_expr(child=item1.result)
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
            result.append(child=ws_after__item1.result, label=None)
        if item2 := self.parse_factor__alt1__item2(pos=pos):
            pos = item2.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_factor__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="(")

    def parse_factor__alt1__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Expr] | None:
        return self.apply__parse_expr(pos=pos)

    def parse_factor__alt1__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal=")")

    def parse_number(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Number] | None:
        if alt0 := self.parse_number__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_number(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Number] | None:
        return self.packrat.apply(
            rule_callable=self.parse_number, rule_id=3, rule_cache=self._cache__parse_number, pos=pos
        )

    def parse_number__alt0(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Number] | None:
        _span_start: int = pos
        result: fltk.unparse.toy_cst.Number = fltk.unparse.toy_cst.Number(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_number__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_value(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_number__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_regex(pos=pos, regex="[0-9]+")

    def parse__trivia(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Trivia] | None:
        if alt0 := self.parse__trivia__alt0(pos=pos):
            return alt0
        return None

    def apply__parse__trivia(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Trivia] | None:
        return self.packrat.apply(
            rule_callable=self.parse__trivia, rule_id=4, rule_cache=self._cache__parse__trivia, pos=pos
        )

    def parse__trivia__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.toy_cst.Trivia] | None:
        _span_start: int = pos
        result: fltk.unparse.toy_cst.Trivia = fltk.unparse.toy_cst.Trivia(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse__trivia__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_content(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse__trivia__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_regex(pos=pos, regex="[\\s]+")
