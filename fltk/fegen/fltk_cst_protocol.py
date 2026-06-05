# ruff: noqa: N802, E501
from __future__ import annotations

import typing

import fltk.fegen.pyrt.terminalsrc


class Grammar(typing.Protocol):

    class Label:
        RULE: typing.ClassVar[object]
    span: fltk.fegen.pyrt.terminalsrc.Span
    children: list[tuple[Label | None, Rule | Trivia]]

    def append(self, child: Rule | Trivia, label: Label | None=None) -> None:
        ...

    def extend(self, children: typing.Iterable[Rule | Trivia], label: Label | None=None) -> None:
        ...

    def child(self) -> tuple[Label | None, Rule | Trivia]:
        ...

    def append_rule(self, child: Rule) -> None:
        ...

    def extend_rule(self, children: typing.Iterable[Rule]) -> None:
        ...

    def children_rule(self) -> typing.Iterator[Rule]:
        ...

    def child_rule(self) -> Rule:
        ...

    def maybe_rule(self) -> Rule | None:
        ...

class Rule(typing.Protocol):

    class Label:
        ALTERNATIVES: typing.ClassVar[object]
        NAME: typing.ClassVar[object]
    span: fltk.fegen.pyrt.terminalsrc.Span
    children: list[tuple[Label | None, Alternatives | Identifier | Trivia]]

    def append(self, child: Alternatives | Identifier | Trivia, label: Label | None=None) -> None:
        ...

    def extend(self, children: typing.Iterable[Alternatives | Identifier | Trivia], label: Label | None=None) -> None:
        ...

    def child(self) -> tuple[Label | None, Alternatives | Identifier | Trivia]:
        ...

    def append_alternatives(self, child: Alternatives) -> None:
        ...

    def extend_alternatives(self, children: typing.Iterable[Alternatives]) -> None:
        ...

    def children_alternatives(self) -> typing.Iterator[Alternatives]:
        ...

    def child_alternatives(self) -> Alternatives:
        ...

    def maybe_alternatives(self) -> Alternatives | None:
        ...

    def append_name(self, child: Identifier) -> None:
        ...

    def extend_name(self, children: typing.Iterable[Identifier]) -> None:
        ...

    def children_name(self) -> typing.Iterator[Identifier]:
        ...

    def child_name(self) -> Identifier:
        ...

    def maybe_name(self) -> Identifier | None:
        ...

class Alternatives(typing.Protocol):

    class Label:
        ITEMS: typing.ClassVar[object]
    span: fltk.fegen.pyrt.terminalsrc.Span
    children: list[tuple[Label | None, Items | Trivia]]

    def append(self, child: Items | Trivia, label: Label | None=None) -> None:
        ...

    def extend(self, children: typing.Iterable[Items | Trivia], label: Label | None=None) -> None:
        ...

    def child(self) -> tuple[Label | None, Items | Trivia]:
        ...

    def append_items(self, child: Items) -> None:
        ...

    def extend_items(self, children: typing.Iterable[Items]) -> None:
        ...

    def children_items(self) -> typing.Iterator[Items]:
        ...

    def child_items(self) -> Items:
        ...

    def maybe_items(self) -> Items | None:
        ...

