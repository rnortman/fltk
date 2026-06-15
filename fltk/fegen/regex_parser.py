import collections.abc
import typing

import fltk.fegen.pyrt.errors
import fltk.fegen.pyrt.memo
import fltk.fegen.pyrt.span
import fltk.fegen.pyrt.terminalsrc
import fltk.fegen.regex_cst


class Parser:
    """Parser"""

    def __init__(self, terminalsrc: fltk.fegen.pyrt.terminalsrc.TerminalSource) -> None:
        self.terminalsrc = terminalsrc
        self._source_text = fltk.fegen.pyrt.span.SourceText(text=terminalsrc.terminals)
        self.packrat: fltk.fegen.pyrt.memo.Packrat[int, int] = fltk.fegen.pyrt.memo.Packrat()
        self.error_tracker: fltk.fegen.pyrt.errors.ErrorTracker[int] = fltk.fegen.pyrt.errors.ErrorTracker()
        self.rule_names: typing.Sequence[str] = [
            "regex",
            "alternation",
            "concatenation",
            "repetition",
            "quantifier",
            "bounded",
            "number",
            "atom",
            "dot",
            "anchor",
            "group",
            "non_capturing",
            "flag_group",
            "capturing",
            "inline_flags",
            "flag_chars",
            "char_class",
            "class_body",
            "class_item",
            "class_range",
            "class_member",
            "class_range_atom",
            "class_char",
            "class_escape",
            "class_escape_body",
            "class_char_escape",
            "escape",
            "escape_body",
            "class_shorthand",
            "assertion",
            "anchor_escape",
            "char_escape",
            "control_escape",
            "hex_escape",
            "unicode_escape",
            "meta_escape",
            "literal_char",
            "_trivia",
        ]
        self._cache__parse_regex: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.Regex]
        ] = {}
        self._cache__parse_alternation: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.Alternation]
        ] = {}
        self._cache__parse_concatenation: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.Concatenation]
        ] = {}
        self._cache__parse_repetition: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.Repetition]
        ] = {}
        self._cache__parse_quantifier: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.Quantifier]
        ] = {}
        self._cache__parse_bounded: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.Bounded]
        ] = {}
        self._cache__parse_number: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.Number]
        ] = {}
        self._cache__parse_atom: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.Atom]
        ] = {}
        self._cache__parse_dot: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.Dot]
        ] = {}
        self._cache__parse_anchor: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.Anchor]
        ] = {}
        self._cache__parse_group: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.Group]
        ] = {}
        self._cache__parse_non_capturing: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.NonCapturing]
        ] = {}
        self._cache__parse_flag_group: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.FlagGroup]
        ] = {}
        self._cache__parse_capturing: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.Capturing]
        ] = {}
        self._cache__parse_inline_flags: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.InlineFlags]
        ] = {}
        self._cache__parse_flag_chars: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.FlagChars]
        ] = {}
        self._cache__parse_char_class: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.CharClass]
        ] = {}
        self._cache__parse_class_body: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.ClassBody]
        ] = {}
        self._cache__parse_class_item: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.ClassItem]
        ] = {}
        self._cache__parse_class_range: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.ClassRange]
        ] = {}
        self._cache__parse_class_member: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.ClassMember]
        ] = {}
        self._cache__parse_class_range_atom: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.ClassRangeAtom]
        ] = {}
        self._cache__parse_class_char: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.ClassChar]
        ] = {}
        self._cache__parse_class_escape: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.ClassEscape]
        ] = {}
        self._cache__parse_class_escape_body: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.ClassEscapeBody]
        ] = {}
        self._cache__parse_class_char_escape: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.ClassCharEscape]
        ] = {}
        self._cache__parse_escape: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.Escape]
        ] = {}
        self._cache__parse_escape_body: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.EscapeBody]
        ] = {}
        self._cache__parse_class_shorthand: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.ClassShorthand]
        ] = {}
        self._cache__parse_assertion: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.Assertion]
        ] = {}
        self._cache__parse_anchor_escape: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.AnchorEscape]
        ] = {}
        self._cache__parse_char_escape: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.CharEscape]
        ] = {}
        self._cache__parse_control_escape: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.ControlEscape]
        ] = {}
        self._cache__parse_hex_escape: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.HexEscape]
        ] = {}
        self._cache__parse_unicode_escape: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.UnicodeEscape]
        ] = {}
        self._cache__parse_meta_escape: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.MetaEscape]
        ] = {}
        self._cache__parse_literal_char: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.LiteralChar]
        ] = {}
        self._cache__parse__trivia: collections.abc.MutableMapping[
            int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.regex_cst.Trivia]
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

    def parse_regex(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Regex] | None:
        if alt0 := self.parse_regex__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_regex(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Regex] | None:
        return self.packrat.apply(
            rule_callable=self.parse_regex, rule_id=0, rule_cache=self._cache__parse_regex, pos=pos
        )

    def parse_regex__alt0(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Regex] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Regex = fltk.fegen.regex_cst.Regex(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_regex__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_alternation(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_regex__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Alternation] | None:
        return self.apply__parse_alternation(pos=pos)

    def parse_alternation(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Alternation] | None:
        if alt0 := self.parse_alternation__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_alternation__alt1(pos=pos):
            return alt1
        return None

    def apply__parse_alternation(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Alternation] | None:
        return self.packrat.apply(
            rule_callable=self.parse_alternation, rule_id=1, rule_cache=self._cache__parse_alternation, pos=pos
        )

    def parse_alternation__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Alternation] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Alternation = fltk.fegen.regex_cst.Alternation(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_alternation__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_left(child=item0.result)
        else:
            return None
        if item1 := self.parse_alternation__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if item2 := self.parse_alternation__alt0__item2(pos=pos):
            pos = item2.pos
            result.append_right(child=item2.result)
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_alternation__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Alternation] | None:
        return self.apply__parse_alternation(pos=pos)

    def parse_alternation__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="|")

    def parse_alternation__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Concatenation] | None:
        return self.apply__parse_concatenation(pos=pos)

    def parse_alternation__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Alternation] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Alternation = fltk.fegen.regex_cst.Alternation(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_alternation__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_branch(child=item0.result)
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_alternation__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Concatenation] | None:
        return self.apply__parse_concatenation(pos=pos)

    def parse_concatenation(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Concatenation] | None:
        if alt0 := self.parse_concatenation__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_concatenation__alt1(pos=pos):
            return alt1
        return None

    def apply__parse_concatenation(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Concatenation] | None:
        return self.packrat.apply(
            rule_callable=self.parse_concatenation, rule_id=2, rule_cache=self._cache__parse_concatenation, pos=pos
        )

    def parse_concatenation__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Concatenation] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Concatenation = fltk.fegen.regex_cst.Concatenation(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_concatenation__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_head(child=item0.result)
        else:
            return None
        if item1 := self.parse_concatenation__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_tail(child=item1.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_concatenation__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Concatenation] | None:
        return self.apply__parse_concatenation(pos=pos)

    def parse_concatenation__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Repetition] | None:
        return self.apply__parse_repetition(pos=pos)

    def parse_concatenation__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Concatenation] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Concatenation = fltk.fegen.regex_cst.Concatenation(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_concatenation__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_single(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_concatenation__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Repetition] | None:
        return self.apply__parse_repetition(pos=pos)

    def parse_repetition(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Repetition] | None:
        if alt0 := self.parse_repetition__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_repetition(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Repetition] | None:
        return self.packrat.apply(
            rule_callable=self.parse_repetition, rule_id=3, rule_cache=self._cache__parse_repetition, pos=pos
        )

    def parse_repetition__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Repetition] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Repetition = fltk.fegen.regex_cst.Repetition(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_repetition__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_atom(child=item0.result)
        else:
            return None
        if item1 := self.parse_repetition__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_quantifier(child=item1.result)
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_repetition__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Atom] | None:
        return self.apply__parse_atom(pos=pos)

    def parse_repetition__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Quantifier] | None:
        return self.apply__parse_quantifier(pos=pos)

    def parse_quantifier(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Quantifier] | None:
        if alt0 := self.parse_quantifier__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_quantifier(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Quantifier] | None:
        return self.packrat.apply(
            rule_callable=self.parse_quantifier, rule_id=4, rule_cache=self._cache__parse_quantifier, pos=pos
        )

    def parse_quantifier__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Quantifier] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Quantifier = fltk.fegen.regex_cst.Quantifier(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_quantifier__alt0__item0(pos=pos):
            pos = item0.pos
            result.extend_children(other=item0.result)
        else:
            return None
        if item1 := self.parse_quantifier__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_lazy(child=item1.result)
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_quantifier__alt0__item0__alts(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Quantifier] | None:
        if alt0 := self.parse_quantifier__alt0__item0__alts__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_quantifier__alt0__item0__alts__alt1(pos=pos):
            return alt1
        if alt2 := self.parse_quantifier__alt0__item0__alts__alt2(pos=pos):
            return alt2
        if alt3 := self.parse_quantifier__alt0__item0__alts__alt3(pos=pos):
            return alt3
        return None

    def parse_quantifier__alt0__item0__alts__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Quantifier] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Quantifier = fltk.fegen.regex_cst.Quantifier(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_quantifier__alt0__item0__alts__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_one_or_more(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_quantifier__alt0__item0__alts__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="+")

    def parse_quantifier__alt0__item0__alts__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Quantifier] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Quantifier = fltk.fegen.regex_cst.Quantifier(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_quantifier__alt0__item0__alts__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_zero_or_more(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_quantifier__alt0__item0__alts__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="*")

    def parse_quantifier__alt0__item0__alts__alt2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Quantifier] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Quantifier = fltk.fegen.regex_cst.Quantifier(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_quantifier__alt0__item0__alts__alt2__item0(pos=pos):
            pos = item0.pos
            result.append_optional(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_quantifier__alt0__item0__alts__alt2__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="?")

    def parse_quantifier__alt0__item0__alts__alt3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Quantifier] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Quantifier = fltk.fegen.regex_cst.Quantifier(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_quantifier__alt0__item0__alts__alt3__item0(pos=pos):
            pos = item0.pos
            result.append_bound(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_quantifier__alt0__item0__alts__alt3__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Bounded] | None:
        return self.apply__parse_bounded(pos=pos)

    def parse_quantifier__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Quantifier] | None:
        return self.parse_quantifier__alt0__item0__alts(pos=pos)

    def parse_quantifier__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="?")

    def parse_bounded(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Bounded] | None:
        if alt0 := self.parse_bounded__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_bounded__alt1(pos=pos):
            return alt1
        if alt2 := self.parse_bounded__alt2(pos=pos):
            return alt2
        return None

    def apply__parse_bounded(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Bounded] | None:
        return self.packrat.apply(
            rule_callable=self.parse_bounded, rule_id=5, rule_cache=self._cache__parse_bounded, pos=pos
        )

    def parse_bounded__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Bounded] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Bounded = fltk.fegen.regex_cst.Bounded(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_bounded__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if item1 := self.parse_bounded__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_min(child=item1.result)
        else:
            return None
        if item2 := self.parse_bounded__alt0__item2(pos=pos):
            pos = item2.pos
        else:
            return None
        if item3 := self.parse_bounded__alt0__item3(pos=pos):
            pos = item3.pos
            result.append_max(child=item3.result)
        else:
            return None
        if item4 := self.parse_bounded__alt0__item4(pos=pos):
            pos = item4.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_bounded__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="{")

    def parse_bounded__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Number] | None:
        return self.apply__parse_number(pos=pos)

    def parse_bounded__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal=",")

    def parse_bounded__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Number] | None:
        return self.apply__parse_number(pos=pos)

    def parse_bounded__alt0__item4(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="}")

    def parse_bounded__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Bounded] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Bounded = fltk.fegen.regex_cst.Bounded(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_bounded__alt1__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if item1 := self.parse_bounded__alt1__item1(pos=pos):
            pos = item1.pos
            result.append_min(child=item1.result)
        else:
            return None
        if item2 := self.parse_bounded__alt1__item2(pos=pos):
            pos = item2.pos
        else:
            return None
        if item3 := self.parse_bounded__alt1__item3(pos=pos):
            pos = item3.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_bounded__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="{")

    def parse_bounded__alt1__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Number] | None:
        return self.apply__parse_number(pos=pos)

    def parse_bounded__alt1__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal=",")

    def parse_bounded__alt1__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="}")

    def parse_bounded__alt2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Bounded] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Bounded = fltk.fegen.regex_cst.Bounded(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_bounded__alt2__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if item1 := self.parse_bounded__alt2__item1(pos=pos):
            pos = item1.pos
            result.append_count(child=item1.result)
        else:
            return None
        if item2 := self.parse_bounded__alt2__item2(pos=pos):
            pos = item2.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_bounded__alt2__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="{")

    def parse_bounded__alt2__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Number] | None:
        return self.apply__parse_number(pos=pos)

    def parse_bounded__alt2__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="}")

    def parse_number(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Number] | None:
        if alt0 := self.parse_number__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_number(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Number] | None:
        return self.packrat.apply(
            rule_callable=self.parse_number, rule_id=6, rule_cache=self._cache__parse_number, pos=pos
        )

    def parse_number__alt0(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Number] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Number = fltk.fegen.regex_cst.Number(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_number__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_digits(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_number__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_regex(pos=pos, regex="[0-9]+")

    def parse_atom(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Atom] | None:
        if alt0 := self.parse_atom__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_atom__alt1(pos=pos):
            return alt1
        if alt2 := self.parse_atom__alt2(pos=pos):
            return alt2
        if alt3 := self.parse_atom__alt3(pos=pos):
            return alt3
        if alt4 := self.parse_atom__alt4(pos=pos):
            return alt4
        if alt5 := self.parse_atom__alt5(pos=pos):
            return alt5
        if alt6 := self.parse_atom__alt6(pos=pos):
            return alt6
        return None

    def apply__parse_atom(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Atom] | None:
        return self.packrat.apply(rule_callable=self.parse_atom, rule_id=7, rule_cache=self._cache__parse_atom, pos=pos)

    def parse_atom__alt0(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Atom] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Atom = fltk.fegen.regex_cst.Atom(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_atom__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_group(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_atom__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Group] | None:
        return self.apply__parse_group(pos=pos)

    def parse_atom__alt1(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Atom] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Atom = fltk.fegen.regex_cst.Atom(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_atom__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_char_class(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_atom__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.CharClass] | None:
        return self.apply__parse_char_class(pos=pos)

    def parse_atom__alt2(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Atom] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Atom = fltk.fegen.regex_cst.Atom(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_atom__alt2__item0(pos=pos):
            pos = item0.pos
            result.append_escape(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_atom__alt2__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Escape] | None:
        return self.apply__parse_escape(pos=pos)

    def parse_atom__alt3(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Atom] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Atom = fltk.fegen.regex_cst.Atom(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_atom__alt3__item0(pos=pos):
            pos = item0.pos
            result.append_anchor(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_atom__alt3__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Anchor] | None:
        return self.apply__parse_anchor(pos=pos)

    def parse_atom__alt4(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Atom] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Atom = fltk.fegen.regex_cst.Atom(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_atom__alt4__item0(pos=pos):
            pos = item0.pos
            result.append_inline_flags(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_atom__alt4__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.InlineFlags] | None:
        return self.apply__parse_inline_flags(pos=pos)

    def parse_atom__alt5(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Atom] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Atom = fltk.fegen.regex_cst.Atom(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_atom__alt5__item0(pos=pos):
            pos = item0.pos
            result.append_dot(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_atom__alt5__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Dot] | None:
        return self.apply__parse_dot(pos=pos)

    def parse_atom__alt6(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Atom] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Atom = fltk.fegen.regex_cst.Atom(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_atom__alt6__item0(pos=pos):
            pos = item0.pos
            result.append_literal_char(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_atom__alt6__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.LiteralChar] | None:
        return self.apply__parse_literal_char(pos=pos)

    def parse_dot(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Dot] | None:
        if alt0 := self.parse_dot__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_dot(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Dot] | None:
        return self.packrat.apply(rule_callable=self.parse_dot, rule_id=8, rule_cache=self._cache__parse_dot, pos=pos)

    def parse_dot__alt0(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Dot] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Dot = fltk.fegen.regex_cst.Dot(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_dot__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_value(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_dot__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal=".")

    def parse_anchor(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Anchor] | None:
        if alt0 := self.parse_anchor__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_anchor__alt1(pos=pos):
            return alt1
        return None

    def apply__parse_anchor(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Anchor] | None:
        return self.packrat.apply(
            rule_callable=self.parse_anchor, rule_id=9, rule_cache=self._cache__parse_anchor, pos=pos
        )

    def parse_anchor__alt0(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Anchor] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Anchor = fltk.fegen.regex_cst.Anchor(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_anchor__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_caret(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_anchor__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="^")

    def parse_anchor__alt1(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Anchor] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Anchor = fltk.fegen.regex_cst.Anchor(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_anchor__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_dollar(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_anchor__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="$")

    def parse_group(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Group] | None:
        if alt0 := self.parse_group__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_group__alt1(pos=pos):
            return alt1
        if alt2 := self.parse_group__alt2(pos=pos):
            return alt2
        return None

    def apply__parse_group(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Group] | None:
        return self.packrat.apply(
            rule_callable=self.parse_group, rule_id=10, rule_cache=self._cache__parse_group, pos=pos
        )

    def parse_group__alt0(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Group] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Group = fltk.fegen.regex_cst.Group(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_group__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_non_capturing(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_group__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.NonCapturing] | None:
        return self.apply__parse_non_capturing(pos=pos)

    def parse_group__alt1(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Group] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Group = fltk.fegen.regex_cst.Group(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_group__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_flag_group(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_group__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.FlagGroup] | None:
        return self.apply__parse_flag_group(pos=pos)

    def parse_group__alt2(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Group] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Group = fltk.fegen.regex_cst.Group(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_group__alt2__item0(pos=pos):
            pos = item0.pos
            result.append_capturing(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_group__alt2__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Capturing] | None:
        return self.apply__parse_capturing(pos=pos)

    def parse_non_capturing(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.NonCapturing] | None:
        if alt0 := self.parse_non_capturing__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_non_capturing(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.NonCapturing] | None:
        return self.packrat.apply(
            rule_callable=self.parse_non_capturing, rule_id=11, rule_cache=self._cache__parse_non_capturing, pos=pos
        )

    def parse_non_capturing__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.NonCapturing] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.NonCapturing = fltk.fegen.regex_cst.NonCapturing(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_non_capturing__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if item1 := self.parse_non_capturing__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_body(child=item1.result)
        else:
            return None
        if item2 := self.parse_non_capturing__alt0__item2(pos=pos):
            pos = item2.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_non_capturing__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="(?:")

    def parse_non_capturing__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Alternation] | None:
        return self.apply__parse_alternation(pos=pos)

    def parse_non_capturing__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal=")")

    def parse_flag_group(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.FlagGroup] | None:
        if alt0 := self.parse_flag_group__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_flag_group(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.FlagGroup] | None:
        return self.packrat.apply(
            rule_callable=self.parse_flag_group, rule_id=12, rule_cache=self._cache__parse_flag_group, pos=pos
        )

    def parse_flag_group__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.FlagGroup] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.FlagGroup = fltk.fegen.regex_cst.FlagGroup(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_flag_group__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if item1 := self.parse_flag_group__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_flags(child=item1.result)
        else:
            return None
        if item2 := self.parse_flag_group__alt0__item2(pos=pos):
            pos = item2.pos
        else:
            return None
        if item3 := self.parse_flag_group__alt0__item3(pos=pos):
            pos = item3.pos
            result.append_body(child=item3.result)
        else:
            return None
        if item4 := self.parse_flag_group__alt0__item4(pos=pos):
            pos = item4.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_flag_group__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="(?")

    def parse_flag_group__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.FlagChars] | None:
        return self.apply__parse_flag_chars(pos=pos)

    def parse_flag_group__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal=":")

    def parse_flag_group__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Alternation] | None:
        return self.apply__parse_alternation(pos=pos)

    def parse_flag_group__alt0__item4(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal=")")

    def parse_capturing(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Capturing] | None:
        if alt0 := self.parse_capturing__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_capturing(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Capturing] | None:
        return self.packrat.apply(
            rule_callable=self.parse_capturing, rule_id=13, rule_cache=self._cache__parse_capturing, pos=pos
        )

    def parse_capturing__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Capturing] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Capturing = fltk.fegen.regex_cst.Capturing(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_capturing__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if item1 := self.parse_capturing__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_body(child=item1.result)
        else:
            return None
        if item2 := self.parse_capturing__alt0__item2(pos=pos):
            pos = item2.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_capturing__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="(")

    def parse_capturing__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Alternation] | None:
        return self.apply__parse_alternation(pos=pos)

    def parse_capturing__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal=")")

    def parse_inline_flags(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.InlineFlags] | None:
        if alt0 := self.parse_inline_flags__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_inline_flags(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.InlineFlags] | None:
        return self.packrat.apply(
            rule_callable=self.parse_inline_flags, rule_id=14, rule_cache=self._cache__parse_inline_flags, pos=pos
        )

    def parse_inline_flags__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.InlineFlags] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.InlineFlags = fltk.fegen.regex_cst.InlineFlags(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_inline_flags__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if item1 := self.parse_inline_flags__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_flags(child=item1.result)
        else:
            return None
        if item2 := self.parse_inline_flags__alt0__item2(pos=pos):
            pos = item2.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_inline_flags__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="(?")

    def parse_inline_flags__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.FlagChars] | None:
        return self.apply__parse_flag_chars(pos=pos)

    def parse_inline_flags__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal=")")

    def parse_flag_chars(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.FlagChars] | None:
        if alt0 := self.parse_flag_chars__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_flag_chars(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.FlagChars] | None:
        return self.packrat.apply(
            rule_callable=self.parse_flag_chars, rule_id=15, rule_cache=self._cache__parse_flag_chars, pos=pos
        )

    def parse_flag_chars__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.FlagChars] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.FlagChars = fltk.fegen.regex_cst.FlagChars(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_flag_chars__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_value(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_flag_chars__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_regex(pos=pos, regex="[imsU]+")

    def parse_char_class(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.CharClass] | None:
        if alt0 := self.parse_char_class__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_char_class(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.CharClass] | None:
        return self.packrat.apply(
            rule_callable=self.parse_char_class, rule_id=16, rule_cache=self._cache__parse_char_class, pos=pos
        )

    def parse_char_class__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.CharClass] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.CharClass = fltk.fegen.regex_cst.CharClass(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_char_class__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if item1 := self.parse_char_class__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_negated(child=item1.result)
        if item2 := self.parse_char_class__alt0__item2(pos=pos):
            pos = item2.pos
            result.append_class_body(child=item2.result)
        else:
            return None
        if item3 := self.parse_char_class__alt0__item3(pos=pos):
            pos = item3.pos
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_char_class__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="[")

    def parse_char_class__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="^")

    def parse_char_class__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassBody] | None:
        return self.apply__parse_class_body(pos=pos)

    def parse_char_class__alt0__item3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="]")

    def parse_class_body(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassBody] | None:
        if alt0 := self.parse_class_body__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_class_body__alt1(pos=pos):
            return alt1
        return None

    def apply__parse_class_body(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassBody] | None:
        return self.packrat.apply(
            rule_callable=self.parse_class_body, rule_id=17, rule_cache=self._cache__parse_class_body, pos=pos
        )

    def parse_class_body__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassBody] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.ClassBody = fltk.fegen.regex_cst.ClassBody(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_class_body__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_lead_dash(child=item0.result)
        else:
            return None
        if item1 := self.parse_class_body__alt0__item1(pos=pos):
            pos = item1.pos
            result.extend_children(other=item1.result)
        if item2 := self.parse_class_body__alt0__item2(pos=pos):
            pos = item2.pos
            result.append_trail_dash(child=item2.result)
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_class_body__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="-")

    def parse_class_body__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassBody] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.ClassBody = fltk.fegen.regex_cst.ClassBody(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        while one_result := self.apply__parse_class_item(pos=pos):
            if not one_result.pos > pos:
                break
            pos = one_result.pos
            result.append_items(child=one_result.result)
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_class_body__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="-")

    def parse_class_body__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassBody] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.ClassBody = fltk.fegen.regex_cst.ClassBody(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_class_body__alt1__item0(pos=pos):
            pos = item0.pos
            result.extend_children(other=item0.result)
        else:
            return None
        if item1 := self.parse_class_body__alt1__item1(pos=pos):
            pos = item1.pos
            result.append_trail_dash(child=item1.result)
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_class_body__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassBody] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.ClassBody = fltk.fegen.regex_cst.ClassBody(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        while one_result := self.apply__parse_class_item(pos=pos):
            if not one_result.pos > pos:
                break
            pos = one_result.pos
            result.append_items(child=one_result.result)
        if pos == _span_start:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_class_body__alt1__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="-")

    def parse_class_item(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassItem] | None:
        if alt0 := self.parse_class_item__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_class_item__alt1(pos=pos):
            return alt1
        return None

    def apply__parse_class_item(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassItem] | None:
        return self.packrat.apply(
            rule_callable=self.parse_class_item, rule_id=18, rule_cache=self._cache__parse_class_item, pos=pos
        )

    def parse_class_item__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassItem] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.ClassItem = fltk.fegen.regex_cst.ClassItem(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_class_item__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_class_range(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_class_item__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassRange] | None:
        return self.apply__parse_class_range(pos=pos)

    def parse_class_item__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassItem] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.ClassItem = fltk.fegen.regex_cst.ClassItem(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_class_item__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_class_member(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_class_item__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassMember] | None:
        return self.apply__parse_class_member(pos=pos)

    def parse_class_range(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassRange] | None:
        if alt0 := self.parse_class_range__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_class_range(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassRange] | None:
        return self.packrat.apply(
            rule_callable=self.parse_class_range, rule_id=19, rule_cache=self._cache__parse_class_range, pos=pos
        )

    def parse_class_range__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassRange] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.ClassRange = fltk.fegen.regex_cst.ClassRange(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_class_range__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_lo(child=item0.result)
        else:
            return None
        if item1 := self.parse_class_range__alt0__item1(pos=pos):
            pos = item1.pos
        else:
            return None
        if item2 := self.parse_class_range__alt0__item2(pos=pos):
            pos = item2.pos
            result.append_hi(child=item2.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_class_range__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassRangeAtom] | None:
        return self.apply__parse_class_range_atom(pos=pos)

    def parse_class_range__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="-")

    def parse_class_range__alt0__item2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassRangeAtom] | None:
        return self.apply__parse_class_range_atom(pos=pos)

    def parse_class_member(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassMember] | None:
        if alt0 := self.parse_class_member__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_class_member__alt1(pos=pos):
            return alt1
        return None

    def apply__parse_class_member(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassMember] | None:
        return self.packrat.apply(
            rule_callable=self.parse_class_member, rule_id=20, rule_cache=self._cache__parse_class_member, pos=pos
        )

    def parse_class_member__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassMember] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.ClassMember = fltk.fegen.regex_cst.ClassMember(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_class_member__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_class_escape(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_class_member__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassEscape] | None:
        return self.apply__parse_class_escape(pos=pos)

    def parse_class_member__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassMember] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.ClassMember = fltk.fegen.regex_cst.ClassMember(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_class_member__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_class_char(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_class_member__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassChar] | None:
        return self.apply__parse_class_char(pos=pos)

    def parse_class_range_atom(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassRangeAtom] | None:
        if alt0 := self.parse_class_range_atom__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_class_range_atom__alt1(pos=pos):
            return alt1
        return None

    def apply__parse_class_range_atom(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassRangeAtom] | None:
        return self.packrat.apply(
            rule_callable=self.parse_class_range_atom,
            rule_id=21,
            rule_cache=self._cache__parse_class_range_atom,
            pos=pos,
        )

    def parse_class_range_atom__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassRangeAtom] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.ClassRangeAtom = fltk.fegen.regex_cst.ClassRangeAtom(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_class_range_atom__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_class_char_escape(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_class_range_atom__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassCharEscape] | None:
        return self.apply__parse_class_char_escape(pos=pos)

    def parse_class_range_atom__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassRangeAtom] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.ClassRangeAtom = fltk.fegen.regex_cst.ClassRangeAtom(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_class_range_atom__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_class_char(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_class_range_atom__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassChar] | None:
        return self.apply__parse_class_char(pos=pos)

    def parse_class_char(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassChar] | None:
        if alt0 := self.parse_class_char__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_class_char(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassChar] | None:
        return self.packrat.apply(
            rule_callable=self.parse_class_char, rule_id=22, rule_cache=self._cache__parse_class_char, pos=pos
        )

    def parse_class_char__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassChar] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.ClassChar = fltk.fegen.regex_cst.ClassChar(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_class_char__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_value(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_class_char__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_regex(pos=pos, regex="[^\\\\\\]\\[\\-\\n]")

    def parse_class_escape(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassEscape] | None:
        if alt0 := self.parse_class_escape__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_class_escape(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassEscape] | None:
        return self.packrat.apply(
            rule_callable=self.parse_class_escape, rule_id=23, rule_cache=self._cache__parse_class_escape, pos=pos
        )

    def parse_class_escape__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassEscape] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.ClassEscape = fltk.fegen.regex_cst.ClassEscape(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_class_escape__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if item1 := self.parse_class_escape__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_body(child=item1.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_class_escape__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="\\")

    def parse_class_escape__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassEscapeBody] | None:
        return self.apply__parse_class_escape_body(pos=pos)

    def parse_class_escape_body(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassEscapeBody] | None:
        if alt0 := self.parse_class_escape_body__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_class_escape_body__alt1(pos=pos):
            return alt1
        return None

    def apply__parse_class_escape_body(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassEscapeBody] | None:
        return self.packrat.apply(
            rule_callable=self.parse_class_escape_body,
            rule_id=24,
            rule_cache=self._cache__parse_class_escape_body,
            pos=pos,
        )

    def parse_class_escape_body__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassEscapeBody] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.ClassEscapeBody = fltk.fegen.regex_cst.ClassEscapeBody(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_class_escape_body__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_class_shorthand(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_class_escape_body__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassShorthand] | None:
        return self.apply__parse_class_shorthand(pos=pos)

    def parse_class_escape_body__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassEscapeBody] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.ClassEscapeBody = fltk.fegen.regex_cst.ClassEscapeBody(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_class_escape_body__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_char_escape(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_class_escape_body__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.CharEscape] | None:
        return self.apply__parse_char_escape(pos=pos)

    def parse_class_char_escape(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassCharEscape] | None:
        if alt0 := self.parse_class_char_escape__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_class_char_escape(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassCharEscape] | None:
        return self.packrat.apply(
            rule_callable=self.parse_class_char_escape,
            rule_id=25,
            rule_cache=self._cache__parse_class_char_escape,
            pos=pos,
        )

    def parse_class_char_escape__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassCharEscape] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.ClassCharEscape = fltk.fegen.regex_cst.ClassCharEscape(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_class_char_escape__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if item1 := self.parse_class_char_escape__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_body(child=item1.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_class_char_escape__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="\\")

    def parse_class_char_escape__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.CharEscape] | None:
        return self.apply__parse_char_escape(pos=pos)

    def parse_escape(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Escape] | None:
        if alt0 := self.parse_escape__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_escape(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Escape] | None:
        return self.packrat.apply(
            rule_callable=self.parse_escape, rule_id=26, rule_cache=self._cache__parse_escape, pos=pos
        )

    def parse_escape__alt0(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Escape] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Escape = fltk.fegen.regex_cst.Escape(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_escape__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if item1 := self.parse_escape__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_body(child=item1.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_escape__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="\\")

    def parse_escape__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.EscapeBody] | None:
        return self.apply__parse_escape_body(pos=pos)

    def parse_escape_body(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.EscapeBody] | None:
        if alt0 := self.parse_escape_body__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_escape_body__alt1(pos=pos):
            return alt1
        if alt2 := self.parse_escape_body__alt2(pos=pos):
            return alt2
        if alt3 := self.parse_escape_body__alt3(pos=pos):
            return alt3
        return None

    def apply__parse_escape_body(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.EscapeBody] | None:
        return self.packrat.apply(
            rule_callable=self.parse_escape_body, rule_id=27, rule_cache=self._cache__parse_escape_body, pos=pos
        )

    def parse_escape_body__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.EscapeBody] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.EscapeBody = fltk.fegen.regex_cst.EscapeBody(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_escape_body__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_class_shorthand(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_escape_body__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassShorthand] | None:
        return self.apply__parse_class_shorthand(pos=pos)

    def parse_escape_body__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.EscapeBody] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.EscapeBody = fltk.fegen.regex_cst.EscapeBody(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_escape_body__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_assertion(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_escape_body__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Assertion] | None:
        return self.apply__parse_assertion(pos=pos)

    def parse_escape_body__alt2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.EscapeBody] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.EscapeBody = fltk.fegen.regex_cst.EscapeBody(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_escape_body__alt2__item0(pos=pos):
            pos = item0.pos
            result.append_anchor_escape(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_escape_body__alt2__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.AnchorEscape] | None:
        return self.apply__parse_anchor_escape(pos=pos)

    def parse_escape_body__alt3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.EscapeBody] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.EscapeBody = fltk.fegen.regex_cst.EscapeBody(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_escape_body__alt3__item0(pos=pos):
            pos = item0.pos
            result.append_char_escape(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_escape_body__alt3__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.CharEscape] | None:
        return self.apply__parse_char_escape(pos=pos)

    def parse_class_shorthand(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassShorthand] | None:
        if alt0 := self.parse_class_shorthand__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_class_shorthand(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassShorthand] | None:
        return self.packrat.apply(
            rule_callable=self.parse_class_shorthand, rule_id=28, rule_cache=self._cache__parse_class_shorthand, pos=pos
        )

    def parse_class_shorthand__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ClassShorthand] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.ClassShorthand = fltk.fegen.regex_cst.ClassShorthand(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_class_shorthand__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_value(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_class_shorthand__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_regex(pos=pos, regex="[dDwWsS]")

    def parse_assertion(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Assertion] | None:
        if alt0 := self.parse_assertion__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_assertion(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Assertion] | None:
        return self.packrat.apply(
            rule_callable=self.parse_assertion, rule_id=29, rule_cache=self._cache__parse_assertion, pos=pos
        )

    def parse_assertion__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Assertion] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Assertion = fltk.fegen.regex_cst.Assertion(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_assertion__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_value(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_assertion__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_regex(pos=pos, regex="[bB]")

    def parse_anchor_escape(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.AnchorEscape] | None:
        if alt0 := self.parse_anchor_escape__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_anchor_escape(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.AnchorEscape] | None:
        return self.packrat.apply(
            rule_callable=self.parse_anchor_escape, rule_id=30, rule_cache=self._cache__parse_anchor_escape, pos=pos
        )

    def parse_anchor_escape__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.AnchorEscape] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.AnchorEscape = fltk.fegen.regex_cst.AnchorEscape(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_anchor_escape__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_value(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_anchor_escape__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_regex(pos=pos, regex="[Az]")

    def parse_char_escape(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.CharEscape] | None:
        if alt0 := self.parse_char_escape__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_char_escape__alt1(pos=pos):
            return alt1
        if alt2 := self.parse_char_escape__alt2(pos=pos):
            return alt2
        if alt3 := self.parse_char_escape__alt3(pos=pos):
            return alt3
        return None

    def apply__parse_char_escape(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.CharEscape] | None:
        return self.packrat.apply(
            rule_callable=self.parse_char_escape, rule_id=31, rule_cache=self._cache__parse_char_escape, pos=pos
        )

    def parse_char_escape__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.CharEscape] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.CharEscape = fltk.fegen.regex_cst.CharEscape(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_char_escape__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_control_escape(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_char_escape__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ControlEscape] | None:
        return self.apply__parse_control_escape(pos=pos)

    def parse_char_escape__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.CharEscape] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.CharEscape = fltk.fegen.regex_cst.CharEscape(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_char_escape__alt1__item0(pos=pos):
            pos = item0.pos
            result.append_hex_escape(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_char_escape__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.HexEscape] | None:
        return self.apply__parse_hex_escape(pos=pos)

    def parse_char_escape__alt2(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.CharEscape] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.CharEscape = fltk.fegen.regex_cst.CharEscape(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_char_escape__alt2__item0(pos=pos):
            pos = item0.pos
            result.append_unicode_escape(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_char_escape__alt2__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.UnicodeEscape] | None:
        return self.apply__parse_unicode_escape(pos=pos)

    def parse_char_escape__alt3(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.CharEscape] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.CharEscape = fltk.fegen.regex_cst.CharEscape(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_char_escape__alt3__item0(pos=pos):
            pos = item0.pos
            result.append_meta_escape(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_char_escape__alt3__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.MetaEscape] | None:
        return self.apply__parse_meta_escape(pos=pos)

    def parse_control_escape(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ControlEscape] | None:
        if alt0 := self.parse_control_escape__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_control_escape(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ControlEscape] | None:
        return self.packrat.apply(
            rule_callable=self.parse_control_escape, rule_id=32, rule_cache=self._cache__parse_control_escape, pos=pos
        )

    def parse_control_escape__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.ControlEscape] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.ControlEscape = fltk.fegen.regex_cst.ControlEscape(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_control_escape__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_value(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_control_escape__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_regex(pos=pos, regex="[nrtfv0a]")

    def parse_hex_escape(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.HexEscape] | None:
        if alt0 := self.parse_hex_escape__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_hex_escape(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.HexEscape] | None:
        return self.packrat.apply(
            rule_callable=self.parse_hex_escape, rule_id=33, rule_cache=self._cache__parse_hex_escape, pos=pos
        )

    def parse_hex_escape__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.HexEscape] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.HexEscape = fltk.fegen.regex_cst.HexEscape(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_hex_escape__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if item1 := self.parse_hex_escape__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_digits(child=item1.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_hex_escape__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="x")

    def parse_hex_escape__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_regex(pos=pos, regex="[0-9A-Fa-f][0-9A-Fa-f]")

    def parse_unicode_escape(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.UnicodeEscape] | None:
        if alt0 := self.parse_unicode_escape__alt0(pos=pos):
            return alt0
        if alt1 := self.parse_unicode_escape__alt1(pos=pos):
            return alt1
        return None

    def apply__parse_unicode_escape(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.UnicodeEscape] | None:
        return self.packrat.apply(
            rule_callable=self.parse_unicode_escape, rule_id=34, rule_cache=self._cache__parse_unicode_escape, pos=pos
        )

    def parse_unicode_escape__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.UnicodeEscape] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.UnicodeEscape = fltk.fegen.regex_cst.UnicodeEscape(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_unicode_escape__alt0__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if item1 := self.parse_unicode_escape__alt0__item1(pos=pos):
            pos = item1.pos
            result.append_digits(child=item1.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_unicode_escape__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="U")

    def parse_unicode_escape__alt0__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_regex(
            pos=pos, regex="[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]"
        )

    def parse_unicode_escape__alt1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.UnicodeEscape] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.UnicodeEscape = fltk.fegen.regex_cst.UnicodeEscape(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_unicode_escape__alt1__item0(pos=pos):
            pos = item0.pos
        else:
            return None
        if item1 := self.parse_unicode_escape__alt1__item1(pos=pos):
            pos = item1.pos
            result.append_digits(child=item1.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_unicode_escape__alt1__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_literal(pos=pos, literal="u")

    def parse_unicode_escape__alt1__item1(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_regex(pos=pos, regex="[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]")

    def parse_meta_escape(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.MetaEscape] | None:
        if alt0 := self.parse_meta_escape__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_meta_escape(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.MetaEscape] | None:
        return self.packrat.apply(
            rule_callable=self.parse_meta_escape, rule_id=35, rule_cache=self._cache__parse_meta_escape, pos=pos
        )

    def parse_meta_escape__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.MetaEscape] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.MetaEscape = fltk.fegen.regex_cst.MetaEscape(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_meta_escape__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_value(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_meta_escape__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_regex(pos=pos, regex="[.*+?()\\[\\]{}|^$\\/\\\\\\-]")

    def parse_literal_char(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.LiteralChar] | None:
        if alt0 := self.parse_literal_char__alt0(pos=pos):
            return alt0
        return None

    def apply__parse_literal_char(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.LiteralChar] | None:
        return self.packrat.apply(
            rule_callable=self.parse_literal_char, rule_id=36, rule_cache=self._cache__parse_literal_char, pos=pos
        )

    def parse_literal_char__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.LiteralChar] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.LiteralChar = fltk.fegen.regex_cst.LiteralChar(
            span=fltk.fegen.pyrt.span.Span.with_source(pos, -1, self._source_text)
        )
        if item0 := self.parse_literal_char__alt0__item0(pos=pos):
            pos = item0.pos
            result.append_value(child=item0.result)
        else:
            return None
        result.span = fltk.fegen.pyrt.span.Span.with_source(_span_start, pos, self._source_text)
        return fltk.fegen.pyrt.memo.ApplyResult(pos=pos, result=result)

    def parse_literal_char__alt0__item0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.pyrt.span.Span] | None:
        return self.consume_regex(pos=pos, regex="[^.*+?()\\[|^$\\\\{\\n]")

    def parse__trivia(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Trivia] | None:
        if alt0 := self.parse__trivia__alt0(pos=pos):
            return alt0
        return None

    def apply__parse__trivia(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Trivia] | None:
        return self.packrat.apply(
            rule_callable=self.parse__trivia, rule_id=37, rule_cache=self._cache__parse__trivia, pos=pos
        )

    def parse__trivia__alt0(
        self, pos: int
    ) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.regex_cst.Trivia] | None:
        _span_start: int = pos
        result: fltk.fegen.regex_cst.Trivia = fltk.fegen.regex_cst.Trivia(
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
