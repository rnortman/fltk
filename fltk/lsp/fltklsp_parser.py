from __future__ import annotations

import collections.abc
import typing

import fltk.fegen.pyrt.errors
import fltk.fegen.pyrt.memo
import fltk.fegen.pyrt.terminalsrc
import fltk.lsp.fltklsp_cst


class Parser:
    """Parser"""

    def __init__(self, terminalsrc: fltk.fegen.pyrt.terminalsrc.TerminalSource) -> None:
        self.terminalsrc = terminalsrc
        self._source_text = fltk.fegen.pyrt.terminalsrc.SourceText(
            text=terminalsrc.terminals, filename=terminalsrc.filename
        )
        self.packrat: fltk.fegen.pyrt.memo.Packrat[int, int] = fltk.fegen.pyrt.memo.Packrat()
        self.error_tracker: fltk.fegen.pyrt.errors.ErrorTracker[int] = fltk.fegen.pyrt.errors.ErrorTracker()
        self.rule_names: typing.Sequence[str] = [
            "lsp_spec",
            "statement",
            "rule_config",
            "rule_statement",
            "scope_stmt",
            "def_stmt",
            "ref_stmt",
            "namespace_stmt",
            "anchor_list",
            "anchor",
            "qualifier",
            "kind_list",
            "dotted_name",
            "identifier",
            "literal",
            "_trivia",
            "line_comment",
        ]
        self._cache__parse_lsp_spec: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.lsp.fltklsp_cst.LspSpec]
        ] = {}
        self._cache__parse_statement: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.lsp.fltklsp_cst.Statement]
        ] = {}
        self._cache__parse_rule_config: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.lsp.fltklsp_cst.RuleConfig]
        ] = {}
        self._cache__parse_rule_statement: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.lsp.fltklsp_cst.RuleStatement]
        ] = {}
        self._cache__parse_scope_stmt: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.lsp.fltklsp_cst.ScopeStmt]
        ] = {}
        self._cache__parse_def_stmt: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.lsp.fltklsp_cst.DefStmt]
        ] = {}
        self._cache__parse_ref_stmt: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.lsp.fltklsp_cst.RefStmt]
        ] = {}
        self._cache__parse_namespace_stmt: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.lsp.fltklsp_cst.NamespaceStmt]
        ] = {}
        self._cache__parse_anchor_list: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.lsp.fltklsp_cst.AnchorList]
        ] = {}
        self._cache__parse_anchor: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.lsp.fltklsp_cst.Anchor]
        ] = {}
        self._cache__parse_qualifier: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.lsp.fltklsp_cst.Qualifier]
        ] = {}
        self._cache__parse_kind_list: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.lsp.fltklsp_cst.KindList]
        ] = {}
        self._cache__parse_dotted_name: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.lsp.fltklsp_cst.DottedName]
        ] = {}
        self._cache__parse_identifier: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.lsp.fltklsp_cst.Identifier]
        ] = {}
        self._cache__parse_literal: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.lsp.fltklsp_cst.Literal]
        ] = {}
        self._cache__parse__trivia: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.lsp.fltklsp_cst.Trivia]
        ] = {}
        self._cache__parse_line_comment: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.lsp.fltklsp_cst.LineComment]
        ] = {}

    def consume_literal(
        self, pos: int, literal: str
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        if span := self.terminalsrc.consume_literal(pos=pos, literal=literal):
            return fltk.fegen.pyrt.memo.ApplyResult(
                pos=span.end,
                result=fltk.fegen.pyrt.terminalsrc.Span.with_source(span.start, span.end, self._source_text),
            )
        self.error_tracker.fail_literal(pos=pos, rule_id=self.packrat.invocation_stack[-1], literal=literal)
        return None

    def consume_regex(
        self, pos: int, regex: str
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        if span := self.terminalsrc.consume_regex(pos=pos, regex=regex):
            return fltk.fegen.pyrt.memo.ApplyResult(
                pos=span.end,
                result=fltk.fegen.pyrt.terminalsrc.Span.with_source(span.start, span.end, self._source_text),
            )
        self.error_tracker.fail_regex(pos=pos, rule_id=self.packrat.invocation_stack[-1], regex=regex)
        return None

    def parse_lsp_spec(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.LspSpec] | None:
        if alt0 := self.parse_lsp_spec__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_lsp_spec(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.LspSpec] | None:
        return self.packrat.apply(
            rule_callable=self.parse_lsp_spec, rule_id=0, rule_cache=self._cache__parse_lsp_spec, pos=pos
        )

    def parse_lsp_spec__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.LspSpec] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.LspSpec = fltk.lsp.fltklsp_cst.LspSpec(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if initial_ws := self.apply__parse__trivia(pos=pos):
            pos = initial_ws.pos
        if item0 := self.parse_lsp_spec__alt0__item0(pos=pos):
            pos = item0.pos
            result.extend_children(other=item0.result)
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_lsp_spec__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.LspSpec] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.LspSpec = fltk.lsp.fltklsp_cst.LspSpec(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        while one_result := self.apply__parse_statement(pos=pos):
            if not one_result.pos > pos:
                break
            pos = one_result.pos
            result.append_statement(child=one_result.result)
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_statement(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Statement] | None:
        if alt0 := self.parse_statement__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_statement__alt1(pos=pos):
            return alt1
        return None

    def apply__parse_statement(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Statement] | None:
        return self.packrat.apply(
            rule_callable=self.parse_statement, rule_id=1, rule_cache=self._cache__parse_statement, pos=pos
        )

    def parse_statement__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Statement] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.Statement = fltk.lsp.fltklsp_cst.Statement(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_statement__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_scope_stmt(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_statement__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.ScopeStmt] | None:
        return self.apply__parse_scope_stmt(pos=pos)

    def parse_statement__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Statement] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.Statement = fltk.lsp.fltklsp_cst.Statement(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_statement__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_rule_config(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_statement__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.RuleConfig] | None:
        return self.apply__parse_rule_config(pos=pos)

    def parse_rule_config(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.RuleConfig] | None:
        if alt0 := self.parse_rule_config__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_rule_config(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.RuleConfig] | None:
        return self.packrat.apply(
            rule_callable=self.parse_rule_config, rule_id=2, rule_cache=self._cache__parse_rule_config, pos=pos
        )

    def parse_rule_config__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.RuleConfig] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.RuleConfig = fltk.lsp.fltklsp_cst.RuleConfig(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_rule_config__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        else:
            return None
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
            result.extend_children(other=item3.result)
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        if item4 := self.parse_rule_config__alt0__item4(pos=pos):
            pos = item4.pos
        else:
            return None
        if ws_after__item4 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item4.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_config__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="rule")

    def parse_rule_config__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Identifier] | None:
        return self.apply__parse_identifier(pos=pos)

    def parse_rule_config__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="{")

    def parse_rule_config__alt0__item3__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.RuleConfig] | None:
        if alt0 := self.parse_rule_config__alt0__item3__alts__alt0(pos=pos):
            return alt0
        return None

    def parse_rule_config__alt0__item3__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.RuleConfig] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.RuleConfig = fltk.lsp.fltklsp_cst.RuleConfig(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_rule_config__alt0__item3__alts__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_rule_statement(child=item0.result)
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_config__alt0__item3__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.RuleStatement] | None:
        return self.apply__parse_rule_statement(pos=pos)

    def parse_rule_config__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.RuleConfig] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.RuleConfig = fltk.lsp.fltklsp_cst.RuleConfig(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        while one_result := self.parse_rule_config__alt0__item3__alts(pos=pos):
            if not one_result.pos > pos:
                break
            pos = one_result.pos
            result.extend_children(other=one_result.result)
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_config__alt0__item4(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="}")

    def parse_rule_statement(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.RuleStatement] | None:
        if alt0 := self.parse_rule_statement__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_rule_statement__alt1(pos=pos):
            return alt1
        if alt2 := self.parse_rule_statement__alt2(pos=pos):
            return alt2
        if alt3 := self.parse_rule_statement__alt3(pos=pos):
            return alt3
        return None

    def apply__parse_rule_statement(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.RuleStatement] | None:
        return self.packrat.apply(
            rule_callable=self.parse_rule_statement, rule_id=3, rule_cache=self._cache__parse_rule_statement, pos=pos
        )

    def parse_rule_statement__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.RuleStatement] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.RuleStatement = fltk.lsp.fltklsp_cst.RuleStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_rule_statement__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_scope_stmt(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_statement__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.ScopeStmt] | None:
        return self.apply__parse_scope_stmt(pos=pos)

    def parse_rule_statement__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.RuleStatement] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.RuleStatement = fltk.lsp.fltklsp_cst.RuleStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_rule_statement__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_def_stmt(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_statement__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.DefStmt] | None:
        return self.apply__parse_def_stmt(pos=pos)

    def parse_rule_statement__alt2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.RuleStatement] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.RuleStatement = fltk.lsp.fltklsp_cst.RuleStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_rule_statement__alt2__item0(pos=pos):
            pos = item0.pos
            result.append_ref_stmt(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_statement__alt2__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.RefStmt] | None:
        return self.apply__parse_ref_stmt(pos=pos)

    def parse_rule_statement__alt3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.RuleStatement] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.RuleStatement = fltk.lsp.fltklsp_cst.RuleStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_rule_statement__alt3__item0(pos=pos):
            pos = item0.pos
            result.append_namespace_stmt(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_statement__alt3__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.NamespaceStmt] | None:
        return self.apply__parse_namespace_stmt(pos=pos)

    def parse_scope_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.ScopeStmt] | None:
        if alt0 := self.parse_scope_stmt__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_scope_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.ScopeStmt] | None:
        return self.packrat.apply(
            rule_callable=self.parse_scope_stmt, rule_id=4, rule_cache=self._cache__parse_scope_stmt, pos=pos
        )

    def parse_scope_stmt__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.ScopeStmt] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.ScopeStmt = fltk.lsp.fltklsp_cst.ScopeStmt(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_scope_stmt__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        else:
            return None
        if item1 := self.parse_scope_stmt__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_anchor_list(child=item1.result)
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_scope_stmt__alt0__item2(pos=pos):
            pos = item2.pos
        else:
            return None
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_scope_stmt__alt0__item3(pos=pos):
            pos = item3.pos
            result.append_scope(child=item3.result)
        else:
            return None
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        if item4 := self.parse_scope_stmt__alt0__item4(pos=pos):
            pos = item4.pos
        else:
            return None
        if ws_after__item4 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item4.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_scope_stmt__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="scope")

    def parse_scope_stmt__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.AnchorList] | None:
        return self.apply__parse_anchor_list(pos=pos)

    def parse_scope_stmt__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=":")

    def parse_scope_stmt__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.DottedName] | None:
        return self.apply__parse_dotted_name(pos=pos)

    def parse_scope_stmt__alt0__item4(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_def_stmt(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.DefStmt] | None:
        if alt0 := self.parse_def_stmt__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_def_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.DefStmt] | None:
        return self.packrat.apply(
            rule_callable=self.parse_def_stmt, rule_id=5, rule_cache=self._cache__parse_def_stmt, pos=pos
        )

    def parse_def_stmt__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.DefStmt] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.DefStmt = fltk.lsp.fltklsp_cst.DefStmt(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_def_stmt__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        else:
            return None
        if item1 := self.parse_def_stmt__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_anchor(child=item1.result)
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_def_stmt__alt0__item2(pos=pos):
            pos = item2.pos
        else:
            return None
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_def_stmt__alt0__item3(pos=pos):
            pos = item3.pos
            result.append_kind(child=item3.result)
        else:
            return None
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        if item4 := self.parse_def_stmt__alt0__item4(pos=pos):
            pos = item4.pos
        else:
            return None
        if ws_after__item4 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item4.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_def_stmt__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="def")

    def parse_def_stmt__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Anchor] | None:
        return self.apply__parse_anchor(pos=pos)

    def parse_def_stmt__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=":")

    def parse_def_stmt__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.DottedName] | None:
        return self.apply__parse_dotted_name(pos=pos)

    def parse_def_stmt__alt0__item4(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_ref_stmt(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.RefStmt] | None:
        if alt0 := self.parse_ref_stmt__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_ref_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.RefStmt] | None:
        return self.packrat.apply(
            rule_callable=self.parse_ref_stmt, rule_id=6, rule_cache=self._cache__parse_ref_stmt, pos=pos
        )

    def parse_ref_stmt__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.RefStmt] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.RefStmt = fltk.lsp.fltklsp_cst.RefStmt(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_ref_stmt__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        else:
            return None
        if item1 := self.parse_ref_stmt__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_anchor(child=item1.result)
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_ref_stmt__alt0__item2(pos=pos):
            pos = item2.pos
        else:
            return None
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_ref_stmt__alt0__item3(pos=pos):
            pos = item3.pos
            result.append_kind_list(child=item3.result)
        else:
            return None
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        if item4 := self.parse_ref_stmt__alt0__item4(pos=pos):
            pos = item4.pos
        else:
            return None
        if ws_after__item4 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item4.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_ref_stmt__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="ref")

    def parse_ref_stmt__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Anchor] | None:
        return self.apply__parse_anchor(pos=pos)

    def parse_ref_stmt__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=":")

    def parse_ref_stmt__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.KindList] | None:
        return self.apply__parse_kind_list(pos=pos)

    def parse_ref_stmt__alt0__item4(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_namespace_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.NamespaceStmt] | None:
        if alt0 := self.parse_namespace_stmt__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_namespace_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.NamespaceStmt] | None:
        return self.packrat.apply(
            rule_callable=self.parse_namespace_stmt, rule_id=7, rule_cache=self._cache__parse_namespace_stmt, pos=pos
        )

    def parse_namespace_stmt__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.NamespaceStmt] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.NamespaceStmt = fltk.lsp.fltklsp_cst.NamespaceStmt(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_namespace_stmt__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_namespace_stmt__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_namespace_stmt__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="namespace")

    def parse_namespace_stmt__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_anchor_list(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.AnchorList] | None:
        if alt0 := self.parse_anchor_list__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_anchor_list(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.AnchorList] | None:
        return self.packrat.apply(
            rule_callable=self.parse_anchor_list, rule_id=8, rule_cache=self._cache__parse_anchor_list, pos=pos
        )

    def parse_anchor_list__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.AnchorList] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.AnchorList = fltk.lsp.fltklsp_cst.AnchorList(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_anchor_list__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_anchor(child=item0.result)
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_anchor_list__alt0__item1(pos=pos):
            pos = item1.pos
            result.extend_children(other=item1.result)
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_anchor_list__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Anchor] | None:
        return self.apply__parse_anchor(pos=pos)

    def parse_anchor_list__alt0__item1__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.AnchorList] | None:
        if alt0 := self.parse_anchor_list__alt0__item1__alts__alt0(pos=pos):
            return alt0
        return None

    def parse_anchor_list__alt0__item1__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.AnchorList] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.AnchorList = fltk.lsp.fltklsp_cst.AnchorList(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_anchor_list__alt0__item1__alts__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_anchor_list__alt0__item1__alts__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_anchor(child=item1.result)
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_anchor_list__alt0__item1__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=",")

    def parse_anchor_list__alt0__item1__alts__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Anchor] | None:
        return self.apply__parse_anchor(pos=pos)

    def parse_anchor_list__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.AnchorList] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.AnchorList = fltk.lsp.fltklsp_cst.AnchorList(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        while one_result := self.parse_anchor_list__alt0__item1__alts(pos=pos):
            if not one_result.pos > pos:
                break
            pos = one_result.pos
            result.extend_children(other=one_result.result)
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_anchor(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Anchor] | None:
        if alt0 := self.parse_anchor__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_anchor__alt1(pos=pos):
            return alt1
        return None

    def apply__parse_anchor(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Anchor] | None:
        return self.packrat.apply(
            rule_callable=self.parse_anchor, rule_id=9, rule_cache=self._cache__parse_anchor, pos=pos
        )

    def parse_anchor__alt0(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Anchor] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.Anchor = fltk.lsp.fltklsp_cst.Anchor(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_anchor__alt0__item0(pos=pos):
            pos = item0.pos
            result.extend_children(other=item0.result)
        if item1 := self.parse_anchor__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_name(child=item1.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_anchor__alt0__item0__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Anchor] | None:
        if alt0 := self.parse_anchor__alt0__item0__alts__alt0(pos=pos):
            return alt0
        return None

    def parse_anchor__alt0__item0__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Anchor] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.Anchor = fltk.lsp.fltklsp_cst.Anchor(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_anchor__alt0__item0__alts__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_qualifier(child=item0.result)
        else:
            return None
        if item1 := self.parse_anchor__alt0__item0__alts__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_anchor__alt0__item0__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Qualifier] | None:
        return self.apply__parse_qualifier(pos=pos)

    def parse_anchor__alt0__item0__alts__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=":")

    def parse_anchor__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Anchor] | None:
        return self.parse_anchor__alt0__item0__alts(pos=pos)

    def parse_anchor__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Identifier] | None:
        return self.apply__parse_identifier(pos=pos)

    def parse_anchor__alt1(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Anchor] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.Anchor = fltk.lsp.fltklsp_cst.Anchor(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_anchor__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_literal(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_anchor__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Literal] | None:
        return self.apply__parse_literal(pos=pos)

    def parse_qualifier(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Qualifier] | None:
        if alt0 := self.parse_qualifier__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_qualifier__alt1(pos=pos):
            return alt1
        return None

    def apply__parse_qualifier(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Qualifier] | None:
        return self.packrat.apply(
            rule_callable=self.parse_qualifier, rule_id=10, rule_cache=self._cache__parse_qualifier, pos=pos
        )

    def parse_qualifier__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Qualifier] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.Qualifier = fltk.lsp.fltklsp_cst.Qualifier(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_qualifier__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_label(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_qualifier__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="label")

    def parse_qualifier__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Qualifier] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.Qualifier = fltk.lsp.fltklsp_cst.Qualifier(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_qualifier__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_rule(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_qualifier__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="rule")

    def parse_kind_list(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.KindList] | None:
        if alt0 := self.parse_kind_list__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_kind_list__alt1(pos=pos):
            return alt1
        return None

    def apply__parse_kind_list(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.KindList] | None:
        return self.packrat.apply(
            rule_callable=self.parse_kind_list, rule_id=11, rule_cache=self._cache__parse_kind_list, pos=pos
        )

    def parse_kind_list__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.KindList] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.KindList = fltk.lsp.fltklsp_cst.KindList(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_kind_list__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_wildcard(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_kind_list__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="*")

    def parse_kind_list__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.KindList] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.KindList = fltk.lsp.fltklsp_cst.KindList(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_kind_list__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_kind(child=item0.result)
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_kind_list__alt1__item1(pos=pos):
            pos = item1.pos
            result.extend_children(other=item1.result)
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_kind_list__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.DottedName] | None:
        return self.apply__parse_dotted_name(pos=pos)

    def parse_kind_list__alt1__item1__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.KindList] | None:
        if alt0 := self.parse_kind_list__alt1__item1__alts__alt0(pos=pos):
            return alt0
        return None

    def parse_kind_list__alt1__item1__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.KindList] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.KindList = fltk.lsp.fltklsp_cst.KindList(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_kind_list__alt1__item1__alts__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_kind_list__alt1__item1__alts__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_kind(child=item1.result)
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_kind_list__alt1__item1__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=",")

    def parse_kind_list__alt1__item1__alts__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.DottedName] | None:
        return self.apply__parse_dotted_name(pos=pos)

    def parse_kind_list__alt1__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.KindList] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.KindList = fltk.lsp.fltklsp_cst.KindList(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        while one_result := self.parse_kind_list__alt1__item1__alts(pos=pos):
            if not one_result.pos > pos:
                break
            pos = one_result.pos
            result.extend_children(other=one_result.result)
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_dotted_name(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.DottedName] | None:
        if alt0 := self.parse_dotted_name__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_dotted_name(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.DottedName] | None:
        return self.packrat.apply(
            rule_callable=self.parse_dotted_name, rule_id=12, rule_cache=self._cache__parse_dotted_name, pos=pos
        )

    def parse_dotted_name__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.DottedName] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.DottedName = fltk.lsp.fltklsp_cst.DottedName(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_dotted_name__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_part(child=item0.result)
        else:
            return None
        if item1 := self.parse_dotted_name__alt0__item1(pos=pos):
            pos = item1.pos
            result.extend_children(other=item1.result)
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_dotted_name__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Identifier] | None:
        return self.apply__parse_identifier(pos=pos)

    def parse_dotted_name__alt0__item1__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.DottedName] | None:
        if alt0 := self.parse_dotted_name__alt0__item1__alts__alt0(pos=pos):
            return alt0
        return None

    def parse_dotted_name__alt0__item1__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.DottedName] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.DottedName = fltk.lsp.fltklsp_cst.DottedName(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_dotted_name__alt0__item1__alts__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if item1 := self.parse_dotted_name__alt0__item1__alts__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_part(child=item1.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_dotted_name__alt0__item1__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=".")

    def parse_dotted_name__alt0__item1__alts__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Identifier] | None:
        return self.apply__parse_identifier(pos=pos)

    def parse_dotted_name__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.DottedName] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.DottedName = fltk.lsp.fltklsp_cst.DottedName(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        while one_result := self.parse_dotted_name__alt0__item1__alts(pos=pos):
            if not one_result.pos > pos:
                break
            pos = one_result.pos
            result.extend_children(other=one_result.result)
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_identifier(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Identifier] | None:
        if alt0 := self.parse_identifier__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_identifier(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Identifier] | None:
        return self.packrat.apply(
            rule_callable=self.parse_identifier, rule_id=13, rule_cache=self._cache__parse_identifier, pos=pos
        )

    def parse_identifier__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Identifier] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.Identifier = fltk.lsp.fltklsp_cst.Identifier(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_identifier__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_name(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_identifier__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_regex(pos=pos, regex="[a-zA-Z_][a-zA-Z0-9_]*")

    def parse_literal(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Literal] | None:
        if alt0 := self.parse_literal__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_literal(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Literal] | None:
        return self.packrat.apply(
            rule_callable=self.parse_literal, rule_id=14, rule_cache=self._cache__parse_literal, pos=pos
        )

    def parse_literal__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Literal] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.Literal = fltk.lsp.fltklsp_cst.Literal(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_literal__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_value(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_literal__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_regex(pos=pos, regex="(\"([^\"\\n\\\\]|\\\\.)+\"|'([^'\\n\\\\]|\\\\.)+')")

    def parse__trivia(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Trivia] | None:
        if alt0 := self.parse__trivia__alt0(pos=pos):
            return alt0
        return None

    def apply__parse__trivia(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Trivia] | None:
        return self.packrat.apply(
            rule_callable=self.parse__trivia, rule_id=15, rule_cache=self._cache__parse__trivia, pos=pos
        )

    def parse__trivia__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Trivia] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.Trivia = fltk.lsp.fltklsp_cst.Trivia(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse__trivia__alt0__item0(pos=pos):
            pos = item0.pos
            result.extend_children(other=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse__trivia__alt0__item0__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Trivia] | None:
        if alt0 := self.parse__trivia__alt0__item0__alts__alt0(pos=pos):
            return alt0
        if alt1 := self.parse__trivia__alt0__item0__alts__alt1(pos=pos):
            return alt1
        return None

    def parse__trivia__alt0__item0__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Trivia] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.Trivia = fltk.lsp.fltklsp_cst.Trivia(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse__trivia__alt0__item0__alts__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_line_comment(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse__trivia__alt0__item0__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.LineComment] | None:
        return self.apply__parse_line_comment(pos=pos)

    def parse__trivia__alt0__item0__alts__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Trivia] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.Trivia = fltk.lsp.fltklsp_cst.Trivia(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse__trivia__alt0__item0__alts__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_line_comment(child=item0.result)
        if ws_after__item0 := self.consume_regex(pos=pos, regex="\\s+"):
            pos = ws_after__item0.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse__trivia__alt0__item0__alts__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.LineComment] | None:
        return self.apply__parse_line_comment(pos=pos)

    def parse__trivia__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.Trivia] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.Trivia = fltk.lsp.fltklsp_cst.Trivia(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        while one_result := self.parse__trivia__alt0__item0__alts(pos=pos):
            if not one_result.pos > pos:
                break
            pos = one_result.pos
            result.extend_children(other=one_result.result)
        if pos == _span_start:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_line_comment(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.LineComment] | None:
        if alt0 := self.parse_line_comment__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_line_comment(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.LineComment] | None:
        return self.packrat.apply(
            rule_callable=self.parse_line_comment, rule_id=16, rule_cache=self._cache__parse_line_comment, pos=pos
        )

    def parse_line_comment__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.lsp.fltklsp_cst.LineComment] | None:
        _span_start: int = pos
        result: fltk.lsp.fltklsp_cst.LineComment = fltk.lsp.fltklsp_cst.LineComment(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
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
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
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