class Items(typing.Protocol):

    class Label:
        ITEM: typing.ClassVar[object]
        NO_WS: typing.ClassVar[object]
        WS_ALLOWED: typing.ClassVar[object]
        WS_REQUIRED: typing.ClassVar[object]
    span: fltk.fegen.pyrt.terminalsrc.Span
    children: list[tuple[Label | None, Item | Trivia | fltk.fegen.pyrt.terminalsrc.Span]]

    def append(self, child: Item | Trivia | fltk.fegen.pyrt.terminalsrc.Span, label: Label | None=None) -> None:
        ...

    def extend(self, children: typing.Iterable[Item | Trivia | fltk.fegen.pyrt.terminalsrc.Span], label: Label | None=None) -> None:
        ...

    def child(self) -> tuple[Label | None, Item | Trivia | fltk.fegen.pyrt.terminalsrc.Span]:
        ...

    def append_item(self, child: Item) -> None:
        ...

    def extend_item(self, children: typing.Iterable[Item]) -> None:
        ...

    def children_item(self) -> typing.Iterator[Item]:
        ...

    def child_item(self) -> Item:
        ...

    def maybe_item(self) -> Item | None:
        ...

    def append_no_ws(self, child: fltk.fegen.pyrt.terminalsrc.Span) -> None:
        ...

    def extend_no_ws(self, children: typing.Iterable[fltk.fegen.pyrt.terminalsrc.Span]) -> None:
        ...

    def children_no_ws(self) -> typing.Iterator[fltk.fegen.pyrt.terminalsrc.Span]:
        ...

    def child_no_ws(self) -> fltk.fegen.pyrt.terminalsrc.Span:
        ...

    def maybe_no_ws(self) -> fltk.fegen.pyrt.terminalsrc.Span | None:
        ...

    def append_ws_allowed(self, child: fltk.fegen.pyrt.terminalsrc.Span) -> None:
        ...

    def extend_ws_allowed(self, children: typing.Iterable[fltk.fegen.pyrt.terminalsrc.Span]) -> None:
        ...

    def children_ws_allowed(self) -> typing.Iterator[fltk.fegen.pyrt.terminalsrc.Span]:
        ...

    def child_ws_allowed(self) -> fltk.fegen.pyrt.terminalsrc.Span:
        ...

    def maybe_ws_allowed(self) -> fltk.fegen.pyrt.terminalsrc.Span | None:
        ...

    def append_ws_required(self, child: fltk.fegen.pyrt.terminalsrc.Span) -> None:
        ...

    def extend_ws_required(self, children: typing.Iterable[fltk.fegen.pyrt.terminalsrc.Span]) -> None:
        ...

    def children_ws_required(self) -> typing.Iterator[fltk.fegen.pyrt.terminalsrc.Span]:
        ...

    def child_ws_required(self) -> fltk.fegen.pyrt.terminalsrc.Span:
        ...

    def maybe_ws_required(self) -> fltk.fegen.pyrt.terminalsrc.Span | None:
        ...

class Item(typing.Protocol):

    class Label:
        DISPOSITION: typing.ClassVar[object]
        LABEL: typing.ClassVar[object]
        QUANTIFIER: typing.ClassVar[object]
        TERM: typing.ClassVar[object]
    span: fltk.fegen.pyrt.terminalsrc.Span
    children: list[tuple[Label | None, Disposition | Identifier | Quantifier | Term | Trivia]]

    def append(self, child: Disposition | Identifier | Quantifier | Term | Trivia, label: Label | None=None) -> None:
        ...

    def extend(self, children: typing.Iterable[Disposition | Identifier | Quantifier | Term | Trivia], label: Label | None=None) -> None:
        ...

    def child(self) -> tuple[Label | None, Disposition | Identifier | Quantifier | Term | Trivia]:
        ...

    def append_disposition(self, child: Disposition) -> None:
        ...

    def extend_disposition(self, children: typing.Iterable[Disposition]) -> None:
        ...

    def children_disposition(self) -> typing.Iterator[Disposition]:
        ...

    def child_disposition(self) -> Disposition:
        ...

    def maybe_disposition(self) -> Disposition | None:
        ...

    def append_label(self, child: Identifier) -> None:
        ...

    def extend_label(self, children: typing.Iterable[Identifier]) -> None:
        ...

    def children_label(self) -> typing.Iterator[Identifier]:
        ...

    def child_label(self) -> Identifier:
        ...

    def maybe_label(self) -> Identifier | None:
        ...

    def append_quantifier(self, child: Quantifier) -> None:
        ...

    def extend_quantifier(self, children: typing.Iterable[Quantifier]) -> None:
        ...

    def children_quantifier(self) -> typing.Iterator[Quantifier]:
        ...

    def child_quantifier(self) -> Quantifier:
        ...

    def maybe_quantifier(self) -> Quantifier | None:
        ...

    def append_term(self, child: Term) -> None:
        ...

    def extend_term(self, children: typing.Iterable[Term]) -> None:
        ...

    def children_term(self) -> typing.Iterator[Term]:
        ...

    def child_term(self) -> Term:
        ...

    def maybe_term(self) -> Term | None:
        ...

