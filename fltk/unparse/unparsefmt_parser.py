import collections.abc
import typing

import fltk.fegen.pyrt.errors
import fltk.fegen.pyrt.memo
import fltk.fegen.pyrt.terminalsrc
import fltk.unparse.unparsefmt_cst


class Parser:
    """Parser"""

    def __init__(self, terminalsrc: fltk.fegen.pyrt.terminalsrc.TerminalSource) -> None:
        self.terminalsrc = terminalsrc
        self.packrat: fltk.fegen.pyrt.memo.Packrat[int, int] = fltk.fegen.pyrt.memo.Packrat()
        self.error_tracker: fltk.fegen.pyrt.errors.ErrorTracker[int] = fltk.fegen.pyrt.errors.ErrorTracker()
        self.rule_names: typing.Sequence[str] = [
            "formatter",
            "statement",
            "default",
            "rule_config",
            "rule_statement",
            "group",
            "nest",
            "join",
            "from_spec",
            "to_spec",
            "anchor",
            "after",
            "before",
            "omit",
            "render",
            "position_spec_statement",
            "spacing",
            "doc_literal",
            "text_literal",
            "concat_literal",
            "join_literal",
            "doc_list_literal",
            "compound_literal",
            "trivia_preserve",
            "trivia_node_list",
            "identifier",
            "literal",
            "integer",
            "_trivia",
            "line_comment",
        ]
        self._cache__parse_formatter: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.Formatter]
        ] = {}
        self._cache__parse_statement: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.Statement]
        ] = {}
        self._cache__parse_default: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.Default]
        ] = {}
        self._cache__parse_rule_config: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.RuleConfig]
        ] = {}
        self._cache__parse_rule_statement: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.RuleStatement]
        ] = {}
        self._cache__parse_group: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.Group]
        ] = {}
        self._cache__parse_nest: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.Nest]
        ] = {}
        self._cache__parse_join: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.Join]
        ] = {}
        self._cache__parse_from_spec: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.FromSpec]
        ] = {}
        self._cache__parse_to_spec: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.ToSpec]
        ] = {}
        self._cache__parse_anchor: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.Anchor]
        ] = {}
        self._cache__parse_after: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.After]
        ] = {}
        self._cache__parse_before: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.Before]
        ] = {}
        self._cache__parse_omit: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.Omit]
        ] = {}
        self._cache__parse_render: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.Render]
        ] = {}
        self._cache__parse_position_spec_statement: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.PositionSpecStatement]
        ] = {}
        self._cache__parse_spacing: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.Spacing]
        ] = {}
        self._cache__parse_doc_literal: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.DocLiteral]
        ] = {}
        self._cache__parse_text_literal: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.TextLiteral]
        ] = {}
        self._cache__parse_concat_literal: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.ConcatLiteral]
        ] = {}
        self._cache__parse_join_literal: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.JoinLiteral]
        ] = {}
        self._cache__parse_doc_list_literal: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.DocListLiteral]
        ] = {}
        self._cache__parse_compound_literal: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.CompoundLiteral]
        ] = {}
        self._cache__parse_trivia_preserve: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.TriviaPreserve]
        ] = {}
        self._cache__parse_trivia_node_list: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.TriviaNodeList]
        ] = {}
        self._cache__parse_identifier: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.Identifier]
        ] = {}
        self._cache__parse_literal: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.Literal]
        ] = {}
        self._cache__parse_integer: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.Integer]
        ] = {}
        self._cache__parse__trivia: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.Trivia]
        ] = {}
        self._cache__parse_line_comment: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.unparse.unparsefmt_cst.LineComment]
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

    def parse_formatter(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Formatter] | None:
        if alt0 := self.parse_formatter__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_formatter(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Formatter] | None:
        return self.packrat.apply(
            rule_callable=self.parse_formatter, rule_id=0, rule_cache=self._cache__parse_formatter, pos=pos
        )

    def parse_formatter__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Formatter] | None:
        result: fltk.unparse.unparsefmt_cst.Formatter = fltk.unparse.unparsefmt_cst.Formatter(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if initial_ws := self.apply__parse__trivia(pos=pos):
            pos = initial_ws.pos
        if item0 := self.parse_formatter__alt0__item0(pos=pos):
            pos = item0.pos
            result.children.extend(item0.result.children)
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_formatter__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Formatter] | None:
        result: fltk.unparse.unparsefmt_cst.Formatter = fltk.unparse.unparsefmt_cst.Formatter(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        while one_result := self.apply__parse_statement(pos=pos):
            pos = one_result.pos
            result.append_statement(child=one_result.result)
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_statement(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Statement] | None:
        if alt0 := self.parse_statement__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_statement__alt1(pos=pos):
            return alt1
        if alt2 := self.parse_statement__alt2(pos=pos):
            return alt2
        if alt3 := self.parse_statement__alt3(pos=pos):
            return alt3
        if alt4 := self.parse_statement__alt4(pos=pos):
            return alt4
        if alt5 := self.parse_statement__alt5(pos=pos):
            return alt5
        if alt6 := self.parse_statement__alt6(pos=pos):
            return alt6
        if alt7 := self.parse_statement__alt7(pos=pos):
            return alt7
        if alt8 := self.parse_statement__alt8(pos=pos):
            return alt8
        if alt9 := self.parse_statement__alt9(pos=pos):
            return alt9
        return None

    def apply__parse_statement(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Statement] | None:
        return self.packrat.apply(
            rule_callable=self.parse_statement, rule_id=1, rule_cache=self._cache__parse_statement, pos=pos
        )

    def parse_statement__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Statement] | None:
        result: fltk.unparse.unparsefmt_cst.Statement = fltk.unparse.unparsefmt_cst.Statement(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_statement__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_default(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_statement__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Default] | None:
        return self.apply__parse_default(pos=pos)

    def parse_statement__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Statement] | None:
        result: fltk.unparse.unparsefmt_cst.Statement = fltk.unparse.unparsefmt_cst.Statement(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_statement__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_group(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_statement__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Group] | None:
        return self.apply__parse_group(pos=pos)

    def parse_statement__alt2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Statement] | None:
        result: fltk.unparse.unparsefmt_cst.Statement = fltk.unparse.unparsefmt_cst.Statement(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_statement__alt2__item0(pos=pos):
            pos = item0.pos
            result.append_nest(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_statement__alt2__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Nest] | None:
        return self.apply__parse_nest(pos=pos)

    def parse_statement__alt3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Statement] | None:
        result: fltk.unparse.unparsefmt_cst.Statement = fltk.unparse.unparsefmt_cst.Statement(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_statement__alt3__item0(pos=pos):
            pos = item0.pos
            result.append_join(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_statement__alt3__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Join] | None:
        return self.apply__parse_join(pos=pos)

    def parse_statement__alt4(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Statement] | None:
        result: fltk.unparse.unparsefmt_cst.Statement = fltk.unparse.unparsefmt_cst.Statement(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_statement__alt4__item0(pos=pos):
            pos = item0.pos
            result.append_after(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_statement__alt4__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.After] | None:
        return self.apply__parse_after(pos=pos)

    def parse_statement__alt5(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Statement] | None:
        result: fltk.unparse.unparsefmt_cst.Statement = fltk.unparse.unparsefmt_cst.Statement(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_statement__alt5__item0(pos=pos):
            pos = item0.pos
            result.append_before(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_statement__alt5__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Before] | None:
        return self.apply__parse_before(pos=pos)

    def parse_statement__alt6(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Statement] | None:
        result: fltk.unparse.unparsefmt_cst.Statement = fltk.unparse.unparsefmt_cst.Statement(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_statement__alt6__item0(pos=pos):
            pos = item0.pos
            result.append_rule_config(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_statement__alt6__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.RuleConfig] | None:
        return self.apply__parse_rule_config(pos=pos)

    def parse_statement__alt7(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Statement] | None:
        result: fltk.unparse.unparsefmt_cst.Statement = fltk.unparse.unparsefmt_cst.Statement(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_statement__alt7__item0(pos=pos):
            pos = item0.pos
            result.append_trivia_preserve(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_statement__alt7__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.TriviaPreserve] | None:
        return self.apply__parse_trivia_preserve(pos=pos)

    def parse_statement__alt8(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Statement] | None:
        result: fltk.unparse.unparsefmt_cst.Statement = fltk.unparse.unparsefmt_cst.Statement(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_statement__alt8__item0(pos=pos):
            pos = item0.pos
            result.append_omit(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_statement__alt8__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Omit] | None:
        return self.apply__parse_omit(pos=pos)

    def parse_statement__alt9(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Statement] | None:
        result: fltk.unparse.unparsefmt_cst.Statement = fltk.unparse.unparsefmt_cst.Statement(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_statement__alt9__item0(pos=pos):
            pos = item0.pos
            result.append_render(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_statement__alt9__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Render] | None:
        return self.apply__parse_render(pos=pos)

    def parse_default(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Default] | None:
        if alt0 := self.parse_default__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_default(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Default] | None:
        return self.packrat.apply(
            rule_callable=self.parse_default, rule_id=2, rule_cache=self._cache__parse_default, pos=pos
        )

    def parse_default__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Default] | None:
        result: fltk.unparse.unparsefmt_cst.Default = fltk.unparse.unparsefmt_cst.Default(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_default__alt0__item0(pos=pos):
            pos = item0.pos
            result.children.extend(item0.result.children)
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_default__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_default__alt0__item2(pos=pos):
            pos = item2.pos
            result.append_spacing(child=item2.result)
        else:
            return None
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_default__alt0__item3(pos=pos):
            pos = item3.pos
        else:
            return None
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_default__alt0__item0__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Default] | None:
        if alt0 := self.parse_default__alt0__item0__alts__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_default__alt0__item0__alts__alt1(pos=pos):
            return alt1
        return None

    def parse_default__alt0__item0__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Default] | None:
        result: fltk.unparse.unparsefmt_cst.Default = fltk.unparse.unparsefmt_cst.Default(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_default__alt0__item0__alts__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_ws_allowed(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_default__alt0__item0__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="ws_allowed")

    def parse_default__alt0__item0__alts__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Default] | None:
        result: fltk.unparse.unparsefmt_cst.Default = fltk.unparse.unparsefmt_cst.Default(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_default__alt0__item0__alts__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_ws_required(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_default__alt0__item0__alts__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="ws_required")

    def parse_default__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Default] | None:
        return self.parse_default__alt0__item0__alts(pos=pos)

    def parse_default__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=":")

    def parse_default__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Spacing] | None:
        return self.apply__parse_spacing(pos=pos)

    def parse_default__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_rule_config(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.RuleConfig] | None:
        if alt0 := self.parse_rule_config__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_rule_config(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.RuleConfig] | None:
        return self.packrat.apply(
            rule_callable=self.parse_rule_config, rule_id=3, rule_cache=self._cache__parse_rule_config, pos=pos
        )

    def parse_rule_config__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.RuleConfig] | None:
        result: fltk.unparse.unparsefmt_cst.RuleConfig = fltk.unparse.unparsefmt_cst.RuleConfig(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_rule_config__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_rule_config__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_rule_name(child=item1.result)
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_rule_config__alt0__item2(pos=pos):
            pos = item2.pos
        else:
            return None
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_rule_config__alt0__item3(pos=pos):
            pos = item3.pos
            result.children.extend(item3.result.children)
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        if item4 := self.parse_rule_config__alt0__item4(pos=pos):
            pos = item4.pos
        else:
            return None
        if ws_after__item4 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item4.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_config__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="rule")

    def parse_rule_config__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Identifier] | None:
        return self.apply__parse_identifier(pos=pos)

    def parse_rule_config__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="{")

    def parse_rule_config__alt0__item3__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.RuleConfig] | None:
        if alt0 := self.parse_rule_config__alt0__item3__alts__alt0(pos=pos):
            return alt0
        return None

    def parse_rule_config__alt0__item3__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.RuleConfig] | None:
        result: fltk.unparse.unparsefmt_cst.RuleConfig = fltk.unparse.unparsefmt_cst.RuleConfig(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_rule_config__alt0__item3__alts__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_rule_statement(child=item0.result)
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_config__alt0__item3__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.RuleStatement] | None:
        return self.apply__parse_rule_statement(pos=pos)

    def parse_rule_config__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.RuleConfig] | None:
        result: fltk.unparse.unparsefmt_cst.RuleConfig = fltk.unparse.unparsefmt_cst.RuleConfig(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        while one_result := self.parse_rule_config__alt0__item3__alts(pos=pos):
            pos = one_result.pos
            result.children.extend(one_result.result.children)
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_config__alt0__item4(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="}")

    def parse_rule_statement(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.RuleStatement] | None:
        if alt0 := self.parse_rule_statement__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_rule_statement__alt1(pos=pos):
            return alt1
        if alt2 := self.parse_rule_statement__alt2(pos=pos):
            return alt2
        if alt3 := self.parse_rule_statement__alt3(pos=pos):
            return alt3
        if alt4 := self.parse_rule_statement__alt4(pos=pos):
            return alt4
        if alt5 := self.parse_rule_statement__alt5(pos=pos):
            return alt5
        if alt6 := self.parse_rule_statement__alt6(pos=pos):
            return alt6
        if alt7 := self.parse_rule_statement__alt7(pos=pos):
            return alt7
        return None

    def apply__parse_rule_statement(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.RuleStatement] | None:
        return self.packrat.apply(
            rule_callable=self.parse_rule_statement, rule_id=4, rule_cache=self._cache__parse_rule_statement, pos=pos
        )

    def parse_rule_statement__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.RuleStatement] | None:
        result: fltk.unparse.unparsefmt_cst.RuleStatement = fltk.unparse.unparsefmt_cst.RuleStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_rule_statement__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_default(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_statement__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Default] | None:
        return self.apply__parse_default(pos=pos)

    def parse_rule_statement__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.RuleStatement] | None:
        result: fltk.unparse.unparsefmt_cst.RuleStatement = fltk.unparse.unparsefmt_cst.RuleStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_rule_statement__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_group(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_statement__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Group] | None:
        return self.apply__parse_group(pos=pos)

    def parse_rule_statement__alt2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.RuleStatement] | None:
        result: fltk.unparse.unparsefmt_cst.RuleStatement = fltk.unparse.unparsefmt_cst.RuleStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_rule_statement__alt2__item0(pos=pos):
            pos = item0.pos
            result.append_nest(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_statement__alt2__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Nest] | None:
        return self.apply__parse_nest(pos=pos)

    def parse_rule_statement__alt3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.RuleStatement] | None:
        result: fltk.unparse.unparsefmt_cst.RuleStatement = fltk.unparse.unparsefmt_cst.RuleStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_rule_statement__alt3__item0(pos=pos):
            pos = item0.pos
            result.append_join(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_statement__alt3__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Join] | None:
        return self.apply__parse_join(pos=pos)

    def parse_rule_statement__alt4(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.RuleStatement] | None:
        result: fltk.unparse.unparsefmt_cst.RuleStatement = fltk.unparse.unparsefmt_cst.RuleStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_rule_statement__alt4__item0(pos=pos):
            pos = item0.pos
            result.append_after(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_statement__alt4__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.After] | None:
        return self.apply__parse_after(pos=pos)

    def parse_rule_statement__alt5(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.RuleStatement] | None:
        result: fltk.unparse.unparsefmt_cst.RuleStatement = fltk.unparse.unparsefmt_cst.RuleStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_rule_statement__alt5__item0(pos=pos):
            pos = item0.pos
            result.append_before(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_statement__alt5__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Before] | None:
        return self.apply__parse_before(pos=pos)

    def parse_rule_statement__alt6(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.RuleStatement] | None:
        result: fltk.unparse.unparsefmt_cst.RuleStatement = fltk.unparse.unparsefmt_cst.RuleStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_rule_statement__alt6__item0(pos=pos):
            pos = item0.pos
            result.append_omit(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_statement__alt6__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Omit] | None:
        return self.apply__parse_omit(pos=pos)

    def parse_rule_statement__alt7(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.RuleStatement] | None:
        result: fltk.unparse.unparsefmt_cst.RuleStatement = fltk.unparse.unparsefmt_cst.RuleStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_rule_statement__alt7__item0(pos=pos):
            pos = item0.pos
            result.append_render(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_statement__alt7__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Render] | None:
        return self.apply__parse_render(pos=pos)

    def parse_group(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Group] | None:
        if alt0 := self.parse_group__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_group__alt1(pos=pos):
            return alt1
        return None

    def apply__parse_group(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Group] | None:
        return self.packrat.apply(
            rule_callable=self.parse_group, rule_id=5, rule_cache=self._cache__parse_group, pos=pos
        )

    def parse_group__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Group] | None:
        result: fltk.unparse.unparsefmt_cst.Group = fltk.unparse.unparsefmt_cst.Group(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_group__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_group__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_group__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="group")

    def parse_group__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_group__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Group] | None:
        result: fltk.unparse.unparsefmt_cst.Group = fltk.unparse.unparsefmt_cst.Group(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_group__alt1__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        else:
            return None
        if item1 := self.parse_group__alt1__item1(pos=pos):
            pos = item1.pos
            result.append_from_spec(child=item1.result)
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_group__alt1__item2(pos=pos):
            pos = item2.pos
            result.append_to_spec(child=item2.result)
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_group__alt1__item3(pos=pos):
            pos = item3.pos
        else:
            return None
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_group__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="group")

    def parse_group__alt1__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.FromSpec] | None:
        return self.apply__parse_from_spec(pos=pos)

    def parse_group__alt1__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.ToSpec] | None:
        return self.apply__parse_to_spec(pos=pos)

    def parse_group__alt1__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_nest(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Nest] | None:
        if alt0 := self.parse_nest__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_nest__alt1(pos=pos):
            return alt1
        return None

    def apply__parse_nest(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Nest] | None:
        return self.packrat.apply(rule_callable=self.parse_nest, rule_id=6, rule_cache=self._cache__parse_nest, pos=pos)

    def parse_nest__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Nest] | None:
        result: fltk.unparse.unparsefmt_cst.Nest = fltk.unparse.unparsefmt_cst.Nest(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_nest__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_nest__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_nest__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="nest")

    def parse_nest__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_nest__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Nest] | None:
        result: fltk.unparse.unparsefmt_cst.Nest = fltk.unparse.unparsefmt_cst.Nest(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_nest__alt1__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        else:
            return None
        if item1 := self.parse_nest__alt1__item1(pos=pos):
            pos = item1.pos
            result.children.extend(item1.result.children)
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_nest__alt1__item2(pos=pos):
            pos = item2.pos
            result.append_from_spec(child=item2.result)
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_nest__alt1__item3(pos=pos):
            pos = item3.pos
            result.append_to_spec(child=item3.result)
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        if item4 := self.parse_nest__alt1__item4(pos=pos):
            pos = item4.pos
        else:
            return None
        if ws_after__item4 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item4.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_nest__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="nest")

    def parse_nest__alt1__item1__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Nest] | None:
        if alt0 := self.parse_nest__alt1__item1__alts__alt0(pos=pos):
            return alt0
        return None

    def parse_nest__alt1__item1__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Nest] | None:
        result: fltk.unparse.unparsefmt_cst.Nest = fltk.unparse.unparsefmt_cst.Nest(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_nest__alt1__item1__alts__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_indent(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_nest__alt1__item1__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Integer] | None:
        return self.apply__parse_integer(pos=pos)

    def parse_nest__alt1__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Nest] | None:
        return self.parse_nest__alt1__item1__alts(pos=pos)

    def parse_nest__alt1__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.FromSpec] | None:
        return self.apply__parse_from_spec(pos=pos)

    def parse_nest__alt1__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.ToSpec] | None:
        return self.apply__parse_to_spec(pos=pos)

    def parse_nest__alt1__item4(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_join(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Join] | None:
        if alt0 := self.parse_join__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_join(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Join] | None:
        return self.packrat.apply(rule_callable=self.parse_join, rule_id=7, rule_cache=self._cache__parse_join, pos=pos)

    def parse_join__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Join] | None:
        result: fltk.unparse.unparsefmt_cst.Join = fltk.unparse.unparsefmt_cst.Join(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_join__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        else:
            return None
        if item1 := self.parse_join__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_from_spec(child=item1.result)
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_join__alt0__item2(pos=pos):
            pos = item2.pos
            result.append_to_spec(child=item2.result)
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_join__alt0__item3(pos=pos):
            pos = item3.pos
            result.append_doc_literal(child=item3.result)
        else:
            return None
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        if item4 := self.parse_join__alt0__item4(pos=pos):
            pos = item4.pos
        else:
            return None
        if ws_after__item4 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item4.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_join__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="join")

    def parse_join__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.FromSpec] | None:
        return self.apply__parse_from_spec(pos=pos)

    def parse_join__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.ToSpec] | None:
        return self.apply__parse_to_spec(pos=pos)

    def parse_join__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.DocLiteral] | None:
        return self.apply__parse_doc_literal(pos=pos)

    def parse_join__alt0__item4(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_from_spec(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.FromSpec] | None:
        if alt0 := self.parse_from_spec__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_from_spec(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.FromSpec] | None:
        return self.packrat.apply(
            rule_callable=self.parse_from_spec, rule_id=8, rule_cache=self._cache__parse_from_spec, pos=pos
        )

    def parse_from_spec__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.FromSpec] | None:
        result: fltk.unparse.unparsefmt_cst.FromSpec = fltk.unparse.unparsefmt_cst.FromSpec(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_from_spec__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        else:
            return None
        if item1 := self.parse_from_spec__alt0__item1(pos=pos):
            pos = item1.pos
            result.children.extend(item1.result.children)
        if item2 := self.parse_from_spec__alt0__item2(pos=pos):
            pos = item2.pos
            result.append_from_anchor(child=item2.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_from_spec__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="from")

    def parse_from_spec__alt0__item1__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.FromSpec] | None:
        if alt0 := self.parse_from_spec__alt0__item1__alts__alt0(pos=pos):
            return alt0
        return None

    def parse_from_spec__alt0__item1__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.FromSpec] | None:
        result: fltk.unparse.unparsefmt_cst.FromSpec = fltk.unparse.unparsefmt_cst.FromSpec(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_from_spec__alt0__item1__alts__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_after(child=item0.result)
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_from_spec__alt0__item1__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="after")

    def parse_from_spec__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.FromSpec] | None:
        return self.parse_from_spec__alt0__item1__alts(pos=pos)

    def parse_from_spec__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Anchor] | None:
        return self.apply__parse_anchor(pos=pos)

    def parse_to_spec(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.ToSpec] | None:
        if alt0 := self.parse_to_spec__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_to_spec(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.ToSpec] | None:
        return self.packrat.apply(
            rule_callable=self.parse_to_spec, rule_id=9, rule_cache=self._cache__parse_to_spec, pos=pos
        )

    def parse_to_spec__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.ToSpec] | None:
        result: fltk.unparse.unparsefmt_cst.ToSpec = fltk.unparse.unparsefmt_cst.ToSpec(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_to_spec__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        else:
            return None
        if item1 := self.parse_to_spec__alt0__item1(pos=pos):
            pos = item1.pos
            result.children.extend(item1.result.children)
        if item2 := self.parse_to_spec__alt0__item2(pos=pos):
            pos = item2.pos
            result.append_to_anchor(child=item2.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_to_spec__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="to")

    def parse_to_spec__alt0__item1__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.ToSpec] | None:
        if alt0 := self.parse_to_spec__alt0__item1__alts__alt0(pos=pos):
            return alt0
        return None

    def parse_to_spec__alt0__item1__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.ToSpec] | None:
        result: fltk.unparse.unparsefmt_cst.ToSpec = fltk.unparse.unparsefmt_cst.ToSpec(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_to_spec__alt0__item1__alts__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_before(child=item0.result)
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_to_spec__alt0__item1__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="before")

    def parse_to_spec__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.ToSpec] | None:
        return self.parse_to_spec__alt0__item1__alts(pos=pos)

    def parse_to_spec__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Anchor] | None:
        return self.apply__parse_anchor(pos=pos)

    def parse_anchor(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Anchor] | None:
        if alt0 := self.parse_anchor__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_anchor__alt1(pos=pos):
            return alt1
        return None

    def apply__parse_anchor(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Anchor] | None:
        return self.packrat.apply(
            rule_callable=self.parse_anchor, rule_id=10, rule_cache=self._cache__parse_anchor, pos=pos
        )

    def parse_anchor__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Anchor] | None:
        result: fltk.unparse.unparsefmt_cst.Anchor = fltk.unparse.unparsefmt_cst.Anchor(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_anchor__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_label(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_anchor__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Identifier] | None:
        return self.apply__parse_identifier(pos=pos)

    def parse_anchor__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Anchor] | None:
        result: fltk.unparse.unparsefmt_cst.Anchor = fltk.unparse.unparsefmt_cst.Anchor(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_anchor__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_literal(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_anchor__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Literal] | None:
        return self.apply__parse_literal(pos=pos)

    def parse_after(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.After] | None:
        if alt0 := self.parse_after__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_after(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.After] | None:
        return self.packrat.apply(
            rule_callable=self.parse_after, rule_id=11, rule_cache=self._cache__parse_after, pos=pos
        )

    def parse_after__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.After] | None:
        result: fltk.unparse.unparsefmt_cst.After = fltk.unparse.unparsefmt_cst.After(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_after__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        else:
            return None
        if item1 := self.parse_after__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_anchor(child=item1.result)
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_after__alt0__item2(pos=pos):
            pos = item2.pos
        else:
            return None
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_after__alt0__item3(pos=pos):
            pos = item3.pos
            result.children.extend(item3.result.children)
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        if item4 := self.parse_after__alt0__item4(pos=pos):
            pos = item4.pos
        else:
            return None
        if ws_after__item4 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item4.pos
        if item5 := self.parse_after__alt0__item5(pos=pos):
            pos = item5.pos
        if ws_after__item5 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item5.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_after__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="after")

    def parse_after__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Anchor] | None:
        return self.apply__parse_anchor(pos=pos)

    def parse_after__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="{")

    def parse_after__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.After] | None:
        result: fltk.unparse.unparsefmt_cst.After = fltk.unparse.unparsefmt_cst.After(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        while one_result := self.apply__parse_position_spec_statement(pos=pos):
            pos = one_result.pos
            result.append_position_spec_statement(child=one_result.result)
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_after__alt0__item4(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="}")

    def parse_after__alt0__item5(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_before(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Before] | None:
        if alt0 := self.parse_before__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_before(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Before] | None:
        return self.packrat.apply(
            rule_callable=self.parse_before, rule_id=12, rule_cache=self._cache__parse_before, pos=pos
        )

    def parse_before__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Before] | None:
        result: fltk.unparse.unparsefmt_cst.Before = fltk.unparse.unparsefmt_cst.Before(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_before__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        else:
            return None
        if item1 := self.parse_before__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_anchor(child=item1.result)
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_before__alt0__item2(pos=pos):
            pos = item2.pos
        else:
            return None
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_before__alt0__item3(pos=pos):
            pos = item3.pos
            result.children.extend(item3.result.children)
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        if item4 := self.parse_before__alt0__item4(pos=pos):
            pos = item4.pos
        else:
            return None
        if ws_after__item4 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item4.pos
        if item5 := self.parse_before__alt0__item5(pos=pos):
            pos = item5.pos
        if ws_after__item5 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item5.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_before__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="before")

    def parse_before__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Anchor] | None:
        return self.apply__parse_anchor(pos=pos)

    def parse_before__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="{")

    def parse_before__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Before] | None:
        result: fltk.unparse.unparsefmt_cst.Before = fltk.unparse.unparsefmt_cst.Before(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        while one_result := self.apply__parse_position_spec_statement(pos=pos):
            pos = one_result.pos
            result.append_position_spec_statement(child=one_result.result)
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_before__alt0__item4(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="}")

    def parse_before__alt0__item5(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_omit(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Omit] | None:
        if alt0 := self.parse_omit__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_omit(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Omit] | None:
        return self.packrat.apply(
            rule_callable=self.parse_omit, rule_id=13, rule_cache=self._cache__parse_omit, pos=pos
        )

    def parse_omit__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Omit] | None:
        result: fltk.unparse.unparsefmt_cst.Omit = fltk.unparse.unparsefmt_cst.Omit(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_omit__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        else:
            return None
        if item1 := self.parse_omit__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_anchor(child=item1.result)
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_omit__alt0__item2(pos=pos):
            pos = item2.pos
        else:
            return None
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_omit__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="omit")

    def parse_omit__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Anchor] | None:
        return self.apply__parse_anchor(pos=pos)

    def parse_omit__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_render(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Render] | None:
        if alt0 := self.parse_render__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_render(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Render] | None:
        return self.packrat.apply(
            rule_callable=self.parse_render, rule_id=14, rule_cache=self._cache__parse_render, pos=pos
        )

    def parse_render__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Render] | None:
        result: fltk.unparse.unparsefmt_cst.Render = fltk.unparse.unparsefmt_cst.Render(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_render__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        else:
            return None
        if item1 := self.parse_render__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_anchor(child=item1.result)
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_render__alt0__item2(pos=pos):
            pos = item2.pos
        else:
            return None
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        else:
            return None
        if item3 := self.parse_render__alt0__item3(pos=pos):
            pos = item3.pos
            result.append_spacing(child=item3.result)
        else:
            return None
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        if item4 := self.parse_render__alt0__item4(pos=pos):
            pos = item4.pos
        else:
            return None
        if ws_after__item4 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item4.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_render__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="render")

    def parse_render__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Anchor] | None:
        return self.apply__parse_anchor(pos=pos)

    def parse_render__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="as")

    def parse_render__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Spacing] | None:
        return self.apply__parse_spacing(pos=pos)

    def parse_render__alt0__item4(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_position_spec_statement(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.PositionSpecStatement] | None:
        if alt0 := self.parse_position_spec_statement__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_position_spec_statement(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.PositionSpecStatement] | None:
        return self.packrat.apply(
            rule_callable=self.parse_position_spec_statement,
            rule_id=15,
            rule_cache=self._cache__parse_position_spec_statement,
            pos=pos,
        )

    def parse_position_spec_statement__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.PositionSpecStatement] | None:
        result: fltk.unparse.unparsefmt_cst.PositionSpecStatement = fltk.unparse.unparsefmt_cst.PositionSpecStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_position_spec_statement__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_spacing(child=item0.result)
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_position_spec_statement__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_position_spec_statement__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Spacing] | None:
        return self.apply__parse_spacing(pos=pos)

    def parse_position_spec_statement__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_spacing(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Spacing] | None:
        if alt0 := self.parse_spacing__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_spacing(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Spacing] | None:
        return self.packrat.apply(
            rule_callable=self.parse_spacing, rule_id=16, rule_cache=self._cache__parse_spacing, pos=pos
        )

    def parse_spacing__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Spacing] | None:
        result: fltk.unparse.unparsefmt_cst.Spacing = fltk.unparse.unparsefmt_cst.Spacing(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_spacing__alt0__item0(pos=pos):
            pos = item0.pos
            result.children.extend(item0.result.children)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_spacing__alt0__item0__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Spacing] | None:
        if alt0 := self.parse_spacing__alt0__item0__alts__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_spacing__alt0__item0__alts__alt1(pos=pos):
            return alt1
        if alt2 := self.parse_spacing__alt0__item0__alts__alt2(pos=pos):
            return alt2
        if alt3 := self.parse_spacing__alt0__item0__alts__alt3(pos=pos):
            return alt3
        if alt4 := self.parse_spacing__alt0__item0__alts__alt4(pos=pos):
            return alt4
        if alt5 := self.parse_spacing__alt0__item0__alts__alt5(pos=pos):
            return alt5
        return None

    def parse_spacing__alt0__item0__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Spacing] | None:
        result: fltk.unparse.unparsefmt_cst.Spacing = fltk.unparse.unparsefmt_cst.Spacing(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_spacing__alt0__item0__alts__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_nil(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_spacing__alt0__item0__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="nil")

    def parse_spacing__alt0__item0__alts__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Spacing] | None:
        result: fltk.unparse.unparsefmt_cst.Spacing = fltk.unparse.unparsefmt_cst.Spacing(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_spacing__alt0__item0__alts__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_nbsp(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_spacing__alt0__item0__alts__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="nbsp")

    def parse_spacing__alt0__item0__alts__alt2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Spacing] | None:
        result: fltk.unparse.unparsefmt_cst.Spacing = fltk.unparse.unparsefmt_cst.Spacing(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_spacing__alt0__item0__alts__alt2__item0(pos=pos):
            pos = item0.pos
            result.append_bsp(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_spacing__alt0__item0__alts__alt2__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="bsp")

    def parse_spacing__alt0__item0__alts__alt3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Spacing] | None:
        result: fltk.unparse.unparsefmt_cst.Spacing = fltk.unparse.unparsefmt_cst.Spacing(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_spacing__alt0__item0__alts__alt3__item0(pos=pos):
            pos = item0.pos
            result.append_soft(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_spacing__alt0__item0__alts__alt3__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="soft")

    def parse_spacing__alt0__item0__alts__alt4(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Spacing] | None:
        result: fltk.unparse.unparsefmt_cst.Spacing = fltk.unparse.unparsefmt_cst.Spacing(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_spacing__alt0__item0__alts__alt4__item0(pos=pos):
            pos = item0.pos
            result.append_hard(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_spacing__alt0__item0__alts__alt4__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="hard")

    def parse_spacing__alt0__item0__alts__alt5(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Spacing] | None:
        result: fltk.unparse.unparsefmt_cst.Spacing = fltk.unparse.unparsefmt_cst.Spacing(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_spacing__alt0__item0__alts__alt5__item0(pos=pos):
            pos = item0.pos
            result.append_blank(child=item0.result)
        else:
            return None
        if item1 := self.parse_spacing__alt0__item0__alts__alt5__item1(pos=pos):
            pos = item1.pos
            result.children.extend(item1.result.children)
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_spacing__alt0__item0__alts__alt5__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="blank")

    def parse_spacing__alt0__item0__alts__alt5__item1__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Spacing] | None:
        if alt0 := self.parse_spacing__alt0__item0__alts__alt5__item1__alts__alt0(pos=pos):
            return alt0
        return None

    def parse_spacing__alt0__item0__alts__alt5__item1__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Spacing] | None:
        result: fltk.unparse.unparsefmt_cst.Spacing = fltk.unparse.unparsefmt_cst.Spacing(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if initial_ws := self.apply__parse__trivia(pos=pos):
            pos = initial_ws.pos
        if item0 := self.parse_spacing__alt0__item0__alts__alt5__item1__alts__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_spacing__alt0__item0__alts__alt5__item1__alts__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_num_blanks(child=item1.result)
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_spacing__alt0__item0__alts__alt5__item1__alts__alt0__item2(pos=pos):
            pos = item2.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_spacing__alt0__item0__alts__alt5__item1__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="(")

    def parse_spacing__alt0__item0__alts__alt5__item1__alts__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Integer] | None:
        return self.apply__parse_integer(pos=pos)

    def parse_spacing__alt0__item0__alts__alt5__item1__alts__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=")")

    def parse_spacing__alt0__item0__alts__alt5__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Spacing] | None:
        return self.parse_spacing__alt0__item0__alts__alt5__item1__alts(pos=pos)

    def parse_spacing__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Spacing] | None:
        return self.parse_spacing__alt0__item0__alts(pos=pos)

    def parse_doc_literal(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.DocLiteral] | None:
        if alt0 := self.parse_doc_literal__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_doc_literal__alt1(pos=pos):
            return alt1
        if alt2 := self.parse_doc_literal__alt2(pos=pos):
            return alt2
        if alt3 := self.parse_doc_literal__alt3(pos=pos):
            return alt3
        if alt4 := self.parse_doc_literal__alt4(pos=pos):
            return alt4
        return None

    def apply__parse_doc_literal(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.DocLiteral] | None:
        return self.packrat.apply(
            rule_callable=self.parse_doc_literal, rule_id=17, rule_cache=self._cache__parse_doc_literal, pos=pos
        )

    def parse_doc_literal__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.DocLiteral] | None:
        result: fltk.unparse.unparsefmt_cst.DocLiteral = fltk.unparse.unparsefmt_cst.DocLiteral(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_doc_literal__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_concat_literal(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_doc_literal__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.ConcatLiteral] | None:
        return self.apply__parse_concat_literal(pos=pos)

    def parse_doc_literal__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.DocLiteral] | None:
        result: fltk.unparse.unparsefmt_cst.DocLiteral = fltk.unparse.unparsefmt_cst.DocLiteral(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_doc_literal__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_join_literal(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_doc_literal__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.JoinLiteral] | None:
        return self.apply__parse_join_literal(pos=pos)

    def parse_doc_literal__alt2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.DocLiteral] | None:
        result: fltk.unparse.unparsefmt_cst.DocLiteral = fltk.unparse.unparsefmt_cst.DocLiteral(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_doc_literal__alt2__item0(pos=pos):
            pos = item0.pos
            result.append_compound_literal(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_doc_literal__alt2__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.CompoundLiteral] | None:
        return self.apply__parse_compound_literal(pos=pos)

    def parse_doc_literal__alt3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.DocLiteral] | None:
        result: fltk.unparse.unparsefmt_cst.DocLiteral = fltk.unparse.unparsefmt_cst.DocLiteral(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_doc_literal__alt3__item0(pos=pos):
            pos = item0.pos
            result.append_text_literal(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_doc_literal__alt3__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.TextLiteral] | None:
        return self.apply__parse_text_literal(pos=pos)

    def parse_doc_literal__alt4(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.DocLiteral] | None:
        result: fltk.unparse.unparsefmt_cst.DocLiteral = fltk.unparse.unparsefmt_cst.DocLiteral(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_doc_literal__alt4__item0(pos=pos):
            pos = item0.pos
            result.append_spacing(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_doc_literal__alt4__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Spacing] | None:
        return self.apply__parse_spacing(pos=pos)

    def parse_text_literal(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.TextLiteral] | None:
        if alt0 := self.parse_text_literal__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_text_literal(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.TextLiteral] | None:
        return self.packrat.apply(
            rule_callable=self.parse_text_literal, rule_id=18, rule_cache=self._cache__parse_text_literal, pos=pos
        )

    def parse_text_literal__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.TextLiteral] | None:
        result: fltk.unparse.unparsefmt_cst.TextLiteral = fltk.unparse.unparsefmt_cst.TextLiteral(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_text_literal__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_text_literal__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_text_literal__alt0__item2(pos=pos):
            pos = item2.pos
            result.append_text(child=item2.result)
        else:
            return None
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_text_literal__alt0__item3(pos=pos):
            pos = item3.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_text_literal__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="text")

    def parse_text_literal__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="(")

    def parse_text_literal__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Literal] | None:
        return self.apply__parse_literal(pos=pos)

    def parse_text_literal__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=")")

    def parse_concat_literal(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.ConcatLiteral] | None:
        if alt0 := self.parse_concat_literal__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_concat_literal(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.ConcatLiteral] | None:
        return self.packrat.apply(
            rule_callable=self.parse_concat_literal, rule_id=19, rule_cache=self._cache__parse_concat_literal, pos=pos
        )

    def parse_concat_literal__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.ConcatLiteral] | None:
        result: fltk.unparse.unparsefmt_cst.ConcatLiteral = fltk.unparse.unparsefmt_cst.ConcatLiteral(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_concat_literal__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_concat_literal__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_concat_literal__alt0__item2(pos=pos):
            pos = item2.pos
            result.append_doc_list_literal(child=item2.result)
        else:
            return None
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_concat_literal__alt0__item3(pos=pos):
            pos = item3.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_concat_literal__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="concat")

    def parse_concat_literal__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="(")

    def parse_concat_literal__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.DocListLiteral] | None:
        return self.apply__parse_doc_list_literal(pos=pos)

    def parse_concat_literal__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=")")

    def parse_join_literal(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.JoinLiteral] | None:
        if alt0 := self.parse_join_literal__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_join_literal(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.JoinLiteral] | None:
        return self.packrat.apply(
            rule_callable=self.parse_join_literal, rule_id=20, rule_cache=self._cache__parse_join_literal, pos=pos
        )

    def parse_join_literal__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.JoinLiteral] | None:
        result: fltk.unparse.unparsefmt_cst.JoinLiteral = fltk.unparse.unparsefmt_cst.JoinLiteral(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_join_literal__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_join_literal__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_join_literal__alt0__item2(pos=pos):
            pos = item2.pos
            result.append_separator(child=item2.result)
        else:
            return None
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_join_literal__alt0__item3(pos=pos):
            pos = item3.pos
        else:
            return None
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        if item4 := self.parse_join_literal__alt0__item4(pos=pos):
            pos = item4.pos
            result.append_doc_list_literal(child=item4.result)
        else:
            return None
        if ws_after__item4 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item4.pos
        if item5 := self.parse_join_literal__alt0__item5(pos=pos):
            pos = item5.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_join_literal__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="join")

    def parse_join_literal__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="(")

    def parse_join_literal__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.DocLiteral] | None:
        return self.apply__parse_doc_literal(pos=pos)

    def parse_join_literal__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=",")

    def parse_join_literal__alt0__item4(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.DocListLiteral] | None:
        return self.apply__parse_doc_list_literal(pos=pos)

    def parse_join_literal__alt0__item5(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=")")

    def parse_doc_list_literal(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.DocListLiteral] | None:
        if alt0 := self.parse_doc_list_literal__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_doc_list_literal(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.DocListLiteral] | None:
        return self.packrat.apply(
            rule_callable=self.parse_doc_list_literal,
            rule_id=21,
            rule_cache=self._cache__parse_doc_list_literal,
            pos=pos,
        )

    def parse_doc_list_literal__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.DocListLiteral] | None:
        result: fltk.unparse.unparsefmt_cst.DocListLiteral = fltk.unparse.unparsefmt_cst.DocListLiteral(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_doc_list_literal__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_doc_list_literal__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_doc_literal(child=item1.result)
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_doc_list_literal__alt0__item2(pos=pos):
            pos = item2.pos
            result.children.extend(item2.result.children)
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_doc_list_literal__alt0__item3(pos=pos):
            pos = item3.pos
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        if item4 := self.parse_doc_list_literal__alt0__item4(pos=pos):
            pos = item4.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_doc_list_literal__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="[")

    def parse_doc_list_literal__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.DocLiteral] | None:
        return self.apply__parse_doc_literal(pos=pos)

    def parse_doc_list_literal__alt0__item2__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.DocListLiteral] | None:
        if alt0 := self.parse_doc_list_literal__alt0__item2__alts__alt0(pos=pos):
            return alt0
        return None

    def parse_doc_list_literal__alt0__item2__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.DocListLiteral] | None:
        result: fltk.unparse.unparsefmt_cst.DocListLiteral = fltk.unparse.unparsefmt_cst.DocListLiteral(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_doc_list_literal__alt0__item2__alts__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_doc_list_literal__alt0__item2__alts__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_doc_literal(child=item1.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_doc_list_literal__alt0__item2__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=",")

    def parse_doc_list_literal__alt0__item2__alts__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.DocLiteral] | None:
        return self.apply__parse_doc_literal(pos=pos)

    def parse_doc_list_literal__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.DocListLiteral] | None:
        result: fltk.unparse.unparsefmt_cst.DocListLiteral = fltk.unparse.unparsefmt_cst.DocListLiteral(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        while one_result := self.parse_doc_list_literal__alt0__item2__alts(pos=pos):
            pos = one_result.pos
            result.children.extend(one_result.result.children)
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_doc_list_literal__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=",")

    def parse_doc_list_literal__alt0__item4(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="]")

    def parse_compound_literal(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.CompoundLiteral] | None:
        if alt0 := self.parse_compound_literal__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_compound_literal(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.CompoundLiteral] | None:
        return self.packrat.apply(
            rule_callable=self.parse_compound_literal,
            rule_id=22,
            rule_cache=self._cache__parse_compound_literal,
            pos=pos,
        )

    def parse_compound_literal__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.CompoundLiteral] | None:
        result: fltk.unparse.unparsefmt_cst.CompoundLiteral = fltk.unparse.unparsefmt_cst.CompoundLiteral(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_compound_literal__alt0__item0(pos=pos):
            pos = item0.pos
            result.children.extend(item0.result.children)
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_compound_literal__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_compound_literal__alt0__item2(pos=pos):
            pos = item2.pos
            result.append_doc_literal(child=item2.result)
        else:
            return None
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_compound_literal__alt0__item3(pos=pos):
            pos = item3.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_compound_literal__alt0__item0__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.CompoundLiteral] | None:
        if alt0 := self.parse_compound_literal__alt0__item0__alts__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_compound_literal__alt0__item0__alts__alt1(pos=pos):
            return alt1
        return None

    def parse_compound_literal__alt0__item0__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.CompoundLiteral] | None:
        result: fltk.unparse.unparsefmt_cst.CompoundLiteral = fltk.unparse.unparsefmt_cst.CompoundLiteral(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_compound_literal__alt0__item0__alts__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_group(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_compound_literal__alt0__item0__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="group")

    def parse_compound_literal__alt0__item0__alts__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.CompoundLiteral] | None:
        result: fltk.unparse.unparsefmt_cst.CompoundLiteral = fltk.unparse.unparsefmt_cst.CompoundLiteral(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_compound_literal__alt0__item0__alts__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_nest(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_compound_literal__alt0__item0__alts__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="nest")

    def parse_compound_literal__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.CompoundLiteral] | None:
        return self.parse_compound_literal__alt0__item0__alts(pos=pos)

    def parse_compound_literal__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="(")

    def parse_compound_literal__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.DocLiteral] | None:
        return self.apply__parse_doc_literal(pos=pos)

    def parse_compound_literal__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=")")

    def parse_trivia_preserve(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.TriviaPreserve] | None:
        if alt0 := self.parse_trivia_preserve__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_trivia_preserve(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.TriviaPreserve] | None:
        return self.packrat.apply(
            rule_callable=self.parse_trivia_preserve, rule_id=23, rule_cache=self._cache__parse_trivia_preserve, pos=pos
        )

    def parse_trivia_preserve__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.TriviaPreserve] | None:
        result: fltk.unparse.unparsefmt_cst.TriviaPreserve = fltk.unparse.unparsefmt_cst.TriviaPreserve(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_trivia_preserve__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_trivia_preserve__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_trivia_preserve__alt0__item2(pos=pos):
            pos = item2.pos
            result.append_trivia_node_list(child=item2.result)
        else:
            return None
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_trivia_preserve__alt0__item3(pos=pos):
            pos = item3.pos
        else:
            return None
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_trivia_preserve__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="trivia_preserve")

    def parse_trivia_preserve__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=":")

    def parse_trivia_preserve__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.TriviaNodeList] | None:
        return self.apply__parse_trivia_node_list(pos=pos)

    def parse_trivia_preserve__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_trivia_node_list(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.TriviaNodeList] | None:
        if alt0 := self.parse_trivia_node_list__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_trivia_node_list(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.TriviaNodeList] | None:
        return self.packrat.apply(
            rule_callable=self.parse_trivia_node_list,
            rule_id=24,
            rule_cache=self._cache__parse_trivia_node_list,
            pos=pos,
        )

    def parse_trivia_node_list__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.TriviaNodeList] | None:
        result: fltk.unparse.unparsefmt_cst.TriviaNodeList = fltk.unparse.unparsefmt_cst.TriviaNodeList(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_trivia_node_list__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_identifier(child=item0.result)
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_trivia_node_list__alt0__item1(pos=pos):
            pos = item1.pos
            result.children.extend(item1.result.children)
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_trivia_node_list__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Identifier] | None:
        return self.apply__parse_identifier(pos=pos)

    def parse_trivia_node_list__alt0__item1__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.TriviaNodeList] | None:
        if alt0 := self.parse_trivia_node_list__alt0__item1__alts__alt0(pos=pos):
            return alt0
        return None

    def parse_trivia_node_list__alt0__item1__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.TriviaNodeList] | None:
        result: fltk.unparse.unparsefmt_cst.TriviaNodeList = fltk.unparse.unparsefmt_cst.TriviaNodeList(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_trivia_node_list__alt0__item1__alts__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_trivia_node_list__alt0__item1__alts__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_identifier(child=item1.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_trivia_node_list__alt0__item1__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=",")

    def parse_trivia_node_list__alt0__item1__alts__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Identifier] | None:
        return self.apply__parse_identifier(pos=pos)

    def parse_trivia_node_list__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.TriviaNodeList] | None:
        result: fltk.unparse.unparsefmt_cst.TriviaNodeList = fltk.unparse.unparsefmt_cst.TriviaNodeList(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        while one_result := self.parse_trivia_node_list__alt0__item1__alts(pos=pos):
            pos = one_result.pos
            result.children.extend(one_result.result.children)
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_identifier(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Identifier] | None:
        if alt0 := self.parse_identifier__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_identifier(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Identifier] | None:
        return self.packrat.apply(
            rule_callable=self.parse_identifier, rule_id=25, rule_cache=self._cache__parse_identifier, pos=pos
        )

    def parse_identifier__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Identifier] | None:
        result: fltk.unparse.unparsefmt_cst.Identifier = fltk.unparse.unparsefmt_cst.Identifier(
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
        return self.consume_regex(pos=pos, regex="[a-zA-Z_][a-zA-Z0-9_]*")

    def parse_literal(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Literal] | None:
        if alt0 := self.parse_literal__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_literal(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Literal] | None:
        return self.packrat.apply(
            rule_callable=self.parse_literal, rule_id=26, rule_cache=self._cache__parse_literal, pos=pos
        )

    def parse_literal__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Literal] | None:
        result: fltk.unparse.unparsefmt_cst.Literal = fltk.unparse.unparsefmt_cst.Literal(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
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

    def parse_integer(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Integer] | None:
        if alt0 := self.parse_integer__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_integer(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Integer] | None:
        return self.packrat.apply(
            rule_callable=self.parse_integer, rule_id=27, rule_cache=self._cache__parse_integer, pos=pos
        )

    def parse_integer__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Integer] | None:
        result: fltk.unparse.unparsefmt_cst.Integer = fltk.unparse.unparsefmt_cst.Integer(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_integer__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_value(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_integer__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_regex(pos=pos, regex="[0-9]+")

    def parse__trivia(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Trivia] | None:
        if alt0 := self.parse__trivia__alt0(pos=pos):
            return alt0
        return None

    def apply__parse__trivia(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Trivia] | None:
        return self.packrat.apply(
            rule_callable=self.parse__trivia, rule_id=28, rule_cache=self._cache__parse__trivia, pos=pos
        )

    def parse__trivia__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Trivia] | None:
        result: fltk.unparse.unparsefmt_cst.Trivia = fltk.unparse.unparsefmt_cst.Trivia(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse__trivia__alt0__item0(pos=pos):
            pos = item0.pos
            result.children.extend(item0.result.children)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse__trivia__alt0__item0__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Trivia] | None:
        if alt0 := self.parse__trivia__alt0__item0__alts__alt0(pos=pos):
            return alt0
        if alt1 := self.parse__trivia__alt0__item0__alts__alt1(pos=pos):
            return alt1
        return None

    def parse__trivia__alt0__item0__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Trivia] | None:
        result: fltk.unparse.unparsefmt_cst.Trivia = fltk.unparse.unparsefmt_cst.Trivia(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse__trivia__alt0__item0__alts__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_line_comment(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse__trivia__alt0__item0__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.LineComment] | None:
        return self.apply__parse_line_comment(pos=pos)

    def parse__trivia__alt0__item0__alts__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Trivia] | None:
        result: fltk.unparse.unparsefmt_cst.Trivia = fltk.unparse.unparsefmt_cst.Trivia(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse__trivia__alt0__item0__alts__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_line_comment(child=item0.result)
        if ws_after__item0 := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__item0.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse__trivia__alt0__item0__alts__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.LineComment] | None:
        return self.apply__parse_line_comment(pos=pos)

    def parse__trivia__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.Trivia] | None:
        result: fltk.unparse.unparsefmt_cst.Trivia = fltk.unparse.unparsefmt_cst.Trivia(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        while one_result := self.parse__trivia__alt0__item0__alts(pos=pos):
            pos = one_result.pos
            result.children.extend(one_result.result.children)
        if pos == result.span.start:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_line_comment(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.LineComment] | None:
        if alt0 := self.parse_line_comment__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_line_comment(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.LineComment] | None:
        return self.packrat.apply(
            rule_callable=self.parse_line_comment, rule_id=29, rule_cache=self._cache__parse_line_comment, pos=pos
        )

    def parse_line_comment__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.unparse.unparsefmt_cst.LineComment] | None:
        result: fltk.unparse.unparsefmt_cst.LineComment = fltk.unparse.unparsefmt_cst.LineComment(
            span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
        )
        if item0 := self.parse_line_comment__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_prefix(child=item0.result)
        else:
            return None
        if item1 := self.parse_line_comment__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_content(child=item1.result)
        else:
            return None
        if item2 := self.parse_line_comment__alt0__item2(pos=pos):
            pos = item2.pos
            result.append_newline(child=item2.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_line_comment__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="//")

    def parse_line_comment__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_regex(pos=pos, regex="[^\\n]*")

    def parse_line_comment__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="\n")
