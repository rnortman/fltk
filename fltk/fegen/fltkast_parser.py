from __future__ import annotations

import collections.abc
import typing

import fltk.fegen.fltkast_cst
import fltk.fegen.pyrt.errors
import fltk.fegen.pyrt.memo
import fltk.fegen.pyrt.terminalsrc


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
            "ast_spec",
            "statement",
            "option_stmt",
            "option_value",
            "rule_config",
            "rule_statement",
            "type_stmt",
            "type_spec",
            "custom_spec",
            "custom_arg",
            "bool_stmt",
            "transparent_stmt",
            "text_from_stmt",
            "key_stmt",
            "fold_stmt",
            "fold_dir",
            "flatten_stmt",
            "custom_stmt",
            "name_stmt",
            "variant_stmt",
            "field_stmt",
            "field_statement",
            "sum_stmt",
            "product_stmt",
            "identifier",
            "string",
            "_trivia",
            "line_comment",
        ]
        self._cache__parse_ast_spec: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.AstSpec]
        ] = {}
        self._cache__parse_statement: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.Statement]
        ] = {}
        self._cache__parse_option_stmt: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.OptionStmt]
        ] = {}
        self._cache__parse_option_value: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.OptionValue]
        ] = {}
        self._cache__parse_rule_config: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.RuleConfig]
        ] = {}
        self._cache__parse_rule_statement: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.RuleStatement]
        ] = {}
        self._cache__parse_type_stmt: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.TypeStmt]
        ] = {}
        self._cache__parse_type_spec: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.TypeSpec]
        ] = {}
        self._cache__parse_custom_spec: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.CustomSpec]
        ] = {}
        self._cache__parse_custom_arg: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.CustomArg]
        ] = {}
        self._cache__parse_bool_stmt: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.BoolStmt]
        ] = {}
        self._cache__parse_transparent_stmt: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.TransparentStmt]
        ] = {}
        self._cache__parse_text_from_stmt: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.TextFromStmt]
        ] = {}
        self._cache__parse_key_stmt: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.KeyStmt]
        ] = {}
        self._cache__parse_fold_stmt: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.FoldStmt]
        ] = {}
        self._cache__parse_fold_dir: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.FoldDir]
        ] = {}
        self._cache__parse_flatten_stmt: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.FlattenStmt]
        ] = {}
        self._cache__parse_custom_stmt: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.CustomStmt]
        ] = {}
        self._cache__parse_name_stmt: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.NameStmt]
        ] = {}
        self._cache__parse_variant_stmt: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.VariantStmt]
        ] = {}
        self._cache__parse_field_stmt: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.FieldStmt]
        ] = {}
        self._cache__parse_field_statement: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.FieldStatement]
        ] = {}
        self._cache__parse_sum_stmt: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.SumStmt]
        ] = {}
        self._cache__parse_product_stmt: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.ProductStmt]
        ] = {}
        self._cache__parse_identifier: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.Identifier]
        ] = {}
        self._cache__parse_string: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.String]
        ] = {}
        self._cache__parse__trivia: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.Trivia]
        ] = {}
        self._cache__parse_line_comment: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltkast_cst.LineComment]
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

    def parse_ast_spec(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.AstSpec] | None:
        if alt0 := self.parse_ast_spec__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_ast_spec(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.AstSpec] | None:
        return self.packrat.apply(
            rule_callable=self.parse_ast_spec, rule_id=0, rule_cache=self._cache__parse_ast_spec, pos=pos
        )

    def parse_ast_spec__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.AstSpec] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.AstSpec = fltk.fegen.fltkast_cst.AstSpec(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if initial_ws := self.apply__parse__trivia(pos=pos):
            pos = initial_ws.pos
        if item0 := self.parse_ast_spec__alt0__item0(pos=pos):
            pos = item0.pos
            result.extend_children(other=item0.result)
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_ast_spec__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.AstSpec] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.AstSpec = fltk.fegen.fltkast_cst.AstSpec(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        while one_result := self.apply__parse_statement(pos=pos):
            if not one_result.pos > pos:
                break
            pos = one_result.pos
            result.append_statement(child=one_result.result)
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_statement(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Statement] | None:
        if alt0 := self.parse_statement__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_statement__alt1(pos=pos):
            return alt1
        return None

    def apply__parse_statement(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Statement] | None:
        return self.packrat.apply(
            rule_callable=self.parse_statement, rule_id=1, rule_cache=self._cache__parse_statement, pos=pos
        )

    def parse_statement__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Statement] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.Statement = fltk.fegen.fltkast_cst.Statement(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_statement__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_option_stmt(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_statement__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.OptionStmt] | None:
        return self.apply__parse_option_stmt(pos=pos)

    def parse_statement__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Statement] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.Statement = fltk.fegen.fltkast_cst.Statement(
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
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.RuleConfig] | None:
        return self.apply__parse_rule_config(pos=pos)

    def parse_option_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.OptionStmt] | None:
        if alt0 := self.parse_option_stmt__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_option_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.OptionStmt] | None:
        return self.packrat.apply(
            rule_callable=self.parse_option_stmt, rule_id=2, rule_cache=self._cache__parse_option_stmt, pos=pos
        )

    def parse_option_stmt__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.OptionStmt] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.OptionStmt = fltk.fegen.fltkast_cst.OptionStmt(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_option_stmt__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        else:
            return None
        if item1 := self.parse_option_stmt__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_key(child=item1.result)
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_option_stmt__alt0__item2(pos=pos):
            pos = item2.pos
        else:
            return None
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_option_stmt__alt0__item3(pos=pos):
            pos = item3.pos
            result.append_value(child=item3.result)
        else:
            return None
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        if item4 := self.parse_option_stmt__alt0__item4(pos=pos):
            pos = item4.pos
        else:
            return None
        if ws_after__item4 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item4.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_option_stmt__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="option")

    def parse_option_stmt__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Identifier] | None:
        return self.apply__parse_identifier(pos=pos)

    def parse_option_stmt__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="=")

    def parse_option_stmt__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.OptionValue] | None:
        return self.apply__parse_option_value(pos=pos)

    def parse_option_stmt__alt0__item4(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_option_value(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.OptionValue] | None:
        if alt0 := self.parse_option_value__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_option_value__alt1(pos=pos):
            return alt1
        if alt2 := self.parse_option_value__alt2(pos=pos):
            return alt2
        return None

    def apply__parse_option_value(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.OptionValue] | None:
        return self.packrat.apply(
            rule_callable=self.parse_option_value, rule_id=3, rule_cache=self._cache__parse_option_value, pos=pos
        )

    def parse_option_value__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.OptionValue] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.OptionValue = fltk.fegen.fltkast_cst.OptionValue(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_option_value__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_true(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_option_value__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="true")

    def parse_option_value__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.OptionValue] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.OptionValue = fltk.fegen.fltkast_cst.OptionValue(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_option_value__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_false(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_option_value__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="false")

    def parse_option_value__alt2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.OptionValue] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.OptionValue = fltk.fegen.fltkast_cst.OptionValue(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_option_value__alt2__item0(pos=pos):
            pos = item0.pos
            result.append_string(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_option_value__alt2__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.String] | None:
        return self.apply__parse_string(pos=pos)

    def parse_rule_config(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.RuleConfig] | None:
        if alt0 := self.parse_rule_config__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_rule_config(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.RuleConfig] | None:
        return self.packrat.apply(
            rule_callable=self.parse_rule_config, rule_id=4, rule_cache=self._cache__parse_rule_config, pos=pos
        )

    def parse_rule_config__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.RuleConfig] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.RuleConfig = fltk.fegen.fltkast_cst.RuleConfig(
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
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Identifier] | None:
        return self.apply__parse_identifier(pos=pos)

    def parse_rule_config__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="{")

    def parse_rule_config__alt0__item3__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.RuleConfig] | None:
        if alt0 := self.parse_rule_config__alt0__item3__alts__alt0(pos=pos):
            return alt0
        return None

    def parse_rule_config__alt0__item3__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.RuleConfig] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.RuleConfig = fltk.fegen.fltkast_cst.RuleConfig(
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
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.RuleStatement] | None:
        return self.apply__parse_rule_statement(pos=pos)

    def parse_rule_config__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.RuleConfig] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.RuleConfig = fltk.fegen.fltkast_cst.RuleConfig(
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
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.RuleStatement] | None:
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
        if alt8 := self.parse_rule_statement__alt8(pos=pos):
            return alt8
        if alt9 := self.parse_rule_statement__alt9(pos=pos):
            return alt9
        if alt10 := self.parse_rule_statement__alt10(pos=pos):
            return alt10
        if alt11 := self.parse_rule_statement__alt11(pos=pos):
            return alt11
        if alt12 := self.parse_rule_statement__alt12(pos=pos):
            return alt12
        return None

    def apply__parse_rule_statement(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.RuleStatement] | None:
        return self.packrat.apply(
            rule_callable=self.parse_rule_statement, rule_id=5, rule_cache=self._cache__parse_rule_statement, pos=pos
        )

    def parse_rule_statement__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.RuleStatement] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.RuleStatement = fltk.fegen.fltkast_cst.RuleStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_rule_statement__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_type_stmt(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_statement__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.TypeStmt] | None:
        return self.apply__parse_type_stmt(pos=pos)

    def parse_rule_statement__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.RuleStatement] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.RuleStatement = fltk.fegen.fltkast_cst.RuleStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_rule_statement__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_bool_stmt(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_statement__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.BoolStmt] | None:
        return self.apply__parse_bool_stmt(pos=pos)

    def parse_rule_statement__alt2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.RuleStatement] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.RuleStatement = fltk.fegen.fltkast_cst.RuleStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_rule_statement__alt2__item0(pos=pos):
            pos = item0.pos
            result.append_transparent_stmt(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_statement__alt2__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.TransparentStmt] | None:
        return self.apply__parse_transparent_stmt(pos=pos)

    def parse_rule_statement__alt3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.RuleStatement] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.RuleStatement = fltk.fegen.fltkast_cst.RuleStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_rule_statement__alt3__item0(pos=pos):
            pos = item0.pos
            result.append_text_from_stmt(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_statement__alt3__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.TextFromStmt] | None:
        return self.apply__parse_text_from_stmt(pos=pos)

    def parse_rule_statement__alt4(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.RuleStatement] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.RuleStatement = fltk.fegen.fltkast_cst.RuleStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_rule_statement__alt4__item0(pos=pos):
            pos = item0.pos
            result.append_key_stmt(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_statement__alt4__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.KeyStmt] | None:
        return self.apply__parse_key_stmt(pos=pos)

    def parse_rule_statement__alt5(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.RuleStatement] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.RuleStatement = fltk.fegen.fltkast_cst.RuleStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_rule_statement__alt5__item0(pos=pos):
            pos = item0.pos
            result.append_fold_stmt(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_statement__alt5__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.FoldStmt] | None:
        return self.apply__parse_fold_stmt(pos=pos)

    def parse_rule_statement__alt6(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.RuleStatement] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.RuleStatement = fltk.fegen.fltkast_cst.RuleStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_rule_statement__alt6__item0(pos=pos):
            pos = item0.pos
            result.append_flatten_stmt(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_statement__alt6__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.FlattenStmt] | None:
        return self.apply__parse_flatten_stmt(pos=pos)

    def parse_rule_statement__alt7(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.RuleStatement] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.RuleStatement = fltk.fegen.fltkast_cst.RuleStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_rule_statement__alt7__item0(pos=pos):
            pos = item0.pos
            result.append_custom_stmt(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_statement__alt7__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.CustomStmt] | None:
        return self.apply__parse_custom_stmt(pos=pos)

    def parse_rule_statement__alt8(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.RuleStatement] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.RuleStatement = fltk.fegen.fltkast_cst.RuleStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_rule_statement__alt8__item0(pos=pos):
            pos = item0.pos
            result.append_name_stmt(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_statement__alt8__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.NameStmt] | None:
        return self.apply__parse_name_stmt(pos=pos)

    def parse_rule_statement__alt9(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.RuleStatement] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.RuleStatement = fltk.fegen.fltkast_cst.RuleStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_rule_statement__alt9__item0(pos=pos):
            pos = item0.pos
            result.append_variant_stmt(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_statement__alt9__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.VariantStmt] | None:
        return self.apply__parse_variant_stmt(pos=pos)

    def parse_rule_statement__alt10(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.RuleStatement] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.RuleStatement = fltk.fegen.fltkast_cst.RuleStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_rule_statement__alt10__item0(pos=pos):
            pos = item0.pos
            result.append_field_stmt(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_statement__alt10__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.FieldStmt] | None:
        return self.apply__parse_field_stmt(pos=pos)

    def parse_rule_statement__alt11(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.RuleStatement] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.RuleStatement = fltk.fegen.fltkast_cst.RuleStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_rule_statement__alt11__item0(pos=pos):
            pos = item0.pos
            result.append_sum_stmt(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_statement__alt11__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.SumStmt] | None:
        return self.apply__parse_sum_stmt(pos=pos)

    def parse_rule_statement__alt12(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.RuleStatement] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.RuleStatement = fltk.fegen.fltkast_cst.RuleStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_rule_statement__alt12__item0(pos=pos):
            pos = item0.pos
            result.append_product_stmt(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_rule_statement__alt12__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.ProductStmt] | None:
        return self.apply__parse_product_stmt(pos=pos)

    def parse_type_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.TypeStmt] | None:
        if alt0 := self.parse_type_stmt__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_type_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.TypeStmt] | None:
        return self.packrat.apply(
            rule_callable=self.parse_type_stmt, rule_id=6, rule_cache=self._cache__parse_type_stmt, pos=pos
        )

    def parse_type_stmt__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.TypeStmt] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.TypeStmt = fltk.fegen.fltkast_cst.TypeStmt(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_type_stmt__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_type_stmt__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_type_stmt__alt0__item2(pos=pos):
            pos = item2.pos
            result.append_spec(child=item2.result)
        else:
            return None
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_type_stmt__alt0__item3(pos=pos):
            pos = item3.pos
        else:
            return None
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_type_stmt__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="type")

    def parse_type_stmt__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=":")

    def parse_type_stmt__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.TypeSpec] | None:
        return self.apply__parse_type_spec(pos=pos)

    def parse_type_stmt__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_type_spec(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.TypeSpec] | None:
        if alt0 := self.parse_type_spec__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_type_spec__alt1(pos=pos):
            return alt1
        return None

    def apply__parse_type_spec(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.TypeSpec] | None:
        return self.packrat.apply(
            rule_callable=self.parse_type_spec, rule_id=7, rule_cache=self._cache__parse_type_spec, pos=pos
        )

    def parse_type_spec__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.TypeSpec] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.TypeSpec = fltk.fegen.fltkast_cst.TypeSpec(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_type_spec__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_custom(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_type_spec__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.CustomSpec] | None:
        return self.apply__parse_custom_spec(pos=pos)

    def parse_type_spec__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.TypeSpec] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.TypeSpec = fltk.fegen.fltkast_cst.TypeSpec(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_type_spec__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_builtin(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_type_spec__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Identifier] | None:
        return self.apply__parse_identifier(pos=pos)

    def parse_custom_spec(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.CustomSpec] | None:
        if alt0 := self.parse_custom_spec__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_custom_spec(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.CustomSpec] | None:
        return self.packrat.apply(
            rule_callable=self.parse_custom_spec, rule_id=8, rule_cache=self._cache__parse_custom_spec, pos=pos
        )

    def parse_custom_spec__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.CustomSpec] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.CustomSpec = fltk.fegen.fltkast_cst.CustomSpec(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_custom_spec__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_custom_spec__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_custom_spec__alt0__item2(pos=pos):
            pos = item2.pos
            result.append_arg(child=item2.result)
        else:
            return None
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_custom_spec__alt0__item3(pos=pos):
            pos = item3.pos
            result.extend_children(other=item3.result)
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        if item4 := self.parse_custom_spec__alt0__item4(pos=pos):
            pos = item4.pos
        if ws_after__item4 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item4.pos
        if item5 := self.parse_custom_spec__alt0__item5(pos=pos):
            pos = item5.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_custom_spec__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="custom")

    def parse_custom_spec__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="(")

    def parse_custom_spec__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.CustomArg] | None:
        return self.apply__parse_custom_arg(pos=pos)

    def parse_custom_spec__alt0__item3__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.CustomSpec] | None:
        if alt0 := self.parse_custom_spec__alt0__item3__alts__alt0(pos=pos):
            return alt0
        return None

    def parse_custom_spec__alt0__item3__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.CustomSpec] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.CustomSpec = fltk.fegen.fltkast_cst.CustomSpec(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_custom_spec__alt0__item3__alts__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_custom_spec__alt0__item3__alts__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_arg(child=item1.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_custom_spec__alt0__item3__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=",")

    def parse_custom_spec__alt0__item3__alts__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.CustomArg] | None:
        return self.apply__parse_custom_arg(pos=pos)

    def parse_custom_spec__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.CustomSpec] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.CustomSpec = fltk.fegen.fltkast_cst.CustomSpec(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        while one_result := self.parse_custom_spec__alt0__item3__alts(pos=pos):
            if not one_result.pos > pos:
                break
            pos = one_result.pos
            result.extend_children(other=one_result.result)
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_custom_spec__alt0__item4(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=",")

    def parse_custom_spec__alt0__item5(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=")")

    def parse_custom_arg(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.CustomArg] | None:
        if alt0 := self.parse_custom_arg__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_custom_arg(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.CustomArg] | None:
        return self.packrat.apply(
            rule_callable=self.parse_custom_arg, rule_id=9, rule_cache=self._cache__parse_custom_arg, pos=pos
        )

    def parse_custom_arg__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.CustomArg] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.CustomArg = fltk.fegen.fltkast_cst.CustomArg(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_custom_arg__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_key(child=item0.result)
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_custom_arg__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_custom_arg__alt0__item2(pos=pos):
            pos = item2.pos
            result.append_value(child=item2.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_custom_arg__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Identifier] | None:
        return self.apply__parse_identifier(pos=pos)

    def parse_custom_arg__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=":")

    def parse_custom_arg__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.String] | None:
        return self.apply__parse_string(pos=pos)

    def parse_bool_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.BoolStmt] | None:
        if alt0 := self.parse_bool_stmt__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_bool_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.BoolStmt] | None:
        return self.packrat.apply(
            rule_callable=self.parse_bool_stmt, rule_id=10, rule_cache=self._cache__parse_bool_stmt, pos=pos
        )

    def parse_bool_stmt__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.BoolStmt] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.BoolStmt = fltk.fegen.fltkast_cst.BoolStmt(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_bool_stmt__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_bool_stmt__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_bool_stmt__alt0__item2(pos=pos):
            pos = item2.pos
            result.append_truthy(child=item2.result)
        else:
            return None
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_bool_stmt__alt0__item3(pos=pos):
            pos = item3.pos
        else:
            return None
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_bool_stmt__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="bool")

    def parse_bool_stmt__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=":")

    def parse_bool_stmt__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Identifier] | None:
        return self.apply__parse_identifier(pos=pos)

    def parse_bool_stmt__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_transparent_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.TransparentStmt] | None:
        if alt0 := self.parse_transparent_stmt__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_transparent_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.TransparentStmt] | None:
        return self.packrat.apply(
            rule_callable=self.parse_transparent_stmt,
            rule_id=11,
            rule_cache=self._cache__parse_transparent_stmt,
            pos=pos,
        )

    def parse_transparent_stmt__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.TransparentStmt] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.TransparentStmt = fltk.fegen.fltkast_cst.TransparentStmt(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_transparent_stmt__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_transparent_stmt__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_transparent_stmt__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="transparent")

    def parse_transparent_stmt__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_text_from_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.TextFromStmt] | None:
        if alt0 := self.parse_text_from_stmt__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_text_from_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.TextFromStmt] | None:
        return self.packrat.apply(
            rule_callable=self.parse_text_from_stmt, rule_id=12, rule_cache=self._cache__parse_text_from_stmt, pos=pos
        )

    def parse_text_from_stmt__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.TextFromStmt] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.TextFromStmt = fltk.fegen.fltkast_cst.TextFromStmt(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_text_from_stmt__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_text_from_stmt__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_text_from_stmt__alt0__item2(pos=pos):
            pos = item2.pos
            result.append_label(child=item2.result)
        else:
            return None
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_text_from_stmt__alt0__item3(pos=pos):
            pos = item3.pos
        else:
            return None
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_text_from_stmt__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="text_from")

    def parse_text_from_stmt__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=":")

    def parse_text_from_stmt__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Identifier] | None:
        return self.apply__parse_identifier(pos=pos)

    def parse_text_from_stmt__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_key_stmt(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.KeyStmt] | None:
        if alt0 := self.parse_key_stmt__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_key_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.KeyStmt] | None:
        return self.packrat.apply(
            rule_callable=self.parse_key_stmt, rule_id=13, rule_cache=self._cache__parse_key_stmt, pos=pos
        )

    def parse_key_stmt__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.KeyStmt] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.KeyStmt = fltk.fegen.fltkast_cst.KeyStmt(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_key_stmt__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_key_stmt__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_key_stmt__alt0__item2(pos=pos):
            pos = item2.pos
            result.append_label(child=item2.result)
        else:
            return None
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_key_stmt__alt0__item3(pos=pos):
            pos = item3.pos
        else:
            return None
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_key_stmt__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="key")

    def parse_key_stmt__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=":")

    def parse_key_stmt__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Identifier] | None:
        return self.apply__parse_identifier(pos=pos)

    def parse_key_stmt__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_fold_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.FoldStmt] | None:
        if alt0 := self.parse_fold_stmt__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_fold_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.FoldStmt] | None:
        return self.packrat.apply(
            rule_callable=self.parse_fold_stmt, rule_id=14, rule_cache=self._cache__parse_fold_stmt, pos=pos
        )

    def parse_fold_stmt__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.FoldStmt] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.FoldStmt = fltk.fegen.fltkast_cst.FoldStmt(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_fold_stmt__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_dir(child=item0.result)
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_fold_stmt__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_fold_stmt__alt0__item2(pos=pos):
            pos = item2.pos
            result.append_op(child=item2.result)
        else:
            return None
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_fold_stmt__alt0__item3(pos=pos):
            pos = item3.pos
        else:
            return None
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_fold_stmt__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.FoldDir] | None:
        return self.apply__parse_fold_dir(pos=pos)

    def parse_fold_stmt__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=":")

    def parse_fold_stmt__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Identifier] | None:
        return self.apply__parse_identifier(pos=pos)

    def parse_fold_stmt__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_fold_dir(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.FoldDir] | None:
        if alt0 := self.parse_fold_dir__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_fold_dir__alt1(pos=pos):
            return alt1
        return None

    def apply__parse_fold_dir(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.FoldDir] | None:
        return self.packrat.apply(
            rule_callable=self.parse_fold_dir, rule_id=15, rule_cache=self._cache__parse_fold_dir, pos=pos
        )

    def parse_fold_dir__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.FoldDir] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.FoldDir = fltk.fegen.fltkast_cst.FoldDir(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_fold_dir__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_left(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_fold_dir__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="fold_left")

    def parse_fold_dir__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.FoldDir] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.FoldDir = fltk.fegen.fltkast_cst.FoldDir(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_fold_dir__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_right(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_fold_dir__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="fold_right")

    def parse_flatten_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.FlattenStmt] | None:
        if alt0 := self.parse_flatten_stmt__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_flatten_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.FlattenStmt] | None:
        return self.packrat.apply(
            rule_callable=self.parse_flatten_stmt, rule_id=16, rule_cache=self._cache__parse_flatten_stmt, pos=pos
        )

    def parse_flatten_stmt__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.FlattenStmt] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.FlattenStmt = fltk.fegen.fltkast_cst.FlattenStmt(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_flatten_stmt__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_flatten_stmt__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_flatten_stmt__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="flatten")

    def parse_flatten_stmt__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_custom_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.CustomStmt] | None:
        if alt0 := self.parse_custom_stmt__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_custom_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.CustomStmt] | None:
        return self.packrat.apply(
            rule_callable=self.parse_custom_stmt, rule_id=17, rule_cache=self._cache__parse_custom_stmt, pos=pos
        )

    def parse_custom_stmt__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.CustomStmt] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.CustomStmt = fltk.fegen.fltkast_cst.CustomStmt(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_custom_stmt__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_custom_stmt__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_custom_stmt__alt0__item2(pos=pos):
            pos = item2.pos
            result.append_arg(child=item2.result)
        else:
            return None
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_custom_stmt__alt0__item3(pos=pos):
            pos = item3.pos
            result.extend_children(other=item3.result)
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        if item4 := self.parse_custom_stmt__alt0__item4(pos=pos):
            pos = item4.pos
        if ws_after__item4 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item4.pos
        if item5 := self.parse_custom_stmt__alt0__item5(pos=pos):
            pos = item5.pos
        else:
            return None
        if ws_after__item5 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item5.pos
        if item6 := self.parse_custom_stmt__alt0__item6(pos=pos):
            pos = item6.pos
        else:
            return None
        if ws_after__item6 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item6.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_custom_stmt__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="custom")

    def parse_custom_stmt__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="(")

    def parse_custom_stmt__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.CustomArg] | None:
        return self.apply__parse_custom_arg(pos=pos)

    def parse_custom_stmt__alt0__item3__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.CustomStmt] | None:
        if alt0 := self.parse_custom_stmt__alt0__item3__alts__alt0(pos=pos):
            return alt0
        return None

    def parse_custom_stmt__alt0__item3__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.CustomStmt] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.CustomStmt = fltk.fegen.fltkast_cst.CustomStmt(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_custom_stmt__alt0__item3__alts__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_custom_stmt__alt0__item3__alts__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_arg(child=item1.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_custom_stmt__alt0__item3__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=",")

    def parse_custom_stmt__alt0__item3__alts__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.CustomArg] | None:
        return self.apply__parse_custom_arg(pos=pos)

    def parse_custom_stmt__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.CustomStmt] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.CustomStmt = fltk.fegen.fltkast_cst.CustomStmt(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        while one_result := self.parse_custom_stmt__alt0__item3__alts(pos=pos):
            if not one_result.pos > pos:
                break
            pos = one_result.pos
            result.extend_children(other=one_result.result)
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_custom_stmt__alt0__item4(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=",")

    def parse_custom_stmt__alt0__item5(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=")")

    def parse_custom_stmt__alt0__item6(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_name_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.NameStmt] | None:
        if alt0 := self.parse_name_stmt__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_name_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.NameStmt] | None:
        return self.packrat.apply(
            rule_callable=self.parse_name_stmt, rule_id=18, rule_cache=self._cache__parse_name_stmt, pos=pos
        )

    def parse_name_stmt__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.NameStmt] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.NameStmt = fltk.fegen.fltkast_cst.NameStmt(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_name_stmt__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_name_stmt__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_name_stmt__alt0__item2(pos=pos):
            pos = item2.pos
            result.append_new_name(child=item2.result)
        else:
            return None
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_name_stmt__alt0__item3(pos=pos):
            pos = item3.pos
        else:
            return None
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_name_stmt__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="name")

    def parse_name_stmt__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=":")

    def parse_name_stmt__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Identifier] | None:
        return self.apply__parse_identifier(pos=pos)

    def parse_name_stmt__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_variant_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.VariantStmt] | None:
        if alt0 := self.parse_variant_stmt__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_variant_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.VariantStmt] | None:
        return self.packrat.apply(
            rule_callable=self.parse_variant_stmt, rule_id=19, rule_cache=self._cache__parse_variant_stmt, pos=pos
        )

    def parse_variant_stmt__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.VariantStmt] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.VariantStmt = fltk.fegen.fltkast_cst.VariantStmt(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_variant_stmt__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        else:
            return None
        if item1 := self.parse_variant_stmt__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_selector(child=item1.result)
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_variant_stmt__alt0__item2(pos=pos):
            pos = item2.pos
        else:
            return None
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_variant_stmt__alt0__item3(pos=pos):
            pos = item3.pos
            result.append_new_name(child=item3.result)
        else:
            return None
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        if item4 := self.parse_variant_stmt__alt0__item4(pos=pos):
            pos = item4.pos
        else:
            return None
        if ws_after__item4 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item4.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_variant_stmt__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="variant")

    def parse_variant_stmt__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Identifier] | None:
        return self.apply__parse_identifier(pos=pos)

    def parse_variant_stmt__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=":")

    def parse_variant_stmt__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Identifier] | None:
        return self.apply__parse_identifier(pos=pos)

    def parse_variant_stmt__alt0__item4(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_field_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.FieldStmt] | None:
        if alt0 := self.parse_field_stmt__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_field_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.FieldStmt] | None:
        return self.packrat.apply(
            rule_callable=self.parse_field_stmt, rule_id=20, rule_cache=self._cache__parse_field_stmt, pos=pos
        )

    def parse_field_stmt__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.FieldStmt] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.FieldStmt = fltk.fegen.fltkast_cst.FieldStmt(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_field_stmt__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        else:
            return None
        if item1 := self.parse_field_stmt__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_label(child=item1.result)
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        if item2 := self.parse_field_stmt__alt0__item2(pos=pos):
            pos = item2.pos
        else:
            return None
        if ws_after__item2 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item2.pos
        if item3 := self.parse_field_stmt__alt0__item3(pos=pos):
            pos = item3.pos
            result.extend_children(other=item3.result)
        if ws_after__item3 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item3.pos
        if item4 := self.parse_field_stmt__alt0__item4(pos=pos):
            pos = item4.pos
        else:
            return None
        if ws_after__item4 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item4.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_field_stmt__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="field")

    def parse_field_stmt__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Identifier] | None:
        return self.apply__parse_identifier(pos=pos)

    def parse_field_stmt__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="{")

    def parse_field_stmt__alt0__item3__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.FieldStmt] | None:
        if alt0 := self.parse_field_stmt__alt0__item3__alts__alt0(pos=pos):
            return alt0
        return None

    def parse_field_stmt__alt0__item3__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.FieldStmt] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.FieldStmt = fltk.fegen.fltkast_cst.FieldStmt(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_field_stmt__alt0__item3__alts__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_field_statement(child=item0.result)
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_field_stmt__alt0__item3__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.FieldStatement] | None:
        return self.apply__parse_field_statement(pos=pos)

    def parse_field_stmt__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.FieldStmt] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.FieldStmt = fltk.fegen.fltkast_cst.FieldStmt(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        while one_result := self.parse_field_stmt__alt0__item3__alts(pos=pos):
            if not one_result.pos > pos:
                break
            pos = one_result.pos
            result.extend_children(other=one_result.result)
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_field_stmt__alt0__item4(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="}")

    def parse_field_statement(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.FieldStatement] | None:
        if alt0 := self.parse_field_statement__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_field_statement(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.FieldStatement] | None:
        return self.packrat.apply(
            rule_callable=self.parse_field_statement, rule_id=21, rule_cache=self._cache__parse_field_statement, pos=pos
        )

    def parse_field_statement__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.FieldStatement] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.FieldStatement = fltk.fegen.fltkast_cst.FieldStatement(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_field_statement__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_name_stmt(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_field_statement__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.NameStmt] | None:
        return self.apply__parse_name_stmt(pos=pos)

    def parse_sum_stmt(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.SumStmt] | None:
        if alt0 := self.parse_sum_stmt__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_sum_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.SumStmt] | None:
        return self.packrat.apply(
            rule_callable=self.parse_sum_stmt, rule_id=22, rule_cache=self._cache__parse_sum_stmt, pos=pos
        )

    def parse_sum_stmt__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.SumStmt] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.SumStmt = fltk.fegen.fltkast_cst.SumStmt(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_sum_stmt__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_sum_stmt__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_sum_stmt__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="sum")

    def parse_sum_stmt__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_product_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.ProductStmt] | None:
        if alt0 := self.parse_product_stmt__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_product_stmt(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.ProductStmt] | None:
        return self.packrat.apply(
            rule_callable=self.parse_product_stmt, rule_id=23, rule_cache=self._cache__parse_product_stmt, pos=pos
        )

    def parse_product_stmt__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.ProductStmt] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.ProductStmt = fltk.fegen.fltkast_cst.ProductStmt(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_product_stmt__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if ws_after__item0 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item0.pos
        if item1 := self.parse_product_stmt__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if ws_after__item1 := self.apply__parse__trivia(pos=pos):
            pos = ws_after__item1.pos
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_product_stmt__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal="product")

    def parse_product_stmt__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_literal(pos=pos, literal=";")

    def parse_identifier(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Identifier] | None:
        if alt0 := self.parse_identifier__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_identifier(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Identifier] | None:
        return self.packrat.apply(
            rule_callable=self.parse_identifier, rule_id=24, rule_cache=self._cache__parse_identifier, pos=pos
        )

    def parse_identifier__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Identifier] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.Identifier = fltk.fegen.fltkast_cst.Identifier(
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

    def parse_string(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.String] | None:
        if alt0 := self.parse_string__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_string(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.String] | None:
        return self.packrat.apply(
            rule_callable=self.parse_string, rule_id=25, rule_cache=self._cache__parse_string, pos=pos
        )

    def parse_string__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.String] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.String = fltk.fegen.fltkast_cst.String(
            span=fltk.fegen.pyrt.terminalsrc.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_string__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_value(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.terminalsrc.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_string__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span] | None:
        return self.consume_regex(pos=pos, regex='"([^"\\n\\\\]|\\\\.)*"')

    def parse__trivia(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Trivia] | None:
        if alt0 := self.parse__trivia__alt0(pos=pos):
            return alt0
        return None

    def apply__parse__trivia(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Trivia] | None:
        return self.packrat.apply(
            rule_callable=self.parse__trivia, rule_id=26, rule_cache=self._cache__parse__trivia, pos=pos
        )

    def parse__trivia__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Trivia] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.Trivia = fltk.fegen.fltkast_cst.Trivia(
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
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Trivia] | None:
        if alt0 := self.parse__trivia__alt0__item0__alts__alt0(pos=pos):
            return alt0
        if alt1 := self.parse__trivia__alt0__item0__alts__alt1(pos=pos):
            return alt1
        return None

    def parse__trivia__alt0__item0__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Trivia] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.Trivia = fltk.fegen.fltkast_cst.Trivia(
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
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.LineComment] | None:
        return self.apply__parse_line_comment(pos=pos)

    def parse__trivia__alt0__item0__alts__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Trivia] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.Trivia = fltk.fegen.fltkast_cst.Trivia(
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
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.LineComment] | None:
        return self.apply__parse_line_comment(pos=pos)

    def parse__trivia__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.Trivia] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.Trivia = fltk.fegen.fltkast_cst.Trivia(
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
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.LineComment] | None:
        if alt0 := self.parse_line_comment__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_line_comment(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.LineComment] | None:
        return self.packrat.apply(
            rule_callable=self.parse_line_comment, rule_id=27, rule_cache=self._cache__parse_line_comment, pos=pos
        )

    def parse_line_comment__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltkast_cst.LineComment] | None:
        _span_start: int = pos
        result: fltk.fegen.fltkast_cst.LineComment = fltk.fegen.fltkast_cst.LineComment(
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