class Term(typing.Protocol):

    class Label:
        ALTERNATIVES: typing.ClassVar[object]
        IDENTIFIER: typing.ClassVar[object]
        LITERAL: typing.ClassVar[object]
        REGEX: typing.ClassVar[object]
    span: fltk.fegen.pyrt.terminalsrc.Span
    children: list[tuple[Label | None, Alternatives | Identifier | Literal | RawString | Trivia]]

    def append(self, child: Alternatives | Identifier | Literal | RawString | Trivia, label: Label | None=None) -> None:
        ...

    def extend(self, children: typing.Iterable[Alternatives | Identifier | Literal | RawString | Trivia], label: Label | None=None) -> None:
        ...

    def child(self) -> tuple[Label | None, Alternatives | Identifier | Literal | RawString | Trivia]:
        ...

    def append_alternatives(self, child: Alternatives) -> None:
        ...

    def extend_alternatives(self, children: typing.Iterable[Alternatives]) -> None:
        ...

    def children_alternatives(self) -> typing.Iterator[Alternatives]:
        ...

    def child_alternatives(self) -> Alternatives:
        ...

    def maybe_alternatives(self) -> Alternatives | None:
        ...

    def append_identifier(self, child: Identifier) -> None:
        ...

    def extend_identifier(self, children: typing.Iterable[Identifier]) -> None:
        ...

    def children_identifier(self) -> typing.Iterator[Identifier]:
        ...

    def child_identifier(self) -> Identifier:
        ...

    def maybe_identifier(self) -> Identifier | None:
        ...

    def append_literal(self, child: Literal) -> None:
        ...

    def extend_literal(self, children: typing.Iterable[Literal]) -> None:
        ...

    def children_literal(self) -> typing.Iterator[Literal]:
        ...

    def child_literal(self) -> Literal:
        ...

    def maybe_literal(self) -> Literal | None:
        ...

    def append_regex(self, child: RawString) -> None:
        ...

    def extend_regex(self, children: typing.Iterable[RawString]) -> None:
        ...

    def children_regex(self) -> typing.Iterator[RawString]:
        ...

    def child_regex(self) -> RawString:
        ...

    def maybe_regex(self) -> RawString | None:
        ...

class Disposition(typing.Protocol):

    class Label:
        INCLUDE: typing.ClassVar[object]
        INLINE: typing.ClassVar[object]
        SUPPRESS: typing.ClassVar[object]
    span: fltk.fegen.pyrt.terminalsrc.Span
    children: list[tuple[Label | None, fltk.fegen.pyrt.terminalsrc.Span]]

    def append(self, child: fltk.fegen.pyrt.terminalsrc.Span, label: Label | None=None) -> None:
        ...

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.terminalsrc.Span], label: Label | None=None) -> None:
        ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.terminalsrc.Span]:
        ...

    def append_include(self, child: fltk.fegen.pyrt.terminalsrc.Span) -> None:
        ...

    def extend_include(self, children: typing.Iterable[fltk.fegen.pyrt.terminalsrc.Span]) -> None:
        ...

    def children_include(self) -> typing.Iterator[fltk.fegen.pyrt.terminalsrc.Span]:
        ...

    def child_include(self) -> fltk.fegen.pyrt.terminalsrc.Span:
        ...

    def maybe_include(self) -> fltk.fegen.pyrt.terminalsrc.Span | None:
        ...

    def append_inline(self, child: fltk.fegen.pyrt.terminalsrc.Span) -> None:
        ...

    def extend_inline(self, children: typing.Iterable[fltk.fegen.pyrt.terminalsrc.Span]) -> None:
        ...

    def children_inline(self) -> typing.Iterator[fltk.fegen.pyrt.terminalsrc.Span]:
        ...

    def child_inline(self) -> fltk.fegen.pyrt.terminalsrc.Span:
        ...

    def maybe_inline(self) -> fltk.fegen.pyrt.terminalsrc.Span | None:
        ...

    def append_suppress(self, child: fltk.fegen.pyrt.terminalsrc.Span) -> None:
        ...

    def extend_suppress(self, children: typing.Iterable[fltk.fegen.pyrt.terminalsrc.Span]) -> None:
        ...

    def children_suppress(self) -> typing.Iterator[fltk.fegen.pyrt.terminalsrc.Span]:
        ...

    def child_suppress(self) -> fltk.fegen.pyrt.terminalsrc.Span:
        ...

    def maybe_suppress(self) -> fltk.fegen.pyrt.terminalsrc.Span | None:
        ...

class Quantifier(typing.Protocol):

    class Label:
        ONE_OR_MORE: typing.ClassVar[object]
        OPTIONAL: typing.ClassVar[object]
        ZERO_OR_MORE: typing.ClassVar[object]
    span: fltk.fegen.pyrt.terminalsrc.Span
    children: list[tuple[Label | None, fltk.fegen.pyrt.terminalsrc.Span]]

    def append(self, child: fltk.fegen.pyrt.terminalsrc.Span, label: Label | None=None) -> None:
        ...

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.terminalsrc.Span], label: Label | None=None) -> None:
        ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.terminalsrc.Span]:
        ...

    def append_one_or_more(self, child: fltk.fegen.pyrt.terminalsrc.Span) -> None:
        ...

    def extend_one_or_more(self, children: typing.Iterable[fltk.fegen.pyrt.terminalsrc.Span]) -> None:
        ...

    def children_one_or_more(self) -> typing.Iterator[fltk.fegen.pyrt.terminalsrc.Span]:
        ...

    def child_one_or_more(self) -> fltk.fegen.pyrt.terminalsrc.Span:
        ...

    def maybe_one_or_more(self) -> fltk.fegen.pyrt.terminalsrc.Span | None:
        ...

    def append_optional(self, child: fltk.fegen.pyrt.terminalsrc.Span) -> None:
        ...

    def extend_optional(self, children: typing.Iterable[fltk.fegen.pyrt.terminalsrc.Span]) -> None:
        ...

    def children_optional(self) -> typing.Iterator[fltk.fegen.pyrt.terminalsrc.Span]:
        ...

    def child_optional(self) -> fltk.fegen.pyrt.terminalsrc.Span:
        ...

    def maybe_optional(self) -> fltk.fegen.pyrt.terminalsrc.Span | None:
        ...

    def append_zero_or_more(self, child: fltk.fegen.pyrt.terminalsrc.Span) -> None:
        ...

    def extend_zero_or_more(self, children: typing.Iterable[fltk.fegen.pyrt.terminalsrc.Span]) -> None:
        ...

    def children_zero_or_more(self) -> typing.Iterator[fltk.fegen.pyrt.terminalsrc.Span]:
        ...

    def child_zero_or_more(self) -> fltk.fegen.pyrt.terminalsrc.Span:
        ...

    def maybe_zero_or_more(self) -> fltk.fegen.pyrt.terminalsrc.Span | None:
        ...

class Identifier(typing.Protocol):

    class Label:
        NAME: typing.ClassVar[object]
    span: fltk.fegen.pyrt.terminalsrc.Span
    children: list[tuple[Label | None, fltk.fegen.pyrt.terminalsrc.Span]]

    def append(self, child: fltk.fegen.pyrt.terminalsrc.Span, label: Label | None=None) -> None:
        ...

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.terminalsrc.Span], label: Label | None=None) -> None:
        ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.terminalsrc.Span]:
        ...

    def append_name(self, child: fltk.fegen.pyrt.terminalsrc.Span) -> None:
        ...

    def extend_name(self, children: typing.Iterable[fltk.fegen.pyrt.terminalsrc.Span]) -> None:
        ...

    def children_name(self) -> typing.Iterator[fltk.fegen.pyrt.terminalsrc.Span]:
        ...

    def child_name(self) -> fltk.fegen.pyrt.terminalsrc.Span:
        ...

    def maybe_name(self) -> fltk.fegen.pyrt.terminalsrc.Span | None:
        ...

class RawString(typing.Protocol):

    class Label:
        VALUE: typing.ClassVar[object]
    span: fltk.fegen.pyrt.terminalsrc.Span
    children: list[tuple[Label | None, fltk.fegen.pyrt.terminalsrc.Span]]

    def append(self, child: fltk.fegen.pyrt.terminalsrc.Span, label: Label | None=None) -> None:
        ...

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.terminalsrc.Span], label: Label | None=None) -> None:
        ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.terminalsrc.Span]:
        ...

    def append_value(self, child: fltk.fegen.pyrt.terminalsrc.Span) -> None:
        ...

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.terminalsrc.Span]) -> None:
        ...

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.terminalsrc.Span]:
        ...

    def child_value(self) -> fltk.fegen.pyrt.terminalsrc.Span:
        ...

    def maybe_value(self) -> fltk.fegen.pyrt.terminalsrc.Span | None:
        ...

class Literal(typing.Protocol):

    class Label:
        VALUE: typing.ClassVar[object]
    span: fltk.fegen.pyrt.terminalsrc.Span
    children: list[tuple[Label | None, fltk.fegen.pyrt.terminalsrc.Span]]

    def append(self, child: fltk.fegen.pyrt.terminalsrc.Span, label: Label | None=None) -> None:
        ...

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.terminalsrc.Span], label: Label | None=None) -> None:
        ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.terminalsrc.Span]:
        ...

    def append_value(self, child: fltk.fegen.pyrt.terminalsrc.Span) -> None:
        ...

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.terminalsrc.Span]) -> None:
        ...

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.terminalsrc.Span]:
        ...

    def child_value(self) -> fltk.fegen.pyrt.terminalsrc.Span:
        ...

    def maybe_value(self) -> fltk.fegen.pyrt.terminalsrc.Span | None:
        ...

class Trivia(typing.Protocol):

    class Label:
        BLOCK_COMMENT: typing.ClassVar[object]
        LINE_COMMENT: typing.ClassVar[object]
    span: fltk.fegen.pyrt.terminalsrc.Span
    children: list[tuple[Label | None, BlockComment | LineComment | Trivia]]

    def append(self, child: BlockComment | LineComment | Trivia, label: Label | None=None) -> None:
        ...

    def extend(self, children: typing.Iterable[BlockComment | LineComment | Trivia], label: Label | None=None) -> None:
        ...

    def child(self) -> tuple[Label | None, BlockComment | LineComment | Trivia]:
        ...

    def append_block_comment(self, child: BlockComment) -> None:
        ...

    def extend_block_comment(self, children: typing.Iterable[BlockComment]) -> None:
        ...

    def children_block_comment(self) -> typing.Iterator[BlockComment]:
        ...

    def child_block_comment(self) -> BlockComment:
        ...

    def maybe_block_comment(self) -> BlockComment | None:
        ...

    def append_line_comment(self, child: LineComment) -> None:
        ...

    def extend_line_comment(self, children: typing.Iterable[LineComment]) -> None:
        ...

    def children_line_comment(self) -> typing.Iterator[LineComment]:
        ...

    def child_line_comment(self) -> LineComment:
        ...

    def maybe_line_comment(self) -> LineComment | None:
        ...

class LineComment(typing.Protocol):

    class Label:
        CONTENT: typing.ClassVar[object]
        PREFIX: typing.ClassVar[object]
    span: fltk.fegen.pyrt.terminalsrc.Span
    children: list[tuple[Label | None, fltk.fegen.pyrt.terminalsrc.Span]]

    def append(self, child: fltk.fegen.pyrt.terminalsrc.Span, label: Label | None=None) -> None:
        ...

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.terminalsrc.Span], label: Label | None=None) -> None:
        ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.terminalsrc.Span]:
        ...

    def append_content(self, child: fltk.fegen.pyrt.terminalsrc.Span) -> None:
        ...

    def extend_content(self, children: typing.Iterable[fltk.fegen.pyrt.terminalsrc.Span]) -> None:
        ...

    def children_content(self) -> typing.Iterator[fltk.fegen.pyrt.terminalsrc.Span]:
        ...

    def child_content(self) -> fltk.fegen.pyrt.terminalsrc.Span:
        ...

    def maybe_content(self) -> fltk.fegen.pyrt.terminalsrc.Span | None:
        ...

    def append_prefix(self, child: fltk.fegen.pyrt.terminalsrc.Span) -> None:
        ...

    def extend_prefix(self, children: typing.Iterable[fltk.fegen.pyrt.terminalsrc.Span]) -> None:
        ...

    def children_prefix(self) -> typing.Iterator[fltk.fegen.pyrt.terminalsrc.Span]:
        ...

    def child_prefix(self) -> fltk.fegen.pyrt.terminalsrc.Span:
        ...

    def maybe_prefix(self) -> fltk.fegen.pyrt.terminalsrc.Span | None:
        ...

class BlockComment(typing.Protocol):

    class Label:
        CONTENT: typing.ClassVar[object]
        END: typing.ClassVar[object]
        START: typing.ClassVar[object]
    span: fltk.fegen.pyrt.terminalsrc.Span
    children: list[tuple[Label | None, Trivia | fltk.fegen.pyrt.terminalsrc.Span]]

    def append(self, child: Trivia | fltk.fegen.pyrt.terminalsrc.Span, label: Label | None=None) -> None:
        ...

    def extend(self, children: typing.Iterable[Trivia | fltk.fegen.pyrt.terminalsrc.Span], label: Label | None=None) -> None:
        ...

    def child(self) -> tuple[Label | None, Trivia | fltk.fegen.pyrt.terminalsrc.Span]:
        ...

    def append_content(self, child: fltk.fegen.pyrt.terminalsrc.Span) -> None:
        ...

    def extend_content(self, children: typing.Iterable[fltk.fegen.pyrt.terminalsrc.Span]) -> None:
        ...

    def children_content(self) -> typing.Iterator[fltk.fegen.pyrt.terminalsrc.Span]:
        ...

    def child_content(self) -> fltk.fegen.pyrt.terminalsrc.Span:
        ...

    def maybe_content(self) -> fltk.fegen.pyrt.terminalsrc.Span | None:
        ...

    def append_end(self, child: fltk.fegen.pyrt.terminalsrc.Span) -> None:
        ...

    def extend_end(self, children: typing.Iterable[fltk.fegen.pyrt.terminalsrc.Span]) -> None:
        ...

    def children_end(self) -> typing.Iterator[fltk.fegen.pyrt.terminalsrc.Span]:
        ...

    def child_end(self) -> fltk.fegen.pyrt.terminalsrc.Span:
        ...

    def maybe_end(self) -> fltk.fegen.pyrt.terminalsrc.Span | None:
        ...

    def append_start(self, child: fltk.fegen.pyrt.terminalsrc.Span) -> None:
        ...

    def extend_start(self, children: typing.Iterable[fltk.fegen.pyrt.terminalsrc.Span]) -> None:
        ...

    def children_start(self) -> typing.Iterator[fltk.fegen.pyrt.terminalsrc.Span]:
        ...

    def child_start(self) -> fltk.fegen.pyrt.terminalsrc.Span:
        ...

    def maybe_start(self) -> fltk.fegen.pyrt.terminalsrc.Span | None:
        ...

class CstModule(typing.Protocol):

    @property
    def Grammar(self) -> type[Grammar]:
        ...

    @property
    def Rule(self) -> type[Rule]:
        ...

    @property
    def Alternatives(self) -> type[Alternatives]:
        ...

    @property
    def Items(self) -> type[Items]:
        ...

    @property
    def Item(self) -> type[Item]:
        ...

    @property
    def Term(self) -> type[Term]:
        ...

    @property
    def Disposition(self) -> type[Disposition]:
        ...

    @property
    def Quantifier(self) -> type[Quantifier]:
        ...

    @property
    def Identifier(self) -> type[Identifier]:
        ...

    @property
    def RawString(self) -> type[RawString]:
        ...

    @property
    def Literal(self) -> type[Literal]:
        ...

    @property
    def Trivia(self) -> type[Trivia]:
        ...

    @property
    def LineComment(self) -> type[LineComment]:
        ...

    @property
    def BlockComment(self) -> type[BlockComment]:
        ...
